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

# Test WorksAt table
print("=== WorksAt edge table ===")
cursor.execute("SELECT TOP 3 * FROM WorksAt")
columns = [column[0] for column in cursor.description]
print(f"Columns: {columns}")
for row in cursor.fetchall():
    print("\nRow:")
    for i, val in enumerate(row):
        print(f"  {columns[i]}: {val} (type: {type(val)})")

# Also test a Person
print("\n=== Person node table ===")
cursor.execute("SELECT TOP 2 * FROM Person")
columns = [column[0] for column in cursor.description]
for row in cursor.fetchall():
    print("\nRow:")
    for i, val in enumerate(row):
        print(f"  {columns[i]}: {val} (type: {type(val)})")

conn.close()
