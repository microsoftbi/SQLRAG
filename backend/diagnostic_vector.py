"""
向量检索诊断脚本
在 backend 目录下运行: python diagnostic_vector.py
"""

import sys
import os
import json

# 加载 .env
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

import pyodbc
import ollama

def main():
    # 1. 检查 Ollama 嵌入
    print("=== 1. 检查嵌入模型 ===")
    model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    print(f"模型: {model}")

    client = ollama.Client(host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip('/'))
    query_vec = client.embeddings(model=model, prompt="母猪")
    qv = query_vec.get("embedding", [])
    print(f"查询向量维度: {len(qv)}")

    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('SERVER','LOCALHOST')},{os.getenv('PORT','1433')};"
        f"DATABASE={os.getenv('DATABASE_VECTOR','VectorDB')};"
        f"UID={os.getenv('USER','sa')};PWD={os.getenv('PASSWORD','Passw0rd')};"
        f"TrustServerCertificate=yes;"
    )
    cursor = conn.cursor()

    # 2. 检查 VectorIndex 记录
    print("\n=== 2. VectorIndex 前10条记录 ===")
    cursor.execute("SELECT VectorId, ChunkId, IsDeleted FROM VectorIndex ORDER BY VectorId")
    for row in cursor.fetchmany(10):
        print(f"  VectorId={row[0]}, ChunkId={row[1]}, IsDeleted={row[2]}")

    # 3. 检查 VECTOR INDEX
    print("\n=== 3. VECTOR INDEX 状态 ===")
    cursor.execute("""
        SELECT name, type_desc FROM sys.indexes
        WHERE object_id = OBJECT_ID('VectorIndex') AND type = 11
    """)
    idx = cursor.fetchone()
    if idx:
        print(f"  VECTOR INDEX 存在: {idx[0]} ({idx[1]})")
    else:
        print("  VECTOR INDEX 不存在！")

    # 4. 直接测试 VECTOR_SEARCH
    print("\n=== 4. 测试 VECTOR_SEARCH ===")
    qv_json = json.dumps(qv)
    try:
        cursor.execute("""
            DECLARE @json_str NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), ?);
            DECLARE @v VECTOR(1024) = CAST(@json_str AS VECTOR(1024));
            SELECT COUNT(*) AS cnt
            FROM VECTOR_SEARCH(
                TABLE = VectorIndex AS v,
                COLUMN = EmbeddingVector,
                SIMILAR_TO = @v,
                METRIC = 'cosine',
                TOP_N = 5
            )
        """, (qv_json,))
        cnt = cursor.fetchone()[0]
        print(f"  VECTOR_SEARCH 返回: {cnt} 条")
        if cnt == 0:
            # 什么都不返回？检查拿原始数据
            cursor.execute("SELECT COUNT(*) FROM VectorIndex WHERE IsDeleted = 0")
            total = cursor.fetchone()[0]
            print(f"  但 VectorIndex 中有 {total} 条活跃数据")
    except Exception as e:
        print(f"  VECTOR_SEARCH 错误: {e}")

    # 5. 检查 TextChunks JOIN
    print("\n=== 5. TextChunks JOIN 检查 ===")
    cursor.execute("""
        SELECT v.VectorId, v.IsDeleted AS VI_Del,
               c.ChunkId, c.IsDeleted AS TC_Del,
               d.DocumentId, d.Title, d.IsDeleted AS Doc_Del
        FROM VectorIndex v
        LEFT JOIN TextChunks c ON v.ChunkId = c.ChunkId
        LEFT JOIN Documents d ON c.DocumentId = d.DocumentId
    """)
    for row in cursor.fetchall():
        print(f"  VectorId={row[0]}, VI_Del={row[1]}, "
              f"ChunkId={row[2]}, TC_Del={row[3]}, "
              f"Doc={row[4]}, Title={row[5]}, Doc_Del={row[6]}")

    conn.close()


if __name__ == "__main__":
    main()