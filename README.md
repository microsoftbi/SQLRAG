# SQLRAG - 基于 SQL Server 2025 的 RAG 系统

基于 SQL Server 2025 原生 VectorDB 和 GraphDB 支持的 RAG (Retrieval-Augmented Generation) 系统，提供知识图谱可视化和向量检索问答功能。

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- PyODBC (SQL Server 连接)
- OpenAI SDK (LLM 集成)

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
│   ├── main.py          # FastAPI 主文件
│   ├── config.py        # 配置管理
│   ├── database.py      # 数据库连接
│   ├── requirements.txt # Python 依赖
│   ├── .env             # 环境变量 (需自行配置)
│   └── .env.example     # 环境变量示例
├── frontend/            # 前端页面
│   ├── src/
│   │   ├── views/       # 页面组件
│   │   ├── router/      # 路由
│   │   ├── App.vue      # 根组件
│   │   └── main.js      # 入口文件
│   ├── index.html       # HTML 模板
│   ├── package.json     # 前端依赖
│   └── vite.config.js   # Vite 配置
├── 00_GraphDB.sql       # GraphDB 初始化脚本
├── 00_VectorDB.sql      # VectorDB 初始化脚本
├── start.bat           # 启动脚本
└── stop.bat            # 停止脚本
```

## 功能特性

### GraphDB 页面
- 知识图谱可视化展示
- 节点关系查询
- 节点深度探索
- 基于 LLM 的图数据库问答
- 自动生成 SQL Server 图查询

### VectorDB 页面
- 文档管理（查看、添加）
- 文档上传（支持 .txt, .md, .docx, .pdf）
- 文档分块查看
- 基于文档的智能问答
- 参考来源展示

## 快速开始

### 前置要求

1. SQL Server 2025 已安装并运行
2. Python 3.11+ 已安装
3. Node.js 18+ 已安装

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

# LLM 配置
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

## API 文档

后端启动后访问: http://localhost:8798/docs

### 主要 API

#### GraphDB
- `GET /graph/data` - 获取图谱数据
- `POST /graph/qa` - 图数据库问答

#### VectorDB
- `GET /vector/documents` - 获取文档列表
- `POST /vector/documents` - 添加文档
- `POST /vector/documents/upload` - 上传文档
- `GET /vector/documents/{document_id}/chunks` - 获取文档分块
- `POST /vector/qa` - 向量检索问答

## 日志

LLM 交互日志保存在 `backend/llm_sql_logs.log`

## 许可证

MIT License
