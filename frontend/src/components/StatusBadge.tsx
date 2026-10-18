import type { ItemStatus } from "../types";

const STYLES: Record<ItemStatus, string> = {
  "in-progress": "bg-amber-100 text-amber-800 ring-amber-300 dark:bg-amber-900/40 dark:text-amber-200 dark:ring-amber-700",
  completed: "bg-emerald-100 text-emerald-800 ring-emerald-300 dark:bg-emerald-900/40 dark:text-emerald-200 dark:ring-emerald-700",
  planned: "bg-sky-100 text-sky-800 ring-sky-300 dark:bg-sky-900/40 dark:text-sky-200 dark:ring-sky-700",
  paused: "bg-slate-100 text-slate-700 ring-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-600",
};

const LABELS: Record<ItemStatus, string> = {
  "in-progress": "In progress",
  completed: "Completed",
  planned: "Planned",
  paused: "Paused",
};

export default function StatusBadge({ status }: { status: ItemStatus }) {
  return (
    <span
      data-status={status}
      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
