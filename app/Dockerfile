FROM python:3.12-slim

WORKDIR /app

# プロキシ設定（ビルド時のみ。環境変数から build args 経由で受け取り、イメージには残さない）
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY=""
ARG http_proxy=""
ARG https_proxy=""
ARG no_proxy=""

# 任意: TLS 傍受型プロキシ（社内プロキシ等）の独自 CA を信頼する。
# app/certs/ に *.crt を置くとビルド時に信頼ストアへ追加される（空でも可）。
COPY certs/ /usr/local/share/ca-certificates/extra/

# apt（http のため TLS 傍受の影響を受けない）で ca-certificates 等を導入し、独自CAを反映。
RUN HTTP_PROXY="$HTTP_PROXY" HTTPS_PROXY="$HTTPS_PROXY" NO_PROXY="$NO_PROXY" \
    http_proxy="$http_proxy" https_proxy="$https_proxy" no_proxy="$no_proxy" \
    apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates build-essential gcc \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# pip / requests / Node が共通の CA バンドル（独自CA反映済み）を参照するように
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

COPY requirements.txt .
# pip は HTTPS_PROXY/HTTP_PROXY と上記 CA バンドル（PIP_CERT）を参照する
RUN HTTP_PROXY="$HTTP_PROXY" HTTPS_PROXY="$HTTPS_PROXY" NO_PROXY="$NO_PROXY" \
    http_proxy="$http_proxy" https_proxy="$https_proxy" no_proxy="$no_proxy" \
    pip install --no-cache-dir -r requirements.txt

COPY server ./server
COPY web ./web

EXPOSE 8000
WORKDIR /app/server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
