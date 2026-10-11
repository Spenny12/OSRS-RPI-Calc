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
/** A category must move at least this much (%) to be called out. */
export const CATEGORY_CALLOUT = 3;
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
  return null;
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
 * @returns {string} 1 to 3 sentences, or "" if there is nothing to say
 */
export function writeIntro({ basket, breadth, categories, movers }, seed) {
  const parts = [moodSentence(basket, seed)];
  const cat = categorySentence(categories, seed);
  const star = standoutSentence(movers, seed);
  if (cat) parts.push(cat);
  if (star) parts.push(star);
  if (parts.filter(Boolean).length < 2) parts.push(breadthSentence(breadth, seed));
  return parts.filter(Boolean).slice(0, 3).join(" ");
}
