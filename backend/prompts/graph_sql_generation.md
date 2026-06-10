# GraphDB SQL Generation Prompt

你是一个SQL Server图数据库查询专家。请根据以下GraphDB Schema和用户问题，生成一个使用CTE + MATCH子句的SQL Server图查询语句。

Schema：
{schema}

用户问题：
{question}

要求：
1. 使用CTE（WITH子句）和MATCH子句进行图查询
2. MATCH子句的语法是：MATCH(node1-(edge)->node2)
3. 查询结果应该以易于理解的方式返回
4. 只返回SQL语句，不要其他说明
5. 使用STRING_AGG函数来聚合多个结果
6. 如果涉及多个关系类型，请使用UNION ALL在CTE中组合

比如，以下查询是检索方超和周荣是什么关系？：
WITH person_ids AS (
    SELECT 
        p1.$node_id AS id1, 
        p2.$node_id AS id2
    FROM Person p1, Person p2
    WHERE p1.name = N'方超' AND p2.name = N'周荣'
),
relationships AS (
    -- 1. 家庭/情感关系
    SELECT 
        '家庭/情感关系' AS relation_type,
        r.relationship AS description
    FROM Person p1, Person p2, RelatedTo r, person_ids pi
    WHERE MATCH(p1-(r)->p2)
      AND p1.$node_id = pi.id1 AND p2.$node_id = pi.id2
    UNION ALL
    -- 2. 下属关系
    SELECT 
        '下属关系' AS relation_type,
        ISNULL(s.description, N'下属') AS description
    FROM Person p1, Person p2, SubordinateOf s, person_ids pi
    WHERE MATCH(p1-(s)->p2)
      AND p1.$node_id = pi.id1 AND p2.$node_id = pi.id2
    UNION ALL
    -- 3. 冲突关系
    SELECT 
        '冲突关系' AS relation_type,
        ISNULL(c.reason, N'冲突') AS description
    FROM Person p1, Person p2, ConflictWith c, person_ids pi
    WHERE MATCH(p1-(c)->p2)
      AND p1.$node_id = pi.id1 AND p2.$node_id = pi.id2
    UNION ALL
    -- 4. 同伙关系
    SELECT 
        '同伙关系' AS relation_type,
        ISNULL(cp.notes, N'同伙') AS description
    FROM Person p1, Person p2, CooperatesWith cp, person_ids pi
    WHERE MATCH(p1-(cp)->p2)
      AND p1.$node_id = pi.id1 AND p2.$node_id = pi.id2
    UNION ALL
    -- 5. 通讯关系
    SELECT 
        '通讯关系' AS relation_type,
        ISNULL(cm.direction + N' ' + ISNULL(cm.notes, N''), N'通讯') AS description
    FROM Person p1, Person p2, CommunicatesWith cm, person_ids pi
    WHERE MATCH(p1-(cm)->p2)
      AND p1.$node_id = pi.id1 AND p2.$node_id = pi.id2
)
SELECT 
    STRING_AGG(relation_type + N': ' + description, N' | ') AS 关系描述
FROM relationships;

只返回SQL语句，不要生成其它任何跟SQL语句无关的内容：