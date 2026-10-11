#!/usr/bin/env node
// Weekly Discord recap: the biggest raw GE price moves of the last complete
// week (Sunday close to Sunday close), posted to a Discord webhook.
// Runs Mondays in GitHub Actions (.github/workflows/weekly-discord.yml).
//
//   node scripts/weekly-recap.mjs [--dry-run] [--date YYYY-MM-DD] [--cache DIR]
//
//   --dry-run     print the message instead of posting it (no webhook needed)
//   --date        pretend today is this date (to back-test a past week)
//   --cache DIR   read/write raw history JSON in DIR (handy for local runs)
//
// The webhook URL comes from the DISCORD_WEBHOOK_URL environment variable.

import { loadBasketSeries } from "./lib/history.mjs";
import { pointRpi } from "../public/assets/js/lib/rpi.js";
import { DEFAULT_BASKET, ITEM_ID } from "../public/assets/js/lib/basket.js";
import { todayDay, toDay, fromDay } from "../public/assets/js/lib/dates.js";
import { recapWindow, itemMove, selectMovers, contextText, buildEmbed, discordPayload } from "./lib/recap.mjs";

const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const opt = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : null);
const dryRun = flag("--dry-run");
const cacheDir = opt("--cache");
const UA = process.env.USER_AGENT || "OSRS-RPI-Calc weekly recap (github.com/Spenny12/OSRS-RPI-Calc) - Discord: spenny12_";
const SITE_URL = process.env.SITE_URL || "https://osrs-rpi-calc.pages.dev";
const WEBHOOK = process.env.DISCORD_WEBHOOK_URL || "";
const WEBHOOK_RE = /^https:\/\/(?:(?:canary|ptb)\.)?discord(?:app)?\.com\/api\/webhooks\/\d+\/[\w-]+$/;

async function post(url, body) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const res = await fetch(`${url}?wait=true`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30_000),
    });
    if (res.status === 429) {
      const wait = Number((await res.json().catch(() => ({}))).retry_after) || 2;
      await new Promise((r) => setTimeout(r, Math.min(wait, 30) * 1000));
      continue;
    }
    if (!res.ok) throw new Error(`Discord returned HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
    return;
  }
  throw new Error("Discord rate limited the request three times in a row.");
}

async function main() {
  if (!dryRun && !WEBHOOK) throw new Error("DISCORD_WEBHOOK_URL is not set. Add it as a repository secret, or use --dry-run.");
  // Never echo the URL: it is a credential.
  if (!dryRun && !WEBHOOK_RE.test(WEBHOOK)) throw new Error("DISCORD_WEBHOOK_URL doesn't look like a Discord webhook URL.");

  const today = opt("--date") ? toDay(opt("--date")) : todayDay();
  if (today == null) throw new Error("--date must be YYYY-MM-DD");
  const win = recapWindow(today);
  console.log(`Recap window: Sunday ${fromDay(win.start)} → Sunday ${fromDay(win.end)}`);

  const names = Object.keys(DEFAULT_BASKET);
  console.log(`Fetching ${names.length} item histories…`);
  const getSeries = await loadBasketSeries({ names, idOf: (n) => ITEM_ID[n], cacheDir, userAgent: UA, log: console.log });

  const loaded = names.filter((n) => getSeries(n)).length;
  if (loaded < names.length * 0.85) throw new Error(`Only ${loaded}/${names.length} histories loaded; refusing to post.`);
  const latest = Math.max(...names.map((n) => getSeries(n)?.end ?? -Infinity));
  if (latest < win.end) throw new Error(`Price data only runs to ${fromDay(latest)}, but the week ends ${fromDay(win.end)}. Try again later.`);

  const moves = [];
  for (const name of names) {
    const s = getSeries(name);
    const m = itemMove(s, win.start, win.end);
    if (m) moves.push({ name, ...m });
  }
  const movers = selectMovers(moves).map((m) => ({ ...m, context: contextText(getSeries(m.name), win.end, Math.sign(m.change)) }));
  const rpi = pointRpi(DEFAULT_BASKET, getSeries, win.start, win.end);

  const embed = buildEmbed({ window: win, movers, basket: { value: rpi.value, items: rpi.items.length }, siteUrl: SITE_URL });
  console.log(`\n${embed.title}\n${embed.description}\n\n(${moves.length} items eligible, ${movers.length} reported)`);

  if (dryRun) {
    console.log("\n--dry-run: not posting.");
    return;
  }
  await post(WEBHOOK, discordPayload(embed));
  console.log("Posted to Discord.");
}

main().catch((e) => {
  console.error(`✗ ${e.message}`);
  process.exit(1);
});
