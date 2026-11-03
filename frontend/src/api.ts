export interface Source {
  source: string;
  text: string;
  score: number;
}
export interface Step {
  name: string;
  detail: string;
  duration_ms: number;
}
export interface Answer {
  request_id: string;
  question: string;
  answer: string;
  grounded: boolean;
  sources: Source[];
  steps: Step[];
}
export interface DocumentInfo {
  id: string;
  source: string;
  chunks: number;
  characters: number;
}
export interface DocumentDetail extends DocumentInfo {
  text: string;
}
export interface VectorStoreInfo {
  provider: string;
  embeddings: string;
  llm: string;
  documents: number;
  chunks: number;
}

// The API returns stable error codes; this is the only place they become sentences.
const ERRORS: Record<string, string> = {
  empty_question: "Please type a question.",
  empty_document: "This document is empty.",
  file_too_large: "File too large (1 MB maximum).",
  text_files_only: "Only text files (.txt, .md) are accepted.",
  document_not_found: "Document not found.",
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code: string = body.error ?? body.detail ?? "";
    throw new Error(ERRORS[code] ?? "Something went wrong.");
  }
  return body as T;
}

export interface StreamHandlers {
  onStep: (step: Step) => void;
  onSources: (sources: Source[]) => void;
  onToken: (text: string) => void;
  onDone: (answer: Answer) => void;
}

/**
 * Reads a Server-Sent Events stream from POST /api/ask/stream.
 * EventSource only supports GET, so the stream is parsed from fetch().
 */
async function streamAnswer(question: string, handlers: StreamHandlers, signal: AbortSignal): Promise<void> {
  const res = await fetch("/api/ask/stream", { ...json("POST", { question }), signal });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(ERRORS[body.error ?? ""] ?? "Something went wrong.");
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    buffer += value;
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      dispatch(frame, handlers);
    }
  }
}

function dispatch(frame: string, handlers: StreamHandlers): void {
  let event = "message";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return;
  const payload = JSON.parse(data);
  switch (event) {
    case "step":
      return handlers.onStep(payload);
    case "sources":
      return handlers.onSources(payload);
    case "token":
      return handlers.onToken(payload.text);
    case "done":
      return handlers.onDone(payload);
    case "error":
      throw new Error(ERRORS[payload.error ?? ""] ?? "Something went wrong.");
  }
}

const json = (method: string, payload: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

export const api = {
  documents: () => call<DocumentInfo[]>("/documents"),
  document: (id: string) => call<DocumentDetail>(`/documents/${id}`),
  create: (source: string, text: string) => call<DocumentInfo>("/documents/text", json("POST", { source, text })),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return call<DocumentInfo>("/documents/upload", { method: "POST", body: form });
  },
  update: (id: string, source: string, text: string) => call<DocumentInfo>(`/documents/${id}`, json("PUT", { source, text })),
  remove: (id: string) => call<void>(`/documents/${id}`, { method: "DELETE" }),
  vectorStore: () => call<VectorStoreInfo>("/vector-store"),
  clearVectorStore: () => call<void>("/vector-store", { method: "DELETE" }),
  reindex: () => call<{ documents: number; chunks: number }>("/vector-store/reindex", { method: "POST" }),
  askStream: streamAnswer,
};
