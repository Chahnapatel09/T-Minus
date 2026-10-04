(() => {
  "use strict";
  const D = window.TMINUS_DATA || window.TMINUS_SAMPLE;
  const REAL = !D.sample;
  const WORLD = D.world, SCENES = D.scenes, A = D.alerts;
  const app = document.getElementById("app");
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const TYPE = {
    pond: { label: "Pond or flooded pit", chip: "Pond", title: "New pond cluster" },
    bare: { label: "Bare sand or tailings", chip: "Bare ground", title: "New bare sand or tailings" },
    clearing: { label: "Fresh clearing", chip: "Clearing", title: "Fresh clearing" }
  };
  const CONF = { high: "High", medium: "Medium" };
  const STATUS = { "": "Not checked yet", checked: "Checked", confirmed: "Confirmed mining", none: "No mining found" };
  const FACTS = [
    ["92%", "drop in clearing in La Pampa after Operation Mercury began, Feb 2019"],
    ["900 ha", "cleared in La Pampa between February and June 2018"],
    ["24 days", "between RADARSAT-2 passes over the same spot"]
  ];
  const SOURCES = "Sources: MAAP #104; CSA, RADARSAT-2 Tropical Forests dataset";
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"];
  const day = iso => { const [y, m, d] = iso.split("-"); return `${+d} ${MON[m - 1]} ${y}`; };
  const month = iso => { const [y, m] = iso.split("-"); return `${MON[m - 1]} ${y}`; };
  const minus = n => String(n).replace("-", "−");
  const db = v => minus(v.toFixed(1));
  const km = m => (m == null ? "Not mapped" : `${(m / 1000).toFixed(1)} km`);
  const num = n => n.toLocaleString("en");
  const sum = (list, f) => list.reduce((t, a) => t + f(a), 0);

  const I = {
    logo: '<svg class="logo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4.5 8.5a10 10 0 0 1 15 0"/><path d="M8 11.5a5.5 5.5 0 0 1 8 0"/><path d="M12 13v8M9 16.5h6"/></svg>',
    arrow: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8h10M9 4l4 4-4 4"/></svg>',
    back: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13 8H3M7 4 3 8l4 4"/></svg>',
    download: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 2v8M4.5 7 8 10.5 11.5 7M3 13.5h10"/></svg>',
    copy: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 3.5v-1h-8v8h1"/></svg>',
    pin: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" aria-hidden="true"><path d="M8 14.5s4.5-4.2 4.5-7.7a4.5 4.5 0 0 0-9 0c0 3.5 4.5 7.7 4.5 7.7Z"/><circle cx="8" cy="6.7" r="1.6"/></svg>',
    search: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 3 3"/></svg>',
    locate: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M13.5 2.5 2.5 7l4.8 1.7L9 13.5Z"/></svg>',
    layers: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" aria-hidden="true"><path d="m8 2 6 3.2-6 3.2-6-3.2ZM2.5 8.3 8 11.2l5.5-2.9M2.5 11 8 13.9l5.5-2.9"/></svg>',
    map: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" aria-hidden="true"><path d="m2 4 4-1.5 4 1.5 4-1.5v9.5l-4 1.5-4-1.5-4 1.5ZM6 2.5V12M10 4v9.5"/></svg>',
    grip: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 4.5 2.5 8 6 11.5M10 4.5 13.5 8 10 11.5"/></svg>'
  };

  // ---------- data ----------
  // Real results come with lon/lat and the image bounds; the sample scene is
  // 20 m per unit, anchored on MDD-0142.
  const B = D.bounds;
  const toXY = (lon, lat) => ({ x: ((lon - B.west) / (B.east - B.west)) * WORLD.w, y: ((B.north - lat) / (B.north - B.south)) * WORLD.h });
  const toLatLon = (x, y) => (B
    ? { lon: B.west + (x / WORLD.w) * (B.east - B.west), lat: B.north - (y / WORLD.h) * (B.north - B.south) }
    : { lat: -13.0207 - ((y - 705) * 20) / 110574, lon: -70.1931 + ((x - 700) * 20) / 108467 });
  const byId = {};
  A.forEach((a, i) => {
    a.key = String(a.id);
    a.label = typeof a.id === "number" ? `Alert ${a.id}` : a.id;
    a.rank = i + 1;
    Object.assign(a, B ? toXY(a.lon, a.lat) : toLatLon(a.x, a.y));
    // a circle a bit wider than the patch, in map units
    a.r = Math.max(4, (Math.sqrt((a.area_ha * 10000) / Math.PI) / WORLD.m_per_unit) * 1.5 + 3);
    byId[a.key] = a;
  });
  const BOX = B && D.la_pampa ? (() => {
    const [w, s, e, n] = D.la_pampa, p = toXY(w, n), q = toXY(e, s);
    return [Math.max(0, p.x), Math.max(0, p.y), Math.min(WORLD.w, q.x), Math.min(WORLD.h, q.y)];
  })() : null;
  const HOME = BOX && BOX[2] > BOX[0] ? { cx: (BOX[0] + BOX[2]) / 2, cy: (BOX[1] + BOX[3]) / 2 } : { cx: WORLD.w / 2, cy: WORLD.h / 2 };

  const deg = (lat, lon, n) => `${Math.abs(lat).toFixed(n)}° ${lat < 0 ? "S" : "N"}, ${Math.abs(lon).toFixed(n)}° ${lon < 0 ? "W" : "E"}`;
  const coords = a => `${a.lat.toFixed(5)}, ${a.lon.toFixed(5)}`;
  const mapsUrl = a => `https://www.google.com/maps/search/?api=1&query=${a.lat.toFixed(5)},${a.lon.toFixed(5)}`;
  const navUrl = a => `https://www.google.com/maps/dir/?api=1&destination=${a.lat.toFixed(5)},${a.lon.toFixed(5)}`;
  const title = a => TYPE[a.type].title + (a.dist_river_m != null && a.dist_river_m <= 300 ? " beside the river" : a.dist_road_m != null && a.dist_road_m <= 1000 ? " near a road" : "");
  const kmBetween = (a, b) => (Math.hypot(a.x - b.x, a.y - b.y) * WORLD.m_per_unit) / 1000;
  // Which context maps the run had. A flag that is false for every alert means
  // the map was missing, so the page says "Not mapped" and not "No".
  const MAPPED = D.mapped || { buffer: true, indigenous: true, road: true, river: true, amw: false };
  const AMW_FIRST = D.accuracy && D.accuracy.agreement ? +D.accuracy.agreement.parts[0].label.match(/\d{4}/)[0] : 0;
  const AMW_LAST = D.accuracy && D.accuracy.agreement ? D.accuracy.agreement.last_year : 9999;
  // inside a mine that Amazon Mining Watch had mapped by the last scene
  const inMine = a => a.amw_year > 0 && a.amw_year <= AMW_LAST;
  const amwText = a => (!MAPPED.amw || a.amw_year == null ? "Not checked"
    : inMine(a) ? `Mapped as mining, first confirmed ${a.amw_year}${a.amw_year === AMW_FIRST ? " or earlier" : ""}`
    : a.amw_year > 0 ? `Not mapped as mining by ${AMW_LAST} (first confirmed ${a.amw_year})` : "Not mapped as mining");
  const flag = (on, mapped) => (on ? "Yes" : mapped ? "No" : "Not mapped");
  const sceneOf = a => { const i = SCENES.findIndex(s => s.date >= a.first_seen); return i < 0 ? SCENES.length - 1 : i; };
  // The scene where the centre of the alert first goes dark. A patch is dated by
  // its earliest pixel, so the centre can change a scene or two after first_seen.
  const darkScene = a => {
    const s = a.series || [], base = s.find(v => v != null), from = sceneOf(a);
    const i = s.findIndex((v, n) => n >= from && v != null && v <= base - D.drop_db);
    return i < 0 ? from : i;
  };

  // Field status lives in this browser only.
  let status = {};
  try { status = JSON.parse(localStorage.getItem("tminus.status")) || {}; } catch (e) { /* private mode */ }
  function setStatus(id, v) {
    if (v) status[id] = v; else delete status[id];
    try { localStorage.setItem("tminus.status", JSON.stringify(status)); } catch (e) { /* keep in memory */ }
  }

  // ---------- state ----------
  const state = {
    route: "home",
    before: 0,
    after: SCENES.length - 1,
    filter: "all",
    q: "",
    limit: 40,
    selected: null,
    split: 50,
    zoom: 1, cx: HOME.cx, cy: HOME.cy,
    layers: { change: true, zones: true },
    base: "satellite"
  };
  // Alerts first seen after the Before scene, up to the After scene.
  const pool = () => A.filter(a => (state.before === 0 || a.first_seen > SCENES[state.before].date) && a.first_seen <= SCENES[state.after].date);
  const FILTERS = [
    ["all", "All", () => true],
    ["high", "High", a => a.confidence === "high"],
    ["medium", "Medium", a => a.confidence === "medium"],
    ["pond", "Pond", a => a.type === "pond"],
    ["bare", "Bare ground", a => a.type === "bare"],
    ["clearing", "Clearing", a => a.type === "clearing"],
    ["buffer", "Reserve buffer", a => a.in_buffer],
    ["indigenous", "Indigenous land", a => a.in_indigenous]
  ];
  const matchesSearch = a => {
    const q = state.q.trim().toLowerCase();
    return !q || `${a.label} ${TYPE[a.type].label} ${title(a)} ${CONF[a.confidence]}`.toLowerCase().includes(q);
  };
  const filtered = () => pool().filter(a => FILTERS.find(f => f[0] === state.filter)[2](a) && matchesSearch(a));

  // ---------- routing ----------
  // Inside Streamlit the page is an srcdoc iframe, where hash links would
  // navigate the frame away, so routes are kept in memory there.
  const standalone = location.protocol !== "about:";
  function go(route) {
    if (standalone) { if (location.hash !== "#/" + route) { location.hash = "#/" + route; return; } }
    state.route = route;
    render();
    window.scrollTo(0, 0);
  }
  if (standalone) {
    window.addEventListener("hashchange", () => { state.route = location.hash.slice(2) || "home"; render(); window.scrollTo(0, 0); });
    state.route = location.hash.slice(2) || "home";
  }

  // ---------- shared pieces ----------
  const badge = a => `<span class="badge ${a.confidence}">${CONF[a.confidence]}</span>`;
  const tags = a =>
    (a.in_buffer ? '<span class="tag teal">Reserve buffer</span>' : "") +
    (a.in_indigenous ? '<span class="tag teal">Indigenous land</span>' : "") +
    (inMine(a) ? '<span class="tag">In a known mine</span>' : "");
  const chip = (a, scene, cls, size) => `<canvas class="${cls || "chip"}" data-chip="${esc(a.key)}" data-scene="${scene}" data-size="${size || "mid"}" role="img" aria-label="Radar image of ${esc(a.label)} on ${day(SCENES[scene].date)}"></canvas>`;
  const sampleNote = t => (D.sample ? `<p class="fine">${t}</p>` : "");
  const chips = () => `<div class="chips" role="group" aria-label="Filter alerts">
    ${FILTERS.map(([k, l, f]) => {
      const n = pool().filter(a => f(a) && matchesSearch(a)).length;
      return n || k === "all" || k === state.filter ? `<button id="f-${k}" class="chipbtn" data-filter="${k}" aria-pressed="${state.filter === k}">${l}<b>${n}</b></button>` : "";
    }).join("")}
  </div>`;
  const rowHtml = a => `<li><button id="row-${esc(a.key)}" class="row" data-select="${esc(a.key)}" aria-pressed="${a.key === state.selected}">
    ${chip(a, state.after, "mini", "tight")}
    <span class="row-body">
      <span class="row-top"><span class="mono">${esc(a.label)}</span>${badge(a)}</span>
      <span class="row-title">${TYPE[a.type].title}</span>
      <span class="row-meta">${a.area_ha} ha · first seen ${month(a.first_seen)}</span>
    </span>
  </button></li>`;
  const listHtml = list => `<ol class="rows">
    ${list.slice(0, state.limit).map(rowHtml).join("") || `<li class="empty">No alerts match${state.q ? " this search" : " this filter"}.</li>`}
    ${list.length > state.limit ? `<li>${more(state.limit, list.length)}</li>` : ""}
  </ol>`;
  const more = (shown, total) => (total > shown ? `<button class="btn quiet small more" id="more" data-more>Show ${Math.min(40, total - shown)} more</button>` : "");

  // Paint one scene. Real results draw the pipeline's image (and the confidence
  // overlay); the sample draws every site mined by that date.
  function paint(canvas, v, scene, o) {
    o = o || {};
    if (REAL) Scene.radar(canvas, v, null, null, { world: WORLD, img: SCENES[scene].img, overlay: o.overlay === "main" ? D.overlay_main || D.overlay : o.overlay ? D.overlay : null, rings: o.rings, ring: o.ring });
    else Scene.radar(canvas, v, A.filter(a => a.first_seen <= SCENES[scene].date), o.outlined || [], { seed: scene + 1, ring: o.ring });
  }
  function paintChips() {
    $$("canvas[data-chip]").forEach(c => {
      const a = byId[c.dataset.chip], scene = +c.dataset.scene, size = c.dataset.size, tight = size === "tight";
      if (size === "whole") {
        // the whole study area, with the detected change on the After picture and a ring on this alert
        const after = scene === state.after, ring = { x: a.x, y: a.y, r: Math.max(a.r, WORLD.w * 0.02), confidence: a.confidence };
        // fill the panel's height; a study area wider than the panel is centred on this alert
        const span = Math.min(WORLD.w, (WORLD.h * c.clientWidth) / Math.max(c.clientHeight, 1));
        const cx = Math.min(WORLD.w - span / 2, Math.max(span / 2, a.x));
        paint(c, { cx, cy: WORLD.h / 2, span }, scene, { overlay: after ? "main" : false, rings: after ? [ring] : [], ring: 2.5, outlined: after ? pool() : [] });
        return;
      }
      // width of ground shown: [times the alert's radius, at least this many metres, sample units]
      const [k, m, u] = { tight: [5, 900, 150], mid: [7, 1800, 230], wide: [9, 4000, 330] }[size];
      const span = REAL ? Math.max(a.r * k, m / WORLD.m_per_unit) : u;
      const shown = SCENES[scene].date >= a.first_seen;
      // keep the picture inside the image when the alert is near its edge
      const hw = Math.min(span, WORLD.w) / 2, hh = Math.min((span * c.clientHeight) / Math.max(c.clientWidth, 1), WORLD.h) / 2;
      const cx = Math.min(WORLD.w - hw, Math.max(hw, a.x)), cy = Math.min(WORLD.h - hh, Math.max(hh, a.y));
      paint(c, { cx, cy, span }, scene, {
        overlay: false, rings: shown ? [a] : [], ring: tight ? 2 : 3,
        outlined: A.filter(b => b.first_seen <= SCENES[scene].date && sceneOf(b) === sceneOf(a))
      });
    });
  }

  // "detections" is the side-by-side investigation screen, "monitor" the map
  const NAV = [["detections", "Overview"], ["monitor", "Map"], ["analytics", "Analytics"], ["reports", "Reports"]];
  function header(opts) {
    opts = opts || {};
    const pick = (id, label, value, from, to) => `<label class="picker"><span>${label}</span><select id="${id}">${SCENES.map((s, i) => (i >= from && i <= to ? `<option value="${i}" ${i === value ? "selected" : ""}>${day(s.date)}</option>` : "")).join("")}</select></label>`;
    return `
    <header class="hdr">
      <button class="brand" data-go="home" aria-label="T-Minus home">${I.logo}<span><b>T-Minus</b><small>Gold Mining Radar Monitor</small></span></button>
      <nav class="seg" aria-label="Sections">
        ${NAV.map(([r, l]) => `<button id="nav-${r}" data-go="${r}" ${state.route === r ? 'aria-current="page"' : ""}>${l}</button>`).join("")}
      </nav>
      <div class="hdr-right">
        ${opts.search ? `<label class="search">${I.search}<span class="sr">Search alerts</span><input id="search" type="search" placeholder="Search by ID or type" value="${esc(state.q)}" autocomplete="off"></label>` : ""}
        ${opts.dates ? pick("before", "Before", state.before, 0, SCENES.length - 2) + pick("after", "After", state.after, 1, SCENES.length - 1) : ""}
        ${D.sample ? '<span class="pill" title="No pipeline results found in outputs/, so the page shows sample values">Sample data</span>' : ""}
      </div>
    </header>`;
  }
  const footer = note => `
    <footer class="foot">
      <span><b>T-Minus</b> &nbsp;|&nbsp; ${esc(D.sensor)}${note ? " &nbsp;|&nbsp; " + note : ""}</span>
      <span>${esc(D.credit || "")}</span>
    </footer>`;

  // ---------- home ----------
  function home() {
    return `${header()}
    <main class="hero">
      <section class="hero-copy">
        <p class="eyebrow">Madre de Dios, Peru · RADARSAT-2</p>
        <h1>Clouds hide the mining. Radar doesn't.</h1>
        <p class="lede">Illegal gold mining clears forest and digs pits faster than anyone can check on the ground. We compare RADARSAT-2 scenes taken through the cloud to show rangers and prosecutors which sites are new, how big they are and where to act first.</p>
        <div class="cta">
          <button class="btn primary big" data-go="detections">Open the monitor ${I.arrow}</button>
          <button class="link" data-go="analytics">How we check accuracy</button>
        </div>
        <dl class="facts">
          ${FACTS.map(([v, t]) => `<div><dt>${v}</dt><dd>${t}</dd></div>`).join("")}
        </dl>
        <p class="fine">${SOURCES}</p>
      </section>
      <section class="hero-pair" aria-label="The same place seen by an optical satellite and by radar">
        <figure>
          <div class="frame">${D.optical
            ? `<img src="${D.optical}" alt="Sentinel-2 optical image, mostly covered by cloud">`
            : REAL
              ? '<p class="frame-note">Add a cloudy Sentinel-2 screenshot as app/assets/sentinel2.png to show it here.</p>'
              : '<canvas id="cv-optical" role="img" aria-label="Optical satellite image, mostly covered by cloud"></canvas>'}</div>
          <figcaption>Sentinel-2 optical<span>${D.optical_info ? `${day(D.optical_info.date)} · cloud hides the ground` : "Cloud hides the ground"}</span></figcaption>
        ${D.optical_info && D.optical_info.credit ? `<p class="fine">${esc(D.optical_info.credit)}.</p>` : ""}
        </figure>
        <figure>
          <div class="frame"><canvas id="cv-radar" role="img" aria-label="Radar image of La Pampa with new mining marked"></canvas>
            ${D.optical_info ? "" : `<span class="pill-over">${A.length} new sites</span>`}</div>
          <figcaption>RADARSAT-2 radar<span>${REAL ? `${day(SCENES[SCENES.length - 1].date)} · ${D.optical_info && D.optical_info.date === SCENES[SCENES.length - 1].date ? "same day, same place, new mining in red" : "new mining marked"}` : "Same week · new mining outlined"}</span></figcaption>
        </figure>
        ${sampleNote("Illustrative images. They are replaced by the processed radar scene once the pipeline has run.")}
      </section>
    </main>`;
  }
  function mountHome() {
    const last = SCENES.length - 1;
    const v = BOX && BOX[2] > BOX[0] ? { cx: HOME.cx, cy: HOME.cy, span: Math.max(BOX[2] - BOX[0], (BOX[3] - BOX[1]) * (1000 / 860)) } : { cx: WORLD.w / 2, cy: WORLD.h / 2, span: Math.max(WORLD.w, WORLD.h * (1000 / 860)) };
    if ($("#cv-optical")) Scene.optical($("#cv-optical"), v, A);
    // with a real optical image, the radar picture shows exactly the same ground
    const ob = B && D.optical_info && D.optical_info.bounds_WSEN;
    if (ob) { const p = toXY(ob[0], ob[3]), q = toXY(ob[2], ob[1]); Object.assign(v, { cx: (p.x + q.x) / 2, cy: (p.y + q.y) / 2, span: q.x - p.x }); }
    paint($("#cv-radar"), v, last, { overlay: ob ? "main" : true, outlined: A });
  }

  const markerHtml = a => `<button id="mk-${esc(a.key)}" class="marker ${a.confidence} ${a.key === state.selected ? "sel" : ""}" data-marker="${esc(a.key)}" aria-label="Priority ${a.rank}, ${esc(a.label)}, ${CONF[a.confidence]} confidence${a.key === state.selected ? ". Open details" : ""}">${a.rank}</button>`;

  // ---------- real basemap (Leaflet) ----------
  // With real results and the map library loaded, the Overview map is a real
  // web map: satellite or street tiles, with the radar scenes, the change
  // overlay and the alerts on top. Without either it falls back to the canvas.
  const LEAF = REAL && !!B && !!window.L;
  const TILES = {
    satellite: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "Imagery © Esri, Maxar, Earthstar Geographics", 18],
    street: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png", "© OpenStreetMap contributors", 19]
  };
  let lmap = null, lhost = null, G = null, lastSel = null, focusOnMap = false;
  function leafletInit() {
    const bounds = [[B.south, B.west], [B.north, B.east]];
    lhost = document.createElement("div");
    lhost.className = "lmap";
    lmap = L.map(lhost, { zoomControl: false, attributionControl: false, zoomSnap: 0.25, zoomAnimation: false, minZoom: 5, maxZoom: 18 });
    [["before", 250], ["after", 260], ["change", 270]].forEach(([n, z]) => { lmap.createPane(n).style.zIndex = z; });
    G = {
      tiles: Object.fromEntries(Object.entries(TILES).map(([k, [url, , max]]) => [k, L.tileLayer(url, { maxNativeZoom: max, maxZoom: 18 })])),
      before: L.imageOverlay(SCENES[state.before].img, bounds, { pane: "before" }),
      after: L.imageOverlay(SCENES[state.after].img, bounds, { pane: "after" }),
      change: D.overlay ? L.imageOverlay(D.overlay, bounds, { pane: "change" }) : null,
      zone: D.la_pampa ? L.rectangle([[D.la_pampa[1], D.la_pampa[0]], [D.la_pampa[3], D.la_pampa[2]]], { color: "#fff", weight: 1.5, dashArray: "6 5", fill: false, interactive: false })
        .bindTooltip("La Pampa (approximate)", { permanent: true, direction: "top", className: "map-tip" }) : null,
      markers: L.layerGroup().addTo(lmap),
      ring: L.layerGroup().addTo(lmap)
    };
    lmap.on("move zoomend resize", leafletSync);
  }
  const toggle = (layer, on) => { if (layer) { if (on) layer.addTo(lmap); else layer.remove(); } };
  // the part of the map not covered by the floating panels
  function gapBounds() {
    const size = lmap.getSize(), pad = floatPad() + 50;
    return L.latLngBounds(lmap.containerPointToLatLng([pad, 50]), lmap.containerPointToLatLng([size.x - pad, size.y - 50]));
  }
  function leafletUpdate() {
    const radar = state.base === "radar", shown = filtered().slice(0, state.limit), sel = state.selected && byId[state.selected];
    if (sel && !shown.includes(sel)) shown.push(sel);
    toggle(G.tiles.satellite, state.base !== "street");
    toggle(G.tiles.street, state.base === "street");
    G.before.setUrl(SCENES[state.before].img);
    G.after.setUrl(SCENES[state.after].img);
    toggle(G.before, radar);
    toggle(G.after, radar);
    toggle(G.change, state.layers.change);
    toggle(G.zone, state.layers.zones);
    G.markers.clearLayers();
    shown.forEach(a => L.marker([a.lat, a.lon], { icon: L.divIcon({ className: "lmk", iconSize: [0, 0], html: markerHtml(a) }), keyboard: false, zIndexOffset: a === sel ? 1000 : -a.rank }).addTo(G.markers));
    G.ring.clearLayers();
    if (sel && state.layers.change) L.circle([sel.lat, sel.lon], { radius: sel.r * WORLD.m_per_unit, color: sel.confidence === "high" ? "#ff3b3b" : "#ffb020", weight: 2.5, fill: false, interactive: false }).addTo(G.ring);
    if (sel && sel.key !== lastSel && lastSel !== null && !gapBounds().contains([sel.lat, sel.lon])) lmap.panTo([sel.lat, sel.lon]);
    lastSel = sel ? sel.key : "";
    $("#attrib").textContent = TILES[state.base === "street" ? "street" : "satellite"][1] + (state.base === "satellite" ? ". Recent imagery, not from the scene dates." : "");
    leafletSync();
  }
  // Things that follow the view: the divider's clip, the scale bar, the centre.
  function leafletSync() {
    const map = $("#map");
    if (!map || !lmap._loaded) return;
    const size = lmap.getSize(), nw = lmap.containerPointToLayerPoint([0, 0]), x = nw.x + (size.x * state.split) / 100;
    const clip = state.base === "radar" ? `polygon(${x}px ${nw.y}px, ${nw.x + size.x}px ${nw.y}px, ${nw.x + size.x}px ${nw.y + size.y}px, ${x}px ${nw.y + size.y}px)` : "";
    ["after", "change"].forEach(n => { lmap.getPane(n).style.clipPath = clip; });
    const pad = floatPad(), c = lmap.getCenter();
    $("#place").style.left = pad + 14 + "px";
    $("#ctrl").style.right = pad + 14 + "px";
    $("#basepick").style.left = pad + 14 + "px";
    $("#centre").textContent = deg(c.lat, c.lng, 2);
    const mPerPx = (40075016.686 * Math.cos((c.lat * Math.PI) / 180)) / Math.pow(2, lmap.getZoom() + 8);
    const len = [50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1].find(k => (k * 1000) / mPerPx <= 110) || 0.1;
    $("#scale").style.width = (len * 1000) / mPerPx + "px";
    $("#scale-km").textContent = len + " km";
  }
  function leafletMount() {
    if (!lmap) leafletInit();
    $("#lmap-slot").replaceWith(lhost);
    lmap.invalidateSize();
    if (!lmap._loaded) {
      // open on La Pampa (the part of it inside the study area), clear of the panels
      const pad = floatPad() + 12;
      const home = D.la_pampa ? [[Math.max(B.south, D.la_pampa[1]), Math.max(B.west, D.la_pampa[0])], [Math.min(B.north, D.la_pampa[3]), Math.min(B.east, D.la_pampa[2])]] : [[B.south, B.west], [B.north, B.east]];
      lmap.fitBounds(home, { paddingTopLeft: [pad, 12], paddingBottomRight: [pad, 12] });
    }
    if (focusOnMap && state.selected) lmap.setView([byId[state.selected].lat, byId[state.selected].lon], Math.max(lmap.getZoom(), 13.5));
    focusOnMap = false;
    leafletUpdate();
  }

  // ---------- overview: map with floating panels ----------
  function monitor() {
    const b = SCENES[state.before].date, af = SCENES[state.after].date, all = pool(), list = filtered();
    if (!list.some(a => a.key === state.selected)) state.selected = list.length ? list[0].key : null;
    const sel = state.selected && byId[state.selected];
    const shown = list.slice(0, state.limit);
    if (sel && !shown.includes(sel)) shown.push(sel);
    // the before/after divider only makes sense while radar scenes are showing
    const swipe = !LEAF || state.base === "radar";

    return `${header({ search: true, dates: true })}
    <main class="stage">
      <div class="map" id="map" style="--split:${state.split}">
        ${LEAF ? `<div id="lmap-slot"></div>
        <div class="seg basepick" id="basepick" role="group" aria-label="Map view">
          ${[["satellite", "Satellite"], ["radar", "Radar"], ["street", "Street"]].map(([k, l]) => `<button id="base-${k}" data-base="${k}" aria-pressed="${state.base === k}">${l}</button>`).join("")}
        </div>` : `
        <canvas class="lyr" id="cv-before" role="img" aria-label="Radar image before, ${day(b)}"></canvas>
        <div class="after-clip"><canvas class="lyr" id="cv-after" role="img" aria-label="Radar image after, ${day(af)}, with new mining marked"></canvas></div>
        <canvas class="lyr" id="cv-zones" aria-hidden="true"></canvas>
        <span class="map-label" id="lp-label">La Pampa${REAL ? " (approximate)" : " sector"}</span>
        ${shown.map(a => markerHtml(a)).join("")}`}
        ${swipe ? `<div class="stamp l"><small>Before</small>${day(b)}</div>
        <div class="stamp r"><small>After</small>${day(af)}</div>
        <div class="divider" id="divider" role="slider" tabindex="0" aria-label="Before and after divider" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(state.split)}"><span class="knob">${I.grip}</span></div>` : ""}
        <div class="place" id="place">${esc(D.place)}<span class="mono" id="centre"></span>${LEAF ? '<span class="attrib" id="attrib"></span>' : ""}</div>
        <div class="ctrl" id="ctrl">
          <div class="scale" id="scale"><i></i><span class="mono">0</span><span class="mono" id="scale-km">5 km</span></div>
          <details class="layers" id="layers">
            <summary aria-label="Map layers and legend" title="Layers and legend">${I.layers}</summary>
            <div class="layers-pop">
              <label class="check"><input type="checkbox" id="layer-change" data-layer="change" ${state.layers.change ? "checked" : ""}> ${REAL ? "Detected change" : "Change outlines"}</label>
              <label class="check"><input type="checkbox" id="layer-zones" data-layer="zones" ${state.layers.zones ? "checked" : ""}> Zones</label>
              <hr>
              <span><i class="${REAL ? "swatch" : "ring"} high"></i>High confidence</span>
              <span><i class="${REAL ? "swatch" : "ring"} medium"></i>Medium confidence</span>
              ${REAL ? "" : '<span><i class="ln teal"></i>Reserve boundary</span>'}
              <span><i class="ln grey"></i>La Pampa</span>
            </div>
          </details>
          <button id="locate" data-locate aria-label="Centre on the selected alert" title="Centre on the selected alert">${I.locate}</button>
          <button id="zoom-in" data-zoom="1" aria-label="Zoom in">+</button>
          <button id="zoom-out" data-zoom="-1" aria-label="Zoom out">−</button>
        </div>
      </div>

      <section class="float left" aria-label="New mining alerts">
        <div class="float-head">
          <h2>New mining alerts</h2>
          <p>First seen ${day(b)} → ${day(af)}</p>
        </div>
        ${chips()}
        ${listHtml(list)}
        <div class="float-foot"><span>Showing ${Math.min(state.limit, list.length)} of ${all.length}</span><button class="link" data-go="detections">Investigate</button></div>
      </section>

      <section class="float right" aria-label="Selected alert">${sel ? panel(sel, all) : '<div class="info"><p class="empty">Select an alert to see its details.</p></div>'}</section>
    </main>
    ${footer(D.sample ? "Radar images are illustrative until the pipeline has run" : `${SCENES.length} scenes, ${day(SCENES[0].date)} to ${day(SCENES[SCENES.length - 1].date)}`)}`;
  }

  function panel(a, all) {
    const s = a.series || [], before = s[state.before], after = s[state.after];
    const near = all.filter(x => x !== a && kmBetween(a, x) <= 5).sort((x, y) => kmBetween(a, x) - kmBetween(a, y)).slice(0, 6);
    const base = s.find(v => v != null), lo = -25;
    return `
      <div class="float-head">
        <h2>Detection <span class="mono">${esc(a.label)}</span>${badge(a)}</h2>
        <p>${TYPE[a.type].label} · priority ${a.rank} of ${A.length}</p>
      </div>
      <div class="info">
        <div class="prob">
          <div><span>Priority score</span><b>${a.priority} / 100</b></div>
          <span class="track ${a.confidence}"><i style="width:${Math.round(a.priority)}%"></i></span>
        </div>
        <dl class="facts2">
          <div><dt>Area</dt><dd>${a.area_ha} ha</dd></div>
          <div><dt>First seen</dt><dd>${day(a.first_seen)}</dd></div>
          <div class="wide"><dt>Coordinates</dt><dd class="mono">${deg(a.lat, a.lon, 4)}</dd></div>
          ${tags(a) ? `<div class="wide">${tags(a)}</div>` : ""}
        </dl>
        ${before == null || after == null ? "" : `<div>
          <h3>Backscatter analysis</h3>
          <dl class="db">
            <div><dt>Before (dB)</dt><dd>${db(before)}</dd></div>
            <div><dt>After (dB)</dt><dd>${db(after)}</dd></div>
            <div><dt>Change (dB)</dt><dd class="chg">${db(after - before)}</dd></div>
          </dl>
        </div>`}
        ${base == null ? "" : `<div>
          <h3>Time series <span>${s.length} scenes${D.sample ? " · illustrative" : ""}</span></h3>
          <div class="series" role="img" aria-label="Radar brightness at this alert in each scene, from ${day(SCENES[0].date)} to ${day(SCENES[s.length - 1].date)}.">
            ${s.map((v, i) => (v == null ? '<i class="gap" title="' + day(SCENES[i].date) + ': no data"></i>' : `<i class="${v <= base - D.drop_db ? "hit" : ""}" style="height:${Math.max(8, Math.min(100, ((v - lo) / -lo) * 100)).toFixed(0)}%" title="${day(SCENES[i].date)}: ${db(v)} dB"></i>`)).join("")}
          </div>
          <p class="fine">Brightness at the alert in each scene. Red bars are ${D.drop_db} dB or more below the first.</p>
        </div>`}
        <div>
          <h3>Nearby detections <span>within 5 km</span></h3>
          <div class="near">${near.map(x => `<button data-select="${esc(x.key)}"><span class="mono">${esc(x.label)}</span><span class="dist">${x.area_ha} ha · ${kmBetween(a, x).toFixed(1)} km</span>${badge(x)}</button>`).join("") || '<p class="fine">None in this period.</p>'}</div>
        </div>
      </div>
      <div class="float-actions">
        <button class="btn quiet" data-go="alert/${esc(a.key)}">Investigate</button>
        <button class="btn primary" data-export="kml" data-one="${esc(a.key)}">${I.download} Export KML</button>
      </div>`;
  }

  // ---------- map ----------
  // On wide screens the panels float over the map, so the scene is fitted to
  // the gap between them and the map carries on underneath. A study area much
  // wider than the gap fills the height instead and is panned.
  const floatPad = () => (window.matchMedia("(min-width: 1100px)").matches ? 342 : 0);
  function view() {
    const map = $("#map"), w = map.clientWidth, h = map.clientHeight;
    const contain = Math.min((w - 2 * floatPad()) / WORLD.w, h / WORLD.h) * 0.97;
    const k0 = (WORLD.h * contain) / h >= 0.6 ? contain : h / WORLD.h;
    // Keep the image filling the gap between the panels: never show the empty
    // space past its edges unless the whole image is smaller than the gap.
    const k = k0 * state.zoom, halfW = (w - 2 * floatPad()) / 2 / k, halfH = h / 2 / k;
    state.cx = WORLD.w < halfW * 2 ? WORLD.w / 2 : Math.min(WORLD.w - halfW, Math.max(halfW, state.cx));
    state.cy = WORLD.h < halfH * 2 ? WORLD.h / 2 : Math.min(WORLD.h - halfH, Math.max(halfH, state.cy));
    const span = w / k;
    return { cx: state.cx, cy: state.cy, span, hh: (span * h) / w / 2, w };
  }
  function drawMap() {
    const map = $("#map");
    if (!map) return;
    if (LEAF) return leafletUpdate();
    const v = view(), list = filtered().slice(0, state.limit), sel = state.selected && byId[state.selected];
    paint($("#cv-before"), v, state.before);
    paint($("#cv-after"), v, state.after, { overlay: state.layers.change, rings: state.layers.change && sel ? [sel] : [], outlined: state.layers.change ? list : [] });
    Scene.zones($("#cv-zones"), v, state.layers.zones, BOX);
    const place = (el, x, y) => {
      const fx = (x - (v.cx - v.span / 2)) / v.span, fy = (y - (v.cy - v.hh)) / (v.hh * 2);
      el.style.left = fx * 100 + "%";
      el.style.top = fy * 100 + "%";
      el.style.visibility = fx < 0 || fx > 1 || fy < 0 || fy > 1 ? "hidden" : "";
    };
    $$("[data-marker]", map).forEach(el => { const a = byId[el.dataset.marker]; place(el, a.x, a.y); });
    const label = $("#lp-label");
    if (BOX) place(label, (BOX[0] + BOX[2]) / 2, BOX[1] + 14 / (v.w / v.span)); else place(label, 275, 552);
    label.hidden = !state.layers.zones || (REAL && !BOX);
    // keep the map furniture inside the gap between the panels
    const pad = floatPad();
    $("#place").style.left = pad + 14 + "px";
    $("#ctrl").style.right = pad + 14 + "px";
    const c = toLatLon(v.cx, v.cy);
    $("#centre").textContent = deg(c.lat, c.lon, 2);
    // pick the longest round distance that stays under 110 px
    const px = k => ((k * 1000) / WORLD.m_per_unit / v.span) * v.w;
    const len = [50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1].find(k => px(k) <= 110) || 0.1;
    $("#scale").style.width = px(len) + "px";
    $("#scale-km").textContent = len + " km";
  }

  let ro = null, raf = 0;
  const redraw = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(drawMap); };
  function mountMonitor() {
    const map = $("#map"), div = $("#divider");
    const setSplit = s => {
      const edge = ((floatPad() + 30) / map.clientWidth) * 100;
      state.split = Math.min(100 - Math.max(2, edge), Math.max(2, edge, s));
      map.style.setProperty("--split", state.split);
      if (div) div.setAttribute("aria-valuenow", Math.round(state.split));
      if (LEAF && lmap) leafletSync();
    };
    if (div) div.addEventListener("pointerdown", e => {
      div.setPointerCapture(e.pointerId);
      const move = ev => { const r = map.getBoundingClientRect(); setSplit(((ev.clientX - r.left) / r.width) * 100); };
      const up = () => { div.removeEventListener("pointermove", move); div.removeEventListener("pointerup", up); div.removeEventListener("pointercancel", up); };
      div.addEventListener("pointermove", move);
      div.addEventListener("pointerup", up);
      div.addEventListener("pointercancel", up);
      e.preventDefault();
    });
    if (div) div.addEventListener("keydown", e => {
      const step = { ArrowLeft: -2, ArrowRight: 2, Home: -100, End: 100 }[e.key];
      if (step) { setSplit(state.split + step); e.preventDefault(); }
    });
    if (LEAF) {
      leafletMount();
      ro = new ResizeObserver(() => { lmap.invalidateSize(); setSplit(state.split); });
      ro.observe(map);
      scrollToRow();
      return;
    }
    // drag to move around
    map.addEventListener("pointerdown", e => {
      if (e.target.closest("button, summary, label, .divider")) return;
      const sx = e.clientX, sy = e.clientY, cx = state.cx, cy = state.cy, k = view().span / map.clientWidth;
      map.setPointerCapture(e.pointerId);
      map.classList.add("panning");
      const move = ev => { state.cx = cx - (ev.clientX - sx) * k; state.cy = cy - (ev.clientY - sy) * k; redraw(); };
      const up = () => { map.classList.remove("panning"); map.removeEventListener("pointermove", move); map.removeEventListener("pointerup", up); map.removeEventListener("pointercancel", up); };
      map.addEventListener("pointermove", move);
      map.addEventListener("pointerup", up);
      map.addEventListener("pointercancel", up);
    });
    if (focusOnMap && state.selected) { state.zoom = Math.max(state.zoom, 2.56); state.cx = byId[state.selected].x; state.cy = byId[state.selected].y; }
    focusOnMap = false;
    ro = new ResizeObserver(() => { setSplit(state.split); redraw(); });
    ro.observe(map);
    drawMap();
    scrollToRow();
  }
  // bring the selected row into view inside the list, without moving the page
  function scrollToRow() {
    const row = $(".row[aria-pressed='true']"), box = $(".rows");
    if (row && (row.offsetTop < box.scrollTop || row.offsetTop + row.offsetHeight > box.scrollTop + box.clientHeight)) box.scrollTop = row.offsetTop - 8;
  }

  // ---------- detections: side-by-side investigation ----------
  function investigation(a, all) {
    const s = a.series || [], vb = s[state.before], va = s[state.after], base = s.find(v => v != null), lo = -25;
    const near = all.filter(x => x !== a && kmBetween(a, x) <= 5).sort((x, y) => kmBetween(a, x) - kmBetween(a, y)).slice(0, 3);
    const shot = (scene, label, v, change) => `
      <figure class="shot">
        ${chip(a, scene, "shotcv", "whole")}
        <span class="shot-date"><small>${label}</small>${day(SCENES[scene].date)}</span>
        ${v == null ? "" : `<span class="shot-db">Backscatter <b class="mono">${db(v)} dB</b></span>`}
        ${change == null ? "" : `<span class="shot-chg mono">${db(change)} dB change</span>`}
      </figure>`;
    return `
      <p class="crumb">Overview / <span class="mono">${esc(a.label)}</span></p>
      <div class="inv-head">
        <div>
          <h1>${title(a)} ${badge(a)}</h1>
          <p class="inv-sub"><span class="mono">${deg(a.lat, a.lon, 4)}</span> &nbsp; First seen ${day(a.first_seen)}</p>
        </div>
        <div class="inv-actions">
          <button class="btn outline" data-openmap="${esc(a.key)}">${I.map} Open in map</button>
          <button class="btn primary" data-export="kml" data-one="${esc(a.key)}">${I.download} Export KML</button>
        </div>
      </div>
      <div class="inv-pair" style="--ar:${WORLD.w} / ${WORLD.h}">
        ${shot(state.before, "Before", vb)}
        ${shot(state.after, "After", va, vb == null || va == null ? null : va - vb)}
      </div>
      ${REAL && D.overlay_main ? '<p class="fine pair-note">Red on the After image marks the large, high-confidence changes only. The Map tab shows every detection.</p>' : ""}
      <div class="inv-stats">
        <div class="card"><span>Area</span><b>${a.area_ha} ha</b></div>
        <div class="card"><span>Priority score</span><b class="right">${a.priority} / 100</b><i class="track ${a.confidence}"><i style="width:${Math.round(a.priority)}%"></i></i></div>
        <div class="card"><span>Type</span><b>${TYPE[a.type].label}</b></div>
        <div class="card"><span>Coordinates</span><b class="mono coord">${coords(a)}<button class="iconbtn" data-copy="${coords(a)}" aria-label="Copy coordinates" title="Copy coordinates">${I.copy}</button></b></div>
      </div>
      <div class="inv-grid">
        <div class="card">
          <h3>Backscatter analysis</h3>
          ${vb == null || va == null ? '<p class="fine">No radar data at this point in one of the two scenes.</p>' : `<dl class="dbrows">
            <div><dt>Before (dB)</dt><dd class="mono">${db(vb)}</dd></div>
            <div><dt>After (dB)</dt><dd class="mono">${db(va)}</dd></div>
            <div class="chg"><dt>Change (dB)</dt><dd class="mono">${db(va - vb)}</dd></div>
          </dl>`}
        </div>
        <div class="card">
          <h3>Time series <span>${s.length} scenes${D.sample ? " · illustrative" : ""}</span></h3>
          ${base == null ? '<p class="fine">No radar data at this point.</p>' : `<div class="series tall" role="img" aria-label="Radar brightness at this alert in each scene, from ${day(SCENES[0].date)} to ${day(SCENES[s.length - 1].date)}.">
            ${s.map((v, i) => (v == null ? `<i class="gap" title="${day(SCENES[i].date)}: no data"></i>` : `<i class="${v <= base - D.drop_db ? "hit" : ""}" style="height:${Math.max(8, Math.min(100, ((v - lo) / -lo) * 100)).toFixed(0)}%" title="${day(SCENES[i].date)}: ${db(v)} dB"></i>`)).join("")}
          </div>
          <p class="fine">Brightness at the alert in each scene. Red bars are ${D.drop_db} dB or more below the first.</p>`}
        </div>
        <div class="card">
          <h3>Nearby detections <span>within 5 km</span></h3>
          <div class="near">${near.map(x => `<button data-select="${esc(x.key)}"><span class="mono">${esc(x.label)}</span><span class="dist">${x.area_ha} ha · ${kmBetween(a, x).toFixed(1)} km</span>${badge(x)}</button>`).join("") || '<p class="fine">None between these dates.</p>'}</div>
        </div>
      </div>
`;
  }

  function detections() {
    const all = pool(), list = filtered();
    if (!list.some(a => a.key === state.selected)) state.selected = list.length ? list[0].key : null;
    const a = state.selected && byId[state.selected];
    return `${header({ search: true, dates: true })}
    <main class="invest">
      <section class="card inv-list" aria-label="Alerts">
        <div class="float-head">
          <h2>Recent detections</h2>
          <p>Potential mining activity from radar analysis</p>
        </div>
        ${chips()}
        ${listHtml(list)}
        <div class="float-foot"><span>Showing ${Math.min(state.limit, list.length)} of ${num(all.length)}</span></div>
      </section>
      <section class="inv-main" aria-label="Selected alert">
        ${a ? investigation(a, all) : '<div class="card"><p class="empty">No alert selected. Change the filter or the search to see alerts.</p></div>'}
        ${sampleNote("Sample values and illustrative radar images.")}
      </section>
    </main>
    ${footer()}`;
  }

  // ---------- analytics ----------
  // Grouped bars: rows of {label, inside, outside}. mark is the bar group the
  // event line sits before (a whole number), or inside (x.5).
  function barChart(rows, unit, mark, event) {
    const n = rows.length, top = Math.max(1, ...rows.map(r => Math.max(r.inside, r.outside)));
    const step = Math.pow(10, Math.floor(Math.log10(top))), max = Math.ceil(top / step) * step;
    const x0 = 34, x1 = 296, y0 = 18, y1 = 146, gw = (x1 - x0) / n, bw = Math.min(gw * 0.38, 16);
    const y = v => y1 - (v / max) * (y1 - y0);
    const every = Math.ceil(n / 12);
    const bars = rows.map((r, i) => {
      const gx = x0 + i * gw + (gw - bw * 2 - 1) / 2;
      return `<rect class="b-lp" x="${gx.toFixed(1)}" y="${y(r.inside).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y1 - y(r.inside)).toFixed(1)}"><title>La Pampa, ${r.long}: ${r.inside} ${unit}</title></rect>` +
        `<rect class="b-el" x="${(gx + bw + 1).toFixed(1)}" y="${y(r.outside).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y1 - y(r.outside)).toFixed(1)}"><title>Elsewhere, ${r.long}: ${r.outside} ${unit}</title></rect>` +
        (i % every === 0 ? `<text x="${(gx + bw).toFixed(1)}" y="160" text-anchor="middle">${esc(r.label)}</text>` : "");
    }).join("");
    const grid = [0, max / 2, max].map(v => `<line class="grid" x1="${x0}" x2="${x1}" y1="${y(v)}" y2="${y(v)}"/><text x="${x0 - 5}" y="${y(v) + 3}" text-anchor="end">${num(v)}</text>`).join("");
    const ex = mark == null ? null : x0 + mark * gw, flip = ex > (x0 + x1) / 2;
    return `<svg class="chart" viewBox="0 0 300 166" role="img" aria-label="Bar chart of ${unit} in La Pampa and elsewhere. ${rows.map(r => `${r.long}: La Pampa ${r.inside}, elsewhere ${r.outside}`).join("; ")}.">
      ${grid}${bars}
      ${ex == null ? "" : `<line class="event" x1="${ex}" x2="${ex}" y1="${y0 - 10}" y2="${y1}"/>
      <text class="ev" x="${ex + (flip ? -4 : 4)}" y="${y0 - 4}" text-anchor="${flip ? "end" : "start"}">${esc(event)}</text>`}
    </svg>`;
  }

  function crackdownCard() {
    const c = D.crackdown;
    if (!c || !c.rows.length) return '<div class="card chart-card"><p>No crackdown table yet. It is written by the pipeline as outputs/crackdown.csv.</p></div>';
    const when = `${MONTH[c.date.slice(5, 7) - 1]} ${c.date.slice(0, 4)}`;
    const rows = c.rows.map(r => ({
      ...r,
      label: r.label || `${MON[r.end.slice(5, 7) - 1]} '${r.end.slice(2, 4)}`,
      long: r.label ? r.label.replace("'", "20") : `${day(r.start)} to ${day(r.end)}`
    }));
    const firstAfter = rows.findIndex(r => r.phase !== "before");
    const mark = firstAfter < 0 ? null : rows[firstAfter].phase === "straddles" ? firstAfter + 0.5 : firstAfter;
    const s = c.summary || {}, bi = s.before && s.before.inside, ai = s.after && s.after.inside, bo = s.before && s.before.outside, ao = s.after && s.after.outside;
    const f = v => (v == null ? "n/a" : v.toFixed(1));
    const pct = (a, b) => (a ? ` (${b >= a ? "+" : "−"}${Math.abs(Math.round(((b - a) / a) * 100))}%)` : "");
    const text = bi == null || ai == null
      ? `There are not yet scenes on both sides of ${when}, so the rates before and after the crackdown cannot be compared. Add at least one scene interval that ends before it and one that starts after it.`
      : `After ${when}, new clearing in La Pampa ${ai < bi ? "fell" : ai > bi ? "rose" : "stayed level"} from ${f(bi)} to ${f(ai)} ha a month${pct(bi, ai)}` +
        (bo == null || ao == null || (!bo && !ao) ? "." : `, while elsewhere in the area it ${ao > bo ? "rose" : ao < bo ? "fell" : "stayed level"} from ${f(bo)} to ${f(ao)}${pct(bo, ao)}.`);
    // Amazon Mining Watch: its first year holds everything mined up to then, so it is described, not charted.
    const amwFirst = c.amw && c.amw[0], amw = c.amw ? c.amw.slice(1) : [];
    const ha = v => num(Math.round(v)) + " ha";
    let amwText = "";
    if (amw.length) {
      const a0 = amw[0], aN = amw[amw.length - 1], low = amw.reduce((m, r) => (r.inside < m.inside ? r : m));
      const trend = (from, to) => (to > from * 1.1 ? "rose" : to < from * 0.9 ? "fell" : "stayed about level");
      amwText = `In La Pampa, newly confirmed mining ${low === a0 ? "was lowest" : `fell from ${ha(a0.inside)} in ${a0.label} to a low of ${ha(low.inside)}`} in ${low.label}` +
        (low !== aN ? `${aN.inside > low.inside * 1.5 ? ", then rose to" : " and was"} ${ha(aN.inside)} in ${aN.label}` : "") +
        `. Elsewhere in the area it ${trend(a0.outside, aN.outside)}, from ${ha(a0.outside)} in ${a0.label} to ${ha(aN.outside)} in ${aN.label}.`;
    }
    // the crackdown year's bar holds the months after it began, so the line sits at that bar's left edge
    const amwMark = amw.findIndex(r => r.label >= c.date.slice(0, 4));
    const radarCard = `<div class="card chart-card">
          <p>${rows[0].start ? "<strong>From our radar scenes.</strong> " : ""}${text}</p>
          <div class="key"><span><i class="swatch blue"></i>La Pampa</span><span><i class="swatch green"></i>Elsewhere in the area</span></div>
          ${barChart(rows, c.unit, mark, `${c.event}, ${month(c.date)}`)}
          <p class="fine">Newly cleared, ${c.unit}${rows[0].start ? ", for each interval between two scenes (labelled by its end date). An interval that spans the crackdown is left out of the before and after averages" : ""}.${D.sample ? " Sample values." : ""}</p>
        </div>`;
    const amwCard = !amw.length ? "" : `<div class="card chart-card">
          <p><strong>From Amazon Mining Watch.</strong> ${amwText}</p>
          <div class="key"><span><i class="swatch blue"></i>La Pampa</span><span><i class="swatch green"></i>Elsewhere in the area</span></div>
          ${barChart(amw.map(r => ({ ...r, long: r.label })), "ha", amwMark < 0 ? null : amwMark, `${c.event}, ${month(c.date)}`)}
          <p class="fine">Hectares first confirmed as mining each year, mapped from optical Sentinel-2 imagery by Earth Genome, so it does not depend on our radar. ${amwFirst.label} is left off because it holds everything mined up to then (${ha(amwFirst.inside)} in La Pampa, ${ha(amwFirst.outside)} elsewhere), so there is no single pre-crackdown year to compare with. The latest year may be incomplete. Source: Amazon Mining Watch (Earth Genome, Pulitzer Center, Amazon Conservation), CC BY 4.0.</p>
        </div>`;
    const noRadarAnswer = bi == null || ai == null;
    return `
      ${[bi, ai, bo, ao].every(v => v == null) ? "" : `<div class="stats">
        <div class="card stat"><span>La Pampa, before</span><b>${f(bi)}</b><small>ha per month</small></div>
        <div class="card stat"><span>La Pampa, after</span><b>${f(ai)}</b><small>ha per month</small></div>
        <div class="card stat"><span>Elsewhere, before</span><b>${f(bo)}</b><small>ha per month</small></div>
        <div class="card stat"><span>Elsewhere, after</span><b>${f(ao)}</b><small>ha per month</small></div>
      </div>`}
      <div class="charts">${noRadarAnswer ? amwCard + radarCard : radarCard + amwCard}</div>`;
  }

  function accuracySection() {
    const acc = D.accuracy || { tables: [] };
    if (!acc.tables.length) return '<div class="card chart-card wide"><p>No accuracy scores yet. The model needs labels to be trained and graded: run <span class="mono">python -m tminus.labels</span>, then the pipeline again.</p></div>';
    const bar = (v, top) => (v == null ? '<span class="mono dim">n/a</span>' : `<span class="track wide ${top ? "best" : ""}"><i style="width:${(v * 100).toFixed(0)}%"></i></span><span class="mono">${v.toFixed(2)}</span>`);
    const first = acc.tables[0], rule = first.rows.find(r => r.name === "Rule only"), best = first.rows.find(r => r.best);
    const every = first.rows.find(r => r.name.startsWith("Either detector"));
    const p100 = v => Math.round(v * 100) + "%";
    const head = best && every && best.precision != null && every.precision != null
      ? `<h3 class="headline">High-confidence alerts are right ${p100(best.precision)} of the time but catch ${p100(best.recall)} of the mapped mining</h3>
         <p class="lede">Adding the medium-confidence alerts raises the share caught to ${p100(every.recall)}, and drops the share that is right to ${p100(every.precision)}. Check the high-confidence alerts first; treat the medium ones as leads.</p>`
      : rule && best && best !== rule && best.false_alarms < rule.false_alarms
        ? `<h3 class="headline">Requiring both detectors to agree cuts false alarms from ${num(rule.false_alarms)} to ${num(best.false_alarms)} ${first.unit}</h3>
         <p class="lede">The cost is ${best.misses > rule.misses ? `${num(best.misses - rule.misses)} more missed ${first.unit} than the rule alone` : "no extra misses"}. That is why alerts where only one detector fired stay on the map as medium confidence.</p>`
        : "";
    // one table: the first (held-out blocks, or the eye-checked points when that is all there is)
    return head + acc.tables.slice(0, 1).map(t => `
      <h3 class="table-title">${esc(t.title)}</h3>
      <p class="table-note">${esc(t.note)}</p>
      <div class="card table-wrap">
        <table>
          <thead><tr><th scope="col">Detector</th><th scope="col" class="num">Hits</th><th scope="col" class="num">Misses</th><th scope="col" class="num">False alarms</th><th scope="col">Precision</th><th scope="col">Recall</th></tr></thead>
          <tbody>${t.rows.map(m => `<tr class="${m.best ? "best" : ""}"><th scope="row">${esc(m.name)}</th><td class="num mono">${num(m.hits)}</td><td class="num mono">${num(m.misses)}</td><td class="num mono">${num(m.false_alarms)}</td><td><span class="cellbar">${bar(m.precision, m.best)}</span></td><td><span class="cellbar">${bar(m.recall, m.best)}</span></td></tr>`).join("")}</tbody>
        </table>
      </div>`).join("") + `
      <div class="explain">
        <div class="card"><h3>Precision</h3><p>Of everything we flagged, the share that was real mining: hits ÷ (hits + false alarms). High precision means rangers don't waste trips.</p></div>
        <div class="card"><h3>Recall</h3><p>Of the real mining, the share we caught: hits ÷ (hits + misses). Medium-confidence alerts stay visible so fewer sites slip through.</p></div>
      </div>`;
  }

  function analytics() {
    return `${header({ dates: true })}
    <main class="page">
      <p class="eyebrow">Analytics</p>
      <h1>${day(SCENES[state.before].date)} to ${day(SCENES[state.after].date)}</h1>
      <h2>Did the crackdown work?</h2>
      ${crackdownCard()}
      <h2>Accuracy check</h2>
      ${accuracySection()}
      ${sampleNote("Sample values until the pipeline has run.")}
    </main>
    ${footer()}`;
  }

  // ---------- reports ----------
  function reports() {
    const kinds = [
      ["csv", "CSV", "One row per alert, for spreadsheets and case files."],
      ["geojson", "GeoJSON", "Alert points with every attribute, for QGIS or ArcGIS."],
      ["kml", "KML", "Alert points to open in Google Earth or a phone map app."]
    ];
    return `${header({ dates: true })}
    <main class="page">
      <p class="eyebrow">Reports</p>
      <h1>Export the alerts</h1>
      <p class="lede">The ${num(pool().length)} alerts first seen between ${day(SCENES[state.before].date)} and ${day(SCENES[state.after].date)}, with priority, size, type, confidence, coordinates, a Google Maps link and the field status recorded on this device.</p>
      <div class="reports">
        ${kinds.map(([k, name, text]) => `<div class="card report"><h3>${name}</h3><p>${text}</p><button class="btn primary" data-export="${k}">${I.download} Download ${name}</button></div>`).join("")}
      </div>
    </main>
    ${footer()}`;
  }

  // ---------- exports ----------
  function exportAlerts(fmt, one) {
    const list = one ? [byId[one]] : pool();
    if (!list.length) return toast("There are no alerts between these two dates to export");
    const name = one ? byId[one].label.replace(/\s+/g, "_") : `alerts_${SCENES[state.after].date}`;
    const props = a => ({
      id: a.id, priority_rank: a.rank, priority: a.priority, type: TYPE[a.type].label, area_ha: a.area_ha,
      confidence: a.confidence, first_seen: a.first_seen, in_buffer: a.in_buffer, in_indigenous: a.in_indigenous,
      dist_road_m: a.dist_road_m, dist_river_m: a.dist_river_m,
      ...(MAPPED.amw ? { amazon_mining_watch_year: a.amw_year || null } : {}),
      lat: +a.lat.toFixed(5), lon: +a.lon.toFixed(5), field_status: STATUS[status[a.key] || ""], maps_url: mapsUrl(a)
    });
    let text, mime;
    if (fmt === "csv") {
      const rows = list.map(props), keys = Object.keys(rows[0]);
      const cell = v => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : v);
      text = [keys.join(","), ...rows.map(r => keys.map(k => cell(r[k])).join(","))].join("\n");
      mime = "text/csv";
    } else if (fmt === "geojson") {
      text = JSON.stringify({ type: "FeatureCollection", features: list.map(a => ({ type: "Feature", geometry: { type: "Point", coordinates: [+a.lon.toFixed(5), +a.lat.toFixed(5)] }, properties: props(a) })) }, null, 2);
      mime = "application/geo+json";
    } else {
      text = `<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>${esc(name)}</name>\n` +
        list.map(a => `<Placemark><name>${a.rank}. ${esc(a.label)}</name><description>${esc(`${TYPE[a.type].label}, ${a.area_ha} ha, ${a.confidence} confidence, priority ${a.priority}, first seen ${a.first_seen}.`)}</description><Point><coordinates>${a.lon.toFixed(5)},${a.lat.toFixed(5)},0</coordinates></Point></Placemark>`).join("\n") +
        "\n</Document></kml>\n";
      mime = "application/vnd.google-earth.kml+xml";
    }
    const url = URL.createObjectURL(new Blob([text], { type: mime }));
    const link = Object.assign(document.createElement("a"), { href: url, download: `${name}.${fmt}` });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(`${list.length} alert${list.length === 1 ? "" : "s"} exported as ${fmt.toUpperCase()}`);
  }

  let toastTimer;
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("on"), 2200);
  }
  function copy(text) {
    const fallback = () => {
      const ta = Object.assign(document.createElement("textarea"), { value: text });
      document.body.append(ta);
      ta.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { /* blocked */ }
      ta.remove();
      toast(ok ? "Coordinates copied" : "Couldn't copy. Select the coordinates and copy them by hand.");
    };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(() => toast("Coordinates copied"), fallback);
    else fallback();
  }

  // ---------- render ----------
  const ALIAS = { accuracy: "analytics", field: "detections" };
  function render() {
    const focus = document.activeElement && document.activeElement.id;
    const layersOpen = !!$("#layers[open]");
    state.route = ALIAS[state.route] || state.route;
    // an alert link opens that alert in the investigation screen
    if (state.route.startsWith("alert/")) {
      const id = state.route.slice(6);
      if (byId[id]) {
        state.selected = id;
        if (!filtered().includes(byId[id])) { state.filter = "all"; state.q = ""; }
        state.limit = Math.max(state.limit, Math.ceil((filtered().indexOf(byId[id]) + 1) / 40) * 40);
      }
      state.route = "detections";
    }
    const r = state.route;
    if (ro) { ro.disconnect(); ro = null; }
    let mount = null;
    if (r === "monitor") { app.innerHTML = monitor(); mount = mountMonitor; }
    else if (r === "detections") { app.innerHTML = detections(); mount = scrollToRow; }
    else if (r === "analytics") app.innerHTML = analytics();
    else if (r === "reports") app.innerHTML = reports();
    else { app.innerHTML = home(); mount = mountHome; }
    if (layersOpen && $("#layers")) $("#layers").open = true;
    if (mount) mount();
    paintChips();
    if (focus) {
      const el = document.getElementById(focus);
      if (el) {
        el.focus({ preventScroll: true });
        if (el.id === "search") el.setSelectionRange(el.value.length, el.value.length);
      }
    }
  }

  document.addEventListener("click", e => {
    const t = e.target.closest("[data-go],[data-openmap],[data-base],[data-filter],[data-select],[data-marker],[data-export],[data-copy],[data-zoom],[data-locate],[data-more]");
    if (!t) {
      $$("details[open]").forEach(d => { if (!d.contains(e.target)) d.open = false; });
      return;
    }
    const d = t.dataset;
    if (d.go) return go(d.go);
    if (d.openmap) {
      state.selected = d.openmap;
      focusOnMap = true;
      return go("monitor");
    }
    if (d.base) state.base = d.base;
    else if (d.filter) { state.filter = d.filter; state.limit = 40; }
    else if (d.select || d.marker) {
      const id = d.select || d.marker;
      if (d.marker && state.selected === id) return go("alert/" + id);
      state.selected = id;
      if (state.zoom > 1) { state.cx = byId[id].x; state.cy = byId[id].y; }
    }
    else if (d.export) return exportAlerts(d.export, d.one);
    else if (d.copy) return copy(d.copy);
    else if ("more" in d) state.limit += 40;
    else if (d.zoom && LEAF) return void (d.zoom > 0 ? lmap.zoomIn(1) : lmap.zoomOut(1));
    else if ("locate" in d && LEAF) return void (state.selected && lmap.setView([byId[state.selected].lat, byId[state.selected].lon], Math.max(lmap.getZoom(), 14)));
    else if (d.zoom) {
      const z = Math.min(12, state.zoom * (d.zoom > 0 ? 1.6 : 1 / 1.6));
      // leaving the full view: centre on the selected alert; coming back: reset
      if (d.zoom > 0 && state.zoom === 1 && state.selected) { state.cx = byId[state.selected].x; state.cy = byId[state.selected].y; }
      state.zoom = z < 1.05 ? 1 : z;
      if (state.zoom === 1) { state.cx = HOME.cx; state.cy = HOME.cy; }
    }
    else if ("locate" in d && state.selected) {
      if (state.zoom === 1) state.zoom = 1.6 * 1.6;
      state.cx = byId[state.selected].x;
      state.cy = byId[state.selected].y;
    }
    render();
  });
  document.addEventListener("change", e => {
    const t = e.target;
    if (t.id === "before" || t.id === "after") {
      state[t.id] = +t.value;
      // keep Before earlier than After
      if (state.before >= state.after) { if (t.id === "before") state.after = state.before + 1; else state.before = state.after - 1; }
      state.selected = null; state.filter = "all"; state.limit = 40;
      render();
    }
    else if (t.dataset.layer) { state.layers[t.dataset.layer] = t.checked; drawMap(); }
    else if (t.dataset.status != null) { setStatus(t.dataset.status, t.value); toast("Field status saved on this device"); render(); }
  });
  document.addEventListener("input", e => {
    if (e.target.id === "search") { state.q = e.target.value; state.limit = 40; render(); }
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") $$("details[open]").forEach(d => { d.open = false; $("summary", d).focus(); });
  });

  // Real scenes are images: wait for them, so the first paint is complete.
  const urls = REAL ? SCENES.map(s => s.img).concat(D.overlay, D.overlay_main).filter(Boolean) : [];
  if (urls.length) app.innerHTML = '<p class="loading">Loading the radar scenes…</p>';
  Promise.all(urls.map(Scene.load)).then(() => {
    render();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (state.route === "monitor") drawMap(); });
  });
})();
