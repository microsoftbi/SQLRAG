-- ============================================================
-- DZS.md 知识图谱 — SQL Server 2025 Graph Database
-- ============================================================

-- 1. 节点表 (Node Tables)
-- ============================================================

-- 1.1 人物节点
DROP TABLE IF EXISTS Person;
CREATE TABLE Person (
    id          INT IDENTITY PRIMARY KEY,
    name        NVARCHAR(50)  NOT NULL,          -- 姓名
    role        NVARCHAR(100) NULL,               -- 身份/角色标签
    affiliation NVARCHAR(100) NULL,               -- 所属单位
    status      NVARCHAR(50)  NULL DEFAULT '存活', -- 存活/死亡/在逃/被捕
    notes       NVARCHAR(500) NULL
) AS NODE;

-- 1.2 案件节点
DROP TABLE IF EXISTS CaseNode;
CREATE TABLE CaseNode (
    id          INT IDENTITY PRIMARY KEY,
    name        NVARCHAR(100) NOT NULL,           -- 案件名称
    case_type   NVARCHAR(50)  NULL,               -- 类型: 命案/抢劫/贪腐/洗钱
    status      NVARCHAR(50)  NULL DEFAULT '侦办中', -- 已结案/侦办中/悬案
    time_range  NVARCHAR(100) NULL,               -- 案发时间段描述
    notes       NVARCHAR(500) NULL
) AS NODE;

-- 1.3 组织/机构节点
DROP TABLE IF EXISTS Organization;
CREATE TABLE Organization (
    id      INT IDENTITY PRIMARY KEY,
    name    NVARCHAR(100) NOT NULL,
    org_type NVARCHAR(50)  NULL,                  -- 公安机关/企业/政府/媒体
    notes   NVARCHAR(500) NULL
) AS NODE;

-- 1.4 地点节点
DROP TABLE IF EXISTS Location;
CREATE TABLE Location (
    id           INT IDENTITY PRIMARY KEY,
    name         NVARCHAR(100) NOT NULL,
    location_type NVARCHAR(50)  NULL,             -- 城市/建筑/公司/野外
    city         NVARCHAR(50)  NULL,
    notes        NVARCHAR(500) NULL
) AS NODE;

-- 1.5 物品/证据节点
DROP TABLE IF EXISTS Item;
CREATE TABLE Item (
    id          INT IDENTITY PRIMARY KEY,
    name        NVARCHAR(100) NOT NULL,
    item_type   NVARCHAR(50)  NULL,               -- 证据/赃物/凶器/财物/信件
    is_evidence BIT           NULL DEFAULT 1,     -- 是否为证据
    notes       NVARCHAR(500) NULL
) AS NODE;

-- 1.6 关键事件节点
DROP TABLE IF EXISTS Event;
CREATE TABLE Event (
    id        INT IDENTITY PRIMARY KEY,
    name      NVARCHAR(200) NOT NULL,
    event_type NVARCHAR(50)  NULL,                -- 犯罪/追捕/交易/死亡/抓捕
    notes     NVARCHAR(500) NULL
) AS NODE;

-- 2. 边表 (Edge Tables)
-- ============================================================

-- 2.1 Person -(任职于)-> Organization
DROP TABLE IF EXISTS WorksAt;
CREATE TABLE WorksAt (
    id      INT IDENTITY PRIMARY KEY,
    position NVARCHAR(50) NULL                    -- 职位
) AS EDGE;

-- 2.2 Person -(下属)-> Person
DROP TABLE IF EXISTS SubordinateOf;
CREATE TABLE SubordinateOf (
    id          INT IDENTITY PRIMARY KEY,
    description NVARCHAR(100) NULL
) AS EDGE;

-- 2.3 Person -(调查)-> CaseNode
DROP TABLE IF EXISTS Investigates;
CREATE TABLE Investigates (
    id       INT IDENTITY PRIMARY KEY,
    role     NVARCHAR(50) NULL                    -- 主办/协办/参与
) AS EDGE;

-- 2.4 Person -(嫌疑人)-> CaseNode
DROP TABLE IF EXISTS SuspectOf;
CREATE TABLE SuspectOf (
    id     INT IDENTITY PRIMARY KEY,
    degree NVARCHAR(50) NULL,                     -- 重大嫌疑/一般嫌疑/已排除
    notes  NVARCHAR(200) NULL
) AS EDGE;

-- 2.5 Person -(作案人)-> CaseNode
DROP TABLE IF EXISTS PerpetratorOf;
CREATE TABLE PerpetratorOf (
    id         INT IDENTITY PRIMARY KEY,
    confession BIT NULL DEFAULT 0                 -- 是否已认罪
) AS EDGE;

-- 2.6 Person -(受害人)-> CaseNode
DROP TABLE IF EXISTS VictimOf;
CREATE TABLE VictimOf (
    id    INT IDENTITY PRIMARY KEY,
    cause NVARCHAR(100) NULL                      -- 死因/伤因
) AS EDGE;

-- 2.7 Person/Event/Case -(位于)-> Location
DROP TABLE IF EXISTS LocatedIn;
CREATE TABLE LocatedIn (
    id          INT IDENTITY PRIMARY KEY,
    description NVARCHAR(200) NULL
) AS EDGE;

-- 2.8 Person -(拥有)-> Item
DROP TABLE IF EXISTS Owns;
CREATE TABLE Owns (
    id          INT IDENTITY PRIMARY KEY,
    description NVARCHAR(200) NULL
) AS EDGE;

-- 2.9 Person -(发现)-> Item
DROP TABLE IF EXISTS Found;
CREATE TABLE Found (
    id       INT IDENTITY PRIMARY KEY,
    scene    NVARCHAR(200) NULL,                  -- 发现场景
    notes    NVARCHAR(200) NULL
) AS EDGE;

-- 2.10 Item -(流转自/至)-> Person (物品流转)
DROP TABLE IF EXISTS TransferredTo;
CREATE TABLE TransferredTo (
    id       INT IDENTITY PRIMARY KEY,
    method   NVARCHAR(50) NULL,                   -- 交易/抢劫/赠予/销赃
    notes    NVARCHAR(200) NULL
) AS EDGE;

-- 2.11 Person -(目击/见证)-> Event
DROP TABLE IF EXISTS Witness;
CREATE TABLE Witness (
    id       INT IDENTITY PRIMARY KEY,
    notes    NVARCHAR(200) NULL
) AS EDGE;

-- 2.12 Person -(家庭/情感关系)-> Person
DROP TABLE IF EXISTS RelatedTo;
CREATE TABLE RelatedTo (
    id         INT IDENTITY PRIMARY KEY,
    relationship NVARCHAR(50) NOT NULL            -- 兄弟/情侣/夫妻/前姐夫/亲戚
) AS EDGE;

-- 2.13 Person -(冲突)-> Person
DROP TABLE IF EXISTS ConflictWith;
CREATE TABLE ConflictWith (
    id       INT IDENTITY PRIMARY KEY,
    reason   NVARCHAR(200) NULL
) AS EDGE;

-- 2.14 Person -(同伙)-> Person
DROP TABLE IF EXISTS CooperatesWith;
CREATE TABLE CooperatesWith (
    id       INT IDENTITY PRIMARY KEY,
    notes    NVARCHAR(200) NULL
) AS EDGE;

-- 2.15 CaseNode -(举报人)-> Person
DROP TABLE IF EXISTS ReportedBy;
CREATE TABLE ReportedBy (
    id          INT IDENTITY PRIMARY KEY,
    notes       NVARCHAR(200) NULL
) AS EDGE;

-- 2.16 CaseNode -(关联)-> CaseNode
DROP TABLE IF EXISTS ConnectedTo;
CREATE TABLE ConnectedTo (
    id          INT IDENTITY PRIMARY KEY,
    relation    NVARCHAR(100) NULL                -- 因果/同一证据/同一嫌疑人
) AS EDGE;

-- 2.17 Event -(发生于)-> Location
DROP TABLE IF EXISTS OccursAt;
CREATE TABLE OccursAt (
    id       INT IDENTITY PRIMARY KEY,
    time     NVARCHAR(100) NULL                   -- 时间描述
) AS EDGE;

-- 2.18 Item -(证据指向)-> CaseNode
DROP TABLE IF EXISTS EvidenceOf;
CREATE TABLE EvidenceOf (
    id       INT IDENTITY PRIMARY KEY,
    relevance NVARCHAR(200) NULL                  -- 关联说明
) AS EDGE;

-- 2.19 Person -(掩盖)-> CaseNode
DROP TABLE IF EXISTS CoversUp;
CREATE TABLE CoversUp (
    id       INT IDENTITY PRIMARY KEY,
    method   NVARCHAR(200) NULL
) AS EDGE;

-- 2.20 Person -(打电话/通讯)-> Person
DROP TABLE IF EXISTS CommunicatesWith;
CREATE TABLE CommunicatesWith (
    id       INT IDENTITY PRIMARY KEY,
    direction NVARCHAR(20) NULL,                  -- 拨出/接听/未接
    notes    NVARCHAR(200) NULL
) AS EDGE;
