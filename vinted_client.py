from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any

import aiohttp


VINTED_URL = "https://www.vinted.com/api/v2/catalog/items"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
]


@dataclass(slots=True)
class VintedItem:
    title: str
    description: str
    price: float
    currency: str
    url: str


class VintedClient:
    def __init__(self, session: aiohttp.ClientSession, delay: float = 1.2, retries: int = 3) -> None:
        self.session = session
        self.delay = delay
        self.retries = retries

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            try:
                async with self.session.get(VINTED_URL, params=params, headers=headers, timeout=20) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except Exception as exc:  # network/retry safety
                last_exc = exc
                await asyncio.sleep(self.delay * attempt)
        raise RuntimeError(f"Failed Vinted request after {self.retries} attempts") from last_exc

    async def search(self, query: str, max_pages: int = 5, per_page: int = 50) -> list[VintedItem]:
        results: list[VintedItem] = []
        for page in range(1, max_pages + 1):
            payload = await self._request(
                {
                    "search_text": query,
                    "per_page": per_page,
                    "page": page,
                }
            )
            items = payload.get("items", [])
            if not items:
                break

            for item in items:
                price_info = item.get("price") or {}
                amount = price_info.get("amount") or item.get("price_numeric") or 0
                currency = price_info.get("currency_code") or "EUR"
                url = item.get("url") or item.get("path") or ""
                if url.startswith("/"):
                    url = f"https://www.vinted.com{url}"

                results.append(
                    VintedItem(
                        title=item.get("title", "").strip(),
                        description=(item.get("description") or "").strip(),
                        price=float(amount),
                        currency=currency,
                        url=url,
                    )
                )
            await asyncio.sleep(self.delay)
        return results
