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


def spaced_letter_variants(text: str) -> list[str]:
    """Suites de 3 lettres isolées ou plus, plus la même suite moins une lettre.

    Les mots normaux ne sont pas découpés. On retire d'abord une lettre dont la
    casse diffère des autres, puis n'importe quelle lettre.
    """
    pieces = re.findall(r"[A-Za-z0-9]+|[^A-Za-z0-9]+", text or "")
    variants: list[str] = []
    run: list[str] = []
    separated = False

    def flush() -> None:
        if len(run) >= 3:
            folded = [fold(char) for char in run]
            variants.append("".join(folded))
            uppers = sum(char.isupper() for char in run)
            majority_upper = uppers >= len(run) - uppers
            odd = [index for index, char in enumerate(run) if char.isupper() != majority_upper]
            order = odd + [index for index in range(len(run)) if index not in set(odd)]
            for index in order:
                dropped = folded[:index] + folded[index + 1 :]
                variants.append("".join(dropped))
        run.clear()

    for piece in pieces:
        if re.fullmatch(r"[A-Za-z]", piece):
            if run and not separated:
                flush()
            run.append(piece)
            separated = False
            continue
        if re.fullmatch(r"[A-Za-z0-9]+", piece):
            flush()
            separated = False
            continue
        if run:
            separated = True
    flush()
    return variants


def _whole_word(haystack: str, needle: str) -> bool:
    if " " in needle:
        return f" {needle} " in f" {haystack} "
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def contains_term(text: str, term: str, *, spaced_variants: bool = False) -> bool:
    haystack = normalize_text(text)
    needle = normalize_text(term)
    if not needle:
        return False
    if _whole_word(haystack, needle):
        return True
    if not spaced_variants:
        return False
    return any(_whole_word(normalize_text(candidate), needle) for candidate in spaced_letter_variants(text))


def contains_any(text: str, terms: list[str], *, spaced_variants: bool = False) -> bool:
    return any(contains_term(text, term, spaced_variants=spaced_variants) for term in terms)
