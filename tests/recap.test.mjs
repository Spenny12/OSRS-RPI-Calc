import test from "node:test";
import assert from "node:assert/strict";
import { PriceSeries, HISTORY_START_DAY } from "../public/assets/js/lib/rpi.js";
import { toDay, fromDay } from "../public/assets/js/lib/dates.js";
import {
  recapWindow, itemMove, lookback, contextText, spanText, familyKey, selectMovers,
  buildEmbed, discordPayload, escapeMd, fmtPct, fmtGp, MIN_PRICE,
} from "../scripts/lib/recap.mjs";

const flat = (start, len, price) => new PriceSeries({ start, prices: new Array(len).fill(price) });

test("recap window is the last complete Sunday-to-Sunday week", () => {
  const win = (iso) => { const w = recapWindow(toDay(iso)); return [fromDay(w.start), fromDay(w.end)]; };
  assert.deepEqual(win("2026-10-12"), ["2026-10-04", "2026-10-11"]); // Monday run: the week that just ended
  assert.deepEqual(win("2026-10-14"), ["2026-10-04", "2026-10-11"]); // mid-week manual run: same week
  assert.deepEqual(win("2026-10-18"), ["2026-10-04", "2026-10-11"]); // Saturday: Sunday 18th isn't finished
  assert.deepEqual(win("2026-10-11"), ["2026-09-27", "2026-10-04"]); // Sunday: previous full week
  assert.equal(new Date(toDay("2026-10-11") * 86_400_000).getUTCDay(), 0, "sanity: 11 Oct 2026 is a Sunday");
});

test("itemMove computes the change and rejects unusable items", () => {
  const end = 1000, start = 993;
  const ok = new PriceSeries({ start: 900, prices: Array.from({ length: 120 }, (_, i) => (900 + i <= start ? 2000 : 1500)) });
  const m = itemMove(ok, start, end);
  assert.equal(m.oldPrice, 2000);
  assert.equal(m.newPrice, 1500);
  assert.ok(Math.abs(m.change + 25) < 1e-9);
  assert.equal(itemMove(null, start, end), null);
  assert.equal(itemMove(flat(900, 120, MIN_PRICE - 1), start, end), null, "below minimum price");
  assert.equal(itemMove(new PriceSeries({ start: 900, prices: [...new Array(94).fill(1000), ...new Array(26).fill(50_000)] }), start, end), null, "50x spike is a glitch");
  assert.equal(itemMove(flat(900, 60, 5000), start, end), null, "data stops well before the week ends");
  assert.equal(itemMove(flat(995, 50, 5000), start, end), null, "didn't exist at the start of the week");
});

test("lookback finds the last time the price was lower or higher", () => {
  // day 0..9 price 50 (low), days 10..19 price 100, days 20..24 price 80
  const s = new PriceSeries({ start: 0, prices: [...new Array(10).fill(50), ...new Array(10).fill(100), ...new Array(5).fill(80)] });
  assert.deepEqual(lookback(s, 24, -1), { kind: "since", day: 9 }); // 80 was last beaten by 50 on day 9
  assert.deepEqual(lookback(s, 24, +1), { kind: "since", day: 19 }); // 80 last beaten from above on day 19
  const low = new PriceSeries({ start: HISTORY_START_DAY, prices: [100, 90, 80, 70, 60] });
  assert.deepEqual(lookback(low, HISTORY_START_DAY + 4, -1), { kind: "ever" });
  const young = new PriceSeries({ start: 20_000, prices: [100, 90, 80] });
  assert.deepEqual(lookback(young, 20_002, -1), { kind: "release" });
});

test("a price that has stayed flat since a drop still reports the long look-back", () => {
  // 2000 for ages, then fell to 900 and stayed there; it was last below 900 long ago
  const s = new PriceSeries({ start: 0, prices: [...new Array(5).fill(800), ...new Array(2000).fill(2000), ...new Array(10).fill(900)] });
  const end = s.end;
  const text = contextText(s, end, -1);
  assert.match(text, /^Lowest since .+ \(5\.\d years ago\)$/);
});

test("context is omitted when the look-back is short or the history too young", () => {
  const s = new PriceSeries({ start: 0, prices: [...new Array(80).fill(100), ...new Array(10).fill(50)] });
  assert.equal(contextText(s, 89, -1), null, "never lower within 80 days → 'ever', but history < 1y so omitted");
  const recent = new PriceSeries({ start: 0, prices: [...new Array(400).fill(100), ...new Array(100).fill(50), 90] });
  assert.match(contextText(recent, recent.end, +1), /^Highest since .+ \(3 months ago\)$/);
  const brief = new PriceSeries({ start: 0, prices: [...new Array(400).fill(100), 40, ...new Array(30).fill(90), 70] });
  assert.equal(contextText(brief, brief.end, -1), null, "lower only 31 days ago → under 60-day threshold");
  const record = new PriceSeries({ start: HISTORY_START_DAY, prices: [...new Array(500).fill(100), 40] });
  assert.equal(contextText(record, record.end, -1), "Its lowest price on record");
});

test("spanText switches from months to years", () => {
  assert.equal(spanText(90), "3 months");
  assert.equal(spanText(2045), "5.6 years");
});

test("family keys collapse doses", () => {
  assert.equal(familyKey("Prayer potion(4)"), familyKey("Prayer potion(3)"));
  assert.equal(familyKey("Ranarr potion (unf)"), "ranarr potion");
  assert.notEqual(familyKey("Shark"), familyKey("Raw shark"));
});

test("selectMovers balances risers and fallers, collapses families and applies the minimum", () => {
  const mv = (name, change) => ({ name, change, oldPrice: 1000, newPrice: 1000 * (1 + change / 100) });
  const moves = [
    mv("Prayer potion(4)", -30), mv("Prayer potion(3)", -29.5), // same family → one
    mv("Torva platebody", 22), mv("Torva platelegs", 21.4), // same first word, moved together → one
    mv("Dragon bones", -18), mv("Rune bar", -17), mv("Nature rune", 9), mv("Cannonball", 7.5),
    mv("Shark", 3), mv("Yew logs", -4.9), // below the 5% minimum
  ];
  const picked = selectMovers(moves);
  const names = picked.map((m) => m.name);
  assert.equal(picked.length, 5);
  assert.ok(names.includes("Prayer potion(4)") && !names.includes("Prayer potion(3)"));
  assert.ok(names.includes("Torva platebody") && !names.includes("Torva platelegs"));
  assert.ok(!names.includes("Shark") && !names.includes("Yew logs"));
  assert.ok(picked.filter((m) => m.change > 0).length >= 2, "at least two risers");
  assert.ok(picked.filter((m) => m.change < 0).length >= 2, "at least two fallers");
  assert.deepEqual(picked.map((m) => Math.abs(m.change)), [...picked.map((m) => Math.abs(m.change))].sort((a, b) => b - a), "sorted by size");
  assert.deepEqual(selectMovers([mv("Shark", 2)]), []);
});

test("selectMovers fills with whatever exists when one side is empty", () => {
  const mv = (name, change) => ({ name, change });
  const picked = selectMovers([mv("A item", -40), mv("B item", -30), mv("C item", -20), mv("D item", -10), mv("E item", -9), mv("F item", -8)]);
  assert.equal(picked.length, 5);
  assert.ok(picked.every((m) => m.change < 0));
});

test("embed formatting, escaping, quiet week and limits", () => {
  const win = { start: toDay("2026-10-04"), end: toDay("2026-10-11") };
  const embed = buildEmbed({
    window: win,
    basket: { value: 1.234, items: 650 },
    movers: [
      { name: "Dragon *bones*", change: -14.23, oldPrice: 2690, newPrice: 2307, context: "Lowest since March 2021 (5.6 years ago)" },
      { name: "Nature rune", change: 9.5, oldPrice: 100_000, newPrice: 1_250_000, context: null },
    ],
    siteUrl: "https://example.test",
  });
  assert.match(embed.title, /5 Oct – 11 Oct 2026/);
  assert.match(embed.description, /\*\*Basket index:\*\* \+1\.23% on the week \(650 items\)/);
  assert.match(embed.description, /🔻 \*\*Dragon \\\*bones\\\*\*\* −14\.2%  \(2,690 → 2,307 gp\)\n> Lowest since March 2021/);
  assert.match(embed.description, /🔺 \*\*Nature rune\*\* \+9\.5%/);
  assert.ok(embed.description.length < 4096 && embed.title.length < 256);

  const quiet = buildEmbed({ window: win, movers: [], basket: null });
  assert.match(quiet.description, /quiet week/);

  const payload = discordPayload(embed);
  assert.deepEqual(payload.allowed_mentions, { parse: [] });
  assert.equal(payload.embeds.length, 1);
  assert.equal(escapeMd("a_b*c"), "a\\_b\\*c");
  assert.equal(fmtPct(-0.04), "−0.0%");
  assert.equal(fmtGp(1_250_000), "1.25m");
  assert.equal(fmtGp(12_300), "12.3k");
});
