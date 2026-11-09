import { useEffect, useState } from "react";
import {
  aiApi,
  type AIProviderInfo,
  type AIUsageRow,
} from "../services/ai";

export default function AIPanel() {
  const [providers, setProviders] = useState<AIProviderInfo[]>([]);
  const [active, setActive] = useState<string>("");
  const [prompt, setPrompt] = useState(
    "Escribí un título llamativo para un producto electrónico."
  );
  const [text, setText] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<AIUsageRow[]>([]);

  const load = async () => {
    try {
      const [p, u] = await Promise.all([aiApi.providers(), aiApi.usage(10)]);
      setProviders(p.providers);
      setActive(p.active);
      setUsage(u.rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar IA");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runTest = async () => {
    setBusy(true);
    setError(null);
    setText("");
    try {
      const res = await aiApi.testText(prompt);
      setText(res.text);
      const u = await aiApi.usage(10);
      setUsage(u.rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border border-white/5 rounded-xl bg-panel/60">
        <div className="px-4 py-3 border-b border-white/5 text-sm font-medium">
          🤖 Proveedores de IA
        </div>
        <div className="p-4 space-y-2">
          {providers.map((p) => (
            <div
              key={p.name}
              className="flex items-center justify-between px-3 py-2 rounded-lg border border-white/5"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-2 h-2 rounded-full ${
                    p.available ? "bg-green-500" : "bg-white/20"
                  }`}
                />
                <div>
                  <div className="text-sm font-medium capitalize">
                    {p.name}
                    {p.name === active && (
                      <span className="ml-2 text-[10px] uppercase bg-accent/20 text-accent px-2 py-0.5 rounded">
                        activo
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-white/40">
                    {p.requires_internet ? "requiere internet" : "local"}
                    {p.model ? ` · ${p.model}` : ""}
                  </div>
                </div>
              </div>
              <div className="text-[11px] text-white/40">
                {p.available ? "disponible" : "no disponible"}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border border-white/5 rounded-xl bg-panel/60">
        <div className="px-4 py-3 border-b border-white/5 text-sm font-medium">
          🧪 Playground (usa el provider activo:{" "}
          <span className="text-accent">{active}</span>)
        </div>
        <div className="p-4 space-y-3">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
          />
          <button
            onClick={runTest}
            disabled={busy || !prompt.trim()}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/80 text-sm font-medium disabled:opacity-40"
          >
            {busy ? "Generando…" : "Generar"}
          </button>
          {error && (
            <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
              {error}
            </div>
          )}
          {text && (
            <div className="text-xs bg-black/30 border border-white/10 rounded-lg p-3 whitespace-pre-wrap">
              {text}
            </div>
          )}
        </div>
      </div>

      <div className="border border-white/5 rounded-xl bg-panel/60">
        <div className="px-4 py-3 border-b border-white/5 text-sm font-medium">
          📊 Últimas llamadas
        </div>
        <div className="p-4">
          {usage.length === 0 ? (
            <div className="text-xs text-white/40">
              Sin llamadas registradas.
            </div>
          ) : (
            <ul className="space-y-1 text-xs">
              {usage.map((u) => (
                <li
                  key={u.id}
                  className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-white/5"
                >
                  <span className="text-white/60">
                    {new Date(u.created_at).toLocaleTimeString()} ·{" "}
                    <span className="text-accent">{u.provider}</span> ·{" "}
                    {u.task}
                  </span>
                  <span
                    className={
                      u.status === "success"
                        ? "text-green-400"
                        : "text-red-400"
                    }
                  >
                    {u.status}
                    {u.tokens > 0 && ` · ${u.tokens} tok`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}