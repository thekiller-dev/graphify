/* Resilient token storage.

   The workspace is meant to run inside embedded previews and IDE webviews,
   where localStorage can be unavailable outright (sandboxed iframe without
   allow-same-origin) or partitioned/evicted. Every read/write therefore falls
   back, in order: localStorage → a first-party JS-readable cookie → memory.

   The cookie tier is deliberately NOT HttpOnly (the server's gf_session cookie
   is): this one is a client-side mirror so a token survives a /login → /app
   navigation when localStorage is gone. It is SameSite=None; Secure because
   the preview embeds us cross-site over HTTPS.
*/
window.GStore = (() => {
  "use strict";
  const mem = {};

  // A token handed over by the login page as #token=... (fragments never reach
  // the server, so this is safe in transit). Adopted once, at boot, into
  // whichever tier actually works in this context, then erased from the URL.
  let bootToken = null;
  try {
    const fm = window.location.hash.match(/[#&]token=([^&]+)/);
    if (fm) {
      bootToken = decodeURIComponent(fm[1]);
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
  } catch { /* ignore */ }
  let mode = "memory";
  try {
    const probe = "__gf_probe__";
    window.localStorage.setItem(probe, "1");
    window.localStorage.removeItem(probe);
    mode = "local";
  } catch {
    try {
      document.cookie = "__gf_probe__=1; path=/; max-age=5; SameSite=None; Secure";
      mode = document.cookie.includes("__gf_probe__") ? "cookie" : "memory";
    } catch { /* stay on memory */ }
  }
  const cSet = (k, v) => {
    document.cookie = `${k}=${encodeURIComponent(v)}; path=/; max-age=2592000; SameSite=None; Secure`;
  };
  const cGet = (k) => {
    const hit = document.cookie.split("; ").find((c) => c.startsWith(k + "="));
    return hit ? decodeURIComponent(hit.slice(k.length + 1)) : null;
  };
  const cDel = (k) => {
    document.cookie = `${k}=; path=/; max-age=0; SameSite=None; Secure`;
  };
  const store = {
    mode,
    get(k) {
      if (mode === "local") { try { return window.localStorage.getItem(k); } catch { /* fall through */ } }
      if (mode === "cookie") return cGet(k);
      return k in mem ? mem[k] : null;
    },
    set(k, v) {
      if (mode === "local") { try { window.localStorage.setItem(k, v); return; } catch { /* fall through */ } }
      if (mode === "cookie") { cSet(k, v); return; }
      mem[k] = v;
    },
    del(k) {
      if (mode === "local") { try { window.localStorage.removeItem(k); } catch { /* ignore */ } }
      if (mode === "cookie") cDel(k);
      delete mem[k];
    },
  };
  if (bootToken) store.set("graphify.token", bootToken);
  return store;
})();
