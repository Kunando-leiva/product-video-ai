import { api } from "./api";
import type { RenderJob } from "./render";

export interface SubtitleSegment {
  start: number;
  end: number;
  text: string;
}

export interface SubtitleRead {
  exists: boolean;
  srt: string | null;
  segments: SubtitleSegment[];
}

export interface TranscribeResponse {
  segments: SubtitleSegment[];
  srt: string;
  language: string | null;
}

export const subtitlesApi = {
  get: (projectId: string) =>
    api.get<SubtitleRead>(`/projects/${projectId}/subtitles`),

  update: (projectId: string, segments: SubtitleSegment[]) =>
    api.put<SubtitleRead>(`/projects/${projectId}/subtitles`, { segments }),

  transcribe: (
    projectId: string,
    mediaId: string,
    model = "small",
    language?: string
  ) =>
    api.post<TranscribeResponse>(
      `/projects/${projectId}/subtitles/transcribe`,
      { media_id: mediaId, model, language }
    ),

  burn: (projectId: string, renderJobId?: string) =>
    api.post<RenderJob>(`/projects/${projectId}/subtitles/burn`, {
      render_job_id: renderJobId,
    }),
};