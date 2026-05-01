You are a senior Python engineer. Build a production-ready script.

GOAL:
Find underpriced Magic: The Gathering listings on Vinted and compare against market prices, while filtering out fake/proxy/custom cards.

-------------------------------------

1. VINTED DATA (SEARCH)

- Use endpoint:
  https://www.vinted.com/api/v2/catalog/items

- Query params:
  - search_text=magic the gathering
  - per_page=50

- Extract:
  - title
  - description
  - price
  - currency
  - url

- Implement pagination

-------------------------------------

2. FILTER OUT FAKE / LOW-VALUE LISTINGS

Before any price comparison, discard listings if:

A) Keywords indicating fake cards (case-insensitive):
- "proxy"
- "proxies"
- "custom"
- "fan art"
- "handmade"
- "altered"
- "reprint"
- "not original"
- "replica"

B) Keywords indicating bulk / low-value:
- "bulk"
- "lot"
- "random cards"
- "100 cards"
- "collection"
- "bundle"

C) Suspicious pricing patterns:
- extremely low price per card (< €0.05 per card if quantity detected)

D) Language variations (important):
- Portuguese / Spanish / French equivalents:
  - "proxy", "réplica", "reimpresión", "artesanal", etc.

-------------------------------------

3. CARD PRICE SOURCE

Use Scryfall API:
https://api.scryfall.com/cards/named?fuzzy={card_name}

Extract:
- name
- prices.eur (fallback to usd if needed)

-------------------------------------

4. CARD NAME EXTRACTION

- Combine title + description
- Use:
  - regex patterns
  - RapidFuzz

- Detect:
  - single card listings
  - multiple cards

- Ignore:
  - set names
  - grading text (NM, EX, etc.)

-------------------------------------

5. PRICE COMPARISON

- If multiple cards:
  - estimate per-card value OR sum detected cards

- Compute:
  difference = (market_price - vinted_price) / market_price

- Flag listing if:
  difference >= 0.5

-------------------------------------

6. OUTPUT

Console + CSV/JSON file

Include:
- title
- detected_cards
- vinted_price
- estimated_market_price
- difference_percent
- url

-------------------------------------

7. PERFORMANCE

- aiohttp (async requests)
- retry logic
- rate limiting (1–2 sec delay)
- user-agent rotation

-------------------------------------

8. STRUCTURE

- vinted_client.py
- scryfall_client.py
- matcher.py
- filters.py   <-- IMPORTANT
- main.py

-------------------------------------

9. CONFIG FILE

config.json:
- search_query
- min_discount
- max_pages

-------------------------------------

10. BONUS

- Telegram / Discord alerts for deals

-------------------------------------

Return:
- Full working Python code
- requirements.txt
- setup instructions