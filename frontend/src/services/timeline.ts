import { api } from "./api";

export interface TimelineItem {
  id: string;
  project_id: string;
  media_id: string | null;
  order_index: number;
  start: number;
  duration: number;
  effect: string | null;
  text: string | null;
}

export interface TimelineItemWrite {
  media_id: string | null;
  duration: number;
  effect?: string | null;
  start?: number;
  text?: string | null;
}

export const timelineApi = {
  list: (projectId: string) =>
    api.get<{ items: TimelineItem[] }>(`/projects/${projectId}/timeline`),

  replace: (projectId: string, items: TimelineItemWrite[]) =>
    api.put<{ items: TimelineItem[] }>(
      `/projects/${projectId}/timeline`,
      { items }
    ),
};