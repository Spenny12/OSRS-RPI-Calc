# OSRS RPI: Old School RuneScape Inflation Tracker

A weighted inflation index (an "RPI") for Old School RuneScape, built from Grand Exchange prices for a basket of about 680 of the most actively traded items, from runes and food to skilling supplies, PvM gear and mega rares. Made by Mod Kieren and Mod Spenny for the Lil Chungies.

It runs on **Cloudflare Pages** (static front end + Pages Functions). A daily GitHub Action precomputes the index into one small JSON file on the `data` branch, so the home page loads a single ~25 KB (gzipped) request instead of hundreds of price histories.

## Features

- **Headline metrics:** last-full-month YoY (period average), YoY at 7 and 30 days ago (point-in-time) and week-on-week change.
- **Historical chart:** monthly YoY RPI back to 2016, with 1Y, 3Y, 5Y and All ranges.
- **What's driving it:** YoY change by category and each category's contribution to the headline figure.
- **Basket table:** every item's price a year ago vs last month, its change and its contribution. Sortable and filterable.
- **Past-date lookup:** the weekly and monthly figures as they would have looked on any past date.
- **Custom calculator:** single-item inflation with a price chart, or build your own weighted basket. Your basket is saved in your browser.
- Light and dark themes, works on mobile.

## The basket

Built by [`scripts/select_basket.py`](scripts/select_basket.py) using rules in [`scripts/categories.py`](scripts/categories.py):

- **Activity threshold:** a 30-day average of at least 10 trades a day, and at least **25m gp/day** traded for consumables and skilling supplies or **75m gp/day** for equipment. This keeps out junk and dead items.
- **Exclusions:** cosmetics (3rd age, gilded, ornament kits, holiday items), armour sets and degraded/duplicate variants, notes, teleports, keys, impling jars, and NPC-priced loot such as ancient emblems.
- **13 categories with fixed shares:**

| Category | Share | | Category | Share |
|---|---|---|---|---|
| Potions | 10% | | Crafting | 6% |
| Herblore ingredients | 6% | | Farming | 4% |
| Food & fishing | 7% | | Prayer | 4% |
| Runes & magic supplies | 8% | | Mid-tier gear & PvM supplies | 12% |
| Ammunition | 7% | | High-end PvM gear | 12% |
| Logs, planks & construction | 7% | | Mega rares (100m+ and iconic chase items) | 10% |
| Ores, bars & smithing | 7% | | | |

- **Within a category**, items are weighted by the square root of their daily gp traded. Busy items count for more, but a few billion-gp items can't drown out the rest.

To refresh the basket (e.g. after a big update adds new items), regenerate the candidates file and rerun `select_basket.py`. The basket is the slow-moving part; prices update daily.

## How it's calculated

- **Point-in-time** figures use each item's last known price on or before each date.
- **Period-average** figures (the monthly series) average each item's daily price across the month.
- Each item's percentage change is weighted by its basket weight. If an item has no data for a period it's excluded and the remaining weights are rescaled to 100%. Excluded items are listed on the page.
- **New items** only join the index 60 days after they first appear on the GE, once the guide price has settled. Freshly released items often start at nonsense guide prices.
- **Anomaly guard:** any item whose price moves more than 10× within a single comparison is set aside for that comparison (e.g. a guide price stuck at 4.6k before correcting to 2.6m).

## Project layout

```
public/                     static site (Pages build output)
  index.html                overview page
  custom/index.html         custom calculator
  assets/js/lib/            pure logic: basket, dates, RPI maths, data compaction
  assets/js/{home,custom,api,ui}.js
functions/api/
  rpi.js                    GET /api/rpi          -> precomputed index (from the data branch)
  mapping.js                GET /api/mapping      -> [{id, name}]
  history/[id].js           GET /api/history/:id  -> {id, start, prices[]} (custom calculator)
scripts/
  build-index.mjs           builds index.json (run daily by .github/workflows/build-index.yml)
  select_basket.py          regenerates public/assets/js/lib/basket.js
  categories.py             category rules, exclusions and shares
tests/                      node:test unit + parity tests
wrangler.toml
```

Upstream data comes from:
- Item list: the [OSRS Wiki real-time prices API](https://prices.runescape.wiki/api/v1/osrs/mapping)
- Daily GE guide price history: the [Weird Gloop API](https://api.weirdgloop.org/) (`/exchange/history/osrs/all`)

The history function turns about 260 KB of raw JSON per item into an 18 KB gap-filled daily array. Results are cached at the edge for 6 hours, so the upstream APIs get called rarely, not once per visitor.

## Develop

```bash
npm install
npm run dev        # wrangler pages dev on http://localhost:8788
npm test
```

## Deploy

**Option A: connect the GitHub repo in the Cloudflare dashboard** (deploys automatically on every push)
Workers & Pages → Create → Pages → Connect to Git → pick this repo. Framework preset: *None*, build command: *(empty)*, build output directory: `public`.

**Option B: Wrangler CLI**
```bash
npx wrangler pages deploy public --project-name osrs-rpi-calc
```

Optional environment variables: `USER_AGENT` (User-Agent sent to the upstream APIs) and `INDEX_URL` (where `/api/rpi` reads index.json; defaults to this repo's `data` branch).

### Daily index build

`.github/workflows/build-index.yml` runs every day at 06:30 UTC (and on demand from the Actions tab). It fetches every basket item's history, builds `index.json` and force-pushes it as a single commit to the `data` branch. **Scheduled workflows only run from the default branch, so this starts once this code is on `main`.** You can build it locally with `node scripts/build-index.mjs index.json`.

## Changes from the original Streamlit version

The Python/Streamlit app lives in the git history (before the `cloudflare-pages` branch). The port reproduces its numbers exactly (`tests/parity.test.mjs`) and also fixes:

- **Leap-day crash:** the home page called `date.replace(year=year-1)` directly, which raised `ValueError` on 29 February.
- **Look-ahead in gap filling:** missing days were filled with `bfill()` before `ffill()`, so gaps took the *next* known price. They now carry the last known price forward.
- **Default item never selected:** the custom calculator looked for `"shark"` in a list of proper-case names, so it always defaulted to the first item alphabetically.
- **Mixed-up docs:** basket comments claimed category shares (e.g. 18%, 7%, 20%) that didn't match the weights, which totalled 100.3%. Weights are now treated as relative and the comments show the real shares.
- **Mapping User-Agent:** the item list request spoofed a browser User-Agent. The Wiki asks for a descriptive one, which works fine.
- **Bigger basket:** 99 hand-picked items became about 680 chosen by trading activity, with mega rares, Inquisitor's and other popular PvM gear, plus far more skilling supplies.
- **Speed:** the history was recalculated server-side across 99 items × ~127 months on every cold cache. Now the edge caches compact data, and the browser computes everything in milliseconds.
