import { useEffect, useRef, useState } from "react";
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

const toWrite = (item: TimelineItem): TimelineItemWrite => ({
  media_id: item.media_id,
  duration: item.duration,
  effect: item.effect,
  start: item.start,
  text: item.text,
});

export default function TimelineEditor({
  projectId,
  media,
  targetDuration,
  onChange,
}: Props) {
  const [items, setItems] = useState<TimelineItemWrite[]>([]);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const knownMediaIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    setLoaded(false);
    setDirty(false);
    knownMediaIds.current = new Set();
    (async () => {
      try {
        const { items: saved } = await timelineApi.list(projectId);
        if (cancelled) return;
        setItems(saved.map(toWrite));
        onChange?.(saved);
        knownMediaIds.current = new Set(saved.map((item) => item.media_id).filter((id): id is string => Boolean(id)));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Error al cargar timeline");
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [projectId]);

  // Cada archivo nuevo se incorpora una sola vez. Los elementos existentes
  // no se reinsertan si el usuario los quitó deliberadamente.
  useEffect(() => {
    if (!loaded) return;
    const fresh = media.filter((m) =>
      (m.type === "image" || m.type === "video") &&
      !knownMediaIds.current.has(m.id)
    );
    if (!fresh.length) return;

    fresh.forEach((m) => knownMediaIds.current.add(m.id));
    setItems((prev) => [
      ...prev,
      ...fresh.map((m) => ({
        media_id: m.id,
        duration: m.type === "video" && m.duration
          ? Math.max(0.5, Math.min(m.duration, 5))
          : 3,
        effect: "none",
        start: 0,
        text: null,
      })),
    ]);
    setDirty(true);
    setError(null);
  }, [media, loaded]);

  const updateItem = (idx: number, patch: Partial<TimelineItemWrite>) => {
    setItems((prev) => prev.map((it, i) => i === idx ? { ...it, ...patch } : it));
    setDirty(true);
  };

  const removeItem = (idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx));
    setDirty(true);
  };

  const duplicateItem = (idx: number) => {
    setItems((prev) => {
      const copy = [...prev];
      copy.splice(idx + 1, 0, { ...prev[idx] });
      return copy;
    });
    setDirty(true);
  };

  const move = (idx: number, dir: -1 | 1) => {
    setItems((prev) => {
      const next = [...prev];
      const target = idx + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
    setDirty(true);
  };

  const addOne = (mediaId: string) => {
    const m = media.find((entry) => entry.id === mediaId);
    if (!m || (m.type !== "image" && m.type !== "video")) return;
    setItems((prev) => [...prev, {
      media_id: m.id,
      duration: m.type === "video" && m.duration ? Math.min(m.duration, 5) : 3,
      effect: "none",
      start: 0,
      text: null,
    }]);
    setDirty(true);
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const { items: saved } = await timelineApi.replace(projectId, items);
      setItems(saved.map(toWrite));
      onChange?.(saved);
      setDirty(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar timeline");
    } finally {
      setBusy(false);
    }
  };

  const total = items.reduce((sum, item) => sum + (item.duration || 0), 0);
  const mediaById = Object.fromEntries(media.map((m) => [m.id, m]));

  return (
    <section className="mt-10 border border-white/5 rounded-xl bg-panel/60">
      <header className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-white/5">
        <div>
          <div className="text-sm font-medium">🎞 Timeline</div>
          <div className="text-[11px] text-white/40 mt-1">
            {items.length} clips · {total.toFixed(1)}s / {targetDuration}s
          </div>
        </div>
        <button onClick={save} disabled={busy || !loaded || !dirty || items.length === 0}
          className="px-3 py-1.5 rounded bg-accent hover:bg-accent/80 text-xs font-medium disabled:opacity-40">
          {busy ? "Guardando…" : dirty ? "💾 Guardar cambios" : "✓ Timeline guardada"}
        </button>
      </header>

      {error && <div className="mx-4 mt-3 text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">{error}</div>}
      {dirty && <div className="mx-4 mt-3 text-xs text-amber-300">Hay cambios sin guardar. Guardá la timeline antes de renderizar.</div>}

      {!loaded ? <div className="px-4 py-6 text-xs text-white/40">Cargando timeline…</div> :
        items.length === 0 ? <div className="px-4 py-6 text-xs text-white/40">Subí imágenes o videos para agregarlos automáticamente a la secuencia.</div> :
        <ol className="divide-y divide-white/5">
          {items.map((it, idx) => {
            const m = it.media_id ? mediaById[it.media_id] : null;
            return <li key={`${it.media_id ?? "missing"}-${idx}`} className="flex items-center gap-3 px-4 py-3">
              <div className="w-16 h-10 bg-black/40 rounded overflow-hidden flex-shrink-0">
                {m && <img src={fileUrl(m.thumbnail_url ?? m.url)} alt="" className="w-full h-full object-cover" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs truncate">{m?.original_name ?? "(archivo no disponible)"}</div>
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <input aria-label="Duración del clip" type="number" min={0.1} max={600} step={0.1} value={it.duration}
                    onChange={(e) => updateItem(idx, { duration: Math.max(0.1, Number(e.target.value) || 0.1) })}
                    className="w-20 bg-black/30 border border-white/10 rounded px-2 py-1 text-xs" />
                  <span className="text-[11px] text-white/40">s</span>
                  <select aria-label="Efecto del clip" value={it.effect ?? "none"} onChange={(e) => updateItem(idx, { effect: e.target.value })}
                    className="bg-black/30 border border-white/10 rounded px-2 py-1 text-xs">
                    {EFFECTS.map((effect) => <option key={effect.value} value={effect.value}>{effect.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => move(idx, -1)} disabled={idx === 0} className="px-2 py-1 text-xs disabled:opacity-20" title="Mover arriba">↑</button>
                <button onClick={() => move(idx, 1)} disabled={idx === items.length - 1} className="px-2 py-1 text-xs disabled:opacity-20" title="Mover abajo">↓</button>
                <button onClick={() => duplicateItem(idx)} className="px-2 py-1 text-xs" title="Duplicar clip">⧉</button>
                <button onClick={() => removeItem(idx)} className="px-2 py-1 text-xs text-red-400" title="Quitar clip">✕</button>
              </div>
            </li>;
          })}
        </ol>
      }

      {media.some((m) => m.type === "image" || m.type === "video") && (
        <footer className="px-4 py-3 border-t border-white/5">
          <div className="text-[11px] text-white/40 uppercase tracking-wide mb-2">Agregar nuevamente</div>
          <div className="flex flex-wrap gap-2">
            {media.filter((m) => m.type === "image" || m.type === "video").map((m) =>
              <button key={m.id} onClick={() => addOne(m.id)} className="px-2 py-1 rounded border border-white/10 hover:bg-white/5 text-[11px] truncate max-w-[160px]">
                + {m.original_name}
              </button>
            )}
          </div>
        </footer>
      )}
    </section>
  );
}
