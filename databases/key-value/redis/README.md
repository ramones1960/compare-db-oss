# Redis

| 項目 | 内容 |
|---|---|
| カテゴリ | キーバリュー |
| データモデル | KV / インメモリ |
| 主な用途 | キャッシュ・セッション・キュー・レートリミット |
| デフォルトポート | 6379 |
| イメージ | `redis:7` |

## 概要

Redis はインメモリの KVS。文字列だけでなく List / Set / Sorted Set / Hash /
Stream など豊富なデータ構造を持ち、サブミリ秒のレイテンシで動作する。
AOF / RDB による永続化、Pub/Sub、クラスタにも対応。

## 向いている用途・向かない用途

- **向いている**: キャッシュ、セッションストア、ランキング（Sorted Set）、ジョブキュー、レートリミッタ
- **向かない**: 大容量データの恒久保存（メモリ制約）、複雑なクエリ・結合

## 長所・短所

| 長所 | 短所 |
|---|---|
| 超低レイテンシ・高スループット | データ量がメモリに律速される |
| 多彩なデータ構造 | 複雑なクエリは不可 |
| シンプルな運用 | 強整合トランザクションは限定的 |

## 起動方法

```bash
make up DB=redis
```

## 基本操作

```bash
# redis-cli で接続（パスワードは .env の DB_PASSWORD）
docker exec -it cmp-redis redis-cli -a changeme

# サンプル操作を流す
docker exec -i cmp-redis sh < examples/basic.sh
```

詳細は [examples/basic.sh](examples/basic.sh) を参照。

## 性能検証

`redis-benchmark` で SET / GET のスループットを計測する。

```bash
make bench DB=redis
```

## 参考リンク

- 公式ドキュメント: https://redis.io/docs/
