# --- API Configuration ---
# Set a user-agent as required by the wiki API
# A descriptive User-Agent with a contact is required by the OSRS Wiki APIs
# to prevent blocking.
HEADERS = {
    'User-Agent': 'OSRS Inflation Calculator - (github.com/spenny12/osrs-calc)'
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
