import { useEffect, useState } from "react";
import type { MediaItem } from "../services/media";
import { fileUrl } from "../services/media";
import {
  timelineApi,
  type TimelineItem,
  type TimelineItemWrite,
} from "../services/timeline";

interface Props {
  projectId: string;
  media: MediaItem[];
  targetDuration: number;
  onChange?: (items: TimelineItem[]) => void;
}

const EFFECTS = [
  { value: "none", label: "Sin efecto" },
  { value: "zoom_in", label: "Zoom in" },
  { value: "zoom_out", label: "Zoom out" },
  { value: "pan_left", label: "Pan izquierda" },
  { value: "pan_right", label: "Pan derecha" },
  { value: "pan_up", label: "Pan arriba" },
  { value: "pan_down", label: "Pan abajo" },
  { value: "fade", label: "Fade" },
];

export default function TimelineEditor({
  projectId,
  media,
  targetDuration,
  onChange,
}: Props) {
  const [items, setItems] = useState<TimelineItemWrite[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cargar timeline al montar
  useEffect(() => {
    (async () => {
      try {
        const { items: loaded } = await timelineApi.list(projectId);
        setItems(
          loaded.map((i) => ({
            media_id: i.media_id,
            duration: i.duration,
            effect: i.effect,
            start: i.start,
            text: i.text,
          }))
        );
        onChange?.(loaded);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error al cargar timeline");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const addAllMedia = () => {
    const additions = media.map((m) => ({
      media_id: m.id,
      duration: 1.0,
      effect: "none",
      start: 0,
      text: null,
    }));
    setItems((prev) => [...prev, ...additions]);
  };

  const addOne = (mediaId: string) => {
    setItems((prev) => [
      ...prev,
      { media_id: mediaId, duration: 1.0, effect: "none", start: 0, text: null },
    ]);
  };

  const updateItem = (idx: number, patch: Partial<TimelineItemWrite>) => {
    setItems((prev) =>
      prev.map((it, i) => (i === idx ? { ...it, ...patch } : it))
    );
  };

  const removeItem = (idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const move = (idx: number, dir: -1 | 1) => {
    setItems((prev) => {
      const next = [...prev];
      const j = idx + dir;
      if (j < 0 || j >= next.length) return prev;
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const { items: savedItems } = await timelineApi.replace(projectId, items);
      setItems(
        savedItems.map((i) => ({
          media_id: i.media_id,
          duration: i.duration,
          effect: i.effect,
          start: i.start,
          text: i.text,
        }))
      );
      onChange?.(savedItems);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar timeline");
    } finally {
      setBusy(false);
    }
  };

  const total = items.reduce((s, i) => s + (i.duration || 0), 0);
  const mediaById = Object.fromEntries(media.map((m) => [m.id, m]));

  return (
    <div className="mt-10 border border-white/5 rounded-xl bg-panel/60">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="text-sm font-medium">🎞 Timeline</div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-white/40">
            {total.toFixed(1)}s / {targetDuration}s
          </span>
          <button
            onClick={addAllMedia}
            disabled={media.length === 0}
            className="px-3 py-1.5 rounded border border-white/10 hover:bg-white/5 text-xs disabled:opacity-40"
          >
            + Agregar todo el material
          </button>
          <button
            onClick={save}
            disabled={busy}
            className="px-3 py-1.5 rounded bg-accent hover:bg-accent/80 text-xs font-medium disabled:opacity-40"
          >
            {busy ? "Guardando…" : "💾 Guardar timeline"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-3 text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
          {error}
        </div>
      )}

      {items.length === 0 ? (
        <div className="px-4 py-6 text-xs text-white/40">
          Sin clips. Agregá material o subí archivos.
        </div>
      ) : (
        <ul className="divide-y divide-white/5">
          {items.map((it, idx) => {
            const m = it.media_id ? mediaById[it.media_id] : null;
            return (
              <li key={idx} className="flex items-center gap-3 px-4 py-3">
                <div className="w-16 h-10 bg-black/40 rounded overflow-hidden flex-shrink-0">
                  {m && (
                    <img
                      src={fileUrl(m.thumbnail_url ?? m.url)}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="text-xs truncate">
                    {m?.original_name ?? "(media eliminado)"}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <input
                      type="number"
                      min={0.1}
                      step={0.1}
                      value={it.duration}
                      onChange={(e) =>
                        updateItem(idx, { duration: parseFloat(e.target.value) || 1 })
                      }
                      className="w-20 bg-black/30 border border-white/10 rounded px-2 py-1 text-xs"
                    />
                    <span className="text-[11px] text-white/40">s</span>
                    <select
                      value={it.effect ?? "none"}
                      onChange={(e) => updateItem(idx, { effect: e.target.value })}
                      className="bg-black/30 border border-white/10 rounded px-2 py-1 text-xs"
                    >
                      {EFFECTS.map((e) => (
                        <option key={e.value} value={e.value}>
                          {e.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => move(idx, -1)}
                    className="px-2 py-1 text-xs text-white/40 hover:text-white/80"
                    title="Subir"
                  >
                    ↑
                  </button>
                  <button
                    onClick={() => move(idx, 1)}
                    className="px-2 py-1 text-xs text-white/40 hover:text-white/80"
                    title="Bajar"
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => removeItem(idx)}
                    className="px-2 py-1 text-xs text-red-400 hover:text-red-300"
                    title="Quitar"
                  >
                    ✕
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {media.length > 0 && (
        <div className="px-4 py-3 border-t border-white/5">
          <div className="text-[11px] text-white/40 uppercase tracking-wide mb-2">
            Agregar individual
          </div>
          <div className="flex flex-wrap gap-2">
            {media.map((m) => (
              <button
                key={m.id}
                onClick={() => addOne(m.id)}
                className="px-2 py-1 rounded border border-white/10 hover:bg-white/5 text-[11px] truncate max-w-[160px]"
                title={m.original_name}
              >
                + {m.original_name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}