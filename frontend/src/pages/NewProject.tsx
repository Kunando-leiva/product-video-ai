import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  projectsApi,
  type ProjectDuration,
  type ProjectFormat,
} from "../services/projects";

export default function NewProject() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [format, setFormat] = useState<ProjectFormat>("9:16");
  const [duration, setDuration] = useState<ProjectDuration>(30);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("El nombre del producto es obligatorio.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await projectsApi.create({
        name: name.trim(),
        product_url: productUrl.trim(),
        format,
        duration,
      });
      navigate("/projects");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear proyecto");
    } finally {
      setSubmitting(false);
    }
  };

  const formats: ProjectFormat[] = ["9:16", "1:1", "4:5", "16:9"];
  const durations: ProjectDuration[] = [30, 60, 90, 120];

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Nuevo proyecto</h1>
      <p className="text-white/50 text-sm mb-8">
        Completá los datos básicos. En próximos módulos podrás agregar imágenes,
        videos, voz y estilo.
      </p>

      <form onSubmit={onCreate} className="space-y-6">
        <Field label="Nombre del producto">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej: Auriculares Bluetooth X200"
            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-accent"
          />
        </Field>

        <Field label="Link del producto (opcional)">
          <input
            value={productUrl}
            onChange={(e) => setProductUrl(e.target.value)}
            placeholder="https://..."
            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 outline-none focus:border-accent"
          />
        </Field>

        <Field label="Formato">
          <div className="flex gap-2">
            {formats.map((f) => (
              <button
                type="button"
                key={f}
                onClick={() => setFormat(f)}
                className={`px-4 py-2 rounded-lg border text-sm transition ${
                  format === f
                    ? "border-accent bg-accent/20"
                    : "border-white/10 hover:bg-white/5"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Duración">
          <div className="flex gap-2">
            {durations.map((d) => (
              <button
                type="button"
                key={d}
                onClick={() => setDuration(d)}
                className={`px-4 py-2 rounded-lg border text-sm transition ${
                  duration === d
                    ? "border-accent bg-accent/20"
                    : "border-white/10 hover:bg-white/5"
                }`}
              >
                {d}s
              </button>
            ))}
          </div>
        </Field>

        {error && (
          <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="px-5 py-3 rounded-xl bg-accent hover:bg-accent/80 font-medium transition disabled:opacity-50"
          >
            {submitting ? "Creando…" : "Crear proyecto"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="px-5 py-3 rounded-xl border border-white/10 hover:bg-white/5 font-medium transition"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="text-xs uppercase tracking-wide text-white/50 mb-2">
        {label}
      </div>
      {children}
    </label>
  );
}