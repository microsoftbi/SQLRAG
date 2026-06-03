# SQLRAG 技术设计文档

## 1. 系统架构概述

SQLRAG 是一个基于 SQL Server 2025 原生 VectorDB 和 GraphDB 支持的双数据库 RAG (Retrieval-Augmented Generation) 系统。

**整体架构：**

```
┌─────────────────────────────────────────────────────────────────┐
│                        浏览器 (Vue 3 SPA)                        │
│                  http://localhost:3300                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ GraphDB  │  │ VectorDB │  │ 知识库   │  │  配置页面       │  │
│  │ 可视化    │  │ 文档管理  │  │ 管理      │  │                │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │
│       └──────────────┴─────────────┴────────────────┘           │
│                          │ Axios HTTP                           │
└──────────────────────────┼──────────────────────────────────────┘
                           │ REST API (port 8798)
┌──────────────────────────┼──────────────────────────────────────┐
│                  FastAPI 后端                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  main.py - 所有 API 端点 + 业务逻辑                        │   │
│  │                                                          │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────────────┐  │   │
│  │  │ GraphDB  │  │ VectorDB  │  │ LLM 集成             │  │   │
│  │  │ 路由     │  │ 路由      │  │ - OpenAI SDK         │  │   │
│  │  └────┬─────┘  └────┬──────┘  │ - Ollama Embedding   │  │   │
│  │       │              │         └──────────────────────┘  │   │
│  │       └──────┬───────┘                                    │   │
│  │              │ PyODBC                                     │   │
│  └──────────────┼───────────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────────┘
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
│   ├── main.py                       # FastAPI 主应用（所有路由和业务逻辑）
│   ├── config.py                     # 配置管理（pydantic-settings）
│   ├── database.py                   # 数据库连接（FastAPI 依赖注入）
│   ├── .env                          # 环境变量配置（敏感信息）
│   ├── .env.example                  # 环境变量模板
│   ├── requirements.txt              # Python 依赖清单
│   └── llm_sql_logs.log              # 运行时日志文件
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
│           └── VectorDB.vue          # 向量数据库管理页面（文档/上传/QA/知识库/配置）
│
├── 00_GraphDB.sql                    # GraphDB 完整初始化脚本（含示例数据）
├── 00_GraphDB_SchemaOnly.sql         # GraphDB 仅结构脚本（无数据）
├── 00_VectorDB.sql                   # VectorDB 初始化脚本
├── 00_Story.md                       # 示例数据的故事背景
├── add_edges.sql                     # 补充边数据
├── start.bat                         # Windows 启动脚本
├── stop.bat                          # Windows 停止脚本
├── 功能说明.md                       # 功能说明文档
└── README.md                         # 项目简介
```

---

## 3. 各文件详细说明

### 3.1 后端文件

---

#### `backend/main.py`

**作用：** 核心应用文件，包含 FastAPI 应用实例、所有 API 路由和业务逻辑函数。

**导入的模块：**
| 模块 | 用途 |
|------|------|
| `fastapi.FastAPI, Depends, UploadFile, File` | FastAPI 框架核心 |
| `fastapi.middleware.cors.CORSMiddleware` | 跨域支持 |
| `fastapi.responses.JSONResponse` | JSON 响应 |
| `pyodbc` | SQL Server 数据库连接 |
| `json, os, re` | 标准库工具 |
| `logging` | 日志记录 |
| `datetime` | 时间处理 |
| `typing.List, Dict, Any` | 类型提示 |
| `langchain_text_splitters.RecursiveCharacterTextSplitter` | 文本分块 |
| `config.settings` | 全局配置实例 |
| `database.get_graph_db_connection, get_vector_db_connection` | 数据库连接依赖 |

**应用级配置：**
- CORS 中间件：允许所有来源、方法、头
- 日志配置：同时输出到文件 (`backend/llm_sql_logs.log`) 和控制台
- `app = FastAPI(title="SQLRAG API")`

---

**模块级工具函数（非路由）：**

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `log_llm_interaction(question, sql)` | question: str, sql: str | `None` | 记录 LLM 交互日志（问题和生成的 SQL） |
| `get_schema_content()` | 无 | `str` | 读取 `00_GraphDB_SchemaOnly.sql` 文件内容 |
| `extract_sql_from_response(response)` | response: str | `str` | 从 LLM 响应中提取 SQL（支持 ` ```sql ` 代码块） |
| `call_llm_generate_sql(question, schema)` | question: str, schema: str | `str` | 调用 OpenAI 兼容接口让 LLM 生成 SQL |
| `execute_sql_and_format_result(cursor, sql)` | cursor, sql: str | `str` | 执行 SQL 并将结果格式化为可读文本 |
| `parse_graph_id(graph_id_str)` | graph_id_str: str | `tuple` | 解析 SQL Server 图 ID JSON 为 (table, id) |
| `create_chunks_from_content(document_id, content, conn, chunk_size, chunk_overlap)` | 见参数 | `List[Dict]` | 使用 LangChain 按字符数分块并写入数据库 |
| `get_embedding(text)` | text: str | `List[float]` | 调用 Ollama `/api/embeddings` 生成向量 |
| `embed_chunks_for_document(document_id, conn)` | document_id: int, conn | `Dict` | 为文档所有未嵌入的分块生成向量 |
| `extract_docx_content(file_content)` | file_content: bytes | `str` | 提取 Word 文档文本内容 |
| `extract_pdf_content(file_content)` | file_content: bytes | `str` | 提取 PDF 文档文本内容 |
| `generate_answer_with_sources(question, sources)` | question: str, sources: list | `str` | 基于检索结果调用 LLM 生成回答 |
| `legacy_graph_qa(cursor, question)` | cursor, question: str | `dict` | 硬编码的图谱 QA 逻辑（实体匹配） |
| `find_relationship_between_nodes(cursor, name1, name2)` | cursor, name1, name2 | `str` | 查找两个节点之间的直接关系边 |
| `find_related_entities(cursor, entity_name)` | cursor, entity_name | `str` | 查找与某实体关联的所有实体 |
| `find_common_related_entities(cursor, name1, name2)` | cursor, name1, name2 | `str` | 查找同时与两个实体都关联的实体 |
| `find_path_between_nodes(cursor, name1, name2)` | cursor, name1, name2 | `str` | 查找两个节点之间的路径（建议使用可视化） |
| `find_common_entities(cursor)` | cursor | `str` | 查找出现在多个案件中的人物 |
| `get_node_graph_id(cursor, name)` | cursor, name | `str` 或 `None` | 根据名称在所有节点表中查找 graph_id |
| `get_node_name_from_graph_id(cursor, graph_id_str)` | cursor, graph_id_str | `str` 或 `None` | 根据 graph_id 获取节点名称 |

---

**API 端点（路由）：**

**系统：**
| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/` | 无 | 健康检查，返回 `{"message": "SQLRAG API is running"}` |

**GraphDB：**
| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/graph/data` | conn=Depends | 获取所有图节点和边数据用于前端可视化 |
| POST | `/graph/qa` | data: Dict | 图数据库问答（支持 LLM 生成 SQL 或硬编码逻辑） |

**VectorDB — 文档：**
| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/vector/documents` | knowledge_base_id(可选) | 获取文档列表，支持按知识库筛选 |
| POST | `/vector/documents` | data: Dict | 手动创建文档 |
| PUT | `/vector/documents/{document_id}` | document_id, data | 更新文档信息（修改知识库归属） |
| DELETE | `/vector/documents/{document_id}` | document_id | 软删除文档及其分块和向量 |
| POST | `/vector/documents/upload` | file, knowledge_base_id(可选) | 上传文档文件（仅保存，不自动切块） |
| GET | `/vector/documents/{document_id}/chunks` | document_id | 获取文档分块（没有则自动创建） |
| POST | `/vector/documents/{document_id}/embed` | document_id | 为文档分块生成向量嵌入 |
| POST | `/vector/documents/{document_id}/preview-chunks` | document_id, data | 预览固定分块结果（不入库） |
| POST | `/vector/documents/{document_id}/semantic-chunk` | document_id | 调用 LLM 进行语义分块（不入库） |
| POST | `/vector/documents/{document_id}/commit-chunks` | document_id, data | 固定分块并入库 + 生成向量 |
| POST | `/vector/documents/{document_id}/commit-chunks-raw` | document_id, data | 将预定义的分块列表直接入库 + 生成向量 |

**VectorDB — 知识库：**
| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/vector/knowledge-bases` | conn=Depends | 获取所有知识库 |
| POST | `/vector/knowledge-bases` | data: Dict | 创建知识库 |
| PUT | `/vector/knowledge-bases/{kb_id}` | kb_id, data | 更新知识库名称/描述 |
| DELETE | `/vector/knowledge-bases/{kb_id}` | kb_id | 软删除知识库（关联文档置 NULL） |

**VectorDB — 其他：**
| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/vector/chunks` | conn=Depends | 获取所有分块列表 |
| POST | `/vector/qa` | data: Dict | 向量检索问答（关键词匹配 + LLM 生成） |
| GET | `/vector/config` | 无 | 获取当前系统配置 |
| PUT | `/vector/config` | data: Dict | 更新系统配置（写入 .env + 同步内存） |

---

#### `backend/config.py`

**作用：** 集中配置管理，使用 pydantic-settings 从 `.env` 文件加载配置。

**类：`Settings(BaseSettings)`**

| 属性 | 环境变量 | 默认值 | 类型 |
|------|----------|--------|------|
| `server` | `SERVER` | LOCALHOST | str |
| `port` | `PORT` | 1433 | int |
| `database_graph` | `DATABASE_GRAPH` | GraphDB | str |
| `database_vector` | `DATABASE_VECTOR` | VectorDB | str |
| `user` | `USER` | sa | str |
| `password` | `PASSWORD` | Passw0rd | str |
| `backend_port` | `BACKEND_PORT` | 8798 | int |
| `chunk_size` | `CHUNK_SIZE` | 1000 | int |
| `chunk_overlap` | `CHUNK_OVERLAP` | 200 | int |
| `embedding_model` | `EMBEDDING_MODEL` | nomic-embed-text | str |
| `ollama_base_url` | `OLLAMA_BASE_URL` | http://localhost:11434 | str |
| `llm_api_key` | `LLM_API_KEY` | "" | str |
| `llm_base_url` | `LLM_BASE_URL` | https://api.deepseek.com/v1 | str |
| `llm_model` | `LLM_MODEL` | deepseek-chat | str |

**模块级实例：** `settings = Settings()` — 全局单例，在 `main.py` 中 `from config import settings` 导入。

**函数：**

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_db_connection_string(database)` | database: str | `str` | 构建 PyODBC 连接字符串 `DRIVER={ODBC Driver 17 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=...;TrustServerCertificate=yes` |

---

#### `backend/database.py`

**作用：** FastAPI 依赖注入，提供数据库连接。

**函数（均为生成器，配合 FastAPI Depends 使用）：**

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `get_graph_db_connection()` | Generator -> `pyodbc.Connection` | 连接到 GraphDB，请求结束时自动关闭 |
| `get_vector_db_connection()` | Generator -> `pyodbc.Connection` | 连接到 VectorDB，请求结束时自动关闭 |

---

### 3.2 前端文件

---

#### `frontend/src/main.js`

**作用：** Vue 3 应用启动入口。

```javascript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

- 全局注册 Element Plus 组件
- 注册 Vue Router
- 挂载到 `#app` DOM 元素

---

#### `frontend/src/App.vue`

**作用：** 根布局组件，提供侧边栏导航。

**模板结构：**
- `el-container` 全屏高度
- `el-header` — 蓝色标题栏 "SQLRAG 系统"
- `el-aside` (200px) — `el-menu` 侧边栏导航（router 模式）
  - `/graph` — GraphDB（图标: DataLine）
  - `/vector` — VectorDB（图标: Document）
- `el-main` — `<router-view />` 渲染子页面

**脚本：**
```javascript
import { Document, DataLine } from '@element-plus/icons-vue'
```

---

#### `frontend/src/router/index.js`

**作用：** Vue Router 路由配置。

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import GraphDB from '../views/GraphDB.vue'
import VectorDB from '../views/VectorDB.vue'

const routes = [
  { path: '/', redirect: '/graph' },
  { path: '/graph', component: GraphDB },
  { path: '/vector', component: VectorDB }
]
```

使用 `createWebHistory()`（HTML5 History 模式）。

---

#### `frontend/src/views/GraphDB.vue`

**作用：** 知识图谱可视化与问答页面。

**组件结构（模板）：**

| 区域 | 说明 |
|------|------|
| `el-tabs` | 包含"全景视图"和"QA问答"两个标签页 |
| 全景视图 | `vis-network` 可视化 + 子图弹窗 + 深度控制滑块 |
| QA 问答 | 问题输入 + 示例问题按钮 + 答案展示 + 生成的 SQL 展示 |

**数据属性（ref）：**
| 变量 | 类型 | 说明 |
|------|------|------|
| `activeTab` | string | 当前 tab ('panorama' \| 'qa') |
| `networkContainer` | ref | vis-network 容器 DOM |
| `subNetworkContainer` | ref | 子图弹窗容器 DOM |
| `nodesData`, `edgesData` | ref | 全量图数据 |
| `showModal` | boolean | 子图弹窗开关 |
| `selectedNode` | object | 当前选中的节点 |
| `depthLevel` | number | 子图探索深度（1-5） |
| `subNodesData`, `subEdgesData` | ref | 子图数据 |
| `question`, `answer` | string | QA 输入和回答 |
| `isLoading` | boolean | QA 加载状态 |
| `useLlm` | boolean | 是否使用 LLM 生成 SQL |
| `generatedSql` | string | LLM 生成的 SQL |

**常量：**
- `nodeColors` — 节点类型到颜色的映射（6种类型）
- `exampleQuestions` — 5个预定义示例问题

**函数：**
| 函数 | 说明 |
|------|------|
| `getNodeLabel(node)` | 从节点数据中提取显示标签 |
| `findRelatedNodes(centerNodeId, depth)` | BFS 查找指定深度内的关联节点 |
| `updateSubGraph()` | 根据深度滑块渲染子图 |
| `handleNodeClick(params)` | 节点点击事件处理，打开子图弹窗 |
| `closeModal()` | 关闭子图弹窗 |
| `selectExample(ex)` | 填充示例问题到输入框 |
| `askQuestion()` | 调用 `/graph/qa` 接口提问 |
| `onMounted()` | 初始化：加载图数据，渲染 vis-network |

---

#### `frontend/src/views/VectorDB.vue`

**作用：** 向量数据库管理页面，包含文档管理、上传分块、QA、知识库管理、系统配置。

**标签页（el-tabs）：**

| Tab | name | 说明 |
|-----|------|------|
| 文档 | documents | 文档列表、筛选、添加、删除、分块查看 |
| 文档上传 | upload | 文件上传、固定分块/语义分块、预览、入库 |
| QA | qa | RAG 问答 |
| 知识库 | knowledge | 知识库 CRUD |
| 配置 | config | 系统参数在线修改 |

**数据属性（ref，约 35 个）：**
| 变量 | 类型 | 说明 |
|------|------|------|
| `activeTab` | string | 当前 tab |
| `documents` | array | 文档列表 |
| `showAddDialog` | boolean | 添加文档弹窗 |
| `newDoc` | object | 添加文档表单数据 |
| `showChunksDialog` | boolean | 分块查看弹窗 |
| `currentChunks` | array | 当前文档的分块列表 |
| `uploadLoading` | boolean | 上传加载状态 |
| `uploadedFiles` | array | 已上传文件列表 |
| `question`, `answer`, `sources` | string/array | QA 相关 |
| `loading` | boolean | QA 加载状态 |
| `knowledgeBases` | array | 知识库列表 |
| `selectedKB` | number | 文档筛选选中的知识库 ID |
| `uploadKB` | number | 上传时选择的知识库 ID |
| `chunkMethodTab` | string | 分块方式 ('fixed' \| 'semantic') |
| `uploadChunkSize`, `uploadChunkOverlap` | number | 上传时的分块参数 |
| `semanticDocId` | number | 语义分块选中的文档 ID |
| `semanticLoading` | boolean | 语义分块加载状态 |
| `semanticResult` | object | 语义分块结果 |
| `semanticCommitting` | boolean | 语义分块入库状态 |
| `config` | object | 系统配置 |
| `configSaving` | boolean | 配置保存状态 |
| `editingDocId` | number | 正在行内编辑知识库的文档 ID |
| `editDocKB` | number | 行内编辑中的知识库值 |
| `showPreviewDialog` | boolean | 分块预览弹窗 |
| `previewChunks` | array | 预览分块数据 |
| `previewChunkSize`, `previewChunkOverlap` | number | 预览参数 |
| `showCreateKBDialog`, `showEditKBDialog` | boolean | 知识库弹窗 |
| `editingKB` | object | 正在编辑的知识库 |
| `kbForm`, `kbEditForm` | object | 知识库表单 |

**函数：**
| 函数 | 说明 |
|------|------|
| `loadConfig()` | GET `/vector/config` 加载配置 |
| `saveConfig()` | PUT `/vector/config` 保存配置 |
| `loadDocuments()` | GET `/vector/documents` 加载文档列表（支持 KB 筛选） |
| `addDocument()` | POST `/vector/documents` 添加文档 |
| `showChunks(doc)` | GET `/vector/documents/{id}/chunks` 查看分块 |
| `deleteDocument(doc)` | DELETE `/vector/documents/{id}` 删除文档 |
| `startEditDocKB(doc)` | 进入行内编辑知识库模式 |
| `saveDocKB(doc)` | PUT `/vector/documents/{id}` 保存知识库修改 |
| `handleFileUpload(file)` | POST `/vector/documents/upload` 上传文档 |
| `handlePreviewChunks(row)` | POST `/vector/documents/{id}/preview-chunks` 预览固定分块 |
| `commitChunks(row)` | POST `/vector/documents/{id}/commit-chunks` 固定分块入库 |
| `startSemanticChunk()` | POST `/vector/documents/{id}/semantic-chunk` 语义分块 |
| `commitSemanticChunks()` | POST `/vector/documents/{id}/commit-chunks-raw` 语义分块结果入库 |
| `formatFileSize(bytes)` | 格式化文件大小为人类可读 |
| `askQuestion()` | POST `/vector/qa` 问答 |
| `loadKnowledgeBases()` | GET `/vector/knowledge-bases` 加载知识库 |
| `createKB()` | POST `/vector/knowledge-bases` 创建知识库 |
| `editKB(kb)` | 打开编辑知识库弹窗 |
| `updateKB()` | PUT `/vector/knowledge-bases/{id}` 更新知识库 |
| `deleteKB(kb)` | DELETE `/vector/knowledge-bases/{id}` 删除知识库 |

---

### 3.3 SQL 文件

---

#### `00_GraphDB.sql`

**作用：** GraphDB 完整初始化脚本，包含 6 个节点表、20 个边表、示例数据和 5 个示例查询。

**节点表：**
| 表名 | 类型 | 说明 |
|------|------|------|
| `Person` | NODE | 人物（32人） |
| `CaseNode` | NODE | 案件（10案） |
| `Organization` | NODE | 组织（7个） |
| `Location` | NODE | 地点（16个） |
| `Item` | NODE | 物品（18件） |
| `Event` | NODE | 事件（26个） |

**边表（共 20 个）：**
| 边表 | 方向 | 说明 |
|------|------|------|
| `WorksAt` | Person -> Organization | 工作关系 |
| `SubordinateOf` | Person -> Person | 上下级 |
| `Investigates` | Person -> CaseNode | 调查关系 |
| `SuspectOf` | Person -> CaseNode | 嫌疑关系 |
| `PerpetratorOf` | Person -> CaseNode | 实施关系 |
| `VictimOf` | Person -> CaseNode | 受害者关系 |
| `LocatedIn` | 各种 -> Location | 位置关系 |
| `Owns` | Person -> Item | 拥有关系 |
| `Found` | Person -> Item | 发现关系 |
| `TransferredTo` | Item -> Person | 转移关系 |
| `Witness` | Person -> Event | 目击关系 |
| `RelatedTo` | Person -> Person | 关联关系 |
| `ConflictWith` | Person -> Person | 冲突关系 |
| `CooperatesWith` | Person -> Person | 合作关系 |
| `ReportedBy` | CaseNode -> Person | 举报关系 |
| `ConnectedTo` | CaseNode -> CaseNode | 案件关联 |
| `OccursAt` | Event -> Location | 发生地点 |
| `EvidenceOf` | Item -> CaseNode | 证据关系 |
| `CoversUp` | Person -> CaseNode | 掩盖关系 |
| `CommunicatesWith` | Person -> Person | 通讯关系 |

---

#### `00_GraphDB_SchemaOnly.sql`

**作用：** 与 `00_GraphDB.sql` 结构相同，但不包含示例数据。仅用于参考表结构。

---

#### `00_VectorDB.sql`

**作用：** VectorDB 初始化脚本，创建 4 张表、索引和向量索引。

**表结构：**
| 表名 | 关键列 | 外键 |
|------|--------|------|
| `KnowledgeBases` | KnowledgeBaseId (PK), Name, Description, CreatedAt, UpdatedAt, IsDeleted | — |
| `Documents` | DocumentId (PK), KnowledgeBaseId (FK), Title, Content, Source, Metadata, CreatedAt, UpdatedAt, IsDeleted | → KnowledgeBases |
| `TextChunks` | ChunkId (PK), DocumentId (FK), ChunkIndex, ChunkText, ChunkHash, CreatedAt, IsDeleted | → Documents |
| `VectorIndex` | VectorId (PK), ChunkId (FK, UNIQUE), EmbeddingVector VECTOR(768), CreatedAt, IsDeleted | → TextChunks |

**向量索引：** `idx_content_vector` on `VectorIndex(EmbeddingVector)` with `METRIC = 'cosine'`

---

#### `add_edges.sql`

**作用：** 补充边数据，将 4 个人物连接到"高速公路服务区"地点。

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
openai==1.10.0
python-multipart==0.0.6
python-docx==1.1.0
PyPDF2==3.0.1
```

---

#### `frontend/package.json`

| 字段 | 值 |
|------|-----|
| name | sqlrag-frontend |
| version | 1.0.0 |
| 脚本 | `dev` (vite --port 3300), `build`, `preview` |
| 依赖 | vue ^3.4.0, vue-router ^4.2.5, element-plus ^2.4.4, axios ^1.6.2, vis-network ^9.1.6 |
| 开发依赖 | @vitejs/plugin-vue ^5.0.0, vite ^5.0.0 |

---

#### `frontend/vite.config.js`

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  server: { port: 3300 }
})
```

---

#### `start.bat`

**作用：** Windows 启动脚本。
1. 在新窗口中启动后端（port 8798），先 `pip install` 再 `python main.py`
2. 等待 5 秒
3. 在新窗口中启动前端（port 3300），先 `npm install` 再 `npm run dev`

#### `stop.bat`

**作用：** Windows 停止脚本。
1. 按窗口标题杀死后端和前端进程
2. 杀死所有 `node.exe` 和 `python.exe` 进程

---

## 4. 数据库表关系图

```
KnowledgeBases
    │
    │ 1:N
    ▼
Documents ────> TextChunks ────> VectorIndex
                (1:N)           (1:1, UNIQUE)
```

- `KnowledgeBases` 是文档的分组容器
- `Documents` 通过 `KnowledgeBaseId` 外键关联到知识库
- `TextChunks` 通过 `DocumentId` 外键关联到文档（一个文档有多个分块）
- `VectorIndex` 通过 `ChunkId` 外键（UNIQUE）关联到分块（一个分块只有一个向量）
- 所有表均支持软删除（`IsDeleted BIT DEFAULT 0`）

---

## 5. 核心数据流

### 5.1 文档上传与分块流程

```
用户拖拽文件
    │
    ▼
POST /vector/documents/upload
    │
    ▼
解析文件内容 (.txt/.md/.docx/.pdf)
    │
    ▼
保存到 Documents 表（仅保存，不切块）
    │
    ▼
用户在界面选择分块方式
    │
    ├── 固定分块 ──→ POST /preview-chunks（预览）──→ POST /commit-chunks（入库 + 嵌入）
    │
    └── 语义分块 ──→ POST /semantic-chunk（LLM 分段预览）──→ POST /commit-chunks-raw（入库 + 嵌入）
```

### 5.2 智能问答流程（RAG）

```
用户输入问题
    │
    ▼
关键词匹配 TextChunks（LIKE 查询）
    │
    ▼
获取最多 5 个相关文档片段
    │
    ▼
构建上下文 → 调用 LLM 生成回答
    │
    ▼
返回答案 + 参考来源
```

### 5.3 图谱问答流程

```
用户输入问题
    │
    ▼
┌─── 是否使用 LLM？───┐
│   YES               NO
│   │                 │
│   ▼                 ▼
│ 读取 Schema        硬编码实体匹配
│   │                 │
│   ▼                 ▼
│ 调用 LLM 生成 SQL  查找关系/关联实体
│   │                 │
│   ▼                 ▼
│ 执行 SQL           格式化结果
│   │                 │
└───┴─── 返回答案 ────┘
```

---

## 6. 外部依赖

| 依赖 | 用途 | 访问地址 |
|------|------|----------|
| **Ollama** | 本地文本嵌入向量生成 | `http://localhost:11434` |
| **OpenAI 兼容 API** | LLM 生成 SQL 和 RAG 回答 | 由 `LLM_BASE_URL` 配置 |
| **SQL Server 2025** | 数据库存储（GraphDB + VectorDB） | `SERVER:LOCALHOST:1433` |
