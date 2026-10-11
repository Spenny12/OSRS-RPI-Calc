// Pure RPI maths, no DOM. Mirrors the original Python calculator.py logic.
import { minusYears, previousMonth, parts, dayOf } from "./dates.js";

/** A gap-filled daily price series. */
export class PriceSeries {
  constructor({ start, prices }) {
    this.start = start;
    this.prices = prices || [];
    this.end = start + this.prices.length - 1;
  }
  get empty() {
    return this.start == null || this.prices.length === 0;
  }
  /** Last known price on or before `day` (pandas .asof()). */
  asof(day) {
    if (this.empty || day < this.start) return null;
    return this.prices[Math.min(day, this.end) - this.start];
  }
  /** The actual day whose price `asof(day)` returns. */
  asofDay(day) {
    if (this.empty || day < this.start) return null;
    return Math.min(day, this.end);
  }
  /** Mean daily price over [from, to] inclusive, using only days with data. */
  average(from, to) {
    if (this.empty) return null;
    const lo = Math.max(from, this.start);
    const hi = Math.min(to, this.end);
    if (lo > hi) return null;
    let sum = 0;
    for (let d = lo; d <= hi; d++) sum += this.prices[d - this.start];
    return sum / (hi - lo + 1);
  }
}

export const pctChange = (oldP, newP) => ((newP - oldP) / oldP) * 100;

const valid = (p) => p != null && Number.isFinite(p) && p > 0;

function combine(rows, excluded) {
  const totalWeight = rows.reduce((s, r) => s + r.weight, 0);
  if (totalWeight === 0) return { value: null, items: [], excluded };
  let value = 0;
  for (const r of rows) {
    r.share = r.weight / totalWeight;
    r.contribution = r.change * r.share;
    value += r.contribution;
  }
  return { value, items: rows, excluded };
}

/**
 * Weighted basket inflation between two single days (point-in-time prices).
 * @param {Record<string, number>} basket   itemName -> weight
 * @param {(name:string)=>PriceSeries|null} getSeries
 */
export function pointRpi(basket, getSeries, startDay, endDay) {
  const rows = [];
  const excluded = [];
  for (const [name, weight] of Object.entries(basket)) {
    if (!(weight > 0)) continue;
    const s = getSeries(name);
    if (!s || s.empty) { excluded.push({ name, reason: "No price data available" }); continue; }
    const oldP = s.asof(startDay);
    const newP = s.asof(endDay);
    if (!valid(oldP)) { excluded.push({ name, reason: "No price on or before the start date" }); continue; }
    if (!valid(newP)) { excluded.push({ name, reason: "No price on or before the end date" }); continue; }
    rows.push({ name, weight, oldPrice: oldP, newPrice: newP, change: pctChange(oldP, newP) });
  }
  return combine(rows, excluded);
}

/** Weighted basket inflation comparing average prices over two periods. */
export function periodRpi(basket, getSeries, oldRange, newRange) {
  const rows = [];
  const excluded = [];
  for (const [name, weight] of Object.entries(basket)) {
    if (!(weight > 0)) continue;
    const s = getSeries(name);
    if (!s || s.empty) { excluded.push({ name, reason: "No price data available" }); continue; }
    const oldP = s.average(oldRange.start, oldRange.end);
    const newP = s.average(newRange.start, newRange.end);
    if (!valid(oldP)) { excluded.push({ name, reason: "No prices in the earlier period" }); continue; }
    if (!valid(newP)) { excluded.push({ name, reason: "No prices in the later period" }); continue; }
    rows.push({ name, weight, oldPrice: oldP, newPrice: newP, change: pctChange(oldP, newP) });
  }
  return combine(rows, excluded);
}

/** Year-on-year comparison of the last full month before `anchorDay`. */
export function lastMonthYoY(basket, getSeries, anchorDay) {
  const cur = previousMonth(anchorDay);
  const prev = { start: minusYears(cur.start), end: minusYears(cur.end) };
  return { ...periodRpi(basket, getSeries, prev, cur), current: cur, previous: prev };
}

/**
 * Monthly YoY RPI history, newest month first back to the first month whose
 * comparison year is 2015 or later (same stopping rules as the Python app).
 * @returns {Array<{month:number, value:number, itemCount:number}>} oldest first; month = last day of month
 */
export function monthlyHistory(basket, getSeries, todayDay, maxMonths = 240) {
  const out = [];
  let { y, m } = parts(todayDay);
  for (let i = 0; i < maxMonths; i++) {
    const firstOfMonth = dayOf(y, m, 1);
    const cur = previousMonth(firstOfMonth + 1);
    const prev = { start: minusYears(cur.start), end: minusYears(cur.end) };
    if (parts(prev.start).y <= 2014) break;
    const r = periodRpi(basket, getSeries, prev, cur);
    if (r.value == null) break;
    out.push({ month: cur.end, value: r.value, itemCount: r.items.length });
    m -= 1;
    if (m < 0) { m = 11; y -= 1; }
  }
  return out.reverse();
}

/** Inflation for one item between two days. */
export function singleItem(series, startDay, endDay) {
  if (!series || series.empty) return { error: "No price history is available for this item." };
  const oldP = series.asof(startDay);
  const newP = series.asof(endDay);
  if (!valid(oldP)) return { error: "This item has no price data on or before the start date (it may not have existed yet)." };
  if (!valid(newP)) return { error: "This item has no price data on or before the end date." };
  return {
    oldPrice: oldP,
    newPrice: newP,
    actualStart: series.asofDay(startDay),
    actualEnd: series.asofDay(endDay),
    change: pctChange(oldP, newP),
  };
}
