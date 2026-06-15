# ベンチマーク手法

性能検証を再現可能かつ公平に行うための方針・前提・手順を定義する。

## 基本方針

- **同一ホスト・同一リソース制約**で各 DB を計測する（`docker-compose` の `deploy.resources` で CPU / メモリを揃える）
- ワークロードは [../benchmarks/scenarios/](../benchmarks/scenarios/) に定義し、全 DB で共通化する
- 結果は [../benchmarks/results/](../benchmarks/results/) に DB 別・日付別で保存する
- **単一ノード構成**を基本とし、分散構成は別途明記する

## 計測指標

| 指標 | 説明 |
|---|---|
| スループット | 単位時間あたりの処理数 (ops/sec) |
| レイテンシ | 1 操作の応答時間 (p50 / p95 / p99) |
| リソース使用量 | CPU / メモリ / ディスク I/O |
| データサイズ | 投入データの保存容量 |

## 標準ワークロード

汎用 KVS/RDBMS には [YCSB](https://github.com/brianfrankcooper/YCSB) を基準に、以下のワークロードを使用する。

| 名称 | 構成 | 想定用途 |
|---|---|---|
| Workload A | Read 50% / Update 50% | 更新の多いセッションストア |
| Workload B | Read 95% / Update 5% | 参照中心アプリ |
| Workload C | Read 100% | キャッシュ |
| Workload D | Read latest 中心 | 最新データ参照 |
| Workload E | Scan 中心 | 範囲スキャン |

これら A〜E の定義は [../benchmarks/scenarios/](../benchmarks/scenarios/)（`workload-a.md`〜`workload-e.md`）にあり、
**YCSB 対応DB（汎用 KVS/RDBMS）** では `make ycsb DB=<name> WORKLOAD=A` で実測できる
（対応DB・仕組みは [../benchmarks/README.md](../benchmarks/README.md)）。

カテゴリ固有のベンチ（時系列・OLAP・ベクトル・検索）は各 DB の `benchmark/` に専用スクリプトを用意し、
`make bench DB=<name>` で実行する。（例: OLAP は集計クエリのレイテンシ、ベクトルは Recall@k と QPS）

## 前提条件・注意

- **検証用設定**であり、各 DB のチューニングは最小限。生の比較ではなく傾向把握が目的
- ウォームアップ後に計測する（初回はキャッシュ未充填）
- 同一マシンで順番に実行し、並走させない
- バージョンを記録する（`docker-compose.yml` のイメージタグ）

## 実行手順

```bash
# 1. 対象DBを起動
make up DB=postgresql

# 2. 初期データ投入（init/ が自動適用される。追加投入は examples/ 参照）

# 3. ベンチ実行
make bench DB=postgresql

# 4. 結果は benchmarks/results/postgresql/<date>/ に保存される

# 5. 停止
make down DB=postgresql
```

## 結果フォーマット

`benchmarks/results/<db>/<date>/summary.json` に以下の形式で保存する。

```json
{
  "db": "postgresql",
  "version": "16",
  "date": "2026-06-15",
  "host": { "cpu": "4", "memory": "8g" },
  "workloads": {
    "A": { "throughput_ops": 0, "latency_p99_ms": 0 }
  }
}
```
