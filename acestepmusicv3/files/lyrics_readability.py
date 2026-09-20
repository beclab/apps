"""Classify ACE Chinese lyrics without rewriting model output."""

from __future__ import annotations

import re
import unicodedata


LANGUAGE_TAG = re.compile(r"^\[(?:zh|yue)\]\s*", re.IGNORECASE)
BRACKET_TAG = re.compile(r"\[[^\]\r\n]+\]")
PINYIN_TOKEN = re.compile(r"^[a-züv]+[1-5]$", re.IGNORECASE)
WORD_TOKEN = re.compile(r"[A-Za-züÜvV]+[1-5]?", re.UNICODE)
ENGLISH_HOOK_WORDS = frozenset({"baby", "hey", "i", "la", "love", "na", "oh", "tonight", "woo", "yeah", "you"})


def _is_han(character: str) -> bool:
    value = ord(character)
    return (
        0x3400 <= value <= 0x4DBF
        or 0x4E00 <= value <= 0x9FFF
        or 0xF900 <= value <= 0xFAFF
        or 0x20000 <= value <= 0x323AF
    )


def _is_latin(character: str) -> bool:
    return character.isalpha() and "LATIN" in unicodedata.name(character, "")


def _latin_words(line: str) -> list[str]:
    words: list[str] = []
    current: list[str] = []
    for character in line:
        if _is_latin(character):
            current.append(character)
        elif current:
            words.append("".join(current).lower())
            current = []
    if current:
        words.append("".join(current).lower())
    return words


def _has_disallowed_latin_line(lines: list[str]) -> bool:
    for line in lines:
        words = _latin_words(line)
        if words and (len(words) > 4 or any(word not in ENGLISH_HOOK_WORDS for word in words)):
            return True
    return False


def content_lines(lyrics: str) -> list[str]:
    lines: list[str] = []
    for raw in str(lyrics or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        without_language = LANGUAGE_TAG.sub("", line)
        without_tags = BRACKET_TAG.sub("", without_language).strip()
        if without_tags:
            lines.append(without_tags)
    return lines


def phonetic_kind(lyrics: str, language: str) -> str:
    """Return ``han``, ``phonetic`` or ``invalid`` for Chinese-language text."""
    if language not in {"zh", "yue"}:
        return "han"
    lines = content_lines(lyrics)
    if not lines:
        return "invalid"
    letters = [character for line in lines for character in line if character.isalpha()]
    han = sum(1 for character in letters if _is_han(character))
    words = [token for line in lines for token in WORD_TOKEN.findall(line)]
    toned = sum(1 for token in words if PINYIN_TOKEN.fullmatch(token))
    tagged_lines = sum(
        1 for raw in str(lyrics or "").splitlines() if LANGUAGE_TAG.match(raw.strip())
    )
    if words and toned / len(words) >= 0.70 and tagged_lines >= max(1, len(lines) // 2):
        return "phonetic"
    if han >= 20 and letters and han / len(letters) >= 0.70 and not _has_disallowed_latin_line(lines):
        return "han"
    return "invalid"
