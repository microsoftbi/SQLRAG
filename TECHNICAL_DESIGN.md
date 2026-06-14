# SQLRAG 技术设计文档

## 1. 系统架构概述

SQLRAG 是一个基于 SQL Server 2025 原生 VectorDB 和 GraphDB 支持的双数据库 RAG (Retrieval-Augmented Generation) 系统。

**整体架构：**

```
┌─────────────────────────────────────────────────────────────────────┐
│                        浏览器 (Vue 3 SPA)                           │
│                  http://localhost:3300                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ GraphDB  │  │ VectorDB │  │ Debug    │  │  配置页面         │   │
│  │ 可视化+QA │  │ 文档管理  │  │ SQL/LLM  │  │                  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬──────────┘   │
│       └──────────────┴─────────────┴────────────────┘              │
│                          │ Axios HTTP                              │
└──────────────────────────┼─────────────────────────────────────────┘
                           │ REST API (port 8798)
┌──────────────────────────┼─────────────────────────────────────────┐
│                    FastAPI 后端                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  main.py — 路由注册 + CORS                                   │    │
│  │                                                            │    │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐ │    │
│  │  │GraphDB   │  │VectorDB   │  │ Debug    │  │ config/  │ │    │
│  │  │API_Graph │  │API_Vector │  │API_Debug │  │ database │ │    │
│  │  └────┬─────┘  └────┬──────┘  └────┬─────┘  └──────────┘ │    │
│  │       │              │              │                      │    │
│  │       ├──PyODBC──────┴──PyODBC──────┤                      │    │
│  │       │                             │                      │    │
│  │       ├──langchain-deepseek─────────┤  LLM 集成            │    │
│  │       └──Ollama─────────────────────┤  Embedding           │    │
│  └────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
             ┌────▼─────┐           ┌──────▼──────┐
             │ GraphDB  │           │  VectorDB   │
             │ (Graph)  │           │ (Relational │
             │          │           │  + VECTOR)  │
             │ 6 Node   │           │             │
             │ 20 Edge  │           │ Knowledge-  │
             │ Tables   │           │ Bases       │
             │          │           │ Documents   │
             │          │           │ TextChunks  │
             │          │           │ VectorIndex │
             └──────────┘           └─────────────┘
                   SQL Server 2025
```

---

## 2. 项目目录结构

```
SQLRAG/
├── backend/                          # 后端服务（Python FastAPI）
│   ├── main.py                       # FastAPI 入口（注册路由、CORS）
│   ├── config.py                     # 配置管理（pydantic-settings）
│   ├── database.py                   # 数据库连接（FastAPI 依赖注入）
│   ├── .env                          # 环境变量配置（敏感信息）
│   ├── .env.example                  # 环境变量模板
│   ├── requirements.txt              # Python 依赖清单
│   ├── llm_sql_logs.log              # 运行时日志文件
│   ├── API_Graph.py                  # GraphDB API（图谱数据、QA、legacy 查询）
│   ├── API_Vector.py                 # VectorDB API（文档管理、分块、嵌入、QA）
│   ├── API_Debug.py                  # Debug API（执行 SQL、调用 LLM）
│   ├── prompts/                      # LLM 提示词模板（.md 文件，可独立编辑）
│   │   ├── graph_sql_generation.md   #   图查询 SQL 生成
│   │   ├── graph_sql_fix.md          #   SQL 出错修正
│   │   ├── vector_semantic_chunk.md  #   语义分块
│   │   └── vector_qa_answer.md       #   RAG 回答
│   ├── search_vector.py              # 向量检索诊断脚本
│   └── diagnostic_vector.py          # VectorIndex 综合诊断脚本
│
├── frontend/                         # 前端页面（Vue 3 SPA）
│   ├── index.html                    # HTML 入口文件
│   ├── package.json                  # Node.js 依赖清单
│   ├── vite.config.js                # Vite 构建配置
│   └── src/
│       ├── main.js                   # Vue 应用启动入口
│       ├── App.vue                   # 根组件（侧边栏导航布局）
│       ├── router/
│       │   └── index.js              # Vue Router 路由配置
│       └── views/
│           ├── GraphDB.vue           # 知识图谱可视化 + QA 页面
│           ├── VectorDB.vue          # 向量数据库管理页面
│           └── Debug.vue             # 调试页面（SQL 执行 + LLM 调用）
│
├── 00_GraphDB.sql                    # GraphDB 完整初始化脚本（含示例数据）
├── 00_GraphDB_SchemaOnly.sql         # GraphDB 仅结构脚本（无数据）
├── 00_VectorDB.sql                   # VectorDB 初始化脚本
├── 00_Story.md                       # 示例数据的故事背景
├── add_edges.sql                     # 补充边数据
├── insert_vector_test.py             # 向量插入测试脚本
├── start.bat                         # Windows 启动脚本
├── stop.bat                          # Windows 停止脚本
├── 功能说明.md                       # 功能说明文档
├── TECHNICAL_DESIGN.md               # 本文件 — 技术设计文档
└── README.md                         # 项目简介
```

---

## 3. 各文件详细说明

### 3.1 后端文件

---

#### `backend/main.py`

**作用：** FastAPI 应用入口。创建 App 实例，注册中间件，挂载各路由模块。

**导入的模块：**
| 模块 | 用途 |
|------|------|
| `fastapi.FastAPI` + CORS | FastAPI 框架 + 跨域支持 |
| `config.settings` | 全局配置实例 |
| `API_Vector.router` | VectorDB 路由（前缀 `/vector`） |
| `API_Graph.router` | GraphDB 路由（前缀 `/graph`） |
| `API_Debug.router` | Debug 路由（前缀 `/debug`） |

**结构：**
- CORS 中间件：允许所有来源、方法、头
- 日志配置：同时输出到文件 (`backend/llm_sql_logs.log`) 和控制台
- `app.include_router(...)` 挂载三个子路由

**内置端点：**
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| GET | `/story` | 读取 `00_Story.md` 返回故事简介 |

---

#### `backend/API_Graph.py`

**作用：** GraphDB 图数据库相关 API。包含图谱数据导出、LLM SQL 生成、Legacy 硬编码查询。

**文件拆分：**
- 原 `main.py` 中的 GraphDB 相关逻辑全部移至本文件

**模块级工具函数：**

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `log_llm_interaction(question, sql)` | question, sql | `None` | 记录 LLM 交互日志 |
| `get_schema_content()` | 无 | `str` | 读取 `00_GraphDB_SchemaOnly.sql` |
| `extract_sql_from_response(response)` | response: str | `str` | 从 LLM 响应提取 SQL（支持 ` ```sql ` 代码块） |
| `get_prompt_template()` | 无 | `str` | 读取 `prompts/graph_sql_generation.md` |
| `call_llm_generate_sql(question, schema)` | question, schema | `str` | 调用 ChatDeepSeek 生成 SQL（带 thinking 禁用） |
| `get_fix_prompt_template()` | 无 | `str` | 读取 `prompts/graph_sql_fix.md` |
| `call_llm_fix_sql(question, failed_sql, error, schema)` | 4个参数 | `str` | 将失败 SQL + 错误送回 LLM 修正 |
| `execute_sql_and_format_result(cursor, sql)` | cursor, sql | `str` | 执行 SQL 并格式化为可读文本 |
| `parse_graph_id(graph_id_str)` | graph_id_str | `tuple` | 解析 SQL Server 图 ID JSON |
| `legacy_graph_qa(cursor, question)` | cursor, question | `dict` | 硬编码关键词匹配 + 预定义 SQL 模板（返回 `{answer, generated_sql}`） |
| `find_relationship_between_nodes(cursor, name1, name2)` | cursor, name1, name2 | `(str, str)` | 查找两个 Person 之间的直接关系边 |
| `find_related_entities(cursor, entity_name)` | cursor, entity_name | `(str, str)` | 查找某实体的所有关联实体 |
| `find_common_related_entities(cursor, name1, name2)` | cursor, name1, name2 | `(str, str)` | 查找同时关联两个实体的第三方 |
| `find_path_between_nodes(cursor, name1, name2)` | cursor, name1, name2 | `(str, str)` | 路径查询（提示功能） |
| `find_common_entities(cursor)` | cursor | `(str, str)` | 查找跨案件人物 |
| `get_node_graph_id(cursor, name)` | cursor, name | `str` 或 `None` | 按名称查 graph_id |
| `get_node_name_from_graph_id(cursor, graph_id_str)` | cursor, graph_id_str | `str` 或 `None` | 按 graph_id 查名称 |
| `_find_related_via_match(cursor, person_name)` | cursor, person_name | `(dict, str)` | 23 个 UNION ALL 的 MATCH 查询 |

**API 端点：**

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/graph/data` | conn | 获取所有图节点和边数据 |
| POST | `/graph/qa` | `{question, use_llm}` | 图谱 QA。LLM 模式：生成SQL→执行→失败重试修正 |

---

#### `backend/API_Vector.py`

**作用：** VectorDB 向量数据库相关 API。文档 CRUD、分块、嵌入、索引管理、RAG 问答。

**模块级工具函数：**

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `create_chunks_from_content(...)` | document_id, content, conn, chunk_size, chunk_overlap | `List[Dict]` | LangChain 按字符分块并入库 |
| `get_embedding(text)` | text: str | `List[float]` | 调用 Ollama 生成向量（断长度重试 + NaN 容错） |
| `embed_chunks_for_document(document_id, conn)` | document_id, conn | `Dict` | 为所有未嵌入分块生成向量 |
| `extract_docx_content(file_content)` | bytes | `str` | Word 文档文本提取 |
| `extract_pdf_content(file_content)` | bytes | `str` | PDF 文档文本提取 |
| `get_semantic_chunk_prompt()` | 无 | `(str, str)` | 读取 `prompts/vector_semantic_chunk.md` |
| `get_vector_qa_prompt()` | 无 | `str` | 读取 `prompts/vector_qa_answer.md` |
| `generate_answer_with_sources(question, sources)` | question, sources | `str` | 基于向量检索结果调用 LLM 生成回答 |

**API 端点：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/vector/documents` | 文档列表（支持按知识库筛选） |
| GET | `/vector/documents/{id}` | 单个文档详情 |
| POST | `/vector/documents` | 创建文档 |
| PUT | `/vector/documents/{id}` | 更新文档（修改知识库归属） |
| DELETE | `/vector/documents/{id}` | 软删除文档及关联分块、向量 |
| POST | `/vector/documents/upload` | 上传文件（.txt/.md/.docx/.pdf） |
| GET | `/vector/documents/{id}/chunks` | 获取分块（无则自动创建） |
| POST | `/vector/documents/{id}/embed` | 生成向量嵌入 |
| POST | `/vector/documents/{id}/preview-chunks` | 预览固定分块 |
| POST | `/vector/documents/{id}/semantic-chunk` | LLM 语义分块（不入库） |
| POST | `/vector/documents/{id}/commit-chunks` | 固定分块入库 + 嵌入 |
| POST | `/vector/documents/{id}/commit-chunks-raw` | 语义分块结果入库 + 嵌入 |
| GET | `/vector/knowledge-bases` | 知识库列表 |
| POST | `/vector/knowledge-bases` | 创建知识库 |
| PUT | `/vector/knowledge-bases/{id}` | 更新知识库 |
| DELETE | `/vector/knowledge-bases/{id}` | 软删除知识库 |
| GET | `/vector/chunks` | 所有分块列表 |
| POST | `/vector/qa` | RAG 问答（纯向量检索，无关键词回退） |
| GET | `/vector/config` | 获取系统配置 |
| PUT | `/vector/config` | 更新配置（写入 .env + 同步内存） |
| POST | `/vector/index/create` | 创建 VECTOR INDEX |
| POST | `/vector/index/drop` | 删除 VECTOR INDEX |

**向量检索说明：**
- 使用 SQL Server 2025 `VECTOR_SEARCH` 进行余弦相似度检索
- `METRIC = 'cosine'`，`TOP_N = 5`
- 不设关键词回退，无结果直接返回空

---

#### `backend/API_Debug.py`

**作用：** 调试工具。执行任意 SQL、调用 LLM 测试提示词。

**API 端点：**

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| POST | `/debug/execute-sql` | `{sql}` | 执行 SQL 返回表格结果 |
| POST | `/debug/call-llm` | `{prompt}` | 发送提示词给 ChatDeepSeek 返回响应 |

---

#### `backend/config.py`

**作用：** 集中配置管理，使用 pydantic-settings 从 `.env` 文件加载配置。

**类：`Settings(BaseSettings)`**

| 属性 | 环境变量 | 默认值 | 类型 | 说明 |
|------|----------|--------|------|------|
| `server` | `SERVER` | LOCALHOST | str | 数据库服务器 |
| `port` | `PORT` | 1433 | int | 数据库端口 |
| `database_graph` | `DATABASE_GRAPH` | GraphDB | str | GraphDB 库名 |
| `database_vector` | `DATABASE_VECTOR` | VectorDB | str | VectorDB 库名 |
| `user` | `USER` | sa | str | 数据库用户 |
| `password` | `PASSWORD` | Passw0rd | str | 数据库密码 |
| `backend_port` | `BACKEND_PORT` | 8798 | int | 后端服务端口 |
| `chunk_size` | `CHUNK_SIZE` | 500 | int | 分块字符数 |
| `chunk_overlap` | `CHUNK_OVERLAP` | 100 | int | 分块重叠字符数 |
| `embedding_model` | `EMBEDDING_MODEL` | nomic-embed-text | str | Ollama 嵌入模型 |
| `ollama_base_url` | `OLLAMA_BASE_URL` | http://localhost:11434 | str | Ollama 地址 |
| `llm_api_key` | `LLM_API_KEY` | "" | str | LLM API 密钥 |
| `llm_base_url` | `LLM_BASE_URL` | https://api.deepseek.com/v1 | str | LLM API 地址 |
| `llm_model` | `LLM_MODEL` | deepseek-chat | str | LLM 模型名 |

**函数：** `get_db_connection_string(database)` → 构建 PyODBC 连接字符串

---

#### `backend/database.py`

**作用：** FastAPI 依赖注入，提供数据库连接。

| 函数 | 说明 |
|------|------|
| `get_graph_db_connection()` | 连接到 GraphDB，请求结束自动关闭 |
| `get_vector_db_connection()` | 连接到 VectorDB，请求结束自动关闭 |

---

#### `backend/prompts/` 目录

所有 LLM 提示词模板独立为 `.md` 文件，修改提示词无需改 Python 代码：

| 文件 | 使用方 | 说明 |
|------|--------|------|
| `graph_sql_generation.md` | `API_Graph.call_llm_generate_sql` | 图查询 SQL 生成 |
| `graph_sql_fix.md` | `API_Graph.call_llm_fix_sql` | SQL 出错修正 |
| `vector_semantic_chunk.md` | `API_Vector.semantic_chunk_document` | 语义分块（含 system + user prompt） |
| `vector_qa_answer.md` | `API_Vector.generate_answer_with_sources` | RAG 回答 |

---

### 3.2 前端文件

---

#### `frontend/src/main.js`

Vue 3 应用入口。全局注册 Element Plus、Vue Router，挂载到 `#app`。

---

#### `frontend/src/App.vue`

根布局组件。`el-header`（蓝条标题）+ `el-aside`（侧边栏 `el-menu`，router 模式）+ `el-main`（`<router-view />`）。

**菜单项：**
- `/graph` — GraphDB（图标: DataLine）
- `/vector` — VectorDB（图标: Document）
- `/debug` — Debug（图标: Tools）

---

#### `frontend/src/router/index.js`

```javascript
const routes = [
  { path: '/', redirect: '/graph' },
  { path: '/graph', component: GraphDB },
  { path: '/vector', component: VectorDB },
  { path: '/debug', component: Debug }
]
```

使用 `createWebHistory()`（HTML5 History 模式）。

---

#### `frontend/src/views/GraphDB.vue`

知识图谱可视化与问答页面。

**两个内部 Tab（v-if 切换）：**
- **全景** — `vis-network` 可视化 + 子图弹窗 + 深度控制 (1-5层 BFS)
- **QA** — 问题输入、示例问题按钮、答案展示、SQL 展示

**关键函数：**
| 函数 | 说明 |
|------|------|
| `askQuestion()` | POST `/graph/qa`，支持 `use_llm` 选项 |
| `findRelatedNodes(centerNodeId, depth)` | BFS 查找关联节点 |
| `handleNodeClick(params)` | 打开子图弹窗 |
| `selectExample(ex)` | 填入示例问题 |

---

#### `frontend/src/views/VectorDB.vue`

向量数据库管理页面（约 790 行）。Element Plus `el-tabs`：

| Tab | 功能 |
|-----|------|
| 文档 | 文档列表、筛选、分块查看、行内修改知识库 |
| 文档上传 | 上传文件、固定/语义分块、预览、入库 |
| QA | RAG 问答（纯向量检索） |
| 知识库 | 知识库 CRUD |
| 配置 | 在线修改 Chunk Size / Overlap |
| 索引管理 | 创建 / 删除 VECTOR INDEX |

---

#### `frontend/src/views/Debug.vue`

调试页面。两个 `el-tab-pane`：

| Tab | 功能 |
|-----|------|
| SQL | 输入 SQL → 执行 → 下方 `el-table` 展示结果 |
| 提示词 | 输入提示词 → 调用 LLM → 下方展示模型回复 |

---

### 3.3 SQL 文件

---

#### `00_GraphDB.sql`

GraphDB 完整初始化脚本。6 个 NODE 表、20 个 EDGE 表、示例数据、5 个示例查询。

**节点表：** Person (32人), CaseNode (10案), Organization (7个), Location (16个), Item (18件), Event (26个)

**边表（20 个）：** WorksAt, SubordinateOf, Investigates, SuspectOf, PerpetratorOf, VictimOf, LocatedIn, Owns, Found, TransferredTo, Witness, RelatedTo, ConflictWith, CooperatesWith, ReportedBy, ConnectedTo, OccursAt, EvidenceOf, CoversUp, CommunicatesWith

---

#### `00_VectorDB.sql`

VectorDB 初始化脚本，4 张表 + VECTOR INDEX。

| 表名 | 说明 |
|------|------|
| `KnowledgeBases` | 知识库（分组容器） |
| `Documents` | 文档 |
| `TextChunks` | 文档分块 |
| `VectorIndex` | 向量存储，`EmbeddingVector VECTOR(1024)` |

**向量索引：** `idx_content_vector` on `VectorIndex(EmbeddingVector)` with `METRIC = 'cosine'`

---

### 3.4 配置文件

---

#### `backend/requirements.txt`

```
fastapi==0.109.0
uvicorn==0.27.0
pyodbc==5.1.0
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
python-docx==1.1.0
PyPDF2==3.0.1
ollama==0.1.7
langchain-deepseek==0.1.0
langchain-core==0.1.25
langchain-text-splitters==0.0.1
```

---

#### `frontend/package.json`

| 字段 | 值 |
|------|-----|
| 依赖 | vue ^3.4.0, vue-router ^4.2.5, element-plus ^2.4.4, axios ^1.6.2, vis-network ^9.1.6 |
| 开发依赖 | @vitejs/plugin-vue ^5.0.0, vite ^5.0.0 |

---

## 4. 数据库表关系

```
KnowledgeBases
    │ 1:N
    ▼
Documents ────> TextChunks ────> VectorIndex
                (1:N)           (1:1, UNIQUE)
```

- 所有表均支持软删除（`IsDeleted BIT DEFAULT 0`）

---

## 5. 核心数据流

### 5.1 文档上传与分块流程

```
上传文件 → 解析内容 (.txt/.md/.docx/.pdf) → 保存到 Documents
     → 用户选择分块方式:
         ├── 固定分块 → preview-chunks(预览) → commit-chunks(入库 + VECTOR嵌入)
         └── 语义分块 → semantic-chunk(LLM分段) → commit-chunks-raw(入库 + VECTOR嵌入)
```

**嵌入注意事项：**
- VECTOR INDEX 存在时禁止 INSERT 到 VectorIndex 表
- 必须先 DROP INDEX → 嵌入 → CREATE INDEX
- 嵌入模型维度必须与 `VECTOR(N)` 声明一致

### 5.2 智能问答流程（RAG）

```
用户输入问题
    │
    ▼
get_embedding(question) → 向量化
    │
    ▼
VECTOR_SEARCH(cosine, TOP_N=5) → 检索相似向量
    │
    ▼
JOIN TextChunks + Documents → 获取原文片段
    │
    ▼
generate_answer_with_sources() → LLM 根据上下文回答
    │
    ▼
返回 answer + sources
```

### 5.3 图谱问答流程

```
用户输入问题
    │
    ┌─── use_llm? ───┐
    YES               NO
    │                 │
    ▼                 ▼
读取 Schema         legacy_graph_qa()
    │               (硬编码实体匹配)
    ▼                 │
call_llm_generate    ▼
 _sql()             MATCH 图查询
    │               (23个UNION等)
    ▼                 │
执行 SQL ──失败──→ call_llm_fix_sql() ← 重试最多2次
    │                 │
    ▼                 ▼
返回 answer + generated_sql
```

---

## 6. 外部依赖

| 依赖 | 用途 | 访问地址 |
|------|------|----------|
| **Ollama** | 本地文本嵌入向量生成 | `http://localhost:11434` |
| **OpenAI 兼容 API** | LLM 生成 SQL 和 RAG 回答（支持 DeepSeek / Volcengine Ark 等） | 由 `LLM_BASE_URL` 配置 |
| **SQL Server 2025** | 数据库存储（GraphDB + VectorDB） | `SERVER:LOCALHOST:1433` |