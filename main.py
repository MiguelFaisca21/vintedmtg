from __future__ import annotations

import asyncio
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import aiohttp

from filters import should_keep_listing
from matcher import detect_cards
from scryfall_client import ScryfallClient
from vinted_client import VintedAccessError, VintedClient


@dataclass(slots=True)
class Deal:
    title: str
    detected_cards: list[str]
    vinted_price: float
    estimated_market_price: float
    difference_percent: float
    url: str


async def send_telegram_alert(session: aiohttp.ClientSession, config: dict, deal: Deal) -> None:
    tg = config.get("telegram", {})
    if not tg.get("enabled"):
        return
    token = tg.get("bot_token")
    chat_id = tg.get("chat_id")
    if not token or not chat_id:
        return

    text = (
        f"🔥 MTG Deal Found\n{deal.title}\n"
        f"Cards: {', '.join(deal.detected_cards)}\n"
        f"Price: {deal.vinted_price:.2f}\n"
        f"Market: {deal.estimated_market_price:.2f}\n"
        f"Discount: {deal.difference_percent:.1f}%\n{deal.url}"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    await session.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)


async def send_discord_alert(session: aiohttp.ClientSession, config: dict, deal: Deal) -> None:
    dc = config.get("discord", {})
    if not dc.get("enabled"):
        return
    webhook_url = dc.get("webhook_url")
    if not webhook_url:
        return
    content = (
        f"🔥 **MTG Deal**\n**{deal.title}**\n"
        f"Cards: {', '.join(deal.detected_cards)}\n"
        f"Vinted: {deal.vinted_price:.2f} | Market: {deal.estimated_market_price:.2f}\n"
        f"Discount: {deal.difference_percent:.1f}%\n{deal.url}"
    )
    await session.post(webhook_url, json={"content": content}, timeout=15)


def load_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def process() -> None:
    config = load_config()
    async with aiohttp.ClientSession() as session:
        vinted = VintedClient(session, delay=float(config.get("request_delay_seconds", 1.2)))
        scryfall = ScryfallClient(session, delay=float(config.get("request_delay_seconds", 1.2)))

        try:
            listings = await vinted.search(
                query=config.get("search_query", "magic the gathering"),
                max_pages=int(config.get("max_pages", 5)),
                per_page=int(config.get("per_page", 50)),
            )
        except VintedAccessError as exc:
            print(f"Vinted access blocked: {exc}")
            return

        deals: list[Deal] = []
        for item in listings:
            price_eur = item.price if item.currency.upper() == "EUR" else item.price
            filter_result = should_keep_listing(item.title, item.description, price_eur)
            if not filter_result.keep:
                continue

            card_match = detect_cards(item.title, item.description)
            if not card_match.cards:
                continue

            card_prices = await asyncio.gather(*[scryfall.get_card_price(c) for c in card_match.cards])
            valid_prices = [cp.market_price for cp in card_prices if cp and cp.market_price]
            if not valid_prices:
                continue

            estimated_market = sum(valid_prices) if card_match.is_multi else valid_prices[0]
            if estimated_market <= 0:
                continue

            difference = (estimated_market - price_eur) / estimated_market
            if difference < float(config.get("min_discount", 0.5)):
                continue

            deal = Deal(
                title=item.title,
                detected_cards=[cp.resolved_name for cp in card_prices if cp],
                vinted_price=price_eur,
                estimated_market_price=estimated_market,
                difference_percent=difference * 100,
                url=item.url,
            )
            deals.append(deal)
            await asyncio.gather(
                send_telegram_alert(session, config, deal),
                send_discord_alert(session, config, deal),
            )

        _print_deals(deals)
        _write_outputs(deals, config)


def _print_deals(deals: list[Deal]) -> None:
    if not deals:
        print("No underpriced listings found.")
        return
    for d in deals:
        print(
            f"{d.title} | cards={d.detected_cards} | "
            f"vinted={d.vinted_price:.2f} | market={d.estimated_market_price:.2f} | "
            f"discount={d.difference_percent:.1f}% | {d.url}"
        )


def _write_outputs(deals: list[Deal], config: dict) -> None:
    csv_path = Path(config.get("output_csv", "deals.csv"))
    json_path = Path(config.get("output_json", "deals.json"))

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["title", "detected_cards", "vinted_price", "estimated_market_price", "difference_percent", "url"],
        )
        writer.writeheader()
        for deal in deals:
            row = asdict(deal)
            row["detected_cards"] = ", ".join(deal.detected_cards)
            writer.writerow(row)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(d) for d in deals], f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(process())
