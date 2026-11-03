import { FileText, Pencil, Plus, Trash2, Upload } from "lucide-react";
import { useState } from "react";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { DocumentDialog } from "@/components/document-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { DocumentInfo, api } from "@/api";

interface Props {
  documents: DocumentInfo[];
  busy: boolean;
  /** Runs an action with the shared busy/error handling and a success message, then refreshes the lists. */
  run: (action: () => Promise<unknown>, success?: string) => Promise<boolean>;
}

type Editing = { mode: "create" } | { mode: "edit"; id: string; source: string; text: string };

export function DocumentsPanel({ documents, busy, run }: Props) {
  const [editing, setEditing] = useState<Editing | null>(null);
  const [toDelete, setToDelete] = useState<DocumentInfo | null>(null);

  const startEdit = (id: string) =>
    run(async () => {
      const doc = await api.document(id);
      setEditing({ mode: "edit", id, source: doc.source, text: doc.text });
    });

  const save = async (source: string, text: string) => {
    const edit = editing?.mode === "edit" ? editing : null;
    const ok = await run(
      () => (edit ? api.update(edit.id, source, text) : api.create(source, text)),
      edit ? "Document updated and re-indexed" : "Document added",
    );
    if (ok) setEditing(null);
  };

  const upload = (files: FileList | null) =>
    run(async () => {
      for (const file of Array.from(files ?? [])) await api.upload(file);
    }, "Files indexed");

  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle>Documents</CardTitle>
          <CardDescription>Your knowledge base.</CardDescription>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" asChild disabled={busy}>
            <label className="cursor-pointer">
              <Upload /> Upload
              <input
                type="file"
                accept=".txt,.md,text/plain,text/markdown"
                multiple
                hidden
                onChange={(e) => {
                  void upload(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          </Button>
          <Button size="sm" onClick={() => setEditing({ mode: "create" })} disabled={busy}>
            <Plus /> New
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {documents.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed py-8 text-center">
            <FileText className="size-8 text-muted-foreground" />
            <p className="text-sm font-medium">No documents yet</p>
            <p className="max-w-[18rem] text-sm text-muted-foreground">Upload a .md or .txt file, or write a new document, to start asking questions.</p>
          </div>
        ) : (
          <ul className="divide-y rounded-lg border">
            {documents.map((d) => (
              <li key={d.id} className="flex items-center gap-3 px-3 py-2.5">
                <FileText className="size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{d.source}</p>
                  <p className="text-xs text-muted-foreground">
                    {d.chunks} passage{d.chunks === 1 ? "" : "s"} · {d.characters.toLocaleString("en-US")} characters
                    {d.chunks === 0 && " · not indexed"}
                  </p>
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="size-8" disabled={busy} onClick={() => void startEdit(d.id)} aria-label={`Edit ${d.source}`}>
                      <Pencil />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Edit</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-destructive hover:text-destructive"
                      disabled={busy}
                      onClick={() => setToDelete(d)}
                      aria-label={`Delete ${d.source}`}
                    >
                      <Trash2 />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Delete</TooltipContent>
                </Tooltip>
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      <DocumentDialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        initial={editing?.mode === "edit" ? { source: editing.source, text: editing.text } : undefined}
        busy={busy}
        onSave={(source, text) => void save(source, text)}
      />
      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => !open && setToDelete(null)}
        title={`Delete "${toDelete?.source ?? ""}"?`}
        description="The document and its passages are removed from the vector store. This cannot be undone."
        confirmLabel="Delete"
        onConfirm={() => toDelete && void run(() => api.remove(toDelete.id), "Document deleted")}
      />
    </Card>
  );
}
