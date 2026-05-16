FROM python:3.12-slim AS builder

WORKDIR /app
COPY src/ ./src/
RUN python -m compileall -q src/

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/src/ ./src/

CMD ["python", "src/main.py"]
