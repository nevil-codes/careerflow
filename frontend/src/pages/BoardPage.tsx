import { useState } from "react";

import { listApplications, updateApplication } from "../api";
import { ErrorBox, inputClass, statusLabel } from "../components/ui";
import { formatDate } from "../format";
import { href } from "../router";
import { APPLICATION_STATUSES, type ApplicationStatus } from "../types";
import { useAsync } from "../useAsync";

export default function BoardPage() {
  const [state, reload] = useAsync(listApplications);
  const [error, setError] = useState<string | null>(null);

  async function move(id: number, status: ApplicationStatus) {
    setError(null);
    try {
      await updateApplication(id, { status });
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (state.kind === "loading") return <p className="text-slate-500">Loading…</p>;
  if (state.kind === "error") return <ErrorBox message={state.message} />;

  return (
    <>
      <h1 className="mb-6 text-2xl font-bold">Applications</h1>
      {error && (
        <div className="mb-4">
          <ErrorBox message={error} />
        </div>
      )}
      {state.data.length === 0 && (
        <p className="text-slate-500">
          No applications yet. Open a <a className="text-indigo-600 hover:underline" href={href("/postings")}>posting</a>{" "}
          and click "Start application".
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {APPLICATION_STATUSES.map((status) => {
          const apps = state.data.filter((a) => a.status === status);
          return (
            <section key={status} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-900/60">
              <h2 className="mb-2 flex justify-between text-xs font-semibold uppercase tracking-wide text-slate-500">
                {statusLabel(status)} <span>{apps.length}</span>
              </h2>
              <ul className="space-y-2">
                {apps.map((a) => (
                  <li
                    key={a.id}
                    className="rounded-md border border-slate-200 bg-white p-3 text-sm dark:border-slate-800 dark:bg-slate-900"
                  >
                    <a href={href(`/postings/${a.posting.id}`)} className="font-medium hover:underline">
                      {a.posting.title}
                    </a>
                    <p className="text-xs text-slate-500">{a.posting.company}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {a.applied_at ? `Applied ${formatDate(a.applied_at)}` : `Created ${formatDate(a.created_at)}`}
                      {a.open_tasks > 0 && ` · ${a.open_tasks} open task${a.open_tasks > 1 ? "s" : ""}`}
                    </p>
                    <select
                      className={`${inputClass} mt-2 py-1 text-xs`}
                      value={a.status}
                      onChange={(e) => move(a.id, e.target.value as ApplicationStatus)}
                      aria-label={`Move ${a.posting.title}`}
                    >
                      {APPLICATION_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {statusLabel(s)}
                        </option>
                      ))}
                    </select>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </>
  );
}
