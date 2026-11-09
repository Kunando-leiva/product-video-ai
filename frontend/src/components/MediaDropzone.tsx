import { useRef, useState } from "react";

interface Props {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

export default function MediaDropzone({ onFiles, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hover, setHover] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setHover(false);
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) onFiles(files);
  };

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length) onFiles(files);
    e.target.value = ""; // permitir re-seleccionar el mismo archivo
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition ${
        disabled
          ? "border-white/5 opacity-50 cursor-not-allowed"
          : hover
          ? "border-accent bg-accent/5"
          : "border-white/10 hover:border-white/20"
      }`}
    >
      <div className="text-3xl mb-2">⬆️</div>
      <div className="font-medium mb-1">
        Arrastrá archivos o hacé click para elegir
      </div>
      <div className="text-xs text-white/40">
        Imágenes: JPG, PNG, WEBP · Videos: MP4, MOV, WEBM · Audio: MP3, WAV, M4A
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.webm,.mkv,.m4v,.mp3,.wav,.m4a,.aac,.ogg"
        onChange={handleSelect}
        className="hidden"
      />
    </div>
  );
}