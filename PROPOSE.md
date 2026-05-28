## 摘要
我想要设计一套基于SQLServer2025的RAG系统。
包括传统切块的RAG和图数据库的RAG。
主要用到SQLServer对VectorDB和GraphDB的支持。

## 技术架构：
### 后端:
Python 3.11
FastAPI
DAO(暂不适用SQLAlchemy)
数据库:
SQLServer2025

### 前端
Vue3 + ElementPlus

### 端口
前端固定使用3300。
后端固定使用8798。


## 文件的组织：
后端服务：backend
前端页面：frontend

## 页面功能

### GraphDB页
- 功能：只读展示GraphDB中的所有Node和Edge数据
- 参考：https://github.com/microsoftbi/SQLServerRAG/blob/main/frontend/src/components/GraphVisualization.vue

### VectorDB页
- 功能：向量存储与检索
- 支持向量数据的存储、相似度检索

### 用户认证
- 不需要用户认证

### 部署方式
- Windows本地部署

### 数据库配置
SERVER: LOCALHOST
PORT: 1433
DATABASE: GraphDB, VectorDB，两个数据库分开保存数据。
USER: sa
PASSWORD: Passw0rd

数据库的配置信息保存在backend的.env文件中。

GraphDB的架构文件已经保存在：00_GraphDB.sql
VectorDB的架构文件已经保存在：00_VectorDB.sql

### 运维
在项目下创建一个start.bat文件和stop.bat文件，帮助我启动和关闭后端服务和前端页面。


