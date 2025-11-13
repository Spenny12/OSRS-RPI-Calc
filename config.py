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
# We use a compliant User-Agent as required by the wiki API,
# including a contact method (Discord ID).
HEADERS = {
    'User-Agent': 'OSRS Inflation Calculator - Discord: spenny12_'
}
