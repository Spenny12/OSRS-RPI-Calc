"""
Configuration file for the OSRS Inflation Calculator.
Stores the default RPI basket and API headers.
"""

# Default basket of items for the OSRS "RPI"
# Weights should add up to 1.0
DEFAULT_RPI_BASKET = {
    "Shark": 0.25,
    "Prayer potion(4)": 0.30,
    "Adamantite bar": 0.20,
    "Twisted bow": 0.10,
    "Scythe of vitur (uncharged)": 0.15
}

# --- NEW ---
# Header for the 'api.weirdgloop.org' (History API)
# This API requires a compliant User-Agent with a contact.
WEIRDGLOOP_HEADERS = {
    'User-Agent': 'OSRS Inflation Calculator - Discord: spenny12_'
}

# Header for the 'prices.runescape.wiki' (Mapping API)
# This API is stricter and blocks our bot User-Agent. We use a generic browser one.
MAPPING_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
