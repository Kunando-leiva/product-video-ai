import { api } from "./api";

export type RenderStatus = "queued" | "processing" | "completed" | "failed";

export interface RenderJob {
  id: string;
  project_id: string;
  status: RenderStatus;
  progress: number;
  output_path: string | null;
  output_url: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export const renderApi = {
  list: (projectId: string) =>
    api.get<RenderJob[]>(`/projects/${projectId}/render`),

  start: (projectId: string, fps = 30) =>
    api.post<RenderJob>(`/projects/${projectId}/render`, { fps }),

  get: (projectId: string, jobId: string) =>
    api.get<RenderJob>(`/projects/${projectId}/render/${jobId}`),

  remove: (projectId: string, jobId: string) =>
    api.del(`/projects/${projectId}/render/${jobId}`),
};