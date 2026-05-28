
-- Add edges for Highway Service Area

INSERT INTO LocatedIn ($from_id, $to_id, description)
VALUES ('{"type":"node","schema":"dbo","table":"Person","id":23}', '{"type":"node","schema":"dbo","table":"Location","id":12}', N'林凯的车停留在高速服务区');

INSERT INTO LocatedIn ($from_id, $to_id, description)
VALUES ('{"type":"node","schema":"dbo","table":"Person","id":2}', '{"type":"node","schema":"dbo","table":"Location","id":12}', N'方超在高速附近活动');

INSERT INTO LocatedIn ($from_id, $to_id, description)
VALUES ('{"type":"node","schema":"dbo","table":"Person","id":3}', '{"type":"node","schema":"dbo","table":"Location","id":12}', N'刘直在高速附近活动');

INSERT INTO LocatedIn ($from_id, $to_id, description)
VALUES ('{"type":"node","schema":"dbo","table":"Person","id":14}', '{"type":"node","schema":"dbo","table":"Location","id":12}', N'方庸想去高速服务区找林凯');
