import { useCallback, useEffect, useState } from "react";
import { AskPanel } from "./AskPanel";
import { DocumentsPanel } from "./DocumentsPanel";
import { VectorStorePanel } from "./VectorStorePanel";
import { DocumentInfo, VectorStoreInfo, api } from "./api";

export function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [info, setInfo] = useState<VectorStoreInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [docs, store] = await Promise.all([api.documents(), api.vectorStore()]);
    setDocuments(docs);
    setInfo(store);
  }, []);

  // One place for busy/error handling: every action refreshes the lists afterwards.
  const run = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        await refresh();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  useEffect(() => {
    void run(async () => undefined);
  }, [run]);

  return (
    <main>
      <h1>Semantic RAG</h1>
      <p className="muted">FastAPI · LangChain · LangGraph · ChromaDB: ask questions to your own documents.</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <DocumentsPanel documents={documents} busy={busy} run={run} />
      <AskPanel busy={busy} hasDocuments={documents.length > 0} />
      <VectorStorePanel info={info} busy={busy} run={run} />
    </main>
  );
}
