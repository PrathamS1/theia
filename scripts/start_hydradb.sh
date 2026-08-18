#!/usr/bin/env bash
# scripts/start_hydradb.sh
# Starts the local HydraDB stack (MinIO + graph-node) via Docker.
#
#   bash scripts/start_hydradb.sh          # start (idempotent)
#   bash scripts/start_hydradb.sh --reset  # wipe the graph and start clean
#
# Requires: docker. No Rust toolchain, no local HydraDB build.
#
# WHY MinIO INSTEAD OF THE LOCAL FILESYSTEM
# -----------------------------------------
# HydraDB stores its graph in SlateDB, which updates its manifest with a
# conditional put (compare-and-swap). The object_store LocalFileSystem backend
# does not implement that operation:
#
#   object store error: Operation `put_opts` with mode `PutMode::Update`
#   not yet implemented by LocalFileSystem(file:///data/store)
#
# With CLOUD_PROVIDER=local, writes therefore succeed only while the store is
# fresh (pure appends) and then fail permanently. The symptom is an ingest that
# silently stalls partway -- e.g. 332 of 812 documents -- and never recovers,
# no matter how many times it is retried. MinIO speaks the S3 API and supports
# conditional writes, which makes graph writes work.

set -euo pipefail

MINIO_USER="${MINIO_ROOT_USER:-hydradbadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-hydradbadmin123}"
BUCKET="${HYDRA_BUCKET:-hydradb}"
NETWORK="hydranet"
AUTH_TOKEN="${HYDRA_AUTH_TOKEN:-local-development-token-32-bytes}"

if [ "${1:-}" = "--reset" ]; then
  echo "[reset] removing containers and volumes (graph data will be lost)"
  docker rm -f hydradb minio >/dev/null 2>&1 || true
  docker volume rm -f hydra-minio-data hydra-node-data >/dev/null 2>&1 || true
fi

docker network create "$NETWORK" >/dev/null 2>&1 || true
docker volume create hydra-minio-data >/dev/null
docker volume create hydra-node-data  >/dev/null

# ── MinIO (S3-compatible object store) ───────────────────────────────────────
if [ -z "$(docker ps -q -f name=^minio$)" ]; then
  docker rm -f minio >/dev/null 2>&1 || true
  echo "[minio] starting..."
  docker run -d --name minio --restart unless-stopped --network "$NETWORK" \
    -p 9000:9000 -p 9001:9001 \
    -v hydra-minio-data:/data \
    -e MINIO_ROOT_USER="$MINIO_USER" \
    -e MINIO_ROOT_PASSWORD="$MINIO_PASS" \
    minio/minio:latest server /data --console-address ":9001" >/dev/null
else
  echo "[minio] already running"
fi

echo "[minio] waiting for readiness..."
for _ in $(seq 1 60); do
  if docker run --rm --network "$NETWORK" --entrypoint sh minio/mc:latest -c \
      "mc alias set local http://minio:9000 $MINIO_USER $MINIO_PASS" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "[minio] ensuring bucket '$BUCKET' exists..."
docker run --rm --network "$NETWORK" --entrypoint sh minio/mc:latest -c \
  "mc alias set local http://minio:9000 $MINIO_USER $MINIO_PASS >/dev/null && \
   mc mb --ignore-existing local/$BUCKET" >/dev/null

# ── HydraDB graph-node ───────────────────────────────────────────────────────
# The image runs as uid 10001, but a freshly created Docker volume is owned by
# root -- so seed the auth token and fix ownership from a throwaway root
# container first. Without this, graph-node exits immediately with
# "cannot create /data/auth-token: Permission denied".
echo "[hydradb] preparing data volume..."
docker run --rm --user root --entrypoint sh \
  -v hydra-node-data:/data \
  ghcr.io/hydra-db/hydradb:latest \
  -c "printf '%s\n' '$AUTH_TOKEN' > /data/auth-token && mkdir -p /data/cache && chown -R 10001:10001 /data" >/dev/null
if [ -z "$(docker ps -q -f name=^hydradb$)" ]; then
  docker rm -f hydradb >/dev/null 2>&1 || true
  echo "[hydradb] starting..."
  docker run -d --name hydradb --restart unless-stopped --network "$NETWORK" \
    -p 7687:7687 -p 8443:8443 -p 9090:9090 \
    -v hydra-node-data:/data \
    -e CLOUD_PROVIDER=aws \
    -e AWS_ACCESS_KEY_ID="$MINIO_USER" \
    -e AWS_SECRET_ACCESS_KEY="$MINIO_PASS" \
    -e AWS_ENDPOINT=http://minio:9000 \
    -e AWS_BUCKET="$BUCKET" \
    -e AWS_REGION=us-east-1 \
    -e AWS_ALLOW_HTTP=true \
    -e AWS_CONDITIONAL_PUT=etag \
    -e GRAPH_ID=default \
    -e GRAPH_NAMESPACE=default \
    -e GRAPH_CELL_ID=cell-0 \
    -e GRAPH_CELLS=cell-0 \
    -e GRAPH_NODE_ID=node-0 \
    -e GRAPH_BOLT_NODE_ADDRESSES=node-0=0.0.0.0:7687 \
    -e GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687 \
    -e GRAPH_DATA_CACHE_DIR=/data/cache \
    -e GRAPH_AUTH_TOKEN_FILE=/data/auth-token \
    -e GRAPH_ALLOW_PLAINTEXT=true \
    -e RUST_MIN_STACK=33554432 \
    -e RUST_LOG=info \
    -e GRAPH_WRITER_LEASE_MS=300000 \
    ghcr.io/hydra-db/hydradb:latest >/dev/null
else
  echo "[hydradb] already running"
fi

echo "[hydradb] waiting for Bolt on 127.0.0.1:7687..."
for _ in $(seq 1 60); do
  if docker logs hydradb 2>&1 | grep -q "graph node listeners started"; then break; fi
  sleep 2
done

echo ""
echo "  Bolt:          bolt://127.0.0.1:7687"
echo "  HTTP:          http://127.0.0.1:8443"
echo "  Admin:         http://127.0.0.1:9090"
echo "  MinIO console: http://127.0.0.1:9001  ($MINIO_USER / $MINIO_PASS)"
echo ""
echo "  Next: PYTHONPATH=src python scripts/run_ingest.py"
