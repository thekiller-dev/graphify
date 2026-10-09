"""minigraph — a teaching re-implementation of graphify's documented pipeline.

Every module mirrors one row of ARCHITECTURE.md's module table, with the same
entry-point names, the same extraction schema ({nodes, edges} with
EXTRACTED/INFERRED/AMBIGUOUS confidences) and the same stage order:

    detect() → extract() → build() → cluster() → analyze → report → export

Differences from the real engine are deliberate and listed in minigraph/README.md:
stdlib ``ast`` instead of tree-sitter (Python only), greedy modularity instead
of Leiden, no LLM passes. The point is to *see* the construction, not to compete
with it — for production, import graphify itself.
"""
__version__ = "0.1.0"
