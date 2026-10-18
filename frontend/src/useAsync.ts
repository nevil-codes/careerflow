import { useCallback, useEffect, useState } from "react";

export type Async<T> =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: T };

/** Runs `load` on mount and whenever `deps` change; `reload()` refetches. */
export function useAsync<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<Async<T>>({ kind: "loading" });
  const run = useCallback(load, deps);

  const reload = useCallback(() => {
    run()
      .then((data) => setState({ kind: "ready", data }))
      .catch((err: Error) => setState({ kind: "error", message: err.message }));
  }, [run]);

  useEffect(reload, [reload]);
  return [state, reload] as const;
}
