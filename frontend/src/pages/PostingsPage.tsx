import { useState } from "react";

import { createPosting, listPostings } from "../api";
import PostingForm from "../components/PostingForm";
import { AppStatusBadge, Button, Card, ErrorBox, inputClass } from "../components/ui";
import { formatDate } from "../format";
import { href, navigate } from "../router";
import { useAsync } from "../useAsync";

export default function PostingsPage() {
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [state] = useAsync(() => listPostings(query), [query]);

  return (
    <>
      <div className="mb-6 flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Postings</h1>
        {!adding && (
          <Button variant="primary" onClick={() => setAdding(true)}>
            New posting
          </Button>
        )}
      </div>

      {adding && (
        <Card className="mb-6">
          <PostingForm
            submitLabel="Save posting"
            onSubmit={async (data) => {
              const posting = await createPosting(data);
              navigate(`/postings/${posting.id}`);
            }}
            onCancel={() => setAdding(false)}
          />
        </Card>
      )}

      <input
        className={`${inputClass} mb-4`}
        placeholder="Search title or company…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {state.kind === "loading" && <p className="text-slate-500">Loading…</p>}
      {state.kind === "error" && <ErrorBox message={state.message} />}
      {state.kind === "ready" && state.data.length === 0 && (
        <p className="text-slate-500">{query ? "No matches." : "No postings yet. Paste your first one."}</p>
      )}
      {state.kind === "ready" && (
        <ul className="space-y-2">
          {state.data.map((p) => (
            <li key={p.id}>
              <a
                href={href(`/postings/${p.id}`)}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4 hover:border-indigo-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-indigo-700"
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold">{p.title}</p>
                  <p className="truncate text-sm text-slate-500">
                    {[p.company, p.location].filter(Boolean).join(" · ")} · added {formatDate(p.created_at)}
                  </p>
                </div>
                {p.application_status ? (
                  <AppStatusBadge status={p.application_status} />
                ) : (
                  <span className="shrink-0 text-xs text-slate-400">Not tracked</span>
                )}
              </a>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
