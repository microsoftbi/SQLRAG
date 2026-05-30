"""
向 VectorIndexTEST 表插入向量记录的测试脚本
用法: python insert_vector_test.py
"""

import urllib.request
import json
import pyodbc
import os

# ====== 配置（从 .env 读取或直接写死测试）======
SERVER = os.getenv("SERVER", "LOCALHOST")
PORT = os.getenv("PORT", "1433")
DATABASE = "VectorDB"
USER = os.getenv("USER", "sa")
PASSWORD = os.getenv("PASSWORD", "Passw0rd")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# ====== 1. 数据库连接 ======
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER},{PORT};"
    f"DATABASE={DATABASE};"
    f"UID={USER};"
    f"PWD={PASSWORD};"
    f"TrustServerCertificate=yes;"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
print(f"✅ 连接数据库 {DATABASE} 成功")

# ====== 2. 获取一条 Chunk 文本 ======
cursor.execute("SELECT TOP 1 ChunkId, ChunkText FROM TextChunks WHERE IsDeleted = 0")
row = cursor.fetchone()
if not row:
    print("❌ TextChunks 表中没有数据")
    exit(1)

chunk_id, chunk_text = row
print(f"✅ 获取 Chunk: ChunkId={chunk_id}, 文本长度={len(chunk_text)}")

# ====== 3. 调用 Ollama 生成向量 ======
payload = json.dumps({
    "model": EMBEDDING_MODEL,
    "prompt": chunk_text,
}).encode()

req = urllib.request.Request(
    f"{OLLAMA_URL}/api/embeddings",
    data=payload,
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read())

vector = data.get("embedding", [])
print(f"✅ 生成向量: 维度={len(vector)}, 前3个值={vector[:3]}")

# ====== 4. 删除已有 VECTOR INDEX ======
drop_sql = """
    IF EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = N'idx_content_vector2'
          AND object_id = OBJECT_ID(N'dbo.VectorIndexTEST')
    )
    DROP INDEX [idx_content_vector2] ON [dbo].[VectorIndexTEST];
"""
print(f"🗑️ 删除 VECTOR INDEX:\n   {drop_sql}")
cursor.execute(drop_sql)
print("✅ VECTOR INDEX 已删除")

# ====== 5. 插入 VectorIndexTEST 表 ======
vector_json = json.dumps(vector)
insert_sql = """
    DECLARE @json_str NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), ?);
    DECLARE @v VECTOR(768) = CAST(@json_str AS VECTOR(768));
    INSERT INTO VectorIndexTEST (ChunkId, EmbeddingVector, CreatedAt)
    VALUES (?, @v, GETDATE());
"""
print(f"📝 执行 INSERT SQL:\n   {insert_sql.strip()}")
cursor.execute(insert_sql, (vector_json, chunk_id))
conn.commit()

print(f"✅ 插入 VectorIndexTEST 成功 (ChunkId={chunk_id})")

# ====== 6. 重新创建 VECTOR INDEX（需独立的 autocommit 连接） ======
create_sql = """
    CREATE VECTOR INDEX idx_content_vector2
    ON dbo.VectorIndexTEST(EmbeddingVector)
    WITH (METRIC = 'cosine');
"""
print(f"🔄 重新创建 VECTOR INDEX:\n   {create_sql.strip()}")
rebuild_conn = pyodbc.connect(conn_str, autocommit=True)
rebuild_cursor = rebuild_conn.cursor()
rebuild_cursor.execute(create_sql)
rebuild_conn.close()
print("✅ VECTOR INDEX 已重新创建")

# ====== 7. 验证 ======
cursor.execute("SELECT TOP 5 * FROM VectorIndexTEST ORDER BY VectorId DESC")
columns = [column[0] for column in cursor.description]
rows = cursor.fetchall()
for r in rows:
    record = dict(zip(columns, r))
    print(f"   VectorId={record.get('VectorId')}, ChunkId={record.get('ChunkId')}, CreatedAt={record.get('CreatedAt')}")

conn.close()
print("✅ 完成")
