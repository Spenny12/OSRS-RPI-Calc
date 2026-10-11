// GET /api/rpi -> precomputed index for the default basket.
// Built daily by .github/workflows/build-index.yml and committed to the `data`
// branch; this function serves it from Cloudflare's edge cache.

import { json } from "./mapping.js";

const DEFAULT_SOURCE = "https://raw.githubusercontent.com/Spenny12/OSRS-RPI-Calc/data/index.json";
const EDGE_TTL = 30 * 60; // 30 minutes
const BROWSER_TTL = 10 * 60;

export async function onRequestGet(context) {
  const { request, env } = context;
  const source = (env && env.INDEX_URL) || DEFAULT_SOURCE;
  const cache = typeof caches !== "undefined" ? caches.default : null;
  const cacheKey = new Request(new URL("/api/rpi?v=3", request.url).toString());
  if (cache) {
    const hit = await cache.match(cacheKey);
    if (hit) return hit;
  }
  let upstream;
  try {
    upstream = await fetch(source, { cf: { cacheTtl: EDGE_TTL, cacheEverything: true } });
  } catch {
    return json({ error: "Could not load the index data." }, 502);
  }
  if (!upstream.ok) return json({ error: `Index data returned ${upstream.status}.` }, 502);
  const body = await upstream.text();
  const response = new Response(body, {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": `public, max-age=${BROWSER_TTL}, s-maxage=${EDGE_TTL}`,
    },
  });
  if (cache) context.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
}
