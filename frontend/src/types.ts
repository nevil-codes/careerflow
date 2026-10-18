// Mirrors the Read/Create/Update schemas in backend/app/models.py.

export type ItemType = "education" | "job" | "project" | "course" | "skill";
export type ItemStatus = "completed" | "in-progress" | "planned" | "paused";
export type ApplicationStatus = "draft" | "applied" | "interviewing" | "offer" | "rejected" | "withdrawn";
export type TaskStatus = "todo" | "doing" | "done";

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  "draft",
  "applied",
  "interviewing",
  "offer",
  "rejected",
  "withdrawn",
];

export interface Profile {
  id: number;
  full_name: string;
  headline: string | null;
  email: string | null;
  location: string | null;
  german_level: string;
}

export interface ProfileItem {
  id: number;
  type: ItemType;
  title: string;
  organization: string | null;
  period: string | null;
  status: ItemStatus | null;
  description: string | null;
  stack: string[];
  metrics: string[];
  link: string | null;
  position: number;
}

export interface PostingInput {
  title: string;
  company: string;
  location?: string | null;
  url?: string | null;
  source?: string | null;
  language?: string | null;
  description?: string | null;
}

export interface Posting extends PostingInput {
  id: number;
  created_at: string;
  updated_at: string;
  application_id: number | null;
  application_status: ApplicationStatus | null;
}

export interface ApplicationEvent {
  id: number;
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus;
  created_at: string;
}

export interface Task {
  id: number;
  title: string;
  status: TaskStatus;
  due_at: string | null;
  application_id: number | null;
  created_at: string;
}

export interface Application {
  id: number;
  posting_id: number;
  status: ApplicationStatus;
  applied_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  posting: { id: number; title: string; company: string };
  open_tasks: number;
}

export interface ApplicationDetail extends Application {
  events: ApplicationEvent[];
  tasks: Task[];
}
