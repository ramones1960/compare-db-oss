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
他のワークロードは以下に定義済み:

- [Workload B](workload-b.md) — Read 95% / Update 5%（参照中心）
- [Workload C](workload-c.md) — Read 100%（キャッシュ）
- [Workload D](workload-d.md) — Read latest 中心
- [Workload E](workload-e.md) — Scan 中心
