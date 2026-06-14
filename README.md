# SQLRAG - 基于 SQL Server 2025 的 RAG 系统

基于 SQL Server 2025 原生 VectorDB 和 GraphDB 支持的 RAG (Retrieval-Augmented Generation) 系统，提供知识图谱可视化和向量检索问答功能。

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- PyODBC (SQL Server 连接)
- LangChain + langchain-deepseek (LLM 集成)
- LangChain Text Splitters (文档分块)
- python-docx / PyPDF2 (文档解析)

### 前端
- Vue 3
- Element Plus
- Vite
- Axios
- Vis Network (图谱可视化)

### 数据库
- SQL Server 2025 (支持 VectorDB 和 GraphDB)

## 项目结构

```
SQLRAG/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI 入口（注册路由、CORS）
│   ├── config.py        # 配置管理（pydantic-settings）
│   ├── database.py      # 数据库连接依赖
│   ├── requirements.txt # Python 依赖
│   ├── .env             # 环境变量 (需自行配置)
│   ├── .env.example     # 环境变量示例
│   ├── API_Graph.py     # GraphDB API（图谱数据、QA、legacy 查询）
│   ├── API_Vector.py    # VectorDB API（文档管理、分块、嵌入、QA）
│   ├── API_Debug.py     # Debug API（执行 SQL、调用 LLM）
│   ├── prompts/         # LLM 提示词模板（.md 文件，可独立编辑）
│   │   ├── graph_sql_generation.md
│   │   ├── graph_sql_fix.md
│   │   ├── vector_semantic_chunk.md
│   │   └── vector_qa_answer.md
│   └── search_vector.py # 向量检索诊断脚本
├── frontend/            # 前端页面
│   ├── src/
│   │   ├── views/       # 页面组件（GraphDB.vue, VectorDB.vue, Debug.vue）
│   │   ├── router/      # 路由配置
│   │   ├── App.vue      # 根组件（含侧边栏导航）
│   │   └── main.js      # 入口文件
│   ├── index.html       # HTML 模板
│   ├── package.json     # 前端依赖
│   └── vite.config.js   # Vite 配置
├── 00_GraphDB.sql       # GraphDB 初始化脚本
├── 00_VectorDB.sql      # VectorDB 初始化脚本
├── 功能说明.md          # 详细功能说明文档
├── start.bat           # 启动脚本
└── stop.bat            # 停止脚本
```

## 功能特性

### GraphDB 页面
- 知识图谱可视化展示
- 节点关系查询与深度探索
- 基于 LLM 的图数据库问答（支持 AI 生成 SQL 和 Legacy 硬编码两种模式）
- 自动生成 SQL Server 图查询，SQL 执行失败时自动修正
- 非 AI 模式也展示生成的 SQL

### VectorDB 页面
- **文档管理**：查看、添加、删除文档，支持知识库筛选和行内修改所属知识库
- **文档上传**：支持 .txt, .md, .docx, .pdf 格式上传，上传后暂不入库
- **固定分块**：使用 LangChain 按字符数分块，可自定义 Chunk Size 和 Overlap，预览后入库
- **语义分块**：调用大模型对文档进行智能语义分段，原文/结果对比预览后入库
- **知识库管理**：创建、编辑、删除知识库，用于文档分组管理
- **系统配置**：在线修改 Chunk Size、Chunk Overlap 等参数
- **向量索引管理**：在线创建/删除 VECTOR INDEX
- **智能问答**：基于向量检索的 RAG 问答，支持来源展示

### Debug 页面
- **SQL**：执行任意 SQL 语句并展示表格结果
- **提示词**：发送自定义提示词给 LLM 并查看响应

## 快速开始

### 前置要求

1. SQL Server 2025 已安装并运行
2. Python 3.11+ 已安装
3. Node.js 18+ 已安装
4. Ollama 已安装并运行（用于生成文本嵌入向量）

### 数据库初始化

1. 执行 `00_GraphDB.sql` 初始化 GraphDB
2. 执行 `00_VectorDB.sql` 初始化 VectorDB

### 后端配置

1. 复制 `backend/.env.example` 为 `backend/.env`
2. 根据实际情况修改配置：

```env
# 数据库配置
SERVER=LOCALHOST
PORT=1433
DATABASE_GRAPH=GraphDB
DATABASE_VECTOR=VectorDB
USER=sa
PASSWORD=Passw0rd

# 后端端口
BACKEND_PORT=8798

# 分块配置
CHUNK_SIZE=500
CHUNK_OVERLAP=100

# Embedding 配置（支持 Ollama 中的任意嵌入模型）
EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_BASE_URL=http://localhost:11434

# LLM 配置（兼容 OpenAI/DeepSeek/Volcengine Ark 等 API）
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 安装依赖

**后端:**
```bash
cd backend
pip install -r requirements.txt
```

**前端:**
```bash
cd frontend
npm install
```

### 启动服务

**方式一：使用脚本 (Windows)**
```bash
# 启动
start.bat

# 停止
stop.bat
```

**方式二：手动启动**

**后端:**
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8798
```

**前端:**
```bash
cd frontend
npm run dev
```

## 端口说明

- 前端: http://localhost:3300
- 后端: http://localhost:8798
- 后端 API 文档: http://localhost:8798/docs

## 主要 API

### GraphDB
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/graph/data` | 获取图谱数据 |
| POST | `/graph/qa` | 图数据库问答（AI / Legacy） |

### VectorDB — 文档
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/vector/documents` | 获取文档列表（支持按知识库筛选） |
| POST | `/vector/documents` | 添加文档 |
| PUT | `/vector/documents/{id}` | 更新文档信息 |
| DELETE | `/vector/documents/{id}` | 删除文档 |
| POST | `/vector/documents/upload` | 上传文档 |
| GET | `/vector/documents/{id}` | 获取单个文档 |
| GET | `/vector/documents/{id}/chunks` | 获取文档分块 |
| POST | `/vector/documents/{id}/embed` | 生成向量嵌入 |
| POST | `/vector/documents/{id}/preview-chunks` | 预览固定分块 |
| POST | `/vector/documents/{id}/semantic-chunk` | 语义分块 |
| POST | `/vector/documents/{id}/commit-chunks` | 固定分块入库 |
| POST | `/vector/documents/{id}/commit-chunks-raw` | 语义分块结果入库 |

### VectorDB — 知识库
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/vector/knowledge-bases` | 获取知识库列表 |
| POST | `/vector/knowledge-bases` | 创建知识库 |
| PUT | `/vector/knowledge-bases/{id}` | 更新知识库 |
| DELETE | `/vector/knowledge-bases/{id}` | 删除知识库 |

### VectorDB — 向量索引
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/vector/index/create` | 创建 VECTOR INDEX |
| POST | `/vector/index/drop` | 删除 VECTOR INDEX |

### VectorDB — 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/vector/config` | 获取系统配置 |
| PUT | `/vector/config` | 更新系统配置 |
| POST | `/vector/qa` | 向量检索问答（纯向量检索） |

### Debug
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/debug/execute-sql` | 执行 SQL 并返回表格结果 |
| POST | `/debug/call-llm` | 发送提示词调用 LLM |

## 日志

LLM 交互日志保存在 `backend/llm_sql_logs.log`

## 许可证

MIT License