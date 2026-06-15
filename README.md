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
├── app/               # 用途別GUIのお試しアプリ（FastAPI + JS）
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

## 動作要件

- **必須**: Docker / docker compose（Compose v2）。Linux / macOS / Windows(WSL2) で動作。
  GUI お試しアプリ（`make app`）は Docker で起動するため追加ランタイムは不要。
- **設計前提**: DB は `make up DB=<name>` で **1 つずつ起動**する。各 DB の compose は
  リソース上限 `cpus "4" / memory 8g`（公平な計測のための**上限**で、アイドル時の実消費はもっと小さい）。
  全 15 DB の**同時起動は想定していない**。

| 区分 | CPU | メモリ | ディスク空き | 用途 |
|---|---|---|---|---|
| 最低限 | 2 コア | 8 GB | 20 GB | 軽量DB（PostgreSQL/Redis/SQLite 等）を1つずつ起動・学習 |
| 推奨 | 4 コア | 16 GB | 40〜60 GB | 全DBを順番に検証。JVM系（Cassandra/OpenSearch/Neo4j）も快適 |
| 余裕 | 8 コア | 32 GB | 100 GB | ベンチを上限どおり効かせる・複数DB同時・YCSB イメージ込み |

- **メモリ**: JVM 系（Cassandra ヒープ 2G、OpenSearch `-Xmx2g` 等）は実際に 2GB 前後を確保するため 16GB 推奨。
- **ディスク**: DB イメージは多種（各数百MB〜1GB級）。一通り pull すると 20〜40GB 消費。`make ycsb` で +α。
- **プロキシ環境**: イメージ/パッケージ取得にプロキシ設定が要る場合は [docs/proxy.md](docs/proxy.md) を参照。

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

## 性能検証の考え方

**方針**: 各 DB を同一ホスト・同一リソース制約（CPU 4 / メモリ 8g）で起動し、共通の方針で計測して
**傾向**を比較します。各 DB に適したワークロード（pgbench / redis-benchmark / cassandra-stress /
`cockroach workload` / ネイティブ操作など）で計測し、結果を `summary.json` に統一フォーマットで保存。
絶対値の優劣付けではなく **用途ごとの傾向把握** が目的です（同一マシンで順次・ウォームアップ後に計測）。

```bash
make bench DB=postgresql
# 結果: benchmarks/results/<db>/<date>/summary.json
```

また、汎用 KVS/RDBMS は **YCSB 共通ワークロード(A〜E)** でも横並び計測できる
（対応: PostgreSQL / MySQL / CockroachDB / TimescaleDB / pgvector / MongoDB / Redis / Cassandra）。

```bash
make ycsb DB=postgresql WORKLOAD=A
# 結果: benchmarks/results/<db>/<date>-ycsb-A/summary.json
```

- 計測方針・指標・前提・結果フォーマットの詳細 → [docs/benchmark-methodology.md](docs/benchmark-methodology.md)
- ネイティブ計測 / YCSB の使い分け → [benchmarks/README.md](benchmarks/README.md)
- 全15 DB の参考値・比較表 → [docs/comparison-matrix.md](docs/comparison-matrix.md)

## GUI でお試し

各 DB を **用途別の GUI** から SELECT / INSERT などで操作できるサンプルアプリを同梱。

```bash
# 試したい DB を起動してから
make up DB=postgresql
make up DB=redis
make up DB=mongodb

# お試しアプリを起動（http://localhost:8000）
make app
```

DB のデータモデルに応じて画面が切り替わります（SQL エディタ / ドキュメント / KVS /
Cypher / 時系列 / 全文検索 / ベクトル）。詳細は [app/README.md](app/README.md)。

## 新しい DB を追加する

雛形生成 → 編集 → 登録、の流れを標準化している。

```bash
# 雛形を生成（テンプレートを複製してプレースホルダ置換）
make new-db CATEGORY=relational DB=mariadb IMAGE=mariadb:11 PORT=3307
# または ./scripts/new-db.sh relational mariadb mariadb:11 3307
```

生成後は `docker-compose.yml` / `init/` / `examples/` / `benchmark/run.sh` を埋め、
`.env.example`・`docs/comparison-matrix.md`・本 README を更新する。
規約・必須項目・チェックリストの全手順は [docs/adding-a-database.md](docs/adding-a-database.md) を参照。

## プロキシ環境での利用

社内プロキシ等の環境では、イメージ取得や pip/apt のパッケージ取得にプロキシ設定が必要です。
プロキシは **環境変数（`HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`）から取得**する方針で、
Docker デーモン・アプリのビルド（pip/apt）・pip/npm への設定方法を
[docs/proxy.md](docs/proxy.md) にまとめています。

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1,::1
make app   # ビルド時に pip/apt がプロキシ経由（値はイメージに残さない）
```

## ライセンス

各 DB のライセンスは個別に従います。本リポジトリのスクリプト・ドキュメントは MIT を想定。
