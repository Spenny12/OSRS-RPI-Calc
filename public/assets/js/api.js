// Browser data layer: talks to the Pages Functions under /api.
import { PriceSeries } from "./lib/rpi.js?v=4";

let mappingPromise = null;
const seriesCache = new Map(); // id -> Promise<PriceSeries|null>

/** Loads the item list once. Returns { names, idOf(name), canonical(name) }. */
export function loadMapping() {
  if (!mappingPromise) {
    mappingPromise = fetch("/api/mapping")
      .then((r) => {
        if (!r.ok) throw new Error(`Item database request failed (${r.status})`);
        return r.json();
      })
      .then((items) => {
        const byLower = new Map(items.map((i) => [i.name.toLowerCase(), i]));
        return {
          names: items.map((i) => i.name),
          idOf: (name) => byLower.get(String(name).toLowerCase())?.id ?? null,
          canonical: (name) => byLower.get(String(name).trim().toLowerCase())?.name ?? null,
        };
      })
      .catch((err) => {
        mappingPromise = null; // allow retry
        throw err;
      });
  }
  return mappingPromise;
}

export function loadSeries(id) {
  if (id == null) return Promise.resolve(null);
  if (!seriesCache.has(id)) {
    const p = fetchWithRetry(`/api/history/${id}`)
      .then((d) => (d && d.start != null ? new PriceSeries(d) : null))
      .catch(() => {
        seriesCache.delete(id);
        return null;
      });
    seriesCache.set(id, p);
  }
  return seriesCache.get(id);
}

async function fetchWithRetry(url, tries = 3) {
  let lastErr;
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url);
      if (r.ok) return r.json();
      lastErr = new Error(`HTTP ${r.status}`);
      if (r.status < 500 && r.status !== 429) break;
    } catch (e) {
      lastErr = e;
    }
    await new Promise((res) => setTimeout(res, 400 * 2 ** i));
  }
  throw lastErr;
}

/**
 * Loads price series for every item name, a few at a time.
 * @returns {Promise<(name:string)=>PriceSeries|null>} synchronous lookup
 */
export async function loadBasketSeries(names, mapping, { concurrency = 8, onProgress } = {}) {
  const result = new Map();
  let done = 0;
  const queue = [...names];
  async function worker() {
    while (queue.length) {
      const name = queue.shift();
      result.set(name, await loadSeries(mapping.idOf(name)));
      done += 1;
      onProgress?.(done, names.length);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, names.length) }, worker));
  return (name) => result.get(name) ?? null;
}
