# プロキシ環境での利用

本リポジトリは多数のコンテナイメージ取得・Python パッケージ取得を行います。
社内プロキシ等の環境では各ツールにプロキシ設定が必要です。
本リポジトリは **プロキシを環境変数から取得**する方針で統一しています。

## 0. 前提となる環境変数

標準的なプロキシ環境変数を export します（ツールにより大文字/小文字どちらを参照するかが
異なるため、両方を設定するのが安全です）。

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1,::1
# 小文字版（curl/requests 等は小文字を参照することがある）
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export no_proxy="$NO_PROXY"
```

> **重要**: `NO_PROXY` に必ず `localhost,127.0.0.1` を含めてください。
> 各 DB へは `localhost:<port>` で接続するため、除外しないと DB アクセスがプロキシに回り失敗します。

## CA 証明書（TLS 傍受型プロキシの場合）

企業の secure web proxy / egress gateway などは、HTTPS を**傍受して独自のルート CA で
再署名**します。この CA を信頼しないと、pip / requests / npm が
`CERTIFICATE_VERIFY_FAILED`（self-signed certificate in certificate chain）で失敗します。

CA バンドルは環境変数で参照されます（多くの環境で設定済み）。

```bash
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt      # OpenSSL/requests 等
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt # requests/pip
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt # Node/npm
```

- **ローカル実行**: 上記が設定されていれば pip / アプリの `requests` はそのまま動作します。
- **Docker ビルド**: コンテナ内には独自 CA が無いため、`app/certs/` に CA（`*.crt`）を置くと
  ビルド時に `update-ca-certificates` で信頼ストアへ追加されます（詳細は
  [`app/certs/README.md`](../app/certs/README.md)）。証明書はコミットされません（`.gitignore` 済み）。

## 1. Docker（イメージ取得）

`make up DB=...` や `docker compose up` のイメージ pull は、**Docker デーモン**の
プロキシ設定を使います（シェルや compose の環境変数ではありません）。次のいずれかを設定します。

**A. クライアント設定 `~/.docker/config.json`**

```json
{
  "proxies": {
    "default": {
      "httpProxy":  "http://proxy.example.com:8080",
      "httpsProxy": "http://proxy.example.com:8080",
      "noProxy":    "localhost,127.0.0.1"
    }
  }
}
```

**B. デーモン（systemd）設定**

`/etc/systemd/system/docker.service.d/http-proxy.conf`:

```ini
[Service]
Environment="HTTP_PROXY=http://proxy.example.com:8080"
Environment="HTTPS_PROXY=http://proxy.example.com:8080"
Environment="NO_PROXY=localhost,127.0.0.1"
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart docker
```

## 2. アプリのビルド（pip / apt）

`make app`（= `app/` の `docker compose build`）は、**シェルのプロキシ環境変数を
build args として渡し**、コンテナ内の apt / pip がそれを使うように設定済みです
（[`app/docker-compose.yml`](../app/docker-compose.yml) と [`app/Dockerfile`](../app/Dockerfile)）。

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
make app   # build 時に pip/apt がプロキシ経由
```

- プロキシ値は **build args としてのみ使用し、イメージには残しません**（実行時の環境変数には焼き込まれません）。
- 実行時は `app/docker-compose.yml` の `no_proxy` 既定設定により、`localhost` の DB 接続はプロキシを経由しません。
- TLS 傍受型プロキシの場合は、CA を `app/certs/*.crt` に置くとビルド時に信頼されます（上の「CA 証明書」節）。

## 3. pip（ローカル実行）

pip は `HTTP_PROXY` / `HTTPS_PROXY` を自動参照します。明示する場合:

```bash
pip install --proxy "$HTTPS_PROXY" -r app/requirements.txt
```

恒久設定（任意）— `~/.config/pip/pip.conf`:

```ini
[global]
proxy = http://proxy.example.com:8080
```

## 4. npm / Node（将来 Node ツールを使う場合）

現状 Node は未使用ですが、追加する場合 npm も `HTTP_PROXY` / `HTTPS_PROXY` を参照します。
プロジェクトに `.npmrc` を置く場合は環境変数を展開できます:

```
proxy=${HTTP_PROXY}
https-proxy=${HTTPS_PROXY}
noproxy=${NO_PROXY}
```

または CLI で明示:

```bash
npm config set proxy "$HTTP_PROXY"
npm config set https-proxy "$HTTPS_PROXY"
```

## 5. 動作確認

```bash
# プロキシ経由でイメージが pull できるか
docker pull hello-world

# アプリのビルド（pip/apt がプロキシ経由）
make app
```

うまくいかない場合は、`NO_PROXY` に `localhost,127.0.0.1` が含まれているか、
Docker デーモンのプロキシ設定（セクション1）が反映されているか（`sudo systemctl show docker --property Environment`）を確認してください。
