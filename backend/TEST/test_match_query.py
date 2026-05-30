import pyodbc
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import settings

def test_match_query():
    conn = None
    try:
        conn_str = (
            f"DRIVER={settings.DB_DRIVER};"
            f"SERVER={settings.DB_SERVER};"
            f"DATABASE={settings.GRAPH_DB_NAME};"
            f"Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        print("=" * 80)
        print("测试SQL Server图查询（MATCH）方式")
        print("=" * 80)

        query = """
        WITH PersonCaseRelations AS (
            SELECT p.name AS person_name, c.name AS case_name, 'SuspectOf' AS relation_type
            FROM Person p, SuspectOf so, CaseNode c
            WHERE MATCH(p-(so)->c)
            
            UNION ALL
            
            SELECT p.name AS person_name, c.name AS case_name, 'VictimOf' AS relation_type
            FROM Person p, VictimOf vo, CaseNode c
            WHERE MATCH(p-(vo)->c)
            
            UNION ALL
            
            SELECT p.name AS person_name, c.name AS case_name, 'Investigates' AS relation_type
            FROM Person p, Investigates inv, CaseNode c
            WHERE MATCH(p-(inv)->c)
            
            UNION ALL
            
            SELECT p.name AS person_name, c.name AS case_name, 'PerpetratorOf' AS relation_type
            FROM Person p, PerpetratorOf po, CaseNode c
            WHERE MATCH(p-(po)->c)
            
            UNION ALL
            
            SELECT p.name AS person_name, c.name AS case_name, 'Witness' AS relation_type
            FROM Person p, Witness w, CaseNode c
            WHERE MATCH(p-(w)->c)
        )
        SELECT 
            person_name,
            COUNT(DISTINCT case_name) AS case_count,
            STRING_AGG(DISTINCT case_name, ', ') AS involved_cases,
            STRING_AGG(DISTINCT relation_type, ', ') AS relation_types
        FROM PersonCaseRelations
        GROUP BY person_name
        HAVING COUNT(DISTINCT case_name) > 1
        ORDER BY case_count DESC
        """

        print("\n执行查询...")
        cursor.execute(query)

        print("\n查询结果：")
        print("-" * 80)
        print(f"{'人物':<10} {'案件数':<10} {'涉及案件':<50} {'关系类型':<20}")
        print("-" * 80)
        
        results = []
        for row in cursor.fetchall():
            person_name = row[0]
            case_count = row[1]
            involved_cases = row[2] or "无"
            relation_types = row[3] or "无"
            print(f"{person_name:<10} {case_count:<10} {involved_cases:<50} {relation_types:<20}")
            results.append((person_name, case_count, involved_cases, relation_types))

        print("-" * 80)
        
        return results

    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_match_query()
