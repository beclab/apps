"""Canonical Olares music API in front of ACE-Step's native async API."""

from __future__ import annotations

import atexit
import base64
import binascii
import hashlib
import json
import math
import mimetypes
import os
import re
import signal
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from lyrics_readability import phonetic_kind


NATIVE_BASE = "http://127.0.0.1:8002"
MODEL_NAME = os.getenv("MODEL_NAME", "ACE-Step/acestep-v15-xl-sft")
QUALITY_MODEL = os.getenv("ACESTEP_CONFIG_PATH", "acestep-v15-xl-sft")
TASKS: dict[str, dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()
REPAINT_INPUT_DIR = os.getenv("REPAINT_INPUT_DIR", "/app/data/repaint-inputs")
LYRICS_ALIGNMENT_DIR = os.getenv("LYRICS_ALIGNMENT_DIR", "/app/data/lyrics-alignments")
ALIGNMENT_AUDIO_ROOTS = ("/app/data", "/app/gradio_outputs")
MAX_ALIGNMENT_BYTES = 1024 * 1024
MAX_REPAINT_AUDIO_BYTES = 64 * 1024 * 1024
CLEAN_NEGATIVE_PROMPT = (
    "background hiss, static, vinyl crackle, tape noise, lo-fi noise, noisy room, "
    "muddy wash, harsh sibilance, brittle cymbals, distorted vocal"
)
VOCAL_LANGUAGES = (
    "ar", "az", "bg", "bn", "ca", "cs", "da", "de", "el", "en", "es", "fa", "fi", "fr", "he", "hi",
    "hr", "ht", "hu", "id", "is", "it", "ja", "ko", "la", "lt", "ms", "ne", "nl", "no", "pa", "pl",
    "pt", "ro", "ru", "sa", "sk", "sr", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "vi",
    "yue", "zh",
)
VOCAL_LANGUAGE_SET = frozenset(VOCAL_LANGUAGES)
ROMANIZED_LINE = re.compile(r"^\[[a-z]{2,3}\]\s")
ENGLISH_HOOK_WORDS = frozenset({"baby", "hey", "i", "la", "love", "na", "oh", "tonight", "woo", "yeah", "you"})
DRAFT_ATTEMPTS = 5


class PhoneticLyricsError(ValueError):
    """ACE returned internal pronunciation codes instead of display lyrics."""


class DraftValidationError(ValueError):
    """ACE returned a draft that cannot be shown as readable lyrics."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

app = FastAPI(title="Olares Music Engine", version="1")


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "request_failed", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _native_json(path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        NATIVE_BASE + path,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise _error(502, "upstream_unavailable", f"ACE-Step native API unavailable: {exc}") from exc
    if not isinstance(parsed, dict) or parsed.get("code", 200) != 200:
        message = parsed.get("error", "ACE-Step request failed") if isinstance(parsed, dict) else "ACE-Step request failed"
        raise _error(502, "upstream_error", str(message))
    return parsed


def _task(task_id: str) -> dict[str, Any]:
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if task is None:
            raise _error(410, "task_lost", "The engine restarted and no longer knows this generation.")
        return dict(task)


def _public(task: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": task["id"],
        "object": "music.generation",
        "status": task["status"],
        "created_at": task["created_at"],
        "model": MODEL_NAME,
        "outputs": task.get("outputs", []),
    }
    if task.get("error"):
        result["error"] = task["error"]
    if task.get("effective_prompt"):
        result["effective_prompt"] = task["effective_prompt"]
    if task.get("effective_lyrics"):
        result["effective_lyrics"] = task["effective_lyrics"]
    if task.get("metas"):
        result["metas"] = task["metas"]
    return result


def _public_draft(task: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": task["id"],
        "object": "music.draft",
        "status": task["status"],
        "created_at": task["created_at"],
        "model": MODEL_NAME,
        "brief": task["brief"],
        "instrumental": task["instrumental"],
        "vocal_language": task["vocal_language"],
        "warnings": task.get("warnings", []),
        "metrics": task.get("metrics", {}),
    }
    for field in ("prompt", "lyrics", "conditioning_lyrics", "duration_seconds", "style_plan"):
        if task.get(field) is not None:
            result[field] = task[field]
    if task.get("error"):
        result["error"] = task["error"]
    return result


def _public_format(task: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": task["id"],
        "object": "music.format",
        "status": task["status"],
        "created_at": task["created_at"],
        "model": MODEL_NAME,
        "draft_prompt": task["draft_prompt"],
        "draft_lyrics": task["draft_lyrics"],
        "vocal_language": task["vocal_language"],
        "warnings": task.get("warnings", []),
        "metrics": task.get("metrics", {}),
    }
    if task.get("effective_prompt") is not None:
        result["effective_prompt"] = task["effective_prompt"]
    if task.get("effective_lyrics") is not None:
        result["effective_lyrics"] = task["effective_lyrics"]
    if task.get("conditioning_lyrics"):
        result["conditioning_lyrics"] = task["conditioning_lyrics"]
    if task.get("error"):
        result["error"] = task["error"]
    return result


def _active_task(kind: str | None = None) -> bool:
    with TASKS_LOCK:
        return any(
            (kind is None or task.get("kind") == kind)
            and task.get("status") not in {"completed", "failed"}
            for task in TASKS.values()
        )


def _has_sung_content(lyrics: str) -> bool:
    """Reject empty/section-only lyrics such as ACE's `[Instrumental]`."""
    return any(
        line and not (line.startswith("[") and line.endswith("]"))
        for line in (raw.strip() for raw in lyrics.splitlines())
    )


def _lyric_content_lines(lyrics: str) -> list[str]:
    return [
        line for line in (raw.strip() for raw in lyrics.splitlines())
        if line and not (line.startswith("[") and line.endswith("]"))
    ]


def _is_han(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x323AF
    )


def _has_expected_chinese_script(lyrics: str, language: str) -> bool:
    if language not in {"zh", "yue"}:
        return True
    letters = [character for line in _lyric_content_lines(lyrics) for character in line if character.isalpha()]
    for line in _lyric_content_lines(lyrics):
        latin_words: list[str] = []
        current: list[str] = []
        for character in line:
            if character.isalpha() and "LATIN" in unicodedata.name(character, ""):
                current.append(character.lower())
            elif current:
                latin_words.append("".join(current))
                current = []
        if current:
            latin_words.append("".join(current))
        if latin_words and (
            len(latin_words) > 4
            or any(word not in ENGLISH_HOOK_WORDS for word in latin_words)
        ):
            return False
    if any(
        0x3040 <= ord(character) <= 0x30FF
        or 0x31F0 <= ord(character) <= 0x31FF
        or 0x1B000 <= ord(character) <= 0x1B16F
        or 0x1100 <= ord(character) <= 0x11FF
        or 0x3130 <= ord(character) <= 0x318F
        or 0xA960 <= ord(character) <= 0xA97F
        or 0xAC00 <= ord(character) <= 0xD7FF
        for character in letters
    ):
        return False
    han = sum(1 for character in letters if _is_han(character))
    return han >= 20 and bool(letters) and han / len(letters) >= 0.70


def _normalized_lyric_value(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _has_extreme_repetition(lyrics: str) -> bool:
    lines = _lyric_content_lines(lyrics)
    for line in lines:
        han = [character for character in line if _is_han(character)]
        if not han:
            continue
        run = 1
        longest_run = 1
        for previous, current in zip(han, han[1:]):
            run = run + 1 if current == previous else 1
            longest_run = max(longest_run, run)
        if longest_run >= 4:
            return True
        if len(han) >= 8 and len(set(han)) / len(han) < 0.35:
            return True
        character_counts = {character: han.count(character) for character in set(han)}
        if len(han) >= 8 and max(character_counts.values()) >= 4 and max(character_counts.values()) / len(han) >= 0.40:
            return True
        if len(han) >= 8:
            bigrams = ["".join(han[index:index + 2]) for index in range(len(han) - 1)]
            bigram_counts = {bigram: bigrams.count(bigram) for bigram in set(bigrams)}
            if bigram_counts and max(bigram_counts.values()) >= 3 and max(bigram_counts.values()) * 2 / len(han) >= 0.50:
                return True
    if len(lines) < 8:
        return False
    counts: dict[str, int] = {}
    maximum = 0
    previous = ""
    consecutive = 0
    for line in lines:
        normalized = _normalized_lyric_value(line)
        if normalized:
            counts[normalized] = counts.get(normalized, 0) + 1
            maximum = max(maximum, counts[normalized])
            if normalized == previous:
                consecutive += 1
            else:
                previous = normalized
                consecutive = 1
            if consecutive >= 4:
                return True
        words = line.split()
        if len(words) >= 8:
            word_counts: dict[str, int] = {}
            for word in words:
                word = _normalized_lyric_value(word)
                if word:
                    word_counts[word] = word_counts.get(word, 0) + 1
            if word_counts and max(word_counts.values()) / len(words) >= 0.60:
                return True
    if not counts:
        return False
    return (
        len(counts) / len(lines) < 0.40
        or (maximum >= 4 and maximum / len(lines) >= 0.40)
    )


def _draft_validation_error(task: dict[str, Any], prompt: str, lyrics: str) -> DraftValidationError | None:
    if not prompt:
        return DraftValidationError("draft_failed", "ACE-Step returned an empty caption")
    if task["instrumental"]:
        return None
    if not _has_sung_content(lyrics):
        return DraftValidationError("draft_failed", "ACE-Step returned no lyrics for a vocal draft")
    if _romanized(lyrics) or not _has_expected_chinese_script(lyrics, task["vocal_language"]):
        return DraftValidationError(
            "lyrics_script_invalid",
            "ACE-Step returned lyrics outside the requested readable writing system",
        )
    if _has_extreme_repetition(lyrics):
        return DraftValidationError(
            "lyrics_repetition_invalid",
            "ACE-Step returned excessively repetitive lyrics",
        )
    if len(lyrics) > 4096:
        return DraftValidationError("draft_failed", "ACE-Step returned lyrics that exceed 4096 characters")
    return None


def _draft_query(task: dict[str, Any], attempt: int) -> str:
    """Pass Music's subject through unchanged on every independent sample."""
    del attempt
    return task["brief"]


def _draft_temperature(initial: float, attempt: int, failure: DraftValidationError | None) -> float:
    del attempt, failure
    return initial


def _draft_candidate_kind(task: dict[str, Any], lyrics: str, failure: DraftValidationError | None) -> str:
    if failure is None:
        return "native_hanzi" if task["vocal_language"] in {"zh", "yue"} else "native_lyrics"
    if phonetic_kind(lyrics, task["vocal_language"]) == "phonetic":
        return "phonetic_rejected"
    if failure.code == "lyrics_repetition_invalid":
        return "repetition_rejected"
    return "invalid_script"


def _line_metrics(lyrics: str, language: str) -> tuple[list[str], dict[str, Any]]:
    lines = [
        line.strip() for line in lyrics.splitlines()
        if line.strip() and not (line.strip().startswith("[") and line.strip().endswith("]"))
    ]
    if not lines:
        return [], {"line_count": 0, "line_length_variation": 0.0, "uniformity_risk": "low", "syntactic_pattern_risk": "low"}
    if language in {"zh", "yue"}:
        counts = [sum(1 for char in line if "\u3400" <= char <= "\u9fff") for line in lines]
    else:
        counts = [len(line.split()) if " " in line else len(line) for line in lines]
    mean = sum(counts) / len(counts)
    variation = 0.0 if mean == 0 else (sum(abs(value - mean) for value in counts) / len(counts)) / mean
    most_common = max(counts.count(value) for value in set(counts)) / len(counts)
    longest_run = 1
    current_run = 1
    for previous, current in zip(counts, counts[1:]):
        if previous == current:
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 1
    risk = "high" if most_common >= 0.7 or longest_run >= 4 else "low"
    warnings = []
    if language in {"zh", "yue"} and risk == "high":
        warnings.append("uniform_chinese_line_lengths")
    if language == "yue":
        warnings.append("cantonese_tone_melody_alignment_requires_listening_review")
    syntactic_risk = "high" if language in {"zh", "yue"} and _repeated_chinese_opening(lyrics) else "low"
    if syntactic_risk == "high":
        warnings.append("repetitive_chinese_line_openings")
    return warnings, {
        "line_count": len(lines),
        "line_length_variation": round(variation, 3),
        "uniformity_risk": risk,
        "syntactic_pattern_risk": syntactic_risk,
    }


def _repeated_chinese_opening(lyrics: str) -> bool:
    previous = ""
    run = 0
    for raw in lyrics.splitlines():
        line = raw.strip()
        if not line or (line.startswith("[") and line.endswith("]")):
            previous, run = "", 0
            continue
        opening = "".join(char for char in line if "\u3400" <= char <= "\u9fff")[:1]
        if opening and opening == previous:
            run += 1
        else:
            previous, run = opening, 1
        if run >= 4:
            return True
    return False


def _fit_caption(caption: str, limit: int = 512) -> tuple[str, bool]:
    """Fit ACE's unconstrained /format_input caption into our API contract."""
    caption = " ".join(caption.split()).strip()
    if len(caption) <= limit:
        return caption, False

    prefix = caption[:limit]
    # Prefer a complete sentence near the end of the available budget. ACE
    # commonly emits 550-700 character prose despite receiving a <=512 input.
    boundaries = [match.end() for match in re.finditer(r"[.!?;](?:\s|$)", prefix)]
    cutoff = max((value for value in boundaries if value >= limit // 2), default=0)
    if not cutoff:
        cutoff = prefix.rfind(" ")
    if cutoff <= 0:
        cutoff = limit
    return prefix[:cutoff].strip(), True


def _run_format_task(task_id: str, temperature: float, duration: int) -> None:
    with TASKS_LOCK:
        task = dict(TASKS[task_id])
        task["status"] = "running"
        TASKS[task_id] = task
    try:
        native = _native_json(
            "/format_input",
            {
                "prompt": task["draft_prompt"],
                "lyrics": task["draft_lyrics"],
                "temperature": temperature,
                "param_obj": json.dumps({
                    "duration": duration,
                    "language": task["vocal_language"],
                }),
            },
            timeout=300,
        )
        data = native.get("data") or {}
        effective_prompt, caption_truncated = _fit_caption(
            str(data.get("caption") or task["draft_prompt"])
        )
        effective_lyrics = str(data.get("lyrics") or task["draft_lyrics"]).strip()
        conditioning_lyrics = str(data.get("conditioning_lyrics") or "").strip()
        if not effective_prompt:
            raise ValueError("ACE-Step returned an invalid formatted caption")
        if len(effective_lyrics) > 4096:
            raise ValueError("ACE-Step returned formatted lyrics that exceed 4096 characters")
        if _romanized(effective_lyrics):
            raise PhoneticLyricsError("ACE-Step returned phonetic codes instead of readable formatted lyrics")
        if conditioning_lyrics and (
            task["vocal_language"] not in {"zh", "yue"}
            or phonetic_kind(conditioning_lyrics, task["vocal_language"]) != "phonetic"
            or len(_lyric_content_lines(conditioning_lyrics)) != len(_lyric_content_lines(effective_lyrics))
        ):
            raise PhoneticLyricsError("ACE-Step returned an invalid internal conditioning lyric")
        warnings, metrics = _line_metrics(effective_lyrics, task["vocal_language"])
        if caption_truncated:
            warnings.insert(0, "formatted_caption_trimmed_to_512_characters")
        task.update({
            "status": "completed",
            "effective_prompt": effective_prompt,
            "effective_lyrics": effective_lyrics,
            "conditioning_lyrics": conditioning_lyrics,
            "warnings": warnings,
            "metrics": metrics,
        })
    except Exception as exc:
        task.update({
            "status": "failed",
            "error": {"code": "lyrics_script_invalid" if isinstance(exc, PhoneticLyricsError) else "format_failed", "message": str(exc)},
        })
    with TASKS_LOCK:
        TASKS[task_id] = task


def _run_draft_task(task_id: str, temperature: float) -> None:
    with TASKS_LOCK:
        task = dict(TASKS[task_id])
        task["status"] = "running"
        TASKS[task_id] = task
    try:
        failure: DraftValidationError | None = None
        for attempt in range(DRAFT_ATTEMPTS):
            attempt_temperature = _draft_temperature(temperature, attempt, failure)
            native = _native_json(
                "/v1/create_sample",
                {
                    # Keep retries on the same positive song subject. The 4B
                    # writer may turn appended correction prose into lyrics.
                    "query": _draft_query(task, attempt),
                    "instrumental": task["instrumental"],
                    "vocal_language": task["vocal_language"],
                    "temperature": attempt_temperature,
                },
                timeout=600,
            )
            data = native.get("data") or {}
            lyrics = "" if task["instrumental"] else str(data.get("lyrics") or "").strip()
            prompt, caption_truncated = _fit_caption(str(data.get("caption") or ""))
            failure = _draft_validation_error(task, prompt, lyrics)
            candidate_kind = _draft_candidate_kind(task, lyrics, failure)
            if failure is None:
                print(
                    f"[draft-quality] attempt={attempt + 1} result={candidate_kind} "
                    f"temperature={attempt_temperature:.2f}",
                    flush=True,
                )
                break
            print(
                f"[draft-quality] attempt={attempt + 1} result={candidate_kind} "
                f"temperature={attempt_temperature:.2f}",
                flush=True,
            )
        if failure is not None:
            raise failure
        warnings, metrics = _line_metrics(lyrics, task["vocal_language"])
        if caption_truncated:
            warnings.insert(0, "caption_trimmed_to_512_characters")
        task.update({
            "status": "completed",
            "prompt": prompt,
            "lyrics": lyrics,
            "duration_seconds": _draft_duration(data.get("duration")),
            "style_plan": _draft_style_plan(data),
            "warnings": warnings,
            "metrics": metrics,
        })
    except Exception as exc:
        task.update({
            "status": "failed",
            "error": {
                "code": exc.code if isinstance(exc, DraftValidationError) else "draft_failed",
                "message": str(exc),
            },
        })
    with TASKS_LOCK:
        TASKS[task_id] = task


def _romanized(lyrics: str) -> bool:
    """Report ACE's phonetic lyric encoding, `[zh] ye4 se4 luo4 ...`.

    It is valid input for generation but not something a listener can read or
    edit, and it lands in the field an application shows as the lyrics. Which
    of the two forms the LM picks for the same request varies between calls.
    """
    return any(ROMANIZED_LINE.match(line.strip()) for line in lyrics.splitlines())


def _draft_duration(value: Any) -> int | None:
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return None
    return min(600, max(10, seconds))


def _draft_style_plan(data: dict[str, Any]) -> dict[str, Any]:
    """Carry the LM's own metadata in the shape the generation call accepts.

    create_sample spells the key signature `keyscale`; every other surface in
    this API spells it `key_scale`.
    """
    plan: dict[str, Any] = {}
    bpm = data.get("bpm")
    if isinstance(bpm, (int, float)) and 30 <= bpm <= 300:
        plan["bpm"] = int(bpm)
    for source, target in (("keyscale", "key_scale"), ("timesignature", "time_signature")):
        value = str(data.get(source) or "").strip()
        if value:
            plan[target] = value
    return plan


def _options(source: dict[str, Any]) -> dict[str, Any]:
    value = source.get("provider_options") or {}
    if not isinstance(value, dict):
        raise _error(400, "invalid_provider_options", "provider_options must be an object.")
    allowed = {
        "quality_profile", "bpm", "guidance_scale", "key_scale",
        "time_signature", "vocal_language", "vocal_type", "section_structure",
        "production_profile", "caption_mode",
        "conditioning_lyrics",
        "repaint_start_seconds", "repaint_end_seconds", "repaint_mode", "repaint_strength",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise _error(400, "unknown_provider_option", f"Unsupported provider option: {unknown[0]}.")
    return value


def _number(options: dict[str, Any], key: str, minimum: float, maximum: float) -> float | None:
    if key not in options or options[key] in (None, ""):
        return None
    try:
        value = float(options[key])
    except (TypeError, ValueError) as exc:
        raise _error(400, f"invalid_{key}", f"{key} must be a number.") from exc
    if value < minimum or value > maximum:
        raise _error(400, f"invalid_{key}", f"{key} must be between {minimum:g} and {maximum:g}.")
    return value


def _described_prompt(prompt: str, options: dict[str, Any]) -> str:
    additions = []
    vocal_type = str(options.get("vocal_type", "")).strip()
    if vocal_type:
        additions.append(f"Vocal character: {vocal_type}")
    if options.get("production_profile", "clean") == "clean":
        additions.append(
            "Production: clean studio recording, low noise floor, clear lead vocal, "
            "separated instruments, controlled sibilance, polished master"
        )
    described = prompt
    for addition in additions:
        candidate = f"{described}. {addition}"
        if len(candidate) <= 512:
            described = candidate
    return described


def _decode_repaint_audio(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("data:audio/") or ";base64," not in value[:128]:
        raise _error(400, "invalid_input_audio", "input_audio must be a base64 audio data URL.")
    header, encoded = value.split(",", 1)
    subtype = header[11:].split(";", 1)[0].lower()
    suffix = {"wav": "wav", "wave": "wav", "x-wav": "wav", "mpeg": "mp3", "mp3": "mp3", "flac": "flac", "ogg": "ogg"}.get(subtype)
    if suffix is None:
        raise _error(415, "unsupported_input_audio", "Repaint input must be WAV, MP3, FLAC, or OGG.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise _error(400, "invalid_input_audio", "input_audio contains invalid base64 data.") from exc
    if not raw or len(raw) > MAX_REPAINT_AUDIO_BYTES:
        raise _error(413, "input_audio_too_large", "Repaint input audio must be between 1 byte and 64 MiB.")
    os.makedirs(REPAINT_INPUT_DIR, mode=0o750, exist_ok=True)
    path = os.path.join(REPAINT_INPUT_DIR, f"{uuid.uuid4().hex}.{suffix}")
    with open(path, "xb") as output:
        output.write(raw)
    return path


def _cleanup_source(task: dict[str, Any]) -> None:
    path = task.pop("source_path", "")
    if path:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _alignment_path(task_id: str) -> str:
    key = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
    return os.path.join(LYRICS_ALIGNMENT_DIR, key + ".json")


def _validate_alignment(value: Any, duration: float | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("segments"), list):
        raise ValueError("alignment must contain a segments array")
    raw_segments = value["segments"]
    if not raw_segments or len(raw_segments) > 4096:
        raise ValueError("alignment segments must be bounded and non-empty")
    segments: list[dict[str, Any]] = []
    previous_end = 0.0
    maximum = float(duration or 0)
    for index, raw in enumerate(raw_segments):
        if not isinstance(raw, dict):
            raise ValueError(f"alignment segment {index} is not an object")
        text = str(raw.get("text") or "").strip()
        start = float(raw.get("start_seconds"))
        end = float(raw.get("end_seconds"))
        if not text or not math.isfinite(start) or not math.isfinite(end):
            raise ValueError(f"alignment segment {index} has invalid values")
        if start < 0 or end <= start or start < previous_end:
            raise ValueError(f"alignment segment {index} is not monotonic")
        if maximum > 0 and end > maximum + 0.05:
            raise ValueError(f"alignment segment {index} exceeds audio duration")
        segments.append({"text": text, "start_seconds": start, "end_seconds": min(end, maximum) if maximum > 0 else end})
        previous_end = end
    return {"segments": segments}


def _persist_alignment(task_id: str, file_url: str, duration: float) -> bool:
    parsed = urllib.parse.urlparse(file_url)
    if parsed.path != "/v1/audio":
        return False
    source = urllib.parse.parse_qs(parsed.query).get("path", [""])[0]
    source = os.path.realpath(source)
    if not source or not any(
        source == os.path.realpath(root) or source.startswith(os.path.realpath(root) + os.sep)
        for root in ALIGNMENT_AUDIO_ROOTS
    ):
        return False
    sidecar = source + ".lyrics-alignment.json"
    try:
        if os.path.getsize(sidecar) > MAX_ALIGNMENT_BYTES:
            raise ValueError("alignment sidecar exceeds size limit")
        with open(sidecar, "r", encoding="utf-8") as handle:
            alignment = _validate_alignment(json.load(handle), duration)
        with TASKS_LOCK:
            task = dict(TASKS.get(task_id) or {})
        if task.get("conditioning_lyrics"):
            readable_lines = _lyric_content_lines(str(task.get("display_lyrics") or ""))
            if len(readable_lines) != len(alignment["segments"]):
                raise ValueError("readable lyrics do not match alignment segment count")
            for segment, readable in zip(alignment["segments"], readable_lines):
                segment["text"] = readable
        destination = _alignment_path(task_id)
        os.makedirs(os.path.dirname(destination), mode=0o750, exist_ok=True)
        temporary = destination + "." + uuid.uuid4().hex + ".tmp"
        with open(temporary, "x", encoding="utf-8") as handle:
            json.dump(alignment, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        return True
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"[lyrics-alignment] unavailable task_id={task_id} error={exc}", flush=True)
        return False


@app.get("/v1/models")
def models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [{"id": MODEL_NAME, "object": "model", "owned_by": "ACE-Step"}],
    }


@app.get("/api/engine-spec")
def engine_spec() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "model": MODEL_NAME,
        "mode": "music_generation",
        "implements": ["music.generate", "music.repaint", "music.format", "music.draft", "music.lyrics_alignment"],
        "declares": ["music.generate", "music.repaint", "music.format", "music.draft", "music.lyrics_alignment"],
        "serves": ["music.generate", "music.repaint", "music.format", "music.draft", "music.lyrics_alignment"],
        "max_concurrency": 1,
        "workers": 1,
        "extensions": {
            "creative": {
                "media": "music",
                "operations": ["generate", "repaint", "format", "draft"],
            },
            "music": {
                "quality_profiles": ["quality", "high_quality"],
                "default_quality_profile": "high_quality",
                "production_profiles": ["clean", "textured"],
                "default_production_profile": "clean",
                "caption_modes": ["preserve", "enhance"],
                "default_caption_mode": "preserve",
                "vocal_languages": list(VOCAL_LANGUAGES),
                "music_controls": ["bpm", "key_scale", "time_signature", "vocal_language", "vocal_type", "section_structure", "production_profile", "caption_mode"],
            }
        },
        "endpoints": [
            {"method": "GET", "path": "/v1/models", "available": True},
            {"method": "POST", "path": "/v1/music/generations", "available": True, "async_supported": True},
            {"method": "GET", "path": "/v1/music/generations/{id}", "available": True, "async_supported": True},
            {"method": "GET", "path": "/v1/music/generations/{id}/content", "available": True},
            {"method": "GET", "path": "/v1/music/generations/{id}/lyrics-alignment", "available": True},
            {"method": "DELETE", "path": "/v1/music/generations/{id}", "available": True},
            {"method": "POST", "path": "/v1/music/formats", "available": True, "async_supported": True},
            {"method": "GET", "path": "/v1/music/formats/{id}", "available": True, "async_supported": True},
            {"method": "POST", "path": "/v1/music/drafts", "available": True, "async_supported": True},
            {"method": "GET", "path": "/v1/music/drafts/{id}", "available": True, "async_supported": True},
        ],
    }


@app.post("/v1/music/drafts", status_code=202)
async def create_draft(request: Request) -> dict[str, Any]:
    try:
        source = await request.json()
    except json.JSONDecodeError as exc:
        raise _error(400, "invalid_json", "Request body must be JSON.") from exc
    allowed = {"model", "brief", "vocal_language", "instrumental", "temperature"}
    unknown = sorted(set(source) - allowed)
    if unknown:
        raise _error(400, "unknown_field", f"Unsupported draft field: {unknown[0]}.")
    brief = str(source.get("brief", "")).strip()
    instrumental = bool(source.get("instrumental", False))
    language = str(source.get("vocal_language", "")).strip().lower()
    try:
        temperature = float(source.get("temperature", 0.85))
    except (TypeError, ValueError) as exc:
        raise _error(400, "invalid_draft_request", "temperature must be a number.") from exc
    if not brief or len(brief) > 512:
        raise _error(400, "invalid_brief", "brief must contain 1-512 characters.")
    if instrumental:
        if language and language != "unknown":
            raise _error(400, "invalid_vocal_language", "vocal_language must be unknown for instrumental music.")
        language = "unknown"
    elif language not in VOCAL_LANGUAGE_SET:
        raise _error(400, "invalid_vocal_language", "vocal_language must be a supported ACE-Step language code.")
    if temperature < 0 or temperature > 2:
        raise _error(400, "invalid_temperature", "temperature must be between 0 and 2.")
    if _active_task():
        raise _error(409, "model_task_in_progress", "Another ACE-Step model task is already running.")
    task_id = "dft_" + uuid.uuid4().hex
    task = {
        "id": task_id,
        "kind": "draft",
        "status": "queued",
        "created_at": int(time.time()),
        "brief": brief,
        "instrumental": instrumental,
        "vocal_language": language,
        "warnings": [],
        "metrics": {},
    }
    with TASKS_LOCK:
        TASKS[task_id] = task
    threading.Thread(target=_run_draft_task, args=(task_id, temperature), daemon=True).start()
    return _public_draft(task)


@app.get("/v1/music/drafts/{task_id}")
def get_draft(task_id: str) -> dict[str, Any]:
    task = _task(task_id)
    if task.get("kind") != "draft":
        raise _error(404, "draft_not_found", "The requested draft task does not exist.")
    return _public_draft(task)


@app.post("/v1/music/formats", status_code=202)
async def create_format(request: Request) -> dict[str, Any]:
    try:
        source = await request.json()
    except json.JSONDecodeError as exc:
        raise _error(400, "invalid_json", "Request body must be JSON.") from exc
    allowed = {"model", "prompt", "lyrics", "vocal_language", "duration_seconds", "temperature"}
    unknown = sorted(set(source) - allowed)
    if unknown:
        raise _error(400, "unknown_field", f"Unsupported format field: {unknown[0]}.")
    prompt = str(source.get("prompt", "")).strip()
    lyrics = str(source.get("lyrics", "")).strip()
    language = str(source.get("vocal_language", "")).strip().lower()
    try:
        duration = int(source.get("duration_seconds", 240))
        temperature = float(source.get("temperature", 0.85))
    except (TypeError, ValueError) as exc:
        raise _error(400, "invalid_format_request", "duration_seconds and temperature must be numbers.") from exc
    if not prompt or len(prompt) > 512:
        raise _error(400, "invalid_prompt", "prompt must contain 1-512 characters.")
    if not lyrics or len(lyrics) > 4096:
        raise _error(400, "invalid_lyrics", "lyrics must contain 1-4096 characters.")
    if language not in VOCAL_LANGUAGE_SET:
        raise _error(400, "invalid_vocal_language", "vocal_language must be a supported ACE-Step language code.")
    if duration < 10 or duration > 600:
        raise _error(400, "invalid_duration", "duration_seconds must be between 10 and 600.")
    if temperature < 0 or temperature > 2:
        raise _error(400, "invalid_temperature", "temperature must be between 0 and 2.")
    if _active_task():
        raise _error(409, "model_task_in_progress", "Another ACE-Step model task is already running.")
    task_id = "fmt_" + uuid.uuid4().hex
    task = {
        "id": task_id,
        "kind": "format",
        "status": "queued",
        "created_at": int(time.time()),
        "draft_prompt": prompt,
        "draft_lyrics": lyrics,
        "vocal_language": language,
        "warnings": [],
        "metrics": {},
    }
    with TASKS_LOCK:
        TASKS[task_id] = task
    threading.Thread(target=_run_format_task, args=(task_id, temperature, duration), daemon=True).start()
    return _public_format(task)


@app.get("/v1/music/formats/{task_id}")
def get_format(task_id: str) -> dict[str, Any]:
    task = _task(task_id)
    if task.get("kind") != "format":
        raise _error(404, "format_not_found", "The requested format task does not exist.")
    return _public_format(task)


@app.post("/v1/music/generations", status_code=202)
async def create_generation(request: Request) -> dict[str, Any]:
    try:
        source = await request.json()
    except json.JSONDecodeError as exc:
        raise _error(400, "invalid_json", "Request body must be JSON.") from exc
    prompt = str(source.get("prompt", "")).strip()
    lyrics = str(source.get("lyrics", "")).strip()
    instrumental = bool(source.get("instrumental", False))
    duration = int(source.get("duration_seconds", 240))
    options = _options(source)
    profile = str(options.get("quality_profile", "high_quality")).strip().lower()
    if profile not in {"quality", "high_quality"}:
        raise _error(400, "invalid_quality_profile", "quality_profile must be quality or high_quality.")
    bpm = _number(options, "bpm", 30, 300)
    guidance = _number(options, "guidance_scale", 7, 9)
    production_profile = str(options.get("production_profile", "clean")).strip().lower()
    caption_mode = str(options.get("caption_mode", "preserve")).strip().lower()
    if production_profile not in {"clean", "textured"}:
        raise _error(400, "invalid_production_profile", "production_profile must be clean or textured.")
    if caption_mode not in {"preserve", "enhance"}:
        raise _error(400, "invalid_caption_mode", "caption_mode must be preserve or enhance.")
    key_scale = str(options.get("key_scale", "")).strip()
    time_signature = str(options.get("time_signature", "")).strip()
    vocal_language = str(options.get("vocal_language", "")).strip().lower()
    conditioning_lyrics = str(options.get("conditioning_lyrics", "") or "").strip()
    if time_signature and time_signature not in {"2", "3", "4", "6"}:
        raise _error(400, "invalid_time_signature", "time_signature must be 2, 3, 4, or 6.")
    vocal_type = str(options.get("vocal_type", "")).strip()
    if len(key_scale) > 40 or len(vocal_language) > 16 or len(vocal_type) > 120:
        raise _error(400, "invalid_provider_options", "Music control text is too long.")
    if vocal_language and vocal_language not in VOCAL_LANGUAGE_SET and not (instrumental and vocal_language == "unknown"):
        raise _error(400, "invalid_vocal_language", "vocal_language must be a supported ACE-Step language code.")
    if not prompt or len(prompt) > 512:
        raise _error(400, "invalid_prompt", "prompt must contain 1-512 characters.")
    if len(lyrics) > 4096:
        raise _error(400, "invalid_lyrics", "lyrics must contain at most 4096 characters.")
    if instrumental and lyrics:
        raise _error(400, "lyrics_not_allowed", "lyrics must be empty for instrumental music.")
    if conditioning_lyrics:
        if instrumental or vocal_language not in {"zh", "yue"}:
            raise _error(400, "invalid_conditioning_lyrics", "conditioning_lyrics is only valid for Chinese vocal music.")
        if len(conditioning_lyrics) > 4096 or phonetic_kind(conditioning_lyrics, vocal_language) != "phonetic":
            raise _error(400, "invalid_conditioning_lyrics", "conditioning_lyrics must be an ACE phonetic lyric script.")
        if len(_lyric_content_lines(conditioning_lyrics)) != len(_lyric_content_lines(lyrics)):
            raise _error(400, "invalid_conditioning_lyrics", "conditioning_lyrics must match the readable lyric line count.")
    if duration < 10 or duration > 600:
        raise _error(400, "invalid_duration", "duration_seconds must be between 10 and 600.")

    operation = str(source.get("operation", "generate")).strip().lower()
    if operation not in {"generate", "repaint"}:
        raise _error(400, "invalid_operation", "operation must be generate or repaint.")
    source_path = ""
    if operation == "repaint":
        source_path = _decode_repaint_audio(source.get("input_audio"))
        start = _number(options, "repaint_start_seconds", 0, duration)
        end = _number(options, "repaint_end_seconds", 0, duration)
        repaint_mode = str(options.get("repaint_mode", "balanced")).strip().lower()
        if start is None or end is None or end <= start:
            os.remove(source_path)
            raise _error(400, "invalid_repaint_range", "repaint_end_seconds must be greater than repaint_start_seconds.")
        if repaint_mode not in {"conservative", "balanced", "aggressive"}:
            os.remove(source_path)
            raise _error(400, "invalid_repaint_mode", "repaint_mode must be conservative, balanced, or aggressive.")
    native = {
        "prompt": _described_prompt(prompt, options),
        "lyrics": "" if instrumental else (conditioning_lyrics or lyrics),
        "thinking": True,
        "use_format": False,
        "use_cot_caption": caption_mode == "enhance",
        "use_cot_lyrics": False,
        "audio_format": "wav",
        "audio_duration": duration,
        "batch_size": 1,
        "model": QUALITY_MODEL,
        "task_type": "repaint" if operation == "repaint" else "text2music",
        "inference_steps": 64 if profile == "high_quality" else 50,
        "use_adg": profile == "high_quality",
        "guidance_scale": guidance if guidance is not None else (8.0 if profile == "high_quality" else 7.0),
        "shift": 3.0 if profile == "high_quality" else 1.0,
        "infer_method": "ode",
    }
    if production_profile == "clean":
        native["lm_negative_prompt"] = CLEAN_NEGATIVE_PROMPT
    if bpm is not None:
        native["bpm"] = int(bpm)
    if key_scale:
        native["key_scale"] = key_scale
    if time_signature:
        native["time_signature"] = time_signature
    if vocal_language:
        native["vocal_language"] = vocal_language
    if operation == "repaint":
        native["src_audio_path"] = source_path
        native["repainting_start"] = start
        native["repainting_end"] = end
        native["repaint_mode"] = repaint_mode
        strength = _number(options, "repaint_strength", 0, 1)
        native["repaint_strength"] = strength if strength is not None else 0.5
    if "seed" in source:
        native["seed"] = int(source["seed"])
        native["use_random_seed"] = False
    else:
        native["use_random_seed"] = True
    if _active_task():
        raise _error(409, "model_task_in_progress", "Another ACE-Step model task is already running.")
    try:
        released = _native_json("/release_task", native)
    except Exception:
        if source_path:
            os.remove(source_path)
        raise
    data = released.get("data") or {}
    task_id = str(data.get("task_id", ""))
    if not task_id:
        raise _error(502, "invalid_upstream_response", "ACE-Step did not return a task ID.")
    task = {
        "id": task_id,
        "kind": "generation",
        "status": "queued",
        "created_at": int(time.time()),
        "outputs": [],
        "native_outputs": {},
        "source_path": source_path,
        "display_lyrics": lyrics,
        "conditioning_lyrics": conditioning_lyrics,
    }
    with TASKS_LOCK:
        TASKS[task_id] = task
    return _public(task)


def _decode_native_outputs(task_id: str, value: Any) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise _error(502, "invalid_upstream_response", "ACE-Step returned malformed result JSON.") from exc
    rows = value if isinstance(value, list) else []
    outputs: list[dict[str, Any]] = []
    native: dict[str, str] = {}
    effective: dict[str, Any] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("file"):
            continue
        output_id = "out_" + hashlib.sha256(f"{task_id}:{index}".encode()).hexdigest()[:16]
        file_url = str(row["file"])
        suffix = urllib.parse.urlparse(file_url).path.rsplit(".", 1)[-1].lower()
        content_type = mimetypes.types_map.get("." + suffix, "audio/wav")
        metas = row.get("metas") if isinstance(row.get("metas"), dict) else {}
        if not effective:
            with TASKS_LOCK:
                display_lyrics = str((TASKS.get(task_id) or {}).get("display_lyrics") or "").strip()
            effective = {
                "effective_prompt": str(row.get("prompt") or "").strip(),
                "effective_lyrics": display_lyrics or str(row.get("lyrics") or "").strip(),
                "metas": metas,
            }
        outputs.append(
            {
                "id": output_id,
                "content_type": content_type,
                "duration_seconds": float(metas.get("duration") or 0),
                "content_url": f"/v1/music/generations/{task_id}/content?output_id={output_id}",
            }
        )
        native[output_id] = file_url
        if len(outputs) == 1:
            _persist_alignment(task_id, file_url, float(metas.get("duration") or 0))
    return outputs, native, effective


@app.get("/v1/music/generations/{task_id}")
def get_generation(task_id: str) -> dict[str, Any]:
    task = _task(task_id)
    if task["status"] not in {"completed", "failed"}:
        queried = _native_json("/query_result", {"task_id_list": [task_id]})
        rows = queried.get("data") or []
        row = rows[0] if isinstance(rows, list) and rows else {}
        native_status = int(row.get("status", 0)) if isinstance(row, dict) else 0
        if native_status == 1:
            outputs, native_outputs, effective = _decode_native_outputs(task_id, row.get("result"))
            task["status"] = "completed"
            task["outputs"] = outputs
            task["native_outputs"] = native_outputs
            task.update(effective)
            _cleanup_source(task)
        elif native_status == 2:
            task["status"] = "failed"
            task["error"] = {"code": "generation_failed", "message": str(row.get("error") or "ACE-Step generation failed.")}
            _cleanup_source(task)
        else:
            task["status"] = "running"
        with TASKS_LOCK:
            TASKS[task_id] = task
    return _public(task)


@app.delete("/v1/music/generations/{task_id}")
def delete_generation(task_id: str) -> Response:
    _task(task_id)
    raise _error(422, "cancellation_unsupported", "ACE-Step cannot reliably interrupt a running generation.")


@app.get("/v1/music/generations/{task_id}/content")
def generation_content(task_id: str, output_id: str = Query(...)) -> StreamingResponse:
    task = _task(task_id)
    if task["status"] != "completed":
        raise _error(409, "generation_not_completed", "Audio is available only after completion.")
    native_url = task.get("native_outputs", {}).get(output_id)
    if not native_url:
        raise _error(404, "output_not_found", "The requested output does not exist.")
    parsed = urllib.parse.urlparse(native_url)
    if parsed.path != "/v1/audio":
        raise _error(502, "invalid_upstream_response", "ACE-Step returned an unsupported output URL.")
    upstream = urllib.request.urlopen(NATIVE_BASE + parsed.path + "?" + parsed.query, timeout=60)
    content_type = upstream.headers.get_content_type() or "audio/wav"
    return StreamingResponse(upstream, media_type=content_type)


@app.get("/v1/music/generations/{task_id}/lyrics-alignment")
def generation_lyrics_alignment(task_id: str) -> dict[str, Any]:
    with TASKS_LOCK:
        task = dict(TASKS[task_id]) if task_id in TASKS else None
    if task is not None and task.get("status") != "completed":
        raise _error(409, "lyrics_alignment_unavailable", "Lyrics alignment is available only after generation completes.")
    path = _alignment_path(task_id)
    try:
        if os.path.getsize(path) > MAX_ALIGNMENT_BYTES:
            raise ValueError("persisted alignment exceeds size limit")
        with open(path, "r", encoding="utf-8") as handle:
            return _validate_alignment(json.load(handle))
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
        raise _error(404, "lyrics_alignment_unavailable", "Lyrics alignment is unavailable for this generation.")


def _wait_native(process: subprocess.Popen[Any], timeout: int = 1800) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"ACE-Step native API exited with status {process.returncode}")
        try:
            with urllib.request.urlopen(NATIVE_BASE + "/health", timeout=5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(5)
    raise RuntimeError("timed out waiting for ACE-Step native API")


def main() -> None:
    native = subprocess.Popen(
        [sys.executable, "/opt/olares/staged_api.py", "--host", "127.0.0.1", "--port", "8002"],
        start_new_session=False,
    )

    def stop_native() -> None:
        if native.poll() is None:
            native.send_signal(signal.SIGTERM)
            try:
                native.wait(timeout=30)
            except subprocess.TimeoutExpired:
                native.kill()

    atexit.register(stop_native)
    _wait_native(native)
    uvicorn.run(app, host="0.0.0.0", port=8001, workers=1)


if __name__ == "__main__":
    main()
