import { useState } from "react";

import { createApplication, deletePosting, getPosting, updatePosting } from "../api";
import ApplicationPanel from "../components/ApplicationPanel";
import PostingForm from "../components/PostingForm";
import { Button, Card, ErrorBox } from "../components/ui";
import { formatDate } from "../format";
import { href, navigate } from "../router";
import { useAsync } from "../useAsync";

export default function PostingDetailPage({ id }: { id: number }) {
  const [state, reload] = useAsync(() => getPosting(id), [id]);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (state.kind === "loading") return <p className="text-slate-500">Loading…</p>;
  if (state.kind === "error") return <ErrorBox message={state.message} />;
  const posting = state.data;

  async function remove() {
    const extra = posting.application_id ? " Its application, history and tasks will be deleted too." : "";
    if (!confirm(`Delete "${posting.title}"?${extra}`)) return;
    try {
      await deletePosting(posting.id);
      navigate("/postings");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function track() {
    try {
      await createApplication(posting.id);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <>
      <a href={href("/postings")} className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
        ← Postings
      </a>
      {error && (
        <div className="mt-3">
          <ErrorBox message={error} />
        </div>
      )}

      {editing ? (
        <Card className="mt-4">
          <PostingForm
            initial={posting}
            submitLabel="Save changes"
            onSubmit={async (data) => {
              await updatePosting(posting.id, data);
              setEditing(false);
              reload();
            }}
            onCancel={() => setEditing(false)}
          />
        </Card>
      ) : (
        <header className="mt-3 mb-6 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold">{posting.title}</h1>
            <p className="text-slate-600 dark:text-slate-400">
              {[posting.company, posting.location, posting.language].filter(Boolean).join(" · ")}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Added {formatDate(posting.created_at)}
              {posting.url && (
                <>
                  {" · "}
                  <a href={posting.url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline dark:text-indigo-400">
                    Original posting ↗
                  </a>
                </>
              )}
            </p>
          </div>
          <div className="flex shrink-0 gap-1">
            <Button onClick={() => setEditing(true)}>Edit</Button>
            <Button variant="danger" onClick={remove}>
              Delete
            </Button>
          </div>
        </header>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <Card>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Job description</h2>
          {posting.description ? (
            <pre className="whitespace-pre-wrap break-words font-sans text-sm text-slate-700 dark:text-slate-300">
              {posting.description}
            </pre>
          ) : (
            <p className="text-sm text-slate-500">No description pasted.</p>
          )}
        </Card>

        <div>
          {posting.application_id ? (
            <ApplicationPanel applicationId={posting.application_id} onChange={reload} />
          ) : (
            <Card>
              <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">Not tracked yet.</p>
              <Button variant="primary" onClick={track}>
                Start application
              </Button>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
