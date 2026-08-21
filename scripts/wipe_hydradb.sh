#!/usr/bin/env bash
# scripts/wipe_hydradb.sh — Wipes all persistent HydraDB graph data and local vector embeddings.

set -euo pipefail

echo "🧹 Wiping HydraDB store and cache (~/hydradb_store/)..."
rm -rf "${HOME}/hydradb_store/store"/* "${HOME}/hydradb_store/cache"/*

echo "🧹 Wiping local vector embeddings & live workspace data..."
rm -rf data/vectors/* data/live/*

echo "✅ Wipe complete! All graph nodes, relationships, and vector embeddings have been removed."
echo "👉 Now start HydraDB cleanly with: bash scripts/start_hydradb.sh"
