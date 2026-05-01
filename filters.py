from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(slots=True)
class FilterResult:
    keep: bool
    reason: Optional[str] = None


FAKE_KEYWORDS = {
    "proxy",
    "proxies",
    "custom",
    "fan art",
    "handmade",
    "altered",
    "reprint",
    "not original",
    "replica",
    "réplica",
    "reimpresion",
    "reimpresión",
    "artesanal",
    "falso",
    "falsa",
    "faux",
    "contrefaçon",
}

LOW_VALUE_KEYWORDS = {
    "bulk",
    "lot",
    "random cards",
    "100 cards",
    "collection",
    "bundle",
    "lote",
    "colección",
    "colecao",
    "coleção",
    "paquete",
    "pacote",
    "vrac",
}

QUANTITY_PATTERNS = [
    re.compile(r"(\d{2,4})\s*(?:cards?|cartes?|cartas?)", re.IGNORECASE),
    re.compile(r"(?:lot|lote|bundle|pack)\s*(?:of\s*)?(\d{2,4})", re.IGNORECASE),
]


def _contains_any(text: str, keywords: Iterable[str]) -> Optional[str]:
    normalized = text.lower()
    for keyword in keywords:
        if keyword in normalized:
            return keyword
    return None


def detect_quantity(text: str) -> Optional[int]:
    for pattern in QUANTITY_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
    return None


def should_keep_listing(title: str, description: str, price_eur: float) -> FilterResult:
    combined = f"{title}\n{description}".strip()

    hit = _contains_any(combined, FAKE_KEYWORDS)
    if hit:
        return FilterResult(False, f"fake/proxy keyword: {hit}")

    hit = _contains_any(combined, LOW_VALUE_KEYWORDS)
    if hit:
        return FilterResult(False, f"bulk keyword: {hit}")

    quantity = detect_quantity(combined)
    if quantity and quantity > 0:
        if (price_eur / quantity) < 0.05:
            return FilterResult(False, f"suspicious price-per-card ({price_eur/quantity:.4f} EUR)")

    return FilterResult(True)
