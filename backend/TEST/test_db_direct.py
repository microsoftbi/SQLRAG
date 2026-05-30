import sys, os
sys.stdout.reconfigure(encoding='utf-8')

import pyodbc

try:
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=LOCALHOST,1433;DATABASE=VectorDB;UID=sa;PWD=Passw0rd;TrustServerCertificate=yes'
    print(f'Connecting to VectorDB...')
    conn = pyodbc.connect(conn_str, timeout=10)
    print('Connected OK')

    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT COUNT(*) FROM Documents")
    doc_count = cursor.fetchone()[0]
    print(f'Documents count: {doc_count}')

    cursor.execute("SELECT COUNT(*) FROM TextChunks")
    chunk_count = cursor.fetchone()[0]
    print(f'TextChunks count: {chunk_count}')

    # Test INSERT
    cursor.execute(
        "INSERT INTO Documents (Title, Content, Source, Metadata) VALUES (?, ?, ?, ?)",
        ('test_direct_insert.txt', 'This is a direct test insert.', 'test', '{}')
    )
    conn.commit()
    print('INSERT OK')

    # Get ID
    cursor.execute("SELECT IDENT_CURRENT('Documents')")
    row = cursor.fetchone()
    doc_id = int(row[0]) if row and row[0] is not None else None
    print(f'New Document ID: {doc_id}')

    conn.close()
    print('All DB tests passed!')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
