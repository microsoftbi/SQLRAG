import pyodbc
from config import settings, get_db_connection_string
import json

conn = pyodbc.connect(get_db_connection_string(settings.database_graph))
cursor = conn.cursor()

# 检查 CaseNode 表中的所有案件名称
f = open('test_output.txt', 'w', encoding='utf-8')

f.write("=== CaseNode 表中的案件 ===\n")
cursor.execute("SELECT name, $node_id FROM CaseNode")
rows = cursor.fetchall()
for row in rows:
    name = row[0] if row[0] else "None"
    node_id = str(row[1]) if row[1] else "None"
    f.write(f"  {name} -> {node_id}\n")

f.write("\n=== 尝试查找 '叶剑遇害案' ===\n")
cursor.execute("SELECT $node_id FROM CaseNode WHERE name = ?", ("叶剑遇害案",))
row = cursor.fetchone()
if row:
    f.write(f"找到: {row[0]}\n")
else:
    f.write("未找到 '叶剑遇害案'\n")

f.write("\n=== 检查与案件相关的关系 ===\n")
cursor.execute("""
    SELECT p.name, c.name 
    FROM SuspectOf so
    JOIN Person p ON so.$from_id = p.$node_id
    JOIN CaseNode c ON so.$to_id = c.$node_id
""")
rows = cursor.fetchall()
for row in rows:
    p_name = row[0] if row[0] else "None"
    c_name = row[1] if row[1] else "None"
    f.write(f"  {p_name} SuspectOf {c_name}\n")

conn.close()
f.close()
print("Output written to test_output.txt")