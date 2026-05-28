import pyodbc
import json
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

print("=== Checking Location nodes ===")
cursor.execute("SELECT * FROM Location")
columns = [column[0] for column in cursor.description]
for row in cursor.fetchall():
    node = dict(zip(columns, row))
    print(f"\n{node.get('name')}:")
    for key in node.keys():
        if key.startswith("$node_id"):
            print(f"  {key}: {node[key]}")
            try:
                data = json.loads(node[key])
                print(f"  Parsed: table={data['table']}, id={data['id']}")
            except:
                pass

print("\n=== Checking some edges ===")
edge_tables = ["LocatedIn", "WorksAt", "RelatedTo"]
for table in edge_tables:
    print(f"\n--- {table} ---")
    try:
        cursor.execute(f"SELECT TOP 2 * FROM {table}")
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            edge = dict(zip(columns, row))
            print(f"\nEdge:")
            for key in edge.keys():
                if key.startswith("$from_id") or key.startswith("$to_id"):
                    print(f"  {key}: {edge[key]}")
                    try:
                        data = json.loads(edge[key])
                        print(f"  Parsed: table={data['table']}, id={data['id']}")
                    except:
                        pass
    except Exception as e:
        print(f"Error: {e}")

conn.close()
