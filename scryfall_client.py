from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any

import aiohttp

SCRYFALL_URL = "https://api.scryfall.com/cards/named"

USER_AGENTS = [
    "mtg-value-bot/1.0 (+https://example.local)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
]


@dataclass(slots=True)
class CardPrice:
    input_name: str
    resolved_name: str
    eur: float | None
    usd: float | None

    @property
    def market_price(self) -> float | None:
        return self.eur if self.eur is not None else self.usd


class ScryfallClient:
    def __init__(self, session: aiohttp.ClientSession, delay: float = 1.2, retries: int = 3) -> None:
        self.session = session
        self.delay = delay
        self.retries = retries
        self.cache: dict[str, CardPrice | None] = {}

    async def _request(self, name: str) -> dict[str, Any] | None:
        key = name.lower().strip()
        if key in self.cache:
            cached = self.cache[key]
            return None if cached is None else {
                "name": cached.resolved_name,
                "prices": {"eur": str(cached.eur) if cached.eur is not None else None, "usd": str(cached.usd) if cached.usd is not None else None},
            }

        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            try:
                async with self.session.get(SCRYFALL_URL, params={"fuzzy": name}, headers=headers, timeout=20) as resp:
                    if resp.status == 404:
                        self.cache[key] = None
                        return None
                    resp.raise_for_status()
                    data = await resp.json()
                    return data
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(self.delay * attempt)
        raise RuntimeError(f"Failed Scryfall request for {name}") from last_exc

    async def get_card_price(self, name: str) -> CardPrice | None:
        key = name.lower().strip()
        if key in self.cache:
            return self.cache[key]

        data = await self._request(name)
        if not data:
            self.cache[key] = None
            return None

        prices = data.get("prices") or {}
        eur = _to_float(prices.get("eur"))
        usd = _to_float(prices.get("usd"))
        card = CardPrice(
            input_name=name,
            resolved_name=data.get("name", name),
            eur=eur,
            usd=usd,
        )
        self.cache[key] = card
        await asyncio.sleep(self.delay)
        return card


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
