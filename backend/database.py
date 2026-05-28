import pyodbc
from config import settings, get_db_connection_string


def get_graph_db_connection():
    conn = pyodbc.connect(get_db_connection_string(settings.database_graph))
    try:
        yield conn
    finally:
        conn.close()


def get_vector_db_connection():
    conn = pyodbc.connect(get_db_connection_string(settings.database_vector))
    try:
        yield conn
    finally:
        conn.close()
