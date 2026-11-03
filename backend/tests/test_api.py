from fastapi.testclient import TestClient

from app.main import create_app
from tests.wiring import build_test_container


def client() -> TestClient:
    container, *_ = build_test_container()
    return TestClient(create_app(container))


def test_full_flow_ingest_ask_list_delete():
    with client() as c:
        r = c.post("/api/documents/upload", files={"file": ("cats.txt", "the cat sleeps on the sofa".encode())})
        assert r.status_code == 201
        doc_id = r.json()["id"]
        assert c.get("/api/documents").json()[0]["chunks"] == 1
        a = c.post("/api/ask", json={"question": "where the cat sleeps"}).json()
        assert a["grounded"] and a["sources"][0]["source"] == "cats.txt"
        assert c.delete(f"/api/documents/{doc_id}").status_code == 204
        assert c.delete(f"/api/documents/{doc_id}").status_code == 404


def test_blank_question_is_a_domain_error_not_a_crash():
    with client() as c:
        r = c.post("/api/ask", json={"question": "  "})
        assert r.status_code == 422 and r.json() == {"error": "empty_question"}


def test_empty_document_and_binary_upload_are_refused():
    with client() as c:
        assert c.post("/api/documents/text", json={"source": "x", "text": " "}).json() == {"error": "empty_document"}
        assert c.post("/api/documents/upload", files={"file": ("b.bin", b"\xff\xfe\x00")}).status_code == 415


def test_request_id_is_echoed_and_returned_in_the_answer():
    with client() as c:
        c.post("/api/documents/text", json={"source": "x", "text": "the cat sleeps"})
        r = c.post("/api/ask", json={"question": "cat"}, headers={"X-Request-ID": "abc123"})
        assert r.headers["X-Request-ID"] == "abc123" and r.json()["request_id"] == "abc123"
        assert [s["name"] for s in r.json()["steps"]][0] == "retrieve"


def test_unsafe_request_id_is_replaced():
    with client() as c:
        r = c.get("/api/health", headers={"X-Request-ID": "bad id\twith spaces"})
        assert r.headers["X-Request-ID"].isalnum() and len(r.headers["X-Request-ID"]) == 32


def test_metrics_endpoint_exposes_rag_and_http_series():
    with client() as c:
        c.post("/api/ask", json={"question": "nothing"})
        body = c.get("/metrics").text
        assert "rag_questions_total" in body and 'http_requests_total{method="POST",path="/api/ask"' in body
        assert "rag_step_duration_seconds" in body


def test_edit_a_document_then_ask_about_the_new_content():
    with client() as c:
        doc = c.post("/api/documents/text", json={"source": "n.txt", "text": "the cat sleeps"}).json()
        assert c.get(f"/api/documents/{doc['id']}").json()["text"] == "the cat sleeps"
        r = c.put(f"/api/documents/{doc['id']}", json={"text": "the dog barks"})
        assert r.status_code == 200 and r.json()["characters"] == 13
        assert not c.post("/api/ask", json={"question": "cat"}).json()["grounded"]
        assert c.post("/api/ask", json={"question": "dog barks"}).json()["grounded"]


def test_unknown_document_is_404_with_a_stable_code():
    with client() as c:
        assert c.get("/api/documents/nope").json() == {"error": "document_not_found"}
        assert c.put("/api/documents/nope", json={"text": "x"}).status_code == 404
        assert c.delete("/api/documents/nope").status_code == 404


def test_vector_store_info_clear_and_reindex():
    with client() as c:
        c.post("/api/documents/text", json={"source": "a", "text": "one\ntwo"})
        info = c.get("/api/vector-store").json()
        assert info == {"provider": "fake", "embeddings": "fake-embeddings", "llm": "fake-llm", "documents": 1, "chunks": 2}
        assert c.delete("/api/vector-store").status_code == 204
        assert c.get("/api/vector-store").json()["chunks"] == 0
        assert not c.post("/api/ask", json={"question": "one"}).json()["grounded"]
        assert c.post("/api/vector-store/reindex").json() == {"documents": 1, "chunks": 2}
        assert c.post("/api/ask", json={"question": "one"}).json()["grounded"]
