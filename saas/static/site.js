/* Landing + auth pages: theme switcher, decorative graph canvas, auth form.
   Shares /theme.css tokens with the workspace so the whole product is one brand. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const LS_THEME = "graphify.theme", LS_TOKEN = "graphify.token", LS_WS = "graphify.ws";

  // ------------------------------------------------------------------ theme
  async function initTheme() {
    let data = null;
    try { data = await (await fetch("/api/theme")).json(); } catch { return; }
    const mounts = ["#themes", "#themes-m"].map((s) => $(s)).filter(Boolean);
    const saved = GStore.get(LS_THEME);
    const apply = (id) => {
      document.documentElement.dataset.theme = id;
      GStore.set(LS_THEME, id);
      mounts.forEach((m) => [...m.children].forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === id))));
      paintCanvas();
    };
    mounts.forEach((m) => {
      m.innerHTML = "";
      data.themes.forEach((t) => {
        const b = document.createElement("button");
        b.className = "sw"; b.dataset.id = t.id; b.title = t.name;
        b.style.background = `linear-gradient(135deg, ${t.accent} 0 52%, ${t.bg} 52% 100%)`;
        b.onclick = () => apply(t.id);
        m.appendChild(b);
      });
    });
    apply(saved && data.themes.some((t) => t.id === saved) ? saved : data.default);
  }

  // -------------------------------------------- decorative force-layout bg
  let canvasState = null;
  function paintCanvas() {
    const cv = $("#hero-canvas") || $("#side-canvas");
    if (!cv || !canvasState) return;
    const { ctx, w, h, nodes, links } = canvasState;
    const cs = getComputedStyle(document.documentElement);
    const v = (n) => cs.getPropertyValue(n).trim();
    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 1;
    ctx.strokeStyle = v("--border"); ctx.globalAlpha = .5;
    for (const l of links) { ctx.beginPath(); ctx.moveTo(l.a.x, l.a.y); ctx.lineTo(l.b.x, l.b.y); ctx.stroke(); }
    ctx.globalAlpha = 1;
    const series = [v("--accent"), v("--accent-2"), v("--ok"), v("--warn"), v("--danger")];
    nodes.forEach((n, i) => {
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, 6.2832);
      ctx.fillStyle = series[i % series.length]; ctx.globalAlpha = n.hi ? .95 : .55;
      ctx.fill();
    });
    ctx.globalAlpha = 1;
  }
  function initCanvas() {
    const cv = $("#hero-canvas") || $("#side-canvas");
    if (!cv) return;
    const box = cv.parentElement.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(1, box.width), h = Math.max(1, box.height);
    cv.width = w * dpr; cv.height = h * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const N = 46;
    const nodes = Array.from({ length: N }, (_, i) => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: 0, vy: 0, r: 2 + Math.random() * 4.5, hi: i % 9 === 0,
    }));
    const links = [];
    for (let i = 1; i < N; i++) {
      const j = Math.floor(Math.random() * i);
      links.push({ a: nodes[i], b: nodes[j] });
      if (Math.random() < .18) links.push({ a: nodes[i], b: nodes[Math.floor(Math.random() * i)] });
    }
    canvasState = { ctx, w, h, nodes, links };
    paintCanvas();

    let alpha = 1;
    (function step() {
      for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = .5; dy = .5; d2 = .5; }
        if (d2 > 26000) continue;
        const f = (900 * alpha) / d2, d = Math.sqrt(d2);
        a.vx += dx / d * f; a.vy += dy / d * f; b.vx -= dx / d * f; b.vy -= dy / d * f;
      }
      for (const l of links) {
        const dx = l.b.x - l.a.x, dy = l.b.y - l.a.y, d = Math.max(1, Math.hypot(dx, dy));
        const f = (d - 74) * .012 * alpha;
        l.a.vx += dx / d * f; l.a.vy += dy / d * f; l.b.vx -= dx / d * f; l.b.vy -= dy / d * f;
      }
      for (const n of nodes) {
        n.vx += (w / 2 - n.x) * .0009 * alpha; n.vy += (h / 2 - n.y) * .0009 * alpha;
        n.vx *= .86; n.vy *= .86;
        n.x = Math.max(8, Math.min(w - 8, n.x + n.vx));
        n.y = Math.max(8, Math.min(h - 8, n.y + n.vy));
      }
      alpha = Math.max(.12, alpha * .995);
      paintCanvas();
      requestAnimationFrame(step);
    })();
    window.addEventListener("resize", () => {
      const b2 = cv.parentElement.getBoundingClientRect();
      canvasState.w = Math.max(1, b2.width); canvasState.h = Math.max(1, b2.height);
      cv.width = canvasState.w * dpr; cv.height = canvasState.h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    });
  }

  // ------------------------------------------------------------------ auth
  function initAuth() {
    const form = $("#auth-form");
    if (!form) return;
    let mode = location.pathname.endsWith("signup") ? "signup" : "login";
    const setMode = (m) => {
      mode = m;
      $("#tab-login").classList.toggle("on", m === "login");
      $("#tab-signup").classList.toggle("on", m === "signup");
      $("#f-name").style.display = m === "signup" ? "" : "none";
      $("#au-title").textContent = m === "signup" ? "Créez votre workspace" : "Bon retour";
      $("#au-lede").textContent = m === "signup"
        ? "Un compte, autant de workspaces que de codebases."
        : "Connectez-vous pour ouvrir vos workspaces.";
      $("#au-go").textContent = m === "signup" ? "Créer un compte" : "Connexion";
      $("#au-pass").autocomplete = m === "signup" ? "new-password" : "current-password";
      $("#au-err").textContent = "";
    };
    $("#tab-login").onclick = () => setMode("login");
    $("#tab-signup").onclick = () => setMode("signup");
    setMode(mode);

    // One-click demo: the deployment tells us whether a seeded account exists,
    // never the credentials - the button just asks the server to log itself in.
    fetch("/api/health").then((r) => r.json()).then((h) => {
      if (!h.demo_login) return;
      const wrap = document.createElement("div");
      wrap.style.margin = "14px 0 4px";
      wrap.innerHTML = `<button class="btn wide" type="button" id="au-demo"
        style="border-style:dashed">Entrer avec le compte démo</button>`;
      form.before(wrap);
      $("#au-demo").onclick = async (e) => {
        const b = e.currentTarget; b.disabled = true; b.innerHTML = `<span class="spin"></span>`;
        try {
          const r = await fetch("/api/auth/demo", { method: "POST" });
          const d = await r.json();
          if (!r.ok) throw new Error(d.error || "HTTP " + r.status);
          GStore.set(LS_TOKEN, d.token);
          const first = (d.workspaces || [])[0];
          if (first) GStore.set(LS_WS, first.id);
          const next = new URLSearchParams(location.search).get("next");
          const base = next && next.startsWith("/") && !next.startsWith("//") ? next : "/app";
          location.href = base + "#token=" + encodeURIComponent(d.token);
        } catch (ex) {
          $("#au-err").textContent = ex.message;
          b.disabled = false; b.textContent = "Entrer avec le compte démo";
        }
      };
    }).catch(() => {});

    form.onsubmit = async (e) => {
      e.preventDefault();
      const err = $("#au-err"); err.textContent = "";
      const btn = $("#au-go"); const label = btn.textContent;
      btn.innerHTML = `<span class="spin"></span>`; btn.disabled = true;
      try {
        const r = await fetch(`/api/auth/${mode}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: $("#au-email").value.trim(),
            password: $("#au-pass").value,
            name: $("#au-name").value.trim(),
          }),
        });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.error || "HTTP " + r.status);
        GStore.set(LS_TOKEN, d.token);
        const first = (d.workspaces || [])[0];
        if (first) GStore.set(LS_WS, first.id); else GStore.del(LS_WS);
        const next = new URLSearchParams(location.search).get("next");
        const base = next && next.startsWith("/") && !next.startsWith("//") ? next : "/app";
        location.href = base + "#token=" + encodeURIComponent(d.token);
      } catch (ex) {
        err.textContent = ex.message;
        btn.textContent = label; btn.disabled = false;
      }
    };
  }

  // ------------------------------------------------------------------ boot
  // Already signed in and landing here? Go straight to the workspace.
  if (GStore.get("graphify.token") && location.pathname !== "/signup") {
    const qs = new URLSearchParams(location.search);
    // bounce=1 means /app just rejected this token: show the form instead of
    // redirecting straight back into the same rejection.
    if (!qs.has("bounce") && location.pathname === "/login") {
      const back = qs.get("next");
      location.replace(back && back.startsWith("/") && !back.startsWith("//") ? back : "/app");
    }
  }
  initTheme();
  initCanvas();
  initAuth();
})();
