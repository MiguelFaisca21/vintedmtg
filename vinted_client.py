from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any

import aiohttp


VINTED_URL = "https://www.vinted.com/api/v2/catalog/items"
VINTED_HOME = "https://www.vinted.com/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
]


class VintedAccessError(RuntimeError):
    """Raised when Vinted blocks API access (403)."""
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
        self._bootstrapped = False

    async def _bootstrap_session(self) -> None:
        if self._bootstrapped:
            return
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with self.session.get(VINTED_HOME, headers=headers, timeout=20) as resp:
            # even if non-200, this request may still populate anti-bot cookies
            await resp.text()
        self._bootstrapped = True

    def _api_headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.vinted.com/catalog?search_text=magic%20the%20gathering",
            "Origin": "https://www.vinted.com",
            "Connection": "keep-alive",
        }

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        await self._bootstrap_session()
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                async with self.session.get(VINTED_URL, params=params, headers=self._api_headers(), timeout=20) as resp:
                    if resp.status == 403:
                        body = await resp.text()
                        raise VintedAccessError(
                            "Vinted returned HTTP 403 (Forbidden). "
                            "This usually means anti-bot protection is blocking direct API calls from your IP/session. "
                            "Try again later, use a residential connection, reduce request frequency, and ensure cookies are accepted. "
                            f"Response snippet: {body[:180]}"
                        )
                    resp.raise_for_status()
                    return await resp.json()
            except VintedAccessError:
                raise
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
