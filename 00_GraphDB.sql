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

-- 3. 插入节点数据 (Node Data)
-- ============================================================

-- 3.1 人物
INSERT INTO Person (name, role, affiliation, status) VALUES
(N'张一昂', N'刑警/省厅专案组负责人', N'省公安厅', N'存活'),
(N'李茜',   N'省厅优秀新人/刑警',     N'省公安厅', N'存活'),
(N'方超',   N'劫匪/流窜犯',           NULL,        N'被捕'),
(N'刘直',   N'劫匪/方超同伙',         NULL,        N'被捕'),
(N'周荣',   N'荣城集团老板/富商',     N'荣城集团', N'被捕'),
(N'胡建仁', N'周荣心腹/马仔',         N'荣城集团', N'被捕'),
(N'朗博文', N'周荣同伙',              N'荣城集团', N'被捕'),
(N'朗博图', N'朗博文弟弟/留学生',     NULL,        N'被捕'),
(N'卢正',   N'三江口公安局副局长',    N'三江口公安局', N'死亡'),
(N'叶剑',   N'三江口公安局刑警',      N'三江口公安局', N'死亡'),
(N'陆一波', N'举报人/周淇男友',       NULL,        N'存活'),
(N'高栋',   N'省公安厅副厅长',        N'省公安厅', N'存活'),
(N'王瑞军', N'三江口公安局刑警',      N'三江口公安局', N'存活'),
(N'宋星',   N'三江口公安局民警',      N'三江口公安局', N'存活'),
(N'方庸',   N'东部新城管委会主任/贪官', N'东部新城管委会', N'被捕'),
(N'朱亦飞', N'文物贩子',              NULL,        N'死亡'),
(N'霍正',   N'朱亦飞手下/杀手',       NULL,        N'被捕'),
(N'刘背',   N'文物走私犯',            NULL,        N'死亡'),
(N'梅东',   N'洗钱中间人',            NULL,        N'被捕'),
(N'郑勇兵', N'销赃联系人',            NULL,        N'被捕'),
(N'杜聪',   N'周荣司机/手下',         N'荣城集团', N'存活'),
(N'李棚改', N'荣城集团保安队长',      N'荣城集团', N'死亡'),
(N'杨威',   N'路虎车主/林凯拜把兄弟', NULL,        N'存活'),
(N'林凯',   N'方庸前小舅子/混子',     NULL,        N'死亡'),
(N'蒋英',   N'送餐员/李峰妻子',       NULL,        N'存活'),
(N'李峰',   N'A级通缉犯/蒋英丈夫',    NULL,        N'被捕'),
(N'周淇',   N'周荣亲戚/陆一波女友',   N'荣城集团', N'存活'),
(N'齐振兴', N'三江口公安局领导',      N'三江口公安局', N'存活'),
(N'刚哥',   N'混混/黑车司机',         NULL,        N'在逃'),
(N'小毛',   N'混混/刚哥同伙',         NULL,        N'在逃'),
(N'陈法医', N'法医',                  N'三江口公安局', N'存活'),
(N'小飞',   N'三江口刀疤脸/涉案人员', NULL,        N'在逃');

-- 3.2 案件
INSERT INTO CaseNode (name, case_type, status, time_range, notes) VALUES
(N'卢正死亡案',       N'命案',   N'已结案', N'半年前', N'表面为交通意外，实为精心策划的谋杀(最终证实存在疑点)'),
(N'叶剑遇害案',       N'命案',   N'已结案', N'调查期间', N'叶剑在河边被杀，留下"一昂"字样的石头'),
(N'省城爆炸案',       N'抢劫',   N'已结案', N'五年前/近期', N'方超刘直引爆化粪池、抢劫金店，张一昂在现场捡到举报信'),
(N'信用社抢劫案',     N'抢劫',   N'已结案', N'近期', N'方超刘直行为古怪的抢劫案'),
(N'金店抢劫案',       N'抢劫',   N'已结案', N'近期', N'方超刘直乔装抢劫，刘直抱走不值钱摆设'),
(N'编钟交易案',       N'文物走私', N'已结案', N'调查期间', N'周荣通过朱亦飞购买青铜编钟，涉及文物走私'),
(N'梅东洗钱案',       N'洗钱',   N'已结案', N'调查期间', N'周荣通过梅东洗钱至海外'),
(N'方庸贪腐案',       N'贪腐',   N'已结案', N'调查期间', N'方庸被纪委带走，方超提供重要线索'),
(N'朗博图杀人案',     N'命案',   N'已结案', N'调查期间', N'朗博图承认杀害叶剑'),
(N'方超刘直系列抢劫案', N'抢劫', N'已结案', N'跨区域', N'涵盖省城爆炸、金店抢劫、周荣庄园抢劫等');

-- 3.3 组织
INSERT INTO Organization (name, org_type) VALUES
(N'省公安厅',              N'公安机关'),
(N'三江口公安局',          N'公安机关'),
(N'荣城集团',              N'企业'),
(N'东部新城管委会',        N'政府'),
(N'枫林晚酒店',            N'企业'),
(N'三江口日报',            N'媒体'),
(N'朱亦飞文物贩卖团伙',    N'犯罪团伙');

-- 3.4 地点
INSERT INTO Location (name, location_type, city) VALUES
(N'三江口',           N'城市', N'三江口'),
(N'省城',             N'城市', N'省城'),
(N'枫林晚酒店',       N'建筑', N'三江口'),
(N'周荣庄园',         N'建筑', N'三江口'),
(N'废品回收站',       N'建筑', N'三江口'),
(N'方庸住宅',         N'建筑', N'三江口'),
(N'郑勇兵住所',       N'建筑', N'三江口'),
(N'荣城集团大楼',     N'建筑', N'三江口'),
(N'小树林河边',       N'野外', N'三江口'),
(N'东部新城',         N'区域', N'三江口'),
(N'三江口火车站',     N'交通枢纽', N'三江口'),
(N'三江口长途汽车站', N'交通枢纽', N'三江口'),
(N'高速公路服务区',   N'交通枢纽', N'三江口'),
(N'废弃工厂',         N'建筑', N'三江口'),
(N'涵洞',             N'野外', N'三江口'),
(N'枯井',             N'野外', N'三江口');

-- 3.5 物品/证据
INSERT INTO Item (name, item_type, is_evidence) VALUES
(N'残缺举报信',       N'信件', 1),
(N'限量电子表',       N'证据', 1),
(N'假玉财神',         N'赃物', 1),
(N'青铜编钟',         N'文物', 1),
(N'朗博文手机',       N'证据', 1),
(N'一百万美元',        N'财物', 1),
(N'路虎车',           N'财物', 0),
(N'破夏利车',         N'财物', 1),
(N'水疗贵宾卡',       N'证据', 1),
(N'手枪',             N'凶器', 1),
(N'梅东钱箱',         N'证据', 1),
(N'带刀的车',         N'凶器', 1),
(N'叶剑石头(写有一昂)', N'证据', 1),
(N'方庸收藏文玩字画',  N'赃物', 1),
(N'化粪池引爆装置',   N'证据', 1),
(N'刘背手表',         N'证据', 1),
(N'荣城集团奔驰车',   N'财物', 0),
(N'黑色出租车(改装夏利)', N'财物', 1);

-- 3.6 关键事件
INSERT INTO Event (name, event_type) VALUES
(N'方超刘直引爆化粪池',           N'犯罪'),
(N'方超刘直乔装抢劫金店',         N'犯罪'),
(N'张一昂捡到举报信',             N'发现'),
(N'叶剑写下"一昂"后死亡',         N'死亡'),
(N'叶剑重新查看卢正车祸视频',     N'调查'),
(N'张一昂火车站抓捕蒋英李峰',     N'抓捕'),
(N'李茜假扮物业试探刘背',         N'调查'),
(N'方超刘直抢劫周荣庄园百万美元', N'犯罪'),
(N'霍正与刘背火并',               N'死亡'),
(N'梅东被捕',                     N'抓捕'),
(N'宋星被方超刘直扔下楼',         N'犯罪'),
(N'张一昂中弹受伤',               N'受伤'),
(N'朗博图承认杀害叶剑',           N'认罪'),
(N'方庸被纪委带走',               N'抓捕'),
(N'刚哥小毛抢走路虎和美元',       N'犯罪'),
(N'朱亦飞坠崖身亡',               N'死亡'),
(N'杜聪刺伤周荣',                 N'犯罪'),
(N'朗博文带刀车撞死叶剑(伪供)',   N'犯罪'),
(N'周荣庄园枪战',                 N'抓捕'),
(N'张一昂霍正医院互掐',           N'冲突'),
(N'周荣自虐冲进鱼缸',             N'事件'),
(N'陆一波寄出举报信',             N'关键行动'),
(N'张一昂被调离刑侦一线',         N'关键行动'),
(N'刘背偷编钟离开',               N'犯罪'),
(N'方超刘直困于枯井三天',         N'事件'),
(N'霍正假装病人被注射青霉素',     N'事件');

-- 4. 插入边数据 (Edge Data)
-- ============================================================
-- 注意: $from_id / $to_id 通过子查询从节点表获取

-- 4.1 任职关系 WorksAt (Person -> Organization)
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'刑警'
FROM Person p, Organization o WHERE p.name = N'张一昂'    AND o.name = N'省公安厅';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'刑警'
FROM Person p, Organization o WHERE p.name = N'李茜'      AND o.name = N'省公安厅';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'副厅长'
FROM Person p, Organization o WHERE p.name = N'高栋'      AND o.name = N'省公安厅';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'刑警'
FROM Person p, Organization o WHERE p.name = N'叶剑'      AND o.name = N'三江口公安局';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'刑警'
FROM Person p, Organization o WHERE p.name = N'王瑞军'    AND o.name = N'三江口公安局';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'民警'
FROM Person p, Organization o WHERE p.name = N'宋星'      AND o.name = N'三江口公安局';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'副局长'
FROM Person p, Organization o WHERE p.name = N'卢正'      AND o.name = N'三江口公安局';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'领导'
FROM Person p, Organization o WHERE p.name = N'齐振兴'    AND o.name = N'三江口公安局';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'法医'
FROM Person p, Organization o WHERE p.name = N'陈法医'    AND o.name = N'三江口公安局';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'老板'
FROM Person p, Organization o WHERE p.name = N'周荣'      AND o.name = N'荣城集团';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'心腹'
FROM Person p, Organization o WHERE p.name = N'胡建仁'    AND o.name = N'荣城集团';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'同伙'
FROM Person p, Organization o WHERE p.name = N'朗博文'    AND o.name = N'荣城集团';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'司机'
FROM Person p, Organization o WHERE p.name = N'杜聪'      AND o.name = N'荣城集团';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'保安队长'
FROM Person p, Organization o WHERE p.name = N'李棚改'    AND o.name = N'荣城集团';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'亲戚/员工'
FROM Person p, Organization o WHERE p.name = N'周淇'      AND o.name = N'荣城集团';
INSERT INTO WorksAt ($from_id, $to_id, position)
SELECT p.$node_id, o.$node_id, N'主任'
FROM Person p, Organization o WHERE p.name = N'方庸'      AND o.name = N'东部新城管委会';

-- 4.2 上下级关系 SubordinateOf (Person -> Person)
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'专案组下属'
FROM Person p1, Person p2 WHERE p1.name = N'李茜'   AND p2.name = N'张一昂';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'专案组下属'
FROM Person p1, Person p2 WHERE p1.name = N'宋星'   AND p2.name = N'张一昂';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'副厅长管辖'
FROM Person p1, Person p2 WHERE p1.name = N'张一昂' AND p2.name = N'高栋';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'副局长管辖'
FROM Person p1, Person p2 WHERE p1.name = N'叶剑'   AND p2.name = N'卢正';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'公安局领导'
FROM Person p1, Person p2 WHERE p1.name = N'王瑞军' AND p2.name = N'齐振兴';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'心腹马仔'
FROM Person p1, Person p2 WHERE p1.name = N'胡建仁' AND p2.name = N'周荣';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'保安队长'
FROM Person p1, Person p2 WHERE p1.name = N'李棚改' AND p2.name = N'周荣';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'司机'
FROM Person p1, Person p2 WHERE p1.name = N'杜聪'   AND p2.name = N'周荣';
INSERT INTO SubordinateOf ($from_id, $to_id, description)
SELECT p1.$node_id, p2.$node_id, N'杀手马仔'
FROM Person p1, Person p2 WHERE p1.name = N'霍正'   AND p2.name = N'朱亦飞';

-- 4.3 调查关系 Investigates (Person -> CaseNode)
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'主办'
FROM Person p, CaseNode c WHERE p.name = N'张一昂' AND c.name = N'卢正死亡案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'主办'
FROM Person p, CaseNode c WHERE p.name = N'张一昂' AND c.name = N'叶剑遇害案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'主办'
FROM Person p, CaseNode c WHERE p.name = N'张一昂' AND c.name = N'编钟交易案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'主办'
FROM Person p, CaseNode c WHERE p.name = N'张一昂' AND c.name = N'梅东洗钱案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'主办'
FROM Person p, CaseNode c WHERE p.name = N'张一昂' AND c.name = N'方超刘直系列抢劫案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'主办'
FROM Person p, CaseNode c WHERE p.name = N'张一昂' AND c.name = N'朗博图杀人案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'协办'
FROM Person p, CaseNode c WHERE p.name = N'李茜'   AND c.name = N'卢正死亡案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'协办'
FROM Person p, CaseNode c WHERE p.name = N'李茜'   AND c.name = N'叶剑遇害案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'协办'
FROM Person p, CaseNode c WHERE p.name = N'王瑞军' AND c.name = N'叶剑遇害案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'协办'
FROM Person p, CaseNode c WHERE p.name = N'宋星'   AND c.name = N'叶剑遇害案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'协办'
FROM Person p, CaseNode c WHERE p.name = N'宋星'   AND c.name = N'方超刘直系列抢劫案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'曾被调查'
FROM Person p, CaseNode c WHERE p.name = N'叶剑'   AND c.name = N'卢正死亡案';
INSERT INTO Investigates ($from_id, $to_id, role)
SELECT p.$node_id, c.$node_id, N'纪委调查'
FROM Person p, CaseNode c WHERE p.name = N'方庸'   AND c.name = N'方庸贪腐案';

-- 4.4 嫌疑人关系 SuspectOf (Person -> CaseNode)
INSERT INTO SuspectOf ($from_id, $to_id, degree, notes)
SELECT p.$node_id, c.$node_id, N'已排除', N'叶剑留下"一昂"字迹，曾短暂被怀疑'
FROM Person p, CaseNode c WHERE p.name = N'张一昂' AND c.name = N'叶剑遇害案';
INSERT INTO SuspectOf ($from_id, $to_id, degree, notes)
SELECT p.$node_id, c.$node_id, N'重大嫌疑', N'最初伪供认罪'
FROM Person p, CaseNode c WHERE p.name = N'朗博文' AND c.name = N'叶剑遇害案';
INSERT INTO SuspectOf ($from_id, $to_id, degree, notes)
SELECT p.$node_id, c.$node_id, N'已确认', N'最终认罪'
FROM Person p, CaseNode c WHERE p.name = N'朗博图' AND c.name = N'叶剑遇害案';
INSERT INTO SuspectOf ($from_id, $to_id, degree, notes)
SELECT p.$node_id, c.$node_id, N'重大嫌疑', N'卢正死亡案背后可能涉及'
FROM Person p, CaseNode c WHERE p.name = N'周荣'   AND c.name = N'卢正死亡案';
INSERT INTO SuspectOf ($from_id, $to_id, degree, notes)
SELECT p.$node_id, c.$node_id, N'已确认', N'方庸被纪委调查'
FROM Person p, CaseNode c WHERE p.name = N'方庸'   AND c.name = N'方庸贪腐案';

-- 4.5 作案人关系 PerpetratorOf (Person -> CaseNode)
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'朗博图' AND c.name = N'朗博图杀人案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'方超'   AND c.name = N'省城爆炸案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'刘直'   AND c.name = N'省城爆炸案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'方超'   AND c.name = N'金店抢劫案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'刘直'   AND c.name = N'金店抢劫案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'方超'   AND c.name = N'方超刘直系列抢劫案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'刘直'   AND c.name = N'方超刘直系列抢劫案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'方超'   AND c.name = N'信用社抢劫案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'刘直'   AND c.name = N'信用社抢劫案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'梅东'   AND c.name = N'梅东洗钱案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 0
FROM Person p, CaseNode c WHERE p.name = N'周荣'   AND c.name = N'编钟交易案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 0
FROM Person p, CaseNode c WHERE p.name = N'周荣'   AND c.name = N'梅东洗钱案';
INSERT INTO PerpetratorOf ($from_id, $to_id, confession)
SELECT p.$node_id, c.$node_id, 1
FROM Person p, CaseNode c WHERE p.name = N'方庸'   AND c.name = N'方庸贪腐案';

-- 4.6 受害人关系 VictimOf (Person -> CaseNode)
INSERT INTO VictimOf ($from_id, $to_id, cause)
SELECT p.$node_id, c.$node_id, N'被车撞死(伪装成交通意外)'
FROM Person p, CaseNode c WHERE p.name = N'卢正'   AND c.name = N'卢正死亡案';
INSERT INTO VictimOf ($from_id, $to_id, cause)
SELECT p.$node_id, c.$node_id, N'被绑刀的车撞伤后力竭身亡'
FROM Person p, CaseNode c WHERE p.name = N'叶剑'   AND c.name = N'叶剑遇害案';
INSERT INTO VictimOf ($from_id, $to_id, cause)
SELECT p.$node_id, c.$node_id, N'被霍正杀害'
FROM Person p, CaseNode c WHERE p.name = N'刘背'   AND c.name = N'编钟交易案';
INSERT INTO VictimOf ($from_id, $to_id, cause)
SELECT p.$node_id, c.$node_id, N'被方超刘直遗忘在后备箱窒息死亡'
FROM Person p, CaseNode c WHERE p.name = N'林凯'   AND c.name = N'方超刘直系列抢劫案';
INSERT INTO VictimOf ($from_id, $to_id, cause)
SELECT p.$node_id, c.$node_id, N'坠崖身亡'
FROM Person p, CaseNode c WHERE p.name = N'朱亦飞' AND c.name = N'编钟交易案';

-- 4.7 家庭/情感关系 RelatedTo (Person -> Person)
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p1.$node_id, p2.$node_id, N'兄弟'
FROM Person p1, Person p2 WHERE p1.name = N'朗博文' AND p2.name = N'朗博图';
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p1.$node_id, p2.$node_id, N'情侣'
FROM Person p1, Person p2 WHERE p1.name = N'陆一波' AND p2.name = N'周淇';
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p1.$node_id, p2.$node_id, N'夫妻'
FROM Person p1, Person p2 WHERE p1.name = N'蒋英'   AND p2.name = N'李峰';
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p1.$node_id, p2.$node_id, N'前姐夫'
FROM Person p1, Person p2 WHERE p1.name = N'方庸'   AND p2.name = N'林凯';
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p1.$node_id, p2.$node_id, N'亲戚'
FROM Person p1, Person p2 WHERE p1.name = N'周荣'   AND p2.name = N'周淇';
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p1.$node_id, p2.$node_id, N'拜把兄弟'
FROM Person p1, Person p2 WHERE p1.name = N'杨威'   AND p2.name = N'林凯';

-- 4.8 同伙关系 CooperatesWith (Person -> Person)
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'抢劫搭档'
FROM Person p1, Person p2 WHERE p1.name = N'方超'   AND p2.name = N'刘直';
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'文物贩卖团伙'
FROM Person p1, Person p2 WHERE p1.name = N'朱亦飞' AND p2.name = N'霍正';
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'混混搭档'
FROM Person p1, Person p2 WHERE p1.name = N'刚哥'   AND p2.name = N'小毛';
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'老板与心腹'
FROM Person p1, Person p2 WHERE p1.name = N'周荣'   AND p2.name = N'胡建仁';
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'销赃关系'
FROM Person p1, Person p2 WHERE p1.name = N'方超'   AND p2.name = N'郑勇兵';
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'洗钱合作'
FROM Person p1, Person p2 WHERE p1.name = N'周荣'   AND p2.name = N'梅东';
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'编钟交易'
FROM Person p1, Person p2 WHERE p1.name = N'周荣'   AND p2.name = N'朱亦飞';
INSERT INTO CooperatesWith ($from_id, $to_id, notes)
SELECT p1.$node_id, p2.$node_id, N'编钟运输'
FROM Person p1, Person p2 WHERE p1.name = N'刘背'   AND p2.name = N'朱亦飞';

-- 4.9 冲突关系 ConflictWith (Person -> Person)
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'正邪对立'
FROM Person p1, Person p2 WHERE p1.name = N'张一昂' AND p2.name = N'周荣';
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'抢劫与被抢'
FROM Person p1, Person p2 WHERE p1.name = N'方超'   AND p2.name = N'周荣';
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'抢劫与被抢'
FROM Person p1, Person p2 WHERE p1.name = N'刘直'   AND p2.name = N'周荣';
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'霍正杀死刘背'
FROM Person p1, Person p2 WHERE p1.name = N'霍正'   AND p2.name = N'刘背';
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'杜聪刺伤周荣'
FROM Person p1, Person p2 WHERE p1.name = N'杜聪'   AND p2.name = N'周荣';
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'欺骗编钟价格'
FROM Person p1, Person p2 WHERE p1.name = N'周荣'   AND p2.name = N'朱亦飞';
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'兄弟冲突-朗博文被周荣利用朗博图施压，两人貌合神离'
FROM Person p1, Person p2 WHERE p1.name = N'朗博文' AND p2.name = N'周荣';

-- 4.10 通讯关系 CommunicatesWith (Person -> Person)
INSERT INTO CommunicatesWith ($from_id, $to_id, direction, notes)
SELECT p1.$node_id, p2.$node_id, N'未接通', N'叶剑遇害当晚'
FROM Person p1, Person p2 WHERE p1.name = N'张一昂' AND p2.name = N'叶剑';
INSERT INTO CommunicatesWith ($from_id, $to_id, direction, notes)
SELECT p1.$node_id, p2.$node_id, N'拨出', N'陆一波求救电话'
FROM Person p1, Person p2 WHERE p1.name = N'陆一波' AND p2.name = N'张一昂';
INSERT INTO CommunicatesWith ($from_id, $to_id, direction, notes)
SELECT p1.$node_id, p2.$node_id, N'拨出', N'高厅下达破案令'
FROM Person p1, Person p2 WHERE p1.name = N'高栋'   AND p2.name = N'张一昂';
INSERT INTO CommunicatesWith ($from_id, $to_id, direction, notes)
SELECT p1.$node_id, p2.$node_id, N'拨出', N'方超勒索周荣交还手机'
FROM Person p1, Person p2 WHERE p1.name = N'方超'   AND p2.name = N'周荣';

-- 4.11 物品拥有关系 Owns (Person -> Item)
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'限量版电子表'
FROM Person p, Item i WHERE p.name = N'陆一波' AND i.name = N'限量电子表';
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'荣城集团老板'
FROM Person p, Item i WHERE p.name = N'周荣'   AND i.name = N'朗博文手机';
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'购车'
FROM Person p, Item i WHERE p.name = N'杨威'   AND i.name = N'路虎车';
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'购车'
FROM Person p, Item i WHERE p.name = N'方超'   AND i.name = N'破夏利车';
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'收藏'
FROM Person p, Item i WHERE p.name = N'方庸'   AND i.name = N'方庸收藏文玩字画';
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'刘背随身携带'
FROM Person p, Item i WHERE p.name = N'刘背'   AND i.name = N'刘背手表';
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'公司车辆'
FROM Person p, Item i WHERE p.name = N'周荣'   AND i.name = N'荣城集团奔驰车';

-- 4.12 发现关系 Found (Person -> Item)
INSERT INTO Found ($from_id, $to_id, scene, notes)
SELECT p.$node_id, i.$node_id, N'爆炸案现场', N'残缺信件'
FROM Person p, Item i WHERE p.name = N'张一昂' AND i.name = N'残缺举报信';
INSERT INTO Found ($from_id, $to_id, scene, notes)
SELECT p.$node_id, i.$node_id, N'卢正车祸视频', N'发现路人佩戴限量手表'
FROM Person p, Item i WHERE p.name = N'叶剑'   AND i.name = N'限量电子表';
INSERT INTO Found ($from_id, $to_id, scene, notes)
SELECT p.$node_id, i.$node_id, N'叶剑遇害现场', N'写有"一昂"二字的石头'
FROM Person p, Item i WHERE p.name = N'王瑞军' AND i.name = N'叶剑石头(写有一昂)';

-- 4.13 物品流转关系 TransferredTo (Item -> Person, 从...流转至...)
-- 注意: 边方向描述的是物品被转移至某人
INSERT INTO TransferredTo ($from_id, $to_id, method, notes)
SELECT i.$node_id, p.$node_id, N'销赃', N'郑勇兵处销赃'
FROM Item i, Person p WHERE i.name = N'假玉财神' AND p.name = N'郑勇兵';
INSERT INTO TransferredTo ($from_id, $to_id, method, notes)
SELECT i.$node_id, p.$node_id, N'交易', N'朱亦飞卖给周荣'
FROM Item i, Person p WHERE i.name = N'青铜编钟' AND p.name = N'周荣';
INSERT INTO TransferredTo ($from_id, $to_id, method, notes)
SELECT i.$node_id, p.$node_id, N'抢劫', N'方超刘直抢走'
FROM Item i, Person p WHERE i.name = N'一百万美元' AND p.name = N'方超';
INSERT INTO TransferredTo ($from_id, $to_id, method, notes)
SELECT i.$node_id, p.$node_id, N'抢劫', N'方超刘直抢走路虎'
FROM Item i, Person p WHERE i.name = N'路虎车' AND p.name = N'方超';
INSERT INTO TransferredTo ($from_id, $to_id, method, notes)
SELECT i.$node_id, p.$node_id, N'抢劫', N'刚哥小毛从方超刘直处抢走'
FROM Item i, Person p WHERE i.name = N'一百万美元' AND p.name = N'刚哥';
INSERT INTO TransferredTo ($from_id, $to_id, method, notes)
SELECT i.$node_id, p.$node_id, N'抢劫', N'刚哥小毛抢走'
FROM Item i, Person p WHERE i.name = N'路虎车' AND p.name = N'刚哥';

-- 4.14 目击关系 Witness (Person -> Event)
INSERT INTO Witness ($from_id, $to_id, notes)
SELECT p.$node_id, e.$node_id, N'迷迷糊糊中目睹'
FROM Person p, Event e WHERE p.name = N'李茜' AND e.name = N'方超刘直抢劫周荣庄园百万美元';
INSERT INTO Witness ($from_id, $to_id, notes)
SELECT p.$node_id, e.$node_id, NULL
FROM Person p, Event e WHERE p.name = N'张一昂' AND e.name = N'张一昂捡到举报信';
INSERT INTO Witness ($from_id, $to_id, notes)
SELECT p.$node_id, e.$node_id, NULL
FROM Person p, Event e WHERE p.name = N'叶剑'   AND e.name = N'叶剑重新查看卢正车祸视频';
INSERT INTO Witness ($from_id, $to_id, notes)
SELECT p.$node_id, e.$node_id, N'抓获梅东'
FROM Person p, Event e WHERE p.name = N'张一昂' AND e.name = N'梅东被捕';

-- 4.15 案件关联 ConnectedTo (CaseNode -> CaseNode)
INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'因果链-叶剑调查卢正之死后被灭口'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'叶剑遇害案' AND c2.name = N'卢正死亡案';
INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'同一证据-举报信在同一现场'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'省城爆炸案' AND c2.name = N'卢正死亡案';
INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'同一作案人'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'省城爆炸案' AND c2.name = N'金店抢劫案';
INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'同一作案人'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'信用社抢劫案' AND c2.name = N'方超刘直系列抢劫案';
INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'周荣同时涉案'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'编钟交易案' AND c2.name = N'梅东洗钱案';
INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'因果链-朗博图为叶剑案真凶'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'朗博图杀人案' AND c2.name = N'叶剑遇害案';

-- 4.16 举报关系 ReportedBy (CaseNode -> Person)
INSERT INTO ReportedBy ($from_id, $to_id, notes)
SELECT c.$node_id, p.$node_id, N'陆一波寄出举报信'
FROM CaseNode c, Person p WHERE c.name = N'卢正死亡案' AND p.name = N'陆一波';
INSERT INTO ReportedBy ($from_id, $to_id, notes)
SELECT c.$node_id, p.$node_id, N'方超提供方庸贪腐线索'
FROM CaseNode c, Person p WHERE c.name = N'方庸贪腐案' AND p.name = N'方超';
INSERT INTO ReportedBy ($from_id, $to_id, notes)
SELECT c.$node_id, p.$node_id, N'周淇匿名报警'
FROM CaseNode c, Person p WHERE c.name = N'编钟交易案' AND p.name = N'周淇';

-- 4.17 证据指向 EvidenceOf (Item -> CaseNode)
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'举报卢正死亡非意外'
FROM Item i, CaseNode c WHERE i.name = N'残缺举报信' AND c.name = N'卢正死亡案';
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'出现在卢正车祸现场，证明此人与卢正之死有关'
FROM Item i, CaseNode c WHERE i.name = N'限量电子表' AND c.name = N'卢正死亡案';
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'刘背手表与叶剑生前浏览的手表一致'
FROM Item i, CaseNode c WHERE i.name = N'刘背手表' AND c.name = N'叶剑遇害案';
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'叶剑死前留言'
FROM Item i, CaseNode c WHERE i.name = N'叶剑石头(写有一昂)' AND c.name = N'叶剑遇害案';
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'抢劫周荣所得'
FROM Item i, CaseNode c WHERE i.name = N'一百万美元' AND c.name = N'方超刘直系列抢劫案';
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'证明朗博文/朗博图涉案'
FROM Item i, CaseNode c WHERE i.name = N'朗博文手机' AND c.name = N'叶剑遇害案';
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'凶器'
FROM Item i, CaseNode c WHERE i.name = N'带刀的车' AND c.name = N'叶剑遇害案';
INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'枫林晚水疗卡引出调查方向'
FROM Item i, CaseNode c WHERE i.name = N'水疗贵宾卡' AND c.name = N'叶剑遇害案';

-- 4.18 位于关系 LocatedIn (Event/Person/Case -> Location)
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT e.$node_id, l.$node_id, N'叶剑陈尸地点'
FROM Event e, Location l WHERE e.name = N'叶剑写下"一昂"后死亡' AND l.name = N'小树林河边';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'周荣住所'
FROM Person p, Location l WHERE p.name = N'周荣'   AND l.name = N'周荣庄园';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'方庸住所'
FROM Person p, Location l WHERE p.name = N'方庸'   AND l.name = N'方庸住宅';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT e.$node_id, l.$node_id, N'作案地点'
FROM Event e, Location l WHERE e.name = N'方超刘直抢劫周荣庄园百万美元' AND l.name = N'周荣庄园';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT e.$node_id, l.$node_id, N'抓捕地点'
FROM Event e, Location l WHERE e.name = N'张一昂火车站抓捕蒋英李峰' AND l.name = N'三江口火车站';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT e.$node_id, l.$node_id, N'推测在刘背落脚点（郑勇兵住所）'
FROM Event e, Location l WHERE e.name = N'霍正与刘背火并' AND l.name = N'郑勇兵住所';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT e.$node_id, l.$node_id, N'方超刘直被困'
FROM Event e, Location l WHERE e.name = N'方超刘直困于枯井三天' AND l.name = N'枯井';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT e.$node_id, l.$node_id, N'刚哥杜聪对峙'
FROM Event e, Location l WHERE e.name = N'杜聪刺伤周荣' AND l.name = N'废弃工厂';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'林凯的车停留在高速服务区'
FROM Person p, Location l WHERE p.name = N'林凯' AND l.name = N'高速公路服务区';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'方超在高速附近活动'
FROM Person p, Location l WHERE p.name = N'方超' AND l.name = N'高速公路服务区';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'刘直在高速附近活动'
FROM Person p, Location l WHERE p.name = N'刘直' AND l.name = N'高速公路服务区';
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'方庸想去高速服务区找林凯'
FROM Person p, Location l WHERE p.name = N'方庸' AND l.name = N'高速公路服务区';

-- 4.19 掩盖关系 CoversUp (Person -> CaseNode)
INSERT INTO CoversUp ($from_id, $to_id, method)
SELECT p.$node_id, c.$node_id, N'朗博文伪供自己杀人，掩盖弟弟朗博图'
FROM Person p, CaseNode c WHERE p.name = N'朗博文' AND c.name = N'叶剑遇害案';
INSERT INTO CoversUp ($from_id, $to_id, method)
SELECT p.$node_id, c.$node_id, N'试图掩盖卢正死亡真相'
FROM Person p, CaseNode c WHERE p.name = N'周荣'   AND c.name = N'卢正死亡案';
INSERT INTO CoversUp ($from_id, $to_id, method)
SELECT p.$node_id, c.$node_id, N'销毁朗博文手机'
FROM Person p, CaseNode c WHERE p.name = N'周荣'   AND c.name = N'叶剑遇害案';

-- 4.20 案件发生于 OccursAt (Event -> Location)
INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'省城作案期间'
FROM Event e, Location l WHERE e.name = N'方超刘直引爆化粪池' AND l.name = N'省城';
INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'周荣庄园交易当日'
FROM Event e, Location l WHERE e.name = N'张一昂中弹受伤' AND l.name = N'周荣庄园';
INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'张一昂病房'
FROM Event e, Location l WHERE e.name = N'张一昂霍正医院互掐' AND l.name = N'三江口';

-- ============================================================
-- 4.21 新增孤立节点关系补充
-- ============================================================

-- Event节点关系
INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'同一作案人系列'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'金店抢劫案' AND c2.name = N'省城爆炸案';

INSERT INTO ConnectedTo ($from_id, $to_id, relation)
SELECT c1.$node_id, c2.$node_id, N'同一作案人'
FROM CaseNode c1, CaseNode c2 WHERE c1.name = N'信用社抢劫案' AND c2.name = N'金店抢劫案';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'金店抢劫'
FROM Event e, Location l WHERE e.name = N'方超刘直乔装抢劫金店' AND l.name = N'省城';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'调查刘背'
FROM Event e, Location l WHERE e.name = N'李茜假扮物业试探刘背' AND l.name = N'郑勇兵住所';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'朗博图认罪'
FROM Event e, Location l WHERE e.name = N'朗博图承认杀害叶剑' AND l.name = N'三江口';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'方庸落马'
FROM Event e, Location l WHERE e.name = N'方庸被纪委带走' AND l.name = N'三江口';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'刚哥小毛抢劫'
FROM Event e, Location l WHERE e.name = N'刚哥小毛抢走路虎和美元' AND l.name = N'废品回收站';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'朱亦飞身亡'
FROM Event e, Location l WHERE e.name = N'朱亦飞坠崖身亡' AND l.name = N'三江口';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'周荣庄园'
FROM Event e, Location l WHERE e.name = N'周荣庄园枪战' AND l.name = N'周荣庄园';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'周荣庄园'
FROM Event e, Location l WHERE e.name = N'周荣自虐冲进鱼缸' AND l.name = N'周荣庄园';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'举报信寄出'
FROM Event e, Location l WHERE e.name = N'陆一波寄出举报信' AND l.name = N'省城';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'张一昂调离'
FROM Event e, Location l WHERE e.name = N'张一昂被调离刑侦一线' AND l.name = N'省城';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'刘背偷编钟'
FROM Event e, Location l WHERE e.name = N'刘背偷编钟离开' AND l.name = N'三江口';

INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'霍正伪装'
FROM Event e, Location l WHERE e.name = N'霍正假装病人被注射青霉素' AND l.name = N'三江口';

-- Item节点关系
INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'霍正使用手枪'
FROM Person p, Item i WHERE p.name = N'霍正' AND i.name = N'手枪';

INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'梅东的钱箱'
FROM Person p, Item i WHERE p.name = N'梅东' AND i.name = N'梅东钱箱';

INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'方超刘直制作引爆装置'
FROM Person p, Item i WHERE p.name = N'方超' AND i.name = N'化粪池引爆装置';

INSERT INTO Owns ($from_id, $to_id, description)
SELECT p.$node_id, i.$node_id, N'刚哥小毛的黑出租'
FROM Person p, Item i WHERE p.name = N'刚哥' AND i.name = N'黑色出租车(改装夏利)';

INSERT INTO EvidenceOf ($from_id, $to_id, relevance)
SELECT i.$node_id, c.$node_id, N'省城爆炸案作案工具'
FROM Item i, CaseNode c WHERE i.name = N'化粪池引爆装置' AND c.name = N'省城爆炸案';

-- Location节点关系
INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'叶剑遇害当晚去过枫林晚'
FROM Person p, Location l WHERE p.name = N'叶剑' AND l.name = N'枫林晚酒店';

INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'张一昂调查枫林晚'
FROM Person p, Location l WHERE p.name = N'张一昂' AND l.name = N'枫林晚酒店';

INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'刚哥小毛的废品回收站'
FROM Person p, Location l WHERE p.name = N'刚哥' AND l.name = N'废品回收站';

INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'荣城集团总部'
FROM Person p, Location l WHERE p.name = N'周荣' AND l.name = N'荣城集团大楼';

INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'方庸在东部新城管委会'
FROM Person p, Location l WHERE p.name = N'方庸' AND l.name = N'东部新城';

INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'方超刘直在长途汽车站'
FROM Person p, Location l WHERE p.name = N'方超' AND l.name = N'三江口长途汽车站';

INSERT INTO LocatedIn ($from_id, $to_id, description)
SELECT p.$node_id, l.$node_id, N'蒋英李峰在长途汽车站'
FROM Person p, Location l WHERE p.name = N'蒋英' AND l.name = N'三江口长途汽车站';

-- Organization节点关系
INSERT INTO Owns ($from_id, $to_id, description)
SELECT o.$node_id, l.$node_id, N'枫林晚酒店'
FROM Organization o, Location l WHERE o.name = N'枫林晚酒店' AND l.name = N'枫林晚酒店';

INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p.$node_id, o.$node_id, N'方超刘直混入三江口日报'
FROM Person p, Organization o WHERE p.name = N'方超' AND o.name = N'三江口日报';
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p.$node_id, o.$node_id, N'方超刘直混入三江口日报'
FROM Person p, Organization o WHERE p.name = N'刘直' AND o.name = N'三江口日报';

INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p.$node_id, o.$node_id, N'朱亦飞是该团伙成员'
FROM Person p, Organization o WHERE p.name = N'朱亦飞' AND o.name = N'朱亦飞文物贩卖团伙';

INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p.$node_id, o.$node_id, N'刘背是该团伙成员'
FROM Person p, Organization o WHERE p.name = N'刘背' AND o.name = N'朱亦飞文物贩卖团伙';

-- Person节点关系
INSERT INTO RelatedTo ($from_id, $to_id, relationship) SELECT p1.$node_id, p2.$node_id, N'李棚改拆掉小飞硬盘' FROM Person p1, Person p2 WHERE p1.name = N'李棚改' AND p2.name = N'小飞';
INSERT INTO RelatedTo ($from_id, $to_id, relationship) SELECT p1.$node_id, p2.$node_id, N'小飞与刚哥小毛认识' FROM Person p1, Person p2 WHERE p1.name = N'小飞' AND p2.name = N'刚哥';
INSERT INTO RelatedTo ($from_id, $to_id, relationship) SELECT p1.$node_id, p2.$node_id, N'小飞与刚哥小毛认识' FROM Person p1, Person p2 WHERE p1.name = N'小飞' AND p2.name = N'小毛';

-- 涵洞节点关系补充
INSERT INTO LocatedIn ($from_id, $to_id, description) SELECT p.$node_id, l.$node_id, N'刚哥小毛躲藏地点' FROM Person p, Location l WHERE p.name = N'刚哥' AND l.name = N'涵洞';
INSERT INTO LocatedIn ($from_id, $to_id, description) SELECT p.$node_id, l.$node_id, N'小毛躲藏地点' FROM Person p, Location l WHERE p.name = N'小毛' AND l.name = N'涵洞';
INSERT INTO LocatedIn ($from_id, $to_id, description) SELECT p.$node_id, l.$node_id, N'李棚改失足地点' FROM Person p, Location l WHERE p.name = N'李棚改' AND l.name = N'涵洞';
INSERT INTO RelatedTo ($from_id, $to_id, relationship) SELECT p.$node_id, l.$node_id, N'杜聪在涵洞外埋伏' FROM Person p, Location l WHERE p.name = N'杜聪' AND l.name = N'涵洞';

-- 朗博文带刀车撞死叶剑(伪供) 节点关系补充
INSERT INTO OccursAt ($from_id, $to_id, time)
SELECT e.$node_id, l.$node_id, N'朗博文伪供称在此处撞死叶剑'
FROM Event e, Location l WHERE e.name = N'朗博文带刀车撞死叶剑(伪供)' AND l.name = N'小树林河边';

INSERT INTO Witness ($from_id, $to_id, notes)
SELECT p.$node_id, e.$node_id, N'朗博文伪供自己作案，掩盖弟弟朗博图'
FROM Person p, Event e WHERE p.name = N'朗博文' AND e.name = N'朗博文带刀车撞死叶剑(伪供)';

INSERT INTO Witness ($from_id, $to_id, notes)
SELECT p.$node_id, e.$node_id, N'朗博图实际用带刀的车杀死叶剑，朗博文的伪供基于其描述'
FROM Person p, Event e WHERE p.name = N'朗博图' AND e.name = N'朗博文带刀车撞死叶剑(伪供)';

-- ============================================================
-- 5. 示例查询 (Sample Queries)
-- ============================================================

-- 5.1 查询某案件所有相关人员
SELECT p.name, p.role, i.$from_id, i.$to_id
FROM Person p,
     Investigates i,
     CaseNode c
WHERE MATCH(p-(i)->c)
  AND c.name = N'叶剑遇害案';

-- 5.2 查询某人的所有同伙
SELECT p2.name AS 同伙, c.notes
FROM Person p1, CooperatesWith c, Person p2
WHERE MATCH(p1-(c)->p2)
  AND p1.name = N'周荣';

-- 5.3 两跳查询: 谁的手机出现在哪个案件现场?
SELECT p.name AS 持有者, i.name AS 物品, c.name AS 关联案件, ev.relevance
FROM Person p, Owns o, Item i, EvidenceOf ev, CaseNode c
WHERE MATCH(p-(o)->i-(ev)->c)
  AND i.name = N'限量电子表';

-- 5.4 案件关联链
SELECT c1.name AS 案件A, cn.relation AS 关联方式, c2.name AS 案件B
FROM CaseNode c1, ConnectedTo cn, CaseNode c2
WHERE MATCH(c1-(cn)->c2);

-- 5.5 某地点发生的所有事件
SELECT e.name AS 事件, o.time AS 时间
FROM Event e, OccursAt o, Location l
WHERE MATCH(e-(o)->l)
  AND l.name = N'周荣庄园';

-- 5.6 受害者统计
SELECT c.name AS 案件, p.name AS 受害者, v.cause AS 死因
FROM Person p, VictimOf v, CaseNode c
WHERE MATCH(p-(v)->c);