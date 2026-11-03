import { VectorStoreInfo, api } from "./api";

interface Props {
  info: VectorStoreInfo | null;
  busy: boolean;
  run: (action: () => Promise<unknown>) => Promise<void>;
}

export function VectorStorePanel({ info, busy, run }: Props) {
  const clear = () => {
    if (window.confirm("Empty the vector store? Your documents are kept and can be re-indexed.")) {
      void run(() => api.clearVectorStore());
    }
  };

  return (
    <section>
      <h2>Vector store</h2>
      {info && (
        <dl className="facts">
          <dt>Store</dt>
          <dd>{info.provider}</dd>
          <dt>Embeddings</dt>
          <dd>{info.embeddings}</dd>
          <dt>LLM</dt>
          <dd>{info.llm}</dd>
          <dt>Indexed</dt>
          <dd>
            {info.chunks} passage{info.chunks === 1 ? "" : "s"} from {info.documents} document{info.documents === 1 ? "" : "s"}
          </dd>
        </dl>
      )}
      <div className="row">
        <button className="secondary" disabled={busy || !info?.documents} onClick={() => void run(() => api.reindex())}>
          Re-index all documents
        </button>
        <button className="secondary danger" disabled={busy || !info?.chunks} onClick={clear}>
          Empty the vector store
        </button>
      </div>
      <p className="muted">Re-index after changing the embeddings model or the vector store provider.</p>
    </section>
  );
}
