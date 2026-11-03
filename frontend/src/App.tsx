import { BrainCircuit, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import { AskPanel } from "@/components/ask-panel";
import { DocumentsPanel } from "@/components/documents-panel";
import { ThemeToggle } from "@/components/theme-toggle";
import { TooltipProvider } from "@/components/ui/tooltip";
import { VectorStorePanel } from "@/components/vector-store-panel";
import { DocumentInfo, VectorStoreInfo, api } from "@/api";

export function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [info, setInfo] = useState<VectorStoreInfo | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [docs, store] = await Promise.all([api.documents(), api.vectorStore()]);
    setDocuments(docs);
    setInfo(store);
  }, []);

  // One place for busy/error handling: every action refreshes the lists afterwards and reports its outcome.
  const run = useCallback(
    async (action: () => Promise<unknown>, success?: string): Promise<boolean> => {
      setBusy(true);
      try {
        await action();
        await refresh();
        if (success) toast.success(success);
        return true;
      } catch (e) {
        toast.error((e as Error).message);
        return false;
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
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen bg-gradient-to-b from-muted/40 to-background">
        <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
          <div className="container flex h-14 items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
                <BrainCircuit className="size-5" />
              </div>
              <span className="font-semibold tracking-tight">Semantic RAG</span>
              <span className="hidden text-sm text-muted-foreground sm:inline">FastAPI · LangGraph · ChromaDB</span>
            </div>
            <div className="flex items-center gap-2">
              {busy && (
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
                  <Loader2 className="size-4 animate-spin" /> Working…
                </span>
              )}
              <ThemeToggle />
            </div>
          </div>
        </header>

        <main className="container grid grid-cols-[minmax(0,1fr)] gap-6 py-6 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] lg:items-start">
          <div className="order-2 grid grid-cols-[minmax(0,1fr)] gap-6 lg:order-1">
            <DocumentsPanel documents={documents} busy={busy} run={run} />
            <VectorStorePanel info={info} busy={busy} run={run} />
          </div>
          <div className="order-1 lg:order-2">
            <AskPanel busy={busy} hasDocuments={documents.length > 0} onError={(message) => toast.error(message)} />
          </div>
        </main>
      </div>
      <Toaster richColors position="bottom-right" />
    </TooltipProvider>
  );
}
