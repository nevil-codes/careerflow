// Mirrors ProfileRead / ProfileItemRead in backend/app/models.py.

export type ItemType = "education" | "job" | "project" | "course" | "skill";
export type ItemStatus = "completed" | "in-progress" | "planned" | "paused";

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
