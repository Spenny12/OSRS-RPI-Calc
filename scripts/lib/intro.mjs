// Writes the short, lightly whimsical intro for the weekly recap from the
// week's numbers. Pure and deterministic: no network, no AI service, no cost.
// The wording rotates from week to week (seeded by the week's end day) so it
// doesn't read the same every Monday, and it only ever states what the data
// shows. It never guesses at *why* prices moved.

import { fmtPct } from "./recap.mjs";

/** Weekly basket moves smaller than this (%) count as "flat". */
export const FLAT_BELOW = 0.3;
/** Weekly basket moves at least this big (%) count as "big". */
export const BIG_FROM = 2;
/** A category must move at least this much (%) to be called out as a standout. */
export const CATEGORY_CALLOUT = 3;
/** Below the standout bar, a category still gets a milder mention if it moved more than this (%). */
export const CATEGORY_MILD = 0.5;
/** The intro never runs longer than this many sentences. */
export const MAX_SENTENCES = 5;
/** A look-back at least this long (days) earns a "special mention". */
export const STANDOUT_DAYS = 365;

/** Deterministic pick: same seed + salt gives the same option. */
export function pick(options, seed, salt = 0) {
  const h = Math.imul((seed | 0) ^ Math.imul(salt + 1, 0x9e3779b1), 0x85ebca6b) >>> 0;
  return options[h % options.length];
}

const abs = (v, digits = 1) => `${Math.abs(v).toFixed(digits)}%`;
const lowerFirst = (s) => s.replace(/^./, (c) => c.toLowerCase());

// ---------- sentence builders; each returns a string or null ----------

export function moodSentence(basket, seed) {
  if (!basket || basket.value == null) return null;
  const v = basket.value;
  const a = abs(v, 2);
  const s = (opts) => pick(opts, seed, 1);
  if (Math.abs(v) < FLAT_BELOW) {
    return s([
      `A sleepy week on the Grand Exchange: the basket barely stirred (${fmtPct(v, 2)}).`,
      `Prices spent the week minding their own business, with the basket shifting just ${a}.`,
      `Not much to see here: the basket moved ${a} and the market seems to have taken the week off.`,
      `The Grand Exchange had a quiet one, the basket drifting ${a}, barely enough to wake a sleeping banker.`,
    ]);
  }
  if (Math.abs(v) < BIG_FROM) {
    return v > 0
      ? s([
          `Prices crept upwards this week, with the basket up ${a}.`,
          `A gentle climb for the basket (${a}), the kind of rise you only notice when you go shopping.`,
          `The basket rose ${a}, so a pile of gp bought very slightly less than it did last week.`,
        ])
      : s([
          `Prices eased off a touch, with the basket slipping ${a}.`,
          `The basket dipped ${a} this week, a small win for anyone with gp to spend.`,
          `A soft week for prices: the basket slid ${a}, and wallets everywhere let out a quiet sigh of relief.`,
        ]);
  }
  return v > 0
    ? s([
        `A lively one: the basket jumped ${a} this week, and gp had a bit of a lie-down afterwards.`,
        `Prices were on the march, with the basket up a hefty ${a}.`,
        `Hold onto your coin pouches: the basket surged ${a} this week.`,
      ])
    : s([
        `A bumper week for bargain hunters, with the basket tumbling ${a}.`,
        `Prices took a proper tumble this week, the basket falling ${a}.`,
        `The basket dropped ${a} this week, which is the Grand Exchange's way of having a clear-out.`,
      ]);
}

export function categorySentence(categories, seed) {
  if (!categories?.length) return null;
  const top = categories[0];
  const bottom = categories[categories.length - 1];
  const topUp = top.change >= CATEGORY_CALLOUT;
  const bottomDown = bottom.change <= -CATEGORY_CALLOUT;
  const s = (opts) => pick(opts, seed, 2);
  if (topUp && bottomDown) {
    return s([
      `${top.name} led the charge (${fmtPct(top.change)}) while ${bottom.name} sulked at the other end (${fmtPct(bottom.change)}).`,
      `${top.name} had the best week of the lot (${fmtPct(top.change)}); ${bottom.name} had the worst (${fmtPct(bottom.change)}).`,
      `By category, ${top.name} stole the show (${fmtPct(top.change)}) and ${bottom.name} headed for the exit (${fmtPct(bottom.change)}).`,
    ]);
  }
  if (topUp) {
    return s([
      `${top.name} stole the show by category (${fmtPct(top.change)}).`,
      `${top.name} was the standout category this week (${fmtPct(top.change)}).`,
    ]);
  }
  if (bottomDown) {
    return s([
      `${bottom.name} had the roughest week by category (${fmtPct(bottom.change)}).`,
      `${bottom.name} was the category to wince at this week (${fmtPct(bottom.change)}).`,
    ]);
  }
  // Nothing dramatic: still say who was ahead and who lagged, if there's any real difference.
  if (categories.length > 1 && top.change > CATEGORY_MILD && bottom.change < -CATEGORY_MILD) {
    return s([
      `By category, ${top.name} edged ahead (${fmtPct(top.change)}) while ${bottom.name} lagged (${fmtPct(bottom.change)}).`,
      `Category-wise, ${top.name} (${fmtPct(top.change)}) was on top and ${bottom.name} (${fmtPct(bottom.change)}) at the bottom.`,
    ]);
  }
  if (top.change > CATEGORY_MILD) {
    return s([
      `${top.name} was the pick of the categories (${fmtPct(top.change)}).`,
      `By category, ${top.name} did best (${fmtPct(top.change)}).`,
    ]);
  }
  if (categories.length > 1 && bottom.change < -CATEGORY_MILD) {
    return s([
      `${bottom.name} was the weakest category (${fmtPct(bottom.change)}).`,
      `By category, ${bottom.name} fared worst (${fmtPct(bottom.change)}).`,
    ]);
  }
  return null;
}

/**
 * How this week compares with the recent run of weeks: a streak, a turnaround,
 * or the biggest move in a while.
 * @param {{value:number|null}|null} basket this week
 * @param {Array<number|null>} previous earlier weekly basket changes (%), most recent first
 */
export function trendSentence(basket, previous, seed) {
  if (!basket || basket.value == null || !previous?.length) return null;
  const v = basket.value;
  const notable = (x) => x != null && Math.abs(x) >= FLAT_BELOW;
  const last = previous[0];
  const s = (opts) => pick(opts, seed, 5);
  if (notable(v)) {
    const dir = Math.sign(v);
    let run = 1;
    for (const p of previous) {
      if (notable(p) && Math.sign(p) === dir) run++;
      else break;
    }
    if (run >= 3) {
      return s([`That makes ${run} weeks of ${v > 0 ? "rises" : "falls"} in a row.`, `${run} weeks running now of ${v > 0 ? "rising" : "falling"} prices.`]);
    }
    if (notable(last) && Math.sign(last) !== dir) {
      return s([
        `That's a turnaround from last week, when the basket ${last > 0 ? "rose" : "fell"} ${abs(last, 2)}.`,
        `Last week went the other way, with the basket ${last > 0 ? "up" : "down"} ${abs(last, 2)}.`,
      ]);
    }
    const beaten = previous.some((p) => notable(p) && Math.sign(p) === dir && Math.abs(p) >= Math.abs(v));
    if (!beaten && Math.abs(v) >= 1 && previous.length >= 8) {
      return `That's the biggest weekly ${v > 0 ? "rise" : "fall"} in at least ${previous.length} weeks.`;
    }
    return null;
  }
  if (notable(last) && Math.abs(last) >= BIG_FROM) {
    return s([
      `A breather after last week, when the basket ${last > 0 ? "rose" : "fell"} ${abs(last, 2)}.`,
      `Things calmed down after last week's ${last > 0 ? "rise" : "fall"} of ${abs(last, 2)}.`,
    ]);
  }
  return null;
}

/** The week's best riser and worst faller at item level. `movers` is the list shown in the post. */
export function moversSentence(movers, seed) {
  const up = (movers || []).filter((m) => m.change > 0).sort((a, b) => b.change - a.change)[0];
  const down = (movers || []).filter((m) => m.change < 0).sort((a, b) => a.change - b.change)[0];
  const s = (opts) => pick(opts, seed, 6);
  if (up && down) {
    return s([
      `At item level, ${up.name} led the risers (${fmtPct(up.change)}) and ${down.name} the fallers (${fmtPct(down.change)}).`,
      `Item by item, ${up.name} climbed furthest (${fmtPct(up.change)}) while ${down.name} dropped furthest (${fmtPct(down.change)}).`,
      `The biggest swings belonged to ${up.name} (${fmtPct(up.change)}) and ${down.name} (${fmtPct(down.change)}).`,
    ]);
  }
  const one = up || down;
  if (!one) return null;
  return s([
    `${one.name} made the biggest splash at item level (${fmtPct(one.change)}).`,
    `At item level, ${one.name} (${fmtPct(one.change)}) had the week's biggest swing.`,
  ]);
}

export function breadthSentence(breadth, seed) {
  if (!breadth) return null;
  const total = breadth.up + breadth.down + breadth.flat;
  if (!total) return null;
  const s = (opts) => pick(opts, seed, 3);
  if (breadth.up / total >= 0.6) {
    return s([
      `${breadth.up} of ${total} items rose, so it was a broad rise rather than the work of a few show-offs.`,
      `The rise was widespread, with ${breadth.up} of ${total} items finishing higher.`,
    ]);
  }
  if (breadth.down / total >= 0.6) {
    return s([
      `${breadth.down} of ${total} items fell, so this was a broad slide rather than a few dramatic exits.`,
      `The drop was widespread, with ${breadth.down} of ${total} items finishing lower.`,
    ]);
  }
  return s([
    `A mixed bag underneath: ${breadth.up} items up, ${breadth.down} down.`,
    `Under the surface it was a tug of war, with ${breadth.up} items rising and ${breadth.down} falling.`,
  ]);
}

/** "Lowest since March 2021 (5.6 years ago)" -> "at its lowest since March 2021 (5.6 years ago)". */
export const atPhrase = (context) => `at its ${lowerFirst(context.replace(/^Its /, ""))}`;

export function standoutSentence(movers, seed) {
  const candidates = (movers || []).filter((m) => m.context && (m.lookbackDays ?? 0) >= STANDOUT_DAYS);
  if (!candidates.length) return null;
  const m = candidates.reduce((best, c) => (c.lookbackDays > best.lookbackDays ? c : best));
  const when = atPhrase(m.context);
  return pick(
    [
      `${m.name} gets a special mention, now ${when}.`,
      `Special mention to ${m.name} (${fmtPct(m.change)}), which is ${when}.`,
      `One to watch: ${m.name} is ${when} after a ${abs(m.change)} move.`,
    ],
    seed,
    4,
  );
}

/**
 * @param {{basket:{value:number|null}|null, breadth:{up:number,down:number,flat:number}|null,
 *          categories:Array<{name:string,change:number}>, movers:Array<{name:string,change:number,context:string|null,lookbackDays?:number}>}} week
 * @param {number} seed any integer that changes weekly (the week's end day number works)
 * @returns {string} up to MAX_SENTENCES sentences, or "" if there is nothing to say
 */
export function writeIntro({ basket, breadth, categories, movers, previous }, seed) {
  const parts = {
    mood: moodSentence(basket, seed),
    trend: trendSentence(basket, previous, seed),
    breadth: breadthSentence(breadth, seed),
    category: categorySentence(categories, seed),
    movers: moversSentence(movers, seed),
    star: standoutSentence(movers, seed),
  };
  const order = ["mood", "trend", "breadth", "category", "movers", "star"]; // reading order
  const present = () => order.filter((k) => parts[k]);
  // Over the cap? Drop the least interesting parts first.
  for (const k of ["breadth", "movers", "trend"]) {
    if (present().length <= MAX_SENTENCES) break;
    parts[k] = null;
  }
  return present().map((k) => parts[k]).join(" ");
}
