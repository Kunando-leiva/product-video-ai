"""FFmpegEngine: operaciones de alto nivel sobre archivos multimedia."""
import logging
import os
import shutil
import uuid
from pathlib import Path

from app.core.errors import ValidationError
from app.video import plan as plan_mod
from app.video.ffmpeg_runner import ensure_parent, run_ffmpeg


log = logging.getLogger("app.video.engine")


# Extensiones aceptadas como imagen para image_to_video
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}


class FFmpegEngine:
    """Motor de video basado en FFmpeg.

    Métodos:
      - image_to_video: convierte una imagen en un clip
      - trim_video: corta un segmento
      - concat_videos: une varios videos
      - merge_audio: agrega/reemplaza pista de audio
      - overlay_text: agrega texto sobre el video
      - resize_and_pad: ajusta a un tamaño fijo con fondo
      - execute_plan: recorre un VideoPlan y ejecuta las operaciones
    """

    # ------------------------------------------------------------------
    # Operaciones individuales
    # ------------------------------------------------------------------

    def image_to_video(
        self,
        image_path: str,
        out_path: str,
        duration: float,
        width: int,
        height: int,
        fps: int = 30,
        fit: str = "cover",
    ) -> None:
        img = Path(image_path)
        if not img.exists():
            raise ValidationError(
                message="La imagen de entrada no existe.",
                cause=str(img),
            )
        # Fix Bug 1: validar que sea imagen real, no un video disfrazado
        if img.suffix.lower() not in _IMAGE_EXTS:
            raise ValidationError(
                message="image_to_video requiere un archivo de imagen.",
                cause=f"Extensión recibida: {img.suffix}",
                solution=(
                    "Subí una imagen (PNG/JPG/WebP/BMP/TIFF/GIF) o usá "
                    "trim_video para videos existentes."
                ),
            )

        if fit == "cover":
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}"
            )
        else:  # contain
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )

        out = ensure_parent(out_path)
        # `-f image2` explícito + `-loop 1` juntos. Sin el demuxer
        # explícito, FFmpeg en Windows a veces busca `loop` en el demuxer
        # equivocado y falla con "Option loop not found".
        run_ffmpeg(
            [
                "-y",
                "-loop", "1",
                "-f", "image2",
                "-i", str(img),
                "-t", f"{duration:.3f}",
                "-vf", vf,
                "-r", str(fps),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "veryfast",
                "-movflags", "+faststart",
                str(out),
            ]
        )

    def trim_video(
        self,
        in_path: str,
        out_path: str,
        start: float,
        duration: float,
        reencode: bool = True,
    ) -> None:
        src = Path(in_path)
        if not src.exists():
            raise ValidationError(
                message="El video de entrada no existe.",
                cause=str(src),
            )
        if not self._has_stream(str(src), "video"):
            raise ValidationError(
                message="trim_video requiere un archivo con pista de video.",
                cause=str(src),
            )
        out = ensure_parent(out_path)

        args = ["-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{duration:.3f}"]
        if reencode:
            args += [
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-movflags", "+faststart",
            ]
        else:
            args += ["-c", "copy"]
        args += [str(out)]
        run_ffmpeg(args)

    def concat_videos(self, in_paths: list[str], out_path: str) -> None:
        if len(in_paths) < 2:
            raise ValidationError(
                message="Se necesitan al menos 2 videos para concatenar.",
            )
        for p in in_paths:
            if not Path(p).exists():
                raise ValidationError(
                    message="Uno de los videos de entrada no existe.",
                    cause=p,
                )
            if not self._has_stream(p, "video"):
                raise ValidationError(
                    message="Todos los inputs de concat_videos deben tener video.",
                    cause=p,
                )
        out = ensure_parent(out_path)

        # Directorio temporal aislado por ejecución (evita colisiones
        # entre llamadas consecutivas con el mismo out.parent).
        tmp_dir = out.parent / f"_concat_tmp_{uuid.uuid4().hex[:8]}"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        try:
            normalized: list[Path] = []
            for i, p in enumerate(in_paths):
                norm = tmp_dir / f"norm_{i:03d}.mp4"
                has_audio = self._has_stream(p, "audio")
                dur = self._probe_duration(p) or 1.0

                if has_audio:
                    args = [
                        "-y",
                        "-i", p,
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-pix_fmt", "yuv420p",
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-c:a", "aac", "-ar", "44100", "-ac", "2",
                        str(norm),
                    ]
                else:
                    # Sin audio: silencio de duración EXACTA.
                    # `-t` antes y después en vez de `-shortest`, que con
                    # inputs lavfi se comporta de forma inconsistente en
                    # Windows y termina estirando el clip al doble.
                    args = [
                        "-y",
                        "-i", p,
                        "-f", "lavfi",
                        "-t", f"{dur:.3f}",
                        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                        "-map", "0:v:0",
                        "-map", "1:a:0",
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-pix_fmt", "yuv420p",
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-c:a", "aac", "-ar", "44100", "-ac", "2",
                        "-t", f"{dur:.3f}",
                        str(norm),
                    ]
                run_ffmpeg(args)
                normalized.append(norm)

            list_file = tmp_dir / "list.txt"
            list_file.write_text(
                "\n".join(f"file '{n.name}'" for n in normalized),
                encoding="utf-8",
            )

            run_ffmpeg(
                [
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(list_file),
                    "-c", "copy",
                    "-movflags", "+faststart",
                    str(out),
                ]
            )
        finally:
            # Limpieza defensiva: no dejamos basura en el directorio del
            # proyecto aunque falle la operación.
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def merge_audio(
        self,
        video_path: str,
        audio_path: str,
        out_path: str,
        audio_volume: float = 1.0,
        video_volume: float = 0.0,
        mix: bool = False,
    ) -> None:
        v = Path(video_path)
        a = Path(audio_path)
        if not v.exists():
            raise ValidationError(message="El video no existe.", cause=str(v))
        if not a.exists():
            raise ValidationError(message="El audio no existe.", cause=str(a))

        # Validar streams antes de armar el filtergraph.
        if not self._has_stream(str(v), "video"):
            raise ValidationError(
                message="El archivo de video no contiene pista de video.",
                cause=f"Archivo: {v.name}",
                solution="Subí un video real (MP4/MOV/WebM).",
            )
        if not self._has_stream(str(a), "audio"):
            raise ValidationError(
                message="El archivo de audio no contiene pista de audio.",
                cause=f"Archivo: {a.name}",
                solution="Subí un audio real (MP3/M4A/WAV/OGG), no un video.",
            )

        out = ensure_parent(out_path)
        video_has_audio = self._has_stream(str(v), "audio")

        if mix and not video_has_audio:
            # No hay pista original para mezclar → degradamos a reemplazo.
            mix = False

        if mix:
            filter_complex = (
                f"[0:a]volume={video_volume}[va];"
                f"[1:a]volume={audio_volume}[aa];"
                f"[va][aa]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            run_ffmpeg(
                [
                    "-y",
                    "-i", str(v),
                    "-i", str(a),
                    "-filter_complex", filter_complex,
                    "-map", "0:v?",
                    "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    "-movflags", "+faststart",
                    str(out),
                ]
            )
        else:
            run_ffmpeg(
                [
                    "-y",
                    "-i", str(v),
                    "-i", str(a),
                    "-map", "0:v?",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-filter:a", f"volume={audio_volume}",
                    "-shortest",
                    "-movflags", "+faststart",
                    str(out),
                ]
            )

    def overlay_text(
        self,
        in_path: str,
        out_path: str,
        text: str,
        position: str = "bottom",
        font_size: int = 48,
        color: str = "white",
        box: bool = True,
    ) -> None:
        src = Path(in_path)
        if not src.exists():
            raise ValidationError(message="El video no existe.", cause=str(src))
        if not self._has_stream(str(src), "video"):
            raise ValidationError(
                message="overlay_text requiere un archivo con pista de video.",
                cause=str(src),
            )
        out = ensure_parent(out_path)

        font = self._resolve_font()
        if not font:
            raise ValidationError(
                message="No se encontró una fuente TrueType para overlay_text.",
                cause="Ni Windows Fonts ni DejaVuSans disponibles.",
                solution="Instalá una fuente (arial.ttf) o configurá fontconfig.",
            )

        safe = self._escape_drawtext(text)

        y_map = {
            "top": "h*0.08",
            "center": "(h-text_h)/2",
            "bottom": "h*0.88-text_h",
        }
        y = y_map.get(position, y_map["bottom"])

        # `expansion=none` desactiva el motor de expansión %{...} de drawtext.
        # Sin esto, cualquier '%' suelto genera 'Stray %' (Regla 56: además
        # bloquea inyecciones de tipo %{eif:...} provenientes del usuario/IA).
        draw = (
            f"drawtext=fontfile='{font}':"
            f"expansion=none:"
            f"text='{safe}':"
            f"fontcolor={color}:"
            f"fontsize={font_size}:"
            f"x=(w-text_w)/2:y={y}"
        )
        if box:
            draw += ":box=1:boxcolor=black@0.5:boxborderw=12"

        run_ffmpeg(
            [
                "-y",
                "-i", str(src),
                "-vf", draw,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(out),
            ]
        )

    def resize_and_pad(
        self,
        in_path: str,
        out_path: str,
        width: int,
        height: int,
        background: str = "black",
    ) -> None:
        src = Path(in_path)
        if not src.exists():
            raise ValidationError(message="El video no existe.", cause=str(src))
        if not self._has_stream(str(src), "video"):
            raise ValidationError(
                message="resize_and_pad requiere un archivo con pista de video.",
                cause=str(src),
            )
        out = ensure_parent(out_path)

        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:{background}"
        )
        run_ffmpeg(
            [
                "-y",
                "-i", str(src),
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(out),
            ]
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _has_stream(path: str | Path, kind: str) -> bool:
        """Devuelve True si el archivo tiene al menos un stream del tipo dado."""
        from app.core import ffmpeg

        try:
            info = ffmpeg.probe(Path(path))
        except Exception:
            return False
        return any(
            s.get("codec_type") == kind for s in info.get("streams", [])
        )

    @staticmethod
    def _probe_duration(path: str | Path) -> float | None:
        """Duración en segundos, o None si no se puede determinar."""
        from app.core import ffmpeg

        try:
            return ffmpeg.probe_duration(Path(path))
        except Exception:
            return None

    @staticmethod
    def _resolve_font() -> str | None:
        """Devuelve un fontfile utilizable por drawtext, o None.

        En Windows hay que escapar el ':' de la letra de unidad para que
        el parser de filtros de FFmpeg no lo confunda con un separador.
        """
        candidates: list[Path] = []
        if os.name == "nt":
            windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
            for name in ("arial.ttf", "segoeui.ttf", "calibri.ttf", "tahoma.ttf"):
                candidates.append(windir / "Fonts" / name)
        candidates += [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            Path("/System/Library/Fonts/Helvetica.ttc"),
        ]

        for p in candidates:
            if p.exists():
                # Windows: ':' de la unidad → '\:'; slashes hacia adelante.
                return str(p).replace("\\", "/").replace(":", r"\:")
        return None

    @staticmethod
    def _escape_drawtext(s: str) -> str:
        """Escapado para un solo nivel de parser (sin shell=True).

        Con expansion=none, el '%' no dispara expansión, pero igual lo
        escapamos por consistencia con el parser de filtros.
        """
        return (
            s.replace("\\", "\\\\")
             .replace(":", r"\:")
             .replace("'", r"\'")
             .replace("%", r"\%")
             .replace(",", r"\,")
             .replace("[", r"\[")
             .replace("]", r"\]")
             .replace(";", r"\;")
        )

    # ------------------------------------------------------------------
    # Ejecución de un plan completo
    # ------------------------------------------------------------------

    def execute_plan(self, plan: plan_mod.VideoPlan) -> None:
        """Recorre el plan y ejecuta cada operación en orden.

        Regla 43: el plan es validado por Pydantic; aquí solo se ejecuta.
        """
        plan.validate_chain()
        log.info("Ejecutando plan con %d operaciones", len(plan.operations))

        for i, op in enumerate(plan.operations):
            log.info("Op #%d: %s", i, op.type)
            if isinstance(op, plan_mod.ImageToVideoOp):
                self.image_to_video(
                    op.image_path, op.out_path, op.duration,
                    op.width, op.height, op.fps, op.fit,
                )
            elif isinstance(op, plan_mod.TrimVideoOp):
                self.trim_video(
                    op.in_path, op.out_path, op.start, op.duration, op.reencode,
                )
            elif isinstance(op, plan_mod.ConcatVideosOp):
                self.concat_videos(op.in_paths, op.out_path)
            elif isinstance(op, plan_mod.MergeAudioOp):
                self.merge_audio(
                    op.video_path, op.audio_path, op.out_path,
                    op.audio_volume, op.video_volume, op.mix,
                )
            elif isinstance(op, plan_mod.OverlayTextOp):
                self.overlay_text(
                    op.in_path, op.out_path, op.text,
                    op.position, op.font_size, op.color, op.box,
                )
            elif isinstance(op, plan_mod.ResizeAndPadOp):
                self.resize_and_pad(
                    op.in_path, op.out_path, op.width, op.height, op.background,
                )
            else:
                raise ValidationError(
                    message=f"Operación desconocida: {op.type}",
                )