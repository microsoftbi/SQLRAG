不点击"使用AI生成SQL"时，走的是 legacy_graph_qa 函数。它的逻辑是硬编码的关键词匹配 + 预定义的 SQL 模板，流程如下：

1. 实体识别
先预定义了4类实体名单：

类型	实体列表
人物	方超、刘直、周荣、张一昂、李茜、叶剑、霍正 等 21 人
案件	叶剑遇害案、省城爆炸案、金店抢劫案、方庸贪腐案、周荣涉黑案
地点	枫林晚酒店、荣城集团大楼、三江口长途汽车站 等 9 个
组织	荣城集团、三江口日报、朱亦飞文物贩卖团伙
然后扫描问题字符串，看包含哪些实体名。

2. 按问题关键词分派到不同的预定义 SQL 查询

问题模式 → 执行函数
────────────────────────────────────────────────────────────
"哪些人物" + "案件" + "多个"/"同时"  →  find_common_entities(cursor)
    查询同时出现在多个案件中的所有人（suspect/victim/perpetrator/witness/investigator）

"同时" / "认识又" / "和...有关系"     →  find_common_related_entities(cursor, entity1, entity2)
    查询同时与两个实体都有关联的第三方实体

"关系" / "认识" / "联系"            →  find_relationship_between_nodes(cursor, name1, name2)
    查两个 Person 之间的直接边关系（SubordinateOf, RelatedTo, ConflictWith 等）

"涉及" / "关联" / "参与"            →  find_related_entities(cursor, entity)
    查某个实体所有入边和出边关联的实体

"路径" / "之间"                     →  find_path_between_nodes(cursor, name1, name2)
    当前仅返回提示信息，未实现真正的图路径算法

"哪些" / "多个"                     →  find_common_entities(cursor)
    同第一条，查跨案件人物

未匹配任何模式 → 返回一个帮助提示，列出可用的提问方式
3. 底层查询方式
所有这些函数最终都使用MATCH 子句进行图查询（graph match pattern），例如 _find_related_via_match 中是一个包含 23 个 UNION ALL 的 CTE，覆盖 Person → Person / CaseNode / Organization / Item / Location / Event 之间所有方向的边关系，每个查询使用 MATCH(node1-(edge)->node2) 语法。

关键限制
实体名单是硬编码的，新增实体必须改代码
语义理解完全是关键词模式匹配，不灵活
find_path_between_nodes 功能未真正实现
只能处理单跳或预定义模板的查询，复杂的或多跳关联无法回答
相比之下，使用 AI 生成 SQL 时，会把 Schema 和问题一起发给 DeepSeek，让模型动态生成 SQL，能覆盖更灵活的查询。