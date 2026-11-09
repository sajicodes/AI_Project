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
        → chunk (~500 tokens, 80 overlap)
        → Sentence Transformers embeddings
        → FAISS index + metadata map
        → query expand + retrieve top-k (optional UG/Grad filter)
        → evidence gate
        → grounded hosted LLM + citation check
        → Next.js UI (or safe abstention)
```

| Layer | Module |
|-------|--------|
| Config | `src/config.py` |
| Ingest / extract | `src/ingestion.py`, `src/extraction.py` |
| Chunk / embed / index | `src/chunking.py`, `src/embeddings.py`, `src/vector_store.py` |
| Retrieve / answer | `src/retrieval.py`, `src/generation.py`, `src/citations.py` |
| Conversation / identity | `src/conversation.py`, `src/identity.py` |
| Check-in login logs | `src/firestore_logs.py` (optional Firebase / Firestore) |
| HTTP API | `api/main.py` (FastAPI) |
| Product UI | `web/` (Next.js App Router) |
| Eval | `src/evaluation.py`, `scripts/run_evaluation.py` |

**Product shape:** Next.js frontend (Vercel) + Python FastAPI RAG service (Railway preferred; Render/Fly also work). The Streamlit app (`app.py`, `pages/ask.py`) remains as a local legacy prototype and is **not** the deploy target.

**Model defaults**

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (fast, strong baseline; swap via `EMBEDDING_MODEL`)
- LLM: OpenAI-compatible Chat Completions API via Groq free tier by default (`LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=openai/gpt-oss-20b`); any compatible base URL/model works

## Repository layout

```
AI_Project/
├── web/                   # Next.js product UI (landing + Ask)
├── api/                   # FastAPI wrapper around the RAG stack
├── src/                   # RAG pipeline + helpers
├── scripts/build_index.py
├── scripts/run_evaluation.py
├── data/raw/              # sources.json allowlist + local HTML/PDF
├── indexes/               # FAISS + chunk metadata (committed)
├── assets/ucm/            # Crest, campus, Mo the Mule
├── app.py / pages/        # Legacy Streamlit prototype (optional)
├── railway.toml           # API deploy on Railway
├── render.yaml            # Alternate API deploy on Render
├── tests/
├── .env.example
└── requirements.txt
```

## Setup

Requires **Python 3.9+** (3.11+ recommended) and **Node.js 20+** for the UI.

```bash
git clone https://github.com/sajicodes/AI_Project.git
cd AI_Project
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

cd web && npm install && cp .env.example .env.local && cd ..
```

Edit root `.env` and set (Groq free-tier defaults match `.env.example`):

```bash
LLM_API_KEY=gsk_...
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
CORS_ORIGINS=http://localhost:3000
```

Edit `web/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
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

## Run locally (product path)

Terminal 1 — API:

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — Next.js UI:

```bash
npm run dev
# → http://localhost:3000
```

The UI opens on a **University of Central Missouri** branded landing page. Choose **Ask CampusAsk** for grounded Q&A.

**Student check-in (required):** before the first policy chat, enter **full name** and **UCM ID** (9 digits starting with `700`, e.g. `700782694`). The browser keeps a masked ID in `sessionStorage`; UCM ID is never sent to the LLM. When Firebase is configured on the API host, each successful check-in is written to a Firestore `login_logs` collection (name, UCM ID, timestamp, optional academic level / user agent). CampusAsk greets you by first name; the sidebar shows your name and a masked ID, with **Switch student** to reset.

### Firebase login logs (optional)

Firestore stores **check-in / login logs** only (not the FAISS vector index). You must create a Firebase project before this works.

1. In [Firebase Console](https://console.firebase.google.com/), create a project and enable **Cloud Firestore**.
2. Project settings → **Service accounts** → generate a new private key (JSON). Keep the file local — never commit it.
3. Add to root `.env` (see `.env.example`):

```bash
FIREBASE_ENABLED=true
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/serviceAccount.json
# Hosted API alternative (Railway/Render secret):
# FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
CAMPUSASK_ADMIN_TOKEN=change-me-for-local-demo
```

4. Seed ~10 dummy students (and optional sample logs):

```bash
python scripts/seed_firestore.py --with-login-logs
```

5. Successful check-ins from the Next.js Ask UI call `POST /v1/identity/validate`, which appends a `login_logs` document when Firebase is configured.
6. Demo-only recent logs: `GET /v1/admin/login-logs` with header `X-Admin-Token: <CAMPUSASK_ADMIN_TOKEN>` (disabled with 503 until the token env is set).

In Ask mode, use sample question chips, filter **Undergraduate / Graduate / All**, start a **New conversation**, or return **Back to home**. Ask questions, inspect **Sources & evidence** beside answers, and expect a clear abstention when the corpus does not support an answer. Polite greetings / thanks never abstain.

Retrieval defaults: `TOP_K=8`, `EVIDENCE_MIN_SCORE=0.38`, with query expansion for thesis/GPA/probation/credit-hour phrasing.

### Legacy Streamlit (optional)

```bash
streamlit run app.py
```

## Deploy

### 1. API on Railway (preferred)

1. Create a Railway project from this GitHub repo.
2. Railway reads `railway.toml` + `api/Dockerfile`.
3. Set secrets / env vars:

| Variable | Required | Notes |
|----------|----------|-------|
| `LLM_API_KEY` | Yes | Groq (or compatible) key |
| `LLM_BASE_URL` | No | Default `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | No | Default `openai/gpt-oss-20b` |
| `CORS_ORIGINS` | Yes in prod | Your Vercel origin, e.g. `https://campusask.vercel.app` |
| `TOP_K` / `EVIDENCE_MIN_SCORE` | No | Retrieval tuning |
| `FIREBASE_PROJECT_ID` | For login logs | Firebase project id |
| `FIREBASE_CREDENTIALS_JSON` or `FIREBASE_CREDENTIALS_PATH` | For login logs | Service account (never commit the JSON file) |
| `CAMPUSASK_ADMIN_TOKEN` | Optional | Protects `GET /v1/admin/login-logs` |

4. Health check: `GET /health`
5. Copy the public API URL (e.g. `https://campusask-api.up.railway.app`)

**Alternates:** `render.yaml` for Render, or any Docker host (Fly.io) using `api/Dockerfile`.

### 2. Web on Vercel

Team: [https://vercel.com/sajithakonda0909-7027](https://vercel.com/sajithakonda0909-7027)

1. **Import** `AI_Project` in that Vercel team; set **Root Directory** to `web`.
2. Framework preset: Next.js (see `web/vercel.json`).
3. Environment variable:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | API base URL (no trailing slash). For local demos the API can stay on your machine (`http://127.0.0.1:8000`); for a public UI point this at your hosted FastAPI URL. |

4. Deploy. Open the landing page → **Ask CampusAsk**.

### Single-host course demo

If you prefer one platform for the demo day, run the API on Railway and the Next app on Vercel (recommended), **or** host both on Railway (static/Next service + API service) with the same `NEXT_PUBLIC_API_URL` wiring.

## Tests

```bash
pytest
```

Core coverage: HTML/PDF provenance, chunk metadata, FAISS round-trip, citation rejection, evidence-gate abstention, identity validation, query expansion, retrieval smoke for thesis/GPA/credit-hour vs off-topic, conversational greetings, FastAPI health/identity/greeting smoke, Firestore check-in log hooks (mocked), local fixture ingest.

```bash
cd web && npm run build
```

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
- Without `LLM_API_KEY`, the API retrieves evidence but cannot draft grounded answers.
- Mixing catalog years or UG/Grad rules is avoided via metadata filters—keep source metadata accurate.
- FAISS + embeddings are intentionally off Vercel serverless; keep them on the Python API host.

## License / use

Built for an academic AI project demonstration. Official UCM documents remain the property of the University of Central Missouri; use publicly posted materials according to institutional terms.
