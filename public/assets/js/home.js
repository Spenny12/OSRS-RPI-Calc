import { $, $$, esc, pct, gp, trendClass, initTheme, lineChart } from "./ui.js";
import { BASKET_CATEGORIES } from "./lib/basket.js";
import { toDay, formatDay, minusYears, todayDay } from "./lib/dates.js";

initTheme();
$('[data-nav="home"]').setAttribute("aria-current", "page");

const monthDay = (ym) => { const [y, m] = ym.split("-").map(Number); return Math.floor(Date.UTC(y, m, 0) / 86_400_000); }; // last day of month
const monthLabel = (ym) => formatDay(monthDay(ym), { month: "long", year: "numeric" });
const fd = (iso) => formatDay(toDay(iso));

function showError(msg) {
  $("#load-progress").hidden = true;
  const e = $("#load-error");
  e.hidden = false;
  e.innerHTML = `${esc(msg)} <button class="btn small" type="button" onclick="location.reload()">Try again</button>`;
}

function setKpi(key, value, subHtml) {
  const el = $(`[data-kpi="${key}"]`);
  const v = $(".kpi-value", el);
  v.classList.remove("skeleton");
  v.classList.add(trendClass(value));
  v.textContent = pct(value);
  $(".kpi-sub", el).innerHTML = subHtml;
}

async function init() {
  let data;
  try {
    const res = await fetch("/api/rpi");
    if (!res.ok) throw new Error(res.status);
    data = await res.json();
    if (!data.kpis) throw new Error("bad data");
  } catch {
    return showError("Couldn't load the index right now.");
  }
  $("#load-progress").hidden = true;
  $$("[data-basket-size]").forEach((el) => (el.textContent = data.basketSize));

  const k = data.kpis;
  setKpi("lastMonth", k.lastMonth.value, `<strong>${monthLabel(k.lastMonth.to.slice(0, 7))}</strong> vs a year earlier · ${k.lastMonth.items} items`);
  setKpi("yoy7", k.yoy7.value, `${fd(k.yoy7.from)} → <strong>${fd(k.yoy7.to)}</strong> · ${k.yoy7.items} items`);
  setKpi("yoy30", k.yoy30.value, `${fd(k.yoy30.from)} → <strong>${fd(k.yoy30.to)}</strong> · ${k.yoy30.items} items`);
  setKpi("wow", k.wow.value, `${fd(k.wow.from)} → <strong>${fd(k.wow.to)}</strong> · ${k.wow.items} items`);

  renderHistory(data.history);
  renderCategories(data.categories, k.lastMonth);
  renderItems(data.items);
  renderExclusions({ "Last full month YoY": k.lastMonth.excluded, "YoY (7 days ago)": k.yoy7.excluded, "YoY (30 days ago)": k.yoy30.excluded, "Week on week": k.wow.excluded });
  setupLookup(data);
  $("#data-stamp").textContent = `Index rebuilt ${new Date(data.generatedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })} · prices through ${fd(data.dataThrough)} · ${data.basketSize} items in the basket.`;
}

// ---------- history chart ----------
function renderHistory(history) {
  const counts = new Map();
  const all = history.map(([ym, v, n]) => { const x = monthDay(ym); counts.set(x, n); return { x, y: v }; });
  const chart = lineChart($("#history-chart"), all, {
    label: "YoY RPI",
    yFormat: (v, tick) => (tick ? `${v}%` : pct(v)),
    zeroLine: true,
    tooltipDate: { month: "long", year: "numeric" },
    afterLabel: (x) => `${counts.get(x)} items`,
  });
  const today = todayDay();
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
function renderCategories(cats, lm) {
  const max = Math.max(...cats.map((r) => Math.abs(r.change ?? 0)), 1);
  $("#cat-bars").innerHTML = [...cats]
    .sort((a, b) => (b.change ?? -1e9) - (a.change ?? -1e9))
    .map((r) => {
      const cls = trendClass(r.change);
      const width = r.change == null ? 0 : (Math.abs(r.change) / max) * 50;
      return `<div class="bar-row">
        <span>${esc(r.name)} <span class="muted">· ${r.share}% · ${r.used} items</span></span>
        <div class="bar-track"><span class="bar-fill ${cls}" style="width:${width}%"></span></div>
        <span class="bar-val">${pct(r.change, 1)}<small>${pct(r.contribution, 2)} pts</small></span>
      </div>`;
    })
    .join("");
  $("#cat-desc").textContent = `Year-on-year change by category for ${monthLabel(lm.to.slice(0, 7))}, with each category's share of the index and its contribution (in percentage points) to the ${pct(lm.value)} headline.`;
}

// ---------- items table ----------
const COLS = ["name", "cat", "share", "oldPrice", "newPrice", "change", "contribution", "latest", "yoy"];
let itemRows = [];
let sortKey = "contribution", sortDir = -1, showAll = false;
const PREVIEW_ROWS = 20;

function renderItems(items) {
  itemRows = items.map((r) => Object.fromEntries(COLS.map((c, i) => [c, r[i]])));
  const sel = $("#cat-filter");
  for (const c of BASKET_CATEGORIES) sel.insertAdjacentHTML("beforeend", `<option>${esc(c.name)}</option>`);
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
  sel.addEventListener("change", drawItems);
  $("#items-more").addEventListener("click", () => { showAll = !showAll; drawItems(); });
}

function drawItems() {
  const q = $("#item-filter").value.trim().toLowerCase();
  const cat = $("#cat-filter").value;
  const key = sortKey === "contribution" ? (r) => Math.abs(r.contribution) : (r) => r[sortKey];
  const rows = itemRows
    .filter((r) => (!q || r.name.toLowerCase().includes(q)) && (!cat || r.cat === cat))
    .sort((a, b) => {
      const x = key(a), y = key(b);
      return (typeof x === "string" ? x.localeCompare(y) : (x ?? -Infinity) - (y ?? -Infinity)) * sortDir;
    });
  const filtered = q || cat;
  const limited = !filtered && !showAll && rows.length > PREVIEW_ROWS;
  const more = $("#items-more");
  more.hidden = !!filtered || rows.length <= PREVIEW_ROWS;
  more.textContent = showAll ? "Show fewer" : `Show all ${rows.length} items`;
  $("#items-table tbody").innerHTML = rows.length
    ? (limited ? rows.slice(0, PREVIEW_ROWS) : rows).map((r) => `<tr>
        <td>${esc(r.name)}</td><td class="muted">${esc(r.cat)}</td>
        <td class="r">${r.share.toFixed(2)}%</td>
        <td class="r">${gp(r.oldPrice)}</td><td class="r">${gp(r.newPrice)}</td><td class="r">${gp(r.latest)}</td>
        <td class="r"><span class="chip ${trendClass(r.change)}">${pct(r.change, 1)}</span></td>
        <td class="r">${pct(r.contribution, 3)}</td></tr>`).join("")
    : `<tr><td colspan="8" class="muted">No items match.</td></tr>`;
}

function renderExclusions(groups) {
  const html = Object.entries(groups)
    .filter(([, list]) => list.length)
    .map(([label, list]) => `<details><summary>${esc(label)}: ${list.length} item${list.length === 1 ? "" : "s"} excluded</summary>
      <div><ul class="excl-list">${list.map(([n, reason]) => `<li><strong>${esc(n)}</strong>: ${esc(reason)}</li>`).join("")}</ul></div></details>`)
    .join("");
  $("#exclusions").innerHTML = html
    ? html + `<p class="muted" style="margin-top:var(--space-2)">Items are left out of a figure when they have no price for one of its dates, usually because they hadn't been released yet, or when their price moved more than 10×. The remaining weights are rescaled to 100%.</p>`
    : "";
}

// ---------- past month lookup ----------
function setupLookup(data) {
  const yoy = new Map(data.history.map(([ym, v, n]) => [ym, [v, n]]));
  const mom = new Map(data.mom.map(([ym, v, n]) => [ym, [v, n]]));
  const months = [...new Set([...yoy.keys(), ...mom.keys()])].sort();
  const input = $("#historic-month");
  input.min = months[0];
  input.max = months[months.length - 1];
  const yearAgo = months[Math.max(0, months.length - 13)];
  input.value = yearAgo;
  const run = () => {
    const ym = input.value;
    const y = yoy.get(ym), m = mom.get(ym);
    const out = $("#historic-out");
    if (!y && !m) { out.innerHTML = `<p class="alert" style="margin-top:var(--space-4)">No data for that month. Pick a month between ${monthLabel(months[0])} and ${monthLabel(months[months.length - 1])}.</p>`; return; }
    const stat = (label, d, sub) => `<div class="stat"><span class="kpi-label">${label}</span><span class="kpi-value ${trendClass(d?.[0])}">${pct(d?.[0])}</span><span class="kpi-sub">${d ? `${sub} · ${d[1]} items` : "Not available"}</span></div>`;
    out.innerHTML = `<div class="historic-results">
      ${stat("Year on year", y, `${monthLabel(ym)} vs a year earlier`)}
      ${stat("Month on month", m, `${monthLabel(ym)} vs the month before`)}
    </div>`;
  };
  $("#historic-form").addEventListener("submit", (ev) => { ev.preventDefault(); run(); });
  run();
}

init().catch((err) => { console.error(err); showError("Something went wrong while loading the index."); });
