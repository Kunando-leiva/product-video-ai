import {
  fileUrl,
  formatDuration,
  formatResolution,
  type MediaItem,
} from "../services/media";

interface Props {
  items: MediaItem[];
  onDelete: (item: MediaItem) => void;
}

const BADGE: Record<string, string> = {
  image: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  video: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  audio: "bg-amber-500/20 text-amber-300 border-amber-500/30",
};

export default function MediaGrid({ items, onDelete }: Props) {
  if (items.length === 0) {
    return (
      <div className="border border-dashed border-white/10 rounded-xl p-10 text-center text-white/40 text-sm">
        Todavía no hay archivos cargados.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {items.map((m) => (
        <div
          key={m.id}
          className="border border-white/5 rounded-xl bg-panel overflow-hidden flex flex-col"
        >
          <div className="aspect-video bg-black/40 relative flex items-center justify-center overflow-hidden">
            {m.type === "image" && (
              <img
                src={fileUrl(m.url)}
                alt={m.original_name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            )}
            {m.type === "video" && m.thumbnail_url && (
              <img
                src={fileUrl(m.thumbnail_url)}
                alt={m.original_name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            )}
            {m.type === "video" && !m.thumbnail_url && (
              <video
                src={fileUrl(m.url)}
                className="w-full h-full object-cover"
                muted
                preload="metadata"
              />
            )}
            {m.type === "audio" && (
              <div className="text-2xl text-white/40">🎵</div>
            )}
            <span
              className={`absolute top-2 left-2 text-[10px] uppercase px-2 py-0.5 rounded border ${BADGE[m.type]}`}
            >
              {m.type}
            </span>
            {m.duration != null && (
             <span className="absolute bottom-2 right-2 text-[10px] bg-black/70 px-2 py-0.5 rounded">
                {formatDuration(m.duration)}
              </span>
            )}
          </div>

          <div className="p-3 flex flex-col gap-1.5">
            <div
              className="text-xs font-medium truncate"
              title={m.original_name}
            >
              {m.original_name}
            </div>
            <div className="text-[10px] text-white/40 flex flex-wrap gap-x-2">
              {m.width && m.height && (
                <span>{formatResolution(m.width, m.height)}</span>
              )}
              {m.fps && <span>{m.fps} fps</span>}
              {m.orientation && <span>{m.orientation}</span>}
            </div>
            <button
              onClick={() => onDelete(m)}
              className="text-[11px] text-red-400 hover:text-red-300 text-left mt-1"
            >
              Eliminar
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}