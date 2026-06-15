# benchmarks

全 DB 共通のベンチマーク基盤。手法は [../docs/benchmark-methodology.md](../docs/benchmark-methodology.md) を参照。

```
benchmarks/
├── tools/       # 共通計測ツール（YCSB 等）の Dockerfile / ラッパ
├── scenarios/   # ワークロード定義（全DB共通）
└── results/     # 計測結果（<db>/<date>/summary.json）
```

## 使い方

```bash
make bench DB=postgresql
# -> 各DBの databases/<cat>/<db>/benchmark/run.sh を呼び出し
#    結果を benchmarks/results/<db>/<date>/ に保存する
```

## ツール選定方針

- 汎用 KVS/RDBMS: [YCSB](https://github.com/brianfrankcooper/YCSB)
- RDBMS 単体: `pgbench` / `sysbench`
- OLAP: 集計クエリのレイテンシ計測（カテゴリ固有）
- ベクトル: Recall@k と QPS（カテゴリ固有）

共通化できる部分は `tools/` に集約し、固有部分は各 DB の `benchmark/` に置く。
