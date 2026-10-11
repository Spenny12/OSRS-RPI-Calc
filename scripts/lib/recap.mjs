// Pure logic for the weekly Discord recap (no network, no clock): picks the
// week, finds the biggest raw price moves, adds "lowest since…" context and
// builds the Discord embed. Used by scripts/weekly-recap.mjs.

import { pctChange, HISTORY_START_DAY, MAX_PRICE_RATIO } from "../../public/assets/js/lib/rpi.js";
import { formatDay, fromDay } from "../../public/assets/js/lib/dates.js";

/** An item must move at least this much (%) over the week to be reported. */
export const MIN_MOVE_PCT = 5;
/** Items priced below this (gp) at either end are skipped: a few gp of tick noise isn't a move. */
export const MIN_PRICE = 1000;
/** "Lowest since…" is only shown when it reaches back at least this many days. */
export const MIN_CONTEXT_DAYS = 60;
/** "Lowest on record / since release" needs at least this much history to mean anything. */
export const MIN_RECORD_HISTORY_DAYS = 365;
export const MAX_MOVERS = 5;
/** Aim for this many risers and this many fallers before filling up by size. */
export const PER_SIDE = 2;

/**
 * The recap covers the last *complete* week as seen from `today`: the guide
 * price on the most recent Sunday strictly before `today` against the Sunday
 * before that. Run on a Monday it is always the week that just ended.
 * @param {number} today day number (days since 1970-01-01, UTC)
 * @returns {{start:number, end:number}} both are Sundays
 */
export function recapWindow(today) {
  const dow = (((today + 4) % 7) + 7) % 7; // 1970-01-01 was a Thursday; 0 = Sunday
  const end = today - (dow === 0 ? 7 : dow);
  return { start: end - 7, end };
}

/**
 * One item's move across the window, or null if it should not be considered.
 * @param {import("../../public/assets/js/lib/rpi.js").PriceSeries|null} series
 */
export function itemMove(series, startDay, endDay) {
  if (!series || series.empty) return null;
  if (series.end < endDay - 2) return null; // stale or delisted: data stops before the window ends
  const oldPrice = series.asof(startDay);
  const newPrice = series.asof(endDay);
  if (!(oldPrice > 0) || !(newPrice > 0)) return null;
  if (Math.min(oldPrice, newPrice) < MIN_PRICE) return null;
  const ratio = newPrice / oldPrice;
  if (ratio > MAX_PRICE_RATIO || ratio < 1 / MAX_PRICE_RATIO) return null; // likely a data glitch
  return { oldPrice, newPrice, change: pctChange(oldPrice, newPrice) };
}

/**
 * How long the price has been out of this range: the last day strictly before
 * `endDay` on which it was lower (direction < 0) or higher (direction > 0)
 * than it is on `endDay`.
 * @returns {{kind:"since", day:number}|{kind:"ever"}|{kind:"release"}}
 */
export function lookback(series, endDay, direction) {
  const price = series.asof(endDay);
  for (let d = Math.min(endDay, series.end) - 1; d >= series.start; d--) {
    const p = series.prices[d - series.start];
    if (direction < 0 ? p < price : p > price) return { kind: "since", day: d };
  }
  return { kind: series.start <= HISTORY_START_DAY + 7 ? "ever" : "release" };
}

export function spanText(days) {
  if (days < 548) return `${Math.max(1, Math.round(days / 30.44))} months`;
  return `${(days / 365.25).toFixed(1)} years`;
}

/** Human sentence for a lookback result, or null if it isn't notable enough to show. */
export function contextText(series, endDay, direction) {
  const ctx = lookback(series, endDay, direction);
  const word = direction < 0 ? "lowest" : "highest";
  if (ctx.kind === "since") {
    const span = endDay - ctx.day;
    if (span < MIN_CONTEXT_DAYS) return null;
    return `${word[0].toUpperCase()}${word.slice(1)} since ${formatDay(ctx.day, { month: "long", year: "numeric" })} (${spanText(span)} ago)`;
  }
  if (endDay - series.start < MIN_RECORD_HISTORY_DAYS) return null;
  return ctx.kind === "ever" ? `Its ${word} price on record` : `Its ${word} price since release`;
}

/** Strips dose / charge suffixes so "Prayer potion(3)" and "Prayer potion(4)" are one family. */
export function familyKey(name) {
  return name.toLowerCase().replace(/\s*\((\d|unf|uncharged)\)$/, "").trim();
}

const firstWord = (name) => name.toLowerCase().split(/[\s']/)[0];

/** Same family if the base name matches, or they share a first word and moved together (armour sets etc). */
export function sameFamily(a, b) {
  if (familyKey(a.name) === familyKey(b.name)) return true;
  return firstWord(a.name) === firstWord(b.name) && Math.sign(a.change) === Math.sign(b.change) && Math.abs(a.change - b.change) < 2;
}

/**
 * Picks the items to report: biggest raw moves, one per family, with up to
 * `perSide` risers and `perSide` fallers guaranteed before filling by size.
 * @param {Array<{name:string, change:number}>} moves
 * @returns moves sorted by absolute size, at most `max` of them
 */
export function selectMovers(moves, { max = MAX_MOVERS, perSide = PER_SIDE, minMove = MIN_MOVE_PCT } = {}) {
  const ranked = moves.filter((m) => Math.abs(m.change) >= minMove).sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
  const kept = [];
  for (const m of ranked) if (!kept.some((k) => sameFamily(k, m))) kept.push(m);

  const chosen = new Set([...kept.filter((m) => m.change > 0).slice(0, perSide), ...kept.filter((m) => m.change < 0).slice(0, perSide)]);
  for (const m of kept) {
    if (chosen.size >= max) break;
    chosen.add(m);
  }
  return kept.filter((m) => chosen.has(m)).slice(0, max);
}

// ---------- week summaries (context for the written intro) ----------

/**
 * Weighted average weekly change per basket category.
 * @param {Array<{name:string, weight:number, change:number}>} rows items from pointRpi()
 * @param {Record<string,string>} categoryOf item name -> category name
 * @returns {Array<{name:string, change:number, items:number}>} sorted from biggest riser to biggest faller
 */
export function categoryChanges(rows, categoryOf) {
  const by = new Map();
  for (const r of rows) {
    const c = categoryOf[r.name];
    if (!c) continue;
    const b = by.get(c) || { w: 0, wc: 0, n: 0 };
    b.w += r.weight;
    b.wc += r.weight * r.change;
    b.n += 1;
    by.set(c, b);
  }
  return [...by].map(([name, b]) => ({ name, change: b.wc / b.w, items: b.n })).sort((a, b) => b.change - a.change);
}

/** How widespread the week's movement was: items up, down, or within +/- `flatBand` %. */
export function breadth(rows, flatBand = 0.5) {
  let up = 0, down = 0, flat = 0;
  for (const r of rows) {
    if (r.change > flatBand) up++;
    else if (r.change < -flatBand) down++;
    else flat++;
  }
  return { up, down, flat };
}

// ---------- formatting ----------

export function fmtPct(v, digits = 1) {
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${Math.abs(v).toFixed(digits)}%`;
}

export function fmtGp(v) {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}b`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}m`;
  if (v >= 1e4) return `${(v / 1e3).toFixed(1)}k`;
  return Math.round(v).toLocaleString("en-GB");
}

/** Escapes Discord markdown so item names can't break formatting. */
export const escapeMd = (s) => String(s).replace(/[\\*_~`|>]/g, "\\$&");

/** "28 Sep – 4 Oct 2026": the days the week's movement happened on (Monday to Sunday). */
export function weekLabel(win) {
  const d = { day: "numeric", month: "short" };
  return `${formatDay(win.start + 1, d)} – ${formatDay(win.end, { ...d, year: "numeric" })}`;
}

/**
 * @param {{window:{start:number,end:number}, movers:Array<{name:string,change:number,oldPrice:number,newPrice:number,context:string|null}>,
 *          basket:{value:number|null, items:number}|null, siteUrl?:string}} r
 */
export function buildEmbed({ window: win, movers, basket, siteUrl, commentary }) {
  const lines = [];
  if (commentary) lines.push(escapeMd(commentary), "");
  if (basket && basket.value != null) {
    lines.push(`**Basket index:** ${fmtPct(basket.value, 2)} on the week (${basket.items} items)`, "");
  }
  if (!movers.length) {
    lines.push(`A quiet week: no item in the basket moved by ${MIN_MOVE_PCT}% or more.`);
  }
  for (const m of movers) {
    lines.push(`${m.change > 0 ? "🔺" : "🔻"} **${escapeMd(m.name)}** ${fmtPct(m.change)}  (${fmtGp(m.oldPrice)} → ${fmtGp(m.newPrice)} gp)`);
    if (m.context) lines.push(`> ${m.context}`);
  }
  const embed = {
    title: `OSRS Grand Exchange recap · ${weekLabel(win)}`,
    description: lines.join("\n"),
    color: 0xc9a227,
    footer: { text: `Sunday ${fromDay(win.start)} → Sunday ${fromDay(win.end)} · GE guide prices via Weird Gloop` },
  };
  if (siteUrl) embed.url = siteUrl;
  return embed;
}

/** Webhook body. Mentions are disabled so nothing in the text can ping anyone. */
export const discordPayload = (embed) => ({ username: "OSRS RPI", embeds: [embed], allowed_mentions: { parse: [] } });
