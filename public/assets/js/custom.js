import { $, $$, esc, pct, gp, trendClass, initTheme, lineChart, store } from "./ui.js?v=4";
import { loadMapping, loadSeries, loadBasketSeries } from "./api.js?v=4";
import { DEFAULT_BASKET, BASKET_CATEGORIES } from "./lib/basket.js?v=4";
import { pointRpi, singleItem } from "./lib/rpi.js?v=4";
import { todayDay, toDay, fromDay, formatDay } from "./lib/dates.js?v=4";

window.__appStarted = true;
initTheme();
$('[data-nav="custom"]').setAttribute("aria-current", "page");

const today = todayDay();
const result = $("#result");
let mapping = null;
let chart = null;

// ---------- dates ----------
const startEl = $("#start"), endEl = $("#end");
startEl.max = endEl.max = fromDay(today);
startEl.min = endEl.min = "2015-02-01";
const setRange = (days) => { startEl.value = fromDay(today - days); endEl.value = fromDay(today); };
setRange(365);
$$("#presets button").forEach((b) => b.addEventListener("click", () => setRange(Number(b.dataset.days))));

function readRange() {
  const s = toDay(startEl.value), e = toDay(endEl.value);
  if (s == null || e == null) return { error: "Choose both a start and end date." };
  if (s >= e) return { error: "The start date must be before the end date." };
  if (e > today) return { error: "The end date can't be in the future." };
  return { s, e };
}

// ---------- tabs ----------
$$('[role="tab"]').forEach((tab) =>
  tab.addEventListener("click", () => {
    $$('[role="tab"]').forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      $(`#${t.getAttribute("aria-controls")}`).hidden = !on;
    });
  })
);

// ---------- rendering ----------
function setResult(html) {
  if (chart) { chart.destroy(); chart = null; }
  result.innerHTML = html;
}
const errorBox = (msg) => `<p class="alert">${esc(msg)}</p>`;
const loadingBox = (msg) => `<div class="result-empty"><div class="skeleton" style="width:60%;height:24px"></div><p>${esc(msg)}</p></div>`;

// ---------- single item ----------
$("#single-go").addEventListener("click", async () => {
  const r = readRange();
  if (r.error) return setResult(errorBox(r.error));
  if (!mapping) return setResult(errorBox("The item list is still loading. Try again in a moment."));
  const name = mapping.canonical($("#single-item").value);
  if (!name) return setResult(errorBox(`Couldn't find an item called "${$("#single-item").value}". Pick one from the suggestions.`));

  setResult(loadingBox(`Fetching price history for ${name}…`));
  const series = await loadSeries(mapping.idOf(name));
  const res = singleItem(series, r.s, r.e);
  if (res.error) return setResult(`<h2 style="font-size:var(--text-lg);margin-bottom:var(--space-4)">${esc(name)}</h2>${errorBox(res.error)}`);

  setResult(`
    <h2 style="font-size:var(--text-lg);margin-bottom:var(--space-4)">${esc(name)}</h2>
    <div class="stat-row">
      <div class="stat"><span class="kpi-label">Change</span><span class="kpi-value ${trendClass(res.change)}">${pct(res.change)}</span></div>
      <div class="stat"><span class="kpi-label">Price on ${formatDay(res.actualStart)}</span><span class="kpi-value num">${gp(res.oldPrice)}</span></div>
      <div class="stat"><span class="kpi-label">Price on ${formatDay(res.actualEnd)}</span><span class="kpi-value num">${gp(res.newPrice)}</span></div>
    </div>
    <div class="chart-wrap"><canvas id="item-chart" role="img" aria-label="Price history for ${esc(name)}"></canvas></div>
    <p class="muted" style="margin-top:var(--space-3)">Grand Exchange guide price. Days without a price (e.g. API gaps) carry the last known price forward.</p>`);

  const pts = [];
  for (let d = Math.max(r.s, series.start); d <= Math.min(r.e, series.end); d++) pts.push({ x: d, y: series.asof(d) });
  chart = lineChart($("#item-chart"), pts, {
    label: "Price",
    yFormat: (v) => gp(v),
    fill: true,
    tickDate: r.e - r.s > 400 ? { month: "short", year: "numeric" } : { day: "numeric", month: "short" },
  });
});

// ---------- custom basket ----------
let basket = {};
try { basket = JSON.parse(store.get("customBasket") || "{}") || {}; } catch { basket = {}; }
const saveBasket = () => store.set("customBasket", JSON.stringify(basket));

function drawBasket() {
  const entries = Object.entries(basket);
  const total = entries.reduce((s, [, w]) => s + w, 0);
  $("#basket-count").textContent = `${entries.length} item${entries.length === 1 ? "" : "s"}`;
  $("#basket-list").innerHTML = entries.length
    ? entries.map(([n, w]) => `<li>
        <span>${esc(n)}</span>
        <input type="number" min="0.01" step="any" value="${w}" data-weight="${esc(n)}" aria-label="Weight for ${esc(n)}">
        <span class="share">${((w / total) * 100).toFixed(1)}%</span>
        <button class="btn small ghost" type="button" data-remove="${esc(n)}" aria-label="Remove ${esc(n)}">✕</button>
      </li>`).join("")
    : `<li class="muted">Your basket is empty. Add items above, or load a category from the default basket.</li>`;
}
$("#basket-list").addEventListener("change", (e) => {
  const n = e.target.dataset.weight;
  if (n == null) return;
  const w = Number(e.target.value);
  if (w > 0) { basket[n] = w; saveBasket(); }
  drawBasket();
});
$("#basket-list").addEventListener("click", (e) => {
  const n = e.target.closest("[data-remove]")?.dataset.remove;
  if (n == null) return;
  delete basket[n]; saveBasket(); drawBasket();
});
function addItem() {
  const hint = $("#basket-hint");
  if (!mapping) { hint.textContent = "The item list is still loading…"; return; }
  const name = mapping.canonical($("#basket-item").value);
  const w = Number($("#basket-weight").value);
  if (!name) { hint.textContent = "Pick an item from the suggestions."; return; }
  if (!(w > 0)) { hint.textContent = "Weight must be greater than zero."; return; }
  hint.textContent = basket[name] ? `Updated the weight for ${name}.` : "Weights are relative: 2 and 3 become 40% and 60%.";
  basket[name] = w; saveBasket(); drawBasket();
  $("#basket-item").value = ""; $("#basket-item").focus();
}
$("#basket-add").addEventListener("click", addItem);
$("#basket-item").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addItem(); } });
// Load a category (or the whole default basket) with its index weights.
const preset = $("#basket-preset");
for (const c of BASKET_CATEGORIES) preset.insertAdjacentHTML("beforeend", `<option value="${esc(c.name)}">${esc(c.name)} (${c.items.length})</option>`);
preset.insertAdjacentHTML("beforeend", `<option value="*">Entire default basket (${Object.keys(DEFAULT_BASKET).length}, slow)</option>`);
preset.addEventListener("change", () => {
  const v = preset.value;
  if (!v) return;
  const items = v === "*" ? Object.entries(DEFAULT_BASKET) : BASKET_CATEGORIES.find((c) => c.name === v).items.map(([, n, w]) => [n, w]);
  for (const [n, w] of items) basket[n] = Math.round(w * 10000) / 10000;
  saveBasket(); drawBasket();
  preset.value = "";
});
$("#basket-clear").addEventListener("click", () => { basket = {}; saveBasket(); drawBasket(); });
drawBasket();

$("#basket-go").addEventListener("click", async () => {
  const r = readRange();
  if (r.error) return setResult(errorBox(r.error));
  const names = Object.keys(basket);
  if (!names.length) return setResult(errorBox("Add at least one item to your basket."));
  if (!mapping) return setResult(errorBox("The item list is still loading. Try again in a moment."));

  setResult(loadingBox(`Fetching price history… 0/${names.length}`));
  const get = await loadBasketSeries(names, mapping, {
    onProgress: (d, t) => { const p = $(".result-empty p", result); if (p) p.textContent = `Fetching price history… ${d}/${t}`; },
  });
  const res = pointRpi(basket, get, r.s, r.e);
  if (res.value == null) {
    return setResult(errorBox("No item in the basket has price data for both dates.") + exclusionsHtml(res.excluded));
  }
  const rows = [...res.items].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  setResult(`
    <h2 style="font-size:var(--text-lg);margin-bottom:var(--space-4)">Custom basket</h2>
    <div class="stat-row">
      <div class="stat"><span class="kpi-label">Weighted inflation</span><span class="kpi-value ${trendClass(res.value)}">${pct(res.value)}</span></div>
      <div class="stat"><span class="kpi-label">Period</span><span class="kpi-value" style="font-size:var(--text-base)">${formatDay(r.s)} → ${formatDay(r.e)}</span></div>
      <div class="stat"><span class="kpi-label">Items used</span><span class="kpi-value">${res.items.length}<span class="muted"> / ${names.length}</span></span></div>
    </div>
    <div class="table-scroll"><table>
      <thead><tr><th>Item</th><th class="r">Weight</th><th class="r">Start</th><th class="r">End</th><th class="r">Change</th><th class="r">Contribution</th></tr></thead>
      <tbody>${rows.map((x) => `<tr><td>${esc(x.name)}</td><td class="r">${(x.share * 100).toFixed(1)}%</td>
        <td class="r">${gp(x.oldPrice)}</td><td class="r">${gp(x.newPrice)}</td>
        <td class="r"><span class="chip ${trendClass(x.change)}">${pct(x.change, 1)}</span></td>
        <td class="r">${pct(x.contribution, 2)}</td></tr>`).join("")}</tbody>
    </table></div>
    ${exclusionsHtml(res.excluded)}`);
});

function exclusionsHtml(list) {
  if (!list.length) return "";
  return `<details style="margin-top:var(--space-4)"><summary>${list.length} item${list.length === 1 ? "" : "s"} excluded</summary>
    <div><ul class="excl-list">${list.map((e) => `<li><strong>${esc(e.name)}</strong>: ${esc(e.reason)}</li>`).join("")}</ul></div></details>`;
}

// ---------- boot ----------
loadMapping()
  .then((m) => {
    mapping = m;
    const frag = document.createDocumentFragment();
    for (const n of m.names) { const o = document.createElement("option"); o.value = n; frag.appendChild(o); }
    $("#item-names").appendChild(frag);
  })
  .catch(() => setResult(errorBox("Couldn't load the OSRS item database. The prices API may be down; please refresh to try again.")));
