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

# Collect all nodes
all_nodes = {}
node_types = ['Person', 'CaseNode', 'Organization', 'Location', 'Item', 'Event']
for node_type in node_types:
    cursor.execute(f"SELECT * FROM {node_type}")
    columns = [column[0] for column in cursor.description]
    for row in cursor.fetchall():
        node = dict(zip(columns, row))
        graph_id = None
        for key in node.keys():
            if key.startswith("$node_id"):
                try:
                    data = json.loads(node[key])
                    graph_id = (data.get("table"), int(data.get("id")))
                except:
                    pass
        if graph_id:
            name = node.get('name', node.get('title', str(node.get('id'))))
            all_nodes[graph_id] = {'type': node_type, 'name': name, 'data': node}

# Collect all edges and find connected nodes
connected_nodes = set()
edge_tables = ['WorksAt', 'SubordinateOf', 'Investigates', 'SuspectOf', 'PerpetratorOf', 'VictimOf', 'LocatedIn', 'Owns', 'Found', 'TransferredTo', 'Witness', 'RelatedTo', 'ConflictWith', 'CooperatesWith', 'ReportedBy', 'ConnectedTo', 'OccursAt', 'EvidenceOf', 'CoversUp', 'CommunicatesWith']

for edge_table in edge_tables:
    try:
        cursor.execute(f"SELECT * FROM {edge_table}")
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            edge = dict(zip(columns, row))
            from_graph_id = None
            to_graph_id = None
            for key in edge.keys():
                if key.startswith("$from_id"):
                    try:
                        data = json.loads(edge[key])
                        from_graph_id = (data.get("table"), int(data.get("id")))
                    except:
                        pass
                if key.startswith("$to_id"):
                    try:
                        data = json.loads(edge[key])
                        to_graph_id = (data.get("table"), int(data.get("id")))
                    except:
                        pass
            if from_graph_id:
                connected_nodes.add(from_graph_id)
            if to_graph_id:
                connected_nodes.add(to_graph_id)
    except:
        pass

# Find isolated nodes
isolated_nodes = []
for graph_id, node_info in all_nodes.items():
    if graph_id not in connected_nodes:
        isolated_nodes.append(node_info)

# Write to file
with open('c:\\Users\\TEMP\\Desktop\\SQLRAG\\isolated_nodes.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total nodes: {len(all_nodes)}\n")
    f.write(f"Connected nodes: {len(connected_nodes)}\n")
    f.write(f"Isolated nodes: {len(isolated_nodes)}\n\n")
    f.write("Isolated nodes:\n")
    for i, node in enumerate(sorted(isolated_nodes, key=lambda x: x['type']), 1):
        f.write(f"{i}. [{node['type']}] {repr(node['name'])}\n")

print(f"Results saved to isolated_nodes.txt")
print(f"Total nodes: {len(all_nodes)}")
print(f"Connected nodes: {len(connected_nodes)}")
print(f"Isolated nodes: {len(isolated_nodes)}")

conn.close()
