#!/usr/bin/env bash
# scripts/download_dataset.sh
# Downloads the EnterpriseRAG-Bench v1.0.0 dataset from GitHub releases.
# Run this from WSL inside the company-brain project root.
#
# Usage:
#   bash scripts/download_dataset.sh [--all | --questions-only | --source <name>]
#
# Options:
#   --all             Download all_documents.zip (~1.2 GB) — one file, all sources
#   --questions-only  Download only questions.jsonl + extra_questions.jsonl (small, ~500KB)
#   --source <name>   Download slices for a specific source (slack|gmail|linear|drive|hubspot|fireflies|github|confluence)
#
# Default (no args): downloads questions only + one slice per source (fast, enough for Day 1 hand-read)

set -euo pipefail

BASE_URL="https://github.com/onyx-dot-app/EnterpriseRAG-Bench/releases/download/v1.0.0"
DATA_DIR="data/raw"
QUESTIONS_DIR="data/questions"

mkdir -p "$DATA_DIR" "$QUESTIONS_DIR"

download() {
  local url="$1"
  local dest="$2"
  if [ -f "$dest" ]; then
    echo "[skip] Already exists: $dest"
  else
    echo "[dl] $url"
    curl -L --progress-bar -o "$dest" "$url"
  fi
}

extract_zip() {
  local zip_file="$1"
  local dest_dir="$2"
  if command -v unzip >/dev/null 2>&1; then
    unzip -q -o "$zip_file" -d "$dest_dir"
  else
    echo "[extract] Using Python zipfile module..."
    python3 -c "import zipfile, sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$zip_file" "$dest_dir"
  fi
}

download_questions() {
  echo "=== Downloading gold question sets ==="
  download "$BASE_URL/questions.jsonl"       "$QUESTIONS_DIR/questions.jsonl"
  download "$BASE_URL/extra_questions.jsonl" "$QUESTIONS_DIR/extra_questions.jsonl"
  echo "Done. Questions in: $QUESTIONS_DIR/"
}

download_all() {
  echo "=== Downloading all_documents.zip (~1.2 GB) ==="
  download "$BASE_URL/all_documents.zip" "$DATA_DIR/all_documents.zip"
  echo "Extracting..."
  extract_zip "$DATA_DIR/all_documents.zip" "$DATA_DIR/"
  echo "Done."
}

download_source_slices() {
  local source="$1"
  echo "=== Downloading slices for source: $source ==="
  mkdir -p "$DATA_DIR/$source"
  local i=1
  while true; do
    local slice=$(printf "%04d" $i)
    local fname="${source}_slice_${slice}.zip"
    local url="$BASE_URL/$fname"
    # Try to download; if 404, we've exhausted the slices
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -L "$url")
    if [ "$http_code" = "404" ]; then
      echo "[done] No more slices for $source (stopped at slice $slice)"
      break
    fi
    download "$url" "$DATA_DIR/$fname"
    extract_zip "$DATA_DIR/$fname" "$DATA_DIR/$source/"
    i=$((i + 1))
  done
}

download_first_slices() {
  echo "=== Downloading first slice of each source (Day 1 hand-read mode) ==="
  local sources=(slack gmail linear drive hubspot fireflies github confluence)
  for src in "${sources[@]}"; do
    local fname="${src}_slice_0001.zip"
    local url="$BASE_URL/$fname"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -L "$url")
    if [ "$http_code" = "200" ]; then
      mkdir -p "$DATA_DIR/$src"
      download "$url" "$DATA_DIR/$fname"
      extract_zip "$DATA_DIR/$fname" "$DATA_DIR/$src/"
    else
      echo "[skip] No slice_0001 found for $src (http $http_code)"
    fi
  done
}

# --- Argument parsing ---
MODE="${1:-}"

case "$MODE" in
  --all)
    download_questions
    download_all
    ;;
  --questions-only)
    download_questions
    ;;
  --source)
    SOURCE="${2:-}"
    if [ -z "$SOURCE" ]; then
      echo "Usage: $0 --source <name>"
      exit 1
    fi
    download_questions
    download_source_slices "$SOURCE"
    ;;
  "")
    # Default: questions + first slice per source (Day 1 mode)
    download_questions
    download_first_slices
    echo ""
    echo "=== Day 1 dataset ready. ==="
    echo "  Questions:        $QUESTIONS_DIR/"
    echo "  First slices:     $DATA_DIR/<source>/"
    echo ""
    echo "Next: hand-read ~20 docs per source, then run with --all for full dataset."
    ;;
  *)
    echo "Unknown option: $MODE"
    echo "Usage: $0 [--all | --questions-only | --source <name>]"
    exit 1
    ;;
esac
