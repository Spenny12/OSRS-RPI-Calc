# --- API Configuration ---
# Set a user-agent as required by the wiki API
HEADERS = {
    'User-Agent': 'OSRS Inflation Calculator - v2.0'
}

# --- Default Basket Configuration ---
# Weights must sum to 1.0
DEFAULT_RPI_BASKET = {
    "Shark": 0.25,             # 25%
    "Prayer potion(4)": 0.30,  # 30%
    "Adamantite bar": 0.20,    # 20%
    "Twisted bow": 0.10,       # 10%
    "Scythe of vitur": 0.15    # 15%
}
