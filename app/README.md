# サンプルアプリサーバ（DB お試しコンソール）

各 DB に接続し、**用途別の GUI** から SELECT / INSERT などの基本操作を試せる
Web コンソール。FastAPI（バックエンド）＋ バニラ JS（フロントエンド、ビルド不要）。

![構成](../docs/comparison-matrix.md)

## 主な機能

- **用途別 GUI**: DB のデータモデルに応じた操作パネル（SQL / ドキュメント / KVS / グラフ / 時系列 / 検索 / ベクトル）
- **処理時間の計測**: すべての操作で `処理時間: N ms` を結果上部に表示（性能を体感できる）
- **大容量データのお試し**: 「大容量データ」カードから件数を指定して一括投入 → 検索/削除（CRUD）。各 DB ネイティブの一括投入を使用
- **画面から起動/停止**: 各 DB タブの「▶ 起動 / ■ 停止」で `docker compose` を実行（組込 DB を除く）
- **解説タブ**: 各 DB の公式ドキュメントリンク・特徴・ユースケース・アーキテクチャ組み込み例

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
# = cd app && HOST_REPO_ROOT=<repo> docker compose up --build
# ブラウザで http://localhost:8000

# 停止
make app-down
```

`network_mode: host` でホストに公開された各 DB のポートへ到達します。

**画面からの起動/停止について**: `make app` は (1) docker ソケット `/var/run/docker.sock`
と (2) リポジトリを**ホストと同一の絶対パス**でマウントし、`HOST_REPO_ROOT` を渡します。
これによりアプリのコンテナからホストの docker デーモンへ `docker compose up -d / down`
を実行でき、各 DB の相対バインドマウント（`./init` 等）も正しく解決されます。
docker CLI が無い／ソケット未マウントの環境では、起動/停止ボタンは安全に無効化され、
従来どおり `make up DB=<name>` での起動を案内します（**検証/学習用の機能です**）。

### B. ローカルで起動（開発用）

```bash
cd app
pip install -r requirements.txt
cd server && uvicorn main:app --reload --port 8000
# http://localhost:8000
```

## 使い方

1. 左サイドバーで DB を選択（● 緑=接続OK / 灰=停止中）
2. 必要なら DB タブの「▶ 起動」でコンテナを起動（数秒〜数十秒で ready）
3. 「操作」タブ: フォームに入力して実行 → 結果と**処理時間**が表示される
4. 「大容量データ」カード: 件数を指定して投入(Create) → 件数(Read) / 全削除(Delete)
5. 「解説」タブ: 公式ドキュメント・特徴・ユースケース・組み込み例を確認

停止中の DB は「▶ 起動」または「`make up DB=<name>`」で起動できます。

## API（フロントエンドが利用）

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/databases` | 収録 DB と接続状態・制御可否(`controllable`)の一覧 |
| POST | `/api/{key}/action/{action}` | 指定 DB のアクション実行（body=params、応答に `elapsed_ms`） |
| POST | `/api/{key}/control/{op}` | 指定 DB の起動/停止（op: `start` / `stop` / `status`） |

大容量データ用アクション（各 GUI 共通）: `bulk_load`（件数 `n` を投入）/ `bulk_count` / `bulk_clear`。

## 注意

- **検証/学習用**です。認証情報は既定値、SQL/CQL は無加工で実行するため公開環境では使用しないでください。
