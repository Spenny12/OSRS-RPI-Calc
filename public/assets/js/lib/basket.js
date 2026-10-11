// Default OSRS "RPI" basket.
// Weights are relative: they are normalised to 100% at calculation time, and
// re-normalised across whichever items have price data for a given period.
// Category shares below are the actual totals of the weights in each group.

export const BASKET_CATEGORIES = [
  {
    name: "Potions", // 18.5%
    items: {
      "Ranging potion(4)": 0.02,
      "Ranging potion(3)": 0.015,
      "Saradomin brew(4)": 0.025,
      "Saradomin brew(3)": 0.015,
      "Super restore(4)": 0.025,
      "Super restore(3)": 0.015,
      "Divine super combat potion(4)": 0.02,
      "Divine super combat potion(3)": 0.01,
      "Super combat potion(4)": 0.015,
      "Super combat potion(3)": 0.01,
      "Divine ranging potion(4)": 0.01,
      "Divine ranging potion(3)": 0.005,
    },
  },
  {
    name: "Herblore secondaries", // 6.5%
    items: {
      "Snape grass": 0.025,
      "Red spiders' eggs": 0.02,
      "Wine of Zamorak": 0.01,
      "Crushed nest": 0.007,
      "Bird nest (empty)": 0.003,
    },
  },
  {
    name: "Construction & woodcutting", // 21.0%
    items: {
      "Mahogany plank": 0.05,
      "Teak plank": 0.04,
      "Oak plank": 0.03,
      "Plank": 0.02,
      "Redwood logs": 0.015,
      "Magic logs": 0.015,
      "Yew logs": 0.01,
      "Maple logs": 0.005,
      "Willow logs": 0.005,
      "Magic seed": 0.005,
      "Yew seed": 0.005,
      "Coconut": 0.005,
      "Maple seed": 0.005,
    },
  },
  {
    name: "Mining, smithing & crafting", // 12.5%
    items: {
      "Runite bar": 0.025,
      "Adamantite bar": 0.02,
      "Steel bar": 0.015,
      "Gold bar": 0.015,
      "Iron ore": 0.01,
      "Coal": 0.01,
      "Gold ore": 0.005,
      "Diamond": 0.005,
      "Ruby": 0.005,
      "Emerald": 0.005,
      "Sapphire": 0.005,
      "Grapes": 0.005,
    },
  },
  {
    name: "Food", // 9.5%
    items: {
      "Shark": 0.03,
      "Monkfish": 0.02,
      "Cooked karambwan": 0.015,
      "Manta ray": 0.01,
      "Lobster": 0.007,
      "Swordfish": 0.005,
      "Sea turtle": 0.005,
      "Tuna potato": 0.003,
    },
  },
  {
    name: "PvM & high-end gear", // 13.9%
    items: {
      "Twisted bow": 0.03,
      "Tumeken's shadow (uncharged)": 0.025,
      "Scythe of Vitur (uncharged)": 0.02,
      "Bandos chestplate": 0.01,
      "Bandos tassets": 0.01,
      "Occult necklace": 0.007,
      "Dragon boots": 0.005,
      "Berserker ring": 0.005,
      "Dragonfire shield": 0.003,
      "Abyssal whip": 0.003,
      "Granite maul": 0.003,
      "Enhanced crystal weapon seed": 0.003,
      "Zenyte shard": 0.003,
      "Lightbearer": 0.002,
      "Revenant ether": 0.002,
      "Zombie axe": 0.001,
      "Ursine chainmace (u)": 0.001,
      "Webweaver bow (u)": 0.001,
      "Accursed sceptre (u)": 0.001,
      "Guthan's armour set": 0.001,
      "Dharok's armour set": 0.001,
      "Karil's armour set": 0.001,
      "Ahrim's armour set": 0.001,
    },
  },
  {
    name: "Ammunition & projectiles", // 4.7%
    items: {
      "Steel cannonball": 0.01,
      "Rune arrow": 0.005,
      "Amethyst arrow": 0.005,
      "Dragon arrow": 0.005,
      "Rune dart": 0.005,
      "Amethyst dart": 0.005,
      "Dragon dart": 0.005,
      "Adamant arrow": 0.002,
      "Adamant dart": 0.002,
      "Red chinchompa": 0.002,
      "Black chinchompa": 0.001,
    },
  },
  {
    name: "Runes, orbs & other", // 13.7%
    items: {
      "Blood rune": 0.02,
      "Death rune": 0.02,
      "Nature rune": 0.02,
      "Cosmic rune": 0.01,
      "Chaos rune": 0.01,
      "Air orb": 0.01,
      "Water orb": 0.01,
      "Fire orb": 0.01,
      "Earth orb": 0.01,
      "Numulite": 0.005,
      "Air rune": 0.003,
      "Water rune": 0.003,
      "Fire rune": 0.002,
      "Earth rune": 0.002,
      "Soul rune": 0.002,
    },
  },
];

/** Flat { itemName: weight } map of the default basket. */
export const DEFAULT_BASKET = Object.fromEntries(
  BASKET_CATEGORIES.flatMap((c) => Object.entries(c.items))
);

/** itemName -> category name */
export const ITEM_CATEGORY = Object.fromEntries(
  BASKET_CATEGORIES.flatMap((c) => Object.keys(c.items).map((n) => [n, c.name]))
);
