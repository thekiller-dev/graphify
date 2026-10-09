# PROMPT DE MISSION — Construire le SaaS « Grafik » au-dessus de graphify

> Comment l'utiliser : collez ce prompt en entier à votre agent orchestrateur.
> Chaque **phase** (section 7) peut être distribuée à un agent séparé ; un agent
> ne passe à la suivante que si les **critères d'acceptation** de la phase
> courante sont verts. Ne jamais supprimer une contrainte de la section 3 :
> chacune correspond à un bug réel déjà payé.

---

## 0. Rôle

Tu es l'ingénieur principal d'un produit SaaS nommé **Grafik**, construit AU-DESSUS
du moteur open source **graphify** (repo `thekiller-dev/graphify`, v0.9.77,
Apache-2.0 + MIT). Le moteur n'est JAMAIS forké : il est importé comme dépendance
(`pip install -e .`) et consommé via ses modules (`graphify.extract`,
`graphify.serve`, `graph.json`) et son endpoint MCP. Ton travail est la couche
hosted : auth multi-tenant, workspaces, plans & quota, self-serve, équipes,
usage facturable, app web, API REST + MCP périmétrés.

## 1. graphify en 10 lignes (contexte moteur)

1. graphify transforme une base de code (+ docs, PDF, médias) en graphe de
   connaissances `graph.json` : nœuds (symboles, fichiers, concepts) + arêtes
   typées (`calls`, `imports`, `inherits`, `references`…) avec confiance
   `EXTRACTED` / `INFERRED` / `AMBIGUOUS`.
2. Extraction tree-sitter déterministe, locale, **zéro LLM** pour le code
   (37 grammaires, ~40 langages).
3. `cluster.py` : communautés Leiden = sous-systèmes ; `analyze.py` : god nodes,
   filtrage du bruit.
4. Surface de lecture : `query` (sous-graphe à budget de tokens), `path`
   (chemin le plus court), `explain` (un nœud + connexions), `search`.
5. `serve.py` : serveur MCP (stdio/HTTP) avec outils `query_graph`, `get_node`,
   `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`,
   `list_prs`, `get_pr_impact`, `triage_prs`.
6. Tout se sert depuis `graph.json` : c'est LE artefact que Grafik attache à un
   workspace (chemin serveur ou téléversement).
7. Builds lourds possibles (15 000+ nœuds) : toujours découper côté serveur
   avant d'envoyer au navigateur.
8. CLI : `graphify extract . --code-only --out .` produit `graphify-out/graph.json`.
9. Le moteur expose aussi exports (Obsidian, Neo4j, HTML, wiki) et `--watch`.
10. Benchmarks utiles au marketing : LOCOMO recall@10 0,497 (mem0 0,048) ;
    71,5× moins de tokens sur 52 fichiers ; 0 crédit LLM à la construction.

## 2. Vision produit

- **Nom** : Grafik. Logo = « G » ouvert (arc + barre) piqué de nœuds colorés ;
  wordmark en **Sora** ; corps de texte en **Satoshi**. Le moteur garde le nom
  graphify partout où c'est factuel (configs IDE, MCP, CLI).
- **Cible d'hébergement** : cloud managé (process unique + SQLite au début ;
  Postgres/S3 plus tard, sans casser les contrats d'API).
- **Extension IDE d'abord** : l'API JSON + le endpoint MCP par workspace SONT le
  produit pour les IDE ; l'app web est la vitrine et l'admin.
- **Pages obligatoires** : landing marketing complète, `/login` et `/signup`
  RÉELS (pas d'overlay in-app), `/app`, `/invite`. UI en français.
- **Thèmes** : 4 palettes via tokens CSS (`/theme.css`), défaut « daylight »
  (fond #F5F7FC, accent #4F46E5, accent2 #0891B2) ; l'app expose un switcher.
- **Plans** : free 0 $ (3 workspaces, 3 sièges, 250 k nœuds, 50 k appels API/mois,
  100 Mo) ; pro 49 $ (50/25/5 M/2 M/1000 Mo). Dépassement = **402**.

## 3. Contraintes NON NÉGOCIABLES (chacune = un bug déjà payé)

1. **Handlers = Response, jamais de dict.** Un handler Starlette qui retourne un
   `dict` → `TypeError: 'dict' object is not callable` → 500 silencieuse sur
   session VALIDE → l'app rebondit sur /login. Auditer en AST : tout `api_*`
   retourne `JSONResponse`/`Response`.
2. **Auth à 4 canaux** sur `/api/*` : `Authorization: Bearer <session|gf_…>`,
   cookie HttpOnly `gf_session`, **`?token=` en query** (canal de secours : les
   proxies de preview stripent `Authorization` et les iframes bloquent les
   cookies tierce-partie), et handoff `#token=` entre pages. Le query token
   n'est JAMAIS loggé.
3. **Cookie `SameSite=None; Secure`** (iframe cross-site) ; le mirror client,
   lui, est un cookie JS-readable non HttpOnly.
4. **Stockage client résilient** (`store.js`) : sonde localStorage → cookie JS →
   mémoire ; adopte le fragment `#token=` au boot puis l'efface
   (`history.replaceState`). `localStorage` PEUT thrower en iframe sandbox.
5. **Cache** : HTML et `/static/*` en `Cache-Control: no-cache`, et chaque URL
   `/static/` dans le HTML porte `?v=<hash du contenu>` (les iframes de preview
   ne peuvent pas faire de hard-reload ; le cache heuristique épingle sinon un
   vieux app.js contre un HTML neuf).
6. **Chicken-and-egg workspace** : `require()` exige un workspace SAUF sur les
   endpoints qui servent à le créer/lister (`/api/auth/me`, `/api/workspaces`) —
   sinon un compte neuf ne peut jamais créer son premier workspace (403).
7. **Jail de chemins** : tout chemin fourni par un tenant est `resolve()` puis
   vérifié sous `data_root()` (ou le bootstrap) + suffixe `.json` ; sinon 400.
   Les uploads atterrissent sous la racine de données, jamais ailleurs.
8. **MCP** : ne JAMAIS créer le `StreamableHTTPSessionManager` dans un handler
   (cancel-scope anyio) ; un task superviseur par graphe, démarré au lifespan.
   Ne pas monter le MCP comme sous-app Starlette (lifespan) ; ne pas ouvrir un
   2e port.
9. **Metering double** : table `usage` (période mensuelle, quota/facturation) ET
   table `daily` (jour, pour les graphiques du dashboard) ; incrémentées dans le
   même upsert. Quota dépassé → `LimitExceeded` → 402 AVANT tout travail.
10. **Registry LRU** des graphes avec empreinte de contenu (`fingerprint`) :
    `peek()` ne charge pas, `evict()` borne la RAM ; 50 tenants ≠ 50 graphes.
11. **Visibilité serveur** : middleware de log d'accès sur `/api/auth*`, `/mcp`
    et tout statut ≥ 400, CHEMIN SANS QUERY STRING (le token ne fuit pas dans
    les logs). uvicorn en `warning` seul rend les échecs navigateur invisibles.
12. **Selftest en processus** (`python -m saas.selftest`) : driver ASGI brut
    (scope/receive/send, pas d'httpx, pas de port) qui rejoue le parcours
    navigateur : signup → me (3 canaux + anon 401) → création 1er workspace →
    stats/slice bornée → clé API → clé boguée 401. Tout push doit le laisser vert.
13. **Boucle de bounce** : /app renvoie vers `/login?next=/app&bounce=1` ;
    `/login` ne redirige automatiquement que SANS `bounce` (sinon boucle
    infinie de redirects quand un token est vraiment mort).
14. Pas de dépendances hors : `starlette`, `uvicorn`, `mcp`, graphify lui-même.
    Frontend vanilla JS, zéro build, zéro CDN bloquant (Sora self-hosted,
    Satoshi via CDN avec fallback).

## 4. Architecture cible (arborescence)

```
saas/
  auth.py        SQLite : users, sessions, workspaces(+plan), members,
                 api_keys, usage, daily, invites ; PLANS au-dessus des
                 dataclasses ; AuthError/LimitExceeded ; méthodes signup,
                 login, create_session, workspaces_for, create_workspace,
                 members, invites*, usage, daily_series, meter, check_api_quota
  server.py      app Starlette : principal()/require()/require_role(),
                 routes /api/*, middlewares [AccessLog, Revalidate, CORS],
                 _page() (thème + ?v=), safe_graph_path(), SSE /api/events,
                 MCP supervisor, main() avec --graph --host --port --demo --no-mcp
  registry.py    GRAPHS : LRU + fingerprint + preload/peek/evict
  graph_store.py chargement/découpage de graph.json (top/focus/community,
                 search, explain, path, query budgeté)
  theme.py       4 palettes → /theme.css + /api/theme
  selftest.py    driver ASGI (contrainte 12)
  static/        index.html (shell), app.js, app.css, site.js (login/signup),
                 auth.html, invite.html, landing.html, store.js, fonts.css
data/            état runtime GITIGNORE (app.db, graphs téléversés)
```

## 5. Contrat d'API (surface minimale)

Public : `GET /api/health` (dont `demo_login`), `/api/theme`, `/theme.css`,
`/static/*`, pages `/ /login /signup /app /invite`.
Auth : `POST /api/auth/{signup,login,logout,demo}`, `GET /api/auth/me`.
Workspaces : `GET/POST /api/workspaces`, `POST /api/workspaces/upload`
(FormData, jailed, mesuré), `GET /api/stats`, `/api/god-nodes`,
`/api/communities`, `/api/search`, `/api/explain`, `/api/path`, `/api/query`,
`/api/graph?mode=top|focus|community&limit=`, `/api/ide-config?host=`.
Admin : `GET /api/members` + `DELETE /api/members/{id}`, `GET/POST /api/invites`
+ `DELETE /api/invites/{id}` + `POST /api/invites/accept` + public
`GET /api/invites/lookup?token=`, `GET /api/usage` (plan, usage, history,
counts, **daily**), `POST /api/billing/plan`, `GET/POST /api/keys` +
`DELETE /api/keys/{id}`, `GET /api/events` (SSE : `hello`, `graph` au touch).
MCP : `POST /mcp` (clés `gf_…` + `X-Workspace`).
Règles : substitution cross-tenant = **403 fail-loud** (jamais de swap
silencieux) ; `/api/members` GET-only (collision de route paramétrée).

## 6. Spécification frontend

- **Shell** : topbar = [pliage] [logo Grafik + pill workspace] [sélecteur de
  workspace + nœuds/arêtes] [recherche globale avec dropdown] [swatches de
  thèmes] [Clés] [Connecter l'IDE] [déconnexion] ; sidebar **pliable** en rail
  d'icônes (état persisté), sections Espace de travail / Interroger /
  Administration / Compte.
- **Aperçu (dashboard)** : « Vos dépôts indexés » = 1 carte par workspace avec
  miniature canvas (tranche top-110, layout déterministe hashé), badge
  « ✓ Indexé », méta nœuds/arêtes/plan, clic = switch ; boutons « Afficher
  tout » (wrap) et « Graphique combiné » (fusion des tranches, couleur par
  workspace, légende ad hoc). Puis « Statistiques de l'espace de travail » :
  badges (indexés, total nœuds, quota restant), 2 bar charts journaliers
  hachurés (API, MCP) sur la série `daily`, panneau activité du mois,
  « Densité du graphe » classée. Enfin les stats du workspace actif
  (relations, confiance, fichiers, plus connectés).
- **Graphe** : canvas maison (zoom molette, pan, clic = inspecteur, double-clic
  = focus), légende communautés cliquable ; PAS de graph.html au-delà de
  5 000 nœuds.
- **Vues** : communautés, nœuds centraux, requêtes & chemins (query/path/
  explain), IDE & API (configs vscode/cursor/claude/windsurf/codex + création
  de clé montrée une fois), facturation & usage (plans, barres de quota,
  historique), équipe (membres, invitations liées à une adresse, 7 j),
  profil & clés (attach par chemin serveur OU upload).
- **Live** : `EventSource('/api/events?token=…', {withCredentials:true})` ;
  événement `graph` → refresh stats/graphe/communautés + toast.
- Numéros en `fr-FR`, compact K/M pour le dashboard.

## 7. Phases & critères d'acceptation

1. **Fondation** — venv, boot sur un `graph.json`, `/api/health`, thèmes.
   ✔ health 200 ; pages 200 ; log de boot lisible.
2. **Auth & multi-tenant** — signup/login/logout/me, sessions hashées,
   workspaces+roles, clés API hashées (clair montré une fois).
   ✔ matrice curl : me 200 via header/query/cookie, 401 anon ; cross-tenant 403.
3. **Metering & plans** — usage/daily, quota 402, `POST /api/billing/plan`.
   ✔ un appel metered incrémente usage ET daily ; quota tempéré → 402.
4. **Self-serve & équipes** — upload jailed+validé+mesuré, invites lifecycle.
   ✔ lookup→signup→accept→member role ; member 403 sur routes owner.
5. **App web** — shell pliable, canvas, vues, recherche, switcher, thèmes.
   ✔ navigation sans rechargement ; slice bornée ; inspecteur peuplé.
6. **Dashboard** — cartes+miniatures, charts daily, densité, combiné.
   ✔ miniature dessinée par workspace ; combiné merge sans race (setData vide
   avant show('graph')).
7. **Robustesse preview** — store.js, `?token=`, `#token=`, no-cache+`?v=`,
   bounce guard, bouton démo one-click (`--demo`).
   ✔ login→/app→me/events 200 SANS header ni cookie ; aucun bounce en 2 s.
8. **SSE & MCP** — events par workspace, supervisor lifespan, metering MCP.
   ✔ `hello` puis `graph` au touch ; outils MCP répondent avec clé `gf_…`.
9. **Marque & landing** — Grafik (logo, favicon, titres), landing complète,
   login/signup/invite réels, UI française.
   ✔ aucun « graphify » comme marque produit hors mentions moteur.
10. **QA & livraison** — selftest vert, matrice auth rejouée, commit + push par
    phase, message explicite.

## 8. Pièges rencontrés (à relire avant de coder)

- dict retourné par un handler = 500 silencieuse (contrainte 1).
- `require()` qui exige un workspace sur `/api/workspaces` = compte neuf bloqué.
- cache heuristique d'iframe = vieux JS contre HTML neuf → bounce infini.
- `pkill -f "saas.server"` tue son propre shell ; utiliser stop_process/`ss -ltnp`.
- un vieux process survit au resume → `address already in use`.
- ordre des blocs dans auth.py : PLANS AVANT les dataclasses ; `LimitExceeded`
  après `AuthError` ; `_best_plan(a, user_id: str)` pas `(a, user)`.
- ETag insuffisant derrière un proxy : préférer no-cache franc.
- npm `satoshi` = lib Bitcoin ; `@fontsource/satoshi` n'existe pas → CDN.
- `PosixPath not callable` : ne pas nommer une route comme un import (`path`).
- fragments d'URL : jamais envoyés au serveur → handoff purement client.
- sandbox/ré-clone possible : pousser CHAQUE commit sur la branche de travail ;
  `.venv`, `graphify-out/`, `data/` ne survivent pas → script de reconstruction
  (venv + `graphify extract . --code-only --out .`).

## 9. Definition of done (global)

- `python -m saas.selftest` : all green.
- Matrice auth : 3 canaux 200 + anon 401 sur `/api/auth/me`, `/api/stats`,
  `/api/events`.
- Parcours navigateur embedded-preview : login → /app → pas de bounce, dashboard
  peuplé, sidebar pliable persistée, combiné dessiné.
- Logs d'accès montrant chaque échec ≥ 400 (chemin sans query).
- Un commit par phase, poussé ; `data/`, `.venv/`, `graphify-out/` gitignorés.

## 10. Méthode & style

- Identifiants et code en anglais ; textes UI en français ; commits en anglais.
- Aucun artefact généré dans Git ; état runtime sous `data/` ignoré.
- Commenter le POURQUOI des contraintes (ce fichier est la mémoire des bugs).
- En cas de doute entre « joli » et « robuste en iframe » : robuste.
