import { useEffect, useState } from "react";
import { fileUrl, type MediaItem } from "../services/media";
import type { RenderJob } from "../services/render";
import {
  subtitlesApi,
  type SubtitleSegment,
} from "../services/subtitles";

interface Props {
  projectId: string;
  media: MediaItem[];
  lastRender: RenderJob | null;
}

export default function SubtitlePanel({
  projectId,
  media,
  lastRender,
}: Props) {
  const [segments, setSegments] = useState<SubtitleSegment[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [burned, setBurned] = useState<RenderJob | null>(null);

  const audioVisualMedia = media.filter(
    (m) => m.type === "audio" || m.type === "video"
  );
  const [selectedMediaId, setSelectedMediaId] = useState<string>("");
  const [model, setModel] = useState<string>("small");

  useEffect(() => {
    (async () => {
      try {
        const data = await subtitlesApi.get(projectId);
        if (data.exists) setSegments(data.segments);
      } catch {
        /* noop */
      }
    })();
  }, [projectId]);

  useEffect(() => {
    if (!selectedMediaId && audioVisualMedia.length > 0) {
      setSelectedMediaId(audioVisualMedia[0].id);
    }
  }, [audioVisualMedia, selectedMediaId]);

  const onTranscribe = async () => {
    if (!selectedMediaId) return;
    setBusy(true);
    setError(null);
    setStatus("Transcribiendo (puede tardar la primera vez)…");
    try {
      const res = await subtitlesApi.transcribe(
        projectId,
        selectedMediaId,
        model
      );
      setSegments(res.segments);
      setStatus(`Listo · ${res.segments.length} segmentos`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al transcribir");
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  const save = async (updated: SubtitleSegment[]) => {
    try {
      await subtitlesApi.update(projectId, updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    }
  };

  const onSegmentChange = (i: number, patch: Partial<SubtitleSegment>) => {
    const copy = [...segments];
    copy[i] = { ...copy[i], ...patch };
    setSegments(copy);
  };

  const onBlur = () => {
    if (segments.length > 0) save(segments);
  };

  const onAddSegment = () => {
    const last = segments[segments.length - 1];
    const start = last ? last.end : 0;
    setSegments([
      ...segments,
      { start, end: start + 2, text: "Nuevo subtítulo" },
    ]);
  };

  const onDeleteSegment = (i: number) => {
    const copy = segments.filter((_, idx) => idx !== i);
    setSegments(copy);
    save(copy);
  };

  const onBurn = async () => {
    if (!lastRender || lastRender.status !== "completed") {
      setError("Primero renderizá el video (Módulo 9).");
      return;
    }
    setBusy(true);
    setError(null);
    setStatus("Aplicando subtítulos al video…");
    try {
      const job = await subtitlesApi.burn(projectId, lastRender.id);
      setBurned(job);
      setStatus("Subtítulos incrustados.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al incrustar");
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-10 border border-white/5 rounded-xl bg-panel/60">
      <div className="px-4 py-3 border-b border-white/5">
        <div className="text-sm font-medium">💬 Subtítulos</div>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Transcripción */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={selectedMediaId}
            onChange={(e) => setSelectedMediaId(e.target.value)}
            disabled={busy || audioVisualMedia.length === 0}
            className="bg-black/30 border border-white/10 rounded px-2 py-1.5"
          >
            {audioVisualMedia.length === 0 && (
              <option value="">(sin audio/video disponible)</option>
            )}
            {audioVisualMedia.map((m) => (
              <option key={m.id} value={m.id}>
                {m.original_name}
              </option>
            ))}
          </select>

          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={busy}
            className="bg-black/30 border border-white/10 rounded px-2 py-1.5"
          >
            <option value="tiny">tiny (rápido)</option>
            <option value="base">base</option>
            <option value="small">small (recomendado)</option>
            <option value="medium">medium</option>
          </select>

          <button
            onClick={onTranscribe}
            disabled={busy || !selectedMediaId}
            className="px-3 py-1.5 rounded bg-accent hover:bg-accent/80 disabled:opacity-40 transition"
          >
            {busy ? "Procesando…" : "🎙 Transcribir"}
          </button>

          <button
            onClick={onAddSegment}
            disabled={busy}
            className="px-3 py-1.5 rounded border border-white/10 hover:bg-white/5 disabled:opacity-40"
          >
            + Segmento
          </button>

          <button
            onClick={onBurn}
            disabled={busy || !lastRender || segments.length === 0}
            title={
              !lastRender
                ? "Renderizá el video primero"
                : segments.length === 0
                ? "Sin subtítulos"
                : ""
            }
            className="px-3 py-1.5 rounded border border-white/10 hover:bg-white/5 disabled:opacity-40"
          >
            🎬 Incrustar en el video
          </button>
        </div>

        {status && (
          <div className="text-xs text-accent">{status}</div>
        )}
        {error && (
          <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
            {error}
          </div>
        )}

        {/* Segmentos */}
        {segments.length === 0 ? (
          <div className="text-xs text-white/40 text-center py-6 border border-dashed border-white/10 rounded-lg">
            Sin subtítulos todavía. Transcribí un audio o agregá segmentos
            manualmente.
          </div>
        ) : (
          <ul className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {segments.map((s, i) => (
              <li
                key={i}
                className="flex items-center gap-2 bg-black/20 border border-white/5 rounded-lg p-2"
              >
                <span className="text-[10px] text-white/40 w-6">
                  {i + 1}.
                </span>
                <input
                  type="number"
                  step="0.1"
                  value={s.start}
                  onChange={(e) =>
                    onSegmentChange(i, { start: Number(e.target.value) })
                  }
                  onBlur={onBlur}
                  className="w-16 text-xs bg-black/40 border border-white/10 rounded px-1.5 py-1"
                />
                <input
                  type="number"
                  step="0.1"
                  value={s.end}
                  onChange={(e) =>
                    onSegmentChange(i, { end: Number(e.target.value) })
                  }
                  onBlur={onBlur}
                  className="w-16 text-xs bg-black/40 border border-white/10 rounded px-1.5 py-1"
                />
                <input
                  type="text"
                  value={s.text}
                  onChange={(e) =>
                    onSegmentChange(i, { text: e.target.value })
                  }
                  onBlur={onBlur}
                  className="flex-1 text-xs bg-black/40 border border-white/10 rounded px-2 py-1"
                />
                <button
                  onClick={() => onDeleteSegment(i)}
                  className="text-red-400 hover:text-red-300 text-xs px-1"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Resultado del burn */}
        {burned && burned.output_url && (
          <div className="mt-2 space-y-2">
            <video
              src={fileUrl(burned.output_url)}
              controls
              className="w-full max-w-sm rounded-lg border border-white/5"
            />
            <a
              href={fileUrl(burned.output_url)}
              download
              className="inline-block px-3 py-1.5 rounded border border-white/10 hover:bg-white/5 text-xs"
            >
              ⬇ Descargar video con subtítulos
            </a>
          </div>
        )}
      </div>
    </div>
  );
}