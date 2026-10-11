// Shared by the daily index build and the weekly Discord recap: downloads the
// full Weird Gloop GE history for every basket item and returns gap-filled
// PriceSeries objects.

import fs from "node:fs";
import path from "node:path";
import { compactHistory } from "../../public/assets/js/lib/compact.js";
import { PriceSeries, withBurnIn } from "../../public/assets/js/lib/rpi.js";

/**
 * Fetches one item's raw history points, retrying with backoff.
 * With `cacheDir`, raw points are read from / written to `<cacheDir>/<id>.json`.
 * @returns {Promise<Array<{price:number,timestamp:number}>|null>} null if every attempt failed
 */
export async function fetchHistory(id, { cacheDir = null, userAgent }) {
  const cached = cacheDir && path.join(cacheDir, `${id}.json`);
  if (cached && fs.existsSync(cached)) return JSON.parse(fs.readFileSync(cached, "utf8"));
  let lastErr;
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const res = await fetch(`https://api.weirdgloop.org/exchange/history/osrs/all?id=${id}`, {
        headers: { "User-Agent": userAgent, Accept: "application/json" },
        signal: AbortSignal.timeout(30_000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const points = (json[String(id)] || []).map((p) => ({ price: p.price, timestamp: p.timestamp }));
      if (cached) fs.writeFileSync(cached, JSON.stringify(points));
      return points;
    } catch (e) {
      lastErr = e;
      await new Promise((r) => setTimeout(r, 1500 * 2 ** attempt));
    }
  }
  console.warn(`! ${id}: ${lastErr}`);
  return null;
}

/**
 * Loads a series for every name. Items still inside their new-release burn-in
 * period (or with no data) come back as null.
 * @param {{names:string[], idOf:(name:string)=>number, cacheDir?:string|null, userAgent:string, concurrency?:number, log?:(msg:string)=>void}} opts
 * @returns {Promise<(name:string)=>PriceSeries|null>} synchronous lookup
 */
export async function loadBasketSeries({ names, idOf, cacheDir = null, userAgent, concurrency = 4, log = () => {} }) {
  const series = new Map();
  let i = 0, done = 0;
  async function worker() {
    while (i < names.length) {
      const name = names[i++];
      const pts = await fetchHistory(idOf(name), { cacheDir, userAgent });
      const c = pts && compactHistory(pts);
      series.set(name, c ? withBurnIn(new PriceSeries(c)) : null);
      if (++done % 50 === 0) log(`  ${done}/${names.length}`);
    }
  }
  if (cacheDir) fs.mkdirSync(cacheDir, { recursive: true });
  await Promise.all(Array.from({ length: concurrency }, worker));
  return (n) => series.get(n) ?? null;
}
