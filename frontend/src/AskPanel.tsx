import { FormEvent, useRef, useState } from "react";
import { Source, Step, api } from "./api";

interface Props {
  busy: boolean;
  hasDocuments: boolean;
}

interface View {
  steps: Step[];
  sources: Source[];
  text: string;
  grounded: boolean;
  requestId: string | null;
  state: "streaming" | "done" | "stopped";
}

const EMPTY: View = { steps: [], sources: [], text: "", grounded: true, requestId: null, state: "streaming" };

export function AskPanel({ busy, hasDocuments }: Props) {
  const [question, setQuestion] = useState("");
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const streaming = view?.state === "streaming";

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    controller.current = new AbortController();
    setError(null);
    setView(EMPTY);
    const patch = (change: (v: View) => View) => setView((v) => (v ? change(v) : v));
    try {
      await api.askStream(
        question,
        {
          onStep: (step) => patch((v) => ({ ...v, steps: [...v.steps, step] })),
          onSources: (sources) => patch((v) => ({ ...v, sources })),
          onToken: (text) => patch((v) => ({ ...v, text: v.text + text })),
          onDone: (a) =>
            patch((v) => ({ ...v, text: a.answer, grounded: a.grounded, sources: a.sources, steps: a.steps, requestId: a.request_id, state: "done" })),
        },
        controller.current.signal,
      );
    } catch (e) {
      if ((e as Error).name === "AbortError") patch((v) => ({ ...v, state: "stopped" }));
      else {
        setError((e as Error).message);
        setView(null);
      }
    }
  };

  return (
    <>
      <section>
        <h2>Ask a question</h2>
        <form className="row" onSubmit={(e) => void ask(e)}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. How does the LangGraph workflow work?"
            maxLength={1000}
          />
          {streaming ? (
            <button type="button" className="secondary" onClick={() => controller.current?.abort()}>
              Stop
            </button>
          ) : (
            <button type="submit" disabled={busy || !hasDocuments || !question.trim()}>
              Ask
            </button>
          )}
        </form>
        {!hasDocuments && <p className="muted">Add a document first.</p>}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </section>

      {view && (
        <section aria-live="polite">
          <h2>Answer</h2>
          {streaming && view.text === "" && (
            <p className="muted">{view.steps.length ? view.steps[view.steps.length - 1].detail : "Searching…"}</p>
          )}
          {view.text !== "" && (
            <p className={view.grounded ? "answer" : "answer ungrounded"}>
              {view.text}
              {streaming && <span className="caret" aria-hidden="true" />}
            </p>
          )}
          {view.state === "stopped" && <p className="muted">Stopped.</p>}

          {view.sources.length > 0 && (
            <>
              <h3>Sources</h3>
              <ol>
                {view.sources.map((s, i) => (
                  <li key={i}>
                    <strong>{s.source}</strong> <span className="badge">similarity {(s.score * 100).toFixed(0)}%</span>
                    <blockquote>{s.text}</blockquote>
                  </li>
                ))}
              </ol>
            </>
          )}

          <details open={streaming}>
            <summary>Reasoning trace ({view.steps.length} steps)</summary>
            <ol className="trace">
              {view.steps.map((s, i) => (
                <li key={i}>
                  <code>{s.name}</code> {s.detail} <span className="muted">{s.duration_ms} ms</span>
                </li>
              ))}
            </ol>
            {view.requestId && (
              <p className="muted">
                Request ID: <code>{view.requestId}</code> (also present on every API log line)
              </p>
            )}
          </details>
        </section>
      )}
    </>
  );
}
