// Date helpers. Everything works in whole UTC days ("day numbers" = days since
// 1970-01-01) to match how the GE history is bucketed.

export const DAY_MS = 86_400_000;

export const todayDay = (now = Date.now()) => Math.floor(now / DAY_MS);

export function toDay(isoDate) {
  const [y, m, d] = String(isoDate).split("-").map(Number);
  if (!y || !m || !d) return null;
  return Math.floor(Date.UTC(y, m - 1, d) / DAY_MS);
}

export function fromDay(day) {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

export function parts(day) {
  const dt = new Date(day * DAY_MS);
  return { y: dt.getUTCFullYear(), m: dt.getUTCMonth(), d: dt.getUTCDate() };
}

export const dayOf = (y, m, d) => Math.floor(Date.UTC(y, m, d) / DAY_MS);

/** Same calendar date N years earlier. 29 Feb maps to 28 Feb (fixes the leap-day crash). */
export function minusYears(day, years = 1) {
  const { y, m, d } = parts(day);
  const lastDay = new Date(Date.UTC(y - years, m + 1, 0)).getUTCDate();
  return dayOf(y - years, m, Math.min(d, lastDay));
}

/** First and last day of the full calendar month before the month containing `day`. */
export function previousMonth(day) {
  const { y, m } = parts(day);
  const end = dayOf(y, m, 1) - 1;
  const p = parts(end);
  return { start: dayOf(p.y, p.m, 1), end };
}

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
export const monthName = (day) => MONTHS[parts(day).m];

export function formatDay(day, opts = { day: "numeric", month: "short", year: "numeric" }) {
  return new Date(day * DAY_MS).toLocaleDateString("en-GB", { timeZone: "UTC", ...opts });
}
