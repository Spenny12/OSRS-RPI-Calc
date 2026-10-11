# OSRS RPI: Old School RuneScape Inflation Tracker

A weighted inflation index (an "RPI") for Old School RuneScape, built from Grand Exchange prices for a basket of 99 popular items. Made by Mod Kieren and Mod Spenny for the Lil Chungies.

It runs on **Cloudflare Pages**: a static front end plus two small Pages Functions that proxy and cache the price APIs at Cloudflare's edge.

## Features

- **Headline metrics:** last-full-month YoY (period average), YoY at 7 and 30 days ago (point-in-time) and week-on-week change.
- **Historical chart:** monthly YoY RPI back to 2016, with 1Y, 3Y, 5Y and All ranges.
- **What's driving it:** YoY change by category and each category's contribution to the headline figure.
- **Basket table:** every item's price a year ago vs last month, its change and its contribution. Sortable and filterable.
- **Past-date lookup:** the weekly and monthly figures as they would have looked on any past date.
- **Custom calculator:** single-item inflation with a price chart, or build your own weighted basket. Your basket is saved in your browser.
- Light and dark themes, works on mobile.

## How it's calculated

- **Point-in-time** figures use each item's last known price on or before each date.
- **Period-average** figures (the monthly series) average each item's daily price across the month.
- Each item's percentage change is weighted by its basket weight. If an item has no data for a period (usually because it hadn't been released yet), it's excluded and the remaining weights are rescaled to 100%. Excluded items are listed on the page.
- Weights live in [`public/assets/js/lib/basket.js`](public/assets/js/lib/basket.js) and are relative, so they don't need to add up to exactly 1.

## Project layout

```
public/                     static site (Pages build output)
  index.html                overview page
  custom/index.html         custom calculator
  assets/js/lib/            pure logic: basket, dates, RPI maths, data compaction
  assets/js/{home,custom,api,ui}.js
functions/api/
  mapping.js                GET /api/mapping      -> [{id, name}]
  history/[id].js           GET /api/history/:id  -> {id, start, prices[]}
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

Optional environment variable: `USER_AGENT` sets the User-Agent sent to the upstream APIs (set in `wrangler.toml`).

## Changes from the original Streamlit version

The Python/Streamlit app lives in the git history (before the `cloudflare-pages` branch). The port reproduces its numbers exactly (`tests/parity.test.mjs`) and also fixes:

- **Leap-day crash:** the home page called `date.replace(year=year-1)` directly, which raised `ValueError` on 29 February.
- **Look-ahead in gap filling:** missing days were filled with `bfill()` before `ffill()`, so gaps took the *next* known price. They now carry the last known price forward.
- **Default item never selected:** the custom calculator looked for `"shark"` in a list of proper-case names, so it always defaulted to the first item alphabetically.
- **Mixed-up docs:** basket comments claimed category shares (e.g. 18%, 7%, 20%) that didn't match the weights, which totalled 100.3%. Weights are now treated as relative and the comments show the real shares.
- **Mapping User-Agent:** the item list request spoofed a browser User-Agent. The Wiki asks for a descriptive one, which works fine.
- **Speed:** the history was recalculated server-side across 99 items × ~127 months on every cold cache. Now the edge caches compact data, and the browser computes everything in milliseconds.
