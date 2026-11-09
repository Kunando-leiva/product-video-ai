import { API_BASE, api } from "./api";

export interface Voice {
  id: string;
  name: string;
  language: string;
  quality: string;
  gender: string | null;
}

export interface VoiceListResponse {
  available: boolean;
  provider: string;
  voices: Voice[];
}

export interface SynthesizeResponse {
  audio_path: string;
  audio_url: string;
  voice_id: string;
  duration: number | null;
  size_bytes: number;
}

export function voiceUrl(audioUrl: string): string {
  return `${API_BASE.replace(/\/api$/, "")}/files${audioUrl}`;
}

export const voiceApi = {
  list: () => api.get<VoiceListResponse>("/voice/voices"),

  synthesize: (
    projectId: string,
    text: string,
    voiceId?: string,
    speed = 1.0
  ) =>
    api.post<SynthesizeResponse>(
      `/projects/${projectId}/voice/synthesize`,
      { text, voice_id: voiceId, speed }
    ),
};