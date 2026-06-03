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

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'KnowledgeBases')
BEGIN
    DROP TABLE KnowledgeBases;
END
GO

-- ============================================
-- 知识库表 - 用于文档分组管理
-- ============================================
CREATE TABLE KnowledgeBases (
    KnowledgeBaseId BIGINT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(200) NOT NULL,
    Description NVARCHAR(MAX) NULL,
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    UpdatedAt DATETIME2 DEFAULT GETDATE(),
    IsDeleted BIT DEFAULT 0
);

CREATE INDEX IX_KnowledgeBases_Name ON KnowledgeBases(Name);
CREATE INDEX IX_KnowledgeBases_CreatedAt ON KnowledgeBases(CreatedAt);
GO

-- ============================================
-- 文档表 - 存储原始文档
-- ============================================
CREATE TABLE Documents (
    DocumentId BIGINT IDENTITY(1,1) PRIMARY KEY,
    KnowledgeBaseId BIGINT NULL,
    Title NVARCHAR(500) NOT NULL,
    Content NVARCHAR(MAX) NOT NULL,
    Source NVARCHAR(500) NULL,
    Metadata NVARCHAR(MAX) DEFAULT '{}',
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    UpdatedAt DATETIME2 DEFAULT GETDATE(),
    IsDeleted BIT DEFAULT 0,
    FOREIGN KEY (KnowledgeBaseId) REFERENCES KnowledgeBases(KnowledgeBaseId)
);

CREATE INDEX IX_Documents_Title ON Documents(Title);
CREATE INDEX IX_Documents_CreatedAt ON Documents(CreatedAt);
CREATE INDEX IX_Documents_KnowledgeBaseId ON Documents(KnowledgeBaseId);
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






