// MongoDB 基本操作（CRUD）
// 実行: docker exec -i cmp-mongodb mongosh "<uri>" --quiet < examples/basic.js
db = db.getSiblingDB('benchdb');

// CREATE
db.users.insertOne({ name: 'Carol', email: 'carol@example.com', tags: ['user'] });

// READ
printjson(db.users.find({}, { _id: 0 }).toArray());

// UPDATE
db.users.updateOne({ email: 'carol@example.com' }, { $set: { name: 'Carol Smith' } });

// 集計（タグ別件数）
printjson(db.users.aggregate([
  { $unwind: '$tags' },
  { $group: { _id: '$tags', count: { $sum: 1 } } },
]).toArray());

// DELETE
db.users.deleteOne({ email: 'carol@example.com' });
