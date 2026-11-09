import { API_BASE, api } from "./api";

export type MediaType = "image" | "video" | "audio";

export interface MediaItem {
  id: string;
  project_id: string;
  type: MediaType;
  filename: string;
  original_name: string;
  path: string;
  url: string;
  duration: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  orientation: string | null;
  thumbnail_path: string | null;
  thumbnail_url: string | null;
  created_at: string;
}

export function fileUrl(url: string): string {
  return `${API_BASE.replace(/\/api$/, "")}/files${url}`;
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatResolution(
  w: number | null,
  h: number | null
): string {
  if (!w || !h) return "—";
  return `${w}×${h}`;
}

export const mediaApi = {
  list: (projectId: string) =>
    api.get<MediaItem[]>(`/projects/${projectId}/media`),

  upload: async (projectId: string, file: File): Promise<MediaItem> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_BASE}/projects/${projectId}/media`,
      { method: "POST", body: form }
    );
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const msg =
        (body && (body.message || body.error)) ||
        `Error ${res.status} al subir ${file.name}`;
      throw new Error(msg);
    }
    return body as MediaItem;
  },

  remove: (projectId: string, mediaId: string) =>
    api.del(`/projects/${projectId}/media/${mediaId}`),
};