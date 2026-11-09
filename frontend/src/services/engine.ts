import { api } from "./api";

export interface EngineStatus {
  ffmpeg_available: boolean;
  ffmpeg_path: string | null;
  ffprobe_path: string | null;
  version: string | null;
}

export interface EngineTestResponse {
  out_path: string;
  duration: number | null;
  size_bytes: number;
}

export type EngineOperation =
  | "image_to_video"
  | "trim_video"
  | "concat_videos"
  | "merge_audio"
  | "overlay_text"
  | "resize_and_pad";

export const engineApi = {
  status: (projectId: string) =>
    api.get<EngineStatus>(`/projects/${projectId}/engine/status`),

  test: (
    projectId: string,
    operation: EngineOperation,
    mediaIds: string[],
    options: Record<string, unknown> = {}
  ) =>
    api.post<EngineTestResponse>(`/projects/${projectId}/engine/test`, {
      operation,
      media_ids: mediaIds,
      options,
    }),
};