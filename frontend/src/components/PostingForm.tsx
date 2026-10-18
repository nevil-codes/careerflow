import { useState, type FormEvent } from "react";

import type { PostingInput } from "../types";
import { Button, ErrorBox, Label, inputClass } from "./ui";

const EMPTY: PostingInput = { title: "", company: "", location: "", url: "", language: "", description: "" };

export default function PostingForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial?: PostingInput;
  submitLabel: string;
  onSubmit: (data: PostingInput) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<PostingInput>({ ...EMPTY, ...initial });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const set = (key: keyof PostingInput) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form);
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {error && <ErrorBox message={error} />}
      <div className="grid gap-3 sm:grid-cols-2">
        <Label text="Job title *">
          <input className={inputClass} value={form.title} onChange={set("title")} required />
        </Label>
        <Label text="Company *">
          <input className={inputClass} value={form.company} onChange={set("company")} required />
        </Label>
        <Label text="Location">
          <input className={inputClass} value={form.location ?? ""} onChange={set("location")} />
        </Label>
        <Label text="Posting language">
          <input
            className={inputClass}
            value={form.language ?? ""}
            onChange={set("language")}
            placeholder="e.g. English, German"
          />
        </Label>
      </div>
      <Label text="URL">
        <input className={inputClass} value={form.url ?? ""} onChange={set("url")} placeholder="https://…" />
      </Label>
      <Label text="Job description (paste the full text)">
        <textarea
          className={`${inputClass} min-h-48 font-mono text-xs`}
          value={form.description ?? ""}
          onChange={set("description")}
        />
      </Label>
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={saving}>
          {saving ? "Saving…" : submitLabel}
        </Button>
        <Button onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}
