import type { Profile, ProfileItem } from "./types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const getProfile = () => get<Profile>("/profile");
export const getProfileItems = () => get<ProfileItem[]>("/profile/items");
