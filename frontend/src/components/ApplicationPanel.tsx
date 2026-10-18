import { useEffect, useState } from "react";

import { deleteApplication, getApplication, updateApplication } from "../api";
import { formatDate, formatDateTime } from "../format";
import { APPLICATION_STATUSES, type ApplicationStatus } from "../types";
import { useAsync } from "../useAsync";
import TaskList from "./TaskList";
import { AppStatusBadge, Button, Card, ErrorBox, Label, inputClass, statusLabel } from "./ui";

export default function ApplicationPanel({
  applicationId,
  onChange,
}: {
  applicationId: number;
  onChange: () => void;
}) {
  const [state, reload] = useAsync(() => getApplication(applicationId), [applicationId]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (state.kind === "ready") setNotes(state.data.notes ?? "");
  }, [state]);

  if (state.kind === "loading") return <p className="text-slate-500">Loading…</p>;
  if (state.kind === "error") return <ErrorBox message={state.message} />;
  const app = state.data;

  async function save(data: Parameters<typeof updateApplication>[1]) {
    setError(null);
    try {
      await updateApplication(app.id, data);
      reload();
      onChange();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function stopTracking() {
    if (!confirm("Delete this application, its history and its tasks? The posting is kept.")) return;
    try {
      await deleteApplication(app.id);
      onChange();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        {error && <ErrorBox message={error} />}
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Application</h2>
          <AppStatusBadge status={app.status} />
        </div>
        <Label text="Status">
          <select
            className={inputClass}
            value={app.status}
            onChange={(e) => save({ status: e.target.value as ApplicationStatus })}
          >
            {APPLICATION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </Label>
        {app.applied_at && <p className="text-xs text-slate-500">Applied {formatDate(app.applied_at)}</p>}
        <Label text="Notes">
          <textarea
            className={`${inputClass} min-h-20`}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={() => notes !== (app.notes ?? "") && save({ notes: notes || null })}
          />
        </Label>
        <div>
          <h3 className="mb-1 text-xs font-medium text-slate-600 dark:text-slate-400">History</h3>
          <ol className="space-y-0.5 text-xs text-slate-500">
            {app.events.map((e) => (
              <li key={e.id}>
                {formatDateTime(e.created_at)}:{" "}
                {e.from_status ? `${statusLabel(e.from_status)} → ` : "Created as "}
                {statusLabel(e.to_status)}
              </li>
            ))}
          </ol>
        </div>
        <Button variant="danger" className="-ml-3" onClick={stopTracking}>
          Delete application
        </Button>
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Tasks</h2>
        <TaskList tasks={app.tasks} applicationId={app.id} onChange={reload} />
      </Card>
    </div>
  );
}
