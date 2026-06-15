# compare-db-oss

OSS データベースを **性能・用途別に比較**するためのモノレポです。
RDBMS から NoSQL（ドキュメント / KVS / ワイドカラム / グラフ）、分散SQL、時系列、検索、OLAP、ベクトルDB まで、
各 DB を **コンテナ上で独立して起動**し、基本操作と性能検証を同一フォーマットでまとめます。

## 目的

- 各 DB の **用途・特徴・長所短所** を横並びで把握する
- **基本操作（接続・CRUD）** をすぐ試せる形で提供する
- **共通ワークロード**で **性能検証**し、結果を蓄積・比較する

## ディレクトリ構成

```
compare-db-oss/
├── docs/              # 比較表・選定基準・ベンチ手法
├── databases/         # カテゴリ → 個別DB（各DBは自己完結）
│   └── <category>/<db>/
│       ├── README.md          # 概要 / 用途 / 基本操作 / 性能特性
│       ├── docker-compose.yml # 単体起動
│       ├── config/            # 設定ファイル
│       ├── init/              # スキーマ・初期データ
│       ├── examples/          # 基本操作サンプル
│       └── benchmark/         # 性能検証スクリプト
├── benchmarks/        # 共通ベンチ基盤（tools / scenarios / results）
├── scripts/           # 横断オペレーション（up/down/run-benchmark）
└── Makefile           # 統一エントリポイント
```

## 比較対象カテゴリ

| カテゴリ | 用途 | 収録DB |
|---|---|---|
| リレーショナル | 汎用・トランザクション | PostgreSQL / MySQL / SQLite |
| ドキュメント | スキーマレス・Web/API | MongoDB |
| キーバリュー | キャッシュ・低レイテンシ | Redis |
| ワイドカラム | 大量書き込み・分散 | Cassandra |
| グラフ | 関連性探索・推薦 | Neo4j |
| 分散SQL (NewSQL) | 水平スケール＋SQL | CockroachDB |
| 時系列 | メトリクス・IoT | InfluxDB / TimescaleDB |
| 全文検索 | ログ・検索 | OpenSearch |
| 分析 (OLAP) | 集計・BI | ClickHouse / DuckDB |
| ベクトル (AI/RAG) | 類似検索・LLM連携 | Qdrant / pgvector |

詳細は [docs/comparison-matrix.md](docs/comparison-matrix.md) を参照。

### 実装状況

**全 15 DB を通しで実装済み** — README・初期データ・CRUD例・動作する性能検証スクリプトを完備し、
`make bench DB=<name>` で `summary.json` を出力できる状態（全DBコンテナで動作確認済み）。

## クイックスタート

```bash
# 例: PostgreSQL を起動
make up DB=postgresql
# または
cd databases/relational/postgresql && docker compose up -d

# 停止
make down DB=postgresql

# ベンチ実行
make bench DB=postgresql
```

## 新しい DB を追加する

1. `databases/<category>/<db>/` を既存DBのテンプレートを複製して作成
2. `docker-compose.yml` / `init/` / `examples/` / `benchmark/` を埋める
3. `README.md` を共通フォーマットで記述
4. `docs/comparison-matrix.md` に行を追加

## ライセンス

各 DB のライセンスは個別に従います。本リポジトリのスクリプト・ドキュメントは MIT を想定。
