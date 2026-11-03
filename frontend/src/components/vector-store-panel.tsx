import { Bot, Database, Eraser, Layers, RefreshCw, Sparkles } from "lucide-react";
import { useState } from "react";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { VectorStoreInfo, api } from "@/api";

interface Props {
  info: VectorStoreInfo | null;
  busy: boolean;
  run: (action: () => Promise<unknown>, success?: string) => Promise<boolean>;
}

function Fact({ icon: Icon, label, value }: { icon: typeof Database; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <div className="grid size-8 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="truncate text-sm font-medium" title={value}>
          {value}
        </p>
      </div>
    </div>
  );
}

export function VectorStorePanel({ info, busy, run }: Props) {
  const [confirmClear, setConfirmClear] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Vector store</CardTitle>
        <CardDescription>The searchable index, rebuilt from your documents at any time.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {info ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <Fact icon={Database} label="Store" value={info.provider} />
            <Fact icon={Layers} label={`Indexed · ${info.documents} doc${info.documents === 1 ? "" : "s"}`} value={`${info.chunks.toLocaleString("en-US")} passage${info.chunks === 1 ? "" : "s"}`} />
            <Fact icon={Sparkles} label="Embeddings" value={info.embeddings} />
            <Fact icon={Bot} label="LLM" value={info.llm} />
          </div>
        ) : (
          <Skeleton className="h-32 w-full" />
        )}
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={busy || !info?.documents} onClick={() => void run(() => api.reindex(), "Vector store re-indexed")}>
            <RefreshCw /> Re-index all
          </Button>
          <Button variant="outline" size="sm" disabled={busy || !info?.chunks} onClick={() => setConfirmClear(true)}>
            <Eraser /> Empty index
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">Re-index after changing the embeddings model or the vector store provider.</p>
      </CardContent>
      <ConfirmDialog
        open={confirmClear}
        onOpenChange={setConfirmClear}
        title="Empty the vector store?"
        description="Search stops working until you re-index. Your documents are kept."
        confirmLabel="Empty index"
        onConfirm={() => void run(() => api.clearVectorStore(), "Vector store emptied")}
      />
    </Card>
  );
}
