"""The dependency rule is enforced by a test: domain and application know no framework."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
FORBIDDEN = {"langchain", "langchain_core", "langchain_community", "langchain_chroma", "langchain_openai",
             "langchain_anthropic", "langchain_mistralai", "langgraph", "chromadb", "fastapi", "pydantic",
             "pydantic_settings", "fastembed", "prometheus_client", "uvicorn"}


def imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0] if node.level == 0 else "")
            if node.module.startswith("app."):
                roots.add(node.module)
    return roots


def violations(layer: str, forbidden_internal: tuple[str, ...]) -> list[str]:
    found = []
    for path in (APP / layer).rglob("*.py"):
        for root in imported_roots(path):
            if root in FORBIDDEN or root.startswith(forbidden_internal):
                found.append(f"{path.relative_to(APP)} importe {root}")
    return found


def test_domain_depends_on_nothing_outside_itself():
    assert violations("domain", ("app.application", "app.infrastructure", "app.presentation")) == []


def test_application_knows_only_the_domain_and_ports():
    assert violations("application", ("app.infrastructure", "app.presentation")) == []
