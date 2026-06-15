# Workload A — Read 50% / Update 50%

更新の多いワークロード（例: セッションストア、ユーザーステータス更新）。

| 項目 | 値 |
|---|---|
| Read 比率 | 50% |
| Update 比率 | 50% |
| レコード数 | `BENCH_RECORD_COUNT`（既定 100,000） |
| 操作数 | `BENCH_OPERATION_COUNT`（既定 100,000） |
| 分布 | Zipfian |

YCSB 互換。各 DB の `benchmark/run.sh` でこの定義に従って計測する。
他のワークロード（B: Read 95%, C: Read 100%, D: latest, E: scan）も同様に定義を追加する。
