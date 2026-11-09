import { api } from "./api";

export type ProjectFormat = "9:16" | "1:1" | "4:5" | "16:9";
export type ProjectDuration = 30 | 60 | 90 | 120;

export interface Project {
  id: string;
  name: string;
  product_name: string;
  product_description: string;
  product_url: string;
  duration: ProjectDuration;
  format: ProjectFormat;
  style: string;
  voice_enabled: boolean;
  voice_provider: string;
  voice_name: string;
  subtitles_enabled: boolean;
  subtitles_style: string;
  music_enabled: boolean;
  music_track: string | null;
  music_volume: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  product_url: string;
  format: ProjectFormat;
  duration: ProjectDuration;
}

export const projectsApi = {
  list: () => api.get<Project[]>("/projects"),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (payload: ProjectCreatePayload) =>
    api.post<Project>("/projects", payload),
  update: (id: string, patch: Partial<Project>) =>
    api.put<Project>(`/projects/${id}`, patch),
  remove: (id: string) => api.del(`/projects/${id}`),
};