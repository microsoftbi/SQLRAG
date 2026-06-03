from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pyodbc
import json
import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import settings
from database import get_graph_db_connection, get_vector_db_connection

# 获取当前脚本所在目录，确保日志文件在 backend 目录下
_log_dir = os.path.dirname(os.path.abspath(__file__))
_log_path = os.path.join(_log_dir, 'llm_sql_logs.log')

logging.basicConfig(
    filename=_log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# 同时输出到控制台，方便实时查看
_console = logging.StreamHandler()
_console.setLevel(logging.DEBUG)
_console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger('').addHandler(_console)

print(f"日志文件路径: {_log_path}")

def log_llm_interaction(question: str, sql: str):
    """记录LLM交互日志"""
    logging.info(f"User Question: {question}")
    logging.info(f"Generated SQL: {sql}")
    logging.info("-" * 80)

app = FastAPI(title="SQLRAG API")

logging.info("SQLRAG API 启动成功")
logging.info(f"Embedding 模型: {settings.embedding_model}")
logging.info(f"Ollama 地址: {settings.ollama_base_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def call_llm_generate_sql(question: str, schema: str) -> str:
    """调用大模型生成SQL查询"""
    try:
        from openai import OpenAI
        from config import settings
        
        # 配置API
        api_key = settings.llm_api_key
        if not api_key:
            raise Exception("LLM_API_KEY not set in .env file")

        masked_key = api_key[:-10] + "**********" if len(api_key) > 10 else "**********"
        logging.info(f"LLM API Key loaded: {masked_key}")
        logging.info(f"LLM Base URL: {settings.llm_base_url}")
        logging.info(f"LLM Model: {settings.llm_model}")

        client = OpenAI(
            api_key=api_key,
            base_url=settings.llm_base_url
        )
        
        prompt = f"""你是一个SQL Server图数据库查询专家。请根据以下GraphDB Schema和用户问题，生成一个使用CTE + MATCH子句的SQL Server图查询语句。

Schema：
{schema}

用户问题：
{question}

要求：
1. 使用CTE（WITH子句）和MATCH子句进行图查询
2. MATCH子句的语法是：MATCH(node1-(edge)->node2)
3. 查询结果应该以易于理解的方式返回
4. 只返回SQL语句，不要其他说明
5. 使用STRING_AGG函数来聚合多个结果
6. 如果涉及多个关系类型，请使用UNION ALL在CTE中组合

只返回SQL语句，不要生成其它任何跟SQL语句无关的内容："""

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        sql = response.choices[0].message.content
        return extract_sql_from_response(sql)
    except ImportError:
        raise Exception("openai library not installed, please install: pip install openai")
    except Exception as e:
        print(f"Error calling LLM: {e}")
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


@app.get("/")
async def root():
    return {"message": "SQLRAG API is running"}


def parse_graph_id(graph_id_str):
    """Parse SQL Server graph ID JSON to (table, id) - ensure id is int"""
    try:
        data = json.loads(graph_id_str)
        return (data.get("table"), int(data.get("id")))
    except:
        return (None, None)


@app.get("/graph/data")
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


@app.get("/vector/documents")
async def get_documents(knowledge_base_id: int = None, conn=Depends(get_vector_db_connection)):
    cursor = conn.cursor()
    if knowledge_base_id:
        cursor.execute("""
            SELECT d.*, kb.Name AS KnowledgeBaseName
            FROM Documents d
            LEFT JOIN KnowledgeBases kb ON d.KnowledgeBaseId = kb.KnowledgeBaseId
            WHERE d.IsDeleted = 0 AND d.KnowledgeBaseId = ?
            ORDER BY d.CreatedAt DESC
        """, (knowledge_base_id,))
    else:
        cursor.execute("""
            SELECT d.*, kb.Name AS KnowledgeBaseName
            FROM Documents d
            LEFT JOIN KnowledgeBases kb ON d.KnowledgeBaseId = kb.KnowledgeBaseId
            WHERE d.IsDeleted = 0
            ORDER BY d.CreatedAt DESC
        """)
    columns = [column[0] for column in cursor.description]
    documents = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"documents": documents}


@app.post("/vector/documents")
async def create_document(data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Documents (Title, Content, Source, Metadata, KnowledgeBaseId) VALUES (?, ?, ?, ?, ?)",
        (data.get("title"), data.get("content"), data.get("source"), data.get("metadata", "{}"),
         data.get("knowledge_base_id")),
    )
    conn.commit()
    # 获取新 ID
    cursor.execute("SELECT IDENT_CURRENT('Documents')")
    new_id = int(cursor.fetchone()[0])
    return {"message": "Document created", "document_id": new_id}


@app.put("/vector/documents/{document_id}")
async def update_document(document_id: int, data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    """更新文档信息（目前支持修改 knowledge_base_id）"""
    cursor = conn.cursor()
    cursor.execute("SELECT DocumentId FROM Documents WHERE DocumentId = ? AND IsDeleted = 0", (document_id,))
    if not cursor.fetchone():
        return JSONResponse(status_code=404, content={"message": "文档不存在"})
    try:
        if "knowledge_base_id" in data:
            cursor.execute(
                "UPDATE Documents SET KnowledgeBaseId = ? WHERE DocumentId = ?",
                (data["knowledge_base_id"], document_id),
            )
        conn.commit()
        return {"message": "文档已更新"}
    except Exception as e:
        conn.rollback()
        return JSONResponse(status_code=500, content={"message": f"更新失败: {str(e)}"})


@app.get("/vector/documents/{document_id}/chunks")
async def get_document_chunks(document_id: int, conn=Depends(get_vector_db_connection)):
    """获取指定文档的所有分块"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM TextChunks WHERE DocumentId = ? AND IsDeleted = 0 ORDER BY ChunkIndex",
        (document_id,)
    )
    columns = [column[0] for column in cursor.description]
    chunks = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # 如果没有分块，尝试从文档内容创建分块
    if not chunks:
        cursor.execute("SELECT Content FROM Documents WHERE DocumentId = ?", (document_id,))
        doc = cursor.fetchone()
        if doc:
            content = doc[0]
            chunks = create_chunks_from_content(document_id, content, conn)
    
    return {"chunks": chunks}


def create_chunks_from_content(document_id: int, content: str, conn,
                                chunk_size: int = None, chunk_overlap: int = None) -> List[Dict]:
    """使用 LangChain RecursiveCharacterTextSplitter 创建分块并入库"""
    if not content:
        return []

    # 支持自定义分块参数，默认从 settings 读取
    cs = chunk_size or settings.chunk_size
    co = chunk_overlap or settings.chunk_overlap

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=cs,
        chunk_overlap=co,
        add_start_index=True,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )

    texts = text_splitter.split_text(content)
    chunks = []

    for i, chunk_text in enumerate(texts):
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO TextChunks (DocumentId, ChunkIndex, ChunkText, CreatedAt) VALUES (?, ?, ?, GETDATE())",
            (document_id, i, chunk_text)
        )
        conn.commit()

        cursor.execute("SELECT IDENT_CURRENT('TextChunks')")
        row = cursor.fetchone()
        chunk_id = int(row[0]) if row and row[0] is not None else None

        chunks.append({
            "ChunkId": chunk_id,
            "DocumentId": document_id,
            "ChunkIndex": i,
            "ChunkText": chunk_text,
            "CreatedAt": None
        })

    logging.info(f"Created {len(chunks)} chunks for document {document_id}")
    return chunks


def get_embedding(text: str) -> List[float]:
    """调用 Ollama /api/embeddings 获取文本的嵌入向量"""
    if not text or not text.strip():
        raise Exception("不能为空文本生成嵌入向量")

    try:
        import urllib.request
        import json

        url = f"{settings.ollama_base_url.rstrip('/')}/api/embeddings"
        payload = json.dumps({
            "model": settings.embedding_model,
            "prompt": text,
        }).encode()

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        vector = data.get("embedding", [])
        if not vector:
            raise Exception("Ollama 返回了空的嵌入向量")

        return vector
    except urllib.request.HTTPError as e:
        error_body = e.read().decode()
        logging.error(f"Ollama HTTP error {e.code}: {error_body}")
        raise Exception(f"Ollama 返回错误 ({e.code}): {error_body}")
    except urllib.request.URLError:
        logging.error(f"Cannot connect to Ollama at {settings.ollama_base_url}")
        raise Exception(f"无法连接到 Ollama，请确保 Ollama 已启动（{settings.ollama_base_url}）")
    except Exception as e:
        logging.error(f"Embedding error: {e}")
        raise


def embed_chunks_for_document(document_id: int, conn) -> Dict:
    """为指定文档的所有未嵌入分块生成向量并存入 VectorIndex"""
    cursor = conn.cursor()

    # 查询还没有嵌入向量的分块
    cursor.execute("""
        SELECT c.ChunkId, c.ChunkText
        FROM TextChunks c
        LEFT JOIN VectorIndex v ON c.ChunkId = v.ChunkId
        WHERE c.DocumentId = ? AND c.IsDeleted = 0 AND v.ChunkId IS NULL
        ORDER BY c.ChunkIndex
    """, (document_id,))
    rows = cursor.fetchall()

    if not rows:
        return {"message": "所有分块已嵌入，无需重复处理", "embedded": 0}

    # VECTOR INDEX 会阻塞 INSERT，先删除，插入完成后重建
    cursor.execute("DROP INDEX IF EXISTS idx_content_vector ON VectorIndex")
    conn.commit()

    embedded_count = 0
    for chunk_id, chunk_text in rows:
        if not chunk_text or not chunk_text.strip():
            logging.warning(f"Skipping empty chunk {chunk_id}")
            continue
        try:
            vector = get_embedding(chunk_text)
            vector_json = json.dumps(vector)
            cursor.execute("""
                DECLARE @json_str NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), ?);
                DECLARE @v VECTOR(768) = CAST(@json_str AS VECTOR(768));
                INSERT INTO VectorIndex (ChunkId, EmbeddingVector, CreatedAt)
                VALUES (?, @v, GETDATE());
            """, (vector_json, chunk_id))
            conn.commit()
            embedded_count += 1
            logging.info(f"Embedded chunk {chunk_id} for document {document_id}")
        except Exception as e:
            logging.error(f"Failed to embed chunk {chunk_id}: {e}")
            conn.rollback()
            raise

    # 重建 VECTOR INDEX（必须在一个独立的 autocommit 连接中执行）
    try:
        from config import get_db_connection_string
        rebuild_conn = pyodbc.connect(get_db_connection_string("VectorDB"), autocommit=True)
        rebuild_cursor = rebuild_conn.cursor()
        rebuild_cursor.execute("""
            CREATE VECTOR INDEX idx_content_vector
            ON dbo.VectorIndex(EmbeddingVector)
            WITH (METRIC = 'cosine');
        """)
        rebuild_conn.close()
        logging.info(f"Vector index rebuilt after inserting {embedded_count} chunks")
    except Exception as e:
        logging.warning(f"Vector index rebuild failed: {e}")

    logging.info(f"Embedded {embedded_count} chunks for document {document_id}")
    return {"message": f"成功嵌入 {embedded_count} 个分块", "embedded": embedded_count}


@app.post("/vector/documents/{document_id}/embed")
async def embed_document(document_id: int, conn=Depends(get_vector_db_connection)):
    """为指定文档的分块生成嵌入向量"""
    try:
        # 先确保分块已存在
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM TextChunks WHERE DocumentId = ? AND IsDeleted = 0",
            (document_id,)
        )
        chunk_count = cursor.fetchone()[0]

        if chunk_count == 0:
            # 没有分块则先创建分块
            cursor.execute("SELECT Content FROM Documents WHERE DocumentId = ?", (document_id,))
            doc = cursor.fetchone()
            if not doc:
                return JSONResponse(status_code=404, content={"message": "文档不存在"})
            create_chunks_from_content(document_id, doc[0], conn)

        result = embed_chunks_for_document(document_id, conn)
        return result

    except Exception as e:
        logging.error(f"Error embedding document {document_id}: {e}")
        return JSONResponse(status_code=500, content={"message": f"嵌入失败: {str(e)}"})


@app.post("/vector/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    knowledge_base_id: int = None,
    conn=Depends(get_vector_db_connection),
):
    """上传文档并自动提取内容"""
    try:
        import tempfile
        
        # 保存上传的文件到临时目录
        file_content = await file.read()
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # 提取文件内容
        text_content = ""
        if file_ext in ['.txt', '.md']:
            text_content = file_content.decode('utf-8', errors='ignore')
        elif file_ext == '.docx':
            text_content = extract_docx_content(file_content)
        elif file_ext == '.pdf':
            text_content = extract_pdf_content(file_content)
        else:
            text_content = file_content.decode('utf-8', errors='ignore')
        
        # 保存到数据库（仅保存文档，不自动切块和嵌入）
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Documents (Title, Content, Source, Metadata, KnowledgeBaseId) VALUES (?, ?, ?, ?, ?)",
            (
                file.filename,
                text_content,
                f"上传文件: {file.filename}",
                json.dumps({
                    "filename": file.filename,
                    "filesize": len(file_content),
                    "filetype": file_ext,
                    "upload_time": datetime.now().isoformat()
                }),
                knowledge_base_id,
            ),
        )
        conn.commit()

        # 使用单独的查询获取刚插入的文档ID
        cursor.execute("SELECT IDENT_CURRENT('Documents')")
        row = cursor.fetchone()
        document_id = int(row[0]) if row and row[0] is not None else None

        if document_id is None or document_id == 0:
            raise Exception("Failed to get document ID after insert")

        logging.info(f"Document uploaded: {file.filename}, ID: {document_id}")

        return JSONResponse(
            status_code=200,
            content={"message": "Document uploaded successfully", "filename": file.filename, "documentId": document_id}
        )

    except Exception as e:
        logging.error(f"Error uploading document: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"message": f"Error uploading document: {str(e)}", "error": True}
        )


@app.post("/vector/documents/{document_id}/preview-chunks")
async def preview_document_chunks(document_id: int, data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    """预览文档的分块结果（不入库）"""
    cursor = conn.cursor()
    cursor.execute("SELECT Content FROM Documents WHERE DocumentId = ? AND IsDeleted = 0", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        return JSONResponse(status_code=404, content={"message": "文档不存在"})

    content = doc[0]
    if not content:
        return {"chunks": []}

    chunk_size = data.get("chunk_size") or settings.chunk_size
    chunk_overlap = data.get("chunk_overlap") or settings.chunk_overlap

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )

    texts = text_splitter.split_text(content)
    chunks = [
        {"ChunkIndex": i, "ChunkText": t, "Length": len(t)}
        for i, t in enumerate(texts)
    ]

    return {"chunks": chunks, "total_chunks": len(chunks)}


@app.post("/vector/documents/{document_id}/commit-chunks")
async def commit_document_chunks(document_id: int, data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    """将文档按指定参数切块并入库，同时生成向量嵌入"""
    cursor = conn.cursor()
    cursor.execute("SELECT Content FROM Documents WHERE DocumentId = ? AND IsDeleted = 0", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        return JSONResponse(status_code=404, content={"message": "文档不存在"})

    content = doc[0]
    if not content:
        return JSONResponse(status_code=400, content={"message": "文档内容为空"})

    # 先删除已存在的分块和向量（防止重复提交）
    cursor.execute("""
        UPDATE v SET IsDeleted = 1
        FROM VectorIndex v JOIN TextChunks c ON v.ChunkId = c.ChunkId
        WHERE c.DocumentId = ?
    """, (document_id,))
    cursor.execute("UPDATE TextChunks SET IsDeleted = 1 WHERE DocumentId = ?", (document_id,))
    conn.commit()

    chunk_size = data.get("chunk_size") or settings.chunk_size
    chunk_overlap = data.get("chunk_overlap") or settings.chunk_overlap

    # 创建分块并入库
    chunks = create_chunks_from_content(document_id, content, conn,
                                         chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # 生成向量嵌入
    try:
        embed_result = embed_chunks_for_document(document_id, conn)
        embedded = embed_result.get("embedded", 0)
    except Exception as e:
        logging.warning(f"Embedding failed during commit: {e}")
        embedded = 0

    return {
        "message": f"已创建 {len(chunks)} 个分块，已嵌入 {embedded} 个向量",
        "total_chunks": len(chunks),
        "embedded": embedded,
    }


def extract_docx_content(file_content: bytes) -> str:
    """提取Word文档内容"""
    try:
        from docx import Document
        import io
        
        doc = Document(io.BytesIO(file_content))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        logging.error(f"Error extracting docx: {e}")
        return ""


def extract_pdf_content(file_content: bytes) -> str:
    """提取PDF文档内容"""
    try:
        from PyPDF2 import PdfReader
        import io
        
        reader = PdfReader(io.BytesIO(file_content))
        full_text = []
        for page in reader.pages:
            full_text.append(page.extract_text())
        return '\n'.join(full_text)
    except Exception as e:
        logging.error(f"Error extracting pdf: {e}")
        return ""


@app.get("/vector/config")
async def get_config():
    """获取当前配置"""
    return {
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "embedding_model": settings.embedding_model,
        "ollama_base_url": settings.ollama_base_url,
    }


@app.put("/vector/config")
async def update_config(data: Dict[str, Any]):
    """更新 .env 文件中的配置（chunk_size, chunk_overlap, embedding_model）"""
    allowed_keys = {"chunk_size", "chunk_overlap", "embedding_model", "ollama_base_url"}
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    try:
        # 读取当前 .env
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 小写 key -> .env 中的大写变量名
        key_to_env = {
            "chunk_size": "CHUNK_SIZE",
            "chunk_overlap": "CHUNK_OVERLAP",
            "embedding_model": "EMBEDDING_MODEL",
            "ollama_base_url": "OLLAMA_BASE_URL",
        }

        updated = []
        changed = {}
        for line in lines:
            stripped = line.strip()
            for key in allowed_keys:
                env_key = key_to_env[key]
                if stripped.startswith(env_key + "="):
                    new_val = str(data.get(key))
                    if new_val and key in data:
                        old_val = stripped.split("=", 1)[1]
                        if old_val != new_val:
                            changed[key] = (old_val, new_val)
                            line = f"{env_key}={new_val}\n"
                    break
            updated.append(line)

        if changed:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(updated)
            # 同步更新内存中的 settings
            for key, (_, new_val) in changed.items():
                setattr(settings, key, int(new_val) if key in ("chunk_size", "chunk_overlap") else new_val)
            logging.info(f"Config updated: {changed}")
            return {"message": "配置已更新", "changed": {k: {"old": v[0], "new": v[1]} for k, v in changed.items()}}
        else:
            return {"message": "配置无变化", "changed": {}}

    except Exception as e:
        logging.error(f"Error updating config: {e}")
        return JSONResponse(status_code=500, content={"message": f"更新配置失败: {str(e)}"})


# ====== 知识库管理 ======


@app.get("/vector/knowledge-bases")
async def get_knowledge_bases(conn=Depends(get_vector_db_connection)):
    """获取所有知识库"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM KnowledgeBases WHERE IsDeleted = 0 ORDER BY CreatedAt DESC")
    columns = [column[0] for column in cursor.description]
    kbs = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"knowledge_bases": kbs}


@app.post("/vector/knowledge-bases")
async def create_knowledge_base(data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    """创建知识库"""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO KnowledgeBases (Name, Description) VALUES (?, ?)",
        (data.get("name"), data.get("description", "")),
    )
    conn.commit()
    cursor.execute("SELECT IDENT_CURRENT('KnowledgeBases')")
    new_id = int(cursor.fetchone()[0])
    return {"message": "知识库已创建", "knowledge_base_id": new_id}


@app.put("/vector/knowledge-bases/{kb_id}")
async def update_knowledge_base(kb_id: int, data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    """更新知识库名称/描述"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE KnowledgeBases SET Name = ?, Description = ?, UpdatedAt = GETDATE() WHERE KnowledgeBaseId = ? AND IsDeleted = 0",
        (data.get("name"), data.get("description", ""), kb_id),
    )
    if cursor.rowcount == 0:
        return JSONResponse(status_code=404, content={"message": "知识库不存在"})
    conn.commit()
    return {"message": "知识库已更新"}


@app.delete("/vector/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: int, conn=Depends(get_vector_db_connection)):
    """软删除知识库，同时将下属文档的 KnowledgeBaseId 置 NULL"""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Documents SET KnowledgeBaseId = NULL WHERE KnowledgeBaseId = ?", (kb_id,))
        cursor.execute("UPDATE KnowledgeBases SET IsDeleted = 1 WHERE KnowledgeBaseId = ?", (kb_id,))
        if cursor.rowcount == 0:
            conn.rollback()
            return JSONResponse(status_code=404, content={"message": "知识库不存在"})
        conn.commit()
        return {"message": "知识库已删除，下属文档已解除关联"}
    except Exception as e:
        conn.rollback()
        logging.error(f"Error deleting knowledge base {kb_id}: {e}")
        return JSONResponse(status_code=500, content={"message": f"删除失败: {str(e)}"})


@app.get("/vector/chunks")
async def get_chunks(conn=Depends(get_vector_db_connection)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TextChunks WHERE IsDeleted = 0")
    columns = [column[0] for column in cursor.description]
    chunks = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"chunks": chunks}


@app.delete("/vector/documents/{document_id}")
async def delete_document(document_id: int, conn=Depends(get_vector_db_connection)):
    """删除文档及其关联的 TextChunks 和 VectorIndex 记录（软删除）"""
    cursor = conn.cursor()

    # 检查文档是否存在
    cursor.execute("SELECT DocumentId FROM Documents WHERE DocumentId = ? AND IsDeleted = 0", (document_id,))
    if not cursor.fetchone():
        return JSONResponse(status_code=404, content={"message": "文档不存在"})

    try:
        # 软删除 VectorIndex 记录
        cursor.execute("""
            UPDATE v SET IsDeleted = 1
            FROM VectorIndex v
            JOIN TextChunks c ON v.ChunkId = c.ChunkId
            WHERE c.DocumentId = ?
        """, (document_id,))

        # 软删除 TextChunks 记录
        cursor.execute("UPDATE TextChunks SET IsDeleted = 1 WHERE DocumentId = ?", (document_id,))

        # 软删除 Document 记录
        cursor.execute("UPDATE Documents SET IsDeleted = 1 WHERE DocumentId = ?", (document_id,))

        conn.commit()
        logging.info(f"Document {document_id} and its chunks/vectors soft-deleted")
        return {"message": "文档及关联数据已删除"}

    except Exception as e:
        conn.rollback()
        logging.error(f"Error deleting document {document_id}: {e}")
        return JSONResponse(status_code=500, content={"message": f"删除失败: {str(e)}"})


@app.post("/vector/qa")
async def vector_qa(data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    question = data.get("question", "")
    
    if not question:
        return {"answer": "请输入问题", "sources": []}

    try:
        cursor = conn.cursor()
        
        # 检索命中的文档块（基于关键词匹配，后续可替换为向量相似度搜索）
        cursor.execute("""
            SELECT c.ChunkId, c.DocumentId, c.ChunkIndex, c.ChunkText, d.Title
            FROM TextChunks c
            JOIN Documents d ON c.DocumentId = d.DocumentId
            WHERE c.IsDeleted = 0 AND d.IsDeleted = 0
            AND c.ChunkText LIKE ?
            ORDER BY c.DocumentId, c.ChunkIndex
            OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY
        """, (f"%{question}%",))
        
        columns = [column[0] for column in cursor.description]
        sources = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 如果没有命中，用关键词搜索文档标题作为备选
        if not sources:
            cursor.execute("""
                SELECT TOP 3 c.ChunkId, c.DocumentId, c.ChunkIndex, c.ChunkText, d.Title
                FROM Documents d
                JOIN TextChunks c ON d.DocumentId = c.DocumentId
                WHERE d.IsDeleted = 0 AND c.IsDeleted = 0
                AND (d.Title LIKE ? OR d.Source LIKE ?)
                ORDER BY c.DocumentId, c.ChunkIndex
            """, (f"%{question}%", f"%{question}%"))
            columns = [column[0] for column in cursor.description]
            sources = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 使用LLM基于检索到的内容回答问题
        answer = generate_answer_with_sources(question, sources)
        
        return {
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        print(f"Error in vector_qa: {e}")
        import traceback
        traceback.print_exc()
        return {"answer": f"抱歉，处理问题时发生错误: {str(e)}", "sources": []}


def generate_answer_with_sources(question: str, sources: list) -> str:
    """基于检索到的内容使用LLM生成回答"""
    try:
        from openai import OpenAI
        from config import settings
        
        # 配置API
        api_key = settings.llm_api_key
        if not api_key:
            raise Exception("LLM_API_KEY not set in .env file")
        
        masked_key = api_key[:-10] + "**********" if len(api_key) > 10 else "**********"
        logging.info(f"Vector QA - LLM API Key loaded: {masked_key}")
        logging.info(f"Vector QA - LLM Base URL: {settings.llm_base_url}")
        logging.info(f"Vector QA - LLM Model: {settings.llm_model}")
        
        client = OpenAI(
            api_key=api_key,
            base_url=settings.llm_base_url
        )
        
        # 构建上下文
        context_text = ""
        for idx, source in enumerate(sources):
            context_text += f"\n【文档 {idx + 1}】\n"
            context_text += f"标题: {source.get('Title', '无标题')}\n"
            context_text += f"内容: {source.get('ChunkText', '')[:1000]}...\n"
        
        prompt = f"""你是一个智能问答助手。请根据以下文档内容回答用户的问题。

参考文档:
{context_text}

用户问题: {question}

请根据参考文档内容回答问题。如果参考文档中没有相关信息，请如实说明。
请用简洁明了的语言回答。
"""
        
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        logging.info(f"Vector QA - Question: {question}")
        logging.info(f"Vector QA - Answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error in generate_answer_with_sources: {e}")
        
        # 降级方案：基于检索结果的简单回答
        if sources:
            return f"根据检索到的 {len(sources)} 个文档，我为您整理了相关信息。\n\n" + \
                   "\n".join([f"• {s.get('Title', '文档')}: {s.get('Content', '')[:200]}..." 
                             for s in sources])
        else:
            return "抱歉，没有找到相关文档来回答您的问题。"


@app.post("/graph/qa")
async def graph_qa(data: Dict[str, Any], conn=Depends(get_graph_db_connection)):
    question = data.get("question", "")
    use_llm = data.get("use_llm", True)
    
    if not question:
        return {"answer": "请输入问题"}

    try:
        cursor = conn.cursor()
        
        if use_llm:
            # 使用LLM生成SQL
            schema = get_schema_content()
            sql = call_llm_generate_sql(question, schema)

            # 记录LLM交互日志
            log_llm_interaction(question, sql)

            # 执行SQL并获取结果
            result = execute_sql_and_format_result(cursor, sql)
            
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
        result = find_common_entities(cursor)
        return {"answer": result}

    if not node_names:
        return {"answer": "未能识别问题中的实体，请尝试提及具体的人物、案件、地点或组织名称"}

    if "同时" in question or ("认识" in question and "又" in question) or ("和" in question and "有关系" in question):
        if len(node_names) >= 2:
            result = find_common_related_entities(cursor, node_names[0], node_names[1])
            return {"answer": result}
        else:
            return {"answer": "请提供两个实体名称来查询它们之间共同关联的实体"}

    elif "关系" in question or "认识" in question or "联系" in question:
        if len(node_names) >= 2:
            result = find_relationship_between_nodes(cursor, node_names[0], node_names[1])
            return {"answer": result}
        else:
            return {"answer": "请提供两个实体名称来查询它们之间的关系"}

    elif "涉及" in question or "关联" in question or "参与" in question:
        entity = node_names[0]
        result = find_related_entities(cursor, entity)
        return {"answer": result}

    elif "路径" in question or "之间" in question:
        if len(node_names) >= 2:
            result = find_path_between_nodes(cursor, node_names[0], node_names[1])
            return {"answer": result}
        else:
            return {"answer": "请提供两个实体名称来查询它们之间的路径"}

    elif "哪些" in question or "多个" in question:
        result = find_common_entities(cursor)
        return {"answer": result}

    else:
        return {"answer": f"已识别到实体: {', '.join(node_names)}\n\n由于问题较为复杂，建议使用以下方式提问：\n- 'A和B是什么关系？'\n- '某案件涉及哪些人物？'\n- '从A到B之间有哪些关联路径？'\n- '谁认识A，同时又和B有关系？'"}


def find_relationship_between_nodes(cursor, name1, name2):
    """查找两个节点之间的直接关系"""
    try:
        node1_id = get_node_graph_id(cursor, name1)
        node2_id = get_node_graph_id(cursor, name2)

        if not node1_id or not node2_id:
            return f"未能找到实体 '{name1}' 或 '{name2}' 的信息"

        edge_tables = [
            "WorksAt", "SubordinateOf", "Investigates", "SuspectOf",
            "PerpetratorOf", "VictimOf", "LocatedIn", "Owns", "Found",
            "TransferredTo", "Witness", "RelatedTo", "ConflictWith",
            "CooperatesWith", "ReportedBy", "ConnectedTo", "OccursAt",
            "EvidenceOf", "CoversUp", "CommunicatesWith"
        ]

        relationships = []
        for table in edge_tables:
            cursor.execute(f"""
                SELECT * FROM {table}
                WHERE STRING_ESCAPE($from_id, 'json') = STRING_ESCAPE(?, 'json')
                  AND STRING_ESCAPE($to_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node1_id, node2_id))
            if cursor.fetchone():
                relationships.append(f"{name1} ->({table})-> {name2}")

            cursor.execute(f"""
                SELECT * FROM {table}
                WHERE STRING_ESCAPE($from_id, 'json') = STRING_ESCAPE(?, 'json')
                  AND STRING_ESCAPE($to_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node2_id, node1_id))
            if cursor.fetchone():
                relationships.append(f"{name2} ->({table})-> {name1}")

        if relationships:
            return f"{name1} 和 {name2} 之间的关系：\n" + "\n".join(relationships)
        else:
            return f"{name1} 和 {name2} 之间没有直接关系，可能存在间接关联"

    except Exception as e:
        return f"查询关系时出错: {str(e)}"


def find_related_entities(cursor, entity_name):
    """查找与某个实体相关联的所有实体"""
    try:
        node_id = get_node_graph_id(cursor, entity_name)
        if not node_id:
            return f"未能找到实体 '{entity_name}' 的信息"

        edge_tables = [
            "WorksAt", "SubordinateOf", "Investigates", "SuspectOf",
            "PerpetratorOf", "VictimOf", "LocatedIn", "Owns", "Found",
            "TransferredTo", "Witness", "RelatedTo", "ConflictWith",
            "CooperatesWith", "ReportedBy", "ConnectedTo", "OccursAt",
            "EvidenceOf", "CoversUp", "CommunicatesWith"
        ]

        related = {}
        for table in edge_tables:
            cursor.execute(f"""
                SELECT $to_id FROM {table} WHERE STRING_ESCAPE($from_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node_id,))
            for row in cursor.fetchall():
                target_name = get_node_name_from_graph_id(cursor, str(row[0]))
                if target_name:
                    if target_name not in related:
                        related[target_name] = []
                    related[target_name].append(f"({table})")

            cursor.execute(f"""
                SELECT $from_id FROM {table} WHERE STRING_ESCAPE($to_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node_id,))
            for row in cursor.fetchall():
                source_name = get_node_name_from_graph_id(cursor, str(row[0]))
                if source_name:
                    if source_name not in related:
                        related[source_name] = []
                    related[source_name].append(f"({table})")

        if related:
            result = f"与 '{entity_name}' 相关联的实体：\n"
            for name, rels in related.items():
                result += f"- {name}: {', '.join(rels)}\n"
            return result
        else:
            return f"没有找到与 '{entity_name}' 相关联的实体"

    except Exception as e:
        return f"查询关联实体时出错: {str(e)}"


def find_common_related_entities(cursor, name1, name2):
    """查找同时与name1和name2都相关联的实体"""
    try:
        node1_id = get_node_graph_id(cursor, name1)
        node2_id = get_node_graph_id(cursor, name2)

        if not node1_id:
            return f"未能找到实体 '{name1}' 的信息"
        if not node2_id:
            return f"未能找到实体 '{name2}' 的信息"

        edge_tables = [
            "WorksAt", "SubordinateOf", "Investigates", "SuspectOf",
            "PerpetratorOf", "VictimOf", "LocatedIn", "Owns", "Found",
            "TransferredTo", "Witness", "RelatedTo", "ConflictWith",
            "CooperatesWith", "ReportedBy", "ConnectedTo", "OccursAt",
            "EvidenceOf", "CoversUp", "CommunicatesWith"
        ]

        related_to_1 = {}
        for table in edge_tables:
            cursor.execute(f"""
                SELECT $to_id FROM {table} WHERE STRING_ESCAPE($from_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node1_id,))
            for row in cursor.fetchall():
                target_name = get_node_name_from_graph_id(cursor, str(row[0]))
                if target_name and target_name != name1:
                    if target_name not in related_to_1:
                        related_to_1[target_name] = []
                    related_to_1[target_name].append(f"{name1}{table}")

            cursor.execute(f"""
                SELECT $from_id FROM {table} WHERE STRING_ESCAPE($to_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node1_id,))
            for row in cursor.fetchall():
                source_name = get_node_name_from_graph_id(cursor, str(row[0]))
                if source_name and source_name != name1:
                    if source_name not in related_to_1:
                        related_to_1[source_name] = []
                    related_to_1[source_name].append(f"{name1}{table}")

        related_to_2 = {}
        for table in edge_tables:
            cursor.execute(f"""
                SELECT $to_id FROM {table} WHERE STRING_ESCAPE($from_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node2_id,))
            for row in cursor.fetchall():
                target_name = get_node_name_from_graph_id(cursor, str(row[0]))
                if target_name and target_name != name2:
                    if target_name not in related_to_2:
                        related_to_2[target_name] = []
                    related_to_2[target_name].append(f"{name2}{table}")

            cursor.execute(f"""
                SELECT $from_id FROM {table} WHERE STRING_ESCAPE($to_id, 'json') = STRING_ESCAPE(?, 'json')
            """, (node2_id,))
            for row in cursor.fetchall():
                source_name = get_node_name_from_graph_id(cursor, str(row[0]))
                if source_name and source_name != name2:
                    if source_name not in related_to_2:
                        related_to_2[source_name] = []
                    related_to_2[source_name].append(f"{name2}{table}")

        common = set(related_to_1.keys()) & set(related_to_2.keys())

        if common:
            result = f"同时与 '{name1}' 和 '{name2}' 都有关联的实体：\n\n"
            for entity in common:
                rels_1 = related_to_1.get(entity, [])
                rels_2 = related_to_2.get(entity, [])
                result += f"- {entity}:\n"
                result += f"  与{name1}的关系: {', '.join(rels_1)}\n"
                result += f"  与{name2}的关系: {', '.join(rels_2)}\n"
            return result
        else:
            return f"没有找到同时与 '{name1}' 和 '{name2}' 都有关联的实体"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"查询共同关联实体时出错: {str(e)}"


def find_path_between_nodes(cursor, name1, name2):
    """查找两个节点之间的路径"""
    try:
        node1_id = get_node_graph_id(cursor, name1)
        node2_id = get_node_graph_id(cursor, name2)

        if not node1_id or not node2_id:
            return f"未能找到实体 '{name1}' 或 '{name2}' 的信息"

        return f"从 '{name1}' 到 '{name2}' 的路径分析：\n\n由于当前系统限制，路径查询功能需要更复杂的图算法支持。建议使用可视化界面查看节点的关联关系。"

    except Exception as e:
        return f"查询路径时出错: {str(e)}"


def find_common_entities(cursor):
    """查找出现在多个案件中的人物"""
    try:
        cursor.execute("""
            SELECT p.name, COUNT(DISTINCT COALESCE(c1.name, c2.name, c3.name, c4.name, c5.name)) as case_count
            FROM Person p
            LEFT JOIN SuspectOf so ON p.$node_id = so.$from_id
            LEFT JOIN CaseNode c1 ON so.$to_id = c1.$node_id
            LEFT JOIN VictimOf vo ON p.$node_id = vo.$from_id
            LEFT JOIN CaseNode c2 ON vo.$to_id = c2.$node_id
            LEFT JOIN Investigates inv ON p.$node_id = inv.$from_id
            LEFT JOIN CaseNode c3 ON inv.$to_id = c3.$node_id
            LEFT JOIN PerpetratorOf po ON p.$node_id = po.$from_id
            LEFT JOIN CaseNode c4 ON po.$to_id = c4.$node_id
            LEFT JOIN Witness w ON p.$node_id = w.$from_id
            LEFT JOIN CaseNode c5 ON w.$to_id = c5.$node_id
            GROUP BY p.name
            HAVING COUNT(DISTINCT COALESCE(c1.name, c2.name, c3.name, c4.name, c5.name)) > 1
            ORDER BY COUNT(DISTINCT COALESCE(c1.name, c2.name, c3.name, c4.name, c5.name)) DESC
        """)

        results = []
        for row in cursor.fetchall():
            if row[1] > 0:
                results.append(f"{row[0]}: 涉及 {row[1]} 个案件")

        if results:
            return "出现在多个案件中的人物：\n" + "\n".join(results)
        else:
            return "没有找到同时出现在多个案件中的人物"

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)
