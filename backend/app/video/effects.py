"""Filtros FFmpeg para cada efecto de la timeline.

Cada función devuelve un fragmento de `-vf` (video filter) o `None`
si no aplica. Los efectos están pensados para ser sutiles
(Regla 14: claridad del producto > efecto visual).
"""
from typing import Optional


# Duración del fade de entrada/salida en transiciones
FADE_DURATION = 0.25


def build_vf(
    effect: str | None,
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> Optional[str]:
    """Devuelve la cadena de filtros `-vf` para el efecto dado.

    `zoompan` funciona mejor con `d=<frames>` y `s=<WxH>`.
    """
    d_frames = max(int(duration * fps), 1)
    w, h = width, height

    if not effect or effect == "none":
        return (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={fps}"
        )

    if effect == "zoom_in":
        # Zoom suave desde 1.0x hasta 1.15x
        return (
            f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
            f"crop={w*2}:{h*2},"
            f"zoompan=z='min(zoom+0.0008,1.15)':d={d_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={w}x{h}:fps={fps}"
        )

    if effect == "zoom_out":
        # Zoom desde 1.15x hasta 1.0x
        return (
            f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
            f"crop={w*2}:{h*2},"
            f"zoompan=z='max(1.15-0.0008*on,1.0)':d={d_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={w}x{h}:fps={fps}"
        )

    if effect in ("pan_left", "pan_right", "pan_up", "pan_down"):
        # Pan: paneo del encuadre sobre una imagen un 15% más grande
        scale_w = int(w * 1.15) // 2 * 2
        scale_h = int(h * 1.15) // 2 * 2
        pan_max = w * 0.15
        pan_max_h = h * 0.15

        if effect == "pan_left":
            x_expr = f"(iw-iw/zoom)/2 - {pan_max/2} + {pan_max}*on/{d_frames}"
            y_expr = "ih/2-(ih/zoom/2)"
        elif effect == "pan_right":
            x_expr = f"(iw-iw/zoom)/2 + {pan_max/2} - {pan_max}*on/{d_frames}"
            y_expr = "ih/2-(ih/zoom/2)"
        elif effect == "pan_up":
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = f"(ih-ih/zoom)/2 - {pan_max_h/2} + {pan_max_h}*on/{d_frames}"
        else:  # pan_down
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = f"(ih-ih/zoom)/2 + {pan_max_h/2} - {pan_max_h}*on/{d_frames}"

        return (
            f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
            f"crop={scale_w}:{scale_h},"
            f"zoompan=z='1.0':d={d_frames}:"
            f"x='{x_expr}':y='{y_expr}':"
            f"s={w}x{h}:fps={fps}"
        )

    if effect == "fade":
        # Fade in/out a negro
        return (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fade=t=in:st=0:d={FADE_DURATION},"
            f"fade=t=out:st={max(duration - FADE_DURATION, 0)}:d={FADE_DURATION},"
            f"fps={fps}"
        )

    # Efecto desconocido → sin filtro adicional
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={fps}"
    )


def is_ken_burns(effect: str | None) -> bool:
    return effect in ("zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down")