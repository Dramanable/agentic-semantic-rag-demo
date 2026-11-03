import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present when editing an existing document, absent when creating one. */
  initial?: { source: string; text: string };
  busy: boolean;
  onSave: (source: string, text: string) => void;
}

export function DocumentDialog({ open, onOpenChange, initial, busy, onSave }: Props) {
  const [source, setSource] = useState("");
  const [text, setText] = useState("");

  useEffect(() => {
    if (open) {
      setSource(initial?.source ?? "");
      setText(initial?.text ?? "");
    }
  }, [open, initial]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSave(source.trim(), text);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>{initial ? "Edit document" : "New document"}</DialogTitle>
            <DialogDescription>
              {initial ? "Saving re-indexes this document: its passages are replaced." : "The text is split into passages and indexed for search."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="doc-name">Name</Label>
            <Input id="doc-name" value={source} onChange={(e) => setSource(e.target.value)} placeholder="notes.md" maxLength={200} autoFocus />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="doc-text">Content</Label>
            <Textarea
              id="doc-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={12}
              className="font-mono text-[13px]"
              placeholder="Paste or write the document text (Markdown supported)…"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy || !source.trim() || !text.trim()}>
              {initial ? "Save changes" : "Add document"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
