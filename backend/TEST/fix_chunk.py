
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''def create_chunks_from_content(document_id: int, content: str, conn) -> List[Dict]:
    """从文档内容创建分块"""
    if not content:
        return []
    
    # 简单分块：每 500 字符一块，带重叠
    chunk_size = 500
    overlap = 100
    chunks = []
    
    idx = 0
    i = 0
    while idx < len(content):
        end_idx = min(idx + chunk_size, len(content))
        chunk_text = content[idx:end_idx]
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO TextChunks (DocumentId, ChunkIndex, ChunkText, CreatedAt) VALUES (?, ?, ?, GETDATE()); SELECT IDENT_CURRENT('TextChunks') AS ChunkId;",
            (document_id, i, chunk_text)
        )
        
        # 获取新插入的 Chunk ID
        row = cursor.fetchone()
        chunk_id = int(row[0]) if row and row[0] is not None else None
        
        conn.commit()
        
        chunks.append({
            "ChunkId": chunk_id,
            "DocumentId": document_id,
            "ChunkIndex": i,
            "ChunkText": chunk_text,
            "CreatedAt": None
        })
        
        i += 1
        idx = end_idx - overlap
    
    logging.info(f"Created {len(chunks)} chunks for document {document_id}")
    return chunks'''

new_code = '''def create_chunks_from_content(document_id: int, content: str, conn) -> List[Dict]:
    """从文档内容创建分块"""
    if not content:
        return []
    
    # 简单分块：每 500 字符一块，带重叠
    chunk_size = 500
    overlap = 100
    chunks = []
    
    idx = 0
    i = 0
    while idx < len(content):
        end_idx = min(idx + chunk_size, len(content))
        chunk_text = content[idx:end_idx]
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO TextChunks (DocumentId, ChunkIndex, ChunkText, CreatedAt) VALUES (?, ?, ?, GETDATE())",
            (document_id, i, chunk_text)
        )
        conn.commit()
        
        # 使用单独的查询获取刚插入的 Chunk ID
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
        
        i += 1
        idx = end_idx - overlap
    
    logging.info(f"Created {len(chunks)} chunks for document {document_id}")
    return chunks'''

new_content = content.replace(old_code, new_code)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('File updated successfully')
