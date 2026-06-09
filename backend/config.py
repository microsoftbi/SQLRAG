from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

# 手动加载.env文件
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)


class Settings(BaseSettings):
    server: str = os.getenv("SERVER", "LOCALHOST")
    port: int = int(os.getenv("PORT", "1433"))
    database_graph: str = os.getenv("DATABASE_GRAPH", "GraphDB")
    database_vector: str = os.getenv("DATABASE_VECTOR", "VectorDB")
    user: str = os.getenv("USER", "sa")
    password: str = os.getenv("PASSWORD", "Passw0rd")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8798"))

    # 分块配置
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    # Embedding 配置
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # LLM配置
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")


settings = Settings()


def get_db_connection_string(database: str) -> str:
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={settings.server},{settings.port};"
        f"DATABASE={database};"
        f"UID={settings.user};"
        f"PWD={settings.password};"
        f"TrustServerCertificate=yes;"
    )
