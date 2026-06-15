# CQRS パターン

| 項目 | 内容 |
|---|---|
| 構成DB | PostgreSQL（書き込みモデル）+ ClickHouse（読み取りモデル） |
| ポート | PostgreSQL: 5432 / ClickHouse: 8123 |
| 難易度 | ★★☆ 中級 |
| キーワード | CQRS、書き込み/読み取り分離、結果整合性、集計最適化 |

## パターンの概要

**CQRS**（Command Query Responsibility Segregation）は、「書き込み（Command）」と「読み取り（Query）」を異なるモデル・データストアで処理するアーキテクチャパターンです。

Martin Fowler が提唱した考え方で、読み取りと書き込みの特性がまったく異なることに着目します。

- **Command（書き込み）**: 整合性重視、行レベルのトランザクション → PostgreSQL
- **Query（読み取り）**: 集計・分析重視、列指向の高速スキャン → ClickHouse

## アーキテクチャ図

```
                    ┌─────────────────────────────┐
                    │         Application          │
                    └────────────┬────────────────┘
                                 │
               ┌─────────────────┴─────────────────┐
               │                                   │
     ┌─────────▼──────────┐           ┌────────────▼──────────┐
     │   Command Handler   │           │    Query Handler        │
     │   （書き込みAPI）   │           │    （読み取りAPI）      │
     └─────────┬──────────┘           └────────────┬──────────┘
               │                                   │
               ▼                                   ▼
     ┌──────────────────┐    Sync     ┌────────────────────────┐
     │   PostgreSQL     │────────────▶│      ClickHouse        │
     │  (書き込みモデル) │            │    (読み取りモデル)     │
     │                  │            │                         │
     │  - 正規化スキーマ │            │  - 非正規化・列指向    │
     │  - ACID保証      │            │  - 集計クエリ最適化    │
     │  - 行レベルロック │            │  - 高速スキャン        │
     │  port: 5432      │            │  port: 8123            │
     └──────────────────┘            └────────────────────────┘
```

## 同期の仕組み

```
PostgreSQL (WAL)
    │
    │  ① 変更イベント発生
    ▼
┌─────────────────────┐
│   同期メカニズム    │
│                     │
│  A. sync.py (本デモ)│  ← ポーリング方式（増分 id で差分取得）
│  B. Debezium CDC    │  ← WAL ベース、ほぼリアルタイム（推奨）
│  C. バッチ ETL      │  ← 夜間バッチ等、シンプルだが遅延大
└─────────────────────┘
    │
    ▼
ClickHouse（集計テーブル）
```

## クイックスタート

```bash
# コンテナ起動 + デモ実行
# pip install psycopg[binary] clickhouse-connect
./demo.sh

# または手動で
docker compose up -d
python3 demo.py

# 増分同期のみ実行
python3 sync.py

# 30秒ごとに同期（継続実行）
python3 sync.py --loop 30

# 停止・クリーンアップ
docker compose down -v
```

## デモの内容（demo.py）

1. PostgreSQL に `orders` テーブルを作成し、30件の注文データを書き込む（Command）
2. `sync_to_clickhouse()` で全件を ClickHouse に同期
3. ClickHouse で各種集計クエリを実行（Query）
   - 全体売上合計
   - 商品別売上・注文数
   - 日別トレンド

## いつ使うか

- **書き込みと読み取りの特性が大きく異なる**システム
  - 例: 注文処理（書き込み: 整合性重視）+ BI ダッシュボード（読み取り: 集計重視）
- 読み取りクエリがスケールボトルネックになっている場合
- 複雑な集計のために本番 DB に重い SELECT が走っている場合
- 書き込みと読み取りを**独立してスケール**したい場合

## いつ使わないか

- 小規模システム（複雑性が増すだけでメリットが薄い）
- **強整合性**が必須で、書き込み直後に最新値を読みたい場合（結果整合性で問題ある場合）
- チームの理解コストを払えない場合（学習曲線がある）

## 結果整合性（Eventual Consistency）

CQRS の最大の注意点は、書き込み DB と読み取り DB の間に**遅延（lag）**が生じることです。

```
ユーザーが注文（PostgreSQL に書き込み）
         │
         │  同期ラグ（数秒〜数分）
         ▼
ClickHouse に反映される

この間、ダッシュボードには最新の注文が表示されない
```

**対策**:
- **ユーザー向け画面**: 書き込み直後は PostgreSQL から直接読む（Read-Your-Writes 保証）
- **ダッシュボード**: 「最終更新: N秒前」を表示し、遅延を明示する
- **同期頻度を上げる**: Debezium CDC でミリ秒レベルの同期を実現

## 参考リンク

- [Martin Fowler - CQRS](https://martinfowler.com/bliki/CQRS.html)
- [Microsoft CQRS パターン](https://learn.microsoft.com/ja-jp/azure/architecture/patterns/cqrs)
- [ClickHouse ユースケース](https://clickhouse.com/docs/en/use-cases)
