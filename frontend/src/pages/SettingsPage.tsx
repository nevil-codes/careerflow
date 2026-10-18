import { useState, type FormEvent } from "react";

import { createProvider, getProviderDefaults, listProviders } from "../api";
import ProviderCard from "../components/ProviderCard";
import { Button, Card, ErrorBox, Label, SectionTitle, inputClass } from "../components/ui";
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
        CareerFlow runs models locally through Ollama. The active provider is used by every AI feature. It can read
        your profile but never change it.
      </p>
      <div className="space-y-4">
        {providers.map((p) => (
          <ProviderCard key={p.id} config={p} onChange={reload} />
        ))}
        <AddProvider
          defaultUrl={defaults.base_urls.ollama}
          firstOne={providers.length === 0}
          onAdded={reload}
        />
      </div>
    </>
  );
}

function AddProvider({ defaultUrl, firstOne, onAdded }: { defaultUrl: string; firstOne: boolean; onAdded: () => void }) {
  const [open, setOpen] = useState(firstOne);
  const [name, setName] = useState(firstOne ? "Local Ollama" : "");
  const [baseUrl, setBaseUrl] = useState(defaultUrl);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createProvider({ name, base_url: baseUrl, enabled: firstOne });
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
        <h3 className="font-semibold">Add Ollama provider</h3>
        {error && <ErrorBox message={error} />}
        <div className="grid gap-3 sm:grid-cols-2">
          <Label text="Name">
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
          </Label>
          <Label text="Server URL">
            <input className={inputClass} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required />
          </Label>
        </div>
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
