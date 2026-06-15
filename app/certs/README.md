# certs/ — 社内プロキシ等の独自 CA 証明書置き場

TLS 傍受型のプロキシ（企業の secure web proxy / egress gateway 等）を使う環境では、
プロキシが提示する **独自ルート CA** を信頼しないと pip / requests / npm が
`CERTIFICATE_VERIFY_FAILED` で失敗します。

## 使い方

プロキシの CA 証明書（PEM 形式・拡張子 `.crt`）をこのディレクトリに置いてください。

```bash
cp /path/to/corporate-proxy-ca.crt app/certs/
make app   # ビルド時に update-ca-certificates で信頼ストアへ追加される
```

- 複数の `.crt` を置けます。
- 証明書ファイル（`*.crt` / `*.pem`）は `.gitignore` 済みでコミットされません。
- 不要な場合は空のままで構いません（通常のTLSはそのまま動作します）。

## ローカル実行（Docker を使わない場合）

ホスト側で CA を信頼させ、環境変数で参照させます（多くの環境で設定済み）。

```bash
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
```
