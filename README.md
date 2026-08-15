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



_________________

# Company Brain — Build Progress

**Hack Hydra 2026 · Track 01: Enterprise Context + Ontology**  
**Deadline:** Aug 20, 2026 · 11:59 PM PT  
**Repo:** this one — public, created after Aug 12

---

## 🗺️ Phase Overview

| Phase | Description | Status |
|---|---|---|
| 0 | Scaffold, env, HydraDB setup, smoke test | ✅ Done & tested |
| 1 | Dataset download, LLM extraction pipeline, graph loader | ✅ Done & partially tested |
| 2 | Entity resolution (SAME\_AS edges) | 🟡 Scaffolded — not run-tested on real data yet |
| 3 | Conflict layer (SUPERSEDES edges) + Query engine + Abstention | 🟡 Scaffolded — not run-tested yet |
| 4 | Eval harness (scores against 500 gold questions) | 🟡 Scaffolded — not run-tested yet |
| 5 | Streamlit demo UI | 🟡 Scaffolded — not run-tested yet |
| 6 | Video recording + submission | ⬜ Not started |

---

## ✅ Phase 0 — Scaffold & Setup (DONE & TESTED)

Everything below was verified working on Aug 14, 2026.

### Environment

- [x] `.env.example` created with `GEMINI_API_KEY`, `HYDRA_BOLT_URI`, `HYDRA_USER`, `HYDRA_PASSWORD`
- [x] `.env` created (excluded from git)
- [x] `.gitignore` covering secrets, `data/raw/`, `.hydradb/`, `__pycache__`, Streamlit cache
- [x] `requirements.txt` — `neo4j==5.28.0`, `google-genai==1.20.0`, `pydantic==2.10.6`, `pandas`, `rapidfuzz`, `python-dotenv`, `streamlit`, `pytest`, `tqdm`

### HydraDB Build (WSL Ubuntu 22.04)

- [x] Rust updated from 1.80.0 → latest stable via `rustup update stable`
- [x] `libcypher-parser-dev` installed from apt
- [x] `libgraphblas-dev` (system package) found to be **too old** — `GxB_Global_Option_set_INT32` undefined symbol
- [x] Installed `libopenblas-dev` for BLAS dependency
- [x] Updated CMake from 3.22.1 → 4.4.2 via `pip install cmake`
- [x] Built SuiteSparse:GraphBLAS v10.5.0 from source (`~/SuiteSparse/GraphBLAS`)
- [x] `sudo ldconfig` run after install
- [x] `cargo build --locked --features server-runtime --bin graph-node` succeeded
- [x] HydraDB graph-node running on `bolt://127.0.0.1:7687`

### HydraDB Cypher Dialect — Discovered Constraints

These constraints were discovered through iterative smoke testing. All pipeline code must obey them:

| Constraint | Detail |
|---|---|
| `RETURN` | Must be `<binding>.<property>` or `count(*)` — bare `RETURN 1` not supported |
| `MATCH` | Node-only match requires label or property predicate — `MATCH (n)` alone is invalid |
| `id` property | Must be integer — string IDs cause parse errors |
| `CREATE` | Must use one-hop edge pattern `(a:Label)-[:REL]->(b:Label)` — standalone node CREATE not supported |
| `DELETE` | Must use `DETACH DELETE` when a node has incident edges |
| Transactions | Explicit transactions not supported — use auto-commit `session.run()` only |
| Agent string | Python neo4j driver's `check_supported_server_product` must be monkey-patched (see `client.py`) |

### Smoke Test — Verified

- [x] Bolt connection established (`SlateDBGraph/0.1.0` agent bypassed)
- [x] `MATCH (n:Document) RETURN count(*)` returns `{'count(*)': 0}`
- [x] `CREATE (a:_SmokeTest {id: 101})-[:TEST]->(b:_SmokeTest {id: 102})` writes successfully
- [x] `MATCH (a:_SmokeTest) RETURN a.id, a.name` reads nodes back correctly
- [x] `MATCH (a:_SmokeTest) DETACH DELETE a` cleans up successfully
- [x] Full round-trip: **All checks passed ✓**

Run smoke test: `python3 scripts/smoke_test.py`

### Scripts Created

- [x] `scripts/start_hydradb.sh` — sets all 14 required env vars and starts graph-node
- [x] `scripts/download_dataset.sh` — multi-mode dataset downloader (questions-only / first-slice / full)
- [x] `scripts/smoke_test.py` — Bolt connection + write/read/delete verification

---

## ✅ Phase 1 — Ingestion & LLM Extraction (DONE, partially tested)

### Dataset Downloaded

- [x] `data/questions/questions.jsonl` — 500 gold benchmark questions
- [x] `data/questions/extra_questions.jsonl` — extra evaluation set
- [x] `data/raw/slack_slice_0001.zip` (~9.7 MB)
- [x] `data/raw/gmail_slice_0001.zip` (~15 MB)
- [x] `data/raw/linear_slice_0001.zip` (~13.3 MB)
- [x] `data/raw/hubspot_slice_0001.zip` (~9.3 MB)
- [ ] `drive_slice_0001.zip` — 404 (not available in this release)
- [ ] `fireflies`, `github`, `confluence` — not downloaded yet

### Source Loaders

- [x] `src/company_brain/ingest/sources/loader_base.py` — iterates `.zip` (reads contents directly), `.json`, `.jsonl`, `.txt`, `.md` files. Handles nested paths inside zip archives.

### Extraction Pipeline

- [x] `src/company_brain/extraction/prompts.py` — Pydantic models: `ExtractedEntity`, `ExtractedFact`, `DocumentExtractionResult` for Gemini structured JSON output
- [x] `src/company_brain/extraction/extractor.py` — Calls Gemini 2.5 Flash with `response_mime_type="application/json"` and `response_schema=DocumentExtractionResult`
- [x] `src/company_brain/graph/schema.py` — Node labels, edge types, property name constants, source trust rankings
- [x] `src/company_brain/graph/client.py` — Neo4j Bolt driver wrapper (patched for HydraDB, auto-commit `session.run()`, batched write helper)
- [x] `src/company_brain/graph/loader.py` — `GraphLoader` using `zlib.crc32` for integer node IDs, one-hop CREATE patterns, `_sanitize()` for inline Cypher strings
- [x] `src/company_brain/config.py` — Central config with `load_dotenv(override=True)`, `get_gemini_api_key()` dynamic fetch

### Tested (Aug 14 run)

- [x] `python3 scripts/run_ingest.py --limit 10` ran successfully
- [x] First document (`doc_id=dsid_3048e4f240c34...`, Slack) processed
- [x] **10 entities** and **32 facts** extracted by Gemini 2.5 Flash from first document
- [x] Gemini API confirmed working with AFC (Automatic Function Calling) enabled
- [ ] Graph writes verified back in HydraDB (not yet queried back — next step)
- [ ] Remaining sources (fireflies, github, confluence) not yet downloaded and run

---

## 🟡 Phase 2 — Entity Resolution (SCAFFOLDED, not run-tested)

Code is written and wired up. Has **not been run on real extracted data yet**.

- [x] `src/company_brain/resolution/blocking.py` — Candidate pair generation: fetches `Person` nodes from HydraDB, runs `rapidfuzz.fuzz.token_sort_ratio` with configurable threshold (default 85)
- [x] `src/company_brain/resolution/resolve.py` — Auto-resolves high-confidence pairs (≥95%), calls Gemini for adjudication on ambiguous pairs (85–95%), writes `(a)-[:SAME_AS {confidence, evidence}]->(b)` edges
- [x] `scripts/run_resolution.py` — Runner script

**Next step:** Run `python3 scripts/run_ingest.py` on full dataset first, then `python3 scripts/run_resolution.py`

---

## 🟡 Phase 3 — Conflict Layer + Query Engine (SCAFFOLDED, not run-tested)

Code is written. Has **not been run on real data yet**.

### Conflict Layer

- [x] `src/company_brain/resolution/conflicts.py` — Groups `Fact` nodes by `(subject, attribute)`, detects value conflicts, writes `(winner)-[:SUPERSEDES {reason}]->(loser)` edges ranked by `trust_score`

### Query Engine

- [x] `src/company_brain/query/cypher_templates.py` — `build_fact_query(keywords)` and `build_entity_query(name)` using HydraDB-compliant Cypher (label predicates, `<binding>.<property>` RETURN)
- [x] `src/company_brain/query/abstain.py` — Returns `(True, reason)` when retrieved fact set is empty or has no valid subject/value — prevents hallucination
- [x] `src/company_brain/query/engine.py` — Full pipeline: NL question → keyword extraction → Cypher fact retrieval → abstention check → Gemini synthesis with doc citations

**Next step:** After ingest + resolution, test `answer_question("What are the default size limits for file uploads?", client)` manually.

---

## 🟡 Phase 4 — Eval Harness (SCAFFOLDED, not run-tested)

- [x] `src/company_brain/eval/metrics.py` — `compute_metrics(results)` returning accuracy by `question_type` category
- [x] `scripts/run_eval.py` — Loads `questions.jsonl`, runs each question through query engine, checks gold `answer_facts` for keyword overlap, logs category breakdown

**Next step:** Run `python3 scripts/run_eval.py --limit 20` after ingestion and resolution complete.

---

## 🟡 Phase 5 — Demo UI (SCAFFOLDED, not run-tested)

- [x] `demo/app.py` — Streamlit UI: HydraDB status sidebar, sample question buttons, NL query input, answer + citations display, abstention warnings

**Next step:** Run `streamlit run demo/app.py` once query engine has data to answer from.

---

## 📁 Files in the Repo

```
company-brain/
├── .env.example                                # ← copy to .env and fill in GEMINI_API_KEY
├── .gitignore
├── README.md
├── PROGRESS.md                                 # ← this file
├── requirements.txt
├── Getting started.md                          # ← original hackathon brief
├── data/
│   ├── questions/
│   │   ├── questions.jsonl                     # 500 gold questions
│   │   └── extra_questions.jsonl
│   └── raw/                                    # ← gitignored; download via script
│       ├── slack_slice_0001.zip
│       ├── gmail_slice_0001.zip
│       ├── linear_slice_0001.zip
│       └── hubspot_slice_0001.zip
├── scripts/
│   ├── start_hydradb.sh                        # ← run from ~/hydradb in WSL
│   ├── download_dataset.sh                     # ← bash scripts/download_dataset.sh
│   ├── smoke_test.py                           # ← python3 scripts/smoke_test.py
│   ├── run_ingest.py                           # ← python3 scripts/run_ingest.py --limit N
│   ├── run_resolution.py                       # ← python3 scripts/run_resolution.py
│   └── run_eval.py                             # ← python3 scripts/run_eval.py --limit N
├── demo/
│   └── app.py                                  # ← streamlit run demo/app.py
└── src/company_brain/
    ├── config.py
    ├── graph/
    │   ├── schema.py
    │   ├── client.py
    │   └── loader.py
    ├── extraction/
    │   ├── prompts.py
    │   └── extractor.py
    ├── ingest/sources/
    │   └── loader_base.py
    ├── resolution/
    │   ├── blocking.py
    │   ├── resolve.py
    │   └── conflicts.py
    ├── query/
    │   ├── cypher_templates.py
    │   ├── abstain.py
    │   └── engine.py
    └── eval/
        └── metrics.py
```

---

## 🔧 Setup Instructions for New Contributors

### Prerequisites
- WSL/Ubuntu 22.04
- Python 3.11+
- Rust (latest stable via `rustup`)

### HydraDB Build
```bash
git clone https://github.com/hydra-db/hydradb.git ~/hydradb
cd ~/hydradb

# Install dependencies (Ubuntu 22.04)
sudo apt-get update
sudo apt-get install -y build-essential clang libclang-dev cmake pkg-config \
  libcypher-parser-dev libopenblas-dev curl git unzip python3 python3-venv

# GraphBLAS must be built from source (apt version is too old)
pip install --upgrade cmake
export PATH="$HOME/.local/bin:$PATH"
cd ~
git clone --depth 1 https://github.com/DrTimothyAldenDavis/SuiteSparse.git
cd SuiteSparse/GraphBLAS
mkdir build && cd build
cmake ..
cd ~/SuiteSparse/GraphBLAS && make -j$(nproc)
sudo make install && sudo ldconfig

# Build HydraDB
cd ~/hydradb
cargo build --locked --features server-runtime --bin graph-node
```

### Project Setup
```bash
cd /mnt/d/hydradb/hydra-brain   # or your WSL path to the repo

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Environment config
cp .env.example .env
# Edit .env → set GEMINI_API_KEY=your-key
```

### Running the Pipeline
```bash
# Terminal 1: Start HydraDB (leave running)
cd ~/hydradb
bash /mnt/d/hydradb/hydra-brain/scripts/start_hydradb.sh

# Terminal 2: Pipeline
cd /mnt/d/hydradb/hydra-brain

# Verify connection
python3 scripts/smoke_test.py

# Download data
bash scripts/download_dataset.sh

# Ingest (start small)
python3 scripts/run_ingest.py --limit 20

# Entity resolution + conflict tagging
python3 scripts/run_resolution.py

# Evaluate
python3 scripts/run_eval.py --limit 20

# Demo UI
streamlit run demo/app.py
```

---

## ⚠️ Known Issues & Things Left to Do

- [ ] **Verify graph writes**: Query HydraDB after `run_ingest.py` to confirm Document/Entity/Fact nodes were actually persisted (not just written without error)
- [ ] **Download remaining sources**: `fireflies`, `github`, `confluence` slices not yet downloaded
- [ ] **Run full ingestion**: Only `--limit 10` has been tested; full dataset not yet ingested
- [ ] **Run resolution + conflict layer on real data**: Phases 2 & 3 code is scaffolded but not yet exercised
- [ ] **Evaluate against benchmark**: `run_eval.py` not yet run — accuracy scores unknown
- [ ] **Query engine tuning**: Cypher keyword matching is naive (split on words); needs improvement for complex multi-hop questions
- [ ] **Eval scoring method**: Current keyword overlap check is a rough proxy — need to improve or add F1/exact-match scoring against `answer_facts`
- [ ] **Demo UI**: Not yet run; needs real data in HydraDB to be meaningful
- [ ] **`MATCH ... MERGE` not tested**: The loader uses `CREATE` for every write — no deduplication yet; re-running ingest will create duplicate nodes

---

*Last updated: Aug 14, 2026 — Phases 0 & 1 tested. Phases 2–5 scaffolded, not yet run on real data.*
