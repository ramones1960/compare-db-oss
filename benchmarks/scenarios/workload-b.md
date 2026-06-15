# Workload B — Read 95% / Update 5%

参照が中心で更新が少ないワークロード（例: 商品ページ・プロフィール参照など読み取り中心アプリ）。

| 項目 | 値 |
|---|---|
| Read 比率 | 95% |
| Update 比率 | 5% |
| レコード数 | `BENCH_RECORD_COUNT`（既定 100,000） |
| 操作数 | `BENCH_OPERATION_COUNT`（既定 100,000） |
| 分布 | Zipfian |

YCSB 互換。各 DB の `benchmark/run.sh` でこの定義に従って計測する。
