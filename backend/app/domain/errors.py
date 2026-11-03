class DomainError(Exception):
    """Business error: carries a stable code, never a technical message."""

    code = "domain_error"


class EmptyQuestionError(DomainError):
    code = "empty_question"


class EmptyDocumentError(DomainError):
    code = "empty_document"


class DocumentNotFoundError(DomainError):
    code = "document_not_found"
