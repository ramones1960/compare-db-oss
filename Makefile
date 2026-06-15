# compare-db-oss 統一エントリポイント
#
# 使い方:
#   make list                         収録DB一覧を表示
#   make up   DB=postgresql           指定DBを起動
#   make down DB=postgresql           指定DBを停止
#   make logs DB=postgresql           ログ表示
#   make bench DB=postgresql          ベンチ実行（各DBネイティブ）
#   make ycsb DB=postgresql WORKLOAD=A  YCSB 共通ワークロードで計測（汎用KVS/RDBMS）
#   make clean DB=postgresql          停止 + ボリューム削除
#   make app                          GUI お試しアプリを起動 (http://localhost:8000)
#   make app-down                     GUI お試しアプリを停止
#   make new-db CATEGORY=relational DB=mariadb  新規DBの雛形を生成
#
# アーキテクチャパターン（patterns/）:
#   make pattern-up   PATTERN=cache-aside   パターン起動
#   make pattern-down PATTERN=cache-aside   パターン停止
#   make pattern-demo PATTERN=cache-aside   パターンデモ実行
#
# シナリオ（scenarios/）:
#   make fault-injection-up    Toxiproxy フォールトインジェクション環境起動
#   make fault-injection-down  停止

.PHONY: help list up down logs bench ycsb clean app app-down new-db \
        pattern-up pattern-down pattern-demo \
        fault-injection-up fault-injection-down

WORKLOAD ?= A

# DB名から databases/ 配下のパスを解決
DB_PATH = $(shell find databases -maxdepth 2 -type d -name "$(DB)" | head -n1)

help:
	@grep -E '^#' Makefile | sed 's/^# \{0,1\}//'

list:
	@echo "収録DB一覧:"
	@find databases -maxdepth 2 -mindepth 2 -type d | sed 's|databases/|  - |' | sort

_check:
	@test -n "$(DB)" || (echo "ERROR: DB=<name> を指定してください (make list で一覧)"; exit 1)
	@test -n "$(DB_PATH)" || (echo "ERROR: '$(DB)' が見つかりません (make list で確認)"; exit 1)

up: _check
	cd $(DB_PATH) && docker compose up -d

down: _check
	cd $(DB_PATH) && docker compose down

logs: _check
	cd $(DB_PATH) && docker compose logs -f

bench: _check
	./scripts/run-benchmark.sh $(DB)

ycsb: _check
	./scripts/run-ycsb.sh $(DB) $(WORKLOAD)

clean: _check
	cd $(DB_PATH) && docker compose down -v

# 画面からの DB 起動/停止のため、リポジトリをホストと同一パスでマウントする
# （HOST_REPO_ROOT に絶対パスを渡す）。docker ソケットも共有する（app/docker-compose.yml）。
app:
	cd app && HOST_REPO_ROOT=$(CURDIR) docker compose up --build

app-down:
	cd app && HOST_REPO_ROOT=$(CURDIR) docker compose down

new-db:
	@test -n "$(CATEGORY)" || (echo "ERROR: CATEGORY=<dir> を指定してください (例: relational)"; exit 1)
	@test -n "$(DB)" || (echo "ERROR: DB=<name> を指定してください"; exit 1)
	./scripts/new-db.sh $(CATEGORY) $(DB) $(IMAGE) $(PORT)

# ---------------------------------------------------------------------------
# アーキテクチャパターン
# ---------------------------------------------------------------------------
PATTERN_PATH = patterns/$(PATTERN)

_check_pattern:
	@test -n "$(PATTERN)" || (echo "ERROR: PATTERN=<name> を指定してください (cache-aside / cqrs / cdc-sync / polyglot)"; exit 1)
	@test -d "$(PATTERN_PATH)" || (echo "ERROR: patterns/$(PATTERN) が見つかりません"; exit 1)

pattern-up: _check_pattern
	cd $(PATTERN_PATH) && docker compose up -d

pattern-down: _check_pattern
	cd $(PATTERN_PATH) && docker compose down

pattern-demo: _check_pattern
	@if [ -f "$(PATTERN_PATH)/demo.sh" ]; then cd $(PATTERN_PATH) && bash demo.sh; \
	elif [ -f "$(PATTERN_PATH)/demo.py" ]; then cd $(PATTERN_PATH) && python3 demo.py; \
	else echo "デモスクリプトが見つかりません"; fi

# ---------------------------------------------------------------------------
# シナリオ（フォールトインジェクション）
# ---------------------------------------------------------------------------
fault-injection-up:
	cd scenarios/fault-injection && docker compose up -d
	@echo "起動後: bash scenarios/fault-injection/setup.sh でプロキシを登録してください"

fault-injection-down:
	cd scenarios/fault-injection && docker compose down
