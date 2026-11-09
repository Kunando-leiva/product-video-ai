import { useEffect, useRef, useState } from "react";
import { fileUrl } from "../services/media";
import { renderApi, type RenderJob } from "../services/render";

interface Props {
  projectId: string;
  canRender: boolean;
}

export default function RenderPanel({ projectId, canRender }: Props) {
  const [job, setJob] = useState<RenderJob | null>(null);
  const [history, setHistory] = useState<RenderJob[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const refresh = async () => {
    try {
      const list = await renderApi.list(projectId);
      setHistory(list);
      if (list.length > 0 && !job) setJob(list[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar renders");
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Polling mientras hay un job en curso
  useEffect(() => {
    if (!job) return;
    if (job.status !== "queued" && job.status !== "processing") return;

    const tick = async () => {
      try {
        const updated = await renderApi.get(projectId, job.id);
        setJob(updated);
        setHistory((h) =>
          h.map((x) => (x.id === updated.id ? updated : x))
        );
      } catch {
        /* ignore */
      }
    };
    pollRef.current = window.setInterval(tick, 500);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [job, projectId]);

  const onStart = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await renderApi.start(projectId);
      setJob(created);
      setHistory((h) => [created, ...h]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al iniciar render");
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (j: RenderJob) => {
    if (!confirm("¿Eliminar este render?")) return;
    try {
      await renderApi.remove(projectId, j.id);
      setHistory((h) => h.filter((x) => x.id !== j.id));
      if (job?.id === j.id) setJob(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Error al eliminar");
    }
  };

  const running = job && (job.status === "queued" || job.status === "processing");
  const pct = job ? Math.round(job.progress * 100) : 0;

  return (
    <div className="mt-10 border border-white/5 rounded-xl bg-panel/60">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="text-sm font-medium">🎬 Render</div>
        <button
          disabled={busy || running || !canRender}
          onClick={onStart}
          title={!canRender ? "Agregá clips a la timeline primero" : ""}
          className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/80 text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          {running ? "Renderizando…" : "▶ Renderizar video"}
        </button>
      </div>

      {error && (
        <div className="mx-4 mt-3 text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
          {error}
        </div>
      )}

      {job && (
        <div className="px-4 py-4 border-b border-white/5">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="text-white/60">
              Estado:{" "}
              <span
                className={
                  job.status === "completed"
                    ? "text-green-400"
                    : job.status === "failed"
                    ? "text-red-400"
                    : "text-accent"
                }
              >
                {job.status}
              </span>
            </span>
            <span className="text-white/40">{pct}%</span>
          </div>

          <div className="h-2 bg-black/40 rounded overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                job.status === "failed" ? "bg-red-500" : "bg-accent"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>

          {job.status === "failed" && job.error && (
            <div className="mt-3 text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2 whitespace-pre-wrap">
              {job.error}
            </div>
          )}

          {job.status === "completed" && job.output_url && (
            <div className="mt-4 space-y-2">
              <video
                src={fileUrl(job.output_url)}
                controls
                className="w-full max-w-sm rounded-lg border border-white/5"
              />
              <div className="flex gap-2">
                <a
                  href={fileUrl(job.output_url)}
                  download
                  className="px-3 py-1.5 rounded border border-white/10 hover:bg-white/5 text-xs"
                >
                  ⬇ Descargar MP4
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {history.length > 1 && (
        <div className="px-4 py-3">
          <div className="text-[11px] text-white/40 uppercase tracking-wide mb-2">
            Historial
          </div>
          <ul className="space-y-1">
            {history.slice(1).map((j) => (
              <li
                key={j.id}
                className="flex items-center justify-between text-xs text-white/50 hover:bg-white/5 rounded px-2 py-1"
              >
                <button
                  onClick={() => setJob(j)}
                  className="text-left flex-1 truncate"
                >
                  {new Date(j.created_at).toLocaleString()} · {j.status} ·{" "}
                  {Math.round(j.progress * 100)}%
                </button>
                <button
                  onClick={() => onDelete(j)}
                  className="text-red-400 hover:text-red-300 px-2"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}