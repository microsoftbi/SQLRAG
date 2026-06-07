-- ============================================================
-- 图数据库关系修正脚本 v2
-- 基于 00_Story.md 剧情文本全面对照核查
-- 日期: 2026-06-07
-- ============================================================

-- 1. 删除：李峰 → PerpetratorOf → 叶剑遇害案（错误）
-- 李峰是A级通缉犯，在叶剑案调查中顺手抓获，但并非该案作案人（第4集）
DELETE FROM PerpetratorOf
WHERE EXISTS (
    SELECT 1 FROM Person p
    WHERE p.$node_id = PerpetratorOf.$from_id AND p.name = N'李峰'
)
AND EXISTS (
    SELECT 1 FROM CaseNode c
    WHERE c.$node_id = PerpetratorOf.$to_id AND c.name = N'叶剑遇害案'
);
PRINT '已删除：李峰 → PerpetratorOf → 叶剑遇害案';

-- 2. 删除：李棚改 → VictimOf → 叶剑遇害案（错误）
-- 李棚改是周荣从犯，在试图杀死张一昂时被击毙（第23集），不是受害者
DELETE FROM VictimOf
WHERE EXISTS (
    SELECT 1 FROM Person p
    WHERE p.$node_id = VictimOf.$from_id AND p.name = N'李棚改'
)
AND EXISTS (
    SELECT 1 FROM CaseNode c
    WHERE c.$node_id = VictimOf.$to_id AND c.name = N'叶剑遇害案'
);
PRINT '已删除：李棚改 → VictimOf → 叶剑遇害案';

-- 3. 补充：刘直 → RelatedTo → 三江口日报
-- 故事第5集：方超刘直混入三江口日报内部寻找线索
INSERT INTO RelatedTo ($from_id, $to_id, relationship)
SELECT p.$node_id, o.$node_id, N'方超刘直混入三江口日报'
FROM Person p, Organization o
WHERE p.name = N'刘直' AND o.name = N'三江口日报'
AND NOT EXISTS (
    SELECT 1 FROM RelatedTo r
    WHERE r.$from_id = p.$node_id AND r.$to_id = o.$node_id
);
PRINT '已补充：刘直 → RelatedTo → 三江口日报';

-- 4. 补充：朗博文 → ConflictWith → 周荣
-- 故事多处提及两人关系紧张：第12集「朗博文和周荣的冲突」、第17集「貌合神离」、第22集「利用朗博图施压」
INSERT INTO ConflictWith ($from_id, $to_id, reason)
SELECT p1.$node_id, p2.$node_id, N'兄弟冲突-朗博文被周荣利用朗博图施压，两人貌合神离'
FROM Person p1, Person p2
WHERE p1.name = N'朗博文' AND p2.name = N'周荣'
AND NOT EXISTS (
    SELECT 1 FROM ConflictWith c
    WHERE c.$from_id = p1.$node_id AND c.$to_id = p2.$node_id
);
PRINT '已补充：朗博文 → ConflictWith → 周荣';

PRINT '============================================';
PRINT '图数据库关系修正完成。';
PRINT '共执行：2 项删除，2 项补充。';
PRINT '============================================';
-- ============================================================