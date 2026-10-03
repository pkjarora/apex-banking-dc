#!/usr/bin/env bash
# Run the banking DC app locally for quick preview.
# Uses only Python stdlib — no pip installs needed.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

rm -f /tmp/apex-banking.db

DB_PATH=/tmp/apex-banking.db \
CLUSTER_NAME="k8s-dc-primary-mumbai" \
DATACENTER="Primary Datacenter" \
DC_REGION="ap-south-1 (Mumbai)" \
NODE_NAME="k8s-worker-node-01" \
POD_NAME="banking-app-dc-7d9f8b-x2kpq" \
K8S_NAMESPACE="banking" \
PORT=8080 \
python3 "$ROOT/app/server.py"
