"""Pure helpers for converting ACE-Step's native LRC into API segments."""

from __future__ import annotations

import math
import re
from typing import Any


LRC_LINE = re.compile(r"^\[(\d{1,3}):(\d{2}(?:\.\d{1,3})?)\](.*)$")


def alignment_segments(lrc_text: str, total_duration: float) -> dict[str, list[dict[str, Any]]]:
    """Convert native LRC to a non-empty, strictly monotonic sentence timeline."""
    duration = float(total_duration)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("audio duration must be finite and positive")
    groups: list[tuple[float, list[str]]] = []
    for raw_line in str(lrc_text or "").splitlines():
        match = LRC_LINE.match(raw_line.strip())
        if match is None:
            continue
        text = match.group(3).strip()
        if not text or (text.startswith("[") and text.endswith("]")):
            continue
        start = int(match.group(1)) * 60.0 + float(match.group(2))
        if not math.isfinite(start) or start < 0 or start >= duration:
            raise ValueError("native LRC contains an out-of-range timestamp")
        if groups and start < groups[-1][0]:
            raise ValueError("native LRC timestamps are not monotonic")
        if groups and start == groups[-1][0]:
            # The native aligner rounds LRC timestamps and can assign adjacent
            # sung lines the same start. Keep every sentence, then divide the
            # interval up to the next distinct timestamp below.
            groups[-1][1].append(text)
        else:
            groups.append((start, [text]))
    if not groups:
        raise ValueError("native LRC contains no sung lines")
    segments: list[dict[str, Any]] = []
    for index, (start, texts) in enumerate(groups):
        end = groups[index + 1][0] if index + 1 < len(groups) else duration
        if end <= start:
            raise ValueError("native LRC contains an empty time range")
        width = (end - start) / len(texts)
        for text_index, text in enumerate(texts):
            segment_start = start + width * text_index
            segment_end = end if text_index + 1 == len(texts) else start + width * (text_index + 1)
            segments.append(
                {"text": text, "start_seconds": segment_start, "end_seconds": min(segment_end, duration)}
            )
    return {"segments": segments}
