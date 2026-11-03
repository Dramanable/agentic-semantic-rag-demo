# --- shared dependencies -------------------------------------------------
FROM python:3.12-slim AS deps
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- tests: docker compose run --rm tests --------------------------------
FROM deps AS test
COPY requirements-dev.txt pytest.ini ./
RUN pip install -r requirements-dev.txt
COPY app app
COPY tests tests
CMD ["pytest", "-q"]

# --- runtime -------------------------------------------------------------
FROM deps AS runtime
# The local embedding model is downloaded at build time: the first start is instant.
ARG FASTEMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ENV FASTEMBED_CACHE_PATH=/opt/fastembed
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('${FASTEMBED_MODEL}')"
COPY app app
RUN useradd --create-home app && mkdir -p /data && chown -R app /data /opt/fastembed
USER app
ENV CHROMA_PATH=/data/chroma DOCUMENTS_PATH=/data/documents
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=10 CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
