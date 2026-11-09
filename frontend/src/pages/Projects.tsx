import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { projectsApi, type Project } from "../services/projects";

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await projectsApi.list();
      setProjects(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar proyectos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onDelete = async (id: string, name: string) => {
    if (!confirm(`¿Eliminar el proyecto “${name}”?`)) return;
    try {
      await projectsApi.remove(id);
      await refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Error al eliminar");
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold mb-1">Proyectos</h1>
          <p className="text-white/50 text-sm">
            {projects.length} proyecto{projects.length === 1 ? "" : "s"}
          </p>
        </div>
        <Link
          to="/new"
          className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/80 text-sm font-medium transition"
        >
          ➕ Nuevo
        </Link>
      </div>

      {loading && <div className="text-sm text-white/40">Cargando…</div>}

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="border border-dashed border-white/10 rounded-xl p-12 text-center text-white/40 text-sm">
          No hay proyectos todavía.
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <div
              key={p.id}
              className="border border-white/5 rounded-xl bg-panel p-4 flex flex-col"
            >
              <div className="aspect-video rounded-lg bg-black/40 mb-3 flex items-center justify-center text-white/20 text-xs">
                sin previsualización
              </div>
              <div className="font-medium truncate">{p.name}</div>
              <div className="text-xs text-white/40 mt-1 mb-3">
                {p.format} · {p.duration}s ·{" "}
                {new Date(p.updated_at).toLocaleDateString()}
              </div>
              {p.product_url && (
                <a
                  href={p.product_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-accent hover:underline truncate mb-3"
                >
                  {p.product_url}
                </a>
              )}
              <div className="mt-auto flex gap-2">
                <button
                  disabled
                  title="Disponible en Módulos posteriores"
                  className="flex-1 px-3 py-2 rounded-lg border border-white/10 text-xs text-white/30 cursor-not-allowed"
                >
                  Abrir editor
                </button>
                <button
                  onClick={() => onDelete(p.id, p.name)}
                  className="px-3 py-2 rounded-lg border border-red-500/30 text-xs text-red-400 hover:bg-red-500/10 transition"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}