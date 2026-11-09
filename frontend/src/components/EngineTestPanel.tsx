import { useEffect, useState } from "react";
import { engineApi, type EngineStatus } from "../services/engine";
import { fileUrl, type MediaItem } from "../services/media";

interface Props {
  projectId: string;
  media: MediaItem[];
}

export default function EngineTestPanel({ projectId, media }: Props) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUrl, setLastUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    engineApi
      .status(projectId)
      .then(setStatus)
      .catch((e) => setError(e.message));
  }, [open, projectId]);

  const run = async (op: Parameters<typeof engineApi.test>[1]) => {
    setBusy(true);
    setError(null);
    setResult(null);
    setLastUrl(null);
    try {
      const picked = media.slice(0, 2).map((m) => m.id);
      const opts: Record<string, unknown> = {};
      if (op === "image_to_video") {
        opts.duration = 2;
        opts.width = 320;
        opts.height = 320;
      } else if (op === "trim_video") {
        opts.start = 0;
        opts.duration = 1;
      } else if (op === "overlay_text") {
        opts.text = "PRUEBA MÓDULO 7";
        opts.position = "bottom";
        opts.font_size = 24;
      } else if (op === "resize_and_pad") {
        opts.width = 360;
        opts.height = 640;
      }
      const res = await engineApi.test(projectId, op, picked, opts);
      setResult(
        `OK · ${(res.size_bytes / 1024).toFixed(1)} KB` +
          (res.duration ? ` · ${res.duration.toFixed(2)}s` : "")
      );
      // El out_path es absoluto; convertimos a URL /files
      const rel = res.out_path.split(/[\\/]projects[\\/]/).pop();
      if (rel) {
        setLastUrl(fileUrl(`/projects/${projectId}/generated/${rel}`));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-10 border border-white/5 rounded-xl bg-panel/60">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium hover:bg-white/5 transition"
      >
        <span>🧪 Motor FFmpeg — pruebas de operaciones (dev)</span>
        <span className="text-white/40">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4">
          <div className="text-xs text-white/50">
            {status?.ffmpeg_available ? (
              <span className="text-green-400">
                ● FFmpeg disponible {status.version && `· ${status.version}`}
              </span>
            ) : (
              <span className="text-red-400">● FFmpeg no disponible</span>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {(
              [
                "image_to_video",
                "trim_video",
                "concat_videos",
                "merge_audio",
                "overlay_text",
                "resize_and_pad",
              ] as const
            ).map((op) => (
              <button
                key={op}
                disabled={busy || !status?.ffmpeg_available}
                onClick={() => run(op)}
                className="px-3 py-2 text-xs rounded-lg border border-white/10 hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {op}
              </button>
            ))}
          </div>

          {media.length < 2 && (
            <div className="text-[11px] text-amber-400/80">
              Tip: algunas operaciones necesitan 2+ archivos. Subí al menos un
              video y un audio para probar todo.
            </div>
          )}

          {busy && <div className="text-xs text-accent">Ejecutando…</div>}
          {result && (
            <div className="text-xs text-green-400 bg-green-500/10 border border-green-500/30 rounded px-3 py-2">
              {result}
            </div>
          )}
          {error && (
            <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
              {error}
            </div>
          )}
          {lastUrl && (
            <video
              src={lastUrl}
              controls
              className="w-full max-w-md rounded-lg border border-white/5"
            />
          )}
        </div>
      )}
    </div>
  );
}