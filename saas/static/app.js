/* graphify workspace frontend — vanilla JS, no build step, no CDN deps.
   Canvas renderer is hand-rolled so the product works offline and inside an IDE
   webview; credentials ride in Authorization (not cookies) so the app also works
   in a cross-site iframe. */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const el = (t, c, h) => { const n = document.createElement(t); if (c) n.className = c; if (h != null) n.innerHTML = h; return n; };
  const nf = new Intl.NumberFormat("fr-FR");
  const cn = (n) => (n >= 1e6 ? (n / 1e6).toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + " M" : n >= 1e3 ? (n / 1e3).toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + " K" : String(n));
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const ago = (ts) => { if (!ts) return "jamais"; const d = Date.now() / 1000 - ts; if (d < 60) return "à l'instant"; if (d < 3600) return `il y a ${Math.floor(d / 60)} min`; if (d < 86400) return `il y a ${Math.floor(d / 3600)} h`; return `il y a ${Math.floor(d / 86400)} j`; };

  const LS = { token: "graphify.token", ws: "graphify.ws", theme: "graphify.theme" };
  const S = { theme: null, pal: null, stats: null, comms: [], view: "overview", ide: "vscode", me: null, ws: null, authMode: "login", seenBuilds: {} };

  // ------------------------------------------------------------------- api
  async function api(path, params, opts = {}) {
    const u = new URL(path, location.origin);
    if (params) Object.entries(params).forEach(([k, v]) => v != null && v !== "" && u.searchParams.set(k, v));
    const headers = Object.assign({}, opts.headers);
    const token = GStore.get(LS.token);
    if (token) {
      headers["Authorization"] = "Bearer " + token;
      // Belt and braces: some embedded-preview proxies strip Authorization and
      // the iframe blocks third-party cookies, so the query param is the one
      // channel guaranteed to arrive. Server reads it only under /api/*.
      u.searchParams.set("token", token);
    }
    if (opts.ws) headers["X-Workspace"] = opts.ws; else if (S.ws) headers["X-Workspace"] = S.ws;
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    const r = await fetch(u, { method: opts.method || "GET", headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined });
    let data = null;
    try { data = await r.json(); } catch {}
    if (r.status === 401 && !path.startsWith("/api/auth/")) { gate(); throw new Error((data && data.error) || "unauthenticated"); }
    if (!r.ok) throw new Error((data && data.error) || "HTTP " + r.status);
    return data;
  }
  const toast = (msg) => { const t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("on"), 2100); };
  const confPill = (c) => c ? `<span class="pill ${c === "EXTRACTED" ? "ex" : c === "INFERRED" ? "in" : "am"}">${c[0]}</span>` : "";

  // ----------------------------------------------------------------- theme
  function applyTheme(id) {
    document.documentElement.dataset.theme = id;
    const p = S.theme.themes.find((t) => t.id === id) || S.theme.themes[0];
    S.pal = p;
    GStore.set(LS.theme, id);
    $$("#themes .sw").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === id)));
    graph.draw();
    if (S.stats) paintOverviewBars();
  }
  function buildThemeSwitcher() {
    const wrap = $("#themes"); wrap.innerHTML = "";
    S.theme.themes.forEach((t) => {
      const b = el("button", "sw");
      b.dataset.id = t.id; b.title = t.name;
      b.style.background = `linear-gradient(135deg, ${t.accent} 0 52%, ${t.bg} 52% 100%)`;
      b.onclick = () => applyTheme(t.id);
      wrap.appendChild(b);
    });
  }
  const comColor = (c) => S.pal.series[((c ?? 0) % S.pal.series.length + S.pal.series.length) % S.pal.series.length];

  // ---------------------------------------------------------------- auth
    // Auth is a real page (/login), not an overlay: an unauthenticated or
    // expired session bounces there and comes back to /app with the token set.
  function gate() {
    GStore.del(LS.token);
    location.replace("/login?next=/app&bounce=1");
  }
  function bindGate() {
    $("#btn-out").onclick = async () => {
      try { await api("/api/auth/logout", null, { method: "POST" }); } catch {}
      GStore.del(LS.token); GStore.del(LS.ws);
      location.href = "/login";
    };
  }

  // ------------------------------------------------------------- navigation
  function show(view) {
    S.view = view;
    $$("#nav button[data-view]").forEach((b) => b.classList.toggle("on", b.dataset.view === view));
    $$(".view").forEach((v) => v.classList.toggle("on", v.id === "v-" + view));
    if (view === "graph") { graph.resize(); if (!graph.data) loadGraph(); }
    if (view === "ide") loadIde();
    if (view === "account") loadAccount();
    if (view === "billing") loadBilling();
    if (view === "team") loadTeam();
    if (view === "builds") loadBuilds();
    if (view === "report") loadReport();
  }

  function bindWorkspaceSwitcher(list, active) {
    const sel = $("#ws");
    sel.innerHTML = list.map((w) => `<option value="${esc(w.id)}">${esc(w.name)}</option>`).join("")
      || `<option>no workspace</option>`;
    sel.value = active || "";
    sel.disabled = list.length < 2;
    sel.onchange = async () => {
      S.ws = sel.value; GStore.set(LS.ws, S.ws);
      sel.disabled = true;
      await enter();
    };
  }

  // -------------------------------------------------------------- overview
  let lastStats = null;
  async function loadOverview() {
    const st = S.stats; lastStats = st;
    $("#proj-meta").textContent = st.nodes != null ? `· ${nf.format(st.nodes)} nœuds / ${nf.format(st.edges)} arêtes` : "";
    $("#k-comm").textContent = st.communities != null ? nf.format(st.communities) : "";
    $("#nav-foot").innerHTML = `<b>${esc((S.me && S.me.email) || "")}</b><br>${nf.format(st.nodes || 0)} nœuds · ${nf.format(st.edges || 0)} arêtes<br>${nf.format(st.files || 0)} fichiers · ${st.communities || 0} communautés${st.built_at_commit ? `<br>commit <code>${esc(String(st.built_at_commit).slice(0, 7))}</code>` : ""}`;

    const cards = [
      ["Nœuds", st.nodes, `${nf.format(st.files || 0)} fichiers sources`],
      ["Arêtes", st.edges, `degré moyen ${st.avg_degree ?? "–"}`],
      ["Communautés", st.communities, "clustering de Leiden"],
      ["Extraction locale", "0", "crédits LLM dépensés"],
    ];
    $("#ov-stats").innerHTML = cards.map(([l, v, h]) =>
      `<div class="card stat"><div class="v">${typeof v === "number" ? nf.format(v) : (v ?? "–")}</div><div class="l">${l}</div><div class="h">${esc(h)}</div></div>`).join("");

    paintOverviewBars();

    const gods = (await api("/api/god-nodes", { limit: 12 })).nodes;
    $("#ov-gods").innerHTML = gods.map(godRow).join("");
    bindItems($("#ov-gods"));
    loadDashboard().catch(() => {});
  }

  // ---------------------------------------------------- dashboard (aperçu)
  const hash01 = (s) => {
    let h = 2166136261;
    for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
    return (h >>> 0) / 4294967295;
  };

  function drawThumb(cv, r) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = cv.clientWidth || 250, h = cv.clientHeight || 118;
    cv.width = w * dpr; cv.height = h * dpr;
    const ctx = cv.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const cs = getComputedStyle(document.documentElement);
    const nodes = r.nodes.map((n) => {
      const a = hash01(n.id) * Math.PI * 2, b = hash01(n.id + "#b") * Math.PI * 2;
      const rr = 10 + hash01(n.id + "#r") * (Math.min(w, h) / 2 - 14);
      return { ...n, x: w / 2 + Math.cos(a) * rr * (w / h) * 0.85, y: h / 2 + Math.sin(b) * rr * 0.85 };
    });
    const byId = new Map(nodes.map((n) => [n.id, n]));
    ctx.strokeStyle = cs.getPropertyValue("--border").trim(); ctx.globalAlpha = .45; ctx.lineWidth = .7;
    r.links.forEach((l) => {
      const a = byId.get(l.source), b = byId.get(l.target); if (!a || !b) return;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    });
    ctx.fillStyle = cs.getPropertyValue("--text").trim();
    nodes.forEach((n) => {
      ctx.globalAlpha = .3 + Math.min(.65, (n.degree || 1) / 80);
      ctx.beginPath(); ctx.arc(n.x, n.y, 1 + Math.min(2.2, (n.degree || 1) / 45), 0, 6.2832); ctx.fill();
    });
    ctx.globalAlpha = 1;
  }

  function paintCols(sel, axisSel, daily, key) {
    const max = Math.max(...daily.map((d) => d[key]), 1);
    $(sel).innerHTML = daily.map((d) =>
      `<div class="col ${d[key] ? "" : "zero"}" style="height:${Math.max(3, (d[key] / max) * 100)}%" title="${d.day} · ${d[key]}"></div>`).join("");
    const lbl = (day) => new Date(day + "T00:00:00Z").toLocaleDateString("fr-FR", { day: "numeric", month: "short", timeZone: "UTC" });
    const f = daily[0], m = daily[Math.floor(daily.length / 2)], l = daily[daily.length - 1];
    $(axisSel).innerHTML = `<span>${lbl(f.day)}</span><span>${lbl(m.day)}</span><span>${lbl(l.day)}</span>`;
  }

  async function loadDashboard() {
    const wl = await api("/api/workspaces");
    const wss = wl.workspaces; S.workspaces = wss;
    $("#dv-count").textContent = wss.length;

    const row = $("#dv-repos");
    row.innerHTML = wss.map((w) => `<div class="repo-card ${w.id === S.ws ? "active" : ""}" data-ws="${esc(w.id)}">
        <div class="thumb"><canvas></canvas><span class="badge ok">✓ Indexé</span></div>
        <div class="rc-body"><div class="rc-name">${esc(w.name)}</div>
        <div class="rc-meta">${w.nodes != null ? `${cn(w.nodes)} nœuds · ${cn(w.edges || 0)} arêtes` : "graphe manquant"} · plan ${esc(w.plan || "free")}</div></div>
      </div>`).join("") || `<p class="empty">Aucun workspace indexé pour l'instant.</p>`;
    $$(".repo-card", row).forEach((c) => {
      c.onclick = async () => {
        if (c.dataset.ws === S.ws) return;
        S.ws = c.dataset.ws; GStore.set(LS.ws, S.ws); await enter();
      };
    });
    await Promise.all($$(".repo-card", row).map(async (c) => {
      try {
        const r = await api("/api/graph", { mode: "top", limit: 110 }, { ws: c.dataset.ws });
        drawThumb(c.querySelector("canvas"), r);
      } catch {}
    }));

    try {
      const u = await api("/api/usage");
      const totalNodes = wss.reduce((a, w) => a + (w.nodes || 0), 0);
      const indexed = wss.filter((w) => w.nodes != null).length;
      const quota = u.plan.max_api_calls_month > 0
        ? Math.max(0, 100 - Math.round((u.usage.api_calls / u.plan.max_api_calls_month) * 100)) : 100;
      $("#dv-badges").innerHTML = `
        <span class="bdg">⚯ ${indexed} / ${wss.length} indexés</span>
        <span class="bdg">❋ ${cn(totalNodes)} nœuds</span>
        <span class="bdg ok">✓ ${quota} % de quota API restant</span>`;
      paintCols("#dv-chart-api", "#dv-axis-api", u.daily, "api");
      paintCols("#dv-chart-mcp", "#dv-axis-mcp", u.daily, "mcp");
      const s7 = (k) => u.daily.reduce((a, d) => a + d[k], 0);
      $("#dv-d-api").textContent = `↑ ${cn(s7("api"))} · 7 j`;
      $("#dv-d-mcp").textContent = `↑ ${cn(s7("mcp"))} · 7 j`;
      $("#dv-activity").innerHTML = `
        <div class="act-row good"><span class="ic">✓</span> Appels API réussis <span class="n">${nf.format(u.usage.api_calls)}</span></div>
        <div class="act-row"><span class="ic">⚯</span> Appels MCP <span class="n">${nf.format(u.usage.mcp_calls)}</span></div>
        <div class="act-row"><span class="ic">⬆</span> Téléversements <span class="n">${u.usage.uploads}</span></div>
        <div class="act-row"><span class="ic">◍</span> Données reçues <span class="n">${(u.usage.uploaded_bytes / 1048576).toFixed(1)} Mo</span></div>`;
    } catch { $("#dv-badges").innerHTML = ""; }

    $("#dv-density").innerHTML = [...wss].sort((a, b) => (b.nodes || 0) - (a.nodes || 0)).map((w) => `
      <div class="item" data-ws="${esc(w.id)}">
        <span class="swatch" style="background:${w.id === S.ws ? "var(--accent)" : "var(--border)"}"></span>
        <span class="nm">${esc(w.name)}</span>
        <span class="rt"><span class="num">${cn(w.nodes || 0)}</span></span>
      </div>`).join("");
    $$("#dv-density .item").forEach((it) => {
      it.onclick = async () => { S.ws = it.dataset.ws; GStore.set(LS.ws, S.ws); await enter(); };
    });
  }

  async function loadCombined() {
    const wss = S.workspaces && S.workspaces.length ? S.workspaces : (await api("/api/workspaces")).workspaces;
    if (!wss.length) return toast("Aucun workspace à combiner");
    // Seed an (empty) payload so show("graph") doesn't fire its own loadGraph()
    // that would race — and possibly win against — the merged slice below.
    graph.setData({ nodes: [], links: [] });
    show("graph");
    $("#g-stat").innerHTML = `<span class="spin"></span> combinaison…`;
    const parts = await Promise.all(wss.map(async (w) => {
      try { return [w, await api("/api/graph", { mode: "top", limit: 120 }, { ws: w.id })]; }
      catch { return [w, null]; }
    }));
    const nodes = [], links = [];
    parts.forEach(([w, r], i) => {
      if (!r) return;
      r.nodes.forEach((n) => nodes.push({ ...n, id: w.slug + ":" + n.id, community: i }));
      const ids = new Set(r.nodes.map((n) => n.id));
      r.links.forEach((l) => {
        if (ids.has(l.source) && ids.has(l.target))
          links.push({ source: w.slug + ":" + l.source, target: w.slug + ":" + l.target, relation: l.relation, confidence: l.confidence });
      });
    });
    const merged = { nodes, links };
    graph.setData(merged);
    $("#g-stat").textContent = `graphique combiné · ${nf.format(nodes.length)} nœuds · ${nf.format(links.length)} arêtes · ${wss.length} workspaces`;
    $("#glegend").innerHTML = `<h2 style="margin-bottom:6px">Workspaces</h2>` + parts.filter((x) => x[1]).map(([w], i) =>
      `<div class="li"><span class="d" style="background:${comColor(i)}"></span><span>${esc(w.name)}</span><span class="c">${w.nodes != null ? cn(w.nodes) : ""}</span></div>`).join("");
  }

  function paintOverviewBars() {
    const st = lastStats; if (!st) return;
    const maxRel = Math.max(...st.relations.map((r) => r[1]), 1);
    $("#ov-rel").innerHTML = st.relations.map(([r, n], i) =>
      `<div class="bar-row"><span class="nm">${esc(r)}</span><span class="track"><span class="fill" style="width:${(n / maxRel * 100).toFixed(1)}%;background:${S.pal.series[i % S.pal.series.length]}"></span></span><span class="n">${nf.format(n)}</span></div>`).join("");

    const conf = st.confidence || {};
    const confTot = Math.max(Object.values(conf).reduce((a, b) => a + b, 0), 1);
    $("#ov-conf").innerHTML = Object.entries(conf).map(([k, n]) => {
      const col = k === "EXTRACTED" ? "var(--ok)" : k === "INFERRED" ? "var(--warn)" : "var(--danger)";
      return `<div class="bar-row"><span class="nm">${esc(k)}</span><span class="track"><span class="fill" style="width:${(n / confTot * 100).toFixed(1)}%;background:${col}"></span></span><span class="n">${(n / confTot * 100).toFixed(1)}%</span></div>`;
    }).join("") || `<p class="empty">pas encore d'arêtes</p>`;

    const files = st.top_files || [];
    const maxF = files.length ? files[0][1] : 1;
    $("#ov-files").innerHTML = files.map(([f, n]) =>
      `<div class="bar-row"><span class="nm" title="${esc(f)}">${esc(String(f || "").split("/").pop())}</span><span class="track"><span class="fill" style="width:${(n / maxF * 100).toFixed(1)}%"></span></span><span class="n">${n}</span></div>`).join("");
  }

  const godRow = (g) => `<div class="item" data-node="${esc(g.id)}">
      <span class="swatch" style="background:${comColor(g.community)}"></span>
      <span style="min-width:0"><span class="nm">${esc(g.label)}</span><br><span class="mt">${esc(g.source_file || "")}${g.source_location ? " · " + esc(g.source_location) : ""}</span></span>
      <span class="rt"><span class="num">${nf.format(g.degree)}</span><br><span class="mt">degré</span></span>
    </div>`;

  function bindItems(root) { $$(".item[data-node]", root).forEach((it) => { it.onclick = () => openNode(it.dataset.node); }); }

  async function openNode(idOrLabel) {
    try {
      const r = await api("/api/explain", { node: idOrLabel });
      show("graph");
      await graph.focus(r.node.id);
      inspector(r.node);
    } catch (e) { toast("Introuvable : " + e.message); }
  }

  async function loadGods() {
    const gods = (await api("/api/god-nodes", { limit: 40 })).nodes;
    $("#gn-list").innerHTML = gods.map(godRow).join("");
    bindItems($("#gn-list"));
  }

  async function loadComms() {
    const cs = (await api("/api/communities", { limit: 30 })).communities;
    S.comms = cs;
    $("#g-comm").innerHTML = cs.map((c) => `<option value="${c.id}">#${c.id} · ${esc(c.hub)} (${c.size})</option>`).join("");
    $("#cm-list").innerHTML = cs.map((c) => `<div class="card item" data-comm="${c.id}" style="align-items:flex-start">
        <span class="swatch" style="background:${comColor(c.id)};margin-top:5px"></span>
        <span style="min-width:0">
          <span class="nm">#${c.id} · ${esc(c.hub)}</span><br>
          <span class="mt">${esc(c.sample.slice(0, 5).join(", "))}</span><br>
          <span class="mt">${c.relations.map(([r, n]) => `${esc(r)} ${n}`).join(" · ")}</span>
        </span>
        <span class="rt"><span class="num">${nf.format(c.size)}</span><br><span class="mt">nœuds</span></span>
      </div>`).join("");
    $$("#cm-list .item").forEach((it) => {
      it.onclick = () => { show("graph"); $("#g-mode").value = "community"; syncMode(); loadGraph(); };
    });
  }

  // ------------------------------------------------------------ graph view
  function syncMode() {
    const m = $("#g-mode").value;
    $("#g-node").style.display = m === "focus" ? "" : "none";
    $("#g-comm").style.display = m === "community" ? "" : "none";
  }

  async function loadGraph() {
    const mode = $("#g-mode").value;
    const limit = +$("#g-limit").value;
    $("#g-stat").innerHTML = `<span class="spin"></span> découpage…`;
    try {
      const r = await api("/api/graph", {
        mode, limit,
        node: mode === "focus" ? $("#g-node").value : null,
        community: mode === "community" ? $("#g-comm").value : null,
        depth: 1,
      });
      graph.setData(r);
      $("#g-stat").textContent = `${nf.format(r.nodes.length)} nœuds · ${nf.format(r.links.length)} arêtes affichés`;
      legend(r);
    } catch (e) { $("#g-stat").textContent = "erreur : " + e.message; }
  }

  function legend(r) {
    const counts = new Map();
    r.nodes.forEach((n) => counts.set(n.community, (counts.get(n.community) || 0) + 1));
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12);
    $("#glegend").innerHTML = `<h2 style="margin-bottom:6px">Communautés</h2>` + top.map(([c, n]) =>
      `<div class="li" data-comm="${c}"><span class="d" style="background:${comColor(c)}"></span>
       <span>#${c}</span><span class="c">${n}</span></div>`).join("");
    $$("#glegend .li").forEach((li) => {
      li.onclick = () => { $("#g-mode").value = "community"; syncMode(); $("#g-comm").value = li.dataset.comm; loadGraph(); };
    });
  }

  function inspector(n) {
    const box = $("#inspector");
    box.classList.add("on");
    box.innerHTML = `<div style="display:flex;gap:8px;align-items:flex-start">
        <span class="swatch" style="background:${comColor(n.community)};margin-top:6px"></span>
        <div style="min-width:0;flex:1"><div class="ttl">${esc(n.label)}</div>
        <div class="kv"><span>degré</span><b>${nf.format(n.degree)}</b><span>· communauté</span><b>#${n.community ?? "–"}</b></div>
        <div class="kv"><span>${esc(n.source_file || "no file")}${n.source_location ? " " + esc(n.source_location) : ""}</span></div></div>
        <button class="btn sm" id="ins-close">✕</button></div>
      <h2 style="margin:14px 0 6px">Connexions · ${nf.format(n.connection_count)}</h2>
      <div id="ins-conns"></div>`;
    $("#ins-close").onclick = () => box.classList.remove("on");
    const wrap = $("#ins-conns");
    n.connections.forEach((c) => {
      const row = el("div", "conn");
      row.style.borderLeftColor = comColor(c.community);
      row.innerHTML = `<span style="color:var(--faint)">${c.direction === "out" ? "→" : "←"}</span>
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.label)}</span>
        <span class="rel">${esc(c.relation)}</span>${confPill(c.confidence)}`;
      row.onclick = () => openNode(c.id);
      wrap.appendChild(row);
    });
    graph.select(n.id);
  }

  // ------------------------------------------------------- canvas + physics
  const graph = (() => {
    const cv = $("#canvas"), ctx = cv.getContext("2d");
    let nodes = [], links = [], byId = new Map(), adj = new Map();
    let scale = 1, tx = 0, ty = 0, alpha = 1, w = 0, h = 0, raf = null;
    let hover = null, selected = null, dragging = null, panning = false, last = null, moved = 0;
    let data = null;

    function resize() {
      const r = cv.parentElement.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = Math.max(1, r.width); h = Math.max(1, r.height);
      cv.width = w * dpr; cv.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }

    function setData(d) {
      data = d;
      byId = new Map(); adj = new Map();
      const R = Math.min(w || 800, h || 600) * 0.42;
      nodes = d.nodes.map((n, i) => {
        const a = (i / Math.max(1, d.nodes.length)) * Math.PI * 2;
        const o = { ...n, x: Math.cos(a) * R * (0.4 + Math.random() * 0.6), y: Math.sin(a) * R * (0.4 + Math.random() * 0.6), vx: 0, vy: 0 };
        byId.set(o.id, o); adj.set(o.id, new Set()); return o;
      });
      links = [];
      d.links.forEach((l) => {
        const s = byId.get(l.source), t = byId.get(l.target);
        if (!s || !t || s === t) return;
        links.push({ s, t, relation: l.relation, confidence: l.confidence });
        adj.get(s.id).add(t.id); adj.get(t.id).add(s.id);
      });
      alpha = 1; scale = 1; tx = 0; ty = 0; selected = null; hover = null;
      $("#inspector").classList.remove("on");
      fit(); loop();
    }

    function fit() {
      if (!nodes.length) return;
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      nodes.forEach((n) => { x0 = Math.min(x0, n.x); y0 = Math.min(y0, n.y); x1 = Math.max(x1, n.x); y1 = Math.max(y1, n.y); });
      const bw = Math.max(1, x1 - x0), bh = Math.max(1, y1 - y0);
      scale = Math.min(3, 0.86 * Math.min(w / bw, h / bh));
      tx = w / 2 - scale * (x0 + bw / 2); ty = h / 2 - scale * (y0 + bh / 2);
      draw();
    }

    function tick() {
      const n = nodes.length;
      if (!n) return;
      const rep = 2600, rest = 62, k = 0.035, damp = 0.86;
      for (let i = 0; i < n; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < n; j++) {
          const b = nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
          if (d2 < 0.01) { dx = (Math.random() - .5) * 2; dy = (Math.random() - .5) * 2; d2 = 4; }
          if (d2 > 90000) continue;
          const f = (rep * alpha) / d2, d = Math.sqrt(d2);
          const fx = (dx / d) * f, fy = (dy / d) * f;
          a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
        }
      }
      for (const l of links) {
        const dx = l.t.x - l.s.x, dy = l.t.y - l.s.y, d = Math.max(1, Math.hypot(dx, dy));
        const f = (d - rest) * k * alpha, fx = (dx / d) * f, fy = (dy / d) * f;
        l.s.vx += fx; l.s.vy += fy; l.t.vx -= fx; l.t.vy -= fy;
      }
      for (const o of nodes) {
        o.vx -= o.x * 0.0022 * alpha; o.vy -= o.y * 0.0022 * alpha;
        if (o === dragging) { o.vx = 0; o.vy = 0; continue; }
        o.vx *= damp; o.vy *= damp;
        o.x += Math.max(-14, Math.min(14, o.vx)); o.y += Math.max(-14, Math.min(14, o.vy));
      }
      alpha *= 0.988; if (alpha < 0.02) alpha = 0.02;
    }

    function draw() {
      if (!w || !h || !S.pal) return;
      const cs = getComputedStyle(document.documentElement);
      const v = (n) => cs.getPropertyValue(n).trim();
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.strokeStyle = v("--grid"); ctx.lineWidth = 1; ctx.globalAlpha = .5;
      const gs = 46 * scale, ox = tx % gs, oy = ty % gs;
      ctx.beginPath();
      for (let x = ox; x < w; x += gs) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
      for (let y = oy; y < h; y += gs) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
      ctx.stroke(); ctx.restore();

      ctx.save(); ctx.translate(tx, ty); ctx.scale(scale, scale);
      const nb = selected ? adj.get(selected) : (hover ? adj.get(hover.id) : null);
      const anchor = selected || (hover && hover.id);

      ctx.lineWidth = 1 / scale;
      for (const l of links) {
        const hot = anchor && (l.s.id === anchor || l.t.id === anchor);
        ctx.strokeStyle = hot ? v("--accent") : v("--border");
        ctx.globalAlpha = hot ? .95 : (anchor ? .14 : .4);
        ctx.beginPath(); ctx.moveTo(l.s.x, l.s.y); ctx.lineTo(l.t.x, l.t.y); ctx.stroke();
      }
      ctx.globalAlpha = 1;
      for (const o of nodes) {
        const dim = anchor && o.id !== anchor && !(nb && nb.has(o.id));
        ctx.globalAlpha = dim ? .16 : 1;
        ctx.beginPath(); ctx.arc(o.x, o.y, o.size, 0, 6.2832);
        ctx.fillStyle = comColor(o.community); ctx.fill();
        if (o.id === anchor) { ctx.lineWidth = 2.4 / scale; ctx.strokeStyle = v("--text"); ctx.stroke(); }
      }
      ctx.globalAlpha = 1;
      if (scale > 0.55 || nodes.length < 90) {
        ctx.font = `${11 / scale}px Inter, system-ui, sans-serif`;
        ctx.textAlign = "center";
        const showAll = nodes.length < 90;
        for (const o of nodes) {
          if (!showAll && scale < 1.25 && o.degree < 26) continue;
          if (anchor && o.id !== anchor && !(nb && nb.has(o.id))) continue;
          ctx.fillStyle = v("--text"); ctx.globalAlpha = .9;
          ctx.fillText(o.label.length > 26 ? o.label.slice(0, 25) + "…" : o.label, o.x, o.y - o.size - 4 / scale);
        }
      }
      ctx.restore(); ctx.globalAlpha = 1;
    }

    function loop() { cancelAnimationFrame(raf); const step = () => { tick(); draw(); raf = requestAnimationFrame(step); }; step(); }

    const toWorld = (e) => { const r = cv.getBoundingClientRect(); return { x: (e.clientX - r.left - tx) / scale, y: (e.clientY - r.top - ty) / scale }; };
    const pick = (e) => {
      const p = toWorld(e); let best = null, bd = Infinity;
      for (const o of nodes) { const d = Math.hypot(o.x - p.x, o.y - p.y); if (d < Math.max(o.size + 3 / scale, 8 / scale) && d < bd) { bd = d; best = o; } }
      return best;
    };

    cv.addEventListener("wheel", (e) => {
      e.preventDefault();
      const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
      const f = Math.exp(-e.deltaY * 0.0016), ns = Math.max(0.06, Math.min(8, scale * f));
      tx = mx - (mx - tx) * (ns / scale); ty = my - (my - ty) * (ns / scale); scale = ns;
    }, { passive: false });

    cv.addEventListener("mousedown", (e) => {
      const o = pick(e); moved = 0; last = { x: e.clientX, y: e.clientY };
      if (o) { dragging = o; alpha = Math.max(alpha, .5); } else { panning = true; cv.classList.add("drag"); }
    });
    window.addEventListener("mousemove", (e) => {
      if (last) moved += Math.abs(e.clientX - last.x) + Math.abs(e.clientY - last.y);
      if (dragging) { const p = toWorld(e); dragging.x = p.x; dragging.y = p.y; dragging.vx = dragging.vy = 0; alpha = Math.max(alpha, .35); }
      else if (panning && last) { tx += e.clientX - last.x; ty += e.clientY - last.y; }
      else { const o = pick(e); if (o !== hover) { hover = o; cv.style.cursor = o ? "pointer" : "grab"; } }
      last = { x: e.clientX, y: e.clientY };
    });
    window.addEventListener("mouseup", async (e) => {
      cv.classList.remove("drag");
      const wasPan = panning;
      dragging = null; panning = false; last = null;
      if (moved > 6) return;
      const o = pick(e);
      if (o && !wasPan) {
        selected = o.id; alpha = Math.max(alpha, .25);
        try { inspector((await api("/api/explain", { node: o.id })).node); } catch {}
      } else if (!o && wasPan) { selected = null; $("#inspector").classList.remove("on"); }
    });
    cv.addEventListener("dblclick", async (e) => {
      const o = pick(e); if (!o) return;
      $("#g-mode").value = "focus"; syncMode(); $("#g-node").value = o.label; await loadGraph();
    });

    window.addEventListener("resize", resize);
    return { resize, setData, fit, draw, get data() { return data; },
             select: (id) => { selected = id; alpha = Math.max(alpha, .2); draw(); },
             async focus(id) { $("#g-mode").value = "focus"; syncMode(); $("#g-node").value = id; await loadGraph(); } };
  })();

  // ----------------------------------------------------------- query view
  async function runQuery(draw) {
    const q = $("#qq").value.trim(); if (!q) return;
    $("#q-out").innerHTML = `<p class="empty"><span class="spin"></span> parcours…</p>`;
    try {
      const r = await api("/api/query", { q, depth: 1, budget: 2000 });
      if (!r.ok) { $("#q-out").innerHTML = `<p class="empty">${esc(r.error)}</p>`; return; }
      $("#q-out").innerHTML = `<div class="hop">${r.seeds.map((s) => `<span class="n" style="border-color:${comColor(s.community)}">${esc(s.label)}</span>`).join("")}</div>
        <p class="sub" style="margin-top:10px">Sous-graphe ciblé : <b class="num">${r.nodes.length}</b> nœuds · <b class="num">${r.links.length}</b> arêtes · ≈<b class="num">${nf.format(r.tokens)}</b> tokens (vs relire les sources).</p>`;
      if (draw) { show("graph"); graph.setData(r); $("#g-stat").textContent = `query: ${q}`; legend(r); }
    } catch (e) { $("#q-out").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  async function runPath() {
    const a = $("#pa").value.trim(), b = $("#pb").value.trim(); if (!a || !b) return;
    $("#p-out").innerHTML = `<p class="empty"><span class="spin"></span> tracé…</p>`;
    try {
      const r = await api("/api/path", { a, b });
      if (!r.ok) { $("#p-out").innerHTML = `<p class="empty">${esc(r.error)} entre « ${esc(a)} » et « ${esc(b)} »</p>`; return; }
      $("#p-out").innerHTML = `<p class="sub">Chemin le plus court — <b class="num">${r.hops}</b> saut${r.hops === 1 ? "" : "s"}</p>
        <div class="hop">${r.steps.map((s, i) => `${i ? `<span class="e">--${esc((s.edge && s.edge.relation) || "")}${s.edge && s.edge.forward === false ? " (rev)" : ""}--></span>` : ""}<span class="n" style="border-color:${comColor(s.community)}">${esc(s.label)}</span>`).join("")}</div>`;
    } catch (e) { $("#p-out").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  async function runExplain() {
    const n = $("#ex").value.trim(); if (!n) return;
    $("#e-out").innerHTML = `<p class="empty"><span class="spin"></span> chargement…</p>`;
    try {
      const node = (await api("/api/explain", { node: n })).node;
      $("#e-out").innerHTML = `<pre class="out"><b>${esc(node.label)}</b>
  source :     ${esc(node.source_file || "—")} ${esc(node.source_location || "")}
  communauté : #${node.community ?? "—"}
  degré :      ${nf.format(node.degree)}
  relations :  ${node.by_relation.map(([k, v]) => `${esc(k)}(${v})`).join(", ")}

connexions (${nf.format(node.connection_count)}) :
${node.connections.slice(0, 14).map((c) => `  ${c.direction === "out" ? "-->" : "<--"} ${esc(c.label)} [${esc(c.relation)}] [${esc(c.confidence || "?")}]`).join("\n")}</pre>`;
    } catch (e) { $("#e-out").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  // -------------------------------------------------------------- ide view
  const HOSTS = [["vscode", "VS Code"], ["cursor", "Cursor"], ["claude", "Claude Code"], ["windsurf", "Windsurf"], ["codex", "Codex"]];
  async function loadIde() {
    $("#ide-tabs").innerHTML = HOSTS.map(([id, nm]) => `<button data-h="${id}" class="${id === S.ide ? "on" : ""}">${nm}</button>`).join("");
    $$("#ide-tabs button").forEach((b) => { b.onclick = () => { S.ide = b.dataset.h; loadIde(); }; });
    try {
      const r = await api("/api/ide-config", { host: S.ide });
      $("#ide-mcp").textContent = r.mcp_enabled
        ? `POST ${r.mcp_url}\nAuthorization: Bearer gf_…   (workspace: ${r.workspace})\n\n# autonome, si vous préférez un processus dédié :\npython -m graphify.serve graphify-out/graph.json \\\n  --transport http --host 0.0.0.0 --port 8080`
        : `MCP endpoint not available in this process.\npip install "graphifyy[mcp]"   # then restart`;
      $("#ide-code").textContent = JSON.stringify(r.config, null, 2);
      $("#ide-copy").onclick = () => { navigator.clipboard.writeText(JSON.stringify(r.config, null, 2)).then(() => toast("Config copiée")); };
    } catch (e) { $("#ide-code").textContent = String(e.message); }

    const eps = [
      ["GET /api/stats", "nœuds, arêtes, communautés, mix de relations, confiance"],
      ["GET /api/god-nodes?limit=15", "concepts les plus connectés"],
      ["GET /api/communities?limit=24", "sous-systèmes avec hub + membres"],
      ["GET /api/search?q=…", "recherche de symbole en tapant"],
      ["GET /api/explain?node=…", "un nœud + toutes ses connexions"],
      ["GET /api/path?a=…&b=…", "chemin le plus court, saut par saut"],
      ["GET /api/query?q=…", "question → sous-graphe ciblé (budget de tokens)"],
      ["GET /api/graph?mode=top|focus|community", "payload canvas, découpé côté serveur"],
      ["GET /api/theme", "tokens de palette, pour qu'une extension s'accorde à l'UI"],
    ];
    $("#api-list").innerHTML = eps.map(([e, d]) => `<div class="item" style="cursor:default">
        <code style="font-size:12px;color:var(--accent);white-space:nowrap">${esc(e)}</code>
        <span class="mt" style="margin-left:auto">${esc(d)}</span></div>`).join("");
    loadKeys($("#key-list"));
  }

  // ---------------------------------------------------------- keys/account
  async function loadKeys(target) {
    if (!target) return;
    try {
      const r = await api("/api/keys");
      target.innerHTML = r.keys.length ? r.keys.map((k) => `<div class="item" style="cursor:default">
          <span class="swatch" style="background:${k.revoked_at ? "var(--faint)" : "var(--ok)"}"></span>
          <span style="min-width:0"><span class="nm">${esc(k.name)}</span> <code style="color:var(--faint)">${esc(k.prefix)}…</code><br>
          <span class="mt">créée ${ago(k.created_at)} · dernier usage ${ago(k.last_used_at)}${k.revoked_at ? " · révoquée " + ago(k.revoked_at) : ""}</span></span>
          <span class="rt">${k.revoked_at ? `<span class="pill">révoquée</span>` : `<button class="btn sm" data-rev="${esc(k.id)}">Révoquer</button>`}</span>
        </div>`).join("") : `<p class="empty">Aucune clé pour l'instant — créez-en une pour connecter un IDE ou un agent.</p>`;
      $$("[data-rev]", target).forEach((b) => {
        b.onclick = async () => {
          try { await api(`/api/keys/${b.dataset.rev}`, null, { method: "DELETE" }); toast("Clé révoquée"); loadKeys(target); if (S.view === "account") loadKeys($("#acc-keys")); } catch (e) { toast(e.message); }
        };
      });
    } catch (e) { target.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  async function loadAccount() {
    try {
      const me = await api("/api/auth/me");
      S.me = me.user;
      $("#acc-user").innerHTML = `<div class="item" style="cursor:default">
          <span class="swatch" style="background:var(--accent)"></span>
          <span><span class="nm">${esc(me.user.name || me.user.email)}</span><br>
          <span class="mt">${esc(me.user.email)} · via ${esc(me.via)}</span></span>
          <span class="rt"><span class="pill">${esc(me.workspaces.length)} workspace${me.workspaces.length === 1 ? "" : "s"}</span></span></div>`;
      $("#acc-ws").innerHTML = me.workspaces.map((w) => `<div class="item" data-ws="${esc(w.id)}">
          <span class="swatch" style="background:${w.id === me.active ? "var(--accent)" : "var(--border)"}"></span>
          <span style="min-width:0"><span class="nm">${esc(w.name)}</span><br>
          <span class="mt">${esc(w.graph)} · ${esc(w.role)}${w.graph_ready ? "" : " · graphe manquant"}</span></span>
          <span class="rt">${w.nodes != null ? `<span class="num">${nf.format(w.nodes)}</span><br><span class="mt">nœuds</span>` : ""}</span></div>`).join("");
      $$("#acc-ws .item").forEach((it) => {
        it.onclick = async () => { S.ws = it.dataset.ws; GStore.set(LS.ws, S.ws); await enter(); show("account"); };
      });
      loadKeys($("#acc-keys"));
    } catch (e) { $("#acc-user").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }


  // --------------------------------------------------------- billing & team
  const money = (n) => (n === 0 ? "$0" : `$${n}`);
  function bar(label, used, cap, fmt) {
    const pct = cap > 0 ? Math.min(100, (used / cap) * 100) : 0;
    const col = pct > 90 ? "var(--danger)" : pct > 70 ? "var(--warn)" : "var(--accent)";
    return `<div class="bar-row" style="margin-bottom:11px"><span class="nm">${label}</span>
      <span class="track" style="height:9px"><span class="fill" style="width:${pct.toFixed(1)}%;background:${col}"></span></span>
      <span class="n" style="width:auto">${fmt(used)} / ${fmt(cap)}</span></div>`;
  }

  async function loadBilling() {
    try {
      const r = await api("/api/usage");
      const cur = r.plan;
      $("#bl-period").textContent = r.usage.period;
      $("#bl-plans").innerHTML = Object.entries(r.plans).map(([id, pl]) => `
        <div class="card pad" style="${id === cur.id ? "border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)" : ""}">
          <div style="display:flex;align-items:baseline;gap:10px">
            <h2 style="margin:0;font-size:17px;text-transform:none;letter-spacing:0;color:var(--text)">${esc(pl.name)}</h2>
            <span class="num" style="font-size:22px">${money(pl.price_month)}<span class="mt">/mo</span></span>
            ${id === cur.id ? `<span class="pill" style="margin-left:auto">actuel</span>` : ""}
          </div>
          <p class="sub" style="margin:8px 0 12px">${esc(pl.blurb)}</p>
          <div class="sub" style="font-size:12.5px;line-height:1.9">
            ${cn(pl.max_workspaces)} workspaces · ${pl.max_members} sièges<br>
            ${cn(pl.max_nodes)} nœuds par graphe<br>
            ${cn(pl.max_api_calls_month)} appels API / mois<br>
            ${pl.max_upload_mb} Mo de téléversements
          </div>
          ${id === cur.id ? "" : `<button class="btn primary wide" style="margin-top:14px" data-plan="${id}">Passer à ${esc(pl.name)}</button>`}
        </div>`).join("");
      $$("[data-plan]").forEach((b) => {
        b.onclick = async () => {
          try {
            await api("/api/billing/plan", null, { method: "POST", body: { plan: b.dataset.plan } });
            toast("Plan mis à jour"); loadBilling();
          } catch (e) { toast(e.message); }
        };
      });

      const u = r.usage, pl = cur;
      $("#bl-bars").innerHTML =
        bar("Appels API", u.api_calls, pl.max_api_calls_month, cn) +
        bar("Appels MCP", u.mcp_calls, pl.max_api_calls_month, cn) +
        bar("Téléversements", u.uploads, 100, cn) +
        bar("Sièges", r.counts.members, pl.max_members, cn) +
        bar("Workspaces (vous)", r.counts.workspaces, pl.max_workspaces, cn);

      $("#bl-hist").innerHTML = r.history.length
        ? `<table class="tbl" style="margin-top:0"><thead><tr><th>Période</th><th>API</th><th>MCP</th><th>Télév.</th><th>Octets</th></tr></thead><tbody>` +
          r.history.map((h) => `<tr><td>${esc(h.period)}</td><td>${cn(h.api_calls)}</td><td>${cn(h.mcp_calls)}</td><td>${h.uploads}</td><td>${(h.uploaded_bytes / 1048576).toFixed(1)} Mo</td></tr>`).join("") +
          `</tbody></table>`
        : `<p class="empty">Aucun usage enregistré pour l'instant.</p>`;
    } catch (e) { $("#bl-bars").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  async function loadTeam() {
    try {
      const m = await api("/api/members");
      $("#tm-members").innerHTML = m.members.map((x) => `<div class="item" style="cursor:default">
          <span class="swatch" style="background:${x.role === "owner" ? "var(--accent)" : x.role === "member" ? "var(--ok)" : "var(--faint)"}"></span>
          <span style="min-width:0"><span class="nm">${esc(x.name || x.email)}</span><br><span class="mt">${esc(x.email)}</span></span>
          <span class="rt"><span class="pill">${esc(x.role)}</span>
          ${x.role !== "owner" ? ` <button class="btn sm" data-rm="${esc(x.id)}">Retirer</button>` : ""}</span>
        </div>`).join("");
      $$("[data-rm]").forEach((b) => {
        b.onclick = async () => {
          try { await api(`/api/members/${b.dataset.rm}`, null, { method: "DELETE" }); toast("Membre retiré"); loadTeam(); }
          catch (e) { toast(e.message); }
        };
      });
      $("#tm-go").onclick = async () => {
        const email = $("#tm-email").value.trim();
        if (!email) return toast("Email requis");
        try {
          const r = await api("/api/invites", null, {
            method: "POST", body: { email, role: $("#tm-role").value },
          });
          $("#tm-link").innerHTML = `<div class="card" style="border-color:var(--ok);margin-top:12px">
            <div class="sub" style="margin-bottom:6px">Envoyez ce lien — il est lié à ${esc(email)} :</div>
            <div class="code" style="white-space:pre-wrap;word-break:break-all;color:var(--text)">${esc(r.accept_url)}</div>
            <button class="btn sm" style="margin-top:8px" id="tm-copy">Copier le lien</button></div>`;
          $("#tm-copy").onclick = () => navigator.clipboard.writeText(r.accept_url).then(() => toast("Lien copié"));
          $("#tm-email").value = "";
          loadTeam();
        } catch (e) { toast(e.message); }
      };
      const iv = await api("/api/invites");
      $("#tm-invites").innerHTML = iv.invites.length ? iv.invites.map((x) => `<div class="item" style="cursor:default">
          <span class="swatch" style="background:${x.accepted_at ? "var(--ok)" : "var(--warn)"}"></span>
          <span style="min-width:0"><span class="nm">${esc(x.email)}</span><br><span class="mt">${esc(x.role)} · ${x.accepted_at ? "acceptée" : "en attente · expire " + ago(x.expires_at)}</span></span>
          <span class="rt">${x.accepted_at ? `<span class="pill">acceptée</span>` : `<button class="btn sm" data-rv="${esc(x.id)}">Révoquer</button>`}</span>
        </div>`).join("") : `<p class="empty">Aucune invitation en attente.</p>`;
      $$("[data-rv]").forEach((b) => {
        b.onclick = async () => {
          try { await api(`/api/invites/${b.dataset.rv}`, null, { method: "DELETE" }); toast("Invitation révoquée"); loadTeam(); }
          catch (e) { toast(e.message); }
        };
      });
    } catch (e) { $("#tm-members").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  // ------------------------------------------------- builds & rapport
  const JOB_FR = { queued: "en file", running: "en cours", done: "terminé", failed: "échoué" };
  async function loadBuilds() {
    try {
      const r = await api("/api/builds");
      $("#bd-jobs").innerHTML = r.jobs.length ? r.jobs.map((j) => `<div class="item" style="cursor:default">
          <span class="swatch" style="background:${j.status === "done" ? "var(--ok)" : j.status === "failed" ? "var(--danger)" : "var(--warn)"}"></span>
          <span style="min-width:0"><span class="nm">${esc(j.name)}</span> <code style="color:var(--faint)">${esc(j.id)}</code><br>
          <span class="mt">${esc(j.source)}${j.wiki ? " · wiki" : ""}</span><br>
          <span class="mt">${j.status === "running" ? `<span class="spin"></span> étape : ${esc(j.stage)}`
            : j.status === "done" ? `${nf.format(j.result.nodes)} nœuds · ${nf.format(j.result.edges)} arêtes · ${j.result.communities} communautés · ${j.result.files} fichiers${j.workspace_error ? " · workspace non créé : " + esc(j.workspace_error) : ""}`
            : esc(j.error || "")}</span></span>
          <span class="rt"><span class="pill">${JOB_FR[j.status] || esc(j.status)}</span></span>
        </div>`).join("") : `<p class="empty">Aucun job pour l'instant — lancez une construction ci-dessus.</p>`;
    } catch (e) { $("#bd-jobs").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  function inlineMd(x) { return esc(x).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>"); }
  function miniMd(src) {
    let html = "", inCode = false, inTable = false, inUl = false;
    const close = () => { if (inCode) { html += "</pre>"; inCode = false; } if (inTable) { html += "</tbody></table>"; inTable = false; } if (inUl) { html += "</ul>"; inUl = false; } };
    for (const ln of String(src).split("\n")) {
      if (ln.startsWith("```")) { if (inCode) { html += "</pre>"; inCode = false; } else { close(); html += '<pre class="code">'; inCode = true; } continue; }
      if (inCode) { html += esc(ln) + "\n"; continue; }
      const t = ln.trim();
      if (t.startsWith("|")) {
        if (!inTable) { close(); html += '<table class="tbl"><tbody>'; inTable = true; }
        if (/^\|[\s:|-]+$/.test(t)) continue;
        html += "<tr>" + t.slice(1, -1).split("|").map((c) => `<td>${inlineMd(c.trim())}</td>`).join("") + "</tr>";
        continue;
      }
      if (inTable) { html += "</tbody></table>"; inTable = false; }
      const h = t.match(/^(#{1,4}) /);
      if (h) { close(); html += `<h${h[1].length} class="md-h${h[1].length}">${inlineMd(t.replace(/^#+ /, ""))}</h${h[1].length}>`; continue; }
      if (/^[-*] /.test(t)) { if (!inUl) { close(); html += '<ul class="md-ul">'; inUl = true; } html += `<li>${inlineMd(t.slice(2))}</li>`; continue; }
      if (inUl) { html += "</ul>"; inUl = false; }
      if (!t) continue;
      close();
      html += `<p class="md-p">${inlineMd(t)}</p>`;
    }
    close();
    return html;
  }

  async function loadReport() {
    try {
      const r = await api("/api/report");
      $("#rp-md").innerHTML = r.available ? miniMd(r.markdown) : `<p class="empty">${esc(r.hint || "rapport indisponible")}</p>`;
    } catch (e) { $("#rp-md").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
    $$("#v-report [data-exp]").forEach((b) => {
      b.onclick = () => {
        const tok = GStore.get(LS.token);
        location.href = `/api/export?kind=${b.dataset.exp}&token=${encodeURIComponent(tok || "")}`;
      };
    });
    $("#rp-bench").onclick = async () => {
      $("#rp-bench-out").innerHTML = `<p class="empty"><span class="spin"></span> mesure…</p>`;
      try {
        const r = await api("/api/benchmark");
        const b = r.benchmark || {};
        $("#rp-bench-out").innerHTML = `<div class="card pad" style="margin-bottom:12px">
          <h2>Benchmark tokens</h2>
          <div class="sub" style="line-height:1.9">${Object.entries(b).slice(0, 10).map(([k, v]) =>
            `${esc(k)} : <b class="num">${typeof v === "number" ? nf.format(v) : esc(JSON.stringify(v))}</b>`).join("<br>")}</div></div>`;
      } catch (e) { $("#rp-bench-out").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
    };
  }

  // ------------------------------------------------------------ live sync
  let sse = null;
  function subscribeEvents() {
    if (sse) { sse.close(); sse = null; }
    if (!GStore.get(LS.token)) return;
    const tok = GStore.get(LS.token);
    try {
      sse = new EventSource("/api/events?token=" + encodeURIComponent(tok || ""), { withCredentials: true });
    } catch { return; }
    sse.addEventListener("build", (ev) => {
      let d = {}; try { d = JSON.parse(ev.data); } catch { return; }
      if (S.view === "builds") loadBuilds();
      (d.jobs || []).forEach((j) => {
        if (j.status === "done" && !S.seenBuilds[j.id]) {
          S.seenBuilds[j.id] = 1;
          toast(`Build « ${j.name} » terminé — ${nf.format((j.result || {}).nodes || 0)} nœuds`);
          enter();
        }
      });
    });
    sse.addEventListener("graph", async () => {
      toast("Graphe reconstruit — actualisation…");
      try {
        S.stats = await api("/api/stats");
        if (S.view === "overview") loadOverview();
        if (S.view === "graph") loadGraph();
        if (S.view === "communities") loadComms();
      } catch {}
    });
    sse.onerror = () => { /* EventSource retries on its own */ };
  }

  // ---------------------------------------------------------------- search
  let sTimer = null;
  function bindSearch() {
    const inp = $("#q"), pop = $("#search-pop");
    const close = () => { pop.style.display = "none"; };
    inp.addEventListener("input", () => {
      clearTimeout(sTimer);
      const v = inp.value.trim();
      if (v.length < 2) return close();
      sTimer = setTimeout(async () => {
        try {
          const r = await api("/api/search", { q: v, limit: 12 });
          pop.innerHTML = r.results.length
            ? r.results.map((n) => `<div class="row" data-node="${esc(n.id)}">
                <span class="sw" style="background:${comColor(n.community)}"></span>
                <span class="nm">${esc(n.label)}</span>
                <span class="meta">${esc(String(n.source_file || "").split("/").pop())} · ${nf.format(n.degree)}</span></div>`).join("")
            : `<div class="row"><span class="mt">aucun résultat</span></div>`;
          pop.style.display = "block";
          $$(".row[data-node]", pop).forEach((row) => { row.onclick = () => { close(); inp.value = ""; openNode(row.dataset.node); }; });
        } catch { close(); }
      }, 150);
    });
    inp.addEventListener("blur", () => setTimeout(close, 180));
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); inp.focus(); }
      if (e.key === "Escape") { close(); $("#inspector").classList.remove("on"); }
    });
  }

  // ------------------------------------------------------------ post-login
  async function enter() {
    const me = await api("/api/auth/me");
    S.me = me.user;
    if (!S.ws || !me.workspaces.some((w) => w.id === S.ws)) S.ws = me.active || (me.workspaces[0] || {}).id || null;
    GStore.set(LS.ws, S.ws || "");
    bindWorkspaceSwitcher(me.workspaces, S.ws);
    $("#verpill").textContent = (me.workspaces.find((w) => w.id === S.ws) || {}).slug || "workspace";

    if (!S.ws) {
      $("#ov-sub").innerHTML = `Pas encore de workspace. Créez-en un dans <b>Profil &amp; clés</b> — pointez-le vers un <code>graph.json</code> construit avec <code>graphify extract . --code-only</code>.`;
      $("#ov-stats").innerHTML = ""; $("#ov-rel").innerHTML = ""; $("#ov-conf").innerHTML = ""; $("#ov-files").innerHTML = ""; $("#ov-gods").innerHTML = "";
      show("account");
      return;
    }
    try {
      S.stats = await api("/api/stats");
      graph.clear && graph.clear();
      await loadOverview();
      await Promise.all([loadComms(), loadGods()]);
      show(S.view === "account" ? "overview" : S.view);
      graph.resize();
    } catch (e) {
      $("#ov-sub").innerHTML = `<span style="color:var(--danger)">${esc(e.message)}</span>`;
    }
  }

  // ------------------------------------------------------------------ boot
  async function boot() {
    if (GStore.get("graphify.navfold") === "1") document.body.classList.add("folded");
    $("#btn-fold").onclick = () => {
      const folded = document.body.classList.toggle("folded");
      GStore.set("graphify.navfold", folded ? "1" : "");
      setTimeout(() => graph.resize(), 220);
    };
    $("#dv-combined").onclick = loadCombined;
    $("#dv-all").onclick = (e) => {
      const wrap = $("#dv-repos").classList.toggle("wrap");
      e.currentTarget.firstChild.textContent = wrap ? "Réduire " : "Afficher tout ";
    };
    $$("#nav button[data-view]").forEach((b) => { b.onclick = () => show(b.dataset.view); });
    $("#btn-ide").onclick = () => show("ide");
    $("#btn-keys").onclick = () => show("ide");
    $("#g-mode").onchange = () => { syncMode(); loadGraph(); };
    $("#g-comm").onchange = loadGraph;
    $("#g-node").onchange = loadGraph;
    $("#g-limit").oninput = () => { $("#g-limit-v").textContent = $("#g-limit").value; };
    $("#g-limit").onchange = loadGraph;
    $("#g-reload").onclick = loadGraph;
    $("#g-fit").onclick = () => graph.fit();
    $("#q-go").onclick = () => runQuery(false);
    $("#q-draw").onclick = () => runQuery(true);
    $("#qq").addEventListener("keydown", (e) => { if (e.key === "Enter") runQuery(false); });
    $("#p-go").onclick = runPath;
    $("#e-go").onclick = runExplain;
    $("#ex").addEventListener("keydown", (e) => { if (e.key === "Enter") runExplain(); });
    $("#key-new").onclick = async () => {
      try {
        const r = await api("/api/keys", null, { method: "POST", body: { name: $("#key-name").value || "default" } });
        $("#key-secret").innerHTML = `<div class="card" style="border-color:var(--ok);margin-bottom:10px">
            <div class="sub" style="margin-bottom:6px">Copiez-la maintenant — elle est stockée hashée et ne sera plus jamais montrée :</div>
            <div class="code" style="white-space:pre-wrap;word-break:break-all;color:var(--text)">${esc(r.key.secret)}</div>
            <button class="btn sm" style="margin-top:8px" id="sec-copy">Copier la clé</button></div>`;
        $("#sec-copy").onclick = () => navigator.clipboard.writeText(r.key.secret).then(() => toast("Clé copiée"));
        $("#key-name").value = "";
        loadKeys($("#key-list"));
      } catch (e) { toast(e.message); }
    };
    $("#nw-go").onclick = async () => {
      try {
        const r = await api("/api/workspaces", null, { method: "POST", body: { name: $("#nw-name").value, graph: $("#nw-graph").value } });
        S.ws = r.workspace.id; GStore.set(LS.ws, S.ws);
        toast("Workspace créé"); await enter(); show("account");
      } catch (e) { $("#nw-hint").innerHTML = `<span style="color:var(--danger)">${esc(e.message)}</span>`; }
    };
    $("#nw-file").onchange = () => {
      const f = $("#nw-file").files[0];
      $("#nw-file-label").textContent = f ? f.name : "Upload graph.json…";
    };
    $("#nw-up").onclick = async () => {
      const f = $("#nw-file").files[0];
      if (!f) return toast("Choisissez d'abord un graph.json");
      const fd = new FormData();
      fd.append("file", f);
      fd.append("name", $("#nw-name").value || f.name.replace(/\.json$/, ""));
      $("#nw-hint").innerHTML = `<span class="spin"></span> téléversement…`;
      try {
        const r = await fetch("/api/workspaces/upload?token=" + encodeURIComponent(GStore.get(LS.token) || ""), {
          method: "POST",
          headers: { Authorization: "Bearer " + GStore.get(LS.token) },
          body: fd,
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || "HTTP " + r.status);
        S.ws = j.workspace.id; GStore.set(LS.ws, S.ws);
        $("#nw-hint").textContent = `Créé : ${j.workspace.slug} (${(j.bytes / 1048576).toFixed(1)} Mo).`;
        $("#nw-file").value = ""; $("#nw-file-label").textContent = "Upload graph.json…";
        await enter(); show("account");
      } catch (e) { $("#nw-hint").innerHTML = `<span style="color:var(--danger)">${esc(e.message)}</span>`; }
    };
    $("#bd-go").onclick = async () => {
      const src = $("#bd-source").value.trim();
      if (!src) return toast("Indiquez un chemin source");
      $("#bd-hint").innerHTML = `<span class="spin"></span> lancement…`;
      try {
        const r = await api("/api/builds", null, { method: "POST", body: {
          name: $("#bd-name").value.trim() || src.split("/").filter(Boolean).pop(),
          source: src, wiki: $("#bd-wiki").checked } });
        $("#bd-hint").textContent = `Job ${r.job.id} lancé — étapes : detect → extract → build → cluster → analyze → report → export.`;
        loadBuilds();
      } catch (e) { $("#bd-hint").innerHTML = `<span style="color:var(--danger)">${esc(e.message)}</span>`; }
    };
    $("#bu-file").onchange = () => {
      const f = $("#bu-file").files[0];
      $("#bu-file-label").textContent = f ? f.name : "Choisir une archive…";
    };
    $("#bu-go").onclick = async () => {
      const f = $("#bu-file").files[0];
      if (!f) return toast("Choisissez d'abord une archive");
      const fd = new FormData();
      fd.append("file", f);
      fd.append("name", $("#bu-name").value || f.name.replace(/\.(zip|tar\.gz|tgz|tar)$/, ""));
      $("#bu-hint").innerHTML = `<span class="spin"></span> téléversement…`;
      try {
        const tok = GStore.get(LS.token);
        const r = await fetch("/api/builds/upload?token=" + encodeURIComponent(tok || ""), {
          method: "POST", headers: { Authorization: "Bearer " + tok }, body: fd });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || "HTTP " + r.status);
        $("#bu-hint").textContent = `Job ${j.job.id} lancé sur l'archive décompressée.`;
        $("#bu-file").value = ""; $("#bu-file-label").textContent = "Choisir une archive…";
        loadBuilds();
      } catch (e) { $("#bu-hint").innerHTML = `<span style="color:var(--danger)">${esc(e.message)}</span>`; }
    };
    bindSearch();
    bindGate();
    subscribeEvents();

    try {
      S.theme = await api("/api/theme");
      buildThemeSwitcher();
      applyTheme(GStore.get(LS.theme) || S.theme.default);
    } catch (e) { return; }

    // Health tells the gate whether a demo account was seeded at boot.
    try {
      const h = await api("/api/health");
      $("#gate-foot").innerHTML = h.mcp ? "Endpoint MCP actif sur <code>/mcp</code>" : "Extra MCP non installé";
    } catch {}

    S.ws = GStore.get(LS.ws) || null;
    if (!GStore.get(LS.token)) return gate();
    try { await enter(); } catch (e) { gate(); }
  }
  boot();
})();
