import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { projectsApi, type Project } from "../services/projects";

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await projectsApi.list();
        if (!cancelled) setProjects(data.slice(0, 5));
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Error desconocido");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
      <p className="text-white/50 text-sm mb-8">
        Bienvenido. Empezá creando un nuevo proyecto o abrí uno existente.
      </p>

      <div className="flex gap-3 mb-10">
        <Link
          to="/new"
          className="px-5 py-3 rounded-xl bg-accent hover:bg-accent/80 font-medium transition"
        >
          ➕ Nuevo proyecto
        </Link>
        <Link
          to="/projects"
          className="px-5 py-3 rounded-xl border border-white/10 hover:bg-white/5 font-medium transition"
        >
          📁 Ver proyectos
        </Link>
      </div>

      <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wide mb-3">
        Proyectos recientes
      </h2>

      {loading && (
        <div className="text-sm text-white/40">Cargando…</div>
      )}

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="border border-dashed border-white/10 rounded-xl p-10 text-center text-white/40 text-sm">
          Todavía no hay proyectos. Creá el primero con “Nuevo proyecto”.
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <ul className="divide-y divide-white/5 border border-white/5 rounded-xl overflow-hidden">
          {projects.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between px-4 py-3 hover:bg-white/5"
            >
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-white/40">
                  {p.format} · {p.duration}s ·{" "}
                  {new Date(p.updated_at).toLocaleString()}
                </div>
              </div>
              <Link
  to={`/projects/${p.id}`}
  className="flex-1 px-3 py-2 rounded-lg border border-white/10 text-xs text-white/80 hover:bg-white/5 text-center transition"
>
  Abrir
</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}