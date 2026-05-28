-- ============================================
-- SQLServer 向量数据库架构初始化脚本
-- 用于构建 RAG (Retrieval Augmented Generation) 系统
-- 使用 Ollama 本地部署 nomic-embed-text 模型 (768维)
-- SQL Server 2025+ 原生 VECTOR 类型支持
-- ============================================

USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'VectorDB')
BEGIN
    CREATE DATABASE VectorDB
    COLLATE Chinese_PRC_CI_AS;
END
GO

USE VectorDB;
GO

-- ============================================
-- 删除旧表（如果存在）
-- ============================================
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'VectorIndex')
BEGIN
    DROP TABLE VectorIndex;
END
GO

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'TextChunks')
BEGIN
    DROP TABLE TextChunks;
END
GO

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'Documents')
BEGIN
    DROP TABLE Documents;
END
GO

-- ============================================
-- 文档表 - 存储原始文档
-- ============================================
CREATE TABLE Documents (
    DocumentId BIGINT IDENTITY(1,1) PRIMARY KEY,
    Title NVARCHAR(500) NOT NULL,
    Content NVARCHAR(MAX) NOT NULL,
    Source NVARCHAR(500) NULL,
    Metadata NVARCHAR(MAX) DEFAULT '{}',
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    UpdatedAt DATETIME2 DEFAULT GETDATE(),
    IsDeleted BIT DEFAULT 0
);

CREATE INDEX IX_Documents_Title ON Documents(Title);
CREATE INDEX IX_Documents_CreatedAt ON Documents(CreatedAt);
GO

-- ============================================
-- 文本块表 - 存储分块后的文本
-- ============================================
CREATE TABLE TextChunks (
    ChunkId BIGINT IDENTITY(1,1) PRIMARY KEY,
    DocumentId BIGINT NOT NULL,
    ChunkIndex INT NOT NULL,
    ChunkText NVARCHAR(MAX) NOT NULL,
    ChunkHash NVARCHAR(64) NULL,
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    IsDeleted BIT DEFAULT 0,
    FOREIGN KEY (DocumentId) REFERENCES Documents(DocumentId)
);

CREATE INDEX IX_TextChunks_DocumentId ON TextChunks(DocumentId);
CREATE INDEX IX_TextChunks_ChunkHash ON TextChunks(ChunkHash);
GO

-- ============================================
-- 向量索引表 - 存储文本嵌入向量
-- nomic-embed-text: 768 维向量
-- SQL Server 2025+ 原生 VECTOR 类型支持
-- ============================================
CREATE TABLE VectorIndex (
    VectorId INT IDENTITY(1,1) PRIMARY KEY,
    ChunkId BIGINT NOT NULL UNIQUE,
    EmbeddingVector VECTOR(768) NOT NULL,
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    IsDeleted BIT DEFAULT 0,
    FOREIGN KEY (ChunkId) REFERENCES TextChunks(ChunkId)
);

CREATE INDEX IX_VectorIndex_ChunkId ON VectorIndex(ChunkId);
GO

CREATE VECTOR INDEX idx_content_vector
ON dbo.VectorIndex(EmbeddingVector)
WITH (METRIC = 'cosine');

PRINT 'VectorDB RAG 系统表结构创建完成！';
GO






-- ============================================
-- SQL Server 2025+ 向量索引创建脚本
-- 用于加速 VECTOR_SEARCH 检索
-- ============================================

USE VectorDB;
GO

-- ============================================
-- 创建向量索引 (HNSW)
-- ============================================

IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_VectorIndex_Embedding_HNSW' AND object_id = OBJECT_ID('VectorIndex'))
BEGIN
    DROP INDEX IX_VectorIndex_Embedding_HNSW ON VectorIndex;
END
GO

CREATE VECTOR INDEX IX_VectorIndex_Embedding_HNSW
ON VectorIndex (EmbeddingVector)
WITH (VECTOR_TYPE = FLOAT, DIMENSIONS = 768, INDEX_TYPE = HNSW, M = 16, EF_CONSTRUCTION = 64);
GO

PRINT 'HNSW 向量索引创建完成！';
GO

-- ============================================
-- 查看索引
-- ============================================
SELECT
    i.name AS IndexName,
    i.type_desc AS IndexType
FROM sys.indexes i
WHERE i.object_id = OBJECT_ID('VectorIndex')
AND i.type > 0;
GO

-- ============================================
-- 索引说明
-- ============================================
/*
HNSW (Hierarchical Navigable Small World):
  - 查询性能: O(log n)
  - 构建速度: 较慢
  - 内存占用: 较高
  - 精度: 高
  - 适用: 生产环境

IVFFLAT (Inverted File Flat):
  - 查询性能: 依赖 nlists 参数
  - 构建速度: 快
  - 内存占用: 低
  - 精度: 依赖聚类质量
  - 适用: 数据量小的场景

-- IVFFLAT 示例:
CREATE VECTOR INDEX IX_VectorIndex_Embedding_IVF
ON VectorIndex (EmbeddingVector)
WITH (VECTOR_TYPE = FLOAT, DIMENSIONS = 768, INDEX_TYPE = IVFFLAT, NLISTS = 100);
GO
*/







