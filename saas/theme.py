"""Design tokens for the graphify app.

Single source of truth for colour: the frontend CSS *and* the graph canvas
palette are both generated from the tables below, so re-branding the product is
one edit here rather than a grep across HTML/JS/CSS.

Each palette is a full token set (surfaces, text ramp, semantic states) plus a
categorical ``series`` used to colour communities in the graph. ``mode`` drives
which text/border ramp the CSS generator picks, so a light theme stays legible
without hand-tuning every token.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Palette:
    id: str
    name: str
    mode: str  # "dark" | "light"
    bg: str
    bg_alt: str
    surface: str
    surface_2: str
    border: str
    border_soft: str
    text: str
    muted: str
    faint: str
    accent: str
    accent_2: str
    accent_text: str  # readable text sitting on top of `accent`
    ok: str
    warn: str
    danger: str
    series: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode,
            "accent": self.accent,
            "accent_2": self.accent_2,
            "bg": self.bg,
            "surface": self.surface,
            "text": self.text,
            "muted": self.muted,
            "series": list(self.series),
        }


MIDNIGHT = Palette(
    id="midnight",
    name="Midnight Indigo",
    mode="dark",
    bg="#0B1020",
    bg_alt="#0E1530",
    surface="#121A2E",
    surface_2="#182241",
    border="#24314F",
    border_soft="#1A2440",
    text="#E8EEFB",
    muted="#93A2C4",
    faint="#5F6E90",
    accent="#6C8CFF",
    accent_2="#22D3EE",
    accent_text="#0B1020",
    ok="#3DDC97",
    warn="#FFB454",
    danger="#FF6B7A",
    series=(
        "#6C8CFF", "#22D3EE", "#3DDC97", "#FFB454", "#FF6B7A", "#C084FC",
        "#F472B6", "#4ADE80", "#FACC15", "#38BDF8", "#FB923C", "#A3E635",
    ),
)

AURORA = Palette(
    id="aurora",
    name="Aurora",
    mode="dark",
    bg="#06120F",
    bg_alt="#08180F",
    surface="#0C1C17",
    surface_2="#12291F",
    border="#1C3A2E",
    border_soft="#14291F",
    text="#E4F5EC",
    muted="#8FBFA9",
    faint="#5A8A75",
    accent="#34D399",
    accent_2="#A3E635",
    accent_text="#04120C",
    ok="#4ADE80",
    warn="#FBBF24",
    danger="#FB7185",
    series=(
        "#34D399", "#A3E635", "#22D3EE", "#FACC15", "#FB7185", "#818CF8",
        "#F472B6", "#2DD4BF", "#FDBA74", "#A78BFA", "#84CC16", "#38BDF8",
    ),
)

SUNSET = Palette(
    id="sunset",
    name="Sunset",
    mode="dark",
    bg="#150B12",
    bg_alt="#1B0F16",
    surface="#1E1119",
    surface_2="#291721",
    border="#3D2130",
    border_soft="#2A1721",
    text="#FBEAF0",
    muted="#C79BAB",
    faint="#8D6474",
    accent="#FB7185",
    accent_2="#F59E0B",
    accent_text="#1A0710",
    ok="#34D399",
    warn="#FBBF24",
    danger="#F43F5E",
    series=(
        "#FB7185", "#F59E0B", "#C084FC", "#38BDF8", "#34D399", "#F472B6",
        "#FACC15", "#818CF8", "#2DD4BF", "#FB923C", "#A3E635", "#E879F9",
    ),
)

DAYLIGHT = Palette(
    id="daylight",
    name="Daylight",
    mode="light",
    bg="#F5F7FC",
    bg_alt="#EEF2FA",
    surface="#FFFFFF",
    surface_2="#F1F4FB",
    border="#DDE3EF",
    border_soft="#E8ECF5",
    text="#0F172A",
    muted="#5A6784",
    faint="#8B96AC",
    accent="#4F46E5",
    accent_2="#0891B2",
    accent_text="#FFFFFF",
    ok="#059669",
    warn="#B45309",
    danger="#DC2626",
    series=(
        "#4F46E5", "#0891B2", "#059669", "#D97706", "#DC2626", "#7C3AED",
        "#DB2777", "#2563EB", "#0D9488", "#CA8A04", "#EA580C", "#65A30D",
    ),
)

PALETTES: dict[str, Palette] = {p.id: p for p in (DAYLIGHT, MIDNIGHT, AURORA, SUNSET)}
# Daylight is the product default: the workspace is read all day next to an
# editor, and a light surface matches VS Code / Linear-style tooling. The dark
# palettes stay one click away in the switcher.
DEFAULT_THEME = "daylight"


def get(theme_id: str | None) -> Palette:
    """Return a palette by id, falling back to the default for unknown ids."""
    return PALETTES.get((theme_id or DEFAULT_THEME).strip().lower(), PALETTES[DEFAULT_THEME])


def theme_css() -> str:
    """Generate the whole stylesheet's token layer, one block per palette.

    The frontend switches theme by setting ``data-theme`` on ``<html>``; every
    palette is already in the document, so switching is instant and offline.
    """
    blocks: list[str] = []
    for pal in PALETTES.values():
        shadow = "0 18px 40px rgba(0,0,0,.45)" if pal.mode == "dark" else "0 14px 34px rgba(15,23,42,.10)"
        blocks.append(
            f"""html[data-theme="{pal.id}"] {{
  --bg: {pal.bg};
  --bg-alt: {pal.bg_alt};
  --surface: {pal.surface};
  --surface-2: {pal.surface_2};
  --border: {pal.border};
  --border-soft: {pal.border_soft};
  --text: {pal.text};
  --muted: {pal.muted};
  --faint: {pal.faint};
  --accent: {pal.accent};
  --accent-2: {pal.accent_2};
  --accent-text: {pal.accent_text};
  --accent-soft: {pal.accent}26;
  --ok: {pal.ok};
  --warn: {pal.warn};
  --danger: {pal.danger};
  --shadow: {shadow};
  --grid: {pal.border_soft};
  color-scheme: {pal.mode};
}}"""
        )
    return "\n\n".join(blocks) + "\n"
