// Draws the map. With real results it paints the pipeline's scene images;
// without them it draws an illustrative scene (a 1000 x 860 world, 20 m per unit).
// A view is {cx, cy, span}: centre and width in world units, so the same code
// serves the map, chips and thumbnails.
window.Scene = (() => {
  "use strict";
  const W = 1000, H = 860;
  const HIGH = "#ff3b3b", MEDIUM = "#ffb020";

  const rng = seed => () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  const hash = s => {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    return h >>> 0;
  };
  const riverY = x => 205 + 40 * Math.sin(x / 110) + 15 * Math.sin(x / 47);

  function begin(canvas, view) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(1, Math.round(canvas.clientWidth * dpr));
    const h = Math.max(1, Math.round(canvas.clientHeight * dpr));
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
    ctx.clearRect(0, 0, w, h);
    const k = w / view.span;
    const m = [k, 0, 0, k, w / 2 - view.cx * k, h / 2 - view.cy * k];
    ctx.setTransform(...m);
    return { ctx, k, w, h, dpr, m };
  }

  const lobeCache = {};
  function lobes(site) {
    if (lobeCache[site.id]) return lobeCache[site.id];
    const r = rng(hash(site.id));
    const r0 = 15 + Math.sqrt(site.area_ha) * 5.6;
    const n = 4 + Math.round(site.area_ha / 3);
    const out = [];
    for (let i = 0; i < n; i++) {
      const a = r() * Math.PI * 2, d = r() * r0 * 0.62;
      out.push({ x: site.x + Math.cos(a) * d, y: site.y + Math.sin(a) * d * 0.85, r: r0 * (0.34 + r() * 0.26), s: r() });
    }
    return (lobeCache[site.id] = out);
  }

  function circles(ctx, list, grow, scale) {
    ctx.beginPath();
    for (const c of list) {
      ctx.moveTo(c.x + c.r * scale + grow, c.y);
      ctx.arc(c.x, c.y, c.r * scale + grow, 0, Math.PI * 2);
    }
  }

  function riverPath(ctx) {
    ctx.beginPath();
    for (let x = -2000; x <= W + 2000; x += 10) ctx.lineTo(x, riverY(x));
  }
  function tributaryPath(ctx) {
    ctx.beginPath();
    ctx.moveTo(372, riverY(372));
    ctx.bezierCurveTo(385, 420, 470, 560, 650, 900);
    ctx.bezierCurveTo(740, 1070, 800, 1300, 820, 1700);
  }

  const tiles = {};
  function speckle(seed) {
    if (tiles[seed]) return tiles[seed];
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const x = c.getContext("2d"), img = x.createImageData(256, 256), r = rng(seed * 7919 + 1);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = 128 + (r() + r() - 1) * 92;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
    x.putImageData(img, 0, 0);
    return (tiles[seed] = c);
  }

  const mottle = (() => {
    const r = rng(42), out = [];
    for (let i = 0; i < 70; i++) out.push({ x: r() * W * 3 - W, y: r() * H * 1.6 - H * 0.3, r: 60 + r() * 160, dark: r() < 0.5, a: 0.05 + r() * 0.08 });
    return out;
  })();

  const images = {};
  // Resolves once the image can be drawn. Failed loads resolve to null.
  function load(url) {
    if (!images[url]) {
      images[url] = new Promise(done => {
        const img = new Image();
        img.onload = () => done((images[url].img = img));
        img.onerror = () => done(null);
        img.src = url;
      });
    }
    return images[url];
  }
  const loaded = url => (url && images[url] && images[url].img) || null;

  // Circles around alerts: [{x, y, r, confidence}] in world units.
  function rings(ctx, k, dpr, list, width) {
    ctx.lineWidth = (width * dpr) / k;
    for (const c of list) {
      ctx.strokeStyle = c.confidence === "high" ? HIGH : MEDIUM;
      ctx.beginPath();
      ctx.arc(c.x, c.y, c.r, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  // opts.img (a scene image url) and opts.world {w, h} paint a real scene, with
  // opts.overlay on top. Otherwise the illustrative scene is drawn: sites is
  // everything mined by this date, outlined the alerts to trace.
  function radar(canvas, view, sites, outlined, opts) {
    opts = opts || {};
    const { ctx, k, w, h, dpr, m } = begin(canvas, view);
    if (opts.world) {
      ctx.fillStyle = "#1e1e1e";
      ctx.fillRect(view.cx - view.span, view.cy - view.span, view.span * 2, view.span * 2);
      const img = loaded(opts.img), over = loaded(opts.overlay);
      ctx.imageSmoothingEnabled = k < 3;   // show the real pixels once zoomed well in
      if (img) ctx.drawImage(img, 0, 0, opts.world.w, opts.world.h);
      if (over) ctx.drawImage(over, 0, 0, opts.world.w, opts.world.h);
      if (opts.rings) rings(ctx, k, dpr, opts.rings, opts.ring || 2.5);
      return;
    }
    const x0 = view.cx - view.span, y0 = view.cy - view.span, big = view.span * 2;  // covers any aspect up to 2:1

    ctx.fillStyle = "#8c8c8c";
    ctx.fillRect(x0, y0, big, big);
    for (const b of mottle) {
      const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
      g.addColorStop(0, b.dark ? `rgba(40,40,40,${b.a})` : `rgba(220,220,220,${b.a})`);
      g.addColorStop(1, "rgba(128,128,128,0)");
      ctx.fillStyle = g;
      ctx.fillRect(b.x - b.r, b.y - b.r, b.r * 2, b.r * 2);
    }

    ctx.lineCap = ctx.lineJoin = "round";
    ctx.strokeStyle = "#0b0b0b";
    riverPath(ctx); ctx.lineWidth = 11; ctx.stroke();
    tributaryPath(ctx); ctx.lineWidth = 6; ctx.stroke();
    ctx.lineWidth = 3;
    for (const [ox, oy, rx, ry] of [[455, 138, 24, 8], [868, 262, 22, 9], [78, 250, 18, 7]]) {
      ctx.beginPath(); ctx.ellipse(ox, oy, rx, ry, 0.1, 0, Math.PI * 2); ctx.stroke();
    }

    for (const s of sites) {
      const L = lobes(s);
      ctx.fillStyle = s.type === "bare" ? "#4b4b4b" : s.type === "clearing" ? "#585858" : "#666";
      circles(ctx, L, 0, 1); ctx.fill();
      ctx.fillStyle = "#070707";
      if (s.type === "pond") {
        circles(ctx, L, 0, 0.58); ctx.fill();
      } else if (s.type === "bare") {
        circles(ctx, L.filter(c => c.s < 0.4), 0, 0.4); ctx.fill();
      } else {
        ctx.fillStyle = "#3d3d3d";
        circles(ctx, L.filter(c => c.s < 0.5), 0, 0.6); ctx.fill();
      }
    }

    // speckle in device pixels, so the grain is the same at every zoom
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    const pat = ctx.createPattern(speckle(opts.seed || 1), "repeat");
    if (pat.setTransform) pat.setTransform(new DOMMatrix().scale(dpr * 1.4));
    ctx.globalCompositeOperation = "overlay";
    ctx.fillStyle = pat;
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "source-over";
    ctx.setTransform(...m);

    if (outlined && outlined.length) {
      // Stroke every lobe, then cut the insides out: what is left is the outer ring.
      const off = document.createElement("canvas");
      off.width = w; off.height = h;
      const o = off.getContext("2d");
      o.setTransform(...m);
      const pad = 3, t = ((opts.ring || 2.5) * dpr) / k;
      for (const s of outlined) {
        const L = lobes(s);
        o.globalCompositeOperation = "source-over";
        o.strokeStyle = s.confidence === "high" ? HIGH : MEDIUM;
        o.lineWidth = t * 2;
        circles(o, L, pad, 1); o.stroke();
        o.globalCompositeOperation = "destination-out";
        circles(o, L, pad, 1); o.fill();
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(off, 0, 0);
    }
  }

  function reservePath(ctx) {
    ctx.beginPath();
    ctx.moveTo(-2000, 700);
    ctx.lineTo(-200, 760);
    ctx.bezierCurveTo(250, 790, 420, 850, 620, 838);
    ctx.bezierCurveTo(800, 826, 900, 790, 1200, 800);
    ctx.lineTo(3000, 830);
  }

  // box is the La Pampa outline [x0, y0, x1, y1] in world units for real results.
  function zones(canvas, view, on, box) {
    const { ctx, k, dpr } = begin(canvas, view);
    if (!on) return;
    const px = dpr / k;
    ctx.lineWidth = 1.5 * px;
    if (box) {
      ctx.setLineDash([6 * px, 5 * px]);
      ctx.strokeStyle = "rgba(255,255,255,.85)";
      ctx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
      ctx.setLineDash([]);
      return;
    }
    ctx.setLineDash([2 * px, 4 * px]);
    ctx.strokeStyle = "#4ec5ae";
    reservePath(ctx); ctx.stroke();
    ctx.setLineDash([6 * px, 5 * px]);
    ctx.strokeStyle = "rgba(255,255,255,.75)";
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(110, 575, 330, 195, 26); else ctx.rect(110, 575, 330, 195);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // The same place through cloud: what Sentinel-2 sees.
  function optical(canvas, view, sites) {
    const { ctx } = begin(canvas, view);
    const r = rng(7);
    ctx.fillStyle = "#1e5631";
    ctx.fillRect(-W, -H, W * 3, H * 3);
    for (let i = 0; i < 60; i++) {
      const x = r() * W, y = r() * H, rad = 30 + r() * 90;
      const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
      g.addColorStop(0, r() < 0.5 ? "rgba(12,58,30,.55)" : "rgba(52,120,62,.4)");
      g.addColorStop(1, "rgba(30,86,49,0)");
      ctx.fillStyle = g;
      ctx.fillRect(x - rad, y - rad, rad * 2, rad * 2);
    }
    ctx.lineCap = "round";
    ctx.strokeStyle = "#b38f5e";
    riverPath(ctx); ctx.lineWidth = 6; ctx.stroke();
    tributaryPath(ctx); ctx.lineWidth = 2.5; ctx.stroke();
    for (const s of sites) {
      const L = lobes(s);
      ctx.fillStyle = "#cdaa72";
      circles(ctx, L, 2, 1); ctx.fill();
      if (s.type === "pond") { ctx.fillStyle = "#4fb5a8"; circles(ctx, L, 0, 0.55); ctx.fill(); }
    }
    for (let i = 0; i < 62; i++) {
      const x = r() * W, y = r() * H, rad = 50 + r() * 130;
      if (Math.hypot(x - 300, y - 690) < 150 || Math.hypot(x - 700, y - 300) < 110) continue;
      const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
      g.addColorStop(0, "rgba(255,255,255,.95)");
      g.addColorStop(0.55, "rgba(246,248,248,.7)");
      g.addColorStop(1, "rgba(240,244,244,0)");
      ctx.fillStyle = g;
      ctx.fillRect(x - rad, y - rad, rad * 2, rad * 2);
    }
  }

  return { W, H, load, radar, zones, optical };
})();
