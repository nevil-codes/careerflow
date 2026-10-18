import type { ProfileItem } from "../types";
import StatusBadge from "./StatusBadge";

export default function ItemCard({ item }: { item: ProfileItem }) {
  const subtitle = [item.organization, item.period].filter(Boolean).join(" · ");

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">
            {item.link ? (
              <a href={item.link} target="_blank" rel="noreferrer" className="hover:underline">
                {item.title}
              </a>
            ) : (
              item.title
            )}
          </h3>
          {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
        {item.status && <StatusBadge status={item.status} />}
      </div>

      {item.description && (
        <p className="mt-2 whitespace-pre-line text-sm text-slate-700 dark:text-slate-300">{item.description}</p>
      )}

      {item.metrics.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-slate-700 dark:text-slate-300">
          {item.metrics.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}

      {item.stack.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {item.stack.map((s) => (
            <li
              key={s}
              className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
