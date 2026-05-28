调整一下GraphDB下QA页面的逻辑，当后台接收到一个问题之后，先把问题，以及00_GraphDB_SchemaOnly.sql中的对GraphDB Schema的定义，发送给大模型，大模型根据问题和Schema，生成一个SQL查询语句，后台执行SQL查询语句，返回结果给前端。
生成的SQL语句要以图查询，即使用CTE + MATCH子句的方式查询图中的节点和边。
QA调用大模型那部分，使用DeepSeek API。
将大模型调用，需要的API KEY以及BASE URL和MODELNAME放到.env文件中保存。