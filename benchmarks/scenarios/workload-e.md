# Workload E — Scan 中心（Scan 95% / Insert 5%）

連続するレコードを範囲スキャンするワークロード（例: 会話スレッド・期間集計の元データ取得）。

| 項目 | 値 |
|---|---|
| Scan 比率 | 95% |
| Insert 比率 | 5% |
| レコード数 | `BENCH_RECORD_COUNT`（既定 100,000） |
| 操作数 | `BENCH_OPERATION_COUNT`（既定 100,000） |
| スキャン長 | `BENCH_SCAN_LENGTH`（既定 1〜100 件をランダム、上限 100） |
| 分布 | 開始キー Zipfian / スキャン長 Uniform |

YCSB 互換。各 DB の `benchmark/run.sh` でこの定義に従って計測する。
範囲スキャンをサポートしない DB（純 KVS 等）では対象外、または近い操作で代替する旨を結果に明記する。
