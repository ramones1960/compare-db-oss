# サンプルアプリサーバ（DB お試しコンソール）

各 DB に接続し、**用途別の GUI** から SELECT / INSERT などの基本操作を試せる
Web コンソール。FastAPI（バックエンド）＋ バニラ JS（フロントエンド、ビルド不要）。

![構成](../docs/comparison-matrix.md)

## 用途別 GUI

DB のデータモデル/用途に応じて、画面（パネル）が切り替わります。

| GUI タイプ | 対象 DB | 操作 |
|---|---|---|
| `sql` | PostgreSQL / MySQL / SQLite / CockroachDB / TimescaleDB / Cassandra(CQL) | SQL/CQL エディタ + 結果テーブル |
| `olap` (sql) | ClickHouse / DuckDB | 分析 SQL エディタ |
| `document` | MongoDB | コレクションへの挿入・JSON フィルタ検索 |
| `keyvalue` | Redis | SET / GET / KEYS / DEL |
| `graph` | Neo4j | Cypher エディタ |
| `timeseries` | InfluxDB | ポイント書き込み + Flux クエリ |
| `search` | OpenSearch | ドキュメント投入 + 全文検索 |
| `vector` | Qdrant / pgvector | ベクトル upsert + 類似検索 |

> 組込 DB（SQLite / DuckDB）はサーバを持たないため、アプリ内（インプロセス）で
> ローカルファイルを直接操作します（`app/data/`）。コンテナ起動は不要。

## 前提

試したい DB のコンテナを先に起動しておきます。

```bash
# 例: いくつか起動
make up DB=postgresql
make up DB=redis
make up DB=mongodb
# ...
```

接続情報はリポジトリ標準（`.env.example`）に合わせています。変更している場合は
環境変数（`DB_USER` / `DB_PASSWORD` / `OPENSEARCH_PASSWORD` / `NEO4J_PASSWORD` 等）で上書きしてください。

## 起動方法

### A. Docker で起動（推奨・Linux）

```bash
make app
# = cd app && docker compose up --build
# ブラウザで http://localhost:8000
```

`network_mode: host` でホストに公開された各 DB のポートへ到達します。

### B. ローカルで起動（開発用）

```bash
cd app
pip install -r requirements.txt
cd server && uvicorn main:app --reload --port 8000
# http://localhost:8000
```

## 使い方

1. 左サイドバーで DB を選択（● 緑=接続OK / 灰=停止中）
2. 用途別パネルのフォームに入力して実行
3. 結果がテーブル / JSON / メッセージで表示されます

停止中の DB は「`make up DB=<name>` で起動 → 右上『状態更新』」の案内が出ます。

## API（フロントエンドが利用）

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/databases` | 収録 DB と接続状態の一覧 |
| POST | `/api/{key}/action/{action}` | 指定 DB のアクション実行（body=params） |

## 注意

- **検証/学習用**です。認証情報は既定値、SQL/CQL は無加工で実行するため公開環境では使用しないでください。
