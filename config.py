# --- API Configuration ---
# Set a user-agent as required by the wiki API
HEADERS = {
    'User-Agent': 'OSRS Inflation Calculator - MyProject v1.0'
}

# --- Default RPI Basket ---
# Weights should ideally sum to 1.0 (or 100)
DEFAULT_RPI_BASKET = {
    "Shark": 0.25,             # 25%
    "Prayer potion(4)": 0.30,  # 30%
    "Adamantite bar": 0.20,    # 20%
    "Twisted bow": 0.10,       # 10%
    "Scythe of vitur (uncharged)": 0.15    # 15%
}
