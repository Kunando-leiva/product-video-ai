import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import MediaDropzone from "../components/MediaDropzone";
import MediaGrid from "../components/MediaGrid";
import TimelineEditor from "../components/TimelineEditor";
import RenderPanel from "../components/RenderPanel";
import EngineTestPanel from "../components/EngineTestPanel";
import SubtitlePanel from "../components/SubtitlePanel";
import { mediaApi, type MediaItem } from "../services/media";
import { projectsApi, type Project } from "../services/projects";
import type { TimelineItem } from "../services/timeline";
import { renderApi, type RenderJob } from "../services/render";
import VoicePanel from "../components/VoicePanel";
import MusicPanel from "../components/MusicPanel";


export default function ProjectDetail() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [lastRender, setLastRender] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, m, jobs] = await Promise.all([
        projectsApi.get(id),
        mediaApi.list(id),
        renderApi.list(id),
      ]);
      setProject(p);
      setMedia(m);
      const completed = jobs.find((j) => j.status === "completed") ?? null;
      setLastRender(completed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onFiles = async (files: File[]) => {
    setUploading(true);
    setError(null);
    try {
      for (const f of files) {
        const created = await mediaApi.upload(id, f);
        setMedia((prev) => [...prev, created]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al subir archivo");
    } finally {
      setUploading(false);
    }
  };

  const onDelete = async (item: MediaItem) => {
    if (!confirm(`¿Eliminar “${item.original_name}”?`)) return;
    try {
      await mediaApi.remove(id, item.id);
      setMedia((prev) => prev.filter((m) => m.id !== item.id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Error al eliminar");
    }
  };

  if (loading) {
    return <div className="text-sm text-white/40">Cargando…</div>;
  }

  if (!project) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          {error || "Proyecto no encontrado."}
        </div>
        <Link
          to="/projects"
          className="mt-4 inline-block text-sm text-accent hover:underline"
        >
          ← Volver al listado
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      <Link to="/projects" className="text-xs text-white/40 hover:text-white/70">
        ← Proyectos
      </Link>

      <div className="flex items-center justify-betweenmt-2 mb-8">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <div className="text-xs text-white/40 mt-1">
            {project.format} · {project.duration}s · {project.style}
          </div>
        </div>
      </div>

      <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wide mb-3">
        Archivos ({media.length})
      </h2>

      <MediaDropzone onFiles={onFiles} disabled={uploading} />
      {uploading && <div className="mt-3 text-xs text-accent">Subiendo…</div>}
      {error && (
        <div className="mt-3 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <div className="mt-6">
        <MediaGrid items={media} onDelete={onDelete} />
      </div>

      <TimelineEditor
        projectId={id}
        media={media}
        targetDuration={project.duration}
        onChange={setTimeline}
      />

      <RenderPanel projectId={id} canRender={timeline.length > 0} />

      <SubtitlePanel
        projectId={id}
        media={media}
        lastRender={lastRender}
      />

      <VoicePanel projectId={id} />

      <MusicPanel projectId={id} />

      <EngineTestPanel projectId={id} media={media} />
    </div>
  );
}