import { useState } from "react";

import { listApplications, listTasks } from "../api";
import TaskList from "../components/TaskList";
import { Card, ErrorBox } from "../components/ui";
import { href } from "../router";
import { useAsync } from "../useAsync";

export default function TasksPage() {
  const [showDone, setShowDone] = useState(false);
  const [state, reload] = useAsync(
    () => Promise.all([listTasks({ open: !showDone || undefined }), listApplications()]),
    [showDone],
  );

  if (state.kind === "loading") return <p className="text-slate-500">Loading…</p>;
  if (state.kind === "error") return <ErrorBox message={state.message} />;
  const [tasks, applications] = state.data;
  const appById = new Map(applications.map((a) => [a.id, a]));

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          <input type="checkbox" checked={showDone} onChange={(e) => setShowDone(e.target.checked)} />
          Show done
        </label>
      </div>
      <Card>
        <TaskList
          tasks={tasks}
          onChange={reload}
          renderContext={(t) => {
            const app = t.application_id ? appById.get(t.application_id) : undefined;
            return (
              app && (
                <a
                  href={href(`/postings/${app.posting.id}`)}
                  className="block text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  {app.posting.title} · {app.posting.company}
                </a>
              )
            );
          }}
        />
      </Card>
    </>
  );
}
