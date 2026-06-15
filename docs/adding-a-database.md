# DB を追加する手順（標準化）

新しい比較対象 DB を追加するときの **標準手順**。各 DB が同一フォーマット・同一の操作感
（`make up/down/bench/app`）で揃うように、規約と必須項目を定める。

> まず選定基準（[selection-criteria.md](selection-criteria.md)）を満たすか確認する。
> 追加候補のバックログも同ファイルにある。

## 0. 雛形を生成する

```bash
./scripts/new-db.sh <category_dir> <db> [image] [port]
# 例:
./scripts/new-db.sh relational mariadb mariadb:11 3307
```

`scripts/templates/db/` を `databases/<category_dir>/<db>/` に複製し、プレースホルダを
置換する。生成後に編集すべき箇所は `__EDIT__` で示される。

`category_dir` は既存のいずれか（無ければ新設）:
`relational / document / key-value / wide-column / graph / newsql / timeseries / search / olap / vector`

## 1. ディレクトリ構成（規約）

```
databases/<category_dir>/<db>/
├── README.md          # 共通フォーマット（下記）
├── docker-compose.yml # 単体起動（container_name は cmp-<db>）
├── config/            # 設定ファイル（無ければ .gitkeep）
├── init/              # スキーマ・初期データ
├── examples/          # 基本操作サンプル
└── benchmark/run.sh   # 性能検証（RESULT_DIR に summary.json を出力）
```

## 2. docker-compose.yml の規約

- `container_name: cmp-<db>`（`make bench` / アダプタ / YCSB ラッパが参照）
- ポートは `${<DB>_PORT:-<default>}:<container_port>` の形（環境変数で衝突回避）
- 認証情報は共通の `DB_USER` / `DB_PASSWORD` / `DB_NAME` に合わせる
  （別ルールが必須な場合のみ専用変数。例: `OPENSEARCH_PASSWORD` / `NEO4J_PASSWORD`）
- `deploy.resources.limits` で **CPU 4 / メモリ 8g** に揃える（公平な計測のため）
- `healthcheck` を必ず定義する（`make bench` の `wait_healthy` が待機に使う。
  定義が無い DB は固定待機にフォールバックする）
- 初期化は `init/` をマウント（マウント先は DB 依存。例: postgres は
  `/docker-entrypoint-initdb.d`、自動適用が無い DB は README に手動適用手順を書く）

## 3. .env.example にポートを追記

`<DB>_PORT=<default>` を「ポートマッピング」節へ追加する。

## 4. init/ と examples/

- `init/`: 起動時に流す最小スキーマ・サンプルデータ
- `examples/`: 接続後にコピペで試せる CRUD / 基本操作（SQL/CQL/スクリプト等）

## 5. benchmark/run.sh の契約

- `set -euo pipefail` ＋ `scripts/lib/common.sh` を読み込む
- `RESULT_DIR`（呼び出し側が設定）必須チェック `: "${RESULT_DIR:?...}"`
- 共通ヘルパーを使う: `ensure_up` / `wait_healthy` / `now_ms` / `write_summary`
- 計測ログは `"$RESULT_DIR/bench.log"` に残す
- 最後に `write_summary <db> <version> <workloads-json>` で
  `summary.json` を統一フォーマットで出力する
- ワークロードは DB に適したもの（ネイティブツール or ネイティブ操作）でよい。
  傾向把握が目的なので絶対値の公平性より再現性を優先する。

詳細な方針は [benchmark-methodology.md](benchmark-methodology.md) を参照。

### YCSB 対応DB（汎用 KVS/RDBMS）の場合

JDBC / MongoDB / Redis / Cassandra(CQL) のいずれかのバインディングがあるなら、
共通ワークロード(A〜E)でも計測できるよう `scripts/run-ycsb.sh` の `case "$DB"` に
バインディングと接続プロパティ・スキーマ準備を追加する。これにより
`make ycsb DB=<db> WORKLOAD=A` が使えるようになる。

## 6. app（GUI お試し）のアダプタ（任意）

GUI で試せるようにする場合:

1. `app/server/adapters.py` に `Adapter` 派生クラスを追加（`gui_type` を既存の
   `sql / olap / document / keyvalue / graph / timeseries / search / vector` から選ぶ。
   新モデルなら `app/web/app.js` にパネルを追加）
2. `build_registry()` の戻りリストにインスタンスを登録（接続情報は `env(...)` 経由）

## 7. ドキュメント更新

- [comparison-matrix.md](comparison-matrix.md): 「カテゴリ別サマリ」と「性能サマリ」に行を追加
- [selection-criteria.md](selection-criteria.md): バックログから採用へ移すなら更新
- ルート [README.md](../README.md): 「比較対象カテゴリ」表・「実装状況」・DB 数を更新

## 8. 動作確認

```bash
make up   DB=<db>      # 起動
make bench DB=<db>     # ベンチ（summary.json 生成）
make ycsb DB=<db>      # YCSB 対応なら共通ワークロードでも計測
make app               # GUI に出てくるか（アダプタを追加した場合）
make down DB=<db>
```

## チェックリスト

- [ ] `databases/<cat>/<db>/` 一式（README/compose/config/init/examples/benchmark）
- [ ] `container_name: cmp-<db>` / ポート env / リソース制限 / healthcheck
- [ ] `.env.example` にポート追記
- [ ] `benchmark/run.sh` が `summary.json` を出力
- [ ] （YCSB対応なら）`scripts/run-ycsb.sh` にマッピング追加
- [ ] （任意）app アダプタ追加・登録
- [ ] `comparison-matrix.md` / `README.md` 更新
- [ ] `make up` / `make bench` で動作確認済み
