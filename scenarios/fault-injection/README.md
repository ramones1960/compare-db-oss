# Fault Injection デモ — Toxiproxy

## Toxiproxy とは

[Toxiproxy](https://github.com/Shopify/toxiproxy) は Shopify が開発した OSS の **ネットワーク障害シミュレーター**。
アプリケーションとデータストアの間に透過プロキシとして立ち、
遅延・パケットロス・帯域制限・タイムアウトなど様々な障害を HTTP API 経由で動的に注入できる。

本番環境に手を入れることなく、**開発・テスト環境で障害時の挙動を再現**できるのが最大の利点。

---

## 構成図

```
┌─────────────────────────────────────────────────────────┐
│  ホスト（あなたのPC）                                    │
│                                                         │
│  ┌──────────────┐     localhost:8666     ┌───────────┐  │
│  │  demo.py     │ ─── (Toxiproxy) ────► │ postgres  │  │
│  │  (クライアント)│                       │  :5432    │  │
│  │              │     localhost:8667     └───────────┘  │
│  │              │ ─── (Toxiproxy) ────► ┌───────────┐  │
│  └──────────────┘                       │   redis   │  │
│                                         │  :6379    │  │
│  ┌──────────────┐                       └───────────┘  │
│  │  demo.sh /   │                                       │
│  │  chaos_api   │ ── REST ──► localhost:8474            │
│  │  (管理)      │             (Toxiproxy 管理 API)      │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

docker-compose 内部では Toxiproxy が `postgres:5432` / `redis:6379` を直接参照し、
ホストからは Toxiproxy 経由のポートで接続する。

---

## 使い方

### 1. 起動

```bash
cd scenarios/fault-injection
docker compose up -d
```

### 2. プロキシのセットアップ

```bash
./setup.sh
```

Toxiproxy に postgres / redis のプロキシを登録する。
（初回のみ。コンテナを削除すると再実行が必要）

### 3. デモ実行

#### シェルスクリプトで一通り体験

```bash
./demo.sh
```

自動で以下を実行する:
1. 正常時の計測
2. 遅延 (200ms + jitter 50ms) 注入 → 計測 → 解除
3. タイムアウト (50% 確率) 注入 → 失敗率確認 → 解除
4. 帯域制限 (10 KB/s) 注入 → 計測 → 解除

#### Python スクリプトで個別実行

```bash
# pip install psycopg[binary] redis requests が必要
python3 demo.py normal       # 正常時
python3 demo.py latency      # 遅延注入中の計測
python3 demo.py packet_loss  # パケットロス中の計測
python3 demo.py inject       # 自前で注入→計測→解除（フルデモ）
python3 demo.py reset        # 全 toxic をリセット
python3 demo.py proxies      # プロキシ一覧表示
```

### 4. 管理 API を直接触る

```bash
# プロキシ一覧
curl http://localhost:8474/proxies

# latency toxic を postgres に注入（200ms + jitter 50ms）
curl -X POST http://localhost:8474/proxies/postgres/toxics \
  -H "Content-Type: application/json" \
  -d '{"name":"my_delay","type":"latency","attributes":{"latency":200,"jitter":50}}'

# 削除
curl -X DELETE http://localhost:8474/proxies/postgres/toxics/my_delay
```

---

## フォールトタイプ一覧

| タイプ | 説明 | 主なパラメータ |
|--------|------|----------------|
| `latency` | 固定遅延を追加する（ジッターも設定可） | `latency`(ms), `jitter`(ms) |
| `bandwidth` | 帯域幅を KB/s 単位で制限する | `rate`(KB/s) |
| `slow_close` | TCP 接続のクローズを遅延させる | `delay`(ms) |
| `timeout` | 一定時間後に接続を切断する | `timeout`(ms) |
| `slicer` | TCP パケットを細かく分割して送信する | `average_size`(B), `delay`(µs) |
| `reset_peer` | TCP RST を送信して接続をリセットする | — |
| `limit_data` | 転送バイト数の上限を設定する | `bytes` |

各 toxic には **toxicity**（0.0～1.0）を設定でき、確率的に適用できる。
例: `"toxicity": 0.5` → 50% の確率でその toxic が適用される。

---

## CAP 定理との関係

CAP 定理は「分散システムは以下の 3 つを同時に保証できない」というもの:

- **C (Consistency)**: 全ノードが同じデータを見る
- **A (Availability)**: 全リクエストが（エラーなく）応答を返す
- **P (Partition Tolerance)**: ネットワーク分断が起きても動作する

ネットワーク障害（パーティション）が発生したとき、各 DB は以下の選択をする:

```
ネットワーク分断（P）が発生した場合:

  CP 系（一貫性 > 可用性）
  例: Zookeeper, etcd, HBase, MongoDB(w:majority)
    → 分断中はリクエストを拒否（エラーを返す）
    → データは常に一致している

  AP 系（可用性 > 一貫性）
  例: Cassandra, CouchDB, DynamoDB
    → 分断中もリクエストに応答する（古いデータかもしれない）
    → データは eventual consistency で最終的に一致する

  CA 系（分断耐性なし）
  例: 単一ノードの RDBMS (PostgreSQL 単体、MySQL 単体)
    → ネットワーク分断は前提としない
    → レプリカ構成では CP または AP の設定を選べる
```

Toxiproxy を使うことで、ネットワーク分断をシミュレーションし、
**各 DB がパーティション時にどう振る舞うか**を実際に確認できる。

---

## カオスエンジニアリングとは

> 「本番環境の障害は、テスト環境で先に経験しておくべき」

カオスエンジニアリングは、**意図的に障害を注入して、システムの耐障害性を検証・改善する手法**。
Netflix の [Chaos Monkey](https://github.com/Netflix/chaosmonkey) が有名。

### 典型的なフロー

```
1. 仮説を立てる
   「latency が 200ms 増加しても 99% のリクエストは成功するはず」

2. 実験設計
   Toxiproxy で 200ms latency を注入

3. 計測
   成功率・レイテンシ・エラーを記録

4. 結果分析
   仮説が崩れた箇所（タイムアウト不足、リトライなし等）を特定

5. 改善
   タイムアウト値を調整、サーキットブレーカーを導入、リトライを実装
```

### よくある改善点

- 適切なタイムアウト値の設定（接続・読み取り・書き込みそれぞれ）
- 指数バックオフ付きのリトライ
- サーキットブレーカー（一定以上のエラー率で即座に失敗させる）
- フォールバック処理（キャッシュ返却、デフォルト値使用）
- ヘルスチェックと自動フェイルオーバー

---

## 停止

```bash
docker compose down
```
