// 各 DB の教育的コンテンツ（解説タブで表示）。
// fields: tagline / docs[] / overview / features[] / usecases[] / architecture[]
// 学習用の要点をまとめたもの。正確性は公式ドキュメント（docs[]）を参照。
const DB_CONTENT = {
  postgresql: {
    tagline: "高機能で拡張性の高いオープンソース RDBMS のデファクト",
    docs: [
      { label: "公式ドキュメント", url: "https://www.postgresql.org/docs/" },
      { label: "チュートリアル", url: "https://www.postgresql.org/docs/current/tutorial.html" },
      { label: "SQL コマンド一覧", url: "https://www.postgresql.org/docs/current/sql-commands.html" },
    ],
    overview: "ACID トランザクション・MVCC・豊富なデータ型（JSONB / 配列 / 範囲型 / 地理空間）を備えた汎用 RDBMS。標準 SQL 準拠度が高く、拡張（pgvector / PostGIS / TimescaleDB）でユースケースを広げられる。",
    features: [
      "MVCC による高い同時実行性（読み取りが書き込みをブロックしない）",
      "JSONB でドキュメント的な柔軟性も両立",
      "豊富なインデックス（B-tree / GIN / GiST / BRIN / Hash）",
      "ウィンドウ関数・CTE・パーティショニング・論理レプリケーション",
      "拡張機構で機能追加（pgvector, PostGIS, pg_partman 等）",
    ],
    usecases: [
      "Web/業務アプリの基幹トランザクション DB",
      "JSONB を活かした半構造化データの格納",
      "分析クエリ（ウィンドウ関数・集計）も同居させたい中規模システム",
    ],
    architecture: [
      "アプリ → コネクションプーラ（PgBouncer）→ PostgreSQL の構成で接続数を抑制",
      "読み取りスケールはストリーミングレプリケーションのリードレプリカで分散",
      "全文検索や類似検索は拡張（pg_trgm / pgvector）で外部 DB を増やさず実現",
    ],
  },

  mysql: {
    tagline: "Web で最も普及した実績豊富な RDBMS",
    docs: [
      { label: "公式ドキュメント", url: "https://dev.mysql.com/doc/" },
      { label: "リファレンスマニュアル", url: "https://dev.mysql.com/doc/refman/8.0/en/" },
      { label: "チュートリアル", url: "https://dev.mysql.com/doc/refman/8.0/en/tutorial.html" },
    ],
    overview: "LAMP スタックの定番。InnoDB による ACID トランザクションとリードレプリケーションが手堅く、運用ノウハウとホスティング対応が非常に厚い。MySQL 8.0 で CTE・ウィンドウ関数・JSON が強化された。",
    features: [
      "InnoDB（行ロック・トランザクション・外部キー）",
      "シンプルで高速なプライマリキー参照",
      "非同期/準同期レプリケーションと豊富な運用ツール",
      "MySQL 8.0: 共通テーブル式・ウィンドウ関数・JSON 関数",
    ],
    usecases: [
      "CMS / EC / SaaS など読み取り中心の Web アプリ",
      "マネージドサービス（RDS / Cloud SQL 等）での標準採用",
      "シャーディング前提の大規模 Web サービス",
    ],
    architecture: [
      "1 プライマリ + 複数リードレプリカで読み取りスケールアウト",
      "ProxySQL 等で読み書きを振り分け",
      "大規模時はアプリ層 or Vitess でシャーディング",
    ],
  },

  sqlite: {
    tagline: "サーバ不要・単一ファイルの組込 SQL DB（世界で最も普及）",
    docs: [
      { label: "公式サイト", url: "https://www.sqlite.org/docs.html" },
      { label: "適材適所（When to use）", url: "https://www.sqlite.org/whentouse.html" },
      { label: "SQL 構文", url: "https://www.sqlite.org/lang.html" },
    ],
    overview: "プロセス内で動作しデータを 1 ファイルに格納する組込 DB。サーバや設定が不要で、アプリに同梱できる。トランザクション（ACID）対応。本リポジトリではアプリ内（インプロセス）で直接ファイルを操作する。",
    features: [
      "サーバ不要・ゼロ設定・単一ファイル",
      "小さなフットプリントで ACID トランザクション",
      "ほぼ全環境・全言語にバインディングが存在",
      "読み取りは高速だが書き込みは単一ライタ（同時書き込みに弱い）",
    ],
    usecases: [
      "モバイル/デスクトップアプリのローカル保存",
      "アプリ設定・キャッシュ・テスト用データストア",
      "データ分析の中間ファイル・配布用データセット",
    ],
    architecture: [
      "アプリと同一プロセスでファイルを開く（ネットワーク不要）",
      "高並行な書き込みが必要なら WAL モードを有効化",
      "サーバ型が必要になったら PostgreSQL / MySQL へ移行",
    ],
  },

  mongodb: {
    tagline: "柔軟なスキーマのドキュメント指向 NoSQL",
    docs: [
      { label: "公式マニュアル", url: "https://www.mongodb.com/docs/manual/" },
      { label: "CRUD 操作", url: "https://www.mongodb.com/docs/manual/crud/" },
      { label: "Aggregation", url: "https://www.mongodb.com/docs/manual/aggregation/" },
    ],
    overview: "JSON ライクな BSON ドキュメントを格納する NoSQL。スキーマレスで開発初期の変更に強く、シャーディングで水平スケールする。集計パイプラインで複雑な変換・集計も可能。",
    features: [
      "スキーマレスなドキュメント（埋め込みで関連を表現）",
      "Aggregation Pipeline による柔軟な集計",
      "レプリカセットによる高可用、シャーディングで水平分割",
      "セカンダリインデックス・地理空間・全文検索",
    ],
    usecases: [
      "仕様が流動的な Web/モバイルの API バックエンド",
      "カタログ・CMS・ユーザープロファイルなど形が一定でないデータ",
      "イベント/ログの一時集約",
    ],
    architecture: [
      "レプリカセット（プライマリ + セカンダリ）で冗長化",
      "シャードキー設計で水平スケール（ホットスポットに注意）",
      "リレーション過多なら参照より埋め込みでクエリ回数を削減",
    ],
  },

  redis: {
    tagline: "超低レイテンシのインメモリ KVS / データ構造サーバ",
    docs: [
      { label: "公式ドキュメント", url: "https://redis.io/docs/latest/" },
      { label: "コマンド一覧", url: "https://redis.io/commands/" },
      { label: "データ型", url: "https://redis.io/docs/latest/develop/data-types/" },
    ],
    overview: "メモリ上でデータを保持しサブミリ秒で応答する KVS。String 以外に List / Hash / Set / Sorted Set / Stream など豊富なデータ構造を持ち、キャッシュ・キュー・ランキング・レート制限などに使える。",
    features: [
      "インメモリでサブミリ秒の読み書き",
      "豊富なデータ構造（Hash / Sorted Set / Stream / HyperLogLog 等）",
      "TTL による自動失効・Pub/Sub・Lua スクリプト",
      "RDB/AOF 永続化、レプリケーション、Cluster で分散",
    ],
    usecases: [
      "DB 前段のキャッシュ（読み取り負荷の軽減）",
      "セッションストア・レート制限・分散ロック",
      "リアルタイムランキング（Sorted Set）・ジョブキュー（Stream）",
    ],
    architecture: [
      "アプリ → Redis（キャッシュ）→ 永続 DB の Cache-Aside パターン",
      "高可用は Sentinel、スケールは Redis Cluster（ハッシュスロット）",
      "メモリ上限と eviction ポリシー（LRU/LFU）の設計が重要",
    ],
  },

  cassandra: {
    tagline: "大量書き込みに強い分散ワイドカラム DB",
    docs: [
      { label: "公式ドキュメント", url: "https://cassandra.apache.org/doc/latest/" },
      { label: "CQL リファレンス", url: "https://cassandra.apache.org/doc/latest/cassandra/cql/" },
      { label: "データモデリング", url: "https://cassandra.apache.org/doc/latest/cassandra/data_modeling/" },
    ],
    overview: "マスターレス（全ノード対等）で線形にスケールする分散 DB。書き込みが非常に高速で、単一障害点がない。クエリ駆動でテーブルを設計（クエリごとにテーブルを作る）する点が RDB と大きく異なる。",
    features: [
      "マスターレス構成で単一障害点なし・線形スケール",
      "書き込み最適化（LSM ツリー）で高スループット",
      "調整可能な整合性（ONE / QUORUM / ALL）",
      "マルチデータセンタレプリケーション",
    ],
    usecases: [
      "IoT / 時系列 / イベントログの大量書き込み",
      "メッセージング・アクティビティフィード",
      "地理分散で常時可用性が必要なシステム",
    ],
    architecture: [
      "パーティションキーでノードに分散（ホットパーティション回避が肝）",
      "クエリ駆動設計: JOIN しない前提でテーブルを非正規化",
      "整合性レベルでレイテンシ vs 一貫性をトレードオフ",
    ],
  },

  neo4j: {
    tagline: "関係性の探索に最適化したグラフ DB",
    docs: [
      { label: "公式ドキュメント", url: "https://neo4j.com/docs/" },
      { label: "Cypher マニュアル", url: "https://neo4j.com/docs/cypher-manual/current/" },
      { label: "Getting Started", url: "https://neo4j.com/docs/getting-started/" },
    ],
    overview: "ノードと関係（エッジ）でデータを表現するグラフ DB。多段のリレーション探索（友達の友達、推薦、経路探索）が RDB の多段 JOIN より高速かつ直感的。Cypher という宣言的クエリ言語を使う。",
    features: [
      "ネイティブグラフ（隣接ノードを直接辿る）で深い探索が高速",
      "Cypher による直感的なパターンマッチ記法",
      "ACID トランザクション対応",
      "Graph Data Science ライブラリ（中心性・コミュニティ検出）",
    ],
    usecases: [
      "推薦エンジン・ソーシャルグラフ",
      "不正検知（取引ネットワークの異常パターン）",
      "ナレッジグラフ・経路/依存関係の探索",
    ],
    architecture: [
      "RDB の正規化された関連を「関係」として表現し多段 JOIN を排除",
      "RAG のナレッジグラフ層として LLM と連携（GraphRAG）",
      "因果/依存の可視化やインパクト分析の基盤",
    ],
  },

  cockroachdb: {
    tagline: "PostgreSQL 互換でグローバルに水平スケールする分散 SQL",
    docs: [
      { label: "公式ドキュメント", url: "https://www.cockroachlabs.com/docs/" },
      { label: "SQL リファレンス", url: "https://www.cockroachlabs.com/docs/stable/sql-statements" },
      { label: "アーキテクチャ", url: "https://www.cockroachlabs.com/docs/stable/architecture/overview" },
    ],
    overview: "PostgreSQL ワイヤプロトコル互換でありながら、自動シャーディング・自動リバランス・地理分散を備えた NewSQL。強整合（Serializable）を保ったまま水平スケールし、ノード障害時も自動で復旧する。",
    features: [
      "PostgreSQL 互換（既存ドライバ/SQL を活用）",
      "分散トランザクションで Serializable な強整合",
      "データを Range に自動分割し自動リバランス・自己修復",
      "マルチリージョンでデータの所在（地理）を制御",
    ],
    usecases: [
      "グローバル展開で低レイテンシ＋強整合が必要な SaaS",
      "ゼロダウンタイムのスケール/アップグレードが要件のシステム",
      "リージョン障害に耐える金融/決済系",
    ],
    architecture: [
      "アプリは PostgreSQL ドライバでそのまま接続",
      "リージョンごとにノードを配置し、行の所在をポリシで制御",
      "シングルノード RDB の限界を、書き換え少なくスケールアウト",
    ],
  },

  influxdb: {
    tagline: "メトリクス/IoT 向けの時系列特化 DB",
    docs: [
      { label: "公式ドキュメント", url: "https://docs.influxdata.com/" },
      { label: "Flux 言語", url: "https://docs.influxdata.com/flux/v0/" },
      { label: "Line Protocol", url: "https://docs.influxdata.com/influxdb/v2/reference/syntax/line-protocol/" },
    ],
    overview: "タイムスタンプ付きの測定値（measurement / tag / field）に特化した時系列 DB。高頻度の書き込みとダウンサンプリング・保持ポリシー（古いデータの自動削除）に強い。クエリは Flux（または InfluxQL）。",
    features: [
      "時系列に最適化した書き込み/圧縮",
      "Retention Policy で古いデータを自動失効",
      "ダウンサンプリング・連続集計",
      "Line Protocol によるシンプルな書き込み",
    ],
    usecases: [
      "サーバ/アプリのメトリクス監視",
      "IoT センサーデータの収集",
      "リアルタイムダッシュボード（Grafana 連携）",
    ],
    architecture: [
      "Telegraf でメトリクス収集 → InfluxDB → Grafana で可視化",
      "高頻度の生データは短期保持、集計値は長期保持に分離",
      "タグ設計（カーディナリティ）がパフォーマンスを左右",
    ],
  },

  timescaledb: {
    tagline: "PostgreSQL 拡張として動く時系列 DB",
    docs: [
      { label: "公式ドキュメント", url: "https://docs.timescale.com/" },
      { label: "Hypertable", url: "https://docs.timescale.com/use-timescale/latest/hypertables/" },
      { label: "Continuous Aggregates", url: "https://docs.timescale.com/use-timescale/latest/continuous-aggregates/" },
    ],
    overview: "PostgreSQL の拡張として時系列機能を追加する DB。普通の SQL とエコシステムをそのまま使いつつ、Hypertable による自動パーティショニングや連続集計で時系列を効率化できる。「SQL を捨てたくない時系列」に最適。",
    features: [
      "完全な PostgreSQL（SQL・JOIN・拡張がそのまま使える）",
      "Hypertable で時間/空間に自動パーティション分割",
      "Continuous Aggregates（増分マテビュー）で集計を高速化",
      "圧縮・データ保持ポリシーで古いデータを節約",
    ],
    usecases: [
      "メトリクス/IoT を SQL と既存ツールで扱いたい場合",
      "時系列 + 関係データ（メタ情報の JOIN）を同居",
      "金融の時系列・分析",
    ],
    architecture: [
      "既存の PostgreSQL 資産（BI/ORM）をそのまま流用",
      "生データは Hypertable、表示用は連続集計ビューで分離",
      "time_bucket() で時間窓集計、圧縮で長期保持",
    ],
  },

  opensearch: {
    tagline: "全文検索・ログ分析の分散検索エンジン（Elasticsearch 派生）",
    docs: [
      { label: "公式ドキュメント", url: "https://opensearch.org/docs/latest/" },
      { label: "Query DSL", url: "https://opensearch.org/docs/latest/query-dsl/" },
      { label: "REST API", url: "https://opensearch.org/docs/latest/api-reference/" },
    ],
    overview: "転置インデックスによる全文検索と、ログ/メトリクスの分析に強い分散エンジン。Apache 2.0 ライセンスの Elasticsearch フォーク。スコアリングされた関連度検索、集約（Aggregations）、ダッシュボード（OpenSearch Dashboards）を備える。",
    features: [
      "転置インデックスによる高速な全文検索・関連度スコアリング",
      "Aggregations による分析・ファセット",
      "シャード/レプリカで水平スケール・冗長化",
      "ベクトル検索（k-NN）プラグインで意味検索も",
    ],
    usecases: [
      "サイト内検索・商品検索・オートコンプリート",
      "ログ集約・可観測性（ELK/OpenSearch スタック）",
      "セキュリティ分析（SIEM）",
    ],
    architecture: [
      "アプリ → 検索クエリは OpenSearch、正データは別 DB（CDC で同期）",
      "ログは Fluent Bit / Logstash → OpenSearch → Dashboards",
      "意味検索は k-NN プラグイン + 埋め込みでハイブリッド検索",
    ],
  },

  clickhouse: {
    tagline: "超高速な列指向 OLAP（分析）DB",
    docs: [
      { label: "公式ドキュメント", url: "https://clickhouse.com/docs" },
      { label: "SQL リファレンス", url: "https://clickhouse.com/docs/sql-reference" },
      { label: "MergeTree エンジン", url: "https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree" },
    ],
    overview: "列指向ストレージと高い圧縮率で、巨大テーブルの集計クエリを桁違いに高速化する OLAP DB。数十億行のスキャン集計が秒で返る。MergeTree エンジン系がコア。リアルタイム分析に向く一方、単一行の更新/削除は不得手。",
    features: [
      "列指向 + ベクトル化実行 + 高圧縮で集計が高速",
      "MergeTree 系エンジン（パーティション/プライマリインデックス）",
      "マテリアライズドビューで取り込み時に集計",
      "分散テーブルで水平スケール",
    ],
    usecases: [
      "プロダクト分析・行動ログの集計（イベント分析）",
      "可観測性（メトリクス/トレースの大規模集計）",
      "リアルタイムダッシュボード・BI バックエンド",
    ],
    architecture: [
      "イベントを Kafka → ClickHouse に取り込み、MV で事前集計",
      "OLTP（Postgres）+ OLAP（ClickHouse）の役割分担",
      "更新は追記 + 集計で表現（行単位 UPDATE は避ける）",
    ],
  },

  duckdb: {
    tagline: "インプロセスで動く「分析の SQLite」",
    docs: [
      { label: "公式ドキュメント", url: "https://duckdb.org/docs/" },
      { label: "SQL 入門", url: "https://duckdb.org/docs/sql/introduction" },
      { label: "データインポート", url: "https://duckdb.org/docs/data/overview" },
    ],
    overview: "サーバ不要でアプリ/ノートブックに組み込める列指向の分析 DB。Parquet/CSV を直接クエリでき、Pandas/Polars と高速に連携。ローカルでの分析・ETL・前処理に最適。本リポジトリではアプリ内で直接ファイルを操作する。",
    features: [
      "ゼロ設定・組込（サーバ不要）で列指向 OLAP",
      "Parquet / CSV / JSON を直接 SQL でクエリ",
      "Pandas / Polars / Arrow とゼロコピー連携",
      "ベクトル化実行で単一マシンでも高速集計",
    ],
    usecases: [
      "データ分析・ノートブックでの探索的集計",
      "ローカル/エッジでの ETL・前処理",
      "Parquet データレイクへのアドホッククエリ",
    ],
    architecture: [
      "Python/アプリに同梱し、S3/ローカルの Parquet を直接集計",
      "前処理を DuckDB で行い、結果のみ DWH に投入",
      "大規模・共有が必要になったら ClickHouse 等のサーバ型へ",
    ],
  },

  qdrant: {
    tagline: "AI/RAG 向けのベクトル類似検索エンジン",
    docs: [
      { label: "公式ドキュメント", url: "https://qdrant.tech/documentation/" },
      { label: "REST/gRPC API", url: "https://api.qdrant.tech/" },
      { label: "コンセプト", url: "https://qdrant.tech/documentation/concepts/" },
    ],
    overview: "埋め込みベクトルの近似最近傍探索（ANN）に特化した専用 DB。HNSW インデックスで高速な類似検索を行い、ペイロード（メタデータ）によるフィルタ付き検索が得意。LLM の RAG / 推薦 / 画像検索のバックエンドに使われる。",
    features: [
      "HNSW による高速・高精度な近似最近傍探索",
      "ペイロードフィルタ付き検索（条件 + 類似度）",
      "距離指標を選択（Cosine / Dot / Euclid）",
      "量子化でメモリ削減・スケール",
    ],
    usecases: [
      "RAG（文書チャンクの意味検索 → LLM 文脈に投入）",
      "レコメンド・類似画像/商品検索",
      "重複検出・異常検知",
    ],
    architecture: [
      "文書 → 埋め込みモデル → Qdrant に upsert、検索時に近傍取得 → LLM",
      "メタデータでテナント/カテゴリを絞り込みつつ類似検索",
      "キーワード検索（OpenSearch）とハイブリッドして精度向上",
    ],
  },

  pgvector: {
    tagline: "PostgreSQL にベクトル検索を足す拡張",
    docs: [
      { label: "GitHub / README", url: "https://github.com/pgvector/pgvector" },
      { label: "PostgreSQL ドキュメント", url: "https://www.postgresql.org/docs/" },
    ],
    overview: "PostgreSQL に vector 型と類似検索（<->, <#>, <=>）を追加する拡張。既存の RDB に専用ベクトル DB を増やさず、SQL の WHERE/JOIN と類似検索を同じクエリで併用できるのが最大の利点。中小規模の RAG に手軽。",
    features: [
      "vector 型と距離演算子（L2 / 内積 / コサイン）",
      "HNSW / IVFFlat インデックスで近似最近傍探索",
      "通常の SQL（フィルタ・JOIN・トランザクション）と同居",
      "既存 PostgreSQL 運用にそのまま乗る",
    ],
    usecases: [
      "既に Postgres を使うアプリへの RAG/類似検索の追加",
      "メタデータ条件 + 類似度を 1 クエリで",
      "中小規模の意味検索・推薦",
    ],
    architecture: [
      "本文 + 埋め込みを同じテーブルに格納し WHERE で絞って ORDER BY 距離",
      "DB を増やさず構成をシンプルに保つ",
      "規模が専用 DB を要するほど大きくなったら Qdrant 等へ移行",
    ],
  },
};
