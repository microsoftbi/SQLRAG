import pyodbc
from config import settings

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={settings.server},{settings.port};"
    f"DATABASE={settings.database_graph};"
    f"UID={settings.user};"
    f"PWD={settings.password};"
    f"TrustServerCertificate=yes;"
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

with open('c:\\Users\\TEMP\\Desktop\\SQLRAG\\add_edges.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# Split and execute each statement
statements = [s.strip() for s in sql.split(';') if s.strip()]
count = 0
for stmt in statements:
    if stmt.startswith('INSERT'):
        cursor.execute(stmt)
        count += 1

conn.commit()
print(f"Executed {count} INSERT statements")

conn.close()
