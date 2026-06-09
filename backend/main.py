from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
from config import settings
from API_Vector import router as vector_router
from API_Graph import router as graph_router

# 获取当前脚本所在目录，确保日志文件在 backend 目录下
_log_dir = os.path.dirname(os.path.abspath(__file__))
_log_path = os.path.join(_log_dir, 'llm_sql_logs.log')

logging.basicConfig(
    filename=_log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# 同时输出到控制台，方便实时查看
_console = logging.StreamHandler()
_console.setLevel(logging.DEBUG)
_console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger('').addHandler(_console)

print(f"日志文件路径: {_log_path}")

app = FastAPI(title="SQLRAG API")

logging.info("SQLRAG API 启动成功")
logging.info(f"Embedding 模型: {settings.embedding_model}")
logging.info(f"Ollama 地址: {settings.ollama_base_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vector_router)
app.include_router(graph_router)


@app.get("/")
async def root():
    return {"message": "SQLRAG API is running"}


@app.get("/story")
async def get_story():
    """返回 00_Story.md 的内容"""
    story_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "00_Story.md")
    try:
        with open(story_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"读取失败: {str(e)}"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)
