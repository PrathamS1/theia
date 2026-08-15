# 🧠 Company Brain — Architecture, Logic, and Code Flow

**Project:** `hydra-brain` (Hack Hydra 2026 — Track 01: Enterprise Context + Ontology)  
**Engine:** [HydraDB](https://github.com/hydra-db/hydradb) (Bolt-compatible graph database)  
**Dataset:** [EnterpriseRAG-Bench](https://github.com/onyx-dot-app/EnterpriseRAG-Bench) (500,000+ enterprise documents across 9 sources)

---

## 1. High-Level Concept

**Company Brain** solves the challenge of extracting, structuring, deduplicating, and querying massive, messy, and contradictory enterprise documentation. It processes 9 internal data sources (*Slack, Gmail, Linear, Drive, HubSpot, Fireflies, GitHub, Confluence*) into a single unified knowledge graph stored inside **HydraDB**.

Key capabilities:
1. **Provenance Tracking**: Every extracted fact links back to its source document (`doc_id`, `source`, `created_at`).
2. **Entity Resolution**: Merges duplicate mentions (e.g. "John Doe", "john@company.com", "@johndoe" on Slack) using fuzzy matching, exact identifier matching, and LLM adjudication (`SAME_AS` edges).
3. **Conflict Resolution**: Resolves contradictory statements (e.g. outdated Slack message vs. updated Linear ticket) using a source trust hierarchy (`SUPERSEDES` edges).
4. **Hallucination Prevention (Abstention)**: Explicitly abstains ("I don't know") when the requested fact is missing from the graph.

---

## 2. System Architecture & Component Mapping

```
                               RAW DATA SOURCES
     (Slack, Gmail, Linear, Drive, HubSpot, Fireflies, GitHub, Confluence)
                                      │
                                      ▼
                        [1. INGESTION & EXTRACTION]
       `loader_base.py` ──► `extractor.py` (Gemini 2.5 Flash + Pydantic)
                                      │
                                      ▼
                           [2. GRAPH STORAGE]
             `loader.py` ──► HydraDB (Bolt driver via `client.py`)
                  ├─ (Document)-[:MENTIONS]->(Entity)
                  └─ (Document)-[:HAS_FACT]->(Fact)
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
      [3. ENTITY RESOLUTION]                      [4. CONFLICT LAYER]
   `blocking.py` + `resolve.py`                    `conflicts.py`
  (fuzzy match + Gemini adjudication)          (source trust ranking)
                 │                                         │
                 ▼                                         ▼
   Creates (Person)-[:SAME_AS]->(Person)    Creates (Fact)-[:SUPERSEDES]->(Fact)
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                         [5. QUERY ENGINE & ABSTENTION]
                       `cypher_templates.py` + `engine.py`
                                      │
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
                 Has Graph Facts?            No Relevant Facts?
                        │                           │
                        ▼                           ▼
            [6. Gemini Answer Synthesis]     [Abstention Engine]
            (Includes doc_id citations)      ("I don't know...")
                        │                           │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                          [7. INTERFACE / EVAL]
                    Streamlit (`demo/app.py`) & `run_eval.py`
```

---

## 3. Detailed Step-by-Step Code Flow

### Phase 1: Ingestion & Extraction (`src/company_brain/ingest/` & `extraction/`)

* **Entry Point**: `python scripts/run_ingest.py`
* **File Processing** (`ingest/sources/loader_base.py`):
  * Recursively scans `data/raw/` for JSON, JSONL, TXT, MD, and ZIP files.
  * Normalizes each document into a standardized dictionary:
    ```python
    {"doc_id": "...", "source": "slack|gmail|linear|...", "created_at": "...", "text": "..."}
    ```
* **LLM Extraction** (`extraction/extractor.py` & `prompts.py`):
  * Passes document content to **Gemini 2.5 Flash** using Pydantic schema validation (`response_mime_type="application/json"`).
  * Returns structured `DocumentExtractionResult`:
    * **Entities**: Named entities (`Person`, `Org`, `Project`, `Ticket`, `Deal`) with emails or handles.
    * **Facts**: Key-value assertions `(subject, attribute, value)` e.g. `subject="multipart upload"`, `attribute="max_file_size"`, `value="10 MiB"`.
* **Graph Bulk Loading** (`graph/loader.py`):
  * Converts string identifiers to positive 32-bit integer IDs (`zlib.crc32`) as required by HydraDB.
  * Writes nodes and relationships into HydraDB using one-hop Cypher patterns:
    * `(Document)-[:MENTIONS]->(Entity)`
    * `(Document)-[:HAS_FACT]->(Fact)`
  * Assigns source trust scores (`trust_score`) to each fact.

---

### Phase 2: Entity Resolution (`src/company_brain/resolution/`)

* **Entry Point**: `python scripts/run_resolution.py` (Step 1)
* **Candidate Blocking** (`resolution/blocking.py`):
  * Queries all `Person` and `Org` nodes from HydraDB.
  * Compares pairs using `rapidfuzz` (`token_sort_ratio`) for names and exact matching for emails/handles.
  * Filters candidate pairs with similarity score $\ge 85\%$.
* **Adjudication & Edge Creation** (`resolution/resolve.py`):
  * High confidence ($\ge 95\%$ or exact email match) $\rightarrow$ Auto-resolved.
  * Ambiguous candidates ($85\% - 94\%$) $\rightarrow$ Sent to Gemini LLM for adjudication (`AdjudicationResult`).
  * Writes `(PersonA)-[:SAME_AS {confidence, evidence}]->(PersonB)` edges in HydraDB.

---

### Phase 3: Conflict Detection & Tagging (`src/company_brain/resolution/conflicts.py`)

* **Entry Point**: `python scripts/run_resolution.py` (Step 2)
* **Conflict Identification**:
  * Fetches all `Fact` nodes and groups them by `(subject, attribute)` tuple.
* **Source Trust Ranking**:
  * When multiple facts conflict on the same `(subject, attribute)`, facts are sorted by `trust_score` based on source authority:
    $$\text{Linear (0.95)} > \text{GitHub (0.92)} > \text{Confluence (0.90)} > \text{HubSpot (0.88)} > \text{Fireflies (0.75)} > \text{Slack (0.65)} > \text{Gmail (0.60)}$$
  * Creates `(WinnerFact)-[:SUPERSEDES {reason}]->(LoserFact)` edges in HydraDB.

---

### Phase 4: Query Engine & Abstention (`src/company_brain/query/`)

* **Query Flow** (`query/engine.py`):
  1. **Keyword Extraction**: Extracts key search terms from the natural language question.
  2. **Graph Traversal** (`query/cypher_templates.py`): Executes Cypher query against HydraDB to fetch relevant `Fact` nodes.
  3. **Abstention Verification** (`query/abstain.py`):
     * If no facts or verifiable matches exist $\rightarrow$ Triggers abstention: `"I don't know based on the provided company data. Information requested is not found..."`
  4. **Answer Synthesis**:
     * If facts exist $\rightarrow$ Passes facts summary to Gemini to synthesize a concise answer with strict `doc_id` citations.

---

### Phase 5: Evaluation & Demo UI (`src/company_brain/eval/` & `demo/`)

* **Eval Harness** (`scripts/run_eval.py` & `eval/metrics.py`):
  * Runs 500 gold questions from `data/questions/questions.jsonl`.
  * Scores generated answers against ground-truth facts across category breakdowns (*Lookup, Multi-hop, Conflict Resolution, Abstention*).
* **Interactive Demo** (`demo/app.py`):
  * Streamlit interface to input questions, inspect live graph responses, view document citations, and test abstentions.

---

## 4. Module Map

| Path | Primary Function |
|---|---|
| [`src/company_brain/config.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/config.py) | Centralized environment variables, paths, and model settings |
| [`src/company_brain/graph/schema.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/graph/schema.py) | Node labels, edge types, property names, and source trust rankings |
| [`src/company_brain/graph/client.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/graph/client.py) | Neo4j Bolt driver wrapper tailored for HydraDB compatibility |
| [`src/company_brain/graph/loader.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/graph/loader.py) | Integer node ID generator (`zlib`) & bulk Cypher loader |
| [`src/company_brain/ingest/sources/loader_base.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/ingest/sources/loader_base.py) | Multiformat reader for raw JSON, JSONL, TXT, MD, and ZIP files |
| [`src/company_brain/extraction/extractor.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/extraction/extractor.py) | LLM entity & fact extraction using Gemini 2.5 Flash JSON mode |
| [`src/company_brain/resolution/blocking.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/resolution/blocking.py) | Rapidfuzz candidate pair blocking for entity resolution |
| [`src/company_brain/resolution/resolve.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/resolution/resolve.py) | LLM adjudication & `SAME_AS` graph edge writer |
| [`src/company_brain/resolution/conflicts.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/resolution/conflicts.py) | Trust-based conflict resolution & `SUPERSEDES` edge writer |
| [`src/company_brain/query/engine.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/query/engine.py) | Natural language graph query pipeline & answer synthesizer |
| [`src/company_brain/query/abstain.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/query/abstain.py) | Abstention engine to prevent hallucinated answers |
| [`src/company_brain/eval/metrics.py`](file:///c:/Users/pratham/Documents/Projects/hydra-brain/src/company_brain/eval/metrics.py) | Category accuracy calculations for benchmark scoring |
