"""Utilidades para SRT (SubRip).

Formato:
    1
    00:00:00,000 --> 00:00:03,500
    Texto del subtítulo

    2
    ...
"""
from dataclasses import dataclass


@dataclass
class SubtitleSegment:
    index: int
    start: float  # segundos
    end: float
    text: str


def _fmt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_time(s: str) -> float:
    # "00:00:03,500"
    hms, ms = s.split(",")
    h, m, sec = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def segments_to_srt(segments: list[SubtitleSegment]) -> str:
    blocks: list[str] = []
    for i, seg in enumerate(segments, start=1):
        blocks.append(
            f"{i}\n"
            f"{_fmt_time(seg.start)} --> {_fmt_time(seg.end)}\n"
            f"{seg.text.strip()}\n"
        )
    return "\n".join(blocks)


def srt_to_segments(content: str) -> list[SubtitleSegment]:
    """Parsea un SRT. Tolera saltos de línea Windows/Linux."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [b for b in content.split("\n\n") if b.strip()]
    segments: list[SubtitleSegment] = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        try:
            idx = int(lines[0].strip())
            times = lines[1]
            start_s, end_s = [t.strip() for t in times.split("-->")]
            text = "\n".join(lines[2:]).strip()
            segments.append(
                SubtitleSegment(
                    index=idx,
                    start=_parse_time(start_s),
                    end=_parse_time(end_s),
                    text=text,
                )
            )
        except (ValueError, IndexError):
            continue
    return segments