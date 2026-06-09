from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import JSONResponse
import pyodbc
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import settings
from database import get_vector_db_connection

router = APIRouter(prefix="/vector", tags=["VectorDB"])


@router.get("/documents")
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


@router.post("/documents")
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


@router.put("/documents/{document_id}")
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


@router.get("/documents/{document_id}")
async def get_document(document_id: int, conn=Depends(get_vector_db_connection)):
    """获取单个文档的详细信息"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Documents WHERE DocumentId = ? AND IsDeleted = 0", (document_id,))
    row = cursor.fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"message": "文档不存在"})
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


@router.get("/documents/{document_id}/chunks")
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
            "INSERT INTO TextChunks (DocumentId, ChunkIndex, ChunkText, CreatedAt, IsDeleted) VALUES (?, ?, ?, GETDATE(), 0)",
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
    """使用 Ollama Python 客户端获取文本的嵌入向量"""
    if not text or not text.strip():
        raise Exception("不能为空文本生成嵌入向量")

    try:
        import math
        import ollama

        client = ollama.Client(host=settings.ollama_base_url.rstrip('/'))

        def request_embedding(input_text: str) -> List[float]:
            response = client.embeddings(
                model=settings.embedding_model,
                prompt=input_text,
            )
            vector = response.get("embedding", [])
            if not vector:
                raise Exception("Ollama 返回了空的嵌入向量")

            # 修复部分模型偶发的 NaN 值问题
            if any(isinstance(v, float) and math.isnan(v) for v in vector):
                nan_count = sum(1 for v in vector if isinstance(v, float) and math.isnan(v))
                logging.warning(f"Embedding 中包含 {nan_count} 个 NaN 值，已替换为 0.0")
                vector = [0.0 if (isinstance(v, float) and math.isnan(v)) else v for v in vector]

            return vector

        retry_lengths = [None, 1200, 800, 500, 300, 150]
        last_error = None
        tried_lengths = set()

        for max_chars in retry_lengths:
            input_text = text if max_chars is None else text[:max_chars]
            if len(input_text) in tried_lengths:
                continue
            tried_lengths.add(len(input_text))

            try:
                if max_chars is not None:
                    logging.warning(
                        f"Embedding input too long, retrying with first {len(input_text)} chars"
                    )
                return request_embedding(input_text)
            except Exception as e:
                error_message = str(e)
                last_error = e
                if "input length exceeds the context length" not in error_message:
                    raise
                logging.warning(
                    f"Embedding input length {len(input_text)} chars still exceeds context length"
                )

        raise last_error

    except ImportError:
        raise Exception("ollama library not installed, please install: pip install ollama")
    except Exception as e:
        error_message = str(e)
        if "connection" in error_message.lower() or "connect" in error_message.lower():
            logging.error(f"Cannot connect to Ollama at {settings.ollama_base_url}: {e}")
            raise Exception(f"无法连接到 Ollama，请确保 Ollama 已启动（{settings.ollama_base_url}）")
        logging.error(f"Embedding error: {e}")
        raise


def embed_chunks_for_document(document_id: int, conn) -> Dict:
    """为指定文档的所有未嵌入分块生成向量并存入 VectorIndex"""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS total_chunks,
            SUM(CASE WHEN ISNULL(IsDeleted, 0) = 0 THEN 1 ELSE 0 END) AS active_chunks
        FROM TextChunks
        WHERE DocumentId = ?
    """, (document_id,))
    chunk_stats = cursor.fetchone()

    cursor.execute("""
        SELECT
            COUNT(*) AS vector_count,
            SUM(CASE WHEN v.IsDeleted = 0 THEN 1 ELSE 0 END) AS active_vector_count
        FROM VectorIndex v
        JOIN TextChunks c ON v.ChunkId = c.ChunkId
        WHERE c.DocumentId = ?
    """, (document_id,))
    vector_stats = cursor.fetchone()

    logging.info(
        f"Embedding document {document_id}: TextChunks total={chunk_stats[0]}, active={chunk_stats[1]}, "
        f"VectorIndex total={vector_stats[0]}, active={vector_stats[1]}"
    )

    # 查询还没有嵌入向量的分块
    cursor.execute("""
        SELECT c.ChunkId, c.ChunkText
        FROM TextChunks c
        LEFT JOIN VectorIndex v ON c.ChunkId = v.ChunkId AND v.IsDeleted = 0
        WHERE c.DocumentId = ? AND ISNULL(c.IsDeleted, 0) = 0 AND v.ChunkId IS NULL
        ORDER BY c.ChunkIndex
    """, (document_id,))
    rows = cursor.fetchall()

    logging.info(f"Embedding document {document_id}: found {len(rows)} chunks without vectors")

    if not rows:
        return {"message": "所有分块已嵌入，无需重复处理", "embedded": 0}

    embedded_count = 0
    failed_errors = []
    for chunk_id, chunk_text in rows:
        if not chunk_text or not chunk_text.strip():
            logging.warning(f"Skipping empty chunk {chunk_id}")
            continue
        try:
            vector = get_embedding(chunk_text)
            vector_json = json.dumps(vector)
            cursor.execute("""
                DECLARE @json_str NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), ?);
                DECLARE @v VECTOR(1024) = CAST(@json_str AS VECTOR(1024));

                IF EXISTS (SELECT 1 FROM VectorIndex WHERE ChunkId = ?)
                BEGIN
                    UPDATE VectorIndex
                    SET EmbeddingVector = @v,
                        CreatedAt = GETDATE(),
                        IsDeleted = 0
                    WHERE ChunkId = ?;
                END
                ELSE
                BEGIN
                    INSERT INTO VectorIndex (ChunkId, EmbeddingVector, CreatedAt, IsDeleted)
                    VALUES (?, @v, GETDATE(), 0);
                END
            """, (vector_json, chunk_id, chunk_id, chunk_id))
            conn.commit()
            embedded_count += 1
            logging.info(f"Embedded chunk {chunk_id} for document {document_id}")
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Failed to embed chunk {chunk_id}: {error_msg}")
            failed_errors.append(f"Chunk {chunk_id}: {error_msg}")
            conn.rollback()
            continue

    logging.info(f"Embedded {embedded_count} chunks for document {document_id}")
    if embedded_count == 0 and failed_errors:
        first_error = failed_errors[0]
        if "vector index" in first_error.lower():
            raise Exception("向量索引存在时不能写入 VectorIndex。请先在 VectorDB -> 索引管理 中点击 DROP INDEX，再执行文档入库。")
        raise Exception(f"所有分块嵌入失败，首个错误: {first_error}")
    return {"message": f"成功嵌入 {embedded_count} 个分块", "embedded": embedded_count, "failed": len(failed_errors)}


@router.post("/documents/{document_id}/embed")
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


@router.post("/documents/upload")
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


@router.post("/documents/{document_id}/preview-chunks")
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


@router.post("/documents/{document_id}/semantic-chunk")
async def semantic_chunk_document(document_id: int, conn=Depends(get_vector_db_connection)):
    """调用大模型对文档进行语义分块"""
    cursor = conn.cursor()
    cursor.execute("SELECT Content FROM Documents WHERE DocumentId = ? AND IsDeleted = 0", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        return JSONResponse(status_code=404, content={"message": "文档不存在"})

    content = doc[0]
    if not content:
        return JSONResponse(status_code=400, content={"message": "文档内容为空"})

    if not settings.llm_api_key:
        return JSONResponse(status_code=400, content={"message": "未配置 LLM API Key，请在 .env 中设置 LLM_API_KEY"})

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url
        )

        prompt = f"""你是一个文本分段专家。请将以下文章按照语义进行合理的分段。

要求：
1. 根据文章的自然段落和语义完整性进行分段
2. 每个分段应该是一个完整的语义单元
3. 保持原文内容不变，不要修改、删除或添加任何文字
4. 返回一个 JSON 数组，每个元素是一个分段的文本

输出格式（仅返回 JSON，不要其他任何内容）：
{{"chunks": ["第一段内容...", "第二段内容...", ...]}}

文章内容：
{content}"""

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "你是一个文本分段专家，擅长将长文本按语义分割成合理的段落。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=8192,
        )

        result_text = response.choices[0].message.content

        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', result_text)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                raise

        chunks = result.get("chunks", [])
        chunked_result = [
            {"ChunkIndex": i, "ChunkText": t, "Length": len(t)}
            for i, t in enumerate(chunks)
        ]

        logging.info(f"Semantic chunked document {document_id}: {len(chunks)} chunks")

        return {
            "original_content": content,
            "chunks": chunked_result,
            "total_chunks": len(chunks),
        }

    except ImportError:
        return JSONResponse(status_code=500, content={"message": "openai library not installed, please install: pip install openai"})
    except Exception as e:
        logging.error(f"Error semantic chunking document {document_id}: {e}")
        return JSONResponse(status_code=500, content={"message": f"语义分块失败: {str(e)}"})


@router.post("/documents/{document_id}/commit-chunks")
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
        logging.error(f"Embedding failed during commit: {e}")
        return JSONResponse(status_code=500, content={"message": f"分块已创建，但向量嵌入失败: {str(e)}"})

    return {
        "message": f"已创建 {len(chunks)} 个分块，已嵌入 {embedded} 个向量",
        "total_chunks": len(chunks),
        "embedded": embedded,
        "failed": embed_result.get("failed", 0),
    }


@router.post("/documents/{document_id}/commit-chunks-raw")
async def commit_document_chunks_raw(document_id: int, data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    """将指定的分块列表直接入库（用于语义分块结果），并生成向量嵌入"""
    cursor = conn.cursor()
    cursor.execute("SELECT DocumentId FROM Documents WHERE DocumentId = ? AND IsDeleted = 0", (document_id,))
    if not cursor.fetchone():
        return JSONResponse(status_code=404, content={"message": "文档不存在"})

    chunks_text = data.get("chunks", [])
    if not chunks_text:
        return JSONResponse(status_code=400, content={"message": "分块列表为空"})

    # 先删除已存在的分块和向量
    cursor.execute("""
        UPDATE v SET IsDeleted = 1
        FROM VectorIndex v JOIN TextChunks c ON v.ChunkId = c.ChunkId
        WHERE c.DocumentId = ?
    """, (document_id,))
    cursor.execute("UPDATE TextChunks SET IsDeleted = 1 WHERE DocumentId = ?", (document_id,))
    conn.commit()

    # 入库分块
    for i, chunk_text in enumerate(chunks_text):
        cursor.execute(
            "INSERT INTO TextChunks (DocumentId, ChunkIndex, ChunkText, CreatedAt, IsDeleted) VALUES (?, ?, ?, GETDATE(), 0)",
            (document_id, i, chunk_text)
        )
        conn.commit()

    # 生成向量嵌入
    try:
        embed_result = embed_chunks_for_document(document_id, conn)
        embedded = embed_result.get("embedded", 0)
    except Exception as e:
        logging.error(f"Embedding failed during raw commit: {e}")
        return JSONResponse(status_code=500, content={"message": f"分块已入库，但向量嵌入失败: {str(e)}"})

    return {
        "message": f"已入库 {len(chunks_text)} 个分块，已嵌入 {embedded} 个向量",
        "total_chunks": len(chunks_text),
        "embedded": embedded,
        "failed": embed_result.get("failed", 0),
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


@router.get("/config")
async def get_config():
    """获取当前配置"""
    return {
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "embedding_model": settings.embedding_model,
        "ollama_base_url": settings.ollama_base_url,
    }


@router.put("/config")
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


@router.get("/knowledge-bases")
async def get_knowledge_bases(conn=Depends(get_vector_db_connection)):
    """获取所有知识库"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM KnowledgeBases WHERE IsDeleted = 0 ORDER BY CreatedAt DESC")
    columns = [column[0] for column in cursor.description]
    kbs = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"knowledge_bases": kbs}


@router.post("/knowledge-bases")
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


@router.put("/knowledge-bases/{kb_id}")
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


@router.delete("/knowledge-bases/{kb_id}")
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


@router.get("/chunks")
async def get_chunks(conn=Depends(get_vector_db_connection)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TextChunks WHERE IsDeleted = 0")
    columns = [column[0] for column in cursor.description]
    chunks = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"chunks": chunks}


@router.delete("/documents/{document_id}")
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


@router.post("/index/create")
async def create_vector_index():
    """创建 VECTOR INDEX"""
    try:
        from config import get_db_connection_string
        # VECTOR INDEX 必须在 autocommit 连接中执行
        rebuild_conn = pyodbc.connect(get_db_connection_string("VectorDB"), autocommit=True)
        rebuild_cursor = rebuild_conn.cursor()
        rebuild_cursor.execute("""
            CREATE VECTOR INDEX idx_content_vector
            ON dbo.VectorIndex(EmbeddingVector)
            WITH (METRIC = 'cosine');
        """)
        rebuild_conn.close()
        logging.info("Vector index created successfully")
        return {"message": "向量索引创建成功"}
    except Exception as e:
        logging.error(f"Error creating vector index: {e}")
        return JSONResponse(status_code=500, content={"message": f"向量索引创建失败: {str(e)}"})


@router.post("/index/drop")
async def drop_vector_index(conn=Depends(get_vector_db_connection)):
    """删除 VECTOR INDEX"""
    try:
        cursor = conn.cursor()
        cursor.execute("DROP INDEX IF EXISTS idx_content_vector ON VectorIndex")
        conn.commit()
        logging.info("Vector index dropped successfully")
        return {"message": "向量索引已删除"}
    except Exception as e:
        logging.error(f"Error dropping vector index: {e}")
        return JSONResponse(status_code=500, content={"message": f"删除向量索引失败: {str(e)}"})


@router.post("/qa")
async def vector_qa(data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    question = data.get("question", "")

    if not question:
        return {"answer": "请输入问题", "sources": []}

    try:
        cursor = conn.cursor()

        # 生成问题的嵌入向量
        query_vector = get_embedding(question)
        query_vector_json = json.dumps(query_vector)

        # 使用 SQL Server 2025 VECTOR_SEARCH 进行向量相似度检索
        cursor.execute("""
            DECLARE @json_str NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), ?);
            DECLARE @v VECTOR(1024) = CAST(@json_str AS VECTOR(1024));

            SELECT c.ChunkId, c.DocumentId, c.ChunkIndex, c.ChunkText, d.Title
            FROM VECTOR_SEARCH(
                TABLE = VectorIndex AS v,
                COLUMN = EmbeddingVector,
                SIMILAR_TO = @v,
                METRIC = 'cosine',
                TOP_N = 5
            )
            JOIN TextChunks c ON v.ChunkId = c.ChunkId
            JOIN Documents d ON c.DocumentId = d.DocumentId
            WHERE ISNULL(c.IsDeleted, 0) = 0 AND d.IsDeleted = 0
        """, (query_vector_json,))

        columns = [column[0] for column in cursor.description]
        sources = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # 如果向量检索没有命中，用关键词搜索文档标题作为备选
        if not sources:
            cursor.execute("""
                SELECT TOP 3 c.ChunkId, c.DocumentId, c.ChunkIndex, c.ChunkText, d.Title
                FROM Documents d
                JOIN TextChunks c ON d.DocumentId = c.DocumentId
                WHERE d.IsDeleted = 0 AND ISNULL(c.IsDeleted, 0) = 0
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
