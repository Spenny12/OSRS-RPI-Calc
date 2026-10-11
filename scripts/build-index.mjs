#!/usr/bin/env node
// Builds the precomputed index (index.json) for the default basket.
// Runs daily in GitHub Actions (.github/workflows/build-index.yml); output is
// committed to the `data` branch and served by /api/rpi.
//
//   node scripts/build-index.mjs [outFile] [--cache DIR]
//
// --cache DIR reads/writes raw history JSON from DIR (handy for local runs).

import fs from "node:fs";
import { loadBasketSeries } from "./lib/history.mjs";
import { pointRpi, periodRpi, lastMonthYoY, monthlyHistory } from "../public/assets/js/lib/rpi.js";
import { DEFAULT_BASKET, BASKET_CATEGORIES, ITEM_ID, ITEM_CATEGORY } from "../public/assets/js/lib/basket.js";
import { todayDay, minusYears, previousMonth, parts, dayOf, fromDay } from "../public/assets/js/lib/dates.js";

const args = process.argv.slice(2);
const outFile = args.find((a) => !a.startsWith("--") && args[args.indexOf(a) - 1] !== "--cache") || "index.json";
const cacheDir = args.includes("--cache") ? args[args.indexOf("--cache") + 1] : null;
const UA = process.env.USER_AGENT || "OSRS-RPI-Calc index builder (github.com/Spenny12/OSRS-RPI-Calc) - Discord: spenny12_";

const loadAll = () =>
  loadBasketSeries({ names: Object.keys(DEFAULT_BASKET), idOf: (n) => ITEM_ID[n], cacheDir, userAgent: UA, log: console.log });

const r2 = (v, d = 4) => (v == null ? null : Math.round(v * 10 ** d) / 10 ** d);
const slimExcl = (list) => list.map((e) => [e.name, e.reason]);

function categoryBreakdown(result) {
  const by = new Map(BASKET_CATEGORIES.map((c) => [c.name, { w: 0, wc: 0, contrib: 0, n: 0 }]));
  for (const r of result.items) {
    const c = by.get(ITEM_CATEGORY[r.name]);
    c.w += r.weight; c.wc += r.weight * r.change; c.contrib += r.contribution; c.n++;
  }
  return BASKET_CATEGORIES.map((c) => {
    const b = by.get(c.name);
    return { name: c.name, share: c.share, items: c.items.length, used: b.n, change: b.w ? r2(b.wc / b.w) : null, contribution: r2(b.contrib) };
  });
}

/** Month-on-month change in average prices for each month (for the past-month lookup). */
function monthOnMonth(getSeries, today) {
  const out = [];
  let { y, m } = parts(today);
  for (let i = 0; i < 240; i++) {
    const cur = previousMonth(dayOf(y, m, 1) + 1);
    const prev = previousMonth(cur.start);
    if (parts(prev.start).y < 2015) break;
    const r = periodRpi(DEFAULT_BASKET, getSeries, prev, cur);
    if (r.value == null) break;
    out.push([fromDay(cur.end).slice(0, 7), r2(r.value), r.items.length]);
    m -= 1; if (m < 0) { m = 11; y -= 1; }
  }
  return out.reverse();
}

async function main() {
  const t0 = Date.now();
  console.log(`Fetching ${Object.keys(DEFAULT_BASKET).length} item histories…`);
  const getSeries = await loadAll();
  const names = Object.keys(DEFAULT_BASKET);
  const loaded = names.filter((n) => getSeries(n)).length; // excludes items still in burn-in
  if (loaded < names.length * 0.85) throw new Error(`Only ${loaded}/${names.length} histories loaded; refusing to publish.`);

  const latest = Math.max(...names.map((n) => getSeries(n)?.end ?? -Infinity));
  const today = Math.min(todayDay(), latest); // anchor on the newest data day

  const lm = lastMonthYoY(DEFAULT_BASKET, getSeries, todayDay());
  const e7 = today - 7, e30 = today - 30;
  const y7 = pointRpi(DEFAULT_BASKET, getSeries, minusYears(e7), e7);
  const y30 = pointRpi(DEFAULT_BASKET, getSeries, minusYears(e30), e30);
  const wow = pointRpi(DEFAULT_BASKET, getSeries, today - 7, today);
  const yoyNow = pointRpi(DEFAULT_BASKET, getSeries, minusYears(today), today);
  const yoyByItem = new Map(yoyNow.items.map((r) => [r.name, r.change]));

  const kpi = (r, from, to, extra = {}) => ({ value: r2(r.value), from: fromDay(from), to: fromDay(to), items: r.items.length, excluded: slimExcl(r.excluded), ...extra });

  const index = {
    version: 3,
    generatedAt: new Date().toISOString(),
    dataThrough: fromDay(latest),
    basketSize: names.length,
    loaded,
    kpis: {
      lastMonth: kpi(lm, lm.current.start, lm.current.end, { prevFrom: fromDay(lm.previous.start), prevTo: fromDay(lm.previous.end) }),
      yoy7: kpi(y7, minusYears(e7), e7),
      yoy30: kpi(y30, minusYears(e30), e30),
      wow: kpi(wow, today - 7, today),
    },
    history: monthlyHistory(DEFAULT_BASKET, getSeries, todayDay()).map((h) => [fromDay(h.month).slice(0, 7), r2(h.value), h.itemCount]),
    mom: monthOnMonth(getSeries, todayDay()),
    categories: categoryBreakdown(lm),
    // [name, category, share%, oldAvg, newAvg, change%, contribution(pts), latestPrice, yoyPoint%]
    items: lm.items
      .map((r) => [r.name, ITEM_CATEGORY[r.name], r2(r.share * 100), r2(r.oldPrice, 1), r2(r.newPrice, 1), r2(r.change), r2(r.contribution), getSeries(r.name)?.asof(latest) ?? null, r2(yoyByItem.get(r.name) ?? null)]),
  };

  fs.writeFileSync(outFile, JSON.stringify(index));
  console.log(`Wrote ${outFile} (${(fs.statSync(outFile).size / 1024).toFixed(0)} KB) in ${((Date.now() - t0) / 1000).toFixed(0)}s. ` +
    `Last month YoY ${index.kpis.lastMonth.value}% across ${lm.items.length} items; data through ${index.dataThrough}.`);
}

main().catch((e) => { console.error(e); process.exit(1); });
