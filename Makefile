# compare-db-oss 統一エントリポイント
#
# 使い方:
#   make list                 収録DB一覧を表示
#   make up   DB=postgresql   指定DBを起動
#   make down DB=postgresql   指定DBを停止
#   make logs DB=postgresql   ログ表示
#   make bench DB=postgresql  ベンチ実行
#   make clean DB=postgresql  停止 + ボリューム削除
#   make app                  GUI お試しアプリを起動 (http://localhost:8000)

.PHONY: help list up down logs bench clean app

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

clean: _check
	cd $(DB_PATH) && docker compose down -v

app:
	cd app && docker compose up --build
