# benchmarks

全 DB 共通のベンチマーク基盤。手法は [../docs/benchmark-methodology.md](../docs/benchmark-methodology.md) を参照。

```
benchmarks/
├── tools/       # 共通計測ツール（YCSB）の Dockerfile / ラッパ
│   └── ycsb/    #   Dockerfile（多バインディング同梱）+ summarize.py
├── scenarios/   # ワークロード定義（全DB共通。workload-a〜e.md）
└── results/     # 計測結果（<db>/<date>/summary.json）
```

## 2 つの計測経路

### 1. 各DBネイティブ（`make bench`）

DB ごとに最適なツール（pgbench / redis-benchmark / cassandra-stress 等）で計測する。
全 15 DB が対応。指標は DB により異なるが、用途に即した傾向を見やすい。

```bash
make bench DB=postgresql
# -> 各DBの databases/<cat>/<db>/benchmark/run.sh を呼び出し
#    結果を benchmarks/results/<db>/<date>/ に保存する
```

### 2. YCSB 共通ワークロード（`make ycsb`）

汎用 KVS/RDBMS を **同一のワークロード(A〜E)** で計測し、横並び比較しやすくする。
[YCSB](https://github.com/brianfrankcooper/YCSB) を Docker 化（`tools/ycsb/`）して使う。

```bash
make ycsb DB=postgresql WORKLOAD=A
# -> tools/ycsb のイメージを（無ければ）ビルドし、対象DBに load + run
#    結果を benchmarks/results/<db>/<date>-ycsb-<WL>/summary.json に保存する
```

- **対応DB**: PostgreSQL / MySQL / CockroachDB / TimescaleDB / pgvector（jdbc）、
  MongoDB、Redis、Cassandra（cassandra-cql）
- 上記以外（OLAP / 検索 / グラフ / 専用時系列 / 専用ベクトル）は YCSB バインディングが
  無いため `make bench` を使う
- 初回はイメージビルドで YCSB 本体・JDBC ドライバを取得する（プロキシは
  [../docs/proxy.md](../docs/proxy.md)）。ビルド後の計測実行は localhost 接続でローカル完結
- ワークロード定義: [scenarios/](scenarios/)（workload-a〜e.md）

## ツール選定方針

- 汎用 KVS/RDBMS: [YCSB](https://github.com/brianfrankcooper/YCSB)
- RDBMS 単体: `pgbench` / `sysbench`
- OLAP: 集計クエリのレイテンシ計測（カテゴリ固有）
- ベクトル: Recall@k と QPS（カテゴリ固有）

共通化できる部分は `tools/` に集約し、固有部分は各 DB の `benchmark/` に置く。
