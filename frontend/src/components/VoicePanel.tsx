import { useEffect, useState } from "react";

import {
  voiceApi,
  voiceUrl,
  type SynthesizeResponse,
  type Voice,
} from "../services/voice";

interface Props {
  projectId: string;
}

export default function VoicePanel({ projectId }: Props) {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [available, setAvailable] = useState<boolean>(true);
  const [provider, setProvider] = useState<string>("");
  const [selected, setSelected] = useState<string>("");
  const [text, setText] = useState(
    "¡Mirá este producto! Diseño moderno, calidad premium, ideal para tu día a día."
  );
  const [speed, setSpeed] = useState(1.0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SynthesizeResponse | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await voiceApi.list();
        setVoices(res.voices);
        setAvailable(res.available);
        setProvider(res.provider);
        if (res.voices.length > 0) setSelected(res.voices[0].id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error al cargar voces");
      }
    })();
  }, []);

  const onGenerate = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await voiceApi.synthesize(
        projectId,
        text,
        selected || undefined,
        speed
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al generar voz");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-10 border border-white/5 rounded-xl bg-panel/60">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="text-sm font-medium">🔊 Voz IA</div>
        <div className="text-[11px] text-white/40">
          {available ? `proveedor: ${provider}` : "no disponible"}
        </div>
      </div>

      <div className="px-4 py-4 space-y-4">
        {!available && (
          <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-2">
            El motor de voz no está instalado. Mirá{" "}
            <span className="font-mono">pip install piper-tts</span> y descargá
            una voz con{" "}
            <span className="font-mono">
              python scripts/download_voice.py es_AR-daniela-high
            </span>
            .
          </div>
        )}

        <div className="flex flex-wrap gap-2 items-center text-xs">
          <label className="flex items-center gap-1">
            <span className="text-white/50">Voz:</span>
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              disabled={busy || voices.length === 0}
              className="bg-black/30 border border-white/10 rounded px-2 py-1.5"
            >
              {voices.length === 0 && (
                <option value="">(sin voces)</option>
              )}
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.id} {v.gender ? `· ${v.gender}` : ""}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-1">
            <span className="text-white/50">Velocidad:</span>
            <input
              type="range"
              min="0.7"
              max="1.5"
              step="0.05"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="w-28"
            />
            <span className="w-8 text-white/60">{speed.toFixed(2)}</span>
          </label>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="Texto a narrar…"
          className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <div className="text-[10px] text-white/40 -mt-3">
          {text.length} / 2000 caracteres
        </div>

        <div className="flex gap-2">
          <button
            onClick={onGenerate}
            disabled={busy || !available || !text.trim()}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/80 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            {busy ? "Generando…" : "🎙 Generar voz"}
          </button>
        </div>

        {error && (
          <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
            {error}
          </div>
        )}

        {result && (
          <div className="border-t border-white/5 pt-3 space-y-2">
            <div className="text-xs text-green-400">
              ✓ Generado · {result.duration ? `${result.duration.toFixed(2)}s · ` : ""}
              {(result.size_bytes / 1024).toFixed(1)} KB
            </div>
            <audio
              src={voiceUrl(result.audio_url)}
              controls
              className="w-full max-w-sm"
            />
            <a
              href={voiceUrl(result.audio_url)}
              download
              className="inline-block px-3 py-1.5 rounded border border-white/10 hover:bg-white/5 text-xs"
            >
              ⬇ Descargar WAV
            </a>
          </div>
        )}
      </div>
    </div>
  );
}