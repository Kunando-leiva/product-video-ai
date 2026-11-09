import { API_BASE, api } from "./api";

export interface MusicTrack {
  id: string;
  name: string;
  filename: string;
  duration: number | null;
  size_bytes: number;
  url: string | null;
}

export interface MusicSelection {
  music_enabled: boolean;
  music_track: string | null;
  music_volume: number;
  voice_enabled: boolean;
  voice_track: string | null;
}

export function musicUrl(u: string): string {
  return `${API_BASE.replace(/\/api$/, "")}/files${u}`;
}

export const musicApi = {
  list: () => api.get<{ tracks: MusicTrack[] }>("/music/tracks"),

  get: (projectId: string) =>
    api.get<MusicSelection>(`/projects/${projectId}/music`),

  update: (projectId: string, patch: Partial<MusicSelection>) =>
    api.put<MusicSelection>(`/projects/${projectId}/music`, patch),
};