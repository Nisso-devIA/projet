"""Met un message au même format pour comparer des mots entiers, malgré le contournement."""

from __future__ import annotations

import re
import unicodedata

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s"})


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold().translate(LEET)


def _collapse_repeats(token: str) -> str:
    collapsed = []
    for char in token:
        if not collapsed or collapsed[-1] != char:
            collapsed.append(char)
    return "".join(collapsed)


def normalize_text(text: str) -> str:
    """Minuscules, sans accent, leetspeak, lettres séparées recollées, répétitions réduites."""
    spaced = re.sub(r"[^a-z0-9]+", " ", fold(text))
    tokens = spaced.split()
    merged: list[str] = []
    singles: list[str] = []

    def flush() -> None:
        if len(singles) >= 2:
            merged.append("".join(singles))
        else:
            merged.extend(singles)
        singles.clear()

    for token in tokens:
        if len(token) == 1:
            singles.append(token)
            continue
        flush()
        merged.append(token)
    flush()
    return " ".join(_strip_plural(_collapse_repeats(token)) for token in merged)


def _strip_plural(token: str) -> str:
    if len(token) >= 5 and token.endswith("s"):
        return token[:-1]
    return token


def contains_term(text: str, term: str) -> bool:
    haystack = normalize_text(text)
    needle = normalize_text(term)
    if not needle:
        return False
    if " " in needle:
        return f" {needle} " in f" {haystack} "
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def contains_any(text: str, terms: list[str]) -> bool:
    return any(contains_term(text, term) for term in terms)
