MTG Vinted Deal Finder

Setup
1) python -m venv .venv
2) source .venv/bin/activate
3) pip install -r requirements.txt
4) Edit config.json
5) python main.py

Outputs
- deals.csv
- deals.json

Notes
- Uses Vinted catalog endpoint with pagination.
- Filters fake/proxy/custom and bulk-style listings (multi-language keywords).
- Uses Scryfall fuzzy name lookup for market value.
- Optional Telegram/Discord alerts via config.
