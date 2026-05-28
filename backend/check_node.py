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

node_tables = [
    ("Person", "Person"),
    ("CaseNode", "Case"),
    ("Organization", "Organization"),
    ("Location", "Location"),
    ("Item", "Item"),
    ("Event", "Event"),
]

found_node = None
found_table = None
found_id = None
found_graph_id = None
found_name = None

for table_name, node_type in node_tables:
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            node = dict(zip(columns, row))
            name = str(node.get('name', ''))
            
            graph_id_val = None
            for key in node.keys():
                if key.startswith("$node_id"):
                    try:
                        data = json.loads(node[key])
                        graph_id_val = int(data.get("id"))
                    except:
                        pass
            
            if graph_id_val is not None:
                if '服务区' in name or '高速' in name:
                    print(f"Match! table={table_name}, id={node.get('id')}, graph_id={graph_id_val}")
                    print(f"  Name: {repr(name)}")
                    found_node = node
                    found_table = table_name
                    found_id = node.get("id")
                    found_graph_id = graph_id_val
                    found_name = name
    except Exception as e:
        pass

if found_table and found_graph_id is not None:
    print(f"\nChecking edges for: {found_table} graph_id={found_graph_id}")
    
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
    
    found_edges = []
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
                
                if (from_table == found_table and from_id == found_graph_id) or \
                   (to_table == found_table and to_id == found_graph_id):
                    found_edges.append({
                        "edge_table": table_name,
                        "edge_type": edge_type,
                        "from_table": from_table,
                        "from_id": from_id,
                        "to_table": to_table,
                        "to_id": to_id
                    })
        except Exception as e:
            pass
    
    print(f"Found {len(found_edges)} edges for this node")
    for e in found_edges:
        print(f"  {e}")

conn.close()
