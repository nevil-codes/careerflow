import type {
  Application,
  ApplicationDetail,
  ApplicationStatus,
  Posting,
  PostingInput,
  Profile,
  ProfileItem,
  Task,
  TaskStatus,
} from "./types";

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const detail = data?.detail;
    // FastAPI validation errors are a list of {loc, msg}.
    const message = Array.isArray(detail)
      ? detail.map((d: { loc: string[]; msg: string }) => `${d.loc.at(-1)}: ${d.msg}`).join("; ")
      : detail;
    throw new Error(message ?? `${res.status} ${res.statusText}`);
  }
  return (res.status === 204 ? undefined : res.json()) as Promise<T>;
}

const qs = (params: Record<string, string | number | boolean | undefined>) => {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined) as [string, string][];
  return entries.length ? `?${new URLSearchParams(entries)}` : "";
};

export const getProfile = () => request<Profile>("GET", "/profile");
export const getProfileItems = () => request<ProfileItem[]>("GET", "/profile/items");

export const listPostings = (q?: string) => request<Posting[]>("GET", `/postings${qs({ q: q || undefined })}`);
export const getPosting = (id: number) => request<Posting>("GET", `/postings/${id}`);
export const createPosting = (data: PostingInput) => request<Posting>("POST", "/postings", data);
export const updatePosting = (id: number, data: Partial<PostingInput>) =>
  request<Posting>("PATCH", `/postings/${id}`, data);
export const deletePosting = (id: number) => request<void>("DELETE", `/postings/${id}`);

export const listApplications = () => request<Application[]>("GET", "/applications");
export const getApplication = (id: number) => request<ApplicationDetail>("GET", `/applications/${id}`);
export const createApplication = (posting_id: number) =>
  request<ApplicationDetail>("POST", "/applications", { posting_id });
export const updateApplication = (
  id: number,
  data: { status?: ApplicationStatus; notes?: string | null; applied_at?: string | null },
) => request<ApplicationDetail>("PATCH", `/applications/${id}`, data);
export const deleteApplication = (id: number) => request<void>("DELETE", `/applications/${id}`);

export const listTasks = (params: { application_id?: number; open?: boolean } = {}) =>
  request<Task[]>("GET", `/tasks${qs(params)}`);
export const createTask = (data: { title: string; due_at?: string | null; application_id?: number | null }) =>
  request<Task>("POST", "/tasks", data);
export const updateTask = (id: number, data: { title?: string; status?: TaskStatus; due_at?: string | null }) =>
  request<Task>("PATCH", `/tasks/${id}`, data);
export const deleteTask = (id: number) => request<void>("DELETE", `/tasks/${id}`);
