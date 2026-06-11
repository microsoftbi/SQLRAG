import os
import json
import pyodbc
import ollama
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def search_similar_text(query_text: str, top_n: int = 5):
    """
    将 query_text 向量化，然后在 VectorDB 中用 VECTOR_SEARCH 检索相似内容

    参数:
        query_text: 搜索文本
        top_n: 返回前 N 条最相似的结果

    返回:
        list[dict]: 搜索结果列表，每项包含 ChunkId, ChunkText, Title, DocumentId, ChunkIndex
    """
    # 1. 嵌入
    model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    client = ollama.Client(host=ollama_url)
    resp = client.embeddings(model=model, prompt=query_text)
    vec = resp.get("embedding", [])
    print(f"嵌入维度: {len(vec)}")
    if not vec:
        raise Exception("嵌入返回为空")

    vec_json = json.dumps(vec)

    # 2. 连接数据库
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('SERVER','LOCALHOST')},{os.getenv('PORT','1433')};"
        f"DATABASE={os.getenv('DATABASE_VECTOR','VectorDB')};"
        f"UID={os.getenv('USER','sa')};PWD={os.getenv('PASSWORD','Passw0rd')};"
        f"TrustServerCertificate=yes;"
    )
    cursor = conn.cursor()

    # 3. VECTOR_SEARCH
    sql = """
        DECLARE @json_str NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), ?);
        DECLARE @v VECTOR(1024) = CAST(@json_str AS VECTOR(1024));

        SELECT c.ChunkId, c.DocumentId, c.ChunkIndex, c.ChunkText, d.Title
        FROM VECTOR_SEARCH(
            TABLE = VectorIndex AS v,
            COLUMN = EmbeddingVector,
            SIMILAR_TO = @v,
            METRIC = 'cosine',
            TOP_N = ?
        )
        JOIN TextChunks c ON v.ChunkId = c.ChunkId
        JOIN Documents d ON c.DocumentId = d.DocumentId
        WHERE ISNULL(c.IsDeleted, 0) = 0 AND d.IsDeleted = 0
    """
    print(f"\n执行 SQL:\n{sql}\n")
    # 截取前 200 个元素打印，太长会刷屏
    preview = vec_json[:500]
    print(f"向量 JSON (前500字符): {preview}...\n")

    cursor.execute(sql, (vec_json, top_n))

    columns = [col[0] for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    conn.close()
    return results


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "母猪"
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"搜索: \"{query}\"  top_n={top_n}")
    print("=" * 60)

    results = search_similar_text(query, top_n)

    if not results:
        print("未找到结果")
    else:
        for i, r in enumerate(results, 1):
            print(f"\n--- 结果 {i} ---")
            print(f"  ChunkId:   {r['ChunkId']}")
            print(f"  DocumentId: {r['DocumentId']}")
            print(f"  Title:     {r['Title']}")
            print(f"  ChunkText: {r['ChunkText'][:200]}...")