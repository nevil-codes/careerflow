import { useEffect, useState } from "react";

// Minimal hash router: "#/postings/3" -> "/postings/3". Avoids a routing dependency.
const current = () => window.location.hash.replace(/^#/, "") || "/postings";

export function useRoute(): string {
  const [route, setRoute] = useState(current);
  useEffect(() => {
    const onChange = () => setRoute(current());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export const href = (path: string) => `#${path}`;
export const navigate = (path: string) => {
  window.location.hash = path;
};
