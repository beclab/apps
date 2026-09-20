"""Cheap structural checks for ACE-Step 5 Hz language-model audio codes."""

from __future__ import annotations

import re
from typing import Any, NamedTuple


_CODE = re.compile(r"<\|audio_code_(\d+)\|>")


class Assessment(NamedTuple):
    accepted: bool
    summary: str


def _strings(result: dict[str, Any]) -> list[str]:
    value = result.get("audio_codes", "")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item if isinstance(item, str) else "" for item in value]
    return [""]


def _longest_run(values: list[int]) -> int:
    longest = current = 0
    previous: int | None = None
    for value in values:
        current = current + 1 if value == previous else 1
        previous = value
        longest = max(longest, current)
    return longest


def assess_audio_codes(result: dict[str, Any], target_duration: Any) -> Assessment:
    """Catch truncated and collapsed plans without judging musical taste."""
    if not result.get("success", False):
        return Assessment(True, "upstream LM failure")
    try:
        duration = float(target_duration or 0)
    except (TypeError, ValueError):
        duration = 0
    expected = int(duration * 5) if duration > 0 else 0
    summaries: list[str] = []
    for index, text in enumerate(_strings(result)):
        codes = [int(value) for value in _CODE.findall(text)]
        count = len(codes)
        unique = len(set(codes))
        unique_ratio = unique / count if count else 0
        longest = _longest_run(codes)
        minimum = max(40, int(expected * 0.72)) if expected else 40
        accepted = count >= minimum and unique_ratio >= 0.08 and longest <= 32
        summaries.append(
            f"sample={index} codes={count}/{expected or '?'} "
            f"unique={unique_ratio:.3f} longest_run={longest}"
        )
        if not accepted:
            return Assessment(False, "; ".join(summaries))
    return Assessment(True, "; ".join(summaries))


def retry_seeds(value: Any, attempt: int) -> list[int] | None:
    """Return stable alternate LM seeds while preserving reproducible retries."""
    if value is None:
        return None
    seeds = value if isinstance(value, list) else [value]
    offset = 1_000_003 * max(1, attempt)
    try:
        return [(int(seed) + offset) % (2**32) for seed in seeds]
    except (TypeError, ValueError):
        return None
