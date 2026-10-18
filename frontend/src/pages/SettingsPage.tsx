import { useState, type FormEvent } from "react";

import { createProvider, getProviderDefaults, listProviders } from "../api";
import ProviderCard from "../components/ProviderCard";
import { Button, Card, ErrorBox, Label, SectionTitle, inputClass } from "../components/ui";
import { PROVIDER_LABELS, type ProviderKind } from "../types";
import { useAsync } from "../useAsync";

export default function SettingsPage() {
  const [state, reload] = useAsync(() => Promise.all([listProviders(), getProviderDefaults()]));

  if (state.kind === "loading") return <p className="text-slate-500">Loading…</p>;
  if (state.kind === "error") return <ErrorBox message={state.message} />;
  const [providers, defaults] = state.data;

  return (
    <>
      <h1 className="mb-6 text-2xl font-bold">Settings</h1>
      <SectionTitle>LLM provider</SectionTitle>
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
        Use a local model through Ollama (free, private, slower) or Claude through the Anthropic API (fast, paid per
        request). The active provider is used by every AI feature. It can read your profile but never change it.
      </p>
      <div className="space-y-4">
        {providers.map((p) => (
          <ProviderCard key={p.id} config={p} onChange={reload} />
        ))}
        <AddProvider
          defaultUrls={defaults.base_urls}
          firstOne={providers.length === 0}
          onAdded={reload}
        />
      </div>
    </>
  );
}

const DEFAULT_NAMES: Record<ProviderKind, string> = { ollama: "Local Ollama", anthropic: "Claude" };

function AddProvider({
  defaultUrls,
  firstOne,
  onAdded,
}: {
  defaultUrls: Record<ProviderKind, string | null>;
  firstOne: boolean;
  onAdded: () => void;
}) {
  const [open, setOpen] = useState(firstOne);
  const [kind, setKind] = useState<ProviderKind>("ollama");
  const [name, setName] = useState(DEFAULT_NAMES.ollama);
  const [baseUrl, setBaseUrl] = useState(defaultUrls.ollama ?? "");

  function chooseKind(next: ProviderKind) {
    if (name === "" || name === DEFAULT_NAMES[kind]) setName(DEFAULT_NAMES[next]);
    setKind(next);
    setBaseUrl(defaultUrls[next] ?? "");
  }
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createProvider({
        name,
        provider: kind,
        base_url: kind === "ollama" ? baseUrl : null,
        enabled: firstOne,
      });
      setOpen(false);
      setName("");
      onAdded();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!open) return <Button onClick={() => setOpen(true)}>Add provider</Button>;
  return (
    <Card>
      <form onSubmit={submit} className="space-y-3">
        <h3 className="font-semibold">Add provider</h3>
        {error && <ErrorBox message={error} />}
        <div className="grid gap-3 sm:grid-cols-2">
          <Label text="Type">
            <select className={inputClass} value={kind} onChange={(e) => chooseKind(e.target.value as ProviderKind)}>
              {(Object.keys(PROVIDER_LABELS) as ProviderKind[]).map((k) => (
                <option key={k} value={k}>
                  {PROVIDER_LABELS[k]}
                </option>
              ))}
            </select>
          </Label>
          <Label text="Name">
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
          </Label>
          {kind === "ollama" && (
            <Label text="Server URL">
              <input className={inputClass} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required />
            </Label>
          )}
        </div>
        {kind === "anthropic" && (
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Needs <code>ANTHROPIC_API_KEY</code> set in the terminal that runs the backend. Create a key at
            console.anthropic.com. It is never stored in CareerFlow.
          </p>
        )}
        <div className="flex gap-2">
          <Button type="submit" variant="primary">
            Add
          </Button>
          {!firstOne && <Button onClick={() => setOpen(false)}>Cancel</Button>}
        </div>
      </form>
    </Card>
  );
}
