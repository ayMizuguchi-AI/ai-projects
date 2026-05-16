# 1
# 必要なものをダウンロード
FROM python:3.12-slim AS builder
WORKDIR /app

# ライブラリのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# コードをコピー
COPY src/ ./src/
RUN python -m compileall -q src/

# 実行用のきれいな箱を作る
FROM python:3.12-slim
WORKDIR /app

# 2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir output

# 1で入れたライブラリとコードだけをコピー
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src/ ./src/

COPY data/ ./data/

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 実行コマンド
CMD ["python", "src/main.py"]
