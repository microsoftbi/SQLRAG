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

print("=== Testing graph data loading ===")
nodes = []
edges = []

node_lookup = {}

node_tables = [
    ("Person", "Person"),
    ("CaseNode", "Case"),
    ("Organization", "Organization"),
    ("Location", "Location"),
    ("Item", "Item"),
    ("Event", "Event"),
]

node_counter = 1
for table_name, node_type in node_tables:
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            node = dict(zip(columns, row))
            graph_id = None
            for key in node.keys():
                if key.startswith("$node_id"):
                    try:
                        data = json.loads(node[key])
                        graph_id = int(data.get("id"))
                    except:
                        pass
                    break
            
            if graph_id is not None:
                our_id = f"{node_type}_{node_counter}"
                node_counter += 1
                node_lookup[(table_name, graph_id)] = our_id
                name = node.get('name', node.get('title', ''))
                nodes.append({
                    "id": our_id,
                    "type": node_type,
                    "name": str(name)[:50]
                })
    except Exception as e:
        print(f"Error with {table_name}: {e}")

print(f"\nLoaded {len(nodes)} nodes")

edge_tables = [
    ("WorksAt", "WorksAt"),
    ("SubordinateOf", "SubordinateOf"),
    ("Investigates", "Investigates"),
    ("SuspectOf", "SuspectOf"),
    ("PerpetratorOf", "PerpetratorOf"),
    ("VictimOf", "VictimOf"),
    ("LocatedIn", "LocatedIn"),
    ("Owns", "Owns"),
    ("Found", "Found"),
    ("TransferredTo", "TransferredTo"),
    ("Witness", "Witness"),
    ("RelatedTo", "RelatedTo"),
    ("ConflictWith", "ConflictWith"),
    ("CooperatesWith", "CooperatesWith"),
    ("ReportedBy", "ReportedBy"),
    ("ConnectedTo", "ConnectedTo"),
    ("OccursAt", "OccursAt"),
    ("EvidenceOf", "EvidenceOf"),
    ("CoversUp", "CoversUp"),
    ("CommunicatesWith", "CommunicatesWith"),
]

edge_counter = 1
missing_edges = 0
for table_name, edge_type in edge_tables:
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            edge = dict(zip(columns, row))
            from_table = None
            from_id = None
            to_table = None
            to_id = None
            
            for key in edge.keys():
                if key.startswith("$from_id"):
                    try:
                        data = json.loads(edge[key])
                        from_table = data.get("table")
                        from_id = int(data.get("id"))
                    except:
                        pass
                if key.startswith("$to_id"):
                    try:
                        data = json.loads(edge[key])
                        to_table = data.get("table")
                        to_id = int(data.get("id"))
                    except:
                        pass
            
            if from_table and from_id is not None and to_table and to_id is not None:
                from_key = (from_table, from_id)
                to_key = (to_table, to_id)
                
                if from_key in node_lookup and to_key in node_lookup:
                    edges.append({
                        "id": f"edge_{edge_counter}",
                        "type": edge_type,
                        "from": node_lookup[from_key],
                        "to": node_lookup[to_key]
                    })
                    edge_counter += 1
                else:
                    missing_edges += 1
    except Exception as e:
        print(f"Error with {table_name}: {e}")

print(f"Loaded {len(edges)} edges, {missing_edges} missing edges")
print(f"\nFirst 10 nodes:")
for n in nodes[:10]:
    print(f"  {n}")

conn.close()
