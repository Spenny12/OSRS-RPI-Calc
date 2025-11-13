"""
Configuration file for the OSRS Inflation Calculator.
Stores the default RPI basket and API headers.
"""

# Default basket of items for the OSRS "RPI"
# Weights should add up to 1.0
DEFAULT_RPI_BASKET = {
    # --- 1. Potions (18.0%) ---
    # High-impact, frequently consumed items. Doses are split equally.
    "Ranging Potion (4)": 0.02,
    "Ranging Potion (3)": 0.015,
    "Saradomin Brew (4)": 0.025,
    "Saradomin Brew (3)": 0.015,
    "Super Restore (4)": 0.025,
    "Super Restore (3)": 0.015,
    "Divine Super Combat Potion (4)": 0.02,
    "Divine Super Combat Potion (3)": 0.01,
    "Super Combat Potion (4)": 0.015,
    "Super Combat Potion (3)": 0.01,
    "Divine Ranging Potion (4)": 0.01,
    "Divine Ranging Potion (3)": 0.005,

    # --- 2. Skilling Materials - Herblore Secondaries (7.0%) ---
    "Snape Grass": 0.025,
    "Red Spiders' Eggs": 0.02,
    "Wine of zamorak": 0.01,
    "Crushed nest": 0.007,
    "Bird nest (empty)": 0.003,

    # --- 3. Skilling Materials - Construction & Woodcutting (20.0%) ---
    "Mahogany Plank": 0.05,
    "Teak Plank": 0.04,
    "Oak Plank": 0.03,
    "Plank": 0.02,
    "Redwood Logs": 0.015,
    "Magic Logs": 0.015,
    "Yew Logs": 0.01,
    "Maple Logs": 0.005,
    "Willow Logs": 0.005,
    "Magic seed": 0.005,
    "Yew seed": 0.005,
    "Coconut": 0.005,
    "Maple seed": 0.005,

    # --- 4. Skilling Materials - Mining, Smithing & Crafting (15.0%) ---
    "Runite Bar": 0.025,
    "Adamantite Bar": 0.02,
    "Steel Bar": 0.015,
    "Gold Bar": 0.015,
    "Iron ore": 0.01,
    "Coal": 0.01,
    "Gold Ore": 0.005,
    "Diamond": 0.005,
    "Ruby": 0.005,
    "Emerald": 0.005,
    "Sapphire": 0.005,
    "Grapes": 0.005,

    # --- 5. Consumables - Food (10.0%) ---
    "Shark": 0.03,
    "Monkfish": 0.02,
    "Karambwan": 0.015,
    "Manta Ray": 0.01,
    "Lobster": 0.007,
    "Swordfish": 0.005,
    "Sea Turtle": 0.005,
    "Tuna Potato": 0.003,

    # --- 6. PvM/High-End Gear (15.0%) ---
    "Twisted Bow": 0.03,
    "Tumeken's Shadow (uncharged)": 0.025,
    "Scythe of Vitur (uncharged)": 0.02,
    "Bandos Chestplate": 0.01,
    "Bandos Tassets": 0.01,
    "Occult Necklace": 0.007,
    "Dragon Boots": 0.005,
    "Berserker Ring": 0.005,
    "Dragonfire shield": 0.003,
    "Abyssal Whip": 0.003,
    "Granite Maul": 0.003,
    "Enhanced Crystal weapon seed": 0.003,
    "Zenyte shard": 0.003,
    "Lightbearer": 0.002,
    "Revenant Ether": 0.002,
    "Zombie axe": 0.001,
    "Ursine chainmace": 0.001,
    "Webweaver Bow": 0.001,
    "Accursed Sceptre": 0.001,
    "Guthan's armour set": 0.001,
    "Dharok's armour set": 0.001,
    "Karil's armour set": 0.001,
    "Ahrim's armour set": 0.001,

    # --- 7. Ammunition & Projectiles (5.0%) ---
    "Steel cannonball": 0.01,
    "Rune Arrow": 0.005,
    "Amethyst Arrow": 0.005,
    "Dragon Arrow": 0.005,
    "Rune Dart": 0.005,
    "Amethyst Dart": 0.005,
    "Dragon Dart": 0.005,
    "Adamant Arrow": 0.002,
    "Adamant Dart": 0.002,
    "Red Chinchompa": 0.002,
    "Black Chinchompa": 0.001,

    # --- 8. Magic, Runes & Other (15.0%) ---
    "Blood Rune": 0.02,
    "Death Rune": 0.02,
    "Nature Rune": 0.02,
    "Cosmic Rune": 0.01,
    "Chaos Rune": 0.01,
    "Air orb": 0.01,
    "Water orb": 0.01,
    "Fire orb": 0.01,
    "Earth orb": 0.01,
    "Numulite": 0.005,
    "Air Rune": 0.003,
    "Water Rune": 0.003,
    "Fire Rune": 0.002,
    "Earth Rune": 0.002,
    "Soul Rune": 0.002,
}


# Header for the 'api.weirdgloop.org' (History API)
# This API requires a compliant User-Agent with a contact.
WEIRDGLOOP_HEADERS = {
    'User-Agent': 'OSRS Inflation Calculator - Discord: spenny12_',
    # Make the request look more legitimate by adding standard Accept headers
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9'
}

# Header for the 'prices.runescape.wiki' (Mapping API)
# This API is stricter and blocks our bot User-Agent. We use a generic browser one.
MAPPING_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    # Also add Accept headers here to match the browser User-Agent
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9'
}
