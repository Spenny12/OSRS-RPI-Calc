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

# API headers.
# We use a generic browser User-Agent to avoid being blocked by the API.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
