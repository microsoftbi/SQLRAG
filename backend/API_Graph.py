from fastapi import APIRouter, Depends
from typing import Dict, Any
import json
import os
import re
import logging
from database import get_graph_db_connection
from config import settings

router = APIRouter(prefix="/graph", tags=["GraphDB"])


def log_llm_interaction(question: str, sql: str):
    """记录LLM交互日志"""
    logging.info(f"User Question: {question}")
    logging.info(f"Generated SQL: {sql}")
    logging.info("-" * 80)

def get_schema_content():
    """读取GraphDB Schema文件内容"""
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "00_GraphDB_SchemaOnly.sql")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading schema file: {e}")
        return ""


def extract_sql_from_response(response: str) -> str:
    """从大模型响应中提取SQL语句"""
    # 尝试找到 ```sql ... ``` 块
    sql_match = re.search(r"```sql\s*([\s\S]*?)\s*```", response)
    if sql_match:
        return sql_match.group(1).strip()
    
    # 尝试找到 ``` ... ``` 块
    sql_match = re.search(r"```\s*([\s\S]*?)\s*```", response)
    if sql_match:
        return sql_match.group(1).strip()
    
    # 如果没有找到代码块，直接返回（假设整个响应就是SQL）
    return response.strip()


def get_prompt_template():
    """从prompts目录加载GraphDB SQL generation prompt模板"""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "graph_sql_generation.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading prompt template: {e}")
        return ""


def call_llm_generate_sql(question: str, schema: str) -> str:
    """调用大模型生成SQL查询"""
    try:
        from langchain_deepseek import ChatDeepSeek
        from langchain_core.messages import HumanMessage
        from config import settings

        # 配置API
        api_key = settings.llm_api_key
        if not api_key:
            raise Exception("LLM_API_KEY not set in .env file")

        masked_key = api_key[:-10] + "**********" if len(api_key) > 10 else "**********"
        #logging.info(f"LLM API Key loaded: {masked_key}")
        #logging.info(f"LLM Base URL: {settings.llm_base_url}")
        #logging.info(f"LLM Model: {settings.llm_model}")

        llm = ChatDeepSeek(
            model=settings.llm_model,
            api_key=api_key,
            base_url=settings.llm_base_url,
            temperature=0,
            max_tokens=5000
        )

        # 从外部md文件加载prompt模板并注入参数
        template = get_prompt_template()
        if not template:
            raise Exception("Failed to load prompt template from backend/prompts/graph_sql_generation.md")
        prompt = template.replace("{schema}", schema).replace("{question}", question)

        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        sql = response.content
        return extract_sql_from_response(sql)
    except ImportError:
        raise Exception("langchain_deepseek library not installed, please install: pip install langchain-deepseek langchain-core")
    except Exception as e:
        print(f"Error calling LLM: {e}")
        raise


def get_fix_prompt_template():
    """从prompts目录加载GraphDB SQL fix prompt模板"""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "graph_sql_fix.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading fix prompt template: {e}")
        return ""


def call_llm_fix_sql(question: str, failed_sql: str, error: str, schema: str) -> str:
    """调用大模型修正SQL查询"""
    try:
        from langchain_deepseek import ChatDeepSeek
        from langchain_core.messages import HumanMessage
        from config import settings

        # 配置API
        api_key = settings.llm_api_key
        if not api_key:
            raise Exception("LLM_API_KEY not set in .env file")

        llm = ChatDeepSeek(
            model=settings.llm_model,
            api_key=api_key,
            base_url=settings.llm_base_url,
            temperature=0,
            max_tokens=5000
        )

        # 从外部md文件加载fix prompt模板并注入参数
        template = get_fix_prompt_template()
        if not template:
            raise Exception("Failed to load prompt template from backend/prompts/graph_sql_fix.md")
        prompt = (template.replace("{schema}", schema)
                         .replace("{question}", question)
                         .replace("{failed_sql}", failed_sql)
                         .replace("{error}", error))

        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        sql = response.content
        return extract_sql_from_response(sql)
    except ImportError:
        raise Exception("langchain_deepseek library not installed, please install: pip install langchain-deepseek langchain-core")
    except Exception as e:
        print(f"Error calling LLM fix: {e}")
        raise


def execute_sql_and_format_result(cursor, sql: str) -> str:
    """执行SQL并格式化结果"""
    try:
        cursor.execute(sql)
        
        # 获取列名
        columns = [column[0] for column in cursor.description] if cursor.description else []
        
        # 获取结果
        rows = cursor.fetchall()
        
        if not rows:
            return "查询结果为空"
        
        # 格式化结果
        result = []
        result.append("查询结果：")
        result.append("-" * 80)
        
        # 添加表头
        if columns:
            header = " | ".join(str(col) for col in columns)
            result.append(header)
            result.append("-" * 80)
        
        # 添加数据行
        for row in rows:
            row_str = " | ".join(str(cell) if cell is not None else "" for cell in row)
            result.append(row_str)
        
        result.append("-" * 80)
        result.append(f"共 {len(rows)} 条记录")
        
        return "\n".join(result)
    except Exception as e:
        return f"执行SQL时出错: {str(e)}"

def parse_graph_id(graph_id_str):
    """Parse SQL Server graph ID JSON to (table, id) - ensure id is int"""
    try:
        data = json.loads(graph_id_str)
        return (data.get("table"), int(data.get("id")))
    except:
        return (None, None)


@router.get("/data")
async def get_graph_data(conn=Depends(get_graph_db_connection)):
    try:
        cursor = conn.cursor()
        nodes = []
        edges = []

        node_lookup = {}

        node_tables = [
            ("Person", "Person"),
            ("CaseNode", "Case"),
            ("Organization", "Organization"),
            ("Location", "Location"),
            ("Item", "Item"),
            ("Event", "Event"),
        ]

        node_counter = 1
        for table_name, node_type in node_tables:
            try:
                cursor.execute(f"SELECT * FROM {table_name}")
                columns = [column[0] for column in cursor.description]
                for row in cursor.fetchall():
                    node = dict(zip(columns, row))

                    graph_id = None
                    for key in node.keys():
                        if key.startswith("$node_id"):
                            _, graph_id = parse_graph_id(node[key])
                            break

                    if graph_id is not None:
                        our_id = f"{node_type}_{node_counter}"
                        node_counter += 1
                        node_lookup[(table_name, graph_id)] = our_id
                        nodes.append({
                            "id": our_id,
                            "type": node_type,
                            "data": node
                        })
            except Exception as e:
                print(f"Error querying node table {table_name}: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"Loaded {len(nodes)} nodes, lookup has {len(node_lookup)} entries")

        edge_tables = [
            ("WorksAt", "WorksAt"),
            ("SubordinateOf", "SubordinateOf"),
            ("Investigates", "Investigates"),
            ("SuspectOf", "SuspectOf"),
            ("PerpetratorOf", "PerpetratorOf"),
            ("VictimOf", "VictimOf"),
            ("LocatedIn", "LocatedIn"),
            ("Owns", "Owns"),
            ("Found", "Found"),
            ("TransferredTo", "TransferredTo"),
            ("Witness", "Witness"),
            ("RelatedTo", "RelatedTo"),
            ("ConflictWith", "ConflictWith"),
            ("CooperatesWith", "CooperatesWith"),
            ("ReportedBy", "ReportedBy"),
            ("ConnectedTo", "ConnectedTo"),
            ("OccursAt", "OccursAt"),
            ("EvidenceOf", "EvidenceOf"),
            ("CoversUp", "CoversUp"),
            ("CommunicatesWith", "CommunicatesWith"),
        ]

        edge_counter = 1
        missing_edges = 0
        for table_name, edge_type in edge_tables:
            try:
                cursor.execute(f"SELECT * FROM {table_name}")
                columns = [column[0] for column in cursor.description]
                for row in cursor.fetchall():
                    edge = dict(zip(columns, row))

                    from_table = None
                    from_id = None
                    to_table = None
                    to_id = None

                    for key in edge.keys():
                        if key.startswith("$from_id"):
                            from_table, from_id = parse_graph_id(edge[key])
                        if key.startswith("$to_id"):
                            to_table, to_id = parse_graph_id(edge[key])

                    if from_table and from_id is not None and to_table and to_id is not None:
                        from_key = (from_table, from_id)
                        to_key = (to_table, to_id)

                        if from_key in node_lookup and to_key in node_lookup:
                            edges.append({
                                "id": f"edge_{edge_counter}",
                                "type": edge_type,
                                "from": node_lookup[from_key],
                                "to": node_lookup[to_key],
                                "data": edge
                            })
                            edge_counter += 1
                        else:
                            missing_edges += 1

            except Exception as e:
                print(f"Error querying edge table {table_name}: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"Loaded {len(edges)} edges, {missing_edges} missing")
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        print(f"Error in get_graph_data: {e}")
        import traceback
        traceback.print_exc()
        return {"nodes": [], "edges": [], "error": str(e)}

@router.post("/qa")
async def graph_qa(data: Dict[str, Any], conn=Depends(get_graph_db_connection)):
    question = data.get("question", "")
    use_llm = data.get("use_llm", True)
    
    if not question:
        return {"answer": "请输入问题"}

    try:
        cursor = conn.cursor()
        
        if use_llm:
            schema = get_schema_content()

            # 最多重试 MAX_RETRIES 次修正
            MAX_RETRIES = 2
            sql = call_llm_generate_sql(question, schema)
            log_llm_interaction(question, sql)

            for attempt in range(MAX_RETRIES + 1):
                if attempt > 0:
                    # 修正模式：将失败SQL和错误信息送回LLM
                    sql = call_llm_fix_sql(question, old_sql, error_msg, schema)
                    log_llm_interaction(question, sql)

                result = execute_sql_and_format_result(cursor, sql)

                # 检测是否出错
                if not result.startswith("执行SQL时出错"):
                    break

                error_msg = result
                old_sql = sql
                logging.warning(
                    f"SQL执行失败，第{attempt+1}次修正尝试 (question={question[:50]})"
                )

            return {
                "answer": result,
                "generated_sql": sql
            }
        else:
            # 使用原有的硬编码逻辑
            return legacy_graph_qa(cursor, question)

    except Exception as e:
        print(f"Error in graph_qa: {e}")
        import traceback
        traceback.print_exc()
        return {"answer": f"抱歉，处理问题时发生错误: {str(e)}"}


def legacy_graph_qa(cursor, question: str) -> dict:
    """原有的硬编码QA逻辑"""
    node_names = []

    people = ["方超", "刘直", "周荣", "张一昂", "李茜", "叶剑", "霍正",
              "朱亦飞", "刘背", "朗博文", "朗博图", "刚哥", "小毛",
              "李棚改", "杜聪", "陆一波", "宋星", "胡建仁", "方庸", "小飞"]

    cases = ["叶剑遇害案", "省城爆炸案", "金店抢劫案", "方庸贪腐案", "周荣涉黑案"]

    locations = ["枫林晚酒店", "荣城集团大楼", "三江口长途汽车站", "高速公路服务区",
                 "废品回收站", "东部新城", "涵洞", "周荣庄园", "郑勇兵住所"]

    orgs = ["荣城集团", "三江口日报", "朱亦飞文物贩卖团伙"]

    all_names = people + cases + locations + orgs

    for name in all_names:
        if name in question:
            node_names.append(name)

    if "哪些人物" in question and "案件" in question and ("多个" in question or "同时" in question):
        result, generated_sql = find_common_entities(cursor)
        return {"answer": result, "generated_sql": generated_sql}

    if not node_names:
        return {"answer": "未能识别问题中的实体，请尝试提及具体的人物、案件、地点或组织名称"}

    if "同时" in question or ("认识" in question and "又" in question) or ("和" in question and "有关系" in question):
        if len(node_names) >= 2:
            result, generated_sql = find_common_related_entities(cursor, node_names[0], node_names[1])
            return {"answer": result, "generated_sql": generated_sql}
        else:
            return {"answer": "请提供两个实体名称来查询它们之间共同关联的实体"}

    elif "关系" in question or "认识" in question or "联系" in question:
        if len(node_names) >= 2:
            result, generated_sql = find_relationship_between_nodes(cursor, node_names[0], node_names[1])
            return {"answer": result, "generated_sql": generated_sql}
        else:
            return {"answer": "请提供两个实体名称来查询它们之间的关系"}

    elif "涉及" in question or "关联" in question or "参与" in question:
        entity = node_names[0]
        result, generated_sql = find_related_entities(cursor, entity)
        return {"answer": result, "generated_sql": generated_sql}

    elif "路径" in question or "之间" in question:
        if len(node_names) >= 2:
            result, generated_sql = find_path_between_nodes(cursor, node_names[0], node_names[1])
            return {"answer": result, "generated_sql": generated_sql}
        else:
            return {"answer": "请提供两个实体名称来查询它们之间的路径"}

    elif "哪些" in question or "多个" in question:
        result, generated_sql = find_common_entities(cursor)
        return {"answer": result, "generated_sql": generated_sql}

    else:
        return {"answer": f"已识别到实体: {', '.join(node_names)}\n\n由于问题较为复杂，建议使用以下方式提问：\n- 'A和B是什么关系？'\n- '某案件涉及哪些人物？'\n- '从A到B之间有哪些关联路径？'\n- '谁认识A，同时又和B有关系？'"}


def find_relationship_between_nodes(cursor, name1, name2):
    """查找两个节点之间的直接关系（使用 MATCH 图查询），返回 (answer_text, sql_pattern)"""
    try:
        # Person -> Person 边表
        person_edge_tables = [
            "SubordinateOf", "RelatedTo", "ConflictWith",
            "CooperatesWith", "CommunicatesWith"
        ]

        relationships = []

        # 方向: name1 ->(edge)-> name2
        for edge_table in person_edge_tables:
            cursor.execute(f"""
                SELECT 1 FROM Person p1, {edge_table} e, Person p2
                WHERE MATCH(p1-(e)->p2) AND p1.name = ? AND p2.name = ?
            """, (name1, name2))
            if cursor.fetchone():
                relationships.append(f"{name1} ->({edge_table})-> {name2}")

        # 方向: name2 ->(edge)-> name1
        for edge_table in person_edge_tables:
            cursor.execute(f"""
                SELECT 1 FROM Person p1, {edge_table} e, Person p2
                WHERE MATCH(p1-(e)->p2) AND p1.name = ? AND p2.name = ?
            """, (name2, name1))
            if cursor.fetchone():
                relationships.append(f"{name2} ->({edge_table})-> {name1}")

        # 生成一个代表性的SQL示例供显示
        sql_pattern = (
            f"MATCH 图查询 (Person → Person 边表: {', '.join(person_edge_tables)})\n"
            f"示例: SELECT 1 FROM Person p1, [EdgeTable] e, Person p2\n"
            f"       WHERE MATCH(p1-(e)->p2) AND p1.name = '{name1}' AND p2.name = '{name2}'"
        )

        if relationships:
            return f"{name1} 和 {name2} 之间的关系：\n" + "\n".join(relationships), sql_pattern
        else:
            return f"{name1} 和 {name2} 之间没有直接关系，可能存在间接关联", sql_pattern

    except Exception as e:
        return f"查询关系时出错: {str(e)}", ""


def find_related_entities(cursor, entity_name):
    """查找与某个实体相关联的所有实体（使用 MATCH 图查询），返回 (answer_text, sql_string)"""
    try:
        related, sql = _find_related_via_match(cursor, entity_name)

        if related:
            result = f"与 '{entity_name}' 相关联的实体：\n"
            for name, rels in related.items():
                result += f"- {name}: {', '.join(f'({r})' for r in rels)}\n"
            return result, sql
        else:
            return f"没有找到与 '{entity_name}' 相关联的实体", sql

    except Exception as e:
        return f"查询关联实体时出错: {str(e)}", ""


def _find_related_via_match(cursor, person_name):
    """使用 MATCH 查询指定人物的所有关联实体（返回 (dict: {实体名: [边名]}, sql_string)）"""
    sql = """
        WITH RelatedCTE AS (
            -- ===== 出向边 (Person -> 其他节点) =====

            -- Person -> Person
            SELECT p2.name AS related_name, 'SubordinateOf' AS edge_name
            FROM Person p1, SubordinateOf e, Person p2
            WHERE MATCH(p1-(e)->p2) AND p1.name = ?
            UNION SELECT p2.name, 'RelatedTo'
            FROM Person p1, RelatedTo e, Person p2
            WHERE MATCH(p1-(e)->p2) AND p1.name = ?
            UNION SELECT p2.name, 'ConflictWith'
            FROM Person p1, ConflictWith e, Person p2
            WHERE MATCH(p1-(e)->p2) AND p1.name = ?
            UNION SELECT p2.name, 'CooperatesWith'
            FROM Person p1, CooperatesWith e, Person p2
            WHERE MATCH(p1-(e)->p2) AND p1.name = ?
            UNION SELECT p2.name, 'CommunicatesWith'
            FROM Person p1, CommunicatesWith e, Person p2
            WHERE MATCH(p1-(e)->p2) AND p1.name = ?

            -- Person -> CaseNode
            UNION SELECT c.name, 'Investigates'
            FROM Person p1, Investigates e, CaseNode c
            WHERE MATCH(p1-(e)->c) AND p1.name = ?
            UNION SELECT c.name, 'SuspectOf'
            FROM Person p1, SuspectOf e, CaseNode c
            WHERE MATCH(p1-(e)->c) AND p1.name = ?
            UNION SELECT c.name, 'PerpetratorOf'
            FROM Person p1, PerpetratorOf e, CaseNode c
            WHERE MATCH(p1-(e)->c) AND p1.name = ?
            UNION SELECT c.name, 'VictimOf'
            FROM Person p1, VictimOf e, CaseNode c
            WHERE MATCH(p1-(e)->c) AND p1.name = ?
            UNION SELECT c.name, 'CoversUp'
            FROM Person p1, CoversUp e, CaseNode c
            WHERE MATCH(p1-(e)->c) AND p1.name = ?

            -- Person -> Organization
            UNION SELECT o.name, 'WorksAt'
            FROM Person p1, WorksAt e, Organization o
            WHERE MATCH(p1-(e)->o) AND p1.name = ?

            -- Person -> Item
            UNION SELECT i.name, 'Owns'
            FROM Person p1, Owns e, Item i
            WHERE MATCH(p1-(e)->i) AND p1.name = ?
            UNION SELECT i.name, 'Found'
            FROM Person p1, Found e, Item i
            WHERE MATCH(p1-(e)->i) AND p1.name = ?

            -- Person -> Location
            UNION SELECT l.name, 'LocatedIn'
            FROM Person p1, LocatedIn e, Location l
            WHERE MATCH(p1-(e)->l) AND p1.name = ?

            -- Person -> Event
            UNION SELECT ev.name, 'Witness'
            FROM Person p1, Witness e, Event ev
            WHERE MATCH(p1-(e)->ev) AND p1.name = ?

            -- ===== 入向边 (其他节点 -> Person) =====

            -- Person <- Person
            UNION SELECT p2.name, 'SubordinateOf'
            FROM Person p1, SubordinateOf e, Person p2
            WHERE MATCH(p2-(e)->p1) AND p1.name = ?
            UNION SELECT p2.name, 'RelatedTo'
            FROM Person p1, RelatedTo e, Person p2
            WHERE MATCH(p2-(e)->p1) AND p1.name = ?
            UNION SELECT p2.name, 'ConflictWith'
            FROM Person p1, ConflictWith e, Person p2
            WHERE MATCH(p2-(e)->p1) AND p1.name = ?
            UNION SELECT p2.name, 'CooperatesWith'
            FROM Person p1, CooperatesWith e, Person p2
            WHERE MATCH(p2-(e)->p1) AND p1.name = ?
            UNION SELECT p2.name, 'CommunicatesWith'
            FROM Person p1, CommunicatesWith e, Person p2
            WHERE MATCH(p2-(e)->p1) AND p1.name = ?

            -- CaseNode -> Person (ReportedBy)
            UNION SELECT c.name, 'ReportedBy'
            FROM Person p1, ReportedBy e, CaseNode c
            WHERE MATCH(c-(e)->p1) AND p1.name = ?

            -- Item -> Person (TransferredTo)
            UNION SELECT i.name, 'TransferredTo'
            FROM Person p1, TransferredTo e, Item i
            WHERE MATCH(i-(e)->p1) AND p1.name = ?
        )
        SELECT related_name, edge_name
        FROM RelatedCTE
        WHERE related_name != ?
    """
    cursor.execute(sql, [person_name] * 23)

    related = {}
    for row in cursor.fetchall():
        name, edge = row
        if name not in related:
            related[name] = []
        related[name].append(edge)
    return related, sql


def find_common_related_entities(cursor, name1, name2):
    """查找同时与name1和name2都相关联的实体（使用 MATCH 图查询），返回 (answer_text, sql_string)"""
    try:
        related_to_1, sql1 = _find_related_via_match(cursor, name1)
        related_to_2, _ = _find_related_via_match(cursor, name2)

        common = set(related_to_1.keys()) & set(related_to_2.keys())

        if common:
            result = f"同时与 '{name1}' 和 '{name2}' 都有关联的实体：\n\n"
            for entity in common:
                rels_1 = related_to_1.get(entity, [])
                rels_2 = related_to_2.get(entity, [])
                result += f"- {entity}:\n"
                result += f"  与{name1}的关系: {', '.join(rels_1)}\n"
                result += f"  与{name2}的关系: {', '.join(rels_2)}\n"
            return result, sql1
        else:
            return f"没有找到同时与 '{name1}' 和 '{name2}' 都有关联的实体", sql1

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"查询共同关联实体时出错: {str(e)}", ""


def find_path_between_nodes(cursor, name1, name2):
    """查找两个节点之间的路径，返回 (answer_text, sql_string)"""
    try:
        node1_id = get_node_graph_id(cursor, name1)
        node2_id = get_node_graph_id(cursor, name2)

        if not node1_id or not node2_id:
            return f"未能找到实体 '{name1}' 或 '{name2}' 的信息", ""

        return f"从 '{name1}' 到 '{name2}' 的路径分析：\n\n由于当前系统限制，路径查询功能需要更复杂的图算法支持。建议使用可视化界面查看节点的关联关系。", ""

    except Exception as e:
        return f"查询路径时出错: {str(e)}", ""


def find_common_entities(cursor):
    """查找出现在多个案件中的人物（使用 MATCH 图查询），返回 (answer_text, sql_string)"""
    sql = """
        WITH PersonCaseCTE AS (
            SELECT p.name AS person_name, c.name AS case_name
            FROM Person p, SuspectOf so, CaseNode c
            WHERE MATCH(p-(so)->c)
            UNION
            SELECT p.name, c.name
            FROM Person p, VictimOf vo, CaseNode c
            WHERE MATCH(p-(vo)->c)
            UNION
            SELECT p.name, c.name
            FROM Person p, PerpetratorOf po, CaseNode c
            WHERE MATCH(p-(po)->c)
            UNION
            SELECT p.name, c.name
            FROM Person p, Witness w, CaseNode c
            WHERE MATCH(p-(w)->c)
            UNION
            SELECT p.name, c.name
            FROM Person p, Investigates inv, CaseNode c
            WHERE MATCH(p-(inv)->c)
        )
        SELECT person_name, COUNT(DISTINCT case_name) AS case_count
        FROM PersonCaseCTE
        GROUP BY person_name
        HAVING COUNT(DISTINCT case_name) > 1
        ORDER BY COUNT(DISTINCT case_name) DESC
    """
    try:
        cursor.execute(sql)

        results = []
        for row in cursor.fetchall():
            if row[1] > 0:
                results.append(f"{row[0]}: 涉及 {row[1]} 个案件")

        if results:
            return "出现在多个案件中的人物：\n" + "\n".join(results), sql
        else:
            return "没有找到同时出现在多个案件中的人物", sql

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"查询时出错: {str(e)}"


def get_node_graph_id(cursor, name):
    """根据名称获取节点的graph_id"""
    node_tables = ["Person", "CaseNode", "Organization", "Location", "Item", "Event"]

    for table in node_tables:
        try:
            cursor.execute(f"SELECT $node_id FROM {table} WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return str(row[0])
        except:
            continue
    return None


def get_node_name_from_graph_id(cursor, graph_id_str):
    """根据graph_id获取节点名称"""
    node_tables = ["Person", "CaseNode", "Organization", "Location", "Item", "Event"]

    for table in node_tables:
        try:
            cursor.execute(f"SELECT name FROM {table} WHERE $node_id = JSON_QUERY(?)", (graph_id_str,))
            row = cursor.fetchone()
            if row:
                return row[0]
        except:
            continue
    return None
