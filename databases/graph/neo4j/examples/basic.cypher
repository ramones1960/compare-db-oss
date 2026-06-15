// Neo4j 基本操作（Cypher）
// 実行: docker exec -i cmp-neo4j cypher-shell -u neo4j -p neo4jPass123 < examples/basic.cypher

// ノード作成
CREATE (a:Person {name: 'Alice'});
CREATE (b:Person {name: 'Bob'});

// 関係作成
MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'})
CREATE (a)-[:KNOWS {since: 2020}]->(b);

// 関連探索（Alice の知り合い）
MATCH (a:Person {name: 'Alice'})-[:KNOWS]->(friend)
RETURN a.name AS person, friend.name AS knows;

// クリーンアップ
MATCH (n:Person) WHERE n.name IN ['Alice','Bob'] DETACH DELETE n;
