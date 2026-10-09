# graphify — ce que c'est, ce qu'il fait, comment il le fait

> Description technique et produit du moteur `graphify` (repo `thekiller-dev/graphify`,
> version 0.9.77, licences Apache-2.0 + MIT, Python 3.10+). La couche SaaS construite
> dessus dans ce repo s'appelle **Grafik** (`saas/`).

## En une phrase

graphify transforme n'importe quelle base de code — et ses docs, PDF, images,
audio/vidéo — en un **graphe de connaissances interrogeable**, construit **en local,
de façon déterministe, sans embeddings, sans vector store et sans aucun crédit LLM**
pour le code.

## Le problème qu'il résout

- « Qu'est-ce qui dépend de ce module ? », « pourquoi ce code existe ? » : aucune
  réponse directe dans un repo, seulement du grep et de la lecture de fichiers.
- Pour un assistant IA, relire les sources à chaque question coûte des tokens et
  rate les liens inter-fichiers ; pour un humain qui arrive, la carte mentale met
  des semaines.
- graphify répond en **une traversée de graphe** au lieu de relire les fichiers.

## Ce qu'il fait

| Capacité | Ce qu'on obtient |
|---|---|
| Cartographie du code | nœuds (fonctions, classes, fichiers, concepts) et arêtes typées `calls`, `imports`, `inherits`, `mixes_in`, `references`… résolues **entre fichiers**, sur ~40 langages via 37 grammaires tree-sitter |
| Confiance par arête | chaque arête est taguée `EXTRACTED` (explicite dans la source), `INFERRED` (résolue par graphify) ou `AMBIGUOUS` (à revoir) — rien n'est caché |
| Rationale | les commentaires `# NOTE:` / `# WHY:` et les références ADR/RFC deviennent des nœuds de premier ordre, liés au code qu'ils expliquent |
| Au-delà du code | docs, `.docx/.xlsx`, PDF, images, audio/vidéo entrent dans le même graphe (passe sémantique optionnelle, seulement si un backend est configuré) |
| Communautés | découpage en sous-systèmes par clustering **Leiden**, avec hubs et échantillons — sans LLM |
| God nodes | les concepts les plus connectés : là où tout passe (abstraction centrale… ou hub à découper) |
| Query / path / explain | poser une question (sous-graphe ciblé, budget de tokens), tracer le chemin le plus court entre deux symboles, expliquer un nœud avec toutes ses connexions |
| Revue de PR | `list_prs`, `get_pr_impact`, `triage_prs` : file de revue classée par impact réel sur le graphe |
| Exports | rapport `GRAPH_REPORT.md`, wiki, vault Obsidian, push Neo4j, HTML |
| Diffusion | CLI, serveur **MCP** (stdio et HTTP), API JSON, mode `--watch`, skill `/graphify` installable dans 18+ assistants (Claude, Cursor, VS Code, Windsurf, Codex…) |
| Local-first | le code est parsé sur la machine, rien ne sort ; **0 crédit LLM** pour construire le graphe |

## Comment il le fait (le pipeline)

1. **Détection & manifeste** (`detect.py`, `manifest.py`, `.graphifyignore`) —
   sélection des fichiers éligibles et empreinte de contenu : un fichier inchangé
   n'est jamais re-parsé.
2. **Extraction structurelle** (`extract.py`, `extractors/`) — AST tree-sitter par
   langage → dictionnaires nœuds/arêtes ; résolution symbolique inter-fichiers
   (`symbol_resolution.py`, `interface_dispatch.py`, résolveurs par langage :
   dispatch C#/Swift/Ruby, Pascal, etc.) ; déduplication (`dedup.py`, MinHash).
   Déterministe : mêmes sources → même graphe, aucune arête hallucinée.
3. **Ingestion non-code** (`ingest.py`, `transcribe.py`, `mcp_ingest.py`,
   `scip_ingest.py`, `google_workspace.py`) — docs, PDF, office, médias, configs
   MCP, manifests de paquets (`pyproject.toml`, `go.mod`, `pom.xml` → un nœud
   package canonique + arêtes `depends_on`). La passe LLM (`llm.py`) n'intervient
   que sur ces sources, et seulement si un backend est configuré.
4. **Clustering** (`cluster.py`) — Leiden (graspologic/networkx) sur le graphe
   stabilisé → communautés = sous-systèmes.
5. **Analyse** (`analyze.py`) — filtrage du bruit (types stdlib, mocks, symboles
   framework), god nodes, connexions surprenantes, stats par communauté.
6. **Persistance & exports** (`build.py`, `export.py`, `exporters/`, `report.py`,
   `wiki.py`) — `graphify-out/graph.json` + analyse + rapport + exports.
7. **Service** (`serve.py`, `watch.py`, `cache.py`) — outils MCP et `query` /
   `path` / `explain` servis depuis `graph.json` ; rebuild incrémental en
   `--watch` ; cache LRU borné invalidé par empreinte (50 tenants ≠ 50 graphes en
   RAM côté serveur).

Choix de design qui expliquent les chiffres : AST déterministe (reproductible),
confiance explicite par arête (auditable), zéro embedding (pas de dérive
sémantique, pas de coût), graphe borné et découpé côté serveur (passage à
l'échelle), local-first (privacy).

## Chiffres & benchmarks (même harness, juge aveugle validé : 90,6 % d'accord, κ = 0,81)

| Benchmark | Métrique | graphify | Terrain |
|---|---|---|---|
| LOCOMO (n=300) | recall@10 | **0,497** | mem0 0,048 · supermemory 0,149 |
| LOCOMO (n=300) | QA accuracy | 45,3 % | supermemory 49,7 % · mem0 27,3 % |
| LongMemEval-S (n=50) | QA accuracy | **76 %** | à égalité avec le RAG dense |
| ERPNext (n=6) | couverture des faits clés | **82,0 %** | baseline grep/lecture 70,8 % |
| Construction du graphe | crédits LLM | **0** | par-token chez la plupart |

Et en pratique : **71,5×** moins de tokens sur un corpus de 52 fichiers (5,4× sur
4 fichiers), AST **1,66×** plus vite avec le pool de processus, un repo cartographié
en **26 s**.

## S'y mettre en 30 secondes

```bash
uv tool install graphifyy      # ou: pipx install graphifyy
graphify install               # skill /graphify dans votre assistant
/graphify .                    # dans l'assistant : cartographie le projet

graphify query "what connects auth to the db?"
graphify path  "UserService" "DatabasePool"
graphify explain "RateLimiter"
python -m graphify.serve graphify-out/graph.json --transport http   # MCP HTTP
```

## Et Grafik dans tout ça

**Grafik** (dossier `saas/` de ce repo) est la couche hosted au-dessus de ce moteur :
auth multi-tenant, workspaces par dépôt, plans & quota, téléversement self-serve,
équipes & invitations, usage facturable, app web (dashboard, explorateur canvas,
requêtes) et endpoints REST + MCP périmétrés par workspace — le moteur, lui, reste
inchangé et open source.
