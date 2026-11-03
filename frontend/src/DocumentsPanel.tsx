import { useState } from "react";
import { DocumentEditor } from "./DocumentEditor";
import { DocumentInfo, api } from "./api";

interface Props {
  documents: DocumentInfo[];
  busy: boolean;
  /** Runs an action with the shared busy/error handling, then refreshes the lists. */
  run: (action: () => Promise<unknown>) => Promise<void>;
}

type Editing = { mode: "create" } | { mode: "edit"; id: string; source: string; text: string };

export function DocumentsPanel({ documents, busy, run }: Props) {
  const [editing, setEditing] = useState<Editing | null>(null);

  const startEdit = (id: string) =>
    run(async () => {
      const doc = await api.document(id);
      setEditing({ mode: "edit", id, source: doc.source, text: doc.text });
    });

  const save = (source: string, text: string) =>
    run(async () => {
      if (editing?.mode === "edit") await api.update(editing.id, source, text);
      else await api.create(source, text);
      setEditing(null);
    });

  const upload = (files: FileList | null) =>
    run(async () => {
      for (const file of Array.from(files ?? [])) await api.upload(file);
    });

  const remove = (doc: DocumentInfo) => {
    if (window.confirm(`Delete "${doc.source}"? Its passages are removed from the vector store too.`)) {
      void run(() => api.remove(doc.id));
    }
  };

  return (
    <section>
      <h2>Documents</h2>
      <div className="row">
        <button onClick={() => setEditing({ mode: "create" })} disabled={busy}>
          New document
        </button>
        <label className="button secondary">
          Upload files (.txt, .md)
          <input type="file" accept=".txt,.md,text/plain,text/markdown" multiple hidden onChange={(e) => void upload(e.target.files)} />
        </label>
      </div>

      {editing && (
        <DocumentEditor
          key={editing.mode === "edit" ? editing.id : "new"}
          initial={editing.mode === "edit" ? { source: editing.source, text: editing.text } : undefined}
          busy={busy}
          onSave={(source, text) => void save(source, text)}
          onCancel={() => setEditing(null)}
        />
      )}

      {documents.length === 0 ? (
        <p className="muted">No documents yet: add one to start asking questions.</p>
      ) : (
        <ul className="documents">
          {documents.map((d) => (
            <li key={d.id}>
              <span className="name">{d.source}</span>
              <span className="muted">
                {d.chunks} passage{d.chunks === 1 ? "" : "s"} · {d.characters.toLocaleString("en-US")} characters
              </span>
              <span className="actions">
                <button className="link" disabled={busy} onClick={() => void startEdit(d.id)}>
                  Edit
                </button>
                <button className="link danger" disabled={busy} onClick={() => remove(d)}>
                  Delete
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
