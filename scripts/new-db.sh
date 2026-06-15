#!/usr/bin/env bash
# 新しい比較対象 DB の雛形を作成する。
#   ./scripts/new-db.sh <category_dir> <db> [image] [port]
#
# 例: ./scripts/new-db.sh relational mariadb mariadb:11 3307
#
# テンプレート（scripts/templates/db/）を databases/<category_dir>/<db>/ に複製し、
# プレースホルダを置換する。生成後の編集すべき箇所は __EDIT__ で示す。
# 完全な手順は docs/adding-a-database.md を参照。
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

CATEGORY_DIR="${1:-}"
DB="${2:-}"
IMAGE="${3:-IMAGE:tag}"
PORT="${4:-0}"

if [[ -z "$CATEGORY_DIR" || -z "$DB" ]]; then
  err "使い方: ./scripts/new-db.sh <category_dir> <db> [image] [port]"
  err "  category_dir 例: relational document key-value wide-column graph newsql timeseries search olap vector"
  exit 1
fi

# 既知カテゴリの日本語ラベル（未知ならディレクトリ名をそのまま使う）
category_label() {
  case "$1" in
    relational)  echo "リレーショナル" ;;
    document)    echo "ドキュメント" ;;
    key-value)   echo "キーバリュー" ;;
    wide-column) echo "ワイドカラム" ;;
    graph)       echo "グラフ" ;;
    newsql)      echo "分散SQL (NewSQL)" ;;
    timeseries)  echo "時系列" ;;
    search)      echo "全文検索" ;;
    olap)        echo "分析 (OLAP)" ;;
    vector)      echo "ベクトル (AI/RAG)" ;;
    *)           echo "$1" ;;
  esac
}

DEST="$ROOT_DIR/databases/$CATEGORY_DIR/$DB"
if [[ -e "$DEST" ]]; then
  err "既に存在します: $DEST"
  exit 1
fi

TITLE="$DB"
CATEGORY="$(category_label "$CATEGORY_DIR")"
CONTAINER="cmp-$DB"
PORT_ENV="$(printf '%s' "$DB" | tr '[:lower:]-' '[:upper:]_')_PORT"

log "雛形を生成: $DEST"
cp -a "$ROOT_DIR/scripts/templates/db" "$DEST"

# プレースホルダ置換（全テキストファイル対象）
while IFS= read -r -d '' f; do
  sed -i \
    -e "s|__DB__|$DB|g" \
    -e "s|__TITLE__|$TITLE|g" \
    -e "s|__CATEGORY__|$CATEGORY|g" \
    -e "s|__CATEGORY_DIR__|$CATEGORY_DIR|g" \
    -e "s|__CONTAINER__|$CONTAINER|g" \
    -e "s|__IMAGE__|$IMAGE|g" \
    -e "s|__PORT_ENV__|$PORT_ENV|g" \
    -e "s|__PORT__|$PORT|g" \
    "$f"
done < <(find "$DEST" -type f -print0)

chmod +x "$DEST/benchmark/run.sh"

log "完了。次の手順:"
cat <<NEXT

  生成物: databases/$CATEGORY_DIR/$DB/

  1. docker-compose.yml の environment / volumes / healthcheck を埋める
     - コンテナ名は $CONTAINER（規約）
  2. .env.example に「$PORT_ENV=$PORT」を追記
  3. init/ examples/ に初期データ・基本操作サンプルを置く
  4. benchmark/run.sh を実装（__EDIT__ 箇所）
     - YCSB 対応DBなら scripts/run-ycsb.sh の case にもマッピングを追加
  5. app/server/adapters.py にアダプタを追加し build_registry() に登録（任意）
  6. docs/comparison-matrix.md に行を追加（必要なら docs/selection-criteria.md のバックログから外す）
  7. README.md の収録カテゴリ表・実装状況・DB 数を更新
  8. 動作確認: make up DB=$DB / make bench DB=$DB / make app

  詳細・チェックリスト: docs/adding-a-database.md
NEXT
