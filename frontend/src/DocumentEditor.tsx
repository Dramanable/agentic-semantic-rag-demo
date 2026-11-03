import { FormEvent, useState } from "react";

interface Props {
  /** Present when editing an existing document, absent when creating one. */
  initial?: { source: string; text: string };
  busy: boolean;
  onSave: (source: string, text: string) => void;
  onCancel: () => void;
}

export function DocumentEditor({ initial, busy, onSave, onCancel }: Props) {
  const [source, setSource] = useState(initial?.source ?? "");
  const [text, setText] = useState(initial?.text ?? "");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSave(source.trim(), text);
  };

  return (
    <form className="editor" onSubmit={submit}>
      <label>
        Name
        <input value={source} onChange={(e) => setSource(e.target.value)} placeholder="notes.md" maxLength={200} />
      </label>
      <label>
        Content
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} placeholder="Paste or write the document text…" />
      </label>
      <div className="row">
        <button type="submit" disabled={busy || !source.trim() || !text.trim()}>
          {initial ? "Save changes" : "Add document"}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
