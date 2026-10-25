# CampusAsk

**CampusAsk** is a retrieval-augmented Q&A assistant for University of Central Missouri (UCM) academic and administrative policy. It searches official catalogs, handbook, and Registrar pages, then answers only from retrieved evidence—with citations—or abstains when the corpus does not support an answer.

Authors: **Sajitha Konda**, **Siri Chandana**, **ByReddy Nishitha Reddy**

## Principles

| Principle | Rule |
|-----------|------|
| **Grounding** | Substantive claims come only from retrieved official text |
| **Citation** | Every claim cites a document and PDF page (or HTML section/URL) |
| **Abstention** | Weak or missing evidence → decline; no invented policy |

This is a **retrieval** system. Documents are a searchable knowledge base, not fine-tuning data.

## Architecture

```
Allowlisted UCM PDF/HTML
        → extract + provenance
        → chunk (~500 tokens, 50 overlap)
        → Sentence Transformers embeddings
        → FAISS index + metadata map
        → retrieve top-k (optional UG/Grad filter)
        → evidence gate
        → grounded hosted LLM + citation check
        → Streamlit answer or safe abstention
```

| Layer | Module |
|-------|--------|
| Config | `src/config.py` |
| Ingest / extract | `src/ingestion.py`, `src/extraction.py` |
| Chunk / embed / index | `src/chunking.py`, `src/embeddings.py`, `src/vector_store.py` |
| Retrieve / answer | `src/retrieval.py`, `src/generation.py`, `src/citations.py` |
| Eval | `src/evaluation.py`, `scripts/run_evaluation.py` |
| UI | `app.py` |

**Model defaults**

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (fast, strong baseline; swap via `EMBEDDING_MODEL`)
- LLM: OpenAI-compatible Chat Completions API via Groq free tier by default (`LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=llama-3.1-8b-instant`); any compatible base URL/model works

## Repository layout

```
AI_Project/
├── app.py
├── src/
├── scripts/build_index.py
├── scripts/run_evaluation.py
├── data/raw/          # sources.json allowlist + local HTML/PDF
├── data/processed/
├── data/benchmark/    # 30-Q template + fixture smoke set
├── indexes/           # FAISS + chunk metadata (built locally)
├── tests/
├── results/
├── .env.example
└── requirements.txt
```

## Setup

Requires **Python 3.11+**.

```bash
git clone https://github.com/sajicodes/AI_Project.git
cd AI_Project
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set (Groq free-tier defaults match `.env.example`):

```bash
LLM_API_KEY=gsk_...
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
```

Retrieval and indexing work without an API key. **Answer generation** requires `LLM_API_KEY`.

### Sources

1. Review `data/raw/sources.json` (allowlist only—no full-site crawl).
2. Official **2026–2027** catalog PDFs are **Included in repo** (no manual download required for a fresh clone):

   - `data/raw/catalogs/ucm_ug_catalog_2026_2027.pdf`
   - `data/raw/catalogs/ucm_grad_catalog_2026_2027.pdf`

   To refresh from the publisher (or recover missing files), run:

```bash
python scripts/download_catalogs.py
```

3. HTML sources use `local_path` when present; otherwise they are fetched and cached under `data/raw/html_cache/`.
4. Development fixtures under `data/raw/fixtures/` are **synthetic** (`[DEV FIXTURE]`). They exist for pipeline smoke tests and are **not** official UCM policy. Disable them for production demos once real catalogs/handbook PDFs are indexed.

Discovery starting points (verify live editions before ingest):

- https://catalog.ucmo.edu/
- https://www.ucmo.edu/current-students/office-of-the-registrar-and-student-records/catalogs/
- https://www.ucmo.edu/current-students/office-of-the-registrar-and-student-records/

Official 2026–2027 PDF editions (also listed in `sources.json`):

- Undergraduate: https://catalog.ucmo.edu/mime/media/view/30/1574/2026-2027+Undergraduate+Catalog+071226.pdf
- Graduate: https://catalog.ucmo.edu/mime/media/view/29/1575/2026-2027+Graduate+Catalog+071226.pdf

## Build the index

```bash
python scripts/download_catalogs.py   # optional refresh; catalogs are already in-repo
python scripts/build_index.py
```

Writes:

- `indexes/campusask.faiss`
- `indexes/chunks.jsonl`
- `data/processed/pages.jsonl` and `ingest_log.json`

Rebuild whenever official documents change.

## Run the app

```bash
streamlit run app.py
```

Use the sidebar to filter **Undergraduate / Graduate / All**, ask questions, inspect **Sources**, and reset the chat. Unsupported questions should produce a clear abstention message—not a guess.

## Tests

```bash
pytest
```

Core coverage: HTML/PDF provenance, chunk metadata, FAISS round-trip, citation rejection, evidence-gate abstention, local fixture ingest.

## Evaluation

Proposal targets (goals—not claimed results until dual human review):

| Metric | Target |
|--------|--------|
| Answer accuracy | ≥ 80% |
| Retrieval hit rate | ≥ 90% |
| Hallucination rate | ≤ 10% |
| Appropriate abstention | ≥ 80% |

Benchmark files:

- `data/benchmark/questions.json` — 30-Q **template** (`verified: false` until the team fills gold answers)
- `data/benchmark/questions.fixture_smoke.json` — small fixture-only smoke set

```bash
# Structure + baselines scaffolding (accuracy/hallucination stay null until human scoring)
python scripts/run_evaluation.py

# Fixture smoke (not for proposal metric claims)
python scripts/run_evaluation.py --benchmark data/benchmark/questions.fixture_smoke.json
```

Baselines included in the harness:

1. Keyword search over the same chunks  
2. Ungrounded chatbot marker (not executed with fabricated answers)

Chunk-size (300/500/800) and `k` (3/5/10) sweeps: rebuild the index with `CHUNK_SIZE=...` for each chunk setting, then re-run with `TOP_K=...`. Do not invent scored tables.

## Limitations

- PDF multi-column layouts may extract poorly; inspect `ingest_log.json`.
- Image-only scanned pages are flagged, not silently treated as text.
- Live UCM HTML can change; prefer versioned local PDFs for demos.
- Without `LLM_API_KEY`, the UI retrieves evidence but cannot draft grounded answers.
- Mixing catalog years or UG/Grad rules is avoided via metadata filters—keep source metadata accurate.

## License / use

Built for an academic AI project demonstration. Official UCM documents remain the property of the University of Central Missouri; use publicly posted materials according to institutional terms.
