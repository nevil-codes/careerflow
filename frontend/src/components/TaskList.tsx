import { useState, type FormEvent, type ReactNode } from "react";

import { createTask, deleteTask, updateTask } from "../api";
import { dateInputToIso, formatDate } from "../format";
import type { Task } from "../types";
import { Button, ErrorBox, inputClass } from "./ui";

const isOverdue = (t: Task) => t.status !== "done" && t.due_at !== null && new Date(t.due_at) < new Date();

export default function TaskList({
  tasks,
  applicationId,
  onChange,
  renderContext,
}: {
  tasks: Task[];
  applicationId?: number;
  onChange: () => void;
  renderContext?: (task: Task) => ReactNode;
}) {
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function run(action: Promise<unknown>) {
    setError(null);
    try {
      await action;
      onChange();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function add(e: FormEvent) {
    e.preventDefault();
    await run(createTask({ title, due_at: dateInputToIso(due), application_id: applicationId ?? null }));
    setTitle("");
    setDue("");
  }

  return (
    <div className="space-y-2">
      {error && <ErrorBox message={error} />}
      {tasks.length === 0 && <p className="text-sm text-slate-500">No tasks.</p>}
      <ul className="space-y-1">
        {tasks.map((t) => (
          <li key={t.id} className="group flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={t.status === "done"}
              onChange={() => run(updateTask(t.id, { status: t.status === "done" ? "todo" : "done" }))}
              aria-label={`Mark "${t.title}" ${t.status === "done" ? "not done" : "done"}`}
            />
            <div className="min-w-0 flex-1">
              <span className={t.status === "done" ? "text-slate-400 line-through" : ""}>{t.title}</span>
              {t.due_at && (
                <span className={`ml-2 text-xs ${isOverdue(t) ? "font-medium text-red-600" : "text-slate-500"}`}>
                  {isOverdue(t) ? "overdue · " : "due "}
                  {formatDate(t.due_at)}
                </span>
              )}
              {renderContext?.(t)}
            </div>
            <button
              type="button"
              className="text-xs text-slate-400 opacity-0 hover:text-red-600 group-hover:opacity-100"
              onClick={() => run(deleteTask(t.id))}
              aria-label={`Delete "${t.title}"`}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap gap-2 pt-1">
        <input
          className={`${inputClass} min-w-32 flex-1`}
          placeholder="Add a task…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <input
          type="date"
          className={`${inputClass} w-auto!`}
          value={due}
          onChange={(e) => setDue(e.target.value)}
          aria-label="Due date"
        />
        <Button type="submit">Add</Button>
      </form>
    </div>
  );
}
