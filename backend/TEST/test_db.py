import pyodbc
from config import settings

print("Testing database connection...")

try:
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={settings.server},{settings.port};"
        f"DATABASE={settings.database_graph};"
        f"UID={settings.user};"
        f"PWD={settings.password};"
        f"TrustServerCertificate=yes;"
    )
    print(f"Connecting to: {settings.server}:{settings.port}/{settings.database_graph}")
    
    conn = pyodbc.connect(conn_str)
    print("Connected successfully!")
    
    cursor = conn.cursor()
    
    # Test query some tables
    tables = ["Person", "CaseNode", "Organization", "Location", "Item", "Event"]
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count} rows")
        except Exception as e:
            print(f"{table}: Error - {e}")
    
    conn.close()
    print("Test completed!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
