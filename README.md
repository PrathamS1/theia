# Company Brain

**Hack Hydra 2026 — Track 01: Enterprise Context + Ontology**

> Turn Redwood Inference's 500K messy, contradictory, multi-source documents into a single trustworthy graph, and answer questions correctly — including knowing when to say "I don't know."

Built on [HydraDB](https://github.com/hydra-db/hydradb) · Scored against [EnterpriseRAG-Bench](https://github.com/onyx-dot-app/EnterpriseRAG-Bench) · 500 gold questions

---

## Architecture

```
Documents (9 sources: Slack, Gmail, Linear, Drive, HubSpot, Fireflies, GitHub, Confluence)
    │
    ▼
[1] Extraction      — Gemini extracts typed entities + facts per document (JSON mode)
    │
    ▼
[2] Entity Resolution — cluster mentions → canonical entities (SAME_AS edges via MSpaths)
    │
    ▼
[3] Graph Load       — canonical nodes + provenance-tagged edges into HydraDB via Bolt
    │
    ▼
[4] Conflict Layer   — detect contradictions → SUPERSEDES edges with trust/recency
    │
    ▼
[5] Query Engine     — NL question → multi-hop Cypher + abstention logic
    │
    ▼
[6] Eval Harness     — 500 gold questions scored by category
    │
    ▼
[7] Demo UI          — Streamlit: question → answer → graph path → sources
```

## Why HydraDB

- **`algo.MSpaths`**: batch-checks thousands of entity-resolution candidate pairs against shared graph context (same ticket, thread, meeting) in one call — impossible to replicate efficiently with naive one-by-one Cypher.
- **Multi-hop Cypher**: natively traverses provenance chains (Document → MENTIONS → Person → SAME_AS → Person → ASSIGNED_TO → Ticket) without materialising intermediate results.
- **Snapshot consistency**: `strong` consistency mode guarantees post-bulk-load queries see all committed writes before the eval run starts.

## Setup

```bash
# 1. Clone this repo
git clone <your-repo-url> company-brain
cd company-brain

# 2. Python environment (requires Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
# Edit .env and fill in GEMINI_API_KEY

# 4. Download the dataset (WSL/Linux)
bash scripts/download_dataset.sh           # Day 1: questions + first slice per source
bash scripts/download_dataset.sh --all     # Full dataset (~1.2 GB)

# 5. Start HydraDB (WSL/Linux, from the hydradb repo root)
cd ~/hydradb
bash /path/to/company-brain/scripts/start_hydradb.sh

# 6. Verify connection
python scripts/smoke_test.py
```

## Running the Pipeline

```bash
# Ingest all 9 sources into HydraDB
python scripts/run_ingest.py

# Run entity resolution + conflict tagging
python scripts/run_resolution.py

# Evaluate against 500 gold questions
python scripts/run_eval.py

# Launch the demo UI
streamlit run demo/app.py
```

## Eval Results

*Fill in after Day 5 eval run.*

| Category | Questions | Accuracy |
|---|---|---|
| Lookup (single-doc) | — | — |
| Multi-hop | — | — |
| Conflict resolution | — | — |
| Abstention | — | — |
| **Total** | **500** | **—** |

## Dependencies

- [HydraDB](https://github.com/hydra-db/hydradb) — graph engine (Bolt-compatible)
- [EnterpriseRAG-Bench](https://github.com/onyx-dot-app/EnterpriseRAG-Bench) — dataset and gold questions (Apache-2.0)
- [Google Gemini](https://ai.google.dev/) — LLM extraction and resolution adjudication
- Python: `neo4j`, `google-genai`, `pydantic`, `pandas`, `rapidfuzz`, `streamlit`, `pytest`

## License

MIT — see [LICENSE](./LICENSE)
