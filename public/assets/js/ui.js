// Shared UI helpers: theme, formatting, charts.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function pct(v, digits = 2) {
  if (v == null || !Number.isFinite(v)) return "N/A";
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${Math.abs(v).toFixed(digits)}%`;
}

export function gp(v) {
  if (v == null || !Number.isFinite(v)) return "N/A";
  const a = Math.abs(v);
  if (a >= 1e9) return `${(v / 1e9).toFixed(2)}b gp`;
  if (a >= 1e7) return `${(v / 1e6).toFixed(1)}m gp`;
  if (a >= 1e5) return `${(v / 1e3).toFixed(0)}k gp`;
  return `${Math.round(v).toLocaleString("en-GB")} gp`;
}

export const trendClass = (v) => (v == null ? "" : v > 0.005 ? "is-up" : v < -0.005 ? "is-down" : "is-flat");

// ---------- theme ----------
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage blocked */ } },
};
export { store };

export function initTheme() {
  const root = document.documentElement;
  const saved = store.get("theme");
  const system = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  root.dataset.theme = saved || system;
  const btn = $("[data-theme-toggle]");
  const label = () => btn?.setAttribute("aria-label", `Switch to ${root.dataset.theme === "dark" ? "light" : "dark"} mode`);
  label();
  btn?.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    store.set("theme", root.dataset.theme);
    label();
    document.dispatchEvent(new CustomEvent("themechange"));
  });
}

export const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// ---------- charts ----------
import { formatDay } from "./lib/dates.js?v=4";

/**
 * Line chart with a numeric x axis of day numbers.
 * @param {HTMLCanvasElement} canvas
 * @param {{x:number,y:number}[]} points
 * @param {{yFormat:(v:number)=>string, zeroLine?:boolean, tooltipDate?:object, label:string}} opts
 */
export function lineChart(canvas, points, opts) {
  const Chart = window.Chart;
  const build = () => {
    const accent = cssVar("--color-primary");
    const grid = cssVar("--color-divider");
    const muted = cssVar("--color-text-muted");
    const text = cssVar("--color-text");
    return {
      type: "line",
      data: {
        datasets: [{
          label: opts.label,
          data: points,
          borderColor: accent,
          backgroundColor: accent + "22",
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHitRadius: 8,
          tension: 0.15,
          fill: opts.fill ?? false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        parsing: false,
        normalized: true,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          decimation: { enabled: points.length > 800, algorithm: "lttb", samples: 600 },
          tooltip: {
            backgroundColor: cssVar("--color-surface-2"),
            titleColor: text,
            bodyColor: text,
            borderColor: grid,
            borderWidth: 1,
            padding: 10,
            displayColors: false,
            callbacks: {
              title: (items) => formatDay(items[0].parsed.x, opts.tooltipDate || undefined),
              label: (item) => `${opts.label}: ${opts.yFormat(item.parsed.y)}`,
              afterLabel: (item) => (opts.afterLabel ? opts.afterLabel(item.parsed.x) : ""),
            },
          },
        },
        scales: {
          x: {
            type: "linear",
            min: points.length ? points[0].x : undefined,
            max: points.length ? points[points.length - 1].x : undefined,
            grid: { display: false },
            border: { color: grid },
            ticks: {
              color: muted,
              maxTicksLimit: 8,
              callback: (v) => formatDay(v, opts.tickDate || { month: "short", year: "numeric" }),
            },
          },
          y: {
            grid: {
              color: (ctx) => (opts.zeroLine && ctx.tick.value === 0 ? muted : grid),
              lineWidth: (ctx) => (opts.zeroLine && ctx.tick.value === 0 ? 1.5 : 1),
            },
            border: { display: false },
            ticks: { color: muted, callback: (v) => opts.yFormat(v, true) },
          },
        },
      },
    };
  };
  let chart = new Chart(canvas, build());
  const onTheme = () => { chart.destroy(); chart = new Chart(canvas, build()); };
  document.addEventListener("themechange", onTheme);
  return {
    update(newPoints) {
      points = newPoints;
      chart.data.datasets[0].data = newPoints;
      chart.options.plugins.decimation.enabled = newPoints.length > 800;
      if (newPoints.length) {
        chart.options.scales.x.min = newPoints[0].x;
        chart.options.scales.x.max = newPoints[newPoints.length - 1].x;
      }
      chart.update();
    },
    destroy() { document.removeEventListener("themechange", onTheme); chart.destroy(); },
  };
}
