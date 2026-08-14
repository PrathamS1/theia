#!/usr/bin/env bash
# scripts/start_hydradb.sh
# Starts a local HydraDB graph-node in development mode.
# Run from the hydradb repo root (NOT from this project root).
# Usage:  bash /path/to/company-brain/scripts/start_hydradb.sh
#
# Prerequisites: HydraDB built with `cargo build --locked --features server-runtime --bin graph-node`

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HYDRA_STORE="${SCRIPT_DIR}/../.hydradb/store"
HYDRA_CACHE="${SCRIPT_DIR}/../.hydradb/cache"
HYDRA_AUTH_TOKEN_FILE="${SCRIPT_DIR}/../.hydradb/auth-token"

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

# Must run from the hydradb repo root where Cargo.toml lives.
# If you cloned hydradb to ~/hydradb, run:
#   cd ~/hydradb && bash /path/to/company-brain/scripts/start_hydradb.sh
cargo run --locked --features server-runtime --bin graph-node
