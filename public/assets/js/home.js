import { $, $$, esc, pct, gp, trendClass, initTheme, lineChart } from "./ui.js";
import { loadMapping, loadBasketSeries } from "./api.js";
import { DEFAULT_BASKET, BASKET_CATEGORIES, ITEM_CATEGORY } from "./lib/basket.js";
import { pointRpi, lastMonthYoY, monthlyHistory } from "./lib/rpi.js";
import { todayDay, minusYears, toDay, fromDay, formatDay, monthName } from "./lib/dates.js";

initTheme();
$('[data-nav="home"]').setAttribute("aria-current", "page");

const today = todayDay();
let getSeries = null;

function setKpi(key, value, subHtml) {
  const el = $(`[data-kpi="${key}"]`);
  const v = $(".kpi-value", el);
  v.classList.remove("skeleton");
  v.classList.add(trendClass(value));
  v.textContent = pct(value);
  if (subHtml) $(".kpi-sub", el).innerHTML = subHtml;
}

function showError(msg) {
  $("#load-progress").hidden = true;
  const e = $("#load-error");
  e.hidden = false;
  e.innerHTML = `${esc(msg)} <button class="btn small" type="button" onclick="location.reload()">Try again</button>`;
}

async function init() {
  let mapping;
  try {
    mapping = await loadMapping();
  } catch (err) {
    return showError("Couldn't load the OSRS item database. The prices API may be down.");
  }
  const names = Object.keys(DEFAULT_BASKET);
  getSeries = await loadBasketSeries(names, mapping, {
    onProgress(done, total) {
      $("#load-text").textContent = `Loading price history… ${done}/${total} items`;
      $("#load-bar").style.width = `${(done / total) * 100}%`;
    },
  });
  $("#load-progress").hidden = true;

  const loaded = names.filter((n) => getSeries(n)).length;
  if (loaded === 0) return showError("Couldn't load any price history. Please try again shortly.");

  // Data recency: the latest day any basket item has a price for.
  const latest = Math.max(...names.map((n) => getSeries(n)?.end ?? -Infinity));

  // KPIs
  const lm = lastMonthYoY(DEFAULT_BASKET, getSeries, today);
  setKpi("lastMonth", lm.value,
    `<strong>${monthName(lm.current.end)} ${formatDay(lm.current.end, { year: "numeric" })}</strong> vs ${monthName(lm.previous.end)} ${formatDay(lm.previous.end, { year: "numeric" })} · ${lm.items.length} items`);

  const e7 = today - 7, e30 = today - 30;
  const y7 = pointRpi(DEFAULT_BASKET, getSeries, minusYears(e7), e7);
  setKpi("yoy7", y7.value, `${formatDay(minusYears(e7))} → <strong>${formatDay(e7)}</strong>`);
  const y30 = pointRpi(DEFAULT_BASKET, getSeries, minusYears(e30), e30);
  setKpi("yoy30", y30.value, `${formatDay(minusYears(e30))} → <strong>${formatDay(e30)}</strong>`);
  const w = pointRpi(DEFAULT_BASKET, getSeries, today - 7, today);
  setKpi("wow", w.value, `${formatDay(today - 7)} → <strong>${formatDay(Math.min(today, latest))}</strong>`);

  renderHistory();
  renderCategories(lm);
  renderItems(lm);
  renderExclusions({ "Last full month YoY": lm.excluded, "YoY (7 days ago)": y7.excluded, "YoY (30 days ago)": y30.excluded, "Week on week": w.excluded });
}

// ---------- history chart ----------
function renderHistory() {
  const hist = monthlyHistory(DEFAULT_BASKET, getSeries, today);
  const all = hist.map((h) => ({ x: h.month, y: Math.round(h.value * 100) / 100 }));
  const chart = lineChart($("#history-chart"), all, {
    label: "YoY RPI",
    yFormat: (v, tick) => (tick ? `${v}%` : pct(v)),
    zeroLine: true,
    tooltipDate: { month: "long", year: "numeric" },
  });
  $$("#range button").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#range button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      const yrs = Number(b.dataset.years);
      const from = yrs ? minusYears(today, yrs) : -Infinity;
      chart.update(all.filter((p) => p.x >= from));
    })
  );
}

// ---------- categories ----------
function renderCategories(lm) {
  const byCat = new Map(BASKET_CATEGORIES.map((c) => [c.name, { w: 0, wChange: 0, contrib: 0, n: 0 }]));
  for (const r of lm.items) {
    const c = byCat.get(ITEM_CATEGORY[r.name]);
    c.w += r.weight; c.wChange += r.weight * r.change; c.contrib += r.contribution; c.n += 1;
  }
  const rows = [...byCat.entries()].map(([name, c]) => ({ name, change: c.w ? c.wChange / c.w : null, contrib: c.contrib, n: c.n }));
  const max = Math.max(...rows.map((r) => Math.abs(r.change ?? 0)), 1);
  $("#cat-bars").innerHTML = rows
    .sort((a, b) => (b.change ?? -1e9) - (a.change ?? -1e9))
    .map((r) => {
      const cls = trendClass(r.change);
      const width = r.change == null ? 0 : (Math.abs(r.change) / max) * 50;
      return `<div class="bar-row">
        <span>${esc(r.name)} <span class="muted">· ${r.n}</span></span>
        <div class="bar-track"><span class="bar-fill ${cls}" style="width:${width}%"></span></div>
        <span class="bar-val">${pct(r.change, 1)}<small>${pct(r.contrib, 2)} pts</small></span>
      </div>`;
    })
    .join("");
  $("#cat-desc").textContent = `Year-on-year change by category for ${monthName(lm.current.end)} (with each category's contribution, in percentage points, to the ${pct(lm.value)} headline).`;
}

// ---------- items table ----------
let itemRows = [];
let sortKey = "contribution", sortDir = -1, showAll = false;
const PREVIEW_ROWS = 15;
function renderItems(lm) {
  itemRows = lm.items.map((r) => ({ ...r, cat: ITEM_CATEGORY[r.name] }));
  drawItems();
  $$("#items-table th button").forEach((b) =>
    b.addEventListener("click", () => {
      const k = b.dataset.sort;
      sortDir = k === sortKey ? -sortDir : k === "name" || k === "cat" ? 1 : -1;
      sortKey = k;
      drawItems();
    })
  );
  $("#item-filter").addEventListener("input", drawItems);
  $("#items-more").addEventListener("click", () => { showAll = !showAll; drawItems(); });
}
function drawItems() {
  const q = $("#item-filter").value.trim().toLowerCase();
  const rows = itemRows
    .filter((r) => !q || r.name.toLowerCase().includes(q) || r.cat.toLowerCase().includes(q))
    .sort((a, b) => {
      const x = a[sortKey], y = b[sortKey];
      return (typeof x === "string" ? x.localeCompare(y) : x - y) * sortDir;
    });
  const limited = !q && !showAll && rows.length > PREVIEW_ROWS;
  const more = $("#items-more");
  more.hidden = !!q || rows.length <= PREVIEW_ROWS;
  more.textContent = showAll ? "Show fewer" : `Show all ${rows.length} items`;
  $("#items-table tbody").innerHTML = rows.length
    ? (limited ? rows.slice(0, PREVIEW_ROWS) : rows).map((r) => `<tr>
        <td>${esc(r.name)}</td><td class="muted">${esc(r.cat)}</td>
        <td class="r">${(r.share * 100).toFixed(1)}%</td>
        <td class="r">${gp(r.oldPrice)}</td><td class="r">${gp(r.newPrice)}</td>
        <td class="r"><span class="chip ${trendClass(r.change)}">${pct(r.change, 1)}</span></td>
        <td class="r">${pct(r.contribution, 2)}</td></tr>`).join("")
    : `<tr><td colspan="7" class="muted">No items match.</td></tr>`;
}

function renderExclusions(groups) {
  const html = Object.entries(groups)
    .filter(([, list]) => list.length)
    .map(([label, list]) => `<details><summary>${esc(label)}: ${list.length} item${list.length === 1 ? "" : "s"} excluded</summary>
      <div><ul class="excl-list">${list.map((e) => `<li><strong>${esc(e.name)}</strong>: ${esc(e.reason)}</li>`).join("")}</ul></div></details>`)
    .join("");
  $("#exclusions").innerHTML = html
    ? html + `<p class="muted" style="margin-top:var(--space-2)">Items are excluded from a figure when they have no price data for one of its dates, usually because they hadn't been released yet. The remaining weights are rescaled to 100%.</p>`
    : "";
}

// ---------- historical lookup ----------
const hd = $("#historic-date");
hd.max = fromDay(today);
hd.min = "2016-01-01";
hd.value = fromDay(minusYears(today));
$("#historic-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const out = $("#historic-out");
  if (!getSeries) { out.innerHTML = `<p class="alert info" style="margin-top:var(--space-4)">Price data is still loading. Try again in a moment.</p>`; return; }
  const d = toDay(hd.value);
  if (d == null || d > today) { out.innerHTML = `<p class="alert" style="margin-top:var(--space-4)">Pick a date on or before today.</p>`; return; }
  const w = pointRpi(DEFAULT_BASKET, getSeries, d - 7, d);
  const lm = lastMonthYoY(DEFAULT_BASKET, getSeries, d);
  out.innerHTML = `<div class="historic-results">
    <div class="stat"><span class="kpi-label">Week on week</span><span class="kpi-value ${trendClass(w.value)}">${pct(w.value)}</span><span class="kpi-sub">${formatDay(d - 7)} → ${formatDay(d)} · ${w.items.length} items</span></div>
    <div class="stat"><span class="kpi-label">Last full month, YoY</span><span class="kpi-value ${trendClass(lm.value)}">${pct(lm.value)}</span><span class="kpi-sub">${monthName(lm.current.end)} ${formatDay(lm.current.end, { year: "numeric" })} vs a year earlier · ${lm.items.length} items</span></div>
  </div>`;
});

// Chart.js is loaded with `defer`; module scripts also defer, so it's ready here.
init().catch((err) => { console.error(err); showError("Something went wrong while calculating the index."); });
