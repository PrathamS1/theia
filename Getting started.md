# Company Brain — Getting Started
### Hack Hydra 2026 · Track 01: Enterprise Context + Ontology

Build target: a conflict-aware, provenance-tracking enterprise ontology on
[EnterpriseRAG-Bench](https://github.com/onyx-dot-app/EnterpriseRAG-Bench),
built on [HydraDB](https://github.com/hydra-db/hydradb), scored against the
benchmark's 500 gold questions.

Deadline: **Aug 20, 2026, 11:59 PM PT.** Today is Aug 14 — you have ~6-7 build
days left. This doc assumes a fresh start from here.

---

## 1. The one-sentence pitch (keep this pinned above your desk)

> Turn Redwood Inference's 500K messy, contradictory, multi-source documents
> into a single trustworthy graph, and answer questions correctly — including
> knowing when to say "I don't know" — better than a long-context RAG baseline.

Everything you build should trace back to this sentence. If a feature doesn't
serve entity resolution, conflict resolution, multi-hop querying, or
abstention, it's scope creep — cut it.

---

## 2. What you're actually working with

- **Dataset**: EnterpriseRAG-Bench simulates a fictional company, *Redwood
  Inference* (an AI-inference-as-a-service startup), across 9 source types:
  Slack, Gmail, Linear/Jira, Google Drive, HubSpot, Fireflies (meeting
  transcripts), GitHub, Confluence. ~500,000 documents total, downloaded as
  release archives, not fetched from any live API.
- **Ground truth**: 500 gold-labeled questions in `questions.jsonl`
  (+100 metadata-aware ones in `extra_questions.jsonl`), spanning single-doc
  lookup → multi-doc/multi-hop reasoning → conflict resolution → correct
  abstention. This is your scoreboard. Everything else is presentation.
- **Deliberately planted problems in the data**: near-duplicate documents,
  misfiled documents, and facts that flatly contradict each other. Don't
  treat these as bugs in the dataset — they're the actual test.

Get the data first, before writing any pipeline code, so your schema design
is grounded in what's really there rather than assumptions.

```bash
git clone https://github.com/onyx-dot-app/EnterpriseRAG-Bench.git
cd EnterpriseRAG-Bench
# pull the release archives (per-source slices, ~5,000 docs each, or full set)
# see: https://github.com/onyx-dot-app/EnterpriseRAG-Bench/releases/latest
```

Skim ~20-30 real documents per source by hand before designing your schema.
You need to see the actual noise (name variants, contradicting statements,
timestamp formats) with your own eyes.

---

## 3. HydraDB — get it running today, before anything else

Clone and smoke-test the repo. Do this on Day 1, not when you need it.

```bash
git clone https://github.com/hydra-db/hydradb.git
cd hydradb
just native-check     # verifies cypher-parser + GraphBLAS are discoverable
just smoke             # local write/traversal/reopen/verify round trip
```

Prerequisites (Ubuntu/WSL):
```bash
sudo apt-get update
sudo apt-get install -y build-essential clang libclang-dev cmake pkg-config \
  libcypher-parser-dev libgraphblas-dev curl git python3 python3-venv
```
macOS:
```bash
xcode-select --install
brew install just cmake pkg-config llvm suite-sparse
brew install cleishm/neo4j/libcypher-parser
```

Run a local dev node (foreground process — leave it running in its own
terminal):

```bash
mkdir -p .hydradb/store .hydradb/cache
printf '%s\n' 'local-development-token-32-bytes' > .hydradb/auth-token

export CLOUD_PROVIDER=local
export LOCAL_PATH="$PWD/.hydradb/store"
export GRAPH_NAMESPACE=default
export GRAPH_ID=default
export GRAPH_CELL_ID=cell-0
export GRAPH_CELLS=cell-0
export GRAPH_NODE_ID=node-0
export GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687
export GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687
export GRAPH_DATA_CACHE_DIR="$PWD/.hydradb/cache"
export GRAPH_AUTH_TOKEN_FILE="$PWD/.hydradb/auth-token"
export GRAPH_ALLOW_PLAINTEXT=true
export RUST_MIN_STACK=33554432

cargo run --locked --features server-runtime --bin graph-node
```

Endpoints once it's up:
| Endpoint | Address | Purpose |
|---|---|---|
| Bolt | `127.0.0.1:7687` | Neo4j-driver-compatible queries |
| HTTP | `127.0.0.1:8443` | JSON/NDJSON query API |
| Admin | `127.0.0.1:9090` | readiness + Prometheus metrics |

For your ingestion pipeline, use the **Python Neo4j driver over Bolt**
(`pip install neo4j`) — it's the fastest path since HydraDB is Bolt-compatible
and you don't have to hand-roll HTTP request plumbing. Use `causal`
consistency for normal reads/writes during ingestion; reach for `strong` only
where a query needs to be certain it's seeing the very latest write (e.g.
right after a bulk load, before your eval run).

Keep this repo cloned **separately** from your submission repo — you're not
forking it into your project, you're building a project that depends on/uses
it. Your submission repo must be freshly created with no pre-Aug-12 commit
history.

---

## 4. Architecture overview

```
Documents (9 sources)
      │
      ▼
[1] Extraction        — LLM pulls typed entities + facts + raw mentions per doc
      │
      ▼
[2] Entity Resolution  — cluster mentions into canonical entities (SAME_AS)
      │
      ▼
[3] Graph Load         — write canonical nodes + provenance-tagged edges into HydraDB
      │
      ▼
[4] Conflict Layer     — detect contradicting facts, tag with trust/recency
      │
      ▼
[5] Query Engine       — multi-hop Cypher + MSpaths, abstention logic
      │
      ▼
[6] Eval Harness       — run questions.jsonl, score vs gold, break down by category
      │
      ▼
[7] Demo UI            — ask a question, see the answer + the graph path + sources
```

Steps 1-3 are your data pipeline (batch, run-once-then-iterate). Steps 4-6
are what you're actually being judged on. Step 7 is what makes the video good.
Do not let step 7 eat time that steps 4-6 need.

---

## 5. Graph schema (draft — refine after you've looked at real data)

**Node types**
| Label | Key properties |
|---|---|
| `Person` | canonical_name, emails[], handles[], resolved_from[] |
| `Org` | name, domain |
| `Project` | name, status |
| `Deal` | name, stage, amount |
| `Ticket` | id, title, status, source_system |
| `Document` | source, doc_id, url, created_at, raw_text_ref |

**Edge types** — every edge that represents a *fact* (not structure) carries
`source`, `timestamp`, `confidence`, `doc_id` (provenance back to the raw
document). This is the single most important schema decision you'll make —
don't skip provenance properties to save time.

| Edge | Meaning |
|---|---|
| `(Document)-[:MENTIONS]->(Entity)` | raw extraction link |
| `(Person)-[:SAME_AS {confidence, evidence}]->(Person)` | resolved identity |
| `(Person)-[:ASSIGNED_TO {source, timestamp}]->(Ticket\|Project)` | |
| `(Person)-[:DISCUSSED_IN {source, timestamp}]->(Document)` | |
| `(Fact)-[:SUPERSEDES {source, timestamp}]->(Fact)` | later fact overrides earlier one |
| `(Deal)-[:OWNED_BY {source, timestamp}]->(Person)` | |

Model contradicting facts as **two separate edges with different
source/timestamp**, not as one overwritten value. Resolution happens at
query time, not ingest time — that's what lets you answer "what did we
believe as of date X" and "what's true now" as two different queries against
the same data.

---

## 6. Day-by-day plan (today = Aug 14)

**Day 1 — Aug 14: Foundations**
- Clone HydraDB, get `graph-node` running locally, confirm a Cypher
  write/read round trip.
- Clone EnterpriseRAG-Bench, download the archives, hand-read ~20 docs per
  source.
- Lock the schema (section 5) based on what you actually saw.
- Create your **submission repo** (fresh, public, OSS license — MIT or
  Apache-2.0 — added on commit #1).
- Skim `questions.jsonl` — read all 500 questions once. This tells you
  exactly what your graph needs to be able to answer.

**Day 2 — Aug 15: Extraction + raw load**
- Write the LLM extraction pass: per document → typed entities + raw facts +
  mentions (JSON output, schema-constrained).
- Bulk-load raw `Document` nodes and `MENTIONS` edges into HydraDB via
  batched `UNWIND` Cypher writes over Bolt.
- Checkpoint: can you run a Cypher query and pull back real Redwood Inference
  people/projects from real documents? If not, don't move on.

**Day 3 — Aug 16: Entity resolution**
- Blocking: group candidate mentions by name similarity / shared email
  domain / shared channel.
- For each candidate cluster, check shared graph context — same ticket,
  same thread, same meeting — using `algo.MSpaths` to batch-check many
  candidate pairs against each other in one call instead of one-by-one.
- LLM adjudicates the ambiguous remainder.
- Write `SAME_AS` edges with `confidence` + `evidence` (which docs justified
  the merge). Never silently collapse nodes — keep the trail.
- Checkpoint: manually spot-check 20 resolved clusters for correctness.

**Day 4 — Aug 17: Conflict layer + query engine**
- Implement conflict detection: when two facts about the same
  subject+attribute disagree, link them with `SUPERSEDES` (by timestamp) and
  tag both with source.
- Build the query engine: given a natural-language question, resolve
  entities mentioned → run bounded multi-hop Cypher (`algo.SSpaths` /
  `algo.MSpaths`) → assemble the fact set, ordered by recency and source
  trust → generate an answer with citations.
- Implement abstention: if the traversal finds no path reaching the required
  entities within your hop bound, return "not in the data" instead of
  letting the LLM guess.

**Day 5 — Aug 18: Eval harness + iterate**
- Run all 500 questions through your pipeline. Score against gold answers.
- Break down accuracy by question category (lookup / multi-hop / conflict /
  abstention) — this breakdown is what goes in your README and demo.
- Spend the rest of the day on your worst-performing category, not on
  features. A 15% jump in conflict-resolution accuracy is worth more than
  any UI polish.

**Day 6 — Aug 19: Demo interface + polish**
- Build a minimal UI (or even a clean CLI/notebook) that shows: question →
  answer → the graph path traversed → source documents with timestamps.
  This visualization is your strongest 30 seconds of demo video.
- Write the README: problem, architecture, how HydraDB is used and why it
  matters (be explicit — judges are told to check this), setup
  instructions, eval results table, attributions/license.
- Final full eval run — freeze the number you'll quote in your video.

**Day 7 — Aug 20 (deadline day): Record, submit, buffer**
- Record the 3-minute demo video (script below). Keep it under 3:00 — judges
  may not review past that mark.
- Fill out the submission form (project description, problem, what you
  built, tech stack, HydraDB usage explanation, team contributions, repo
  link, video link).
- Triple-check: repo is public, license file present, README complete,
  video link is unlisted-but-viewable (not private), no dead links.
- Submit well before 11:59 PM PT — don't test the deadline.

---

## 7. Demo video script skeleton (≤3 min)

1. **0:00-0:20** — The problem: Redwood Inference's knowledge is scattered
   across 9 tools, with contradictions and stale facts nobody can safely
   trust. Show a real messy example from the data.
2. **0:20-0:50** — What you built: the ontology, the entity-resolution
   approach, the conflict layer. One clean architecture diagram.
3. **0:50-2:20** — Live demo: ask 3 questions live —
   - a multi-hop question (show the traversed path),
   - a conflicting-fact question (show both sources + which one it trusts
     and why),
   - a genuinely unanswerable question (show correct abstention).
4. **2:20-2:50** — The number: your accuracy on the 500 gold questions,
   broken down by category, vs. a stated baseline.
5. **2:50-3:00** — Why HydraDB specifically: name the concrete feature
   (`MSpaths` batch resolution, snapshot consistency, multi-hop Cypher) and
   what you'd lose without it.

---

## 8. Submission checklist (from the official rules — don't lose on a technicality)

- [ ] Repo is a **fresh** repo, first commit on or after Aug 12, 2026
- [ ] Repo is **public**
- [ ] Repo has an **open-source license** file (MIT/Apache-2.0 recommended)
- [ ] README has: setup/run instructions, explanation of how HydraDB is used,
      dependency/env info, attribution for EnterpriseRAG-Bench and any other
      third-party code/data/libraries
- [ ] Demo video ≤ 3:00, viewable without requesting access
- [ ] Submission form completed with all team members + individual
      contributions
- [ ] HydraDB does **real work** in the pipeline — the README should be able
      to answer "what would we lose without it" in one paragraph
- [ ] Submitted before **Aug 20, 11:59 PM PT**

---

## 9. Team split suggestion (adjust to your actual headcount/skills)

- **Person A — Data/Backend**: extraction pipeline, HydraDB schema + bulk
  load, entity resolution logic.
- **Person B — Graph/Query**: Cypher query design, `MSpaths`/`SSpaths`
  usage, conflict layer, abstention logic, eval harness.
- **Person C (if 3-4 people) — Product/Demo**: minimal UI, README, video,
  submission form, and running the manual spot-checks on entity resolution
  quality.
- Whoever isn't blocked helps burn down the Day 5 eval-accuracy backlog —
  that's the highest-leverage day of the whole project.

---

## 10. Things that will quietly sink you

- **Scope creep past the 9 sources.** No codebase ASTs, no social scraping,
  no invented data sources — you already decided this. Stay disciplined
  when it's tempting on Day 4.
- **Silent entity merging.** If `SAME_AS` has no evidence trail, you can't
  debug bad merges and you can't show provenance in the demo.
- **Skipping the eval harness until the end.** Run it early and often — Day
  5 shouldn't be the first time you see your real accuracy number.
- **Treating conflicts as bugs.** They're the test. If your pipeline "fixes"
  contradictions at ingest time, you've thrown away the hardest, most
  demo-worthy part of the problem.
- **A commit history that starts before Aug 12** on your submission repo —
  automatic disqualification risk. Start clean.

---

## 11. Tech stack — pick this now, don't debate it later

**Yes, Python, end to end, for everything except the demo front end.** Reasons
specific to this project, not just "Python is popular":

- Both `openai` and `anthropic` SDKs (whichever LLM you use for extraction)
  are best-supported in Python, and you need structured JSON extraction, not
  chat.
- HydraDB speaks Bolt, and the `neo4j` Python driver connects to it directly
  — no custom client needed.
- Entity-resolution blocking wants fuzzy string matching (`rapidfuzz`) and
  light data wrangling (`pandas`) — both mature in Python, painful elsewhere.
- Your eval harness is just "loop over `questions.jsonl`, call your pipeline,
  diff against gold, tally by category" — a 100-line Python script, not a
  service.

**Concrete stack:**

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | see above |
| Graph client | `neo4j` driver over Bolt | HydraDB is Bolt-compatible |
| LLM extraction | `anthropic` or `openai` SDK, structured/JSON-mode output | reliable typed extraction |
| Blocking/fuzzy match | `rapidfuzz` | fast candidate-pair generation for entity resolution |
| Data wrangling | `pandas` | loading source archives, joining eval results |
| Config/env | `python-dotenv` | keep API keys and HydraDB connection out of code |
| Testing | `pytest` | a few tests on extraction/resolution logic go a long way in judging "technical execution" |
| Demo UI | `streamlit` | fastest path to an interactive, good-on-video demo with almost no frontend code |
| Env/deps | `pyproject.toml` + `requirements.txt`, or `uv` if your team already uses it | reproducible setup for judges who clone and run |

Don't reach for a task queue, a real backend framework (FastAPI/Flask), a
database migration tool, or Docker unless something above is genuinely
insufficient — none of that is what's being judged, and every hour spent on
infrastructure ceremony is an hour not spent on entity resolution accuracy.

If someone on the team wants a more polished web front end instead of
Streamlit, that's fine on Day 6 only, once the pipeline works — use the
`frontend-design` conventions for that, and keep it a thin read-only layer
over the same query engine, not a rewrite.

---

## 12. Initializing the submission repo — exact steps

```bash
mkdir company-brain && cd company-brain
git init
git branch -M main

# license — pick one, MIT is simplest for a hackathon
curl -o LICENSE https://raw.githubusercontent.com/github/choosealicense.com/gh-pages/_licenses/mit.txt
# (edit the [year] and [fullname] placeholders inside LICENSE before committing)

python3 -m venv .venv
source .venv/bin/activate

pip install neo4j anthropic openai pandas rapidfuzz python-dotenv streamlit pytest
pip freeze > requirements.txt

git add -A
git commit -m "Initial commit: project scaffold"

# then create the empty repo on GitHub first, public, no template files, and:
git remote add origin git@github.com:<your-org-or-user>/company-brain.git
git push -u origin main
```

`.env.example` (commit this; never commit the real `.env`):
```
ANTHROPIC_API_KEY=
HYDRA_BOLT_URI=bolt://127.0.0.1:7687
HYDRA_USER=neo4j
HYDRA_PASSWORD=local-development-token-32-bytes
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.env
data/raw/
.hydradb/
*.ipynb_checkpoints/
```

---

## 13. Full file/folder layout

```
company-brain/
├── LICENSE
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── raw/                       # downloaded dataset archives — gitignored, large
│   └── questions/
│       ├── questions.jsonl        # gold eval set from EnterpriseRAG-Bench
│       └── extra_questions.jsonl
├── notebooks/
│   └── 01_explore_dataset.ipynb   # Day 1: hand-read real docs, sanity-check schema
├── src/
│   └── company_brain/
│       ├── __init__.py
│       ├── config.py              # env vars, HydraDB connection settings
│       ├── ingest/
│       │   ├── __init__.py
│       │   └── sources/           # one small loader per source, same output shape
│       │       ├── slack.py
│       │       ├── gmail.py
│       │       ├── linear.py
│       │       ├── drive.py
│       │       ├── hubspot.py
│       │       ├── fireflies.py
│       │       ├── github.py
│       │       └── confluence.py
│       ├── extraction/
│       │   ├── __init__.py
│       │   ├── prompts.py         # extraction prompt templates
│       │   └── extractor.py       # doc -> typed entities/facts (JSON mode)
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── client.py          # Bolt driver wrapper
│       │   ├── schema.py          # node/edge label + property constants
│       │   └── loader.py          # batched UNWIND writes into HydraDB
│       ├── resolution/
│       │   ├── __init__.py
│       │   ├── blocking.py        # candidate pair generation (rapidfuzz)
│       │   ├── resolve.py         # MSpaths context check + LLM adjudication -> SAME_AS
│       │   └── conflicts.py       # detect contradictions -> SUPERSEDES edges
│       ├── query/
│       │   ├── __init__.py
│       │   ├── engine.py          # NL question -> entities -> Cypher -> answer
│       │   ├── cypher_templates.py
│       │   └── abstain.py         # no-path-found -> "not in the data"
│       └── eval/
│           ├── __init__.py
│           ├── run_eval.py        # loops questions.jsonl through engine, scores
│           └── metrics.py         # accuracy by category, reporting
├── scripts/
│   ├── start_hydradb.sh           # wraps the local dev-node env vars + run command
│   ├── run_ingest.py              # entrypoint: loads all 9 sources into the graph
│   ├── run_resolution.py          # entrypoint: runs entity resolution + conflict tagging
│   └── run_eval.py                # entrypoint: python scripts/run_eval.py
├── demo/
│   └── app.py                     # Streamlit demo: ask a question, see graph path + sources
└── tests/
    ├── test_extraction.py
    ├── test_resolution.py
    └── test_query_engine.py
```

**How this maps to the day plan:**
- Day 1: `notebooks/01_explore_dataset.ipynb`, `scripts/start_hydradb.sh`,
  `src/company_brain/graph/schema.py` (schema constants only, no logic yet).
- Day 2: `ingest/sources/*.py`, `extraction/*.py`, `graph/client.py`,
  `graph/loader.py`, `scripts/run_ingest.py`.
- Day 3: `resolution/blocking.py`, `resolution/resolve.py`,
  `scripts/run_resolution.py`.
- Day 4: `resolution/conflicts.py`, `query/*.py`.
- Day 5: `eval/*.py`, `scripts/run_eval.py` — run it, don't just write it.
- Day 6: `demo/app.py`, `README.md`, `tests/*.py` (a handful, not full coverage).
- Day 7: nothing new — recording, submission form, buffer.

Don't build the `tests/` or `demo/` folders early out of thoroughness — they
have zero effect on your eval score and everything before Day 6 should be
going toward accuracy on `questions.jsonl`.
