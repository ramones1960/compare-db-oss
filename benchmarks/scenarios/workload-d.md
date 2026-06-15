# Workload D — Read latest 中心（Read 95% / Insert 5%）

新しく挿入されたレコードほど読まれやすいワークロード（例: 最新ニュース・タイムライン・通知）。

| 項目 | 値 |
|---|---|
| Read 比率 | 95% |
| Insert 比率 | 5% |
| レコード数 | `BENCH_RECORD_COUNT`（既定 100,000） |
| 操作数 | `BENCH_OPERATION_COUNT`（既定 100,000） |
| 分布 | Latest（直近挿入を優先して読む） |

YCSB 互換。各 DB の `benchmark/run.sh` でこの定義に従って計測する。
Insert によりレコード数は計測中に増加する。読み取りキーは最新挿入分に偏らせる。
