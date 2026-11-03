import json
import os
import re
from pathlib import Path

from app.domain.entities import Document

_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class JsonDocumentRepository:
    """Adapter of the DocumentRepository port: one JSON file per document, atomic writes."""

    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, document_id: str) -> Path:
        if not _SAFE_ID.match(document_id):  # the id comes from the URL: never an arbitrary path
            raise ValueError("invalid document id")
        return self._dir / f"{document_id}.json"

    def save(self, document: Document) -> None:
        target = self._path(document.id)
        temp = target.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {"id": document.id, "source": document.source, "text": document.text, "chunk_count": document.chunk_count},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(temp, target)

    def get(self, document_id: str) -> Document | None:
        try:
            path = self._path(document_id)
        except ValueError:
            return None
        if not path.exists():
            return None
        return Document(**json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[Document]:
        return [Document(**json.loads(p.read_text(encoding="utf-8"))) for p in self._dir.glob("*.json")]

    def delete(self, document_id: str) -> bool:
        try:
            path = self._path(document_id)
        except ValueError:
            return False
        if not path.exists():
            return False
        path.unlink()
        return True
