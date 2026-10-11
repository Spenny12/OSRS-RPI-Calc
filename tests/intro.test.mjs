import test from "node:test";
import assert from "node:assert/strict";
import { pick, moodSentence, categorySentence, breadthSentence, standoutSentence, atPhrase, writeIntro, STANDOUT_DAYS } from "../scripts/lib/intro.mjs";
import { categoryChanges, breadth, buildEmbed } from "../scripts/lib/recap.mjs";
import { toDay } from "../public/assets/js/lib/dates.js";

const SEED = toDay("2026-10-11");

test("pick is deterministic and rotates across weeks", () => {
  const opts = ["a", "b", "c", "d"];
  assert.equal(pick(opts, SEED, 1), pick(opts, SEED, 1));
  const seen = new Set();
  for (let w = 0; w < 52; w++) seen.add(pick(opts, SEED + 7 * w, 1));
  assert.equal(seen.size, opts.length, "every phrasing gets used over a year of Mondays");
});

test("categoryChanges weights within each category and sorts risers first", () => {
  const rows = [
    { name: "A", weight: 3, change: 10 }, { name: "B", weight: 1, change: -10 }, // cat X: (30-10)/4 = 5
    { name: "C", weight: 2, change: -6 }, // cat Y: -6
    { name: "Z", weight: 9, change: 99 }, // no category: ignored
  ];
  const out = categoryChanges(rows, { A: "X", B: "X", C: "Y" });
  assert.deepEqual(out.map((c) => [c.name, c.change, c.items]), [["X", 5, 2], ["Y", -6, 1]]);
});

test("breadth counts up, down and flat with a +/-0.5% band", () => {
  const rows = [3, 0.6, 0.5, 0, -0.5, -0.6, -8].map((change) => ({ change }));
  assert.deepEqual(breadth(rows), { up: 2, down: 2, flat: 3 });
});

test("mood sentence scales with the basket move and quotes the figure without a stray plus sign", () => {
  const mood = (value) => moodSentence({ value }, SEED);
  assert.match(mood(0.1), /0\.10%|0\.1/);
  assert.match(mood(1.234), /1\.23%/);
  assert.match(mood(-1.234), /1\.23%/);
  assert.match(mood(4.5), /4\.50%/);
  assert.match(mood(-4.5), /4\.50%/);
  assert.ok(!/\+\d/.test(mood(1.234)), "no '+1.23%' inside a sentence that already says 'up'");
  assert.equal(moodSentence(null, SEED), null);
  assert.equal(moodSentence({ value: null }, SEED), null);
  assert.notEqual(mood(4.5), mood(-4.5), "up and down are worded differently");
});

test("category sentence needs a 3% move and names the right categories", () => {
  const cats = (a, b) => [{ name: "Runes", change: a }, { name: "Middle", change: 0 }, { name: "Herbs", change: b }];
  const both = categorySentence(cats(12.3, -8.1), SEED);
  assert.ok(both.includes("Runes") && both.includes("Herbs") && both.includes("+12.3%") && both.includes("−8.1%"));
  const onlyUp = categorySentence(cats(5, -1), SEED);
  assert.ok(onlyUp.includes("Runes") && !onlyUp.includes("Herbs"));
  const onlyDown = categorySentence(cats(1, -5), SEED);
  assert.ok(onlyDown.includes("Herbs") && !onlyDown.includes("Runes"));
  assert.equal(categorySentence(cats(2.9, -2.9), SEED), null);
  assert.equal(categorySentence([], SEED), null);
});

test("breadth sentence distinguishes broad rises, broad falls and mixed weeks", () => {
  assert.match(breadthSentence({ up: 70, down: 20, flat: 10 }, SEED), /70 of 100/);
  assert.match(breadthSentence({ up: 20, down: 70, flat: 10 }, SEED), /70 of 100/);
  assert.match(breadthSentence({ up: 40, down: 40, flat: 20 }, SEED), /40 items/);
  assert.equal(breadthSentence({ up: 0, down: 0, flat: 0 }, SEED), null);
});

test("standout picks the longest look-back of a year or more", () => {
  const mv = (name, change, context, lookbackDays) => ({ name, change, context, lookbackDays });
  const s = standoutSentence([
    mv("Short", -9, "Lowest since June 2026 (4 months ago)", 120),
    mv("Mid", 12, "Highest since May 2024 (2.4 years ago)", 880),
    mv("Long", -15, "Lowest since March 2021 (5.6 years ago)", 2045),
    mv("None", 8, null, 0),
  ], SEED);
  assert.ok(s.includes("Long") && s.includes("lowest since March 2021 (5.6 years ago)"));
  assert.equal(standoutSentence([mv("Short", -9, "Lowest since June 2026 (4 months ago)", STANDOUT_DAYS - 1)], SEED), null);
  const record = standoutSentence([mv("Rare", -20, "Its lowest price on record", Infinity)], SEED);
  assert.ok(record.includes("at its lowest price on record"));
  assert.equal(standoutSentence([], SEED), null);
  assert.equal(atPhrase("Highest since July 2019 (7.3 years ago)"), "at its highest since July 2019 (7.3 years ago)");
  assert.equal(atPhrase("Its lowest price since release"), "at its lowest price since release");
});

const SCENARIOS = {
  rich: {
    basket: { value: 1.84 },
    breadth: { up: 410, down: 180, flat: 58 },
    categories: [{ name: "Runes & magic supplies", change: 12.3 }, { name: "Mid", change: 0.4 }, { name: "Herblore ingredients", change: -8.1 }],
    movers: [{ name: "Dragon bones", change: -23, context: "Lowest since March 2021 (5.6 years ago)", lookbackDays: 2045 }, { name: "Nature rune", change: 16, context: null, lookbackDays: 0 }],
  },
  quiet: { basket: { value: -0.04 }, breadth: { up: 200, down: 210, flat: 238 }, categories: [{ name: "A", change: 1 }, { name: "B", change: -1 }], movers: [] },
  noBasket: { basket: null, breadth: { up: 1, down: 1, flat: 1 }, categories: [], movers: [] },
  empty: { basket: null, breadth: null, categories: [], movers: [] },
};

test("writeIntro is 1-3 sentences, never too long, and varies by week", () => {
  for (const [name, week] of Object.entries(SCENARIOS)) {
    const texts = new Set();
    for (let w = 0; w < 120; w++) {
      const t = writeIntro(week, SEED + 7 * w);
      if (name === "empty") { assert.equal(t, ""); continue; }
      assert.ok(t.length > 20 && t.length <= 500, `${name} week ${w}: ${t.length} chars`);
      assert.ok((t.match(/[.!?](\s|$)/g) || []).length <= 3, `${name}: at most 3 sentences`);
      assert.ok(t.trim() === t && !/\s{2,}/.test(t), "tidy whitespace");
      texts.add(t);
    }
    if (name !== "empty") assert.ok(texts.size > (name === "noBasket" ? 1 : 3), `${name}: wording rotates (got ${texts.size} variants)`);
  }
  assert.equal(writeIntro(SCENARIOS.rich, SEED), writeIntro(SCENARIOS.rich, SEED), "same week, same text");
});

test("every percentage in the intro comes from the data", () => {
  const w = SCENARIOS.rich;
  const allowed = new Set(["1.84%", "12.3%", "8.1%", "23.0%", "16.0%"]);
  for (let i = 0; i < 120; i++) {
    for (const p of writeIntro(w, SEED + 7 * i).match(/\d+(?:\.\d+)?%/g) || []) assert.ok(allowed.has(p), `unexpected figure ${p}`);
  }
});

test("the intro never claims a reason for price moves", () => {
  const reasons = /\b(because|due to|thanks to|update|patch|nerf|buff|bots?|jagex)\b/i;
  for (const week of Object.values(SCENARIOS)) for (let i = 0; i < 120; i++) assert.ok(!reasons.test(writeIntro(week, SEED + 7 * i)));
});

test("embed puts the intro first and escapes markdown in it", () => {
  const win = { start: toDay("2026-10-04"), end: toDay("2026-10-11") };
  const e = buildEmbed({ window: win, movers: [], basket: { value: 0.1, items: 600 }, commentary: "A *lively* week_for gp." });
  assert.ok(e.description.startsWith("A \\*lively\\* week\\_for gp.\n\n**Basket index:**"));
  const none = buildEmbed({ window: win, movers: [], basket: { value: 0.1, items: 600 }, commentary: "" });
  assert.ok(none.description.startsWith("**Basket index:**"), "no blank gap when there is no intro");
});
