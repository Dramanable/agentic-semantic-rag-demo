# Semantic RAG demo

Ask questions to your own documents. **Semantic search** (embeddings + ChromaDB), a
**LangGraph** workflow (retrieve → grade → rewrite → answer), a **FastAPI** API and a
**React** UI, built with **clean architecture** and fully **dockerized**.

- **Any LLM provider**: OpenAI, Anthropic, Mistral, Ollama, or any OpenAI-compatible server (Groq, vLLM, LM Studio…).
- **Any vector store**: ChromaDB or in-memory out of the box; add another one in ~10 lines.
- **Streaming answers**: sources and reasoning steps appear first, then the answer token by token (SSE), with a Stop button.
- **Manage your data**: add, edit and delete documents; inspect, empty and re-index the vector store.
- **Traceable and observable**: request IDs, timed reasoning steps, JSON logs, Prometheus metrics.

## Quick start

```bash
cp .env.example .env     # optional: without any key the demo runs locally
docker compose up --build
```

Open http://localhost:8080, upload the files from `sample-docs/`, then ask
*"How can hallucinations be reduced?"*.

- **No API key**: local multilingual embeddings (FastEmbed) and *extractive* answers (the retrieved passages, nothing invented).
- **With an LLM**: set `LLM_PROVIDER` (and `LLM_API_KEY`) in `.env`. Embeddings are chosen separately (`EMBEDDINGS_PROVIDER`).

### Choosing providers

| Setting | Values |
|---|---|
| `LLM_PROVIDER` | `extractive`, `openai`, `anthropic`, `mistral`, `ollama`, `openai_compatible` |
| `EMBEDDINGS_PROVIDER` | `fastembed`, `openai`, `mistral`, `ollama`, `openai_compatible` |
| `VECTOR_STORE_PROVIDER` | `chroma`, `memory` |

Examples:

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

An unknown provider name stops the API at startup with the list of available ones.
After changing the embeddings model or the vector store, use **Re-index all documents**
(UI or `POST /api/vector-store/reindex`): the documents are the source of truth, the
vector store is a rebuildable index.

## Architecture

```
backend/app
├── domain/           entities, business errors, PORTS (VectorStore, TextGenerator, DocumentRepository, TextSplitter)
├── application/      use cases (IngestDocument, UpdateDocument, ReindexAll, AskQuestion…): they only know ports
├── infrastructure/   ADAPTERS: LangChain LLMs/embeddings/vector stores, JSON document repository,
│   └── providers/    registries: one decorated function per provider
│                     LangGraph workflow, observability, composition root (container.py)
└── presentation/     FastAPI: routes, schemas, tracing middleware
```

Dependency rule: `domain` ← `application` ← `infrastructure` / `presentation`. A test
(`tests/test_architecture.py`) fails if `domain` or `application` imports a framework.
Adapters are proven by the **same tests** run against each implementation
(`tests/test_vector_store_adapters.py`).

### Adding a provider

No existing code changes (open/closed): register a builder.

```python
# backend/app/infrastructure/providers/llm.py
@llm_providers.register("my-llm")
def _my_llm(settings: Settings) -> TextGenerator:
    return LangChainTextGenerator(MyChatModel(api_key=settings.llm_api_key))
```

Then set `LLM_PROVIDER=my-llm`. The same pattern applies to `embeddings_providers` and
`vector_store_providers` (e.g. Qdrant, pgvector: wrap any LangChain `VectorStore`
with `LangChainVectorStore`).

### The workflow

```
retrieve → grade ─┬─ relevant ─────────────────→ generate → end
                  ├─ nothing + rewrite allowed → rewrite → retrieve
                  └─ nothing ──────────────────→ give_up → end   ("I don't know", never an invention)
```

## Evaluation and confidence

**Confidence of an answer.** Every answer carries a confidence (`high` / `medium` / `low`, plus a 0-1 score) shown as a
badge in the UI and returned by the API (`confidence`). It is the similarity of the best source, bucketed by
`CONFIDENCE_HIGH` (0.6) and `CONFIDENCE_MEDIUM` (0.45). It measures *retrieval*, not truth: always check the sources.
No relevant source means no answer and no confidence (`none`), never an invented answer.

**Evaluating the RAG.** `make eval` indexes `sample-docs/` in a throw-away store, runs the questions of
`eval/dataset.json` (answerable ones with their expected source, plus questions the documents cannot answer) through the real
workflow, and prints:

| Metric | Question it answers |
|---|---|
| Retrieval hit rate, MRR | Is the expected source found, and ranked first? |
| Abstention rate | Does it stay silent when the documents cannot answer? |
| Accuracy by confidence level | **Is the confidence trustworthy?** (is `high` really right more often than `low`?) |
| Confidence gap | Does confidence separate answerable from unanswerable questions? |

It uses whatever providers your `.env` selects, so you can compare embeddings models or LLMs on the same questions.
Options: `--json report.json`, `--fail-under 0.8` (exit code 1 below that accuracy, handy in CI).

Reference run with the default local embeddings (14 questions, so indicative only):

| `RELEVANCE_THRESHOLD` | Answerable found | Abstains when it should | `high`/`medium` answers correct |
|---|---|---|---|
| **0.30 (default)** | 70 % | 100 % | 4/4 |
| 0.25 | 80 % | 75 % | 4/4 |
| 0.20 | 90 % | 75 % | 4/4 |

The threshold is a precision/recall trade-off: lower it and more legitimate questions get an answer, but an unrelated one
sometimes slips through (at 0.26, with `low` confidence). The default favours never answering wrongly. Calibrate
`RELEVANCE_THRESHOLD` and the confidence buckets on your own documents and questions.
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
make eval     # RAG quality and confidence report
make test     # unit and API tests in a dedicated container: no network, no model download
make up       # build and start (UI on :8080, API proxied under /api)
make logs     # JSON logs of the API
make reset    # delete documents and the vector store
```

Nothing to install on the host: Python, Node and the embeddings model live in the images.

## API

| Route | Purpose |
|---|---|
| `GET /api/documents` · `GET /api/documents/{id}` | list · read one (with full text) |
| `POST /api/documents/text` · `POST /api/documents/upload` | add (or replace the document with the same name) |
| `PUT /api/documents/{id}` | edit text and/or name, then re-index that document |
| `DELETE /api/documents/{id}` | delete the document and its passages |
| `GET /api/vector-store` | provider, embeddings, LLM, document and passage counts |
| `DELETE /api/vector-store` | empty the index (documents are kept) |
| `POST /api/vector-store/reindex` | rebuild the index from the documents |
| `POST /api/ask/stream` `{question}` | **streamed answer** (Server-Sent Events): `step`, `sources`, `token`…, `done`, or `error` |
| `POST /api/ask` `{question}` | complete answer in one response: answer, sources, trace, `request_id` |
| `GET /api/health` · `GET /metrics` | health · metrics |

Errors are `{"error": "<stable_code>"}` (`empty_question`, `empty_document`, `document_not_found`…).
