import { useEffect, useState } from "react";
import { musicApi, musicUrl, type MusicSelection, type MusicTrack } from "../services/music";

interface Props {
  projectId: string;
}

export default function MusicPanel({ projectId }: Props) {
  const [tracks, setTracks] = useState<MusicTrack[]>([]);
  const [sel, setSel] = useState<MusicSelection | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [listRes, selRes] = await Promise.all([
        musicApi.list(),
        musicApi.get(projectId),
      ]);
      setTracks(listRes.tracks);
      setSel(selRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar música");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const patch = async (p: Partial<MusicSelection>) => {
    setBusy(true);
    setError(null);
    try {
      const updated = await musicApi.update(projectId, p);
      setSel(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setBusy(false);
    }
  };

  const selectedTrack = tracks.find((t) => t.id === sel?.music_track);

  return (
    <div className="mt-10 border border-white/5 rounded-xl bg-panel/60">
      <div className="px-4 py-3 border-b border-white/5">
        <div className="text-sm font-medium">🎵 Música</div>
      </div>

      <div className="px-4 py-4 space-y-4">
        {tracks.length === 0 && (
          <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-2">
            No hay pistas en <span className="font-mono">assets/music/</span>.
            Copiá MP3s ahí o corré{" "}
            <span className="font-mono">
              python scripts/generate_music.py
            </span>
            .
          </div>
        )}

        {sel && (
          <>
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={sel.music_enabled}
                onChange={(e) =>
                  patch({ music_enabled: e.target.checked })
                }
                disabled={busy}
              />
              <span>Activar música</span>
            </label>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <label className="flex items-center gap-1">
                <span className="text-white/50">Pista:</span>
                <select
                  value={sel.music_track ?? ""}
                  onChange={(e) =>
                    patch({ music_track: e.target.value || null })
                  }
                  disabled={busy || !sel.music_enabled}
                  className="bg-black/30 border border-white/10 rounded px-2 py-1.5 min-w-48"
                >
                  <option value="">(sin pista)</option>
                  {tracks.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                      {t.duration ? ` · ${t.duration.toFixed(1)}s` : ""}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex items-center gap-1">
                <span className="text-white/50">Volumen:</span>
                <input
                  type="range"
                  min="0"
                  max="0.5"
                  step="0.01"
                  value={sel.music_volume}
                  onChange={(e) =>
                    setSel({
                      ...sel,
                      music_volume: Number(e.target.value),
                    })
                  }
                  onMouseUp={(e) =>
                    patch({
                      music_volume: Number(
                        (e.target as HTMLInputElement).value
                      ),
                    })
                  }
                  onTouchEnd={(e) =>
                    patch({
                      music_volume: Number(
                        (e.target as HTMLInputElement).value
                      ),
                    })
                  }
                  disabled={busy || !sel.music_enabled}
                  className="w-32"
                />
                <span className="text-white/60 w-10">
                  {Math.round(sel.music_volume * 100)}%
                </span>
              </label>

              {selectedTrack?.url && (
                <audio
                  src={musicUrl(selectedTrack.url)}
                  controls
                  className="h-8"
                />
              )}
            </div>

            <div className="text-[11px] text-white/40 border-t border-white/5 pt-3">
              Voz del proyecto:{" "}
              {sel.voice_track ? (
                <span className="text-green-400">
                  ✓ seleccionada
                </span>
              ) : (
                <span className="text-white/40">
                  no seleccionada — generala en el panel 🔊 Voz IA
                </span>
              )}
            </div>

            <div className="text-[10px] text-white/30">
              Al renderizar, la voz se mantiene al 100% y la música se mezcla
              al volumen elegido (Regla 17).
            </div>
          </>
        )}

        {error && (
          <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}