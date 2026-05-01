from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz


GRADE_TOKENS = {
    "nm", "ex", "lp", "mp", "hp", "damaged", "mint", "foil", "nonfoil", "signed"
}

SET_TOKENS = {
    "mtg", "magic", "the", "gathering", "commander", "modern", "legacy", "pioneer", "standard"
}

CARD_PHRASE_PATTERN = re.compile(r"\b([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){0,5})\b")


@dataclass(slots=True)
class CardMatch:
    cards: list[str]
    is_multi: bool


def _clean_phrase(phrase: str) -> str | None:
    tokens = [t.strip(".,;:!?()[]{}") for t in phrase.split()]
    filtered = [t for t in tokens if t and t.lower() not in GRADE_TOKENS]
    if not filtered:
        return None
    if all(t.lower() in SET_TOKENS for t in filtered):
        return None
    cleaned = " ".join(filtered).strip()
    if len(cleaned) < 3:
        return None
    return cleaned


def extract_candidate_names(text: str) -> list[str]:
    candidates: list[str] = []
    for match in CARD_PHRASE_PATTERN.finditer(text):
        cleaned = _clean_phrase(match.group(1))
        if cleaned:
            candidates.append(cleaned)

    # Add common comma-separated naming style fragments
    for part in re.split(r"[,/|]", text):
        part = part.strip()
        if 3 <= len(part) <= 40 and any(ch.isalpha() for ch in part):
            cleaned = _clean_phrase(part)
            if cleaned:
                candidates.append(cleaned)

    deduped: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def pick_best_names(candidates: Iterable[str], max_names: int = 6) -> list[str]:
    ranked = sorted(candidates, key=lambda x: (-len(x.split()), -fuzz.ratio(x, x)))
    return ranked[:max_names]


def detect_cards(title: str, description: str) -> CardMatch:
    combined = f"{title}\n{description}".strip()
    candidates = extract_candidate_names(combined)
    selected = pick_best_names(candidates)
    return CardMatch(cards=selected, is_multi=len(selected) > 1)
