# アーキテクチャパターン集

実際のシステムで複数の DB を組み合わせて使うパターンを、**動かして学ぶ**デモ集です。
各パターンは独立して起動できます。

```
patterns/
├── cache-aside/     # PostgreSQL + Redis — アプリ主導のキャッシュ
├── cqrs/            # PostgreSQL（書き込み）+ ClickHouse（読み取り）— CQRS
├── cdc-sync/        # PostgreSQL → Kafka（Debezium CDC）→ OpenSearch — リアルタイム同期
└── polyglot/        # PostgreSQL + Redis + MongoDB + OpenSearch + ClickHouse — 役割分担
```

---

## パターン選択ガイド

```
単一DBで収まるか？
 └─ Yes → PostgreSQL（汎用）か SQLite（組込）
 └─ No ↓

読み取りが重い？
 ├─ キャッシュで解決できる → Cache-Aside（Postgres + Redis）
 └─ 集計/分析が重い      → CQRS（Postgres + ClickHouse）

検索が必要？
 └─ Yes → CDC で OpenSearch に同期

用途ごとに DB が明確に異なる？
 └─ Yes → Polyglot Persistence（各DBの得意を使い分け）
```

---

## パターン別サマリ

| パターン | 組み合わせ | 解決する課題 | 増える複雑さ |
|---|---|---|---|
| Cache-Aside | Postgres + Redis | 読み取り負荷・低レイテンシ | キャッシュ無効化・thundering herd |
| CQRS | Postgres + ClickHouse | 書き込みと分析の同居 | 結果整合性・同期ラグ |
| CDC Sync | Postgres → Kafka → OpenSearch | 全文検索・異種DB同期 | Kafkaインフラ・スキーマ変更 |
| Polyglot | 5 DB | 各DBの得意を最大化 | 運用コスト・トランザクション境界 |

---

## クイックスタート

```bash
# 各パターンは独立したディレクトリで完結
cd patterns/cache-aside
docker compose up -d
python demo.py

cd patterns/cqrs
docker compose up -d
python demo.py

cd patterns/cdc-sync
docker compose up -d
bash setup.sh     # Debezium コネクタを登録
bash demo.sh

cd patterns/polyglot
docker compose up -d
python demo.py
```

> **注意**: 各パターンはポートが重複しないよう設定されています。
> ただし `databases/` で同一DBが起動中の場合はポート競合する可能性があります。
> 事前に `make down DB=<name>` で停止してください。
