import test from "node:test";
import assert from "node:assert/strict";
import { compactHistory } from "../public/assets/js/lib/compact.js";
import { PriceSeries, pointRpi, periodRpi, singleItem, withBurnIn, HISTORY_START_DAY } from "../public/assets/js/lib/rpi.js";
import { toDay, fromDay, minusYears, previousMonth } from "../public/assets/js/lib/dates.js";
import { DEFAULT_BASKET, BASKET_CATEGORIES, ITEM_ID } from "../public/assets/js/lib/basket.js";

const D = 86_400_000;

test("compactHistory buckets by UTC day, averages and forward-fills", () => {
  const c = compactHistory([
    { price: 100, timestamp: 10 * D },
    { price: 110, timestamp: 12 * D },
    { price: 130, timestamp: 12 * D + 3600_000 },
    { price: null, timestamp: 13 * D },
  ]);
  assert.deepEqual(c, { start: 10, prices: [100, 100, 120] });
  assert.equal(compactHistory([]), null);
});

test("leap days do not crash and map to 28 Feb", () => {
  assert.equal(fromDay(minusYears(toDay("2028-02-29"))), "2027-02-28");
  assert.equal(fromDay(minusYears(toDay("2026-10-11"))), "2025-10-11");
});

test("previousMonth returns the full prior calendar month", () => {
  const r = previousMonth(toDay("2024-03-15"));
  assert.equal(fromDay(r.start), "2024-02-01");
  assert.equal(fromDay(r.end), "2024-02-29");
  const j = previousMonth(toDay("2026-01-01"));
  assert.equal(fromDay(j.start), "2025-12-01");
});

test("PriceSeries asof / average semantics", () => {
  const s = new PriceSeries({ start: 100, prices: [10, 20, 30] });
  assert.equal(s.asof(99), null);
  assert.equal(s.asof(101), 20);
  assert.equal(s.asof(500), 30);
  assert.equal(s.average(0, 101), 15);
  assert.equal(s.average(200, 300), null);
});

test("basket RPI re-weights across items with data and excludes the rest", () => {
  const series = {
    A: new PriceSeries({ start: 0, prices: [100, 110] }),
    B: new PriceSeries({ start: 0, prices: [50, 40] }),
    C: new PriceSeries({ start: 1, prices: [5] }),
  };
  const r = pointRpi({ A: 3, B: 1, C: 6 }, (n) => series[n], 0, 1);
  assert.equal(r.items.length, 2);
  assert.equal(r.excluded[0].name, "C");
  assert.ok(Math.abs(r.value - (0.75 * 10 + 0.25 * -20)) < 1e-9);
  const p = periodRpi({ A: 1 }, (n) => series[n], { start: 0, end: 0 }, { start: 1, end: 1 });
  assert.ok(Math.abs(p.value - 10) < 1e-9);
  assert.equal(pointRpi({ Z: 1 }, () => null, 0, 1).value, null);
});

test("singleItem reports errors before an item existed", () => {
  const s = new PriceSeries({ start: 10, prices: [1, 2] });
  assert.ok(singleItem(s, 5, 11).error);
  assert.equal(singleItem(s, 10, 11).change, 100);
});

test("default basket is well formed", () => {
  const names = Object.keys(DEFAULT_BASKET);
  assert.ok(names.length > 500);
  assert.equal(BASKET_CATEGORIES.length, 13);
  assert.ok(Object.values(DEFAULT_BASKET).every((w) => w > 0));
  assert.ok(Math.abs(Object.values(DEFAULT_BASKET).reduce((a, b) => a + b, 0) - 100) < 0.01);
  for (const c of BASKET_CATEGORIES) {
    const sum = c.items.reduce((a, [, , w]) => a + w, 0);
    assert.ok(Math.abs(sum - c.share) < 0.01, c.name);
  }
  assert.equal(new Set(Object.values(ITEM_ID)).size, names.length, "unique ids");
  for (const must of ["Twisted bow", "Inquisitor's mace", "Scythe of Vitur (uncharged)", "Shark", "Runite bar", "Prayer potion(4)"])
    assert.ok(DEFAULT_BASKET[must] > 0, must);
});

test("outlier guard sets aside 10x price moves", () => {
  const series = { A: new PriceSeries({ start: 0, prices: [100, 110] }), B: new PriceSeries({ start: 0, prices: [1, 50] }) };
  const r = pointRpi({ A: 1, B: 1 }, (n) => series[n], 0, 1);
  assert.equal(r.items.length, 1);
  assert.match(r.excluded[0].reason, /50× up/);
  assert.equal(pointRpi({ A: 1, B: 1 }, (n) => series[n], 0, 1, { maxRatio: Infinity }).items.length, 2);
});

test("burn-in drops the first 60 days of newly released items only", () => {
  const old = new PriceSeries({ start: HISTORY_START_DAY, prices: new Array(100).fill(1) });
  assert.equal(withBurnIn(old), old);
  const fresh = new PriceSeries({ start: 20000, prices: new Array(100).fill(1) });
  assert.equal(withBurnIn(fresh).start, 20060);
  assert.equal(withBurnIn(new PriceSeries({ start: 20000, prices: [1, 2] })), null);
});
