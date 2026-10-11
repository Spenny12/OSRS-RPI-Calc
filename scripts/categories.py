"""Category rules for building the OSRS RPI basket. First matching rule wins."""
import re

# Items never included: cosmetics, duplicates of other items, notes, lottery items, etc.
EXCLUDE = re.compile(r"""(
    3rd\ age | gilded | armour\ set | robes\ set | \bset\b | ornament\ kit | \(or\) | \(g\) | \(t\) | \(h\d\)
  | \(damaged\) | broken | \(i\)$ | bond | mystery\ box | clue | casket | \bnote\b | impling\ jar
  | partyhat | h'ween | santa | cracker | halloween | christmas | easter | holiday
  | \ 0$ | \(au\) | toxic\ trident\ \(e\) | ^ancient\ (emblem|effigy|statuette|medallion|totem|relic)$ | sawmill\ voucher | contract\ of | robin\ hood\ hat | flared\ trousers
  | purple\ sweets | waystone | fabric | weapon\ scroll | \bteleport\b | tablet | \bkey\b | key\ master
  | burnt\ page | searing\ page | trouver | \(deadman\) | \(bh\) | \(l\)$ | fremennik\ kilt | mole\ skin | mole\ claw
)""", re.I | re.X)

# The iconic chase items. Anything else worth 100m+ also lands here automatically.
MEGA_RARES = {
    "Twisted bow", "Scythe of Vitur (uncharged)", "Tumeken's shadow (uncharged)", "Elysian spirit shield",
    "Harmonised orb", "Eldritch orb", "Volatile orb", "Soulreaper axe", "Zaryte crossbow",
    "Torva full helm", "Torva platebody", "Torva platelegs",
    "Inquisitor's mace", "Inquisitor's great helm", "Inquisitor's hauberk", "Inquisitor's plateskirt",
    "Avernic treads", "Ancestral hat", "Ancestral robe top", "Ancestral robe bottom", "Kodai insignia",
    "Oathplate helm", "Oathplate chest", "Oathplate legs", "Arcane spirit shield", "Spectral spirit shield",
    "Masori body (f)", "Masori chaps (f)", "Masori mask (f)", "Sanguinesti staff (uncharged)", "Ghrazi rapier",
    "Justiciar faceguard", "Justiciar chestguard", "Justiciar legguards", "Twisted buckler", "Dragon hunter crossbow",
    "Elder maul", "Kodai wand", "Dinh's bulwark", "Arcane sigil", "Spectral sigil", "Elysian sigil",
}
MEGA_RARE_PRICE = 100_000_000

# (category, regex) in priority order
RULES = [
    ("Ammunition", r"bolts \(unf\)"),
    ("Crafting", r"^(ring of wealth|amulet of glory|skills necklace|games necklace|ring of dueling|combat bracelet)( ?\(\d\))?$"),
    ("Herblore ingredients", r"\(unf\)"),
    ("Mid-tier gear & PvM supplies", r"^crystal (armour|weapon|tool) seed$|^enhanced crystal weapon seed$|blowpipe"),
    ("Prayer", r"\bbones\b|\bashes\b|ensouled|\bremains\b"),
    ("Potions", r"\(\d\)$|potion|brew|serum|antidote|anti-venom|antifire|stamina|super (attack|strength|defence|energy|restore|combat)"),
    ("Herblore ingredients", r"^(grimy )?(guam|marrentill|tarromin|harralander|ranarr|toadflax|irit|avantoe|kwuarm|snapdragon|cadantine|lantadyme|dwarf weed|torstol|huasca)( weed| leaf)?$|\(unf\)|snape grass$|red spiders' eggs|wine of zamorak|crushed nest|limpwurt|white berries|potato cactus|jangerberries|zulrah's scales|unicorn horn|dragon scale dust|goat horn dust|eye of newt|mort myre fungus|amylase|lava scale|crystal dust|nihil dust|araxyte venom sac|cactus spine|vial of blood|blood essence|bird nest|^nail beast nails|^cadantine blood|^caviar"),
    ("Farming", r"\bseed\b|sapling|compost|\bspore\b"),
    ("Food & fishing", r"^(raw |cooked )?(shark|anglerfish|manta ray|karambwan|dark crab|sea turtle|lobster|swordfish|monkfish|tuna|marlin|halibut|bluefin|bass|salmon|trout|tuna potato|moonlight antelope|summer pie|wild pie|pineapple pizza)$|^cooked |^raw |^papaya|^coconut$|^grapes$|^ham joint$|sandworms|diabolic worms|shark lure|rainbow crab paste"),
    ("Runes & magic supplies", r"\brune$|\borb$|battlestaff|^mystic (air|water|earth|fire|smoke|mud|lava|steam|dust|mist) staff|staff crown|^tome of .* \(empty\)|soul rune|aether"),
    ("Ammunition", r"arrow|bolt|\bdart\b|dart tip|javelin|cannonball|chinchompa|\bknife\b|atlatl dart|^feather$|bow string|bolt tips|arrowtips|javelin tips|^dragon nails$|^rune nails$|^mithril nails$|dynamite"),
    ("Logs, planks & construction", r"\blogs\b|\bplank\b|marble block|magic stone|bolt of cloth|soft clay|^limestone|^camphor|^ironwood|^rosewood plank|keel parts|hull parts|celastrus bark|^redwood|pyre logs"),
    ("Ores, bars & smithing", r"\bore\b|\bbar\b|^coal$|metal sheet|orikalkum|^dragon metal|^gold leaf|silver ore|^amethyst$|^dragon limbs$"),
    ("Crafting", r"^uncut |^(sapphire|emerald|ruby|diamond|dragonstone|onyx|zenyte shard|opal|jade|red topaz)$|dragonhide|dragon leather|^hydra leather|molten glass|\bhide\b(?! body| chaps| coif)|fox fur|^gold bar|^silver bar|(sapphire|emerald|ruby|diamond|dragonstone|onyx) (necklace|amulet|bracelet|ring)|amulet \(u\)|amulet of (glory|power|strength)|^combat bracelet|^skills necklace|^ring of (recoil|wealth|dueling)|^phoenix necklace|^regen bracelet|elemental amulet|^earth emerald|^blessed spirit shield$"),
]

def categorise(name: str, price: float) -> str | None:
    if EXCLUDE.search(name):
        return None
    if name in MEGA_RARES or price >= MEGA_RARE_PRICE:
        return "Mega rares"
    for cat, rx in RULES:
        if re.search(rx, name, re.I):
            return cat
    if price >= 15_000_000:
        return "High-end PvM gear"
    return "Mid-tier gear & PvM supplies"

# Category share of the index (percent). Mega rares are deliberately capped so a
# handful of billion-gp items can't swing the whole index on their own.
CATEGORY_SHARES = {
    "Potions": 10,
    "Herblore ingredients": 6,
    "Food & fishing": 7,
    "Runes & magic supplies": 8,
    "Ammunition": 7,
    "Logs, planks & construction": 7,
    "Ores, bars & smithing": 7,
    "Crafting": 6,
    "Farming": 4,
    "Prayer": 4,
    "Mid-tier gear & PvM supplies": 12,
    "High-end PvM gear": 12,
    "Mega rares": 10,
}
assert sum(CATEGORY_SHARES.values()) == 100
