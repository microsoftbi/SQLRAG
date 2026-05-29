import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: upload_document - reorder fetch/commit
# The file has a blank line with 8 spaces before the comment
old1 = '        \n        # 获取新插入的文档ID\n        row = cursor.fetchone()\n        document_id = int(row[0]) if row and row[0] is not None else None\n        \n        conn.commit()'

new1 = '        conn.commit()\n\n        # 使用单独的查询获取刚插入的文档ID\n        cursor.execute("SELECT IDENT_CURRENT(\'Documents\')")\n        row = cursor.fetchone()\n        document_id = int(row[0]) if row and row[0] is not None else None'

if old1 in content:
    content = content.replace(old1, new1)
    print('Fix 1 applied')
else:
    print('Fix 1: NOT FOUND')
    idx = content.find('获取新插入的文档ID')
    if idx >= 0:
        start = max(0, idx-15)
        end = min(len(content), idx+130)
        snippet = content[start:end]
        print(f'  Context bytes: {snippet.encode("utf-8")}')

# Fix 2: create_chunks_from_content - same pattern
old2 = '        # 获取新插入的Chunk ID\n        row = cursor.fetchone()\n        chunk_id = int(row[0]) if row and row[0] is not None else None\n        \n        conn.commit()'

new2 = '        conn.commit()\n\n        # 获取新插入的Chunk ID\n        cursor.execute("SELECT IDENT_CURRENT(\'TextChunks\')")\n        row = cursor.fetchone()\n        chunk_id = int(row[0]) if row and row[0] is not None else None'

if old2 in content:
    content = content.replace(old2, new2)
    print('Fix 2 applied')
else:
    print('Fix 2: NOT FOUND')
    idx = content.find('Chunk ID')
    if idx >= 0:
        start = max(0, idx-10)
        end = min(len(content), idx+130)
        snippet = content[start:end]
        print(f'  Context: {repr(snippet)}')

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
