import test from "node:test";
import assert from "node:assert/strict";
import { pick, moodSentence, categorySentence, breadthSentence, standoutSentence, trendSentence, moversSentence, atPhrase, writeIntro, STANDOUT_DAYS, MAX_SENTENCES } from "../scripts/lib/intro.mjs";
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
  const mild = categorySentence(cats(2.9, -2.9), SEED);
  assert.ok(mild.includes("Runes") && mild.includes("Herbs") && mild.includes("+2.9%") && mild.includes("−2.9%"), "just under the standout bar still gets a milder mention");
  assert.equal(categorySentence(cats(0.4, -0.4), SEED), null, "differences this small aren't worth a sentence");
  assert.ok(categorySentence([{ name: "Solo", change: 1 }], SEED).includes("Solo"));
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

test("trend sentence spots streaks, turnarounds, breathers and big moves", () => {
  const t = (value, previous) => trendSentence({ value }, previous, SEED);
  assert.match(t(1.2, [0.8, 0.5, -1]), /3 weeks/, "this week plus two before it");
  assert.match(t(-1.2, [-0.8, -0.5, -0.4, 0.2]), /4 weeks/);
  assert.match(t(1.2, [-0.9, 0.5]), /0\.90%/, "turnaround quotes last week's figure");
  assert.match(t(-2.5, [0.2, 0.1, 0.2, 0.1, 0.2, 0.1, 0.2, 0.1]), /biggest weekly fall in at least 8 weeks/);
  assert.equal(t(1.5, [0.2, 0.1]), null, "an ordinary week adds nothing");
  assert.match(t(0.1, [3.2, 0.1]), /3\.20%/, "a calm week after a big one is called a breather");
  assert.equal(t(0.1, [0.2]), null);
  assert.equal(t(1, []), null);
  assert.equal(t(1, [null, null]), null);
  assert.equal(trendSentence(null, [1], SEED), null);
});

test("movers sentence names the best riser and worst faller", () => {
  const mv = (name, change) => ({ name, change });
  const both = moversSentence([mv("Big drop", -23), mv("Big rise", 16), mv("Small rise", 9), mv("Small drop", -8)], SEED);
  assert.ok(both.includes("Big rise") && both.includes("+16.0%") && both.includes("Big drop") && both.includes("−23.0%"));
  assert.ok(!both.includes("Small"));
  const onlyUp = moversSentence([mv("Solo", 12)], SEED);
  assert.ok(onlyUp.includes("Solo") && onlyUp.includes("+12.0%"));
  assert.equal(moversSentence([], SEED), null);
  assert.equal(moversSentence(undefined, SEED), null);
});

const STAR = { name: "Dragon bones", change: -23, context: "Lowest since March 2021 (5.6 years ago)", lookbackDays: 2045 };
const RISER = { name: "Nature rune", change: 16, context: null, lookbackDays: 0 };
const CATS = [{ name: "Runes & magic supplies", change: 12.3 }, { name: "Mid", change: 0.4 }, { name: "Herblore ingredients", change: -8.1 }];
const SCENARIOS = {
  rich: { basket: { value: 1.84 }, breadth: { up: 410, down: 180, flat: 58 }, categories: CATS, movers: [STAR, RISER], previous: [-0.5, 0.4, 1.1, -0.2, 0.9, 0.3, -1.4, 0.7, 0.2, -0.6, 0.1, 0.8] },
  streak: { basket: { value: 1.5 }, breadth: { up: 410, down: 180, flat: 58 }, categories: CATS, movers: [STAR, RISER], previous: [0.9, 0.6, 0.4, -0.1, 0.2, 0.3, 0.1, 0.1, 0.2, 0.1, 0.2, 0.1] },
  quiet: { basket: { value: -0.04 }, breadth: { up: 200, down: 210, flat: 238 }, categories: [{ name: "A", change: 1 }, { name: "B", change: -1 }], movers: [], previous: [0.2, -0.1, 0.3, 0.1] },
  noBasket: { basket: null, breadth: { up: 1, down: 1, flat: 1 }, categories: [], movers: [], previous: [] },
  empty: { basket: null, breadth: null, categories: [], movers: [], previous: [] },
};

const sentences = (t) => (t.match(/[.!?](\s|$)/g) || []).length;

test("writeIntro is a short paragraph, within the cap, and varies by week", () => {
  for (const [name, week] of Object.entries(SCENARIOS)) {
    const texts = new Set();
    for (let w = 0; w < 120; w++) {
      const t = writeIntro(week, SEED + 7 * w);
      if (name === "empty") { assert.equal(t, ""); continue; }
      assert.ok(t.length > 20 && t.length <= 700, `${name} week ${w}: ${t.length} chars`);
      assert.ok(sentences(t) <= MAX_SENTENCES, `${name}: at most ${MAX_SENTENCES} sentences`);
      assert.ok(t.trim() === t && !/\s{2,}/.test(t), "tidy whitespace");
      if (name === "rich" || name === "streak") assert.ok(sentences(t) >= 4, `${name}: a full week gets a proper paragraph, got ${sentences(t)}: ${t}`);
      if (name === "quiet") assert.ok(sentences(t) >= 3, `${name}: even a quiet week gets a few sentences: ${t}`);
      texts.add(t);
    }
    if (name !== "empty") assert.ok(texts.size > (name === "noBasket" ? 1 : 3), `${name}: wording rotates (got ${texts.size} variants)`);
  }
  assert.equal(writeIntro(SCENARIOS.rich, SEED), writeIntro(SCENARIOS.rich, SEED), "same week, same text");
});

test("when there is more to say than fits, the least interesting parts are dropped first", () => {
  const t = writeIntro(SCENARIOS.streak, SEED); // trend + mood + breadth + category + movers + standout = 6
  assert.ok(sentences(t) <= MAX_SENTENCES);
  assert.match(t, /weeks/, "the streak is kept");
  assert.ok(!/of 648/.test(t) && !/410 of/.test(t), "the breadth line goes first");
  assert.ok(t.includes("Dragon bones") && t.includes("Runes & magic supplies"), "standout and category are kept");
});

test("every percentage in the intro comes from the data", () => {
  const f = (v, d) => `${Math.abs(v).toFixed(d)}%`;
  for (const [name, w] of Object.entries(SCENARIOS)) {
    const allowed = new Set([
      w.basket?.value != null && f(w.basket.value, 2),
      w.previous[0] != null && f(w.previous[0], 2),
      ...w.categories.map((c) => f(c.change, 1)),
      ...w.movers.map((m) => f(m.change, 1)),
    ].filter(Boolean));
    for (let i = 0; i < 120; i++) {
      for (const p of writeIntro(w, SEED + 7 * i).match(/\d+(?:\.\d+)?%/g) || []) assert.ok(allowed.has(p), `${name}: unexpected figure ${p}`);
    }
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
