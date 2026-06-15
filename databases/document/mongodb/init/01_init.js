// MongoDB 初期データ（起動時に MONGO_INITDB_DATABASE に対して実行される）
db = db.getSiblingDB('benchdb');
db.users.insertMany([
  { name: 'Alice', email: 'alice@example.com', tags: ['admin'] },
  { name: 'Bob',   email: 'bob@example.com',   tags: ['user'] },
]);
db.users.createIndex({ email: 1 }, { unique: true });
