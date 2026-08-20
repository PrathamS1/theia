#!/usr/bin/env bash
# scripts/start_hydradb.sh
# Starts a local HydraDB graph-node in development mode.
# Can be run directly from the theia project root:
#   bash scripts/start_hydradb.sh
#
# Prerequisites: HydraDB built with `cargo build --locked --features server-runtime --bin graph-node`

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Store on native Linux ext4 filesystem to avoid /mnt/c/ NTFS fsync overhead (~1000x faster)
HYDRA_STORE="${HOME}/hydradb_store/store"
HYDRA_CACHE="${HOME}/hydradb_store/cache"
HYDRA_AUTH_TOKEN_FILE="${HOME}/hydradb_store/auth-token"

mkdir -p "$HYDRA_STORE" "$HYDRA_CACHE"

if [ ! -f "$HYDRA_AUTH_TOKEN_FILE" ]; then
  printf '%s\n' 'local-development-token-32-bytes' > "$HYDRA_AUTH_TOKEN_FILE"
  echo "[hydradb] Created auth token at $HYDRA_AUTH_TOKEN_FILE"
fi

export CLOUD_PROVIDER=local
export LOCAL_PATH="$HYDRA_STORE"
export GRAPH_NAMESPACE=default
export GRAPH_ID=default
export GRAPH_CELL_ID=cell-0
export GRAPH_CELLS=cell-0
export GRAPH_NODE_ID=node-0
export GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687
export GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687
export GRAPH_DATA_CACHE_DIR="$HYDRA_CACHE"
export GRAPH_AUTH_TOKEN_FILE="$HYDRA_AUTH_TOKEN_FILE"
export GRAPH_ALLOW_PLAINTEXT=true
export RUST_MIN_STACK=33554432

echo "[hydradb] Starting graph-node..."
echo "  Bolt:  bolt://127.0.0.1:7687"
echo "  HTTP:  http://127.0.0.1:8443"
echo "  Admin: http://127.0.0.1:9090"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

# Use compiled binary if available, otherwise cargo run
GRAPH_NODE_BIN="/home/pratham/projects/hydradb/target/debug/graph-node"
if [ -f "$GRAPH_NODE_BIN" ]; then
  exec "$GRAPH_NODE_BIN"
else
  cd /home/pratham/projects/hydradb && exec cargo run --locked --features server-runtime --bin graph-node
fi
