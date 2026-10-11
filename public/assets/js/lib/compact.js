// Shared between the Cloudflare Pages Functions (server) and the tests.
// Converts the Weird Gloop "all" history payload into a compact, gap-filled
// daily series so the browser downloads ~20 KB per item instead of ~260 KB.

export const DAY_MS = 86_400_000;

/**
 * @param {Array<{price:number|null, timestamp:number}>} points
 * @returns {{start:number, prices:number[]} | null}
 *   start  = first day (days since Unix epoch, UTC)
 *   prices = one value per day from `start`, forward-filled across gaps
 */
export function compactHistory(points) {
  if (!Array.isArray(points) || points.length === 0) return null;

  // Average all observations that fall on the same UTC day.
  const byDay = new Map();
  for (const p of points) {
    const price = Number(p?.price);
    const ts = Number(p?.timestamp);
    if (!Number.isFinite(price) || !Number.isFinite(ts) || price <= 0) continue;
    const day = Math.floor(ts / DAY_MS);
    const agg = byDay.get(day) || { sum: 0, n: 0 };
    agg.sum += price;
    agg.n += 1;
    byDay.set(day, agg);
  }
  if (byDay.size === 0) return null;

  const days = [...byDay.keys()].sort((a, b) => a - b);
  const start = days[0];
  const end = days[days.length - 1];
  const prices = new Array(end - start + 1);
  let last = null;
  for (let d = start; d <= end; d++) {
    const agg = byDay.get(d);
    if (agg) last = Math.round((agg.sum / agg.n) * 10) / 10;
    prices[d - start] = last; // forward-fill weekends / missing days
  }
  return { start, prices };
}
