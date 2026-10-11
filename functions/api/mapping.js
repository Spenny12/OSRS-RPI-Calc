// GET /api/mapping -> [{ id, name }] for every tradeable OSRS item.
// Proxies the OSRS Wiki real-time prices mapping endpoint with a descriptive
// User-Agent (required by the Wiki's API guidelines) and caches it at the edge.

const UPSTREAM = "https://prices.runescape.wiki/api/v1/osrs/mapping";
const EDGE_TTL = 6 * 60 * 60; // 6 hours
const BROWSER_TTL = 60 * 60; // 1 hour

export async function onRequestGet(context) {
  const { request, env } = context;
  const cache = typeof caches !== "undefined" ? caches.default : null;
  const cacheKey = new Request(new URL("/api/mapping?v=2", request.url).toString());

  if (cache) {
    const hit = await cache.match(cacheKey);
    if (hit) return hit;
  }

  let upstream;
  try {
    upstream = await fetch(UPSTREAM, {
      headers: { "User-Agent": userAgent(env), Accept: "application/json" },
      cf: { cacheTtl: EDGE_TTL, cacheEverything: true },
    });
  } catch (err) {
    return json({ error: "Could not reach the OSRS Wiki prices API." }, 502);
  }
  if (!upstream.ok) {
    return json({ error: `OSRS Wiki prices API returned ${upstream.status}.` }, 502);
  }

  const raw = await upstream.json();
  const items = raw
    .filter((i) => i && i.id != null && i.name && !i.name.startsWith("Exchange ticket"))
    .map((i) => ({ id: i.id, name: i.name }))
    .sort((a, b) => a.name.localeCompare(b.name));

  const response = json(items, 200, {
    "Cache-Control": `public, max-age=${BROWSER_TTL}, s-maxage=${EDGE_TTL}`,
  });
  if (cache) context.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
}

export function userAgent(env) {
  return (env && env.USER_AGENT) || "OSRS-RPI-Calc (Cloudflare Pages) - Discord: spenny12_";
}

export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...headers },
  });
}
