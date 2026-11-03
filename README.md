# Semantic RAG demo

Ask questions to your own documents, in your own words. **Semantic search** (embeddings + ChromaDB), a **LangGraph**
workflow (retrieve → grade → rewrite → answer), a **FastAPI** API and a **React** UI (Tailwind + shadcn/ui), built with
**clean architecture** and fully **dockerized**. The sample corpus is European legislation (GDPR, AI Act, Consumer Rights Directive).

- **Any LLM provider**: OpenAI, Anthropic, Mistral, Ollama, or any OpenAI-compatible server (Groq, vLLM, LM Studio…).
- **Any vector store**: ChromaDB or in-memory out of the box; add another one in ~10 lines.
- **Manage your data**: add, edit and delete documents; inspect, empty and re-index the vector store.
- **Streaming answers**: sources and reasoning steps appear first, then the answer token by token (SSE), with a Stop button.
- **Trustworthy**: every answer has sources and a confidence level; when nothing is relevant it says so instead of inventing.
- **Measurable**: `make eval` reports retrieval quality and whether the confidence can be trusted.
- **Traceable and observable**: request IDs, timed reasoning steps, JSON logs, Prometheus metrics, optional LangSmith.
- **Modern UI**: React + Tailwind CSS + shadcn/ui components (Radix, Lucide icons), light/dark theme, responsive down to phones.
  shadcn/ui is not a CDN library: its components live in `frontend/src/components/ui/` and Tailwind is compiled at build time,
  so the UI works offline.

## Quick start

Requirements: Docker with Compose. Nothing else is installed on your machine.

```bash
cp .env.example .env     # optional: without any key the demo runs locally
docker compose up --build
```

Open http://localhost:8080 and upload the files from `sample-docs/` (the GDPR alone takes a minute or two to index on CPU),
then ask *"When is the processing of personal data lawful?"* or *"What is the withdrawal period for distance contracts?"*.

- **No API key** (default): local multilingual embeddings (FastEmbed) and *extractive* answers: the best matching passage is
  shown, the other passages are listed as sources, nothing is invented.
- **With an LLM**: set `LLM_PROVIDER` (and `LLM_API_KEY`) in `.env`, then `docker compose up -d`. The LLM writes the answer
  from the retrieved passages only. Embeddings are chosen separately (`EMBEDDINGS_PROVIDER`).

## How it works

```
upload / edit ──► split into passages ──► embed ──► vector store          (documents are the source of truth,
                  (each one prefixed with its heading path)                the vector store is a rebuildable index)

question ──► retrieve ──► grade ─┬─ relevant ──────────────────────► generate (streamed) ──► answer + sources + confidence
                                 ├─ nothing, rewrite allowed ──────► rewrite ──► retrieve
                                 └─ nothing ───────────────────────► give_up ──► "no relevant source" (never an invention)
```

- **Contextual chunks.** The text is cut along its Markdown headings, then into passages of at most `CHUNK_SIZE` characters.
  Every passage is stored with its heading path (`Regulation > Article 17 - Right to erasure`): "Article 5" exists in the GDPR
  and in the AI Act, and a long article keeps its title on every passage.
- **Grade.** Passages below `RELEVANCE_THRESHOLD` similarity are dropped. If none is left, the question is rewritten
  (by the LLM, if configured) and searched again, up to `MAX_REWRITES` times, then the system gives up.
- **Editing is safe.** Saving a document replaces only its own passages; if the new text is invalid, the previous version stays.

### Sample documents: European legislation

Legal texts are what semantic search is made for: people ask in everyday words, the law answers in its own. `sample-docs/` holds
official texts of the European Union (EUR-Lex, reuse authorised under Commission Decision 2011/833/EU):

| File | Text |
|---|---|
| `gdpr.md` | General Data Protection Regulation (EU) 2016/679, all 99 articles |
| `ai-act.md` | AI Act (EU) 2024/1689, selected articles (scope, prohibited practices, high-risk requirements, transparency, penalties) |
| `consumer-rights-directive.md` | Consumer Rights Directive 2011/83/EU, all 35 articles |

Any other `.md` or `.txt` file works too, in any language the embeddings model supports (the default one is multilingual).

## Configuration

Everything is configured by environment variables, set in `.env` (see `.env.example`, which documents each one).

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `extractive` | `extractive`, `openai`, `anthropic`, `mistral`, `ollama`, `openai_compatible` |
| `LLM_MODEL` · `LLM_API_KEY` · `LLM_BASE_URL` | empty | model (empty = provider default), key, endpoint (`ollama` / `openai_compatible`) |
| `EMBEDDINGS_PROVIDER` | `fastembed` | `fastembed` (local), `openai`, `mistral`, `ollama`, `openai_compatible` |
| `EMBEDDINGS_MODEL` · `EMBEDDINGS_API_KEY` · `EMBEDDINGS_BASE_URL` | empty | same as above, for embeddings |
| `VECTOR_STORE_PROVIDER` | `chroma` | `chroma` (persistent), `memory` (lost on restart) |
| `CHUNK_SIZE` · `CHUNK_OVERLAP` | `400` · `50` | passage size in characters; keep it under the embeddings model window (~500 characters for the default one) |
| `TOP_K` | `4` | passages retrieved per search |
| `RELEVANCE_THRESHOLD` | `0.45` | minimum similarity (0-1) to count as relevant; below it, no answer |
| `MAX_REWRITES` | `1` | query rewrites attempted before giving up |
| `CONFIDENCE_HIGH` · `CONFIDENCE_MEDIUM` | `0.6` · `0.45` | confidence buckets on the best source similarity |
| `LANGSMITH_TRACING` · `LANGSMITH_API_KEY` · `LANGSMITH_PROJECT` | `false` | optional LangSmith tracing, see below |

Data lives in the `data` Docker volume (`/data`: vector store and document texts). `make reset` deletes it.
An unknown provider name stops the API at startup with the list of available ones.

### Choosing providers

```bash
# Anthropic
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...

# Local Ollama running on the host (nothing leaves your machine)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
EMBEDDINGS_PROVIDER=ollama

# Groq (OpenAI-compatible)
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
LLM_API_KEY=gsk_...
```

After changing the **embeddings model or the vector store**, click **Re-index all** in the UI (or
`POST /api/vector-store/reindex`): vectors from different models are not comparable.

### Adding a provider

No existing code changes (open/closed): register a builder.

```python
# backend/app/infrastructure/providers/llm.py
@llm_providers.register("my-llm")
def _my_llm(settings: Settings) -> TextGenerator:
    return LangChainTextGenerator(MyChatModel(api_key=settings.llm_api_key))
```

Then set `LLM_PROVIDER=my-llm`. The same pattern applies to `embeddings_providers` and `vector_store_providers`
(e.g. Qdrant, pgvector: wrap any LangChain `VectorStore` with `LangChainVectorStore`).

## Architecture

```
.
├── backend/app
│   ├── domain/           entities, confidence rule, business errors, PORTS
│   │                     (VectorStore, TextGenerator, DocumentRepository, TextSplitter)
│   ├── application/      use cases (IngestDocument, UpdateDocument, ReindexAll, AskQuestion…)
│   │                     and the evaluation logic: they only know ports
│   ├── infrastructure/   ADAPTERS: LangChain LLMs / embeddings / vector stores, JSON document repository,
│   │   └── providers/    registries (one decorated function per provider),
│   │                     LangGraph workflow, observability, composition root (container.py)
│   └── presentation/     FastAPI routes and schemas, tracing middleware, evaluation CLI
├── frontend/             React + Tailwind + shadcn/ui, served by nginx (which proxies /api)
├── eval/dataset.json     questions used by `make eval`
├── sample-docs/          the legislation corpus
└── observability/        Prometheus configuration
```

Dependency rule: `domain` ← `application` ← `infrastructure` / `presentation`. A test (`tests/test_architecture.py`) fails if
`domain` or `application` imports a framework. Adapters are proven by the **same tests** run against each implementation
(`tests/test_vector_store_adapters.py` runs every vector store through the same cases).

## Streaming protocol

`POST /api/ask/stream` answers with Server-Sent Events (`text/event-stream`), in this order:

| Event | Payload |
|---|---|
| `step` (several) | `{"name": "retrieve", "detail": "…", "duration_ms": 51.6}` |
| `sources` (once, if any) | `[{"source": "gdpr.md", "text": "…", "score": 0.74}]`, sent **before** the first token |
| `token` (many) | `{"text": " word"}` |
| `done` | the complete answer: `request_id`, `answer`, `grounded`, `confidence`, `sources`, `steps` |
| `error` | `{"error": "<stable_code>"}` if something fails after the stream started |

A blank question is refused with a regular `422` before any stream opens. EventSource only supports GET, so the UI reads the
stream with `fetch`. nginx has proxy buffering disabled so that tokens reach the browser immediately.

## Evaluation and confidence

**Confidence of an answer.** Every answer carries a confidence (`high` / `medium` / `low`, plus a 0-1 score) shown as a
badge in the UI and returned by the API (`confidence`). It is the similarity of the best source, bucketed by
`CONFIDENCE_HIGH` and `CONFIDENCE_MEDIUM`. It measures *retrieval*, not truth: always check the sources.
No relevant source means no answer and no confidence (`none`), never an invented answer.

**Evaluating the RAG.** `make eval` indexes `sample-docs/` in a throw-away store, runs the questions of
`eval/dataset.json` through the real workflow, and prints:

| Metric | Question it answers |
|---|---|
| Retrieval hit rate, MRR | Is the expected source found, and ranked first? |
| Abstention rate | Does it stay silent when the documents cannot answer? |
| Accuracy by confidence level | **Is the confidence trustworthy?** (is `high` really right more often than `low`?) |
| Confidence gap | Does confidence separate answerable from unanswerable questions? |

The dataset is a JSON list; `expected_source: null` marks a question the documents cannot answer (the right behaviour is to abstain):

```json
[
  {"question": "What is the right to erasure?", "expected_source": "gdpr.md"},
  {"question": "What is the capital of Japan?", "expected_source": null}
]
```

It uses whatever providers your `.env` selects, so you can compare embeddings models or LLMs on the same questions.
Options (`docker compose --profile eval run --rm eval python -m app.presentation.evaluation_cli --help`): `--json report.json`,
`--fail-under 0.8` (exit code 1 below that accuracy, handy in CI).

Reference run on the sample legislation (19 questions: 14 answerable, 5 not; default local embeddings, so indicative only):

| `RELEVANCE_THRESHOLD` | Right source found | Abstains when it should | Overall accuracy |
|---|---|---|---|
| 0.30 | 100 % | 60 % | 89 % |
| 0.40 | 100 % | 100 % | 100 % |
| **0.45 (default)** | 100 % | 100 % | 100 % |

At 0.30 the two out-of-corpus *legal-sounding* questions (French corporate tax rate, German minimum wage) were answered from
unrelated GDPR passages, and the badge flagged them `low` confidence (0/2 correct), while all 13 `high` answers were right.
Correct questions scored 0.50 or more and out-of-corpus ones 0.40 or less, so 0.45 sits in the middle of the gap. That
calibration was done on these same questions: **recalibrate `RELEVANCE_THRESHOLD` and the confidence buckets on your own
documents and questions** (short, informal documents usually score lower and need a lower threshold).
Limits: the default `extractive` mode returns passages, so generation faithfulness (hallucination in a model's
wording) is not measured; evaluate it by plugging in an LLM and extending `app/application/evaluation.py`.

## Traceability and observability

- **Request ID**: `X-Request-ID` (reused from an upstream proxy, otherwise generated), returned as a
  header **and** in the answer (`request_id`), and present on **every log line**.
- **Answer trace**: every graph node reports what it did and how long it took (`steps` in the response,
  shown in the UI), along with the sources and their similarity scores.
- **Structured JSON logs** (`ts`, `level`, `service`, `request_id`, `event`, `step`, `duration_ms`…): `make logs`.
- **Prometheus metrics** on `/metrics`: `http_requests_total`, `http_request_duration_seconds`,
  `rag_questions_total{grounded}`, `rag_step_duration_seconds{step}`, `rag_first_token_seconds`, `rag_rewrites_total`.
  `docker compose --profile observability up` adds Prometheus on http://localhost:9090.
- **LangSmith (optional)**: see below.

### LangSmith

Every LangChain/LangGraph call (retrieval, rewrite, LLM generation) can be traced in [LangSmith](https://smith.langchain.com):

```bash
# .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=semantic-rag-demo
# LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com   # EU region
```

Then `docker compose up -d`. Each question appears as a `semantic_rag` run, tagged `semantic-rag-demo`, with the
API `request_id` in its metadata: copy it from the UI trace or from a log line to find the matching LangSmith run.
Tracing is off by default and nothing is sent anywhere unless you enable it.

## Development (everything in Docker)

```bash
make up       # build and start (UI on :8080, API proxied under /api)
make test     # unit and API tests in a dedicated container: no network, no model download
make eval     # RAG quality and confidence report
make logs     # JSON logs of the API
make down     # stop
make reset    # stop and delete documents and the vector store
```

Nothing to install on the host: Python, Node and the embeddings model live in the images. The backend tests use in-memory
fakes for the ports, plus the real ChromaDB and in-memory adapters with fake embeddings.

## API

| Route | Purpose |
|---|---|
| `GET /api/documents` · `GET /api/documents/{id}` | list · read one (with full text) |
| `POST /api/documents/text` · `POST /api/documents/upload` | add (or replace the document with the same name); upload accepts UTF-8 text files up to 1 MB |
| `PUT /api/documents/{id}` | edit text and/or name, then re-index that document |
| `DELETE /api/documents/{id}` | delete the document and its passages |
| `GET /api/vector-store` | provider, embeddings, LLM, document and passage counts |
| `DELETE /api/vector-store` | empty the index (documents are kept) |
| `POST /api/vector-store/reindex` | rebuild the index from the documents |
| `POST /api/ask/stream` `{question}` | **streamed answer** (Server-Sent Events), see above |
| `POST /api/ask` `{question}` | complete answer in one response: answer, sources, confidence, trace, `request_id` |
| `GET /api/health` · `GET /metrics` | health · metrics |

Business errors are `{"error": "<stable_code>"}` (`empty_question`, `empty_document`, `document_not_found`); upload errors are
`{"detail": "file_too_large"}` (413) or `{"detail": "text_files_only"}` (415). The UI is the only place where these codes
become sentences.

## Limits and production notes

This is a demonstration, not a hardened service.

- **No authentication**: do not expose it on the internet as is. Put it behind your own auth and TLS.
- **Single instance**: documents are JSON files and ChromaDB runs embedded, both on the local volume. For several replicas, implement
  `DocumentRepository` on a database and register a networked vector store (Qdrant, pgvector…).
- **Indexing is synchronous**: a large document keeps the request open until it is indexed (about 90 s for the GDPR on CPU).
  Use a hosted embeddings provider or a job queue for bulk loads.
- **Confidence is a retrieval signal**, not a guarantee of truth, and the thresholds are specific to an embeddings model.
- **Legal texts are for demonstration**: this is not legal advice; check the official Journal of the European Union.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "No relevant source" on a question you expect to be covered | similarity is below `RELEVANCE_THRESHOLD`: check the scores with `make eval`, lower the threshold or rephrase |
| Search returns nothing after switching embeddings or vector store | re-index (UI **Re-index all**): the old vectors are not comparable |
| Ollama / LM Studio unreachable from the container | they must listen on the host; the default URL uses `host.docker.internal` (mapped in `docker-compose.yml`) |
| `.env` values seem ignored | `docker compose up -d` again (environment is read at container creation); keep comments on their own line |
| Upload fails with 415 / 413 | only UTF-8 text files up to 1 MB are accepted |
