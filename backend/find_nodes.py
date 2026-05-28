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

result = {}

cursor.execute(f"SELECT * FROM Person")
columns = [column[0] for column in cursor.description]
for row in cursor.fetchall():
    node = dict(zip(columns, row))
    name = node.get('name', '')
    if name:
        graph_id = None
        for key in node.keys():
            if key.startswith("$node_id"):
                try:
                    data = json.loads(node[key])
                    graph_id = int(data.get("id"))
                except:
                    pass
        result[name] = {'graph_id': graph_id, 'id': node.get('id')}

for name, info in result.items():
    print(f"{name}: graph_id={info['graph_id']}, id={info['id']}")

conn.close()
