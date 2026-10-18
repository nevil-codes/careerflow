import { useState } from "react";

import { deleteProvider, listProviderModels, testProvider, updateProvider } from "../api";
import type { ProviderConfig, ProviderTestResult } from "../types";
import { useAsync } from "../useAsync";
import { Button, Card, ErrorBox, Label, inputClass } from "./ui";

export default function ProviderCard({ config, onChange }: { config: ProviderConfig; onChange: () => void }) {
  const [models, reloadModels] = useAsync(() => listProviderModels(config.id), [config.id, config.base_url]);
  const [baseUrl, setBaseUrl] = useState(config.base_url ?? "");
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ProviderTestResult | null>(null);
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

  async function test() {
    setTesting(true);
    setResult(null);
    try {
      setResult(await testProvider(config.id));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setTesting(false);
    }
  }

  const modelOptions = models.kind === "ready" ? models.data : [];
  const modelMissing = config.model !== null && models.kind === "ready" && !modelOptions.includes(config.model);

  return (
    <Card className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{config.name}</h3>
          <p className="text-xs text-slate-500">Ollama</p>
        </div>
        {config.enabled ? (
          <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-emerald-300 ring-inset dark:bg-emerald-900/40 dark:text-emerald-200 dark:ring-emerald-700">
            Active
          </span>
        ) : (
          <Button onClick={() => run(updateProvider(config.id, { enabled: true }))}>Make active</Button>
        )}
      </div>

      {error && <ErrorBox message={error} />}

      <div className="grid gap-3 sm:grid-cols-2">
        <Label text="Server URL">
          <input
            className={inputClass}
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            onBlur={() => baseUrl !== config.base_url && run(updateProvider(config.id, { base_url: baseUrl }))}
          />
        </Label>
        <Label text="Model">
          {models.kind === "ready" ? (
            <select
              className={inputClass}
              value={config.model ?? ""}
              onChange={(e) => run(updateProvider(config.id, { model: e.target.value || null }))}
            >
              <option value="">Choose a model…</option>
              {modelMissing && <option value={config.model!}>{config.model} (not installed)</option>}
              {modelOptions.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          ) : (
            <input
              className={inputClass}
              value={config.model ?? ""}
              disabled
              placeholder={models.kind === "loading" ? "Loading models…" : "Models unavailable"}
            />
          )}
        </Label>
      </div>

      {models.kind === "error" && (
        <div className="flex items-start justify-between gap-3 text-sm text-amber-700 dark:text-amber-300">
          <span>{models.message}</span>
          <Button onClick={reloadModels}>Retry</Button>
        </div>
      )}
      {models.kind === "ready" && modelOptions.length === 0 && (
        <p className="text-sm text-amber-700 dark:text-amber-300">
          No models installed. Pull one, e.g. <code>ollama pull qwen3:8b</code>, then reload.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="primary" onClick={test} disabled={testing || !config.model}>
          {testing ? "Testing…" : "Test provider"}
        </Button>
        {testing && <span className="text-xs text-slate-500">Local models can take a minute to load the first time.</span>}
        <Button
          variant="danger"
          className="ml-auto"
          onClick={() => confirm(`Delete provider "${config.name}"?`) && run(deleteProvider(config.id))}
        >
          Delete
        </Button>
      </div>

      {result && <TestResult result={result} />}
    </Card>
  );
}

function TestResult({ result }: { result: ProviderTestResult }) {
  const seconds = (result.latency_ms / 1000).toFixed(1);
  if (!result.ok) {
    return <ErrorBox message={`Test failed after ${seconds}s: ${result.error}`} />;
  }
  return (
    <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100">
      <p className="font-medium">
        Working. Valid structured reply from {result.model} in {seconds}s
        {result.attempts > 1 && ` (after ${result.attempts} attempts)`}.
      </p>
      <p className="mt-1">
        “{result.answer?.greeting}” · 17 + 25 = {result.answer?.sum}{" "}
        {result.correct ? "✓" : "(wrong, so this model may be unreliable for extraction)"}
      </p>
    </div>
  );
}
