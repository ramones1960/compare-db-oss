#!/usr/bin/env bash
# このDBのベンチマークを実行する。
# RESULT_DIR 環境変数に結果出力先が渡される。
set -euo pipefail
: "${RESULT_DIR:?RESULT_DIR が未設定です}"

echo "[TODO] ベンチマーク未実装です。"
echo "計測ロジックを実装し、結果を \$RESULT_DIR/summary.json に保存してください。"
exit 0
