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

# Find nodes
nodes = {}
cursor.execute(f"SELECT * FROM Person")
columns = [column[0] for column in cursor.description]
for row in cursor.fetchall():
    node = dict(zip(columns, row))
    name = node.get('name', '')
    if name:
        graph_id = None
        node_id_field = None
        for key in node.keys():
            if key.startswith("$node_id"):
                try:
                    data = json.loads(node[key])
                    graph_id = int(data.get("id"))
                    node_id_field = key
                except:
                    pass
        nodes[name] = {'graph_id': graph_id, 'graph_id_str': node.get(node_id_field, '')}

# Find Location node
location_graph_id = None
location_id_field = None
location_graph_id_str = None
cursor.execute(f"SELECT * FROM Location")
columns = [column[0] for column in cursor.description]
for row in cursor.fetchall():
    node = dict(zip(columns, row))
    name = node.get('name', '')
    if name:
        for key in node.keys():
            if key.startswith("$node_id"):
                try:
                    data = json.loads(node[key])
                    loc_graph_id = int(data.get("id"))
                    if loc_graph_id == 12:  # We know this is the one
                        location_graph_id = loc_graph_id
                        location_id_field = key
                        location_graph_id_str = node.get(key, '')
                except:
                    pass

# Now create SQL
sql = """
-- Add edges for Highway Service Area
"""

# Add LocatedIn edges
target_names = ['林凯', '方超', '刘直', '方庸']
descriptions = [
    '林凯的车停留在高速服务区',
    '方超在高速附近活动',
    '刘直在高速附近活动',
    '方庸想去高速服务区找林凯'
]

for name, desc in zip(target_names, descriptions):
    if name in nodes and nodes[name]['graph_id'] is not None and location_graph_id is not None:
        sql += f"""
INSERT INTO LocatedIn ($from_id, $to_id, description)
VALUES ('{nodes[name]['graph_id_str']}', '{location_graph_id_str}', N'{desc}');
"""

# Write SQL to file
with open('c:\\Users\\TEMP\\Desktop\\SQLRAG\\add_edges.sql', 'w', encoding='utf-8') as f:
    f.write(sql)

print("SQL script created: add_edges.sql")
conn.close()
