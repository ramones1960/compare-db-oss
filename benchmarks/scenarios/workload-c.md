# Workload C — Read 100%

読み取り専用ワークロード（例: キャッシュ・参照専用レプリカ）。

| 項目 | 値 |
|---|---|
| Read 比率 | 100% |
| Update 比率 | 0% |
| レコード数 | `BENCH_RECORD_COUNT`（既定 100,000） |
| 操作数 | `BENCH_OPERATION_COUNT`（既定 100,000） |
| 分布 | Zipfian |

YCSB 互換。各 DB の `benchmark/run.sh` でこの定義に従って計測する。
事前に Workload A 等でデータを投入した状態で計測する（読み取り対象が存在している前提）。
