import { useEffect, useState } from "react";

import { getProfile, getProfileItems } from "../api";
import ItemCard from "../components/ItemCard";
import { ErrorBox } from "../components/ui";
import type { ItemType, Profile, ProfileItem } from "../types";

const SECTIONS: { type: ItemType; title: string }[] = [
  { type: "education", title: "Education" },
  { type: "job", title: "Experience" },
  { type: "project", title: "Projects" },
  { type: "course", title: "Courses" },
];

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; profile: Profile; items: ProfileItem[] };

export default function ProfilePage() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    Promise.all([getProfile(), getProfileItems()])
      .then(([profile, items]) => setState({ kind: "ready", profile, items }))
      .catch((err: Error) => setState({ kind: "error", message: err.message }));
  }, []);

  return (
    <>
      {state.kind === "loading" && <p className="text-slate-500">Loading profile…</p>}
      {state.kind === "error" && <ErrorBox message={`Could not load profile: ${state.message}`} />}
      {state.kind === "ready" && <ProfileView profile={state.profile} items={state.items} />}
    </>
  );
}

function ProfileView({ profile, items }: { profile: Profile; items: ProfileItem[] }) {
  const skills = items.filter((i) => i.type === "skill");
  const contact = [profile.location, profile.email].filter(Boolean).join(" · ");

  return (
    <>
      <header className="mb-8">
        <h1 className="text-3xl font-bold">{profile.full_name}</h1>
        {profile.headline && <p className="mt-1 text-lg text-slate-600 dark:text-slate-400">{profile.headline}</p>}
        {contact && <p className="mt-1 text-sm text-slate-500">{contact}</p>}
        <p className="mt-3 inline-flex items-center gap-2 rounded-md bg-indigo-50 px-3 py-1 text-sm text-indigo-900 ring-1 ring-indigo-200 dark:bg-indigo-950 dark:text-indigo-200 dark:ring-indigo-800">
          <span className="font-medium">German:</span> {profile.german_level}
          <span className="text-xs text-indigo-500" title="Locked to candidate_context.md">
            (from file)
          </span>
        </p>
      </header>

      {SECTIONS.map(({ type, title }) => {
        const sectionItems = items.filter((i) => i.type === type);
        if (sectionItems.length === 0) return null;
        return (
          <section key={type} className="mb-8">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
            <ul className="space-y-3">
              {sectionItems.map((item) => (
                <ItemCard key={item.id} item={item} />
              ))}
            </ul>
          </section>
        );
      })}

      {skills.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Skills</h2>
          <ul className="flex flex-wrap gap-2">
            {skills.map((s) => (
              <li
                key={s.id}
                className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm dark:border-slate-800 dark:bg-slate-900"
              >
                {s.title}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
