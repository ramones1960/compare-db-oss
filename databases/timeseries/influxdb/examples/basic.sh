#!/usr/bin/env bash
# InfluxDB 基本操作サンプル（ホストから docker exec で実行）
set -euo pipefail
T="-t cmp-admin-token -o cmp-org"

# 書き込み
docker exec cmp-influxdb influx write --bucket benchdb $T --precision s \
  'cpu,host=h1 value=0.64 1700000000
cpu,host=h2 value=0.81 1700000010'

# 集計クエリ
docker exec cmp-influxdb influx query $T \
  'from(bucket:"benchdb") |> range(start:-100y) |> mean()'
