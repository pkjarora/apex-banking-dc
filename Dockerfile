FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck probe
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY app/ /app/

# Nutanix NDK will attach/replicate the volume at /data
RUN mkdir -p /data && chmod 777 /data

ENV PORT=8080 \
    HOST=0.0.0.0 \
    DB_PATH=/data/banking.db

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --retries=3 \
  CMD curl -sf http://localhost:8080/healthz || exit 1

ENTRYPOINT ["python3", "server.py"]
