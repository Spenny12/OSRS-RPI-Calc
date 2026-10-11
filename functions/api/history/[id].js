// GET /api/history/:id -> { id, start, prices } (compact daily GE price series)
// Proxies the Weird Gloop exchange history API, compacts it, and caches the
// result at Cloudflare's edge so every visitor shares the same cached copy.

import { compactHistory } from "../../../public/assets/js/lib/compact.js";
import { json, userAgent } from "../mapping.js";

const EDGE_TTL = 6 * 60 * 60; // GE guide prices update roughly daily
const BROWSER_TTL = 60 * 60;

export async function onRequestGet(context) {
  const { request, params, env } = context;
  const id = String(params.id || "");
  if (!/^\d{1,6}$/.test(id)) return json({ error: "Invalid item id." }, 400);

  const cache = typeof caches !== "undefined" ? caches.default : null;
  const cacheKey = new Request(new URL(`/api/history/${id}?v=2`, request.url).toString());
  if (cache) {
    const hit = await cache.match(cacheKey);
    if (hit) return hit;
  }

  let upstream;
  try {
    upstream = await fetch(`https://api.weirdgloop.org/exchange/history/osrs/all?id=${id}`, {
      headers: { "User-Agent": userAgent(env), Accept: "application/json" },
      cf: { cacheTtl: EDGE_TTL, cacheEverything: true },
    });
  } catch {
    return json({ error: "Could not reach the Weird Gloop history API." }, 502);
  }
  if (!upstream.ok) {
    return json({ error: `Weird Gloop history API returned ${upstream.status}.` }, 502);
  }

  let payload;
  try {
    payload = await upstream.json();
  } catch {
    return json({ error: "Weird Gloop returned invalid JSON." }, 502);
  }

  const series = compactHistory(payload?.[id]);
  const body = series ? { id: Number(id), ...series } : { id: Number(id), start: null, prices: [] };
  const response = json(body, 200, {
    "Cache-Control": `public, max-age=${BROWSER_TTL}, s-maxage=${EDGE_TTL}`,
  });
  if (cache) context.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
}
