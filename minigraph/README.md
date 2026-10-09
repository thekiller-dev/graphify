# minigraph — lire la construction de graphify en petit

Réimplémentation **pédagogique** du pipeline documenté dans `ARCHITECTURE.md`.
Chaque module reprend le nom et le contrat d'entrée/sortie de la table du doc :

| minigraph | Row ARCHITECTURE.md | Simplification assumée |
|---|---|---|
| `detect.py` | detect(root) → scan summary | extensions `.py`/docs seulement |
| `extract.py` | extract(paths, root=) → {nodes, edges} | `ast` stdlib au lieu de tree-sitter ; 2 passes conservées (structure + résolution inter-fichiers INFERRED) |
| `validate.py` | validate_extraction → list d'erreurs | identique (schema + confiances) |
| `build.py` | build(extractions) → nx.Graph | identique (dedup omise) |
| `cluster.py` | cluster(G) → {cid: [ids]} | modularité gourmande au lieu de Leiden ; 0 = plus grande communauté, comme le doc |
| `analyze.py` | god_nodes / surprising_connections / suggest_questions | heuristiques minimales |
| `report.py` | generate(...) → GRAPH_REPORT.md | même squelette de sections |
| `export.py` | to_json(...) | node-link + communautés, comme graph.json |

Passes 2 et 3 de `docs/how-it-works.md` (whisper, subagents LLM) : absentes à
dessein — la passe 1 suffit à montrer la mécanique, et c'est celle qui est
gratuite et déterministe.

## Lancer

```bash
python -m minigraph.selfdemo saas        # rapport + minigraph-out/graph.json
pytest tests/test_minigraph.py -q
```

Pour produire en vrai : `graphify extract . --code-only` — minigraph est là
pour *comprendre*, graphify pour *construire*.
