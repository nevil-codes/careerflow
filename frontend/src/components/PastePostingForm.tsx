import { useState, type FormEvent } from "react";

import { createPosting, createPostingFromText } from "../api";
import { href, navigate } from "../router";
import PostingForm from "./PostingForm";
import { Button, ErrorBox, inputClass } from "./ui";

/** Paste the job description; the active LLM fills in title, company, etc. */
export default function PastePostingForm({ onCancel }: { onCancel: () => void }) {
  const [text, setText] = useState("");
  const [reading, setReading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manual, setManual] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setReading(true);
    setError(null);
    try {
      const posting = await createPostingFromText(text);
      navigate(`/postings/${posting.id}`);
    } catch (err) {
      setError((err as Error).message);
      setReading(false);
    }
  }

  if (manual) {
    return (
      <PostingForm
        initial={{ title: "", company: "", description: text }}
        submitLabel="Save posting"
        onSubmit={async (data) => {
          const posting = await createPosting(data);
          navigate(`/postings/${posting.id}`);
        }}
        onCancel={onCancel}
      />
    );
  }

  const noProvider = error?.includes("No LLM provider");
  return (
    <form onSubmit={submit} className="space-y-3">
      <label className="block">
        <span className="mb-1 block text-sm font-medium">Paste the full job description</span>
        <textarea
          className={`${inputClass} min-h-64 font-mono text-xs`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Copy everything from the job page: title, company, location, requirements…"
          disabled={reading}
          required
          autoFocus
        />
      </label>
      {error && (
        <ErrorBox
          message={
            noProvider ? "No AI model is set up yet, so the details can't be filled in automatically." : error
          }
        />
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" variant="primary" disabled={reading || text.trim().length === 0}>
          {reading ? "Reading posting…" : "Add posting"}
        </Button>
        {!reading && <Button onClick={onCancel}>Cancel</Button>}
        {reading && (
          <span className="text-xs text-slate-500">
            The local model is filling in title, company and location. This can take up to a minute.
          </span>
        )}
        {error && !reading && (
          <>
            {noProvider && (
              <a href={href("/settings")} className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
                Set up a model
              </a>
            )}
            <button
              type="button"
              className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
              onClick={() => setManual(true)}
            >
              Enter details manually instead
            </button>
          </>
        )}
      </div>
    </form>
  );
}
