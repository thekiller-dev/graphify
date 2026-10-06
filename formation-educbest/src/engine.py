"""
Moteur de composition PDF — documents de formation.

Titres : Sora (600/700/800)
Texte  : Space Grotesk (400/500/600/700)

Principe : on empile des blocs (titre, paragraphe, étape, capture, encadré...).
Chaque bloc sait se mesurer (measure) avant de se dessiner (draw), ce qui permet
de gérer proprement les sauts de page et d'éviter les captures orphelines.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

import pymupdf

import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

FONT_DIR = _os.environ.get("EDUCBEST_FONTS", _os.path.join(_ROOT, "polices"))

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------


def hx(code: str) -> tuple[float, float, float]:
    code = code.lstrip("#")
    return tuple(int(code[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


@dataclass
class Theme:
    accent: str = "#1F6FEB"
    accent_soft: str = "#E8F0FE"
    accent_deep: str = "#0B3C8C"
    ink: str = "#10131A"
    body: str = "#333A47"
    muted: str = "#6B7384"
    line: str = "#E3E7EE"
    surface: str = "#F6F8FB"
    white: str = "#FFFFFF"
    ok: str = "#128A5B"
    ok_soft: str = "#E6F5EE"
    warn: str = "#B4541A"
    warn_soft: str = "#FDF0E6"

    def c(self, name: str) -> tuple[float, float, float]:
        return hx(getattr(self, name))


# --------------------------------------------------------------------------
# Polices
# --------------------------------------------------------------------------


class Fonts:
    def __init__(self, font_dir: str = FONT_DIR):
        self.dir = font_dir
        self._cache: dict[str, pymupdf.Font] = {}

    def get(self, name: str) -> pymupdf.Font:
        if name not in self._cache:
            path = os.path.join(self.dir, f"{name}.ttf")
            self._cache[name] = pymupdf.Font(fontfile=path)
        return self._cache[name]

    # raccourcis
    def title(self, weight: int = 700) -> pymupdf.Font:
        return self.get(f"Sora-{weight}")

    def text(self, weight: int = 400) -> pymupdf.Font:
        return self.get(f"SpaceGrotesk-{weight}")


# --------------------------------------------------------------------------
# Utilitaires texte
# --------------------------------------------------------------------------


def wrap(text: str, font: pymupdf.Font, size: float, width: float) -> list[str]:
    """Découpe un texte en lignes qui tiennent dans `width`."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for w in words[1:]:
            trial = f"{cur} {w}"
            if font.text_length(trial, size) <= width:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# Document
# --------------------------------------------------------------------------


@dataclass
class PageSetup:
    width: float = 595.28  # A4 portrait
    height: float = 841.89
    margin_x: float = 52
    margin_top: float = 62
    margin_bottom: float = 58


class Doc:
    def __init__(
        self,
        setup: PageSetup | None = None,
        theme: Theme | None = None,
        fonts: Fonts | None = None,
        footer_label: str = "",
    ):
        self.s = setup or PageSetup()
        self.t = theme or Theme()
        self.f = fonts or Fonts()
        self.footer_label = footer_label
        self.doc = pymupdf.open()
        self.page: pymupdf.Page | None = None
        self.y = 0.0
        self.page_no = 0
        self._cover_pages: set[int] = set()
        self._section_title = ""
        self._page_sections: dict[int, str] = {}
        self.toc_entries: list[tuple[str, str, int]] = []
        self._toc_page: int | None = None

    # -- géométrie -------------------------------------------------------
    @property
    def content_width(self) -> float:
        return self.s.width - 2 * self.s.margin_x

    @property
    def x0(self) -> float:
        return self.s.margin_x

    @property
    def bottom(self) -> float:
        return self.s.height - self.s.margin_bottom

    def space_left(self) -> float:
        return self.bottom - self.y

    # -- pages -----------------------------------------------------------
    def new_page(self, cover: bool = False) -> pymupdf.Page:
        self.page = self.doc.new_page(width=self.s.width, height=self.s.height)
        self.page_no += 1
        if cover:
            self._cover_pages.add(self.page_no)
        else:
            self._page_sections[self.page_no] = self._section_title
        self.y = self.s.margin_top
        return self.page

    def ensure(self, needed: float) -> None:
        if self.page is None or self.space_left() < needed:
            self.new_page()

    def at_page_top(self) -> bool:
        return self.y <= self.s.margin_top + 8

    def _draw_header(self, page: pymupdf.Page, label: str) -> None:
        """Bandeau discret en haut des pages intérieures."""
        if not label:
            return
        tw = pymupdf.TextWriter(page.rect)
        tw.append(
            (self.x0, self.s.margin_top - 26),
            label.upper(),
            font=self.f.text(600),
            fontsize=7.5,
        )
        tw.write_text(page, color=self.t.c("muted"))
        page.draw_line(
            (self.x0, self.s.margin_top - 18),
            (self.s.width - self.x0, self.s.margin_top - 18),
            color=self.t.c("line"),
            width=0.6,
        )

    def finish(self, path: str, title: str = "", author: str = "", bookmarks: bool = True) -> str:
        if title or author:
            self.doc.set_metadata(
                {"title": title, "author": author, "subject": title, "creator": "EducBest"}
            )
        if bookmarks and self.toc_entries:
            toc = [[1, "Couverture", 1]]
            if self._toc_page:
                toc.append([1, "Sommaire", self._toc_page])
            toc += [[1, f"{n}. {t}", p] for n, t, p in self.toc_entries]
            self.doc.set_toc(toc)
        total = self.doc.page_count
        for i, page in enumerate(self.doc, start=1):
            if i in self._cover_pages:
                continue
            self._draw_header(page, self._page_sections.get(i, ""))
            tw = pymupdf.TextWriter(page.rect)
            y = self.s.height - self.s.margin_bottom + 26
            page.draw_line(
                (self.x0, y - 14),
                (self.s.width - self.x0, y - 14),
                color=self.t.c("line"),
                width=0.6,
            )
            if self.footer_label:
                tw.append((self.x0, y), self.footer_label, font=self.f.text(400), fontsize=7.5)
            num = f"{i} / {total}"
            w = self.f.text(600).text_length(num, 7.5)
            tw.append((self.s.width - self.x0 - w, y), num, font=self.f.text(600), fontsize=7.5)
            tw.write_text(page, color=self.t.c("muted"))
        self.doc.subset_fonts()
        self.doc.save(path, garbage=4, deflate=True, clean=True)
        return path

    # -- primitives de dessin -------------------------------------------
    def _text(
        self,
        x: float,
        y: float,
        s: str,
        font: pymupdf.Font,
        size: float,
        color: str = "body",
        page: pymupdf.Page | None = None,
    ) -> None:
        page = page or self.page
        assert page is not None
        tw = pymupdf.TextWriter(page.rect)
        tw.append((x, y), s, font=font, fontsize=size)
        tw.write_text(page, color=self.t.c(color) if isinstance(color, str) else color)

    def rect(
        self,
        r: pymupdf.Rect,
        fill: str | None = None,
        stroke: str | None = None,
        width: float = 0.8,
        radius: float | None = None,
    ) -> None:
        assert self.page is not None
        kw: dict = {}
        if radius:
            kw["radius"] = min(radius / min(r.width, r.height), 0.5) if r.width and r.height else 0
        self.page.draw_rect(
            r,
            color=self.t.c(stroke) if stroke else None,
            fill=self.t.c(fill) if fill else None,
            width=width if stroke else 0,
            **kw,
        )


# --------------------------------------------------------------------------
# Blocs de contenu
# --------------------------------------------------------------------------


class Blocks:
    """Blocs de haut niveau. Chaque méthode avance `doc.y`."""

    def __init__(self, d: Doc):
        self.d = d

    # ---- couverture ---------------------------------------------------
    def cover(
        self,
        kicker: str,
        title_lines: Sequence[str],
        subtitle: str,
        meta: Sequence[tuple[str, str]] = (),
        badge: str = "",
    ) -> None:
        d = self.d
        p = d.new_page(cover=True)
        t = d.t
        # bandeau couleur plein cadre haut
        p.draw_rect(pymupdf.Rect(0, 0, d.s.width, 268), fill=hx(t.accent), width=0)
        # motif discret : cercles concentriques
        for i, rad in enumerate((210, 160, 112)):
            p.draw_circle(
                (d.s.width - 70, 44),
                rad,
                color=hx(t.white),
                width=0.7,
                stroke_opacity=0.18 + 0.05 * i,
            )
        y = 74
        if badge:
            bw = d.f.text(600).text_length(badge, 8.5) + 22
            p.draw_rect(
                pymupdf.Rect(d.x0, y - 11, d.x0 + bw, y + 5),
                fill=hx(t.white),
                width=0,
                radius=0.45,
            )
            d._text(d.x0 + 11, y + 0.5, badge, d.f.text(600), 8.5, color=hx(t.accent_deep), page=p)
            y += 36
        d._text(d.x0, y, kicker.upper(), d.f.text(600), 9.5, color=hx("#D8E6FF"), page=p)
        y += 34
        for line in title_lines:
            d._text(d.x0, y, line, d.f.title(800), 31, color=hx(t.white), page=p)
            y += 38
        y = 316
        for line in wrap(subtitle, d.f.text(400), 11.5, d.content_width * 0.82):
            d._text(d.x0, y, line, d.f.text(400), 11.5, color="body", page=p)
            y += 18
        y += 18
        # cartes méta
        if meta:
            cw = (d.content_width - 12 * (len(meta) - 1)) / len(meta)
            for i, (label, value) in enumerate(meta):
                x = d.x0 + i * (cw + 12)
                r = pymupdf.Rect(x, y, x + cw, y + 62)
                p.draw_rect(r, fill=hx(t.surface), color=hx(t.line), width=0.8, radius=0.14)
                d._text(x + 14, y + 23, label.upper(), d.f.text(600), 7.5, color="muted", page=p)
                for j, ln in enumerate(wrap(value, d.f.text(500), 10, cw - 28)[:2]):
                    d._text(x + 14, y + 41 + j * 13, ln, d.f.text(500), 10, color="ink", page=p)
            y += 86
        d.y = y

    # ---- titres ---------------------------------------------------------
    def section(self, number: str, title: str, lead: str = "", reserve: float = 205,
                new_page: bool = False) -> None:
        """Ouverture de grande partie : pastille numérotée + grand titre Sora.

        `reserve` = place minimale à garder sous le titre pour que le premier
        bloc de contenu reste sur la même page (évite les titres orphelins et
        les trous en bas de page).
        """
        d = self.d
        need = 120 + (34 if lead else 0) + reserve
        if new_page and d.page is not None:
            d.y = d.bottom + 1
        d.ensure(min(need, d.bottom - d.s.margin_top))
        d._section_title = f"{number} · {title}"
        if d.at_page_top():
            d._page_sections[d.page_no] = d._section_title
        d.toc_entries.append((number, title, d.page_no))
        p = d.page
        assert p is not None
        y = d.y + 6
        p.draw_rect(
            pymupdf.Rect(d.x0, y, d.x0 + 34, y + 34), fill=d.t.c("accent"), width=0, radius=0.3
        )
        nw = d.f.title(700).text_length(number, 15)
        d._text(d.x0 + 17 - nw / 2, y + 23, number, d.f.title(700), 15, color=hx(d.t.white))
        tl = wrap(title, d.f.title(700), 21, d.content_width - 50)
        ty = y + 25
        for ln in tl:
            d._text(d.x0 + 50, ty, ln, d.f.title(700), 21, color="ink")
            ty += 27
        y = max(y + 42, ty + 2)
        if lead:
            for ln in wrap(lead, d.f.text(400), 10.5, d.content_width - 50):
                d._text(d.x0 + 50, y + 11, ln, d.f.text(400), 10.5, color="muted")
                y += 15
        y += 10
        p.draw_line((d.x0, y), (d.s.width - d.x0, y), color=d.t.c("line"), width=0.8)
        d.y = y + 20

    def h2(self, title: str, reserve: float = 130) -> None:
        d = self.d
        lines = wrap(title, d.f.title(600), 14.5, d.content_width)
        d.ensure(min(30 + 20 * len(lines) + reserve, d.bottom - d.s.margin_top))
        d.y += 8
        for ln in lines:
            d._text(d.x0, d.y + 13, ln, d.f.title(600), 14.5, color="ink")
            d.y += 20
        d.y += 6

    def h3(self, title: str, reserve: float = 90) -> None:
        d = self.d
        d.ensure(min(34 + reserve, d.bottom - d.s.margin_top))
        d.y += 4
        d._text(d.x0, d.y + 11, title, d.f.text(700), 10.5, color="accent_deep")
        d.y += 18

    # ---- texte -----------------------------------------------------------
    def para(self, text: str, size: float = 10.3, color: str = "body", gap: float = 8) -> None:
        d = self.d
        lh = size * 1.52
        for ln in wrap(text, d.f.text(400), size, d.content_width):
            d.ensure(lh + 4)
            d._text(d.x0, d.y + size, ln, d.f.text(400), size, color=color)
            d.y += lh
        d.y += gap

    def lead(self, text: str) -> None:
        """Phrase d'accroche : plus grande, couleur encre."""
        d = self.d
        size = 11.6
        for ln in wrap(text, d.f.text(500), size, d.content_width):
            d.ensure(size * 1.5 + 4)
            d._text(d.x0, d.y + size, ln, d.f.text(500), size, color="ink")
            d.y += size * 1.5
        d.y += 10

    def bullets(self, items: Sequence[str], size: float = 10.3, bullet: str = "•") -> None:
        d = self.d
        lh = size * 1.5
        for it in items:
            lines = wrap(it, d.f.text(400), size, d.content_width - 18)
            d.ensure(lh * len(lines) + 6)
            d._text(d.x0 + 3, d.y + size, bullet, d.f.text(700), size, color="accent")
            for i, ln in enumerate(lines):
                d._text(d.x0 + 18, d.y + size, ln, d.f.text(400), size, color="body")
                d.y += lh
            d.y += 3
        d.y += 6

    def checklist(self, items: Sequence[str]) -> None:
        d = self.d
        size = 10.3
        for it in items:
            lines = wrap(it, d.f.text(400), size, d.content_width - 26)
            d.ensure(size * 1.5 * len(lines) + 8)
            box = pymupdf.Rect(d.x0 + 1, d.y + 2, d.x0 + 12, d.y + 13)
            d.rect(box, stroke="accent", width=1.0, radius=2.5)
            for ln in lines:
                d._text(d.x0 + 24, d.y + size, ln, d.f.text(400), size, color="body")
                d.y += size * 1.5
            d.y += 5
        d.y += 6

    # ---- étapes ----------------------------------------------------------
    def step(self, number: int | str, title: str, body: str = "", bullets_: Sequence[str] = ()) -> None:
        """Étape numérotée : pastille + titre + corps, avec filet vertical."""
        d = self.d
        size = 10.2
        tl = wrap(title, d.f.text(700), 11.5, d.content_width - 44)
        bl = wrap(body, d.f.text(400), size, d.content_width - 44) if body else []
        bull: list[list[str]] = [wrap(b, d.f.text(400), size, d.content_width - 62) for b in bullets_]
        h = 10 + 17 * len(tl) + 15.5 * len(bl) + sum(15.5 * len(x) + 3 for x in bull) + 12
        d.ensure(min(h, 240))
        top = d.y
        p = d.page
        assert p is not None
        p.draw_circle((d.x0 + 11, top + 11), 11, fill=d.t.c("accent_soft"), width=0)
        n = str(number)
        nw = d.f.text(700).text_length(n, 10)
        d._text(d.x0 + 11 - nw / 2, top + 14.5, n, d.f.text(700), 10, color="accent_deep")
        y = top
        for ln in tl:
            d._text(d.x0 + 32, y + 11.5, ln, d.f.text(700), 11.5, color="ink")
            y += 17
        y += 2
        for ln in bl:
            d._text(d.x0 + 32, y + size, ln, d.f.text(400), size, color="body")
            y += 15.5
        for grp in bull:
            for i, ln in enumerate(grp):
                if i == 0:
                    d._text(d.x0 + 34, y + size, "–", d.f.text(600), size, color="accent")
                d._text(d.x0 + 46, y + size, ln, d.f.text(400), size, color="body")
                y += 15.5
            y += 2
        if y - top > 26:
            p.draw_line(
                (d.x0 + 11, top + 24), (d.x0 + 11, y - 4), color=d.t.c("line"), width=1.1
            )
        d.y = y + 12

    # ---- encadrés --------------------------------------------------------
    def callout(self, kind: str, title: str, text: str) -> None:
        palette = {
            "tip": ("ok_soft", "ok", "ASTUCE"),
            "warn": ("warn_soft", "warn", "ATTENTION"),
            "info": ("accent_soft", "accent_deep", "À SAVOIR"),
        }
        bg, fg, default = palette.get(kind, palette["info"])
        d = self.d
        size = 9.9
        lines = wrap(text, d.f.text(400), size, d.content_width - 36)
        h = 20 + 14 + 15 * len(lines) + 8
        d.ensure(h + 8)
        top = d.y
        r = pymupdf.Rect(d.x0, top, d.s.width - d.x0, top + h)
        d.rect(r, fill=bg, radius=8)
        p = d.page
        assert p is not None
        p.draw_rect(
            pymupdf.Rect(d.x0, top + 4, d.x0 + 3.2, top + h - 4), fill=d.t.c(fg), width=0, radius=0.5
        )
        label = (title or default).upper()
        d._text(d.x0 + 18, top + 19, label, d.f.text(700), 8.2, color=fg)
        y = top + 24
        for ln in lines:
            d._text(d.x0 + 18, y + size, ln, d.f.text(400), size, color="body")
            y += 15
        d.y = top + h + 14

    def keyline(self, left: str, right: str) -> None:
        """Ligne clé : libellé à gauche, valeur à droite, pointillés entre."""
        d = self.d
        d.ensure(22)
        size = 10
        d._text(d.x0, d.y + size, left, d.f.text(500), size, color="body")
        rw = d.f.text(700).text_length(right, size)
        d._text(d.s.width - d.x0 - rw, d.y + size, right, d.f.text(700), size, color="accent_deep")
        d.y += 18

    # ---- captures --------------------------------------------------------

    def _hotspots(self, rect: pymupdf.Rect, spots: Sequence[tuple[float, float, str]]) -> None:
        """Badges numérotés posés sur la capture (x, y en fraction de l'image)."""
        p = self.d.page
        assert p is not None
        d = self.d
        for fx, fy, label in spots:
            cx = rect.x0 + fx * rect.width
            cy = rect.y0 + fy * rect.height
            p.draw_circle((cx, cy), 9.2, fill=hx("#FFFFFF"), width=0)
            p.draw_circle((cx, cy), 8.2, fill=d.t.c("accent"), width=0)
            lw = d.f.text(700).text_length(label, 8.6)
            d._text(cx - lw / 2, cy + 3.1, label, d.f.text(700), 8.6, color=hx(d.t.white))

    def figure(
        self,
        image: str,
        caption: str = "",
        width_ratio: float = 1.0,
        max_h: float = 430,
        badge: str = "",
        hotspots: Sequence[tuple[float, float, str]] = (),
    ) -> None:
        """Capture pleine largeur (ou fraction), encadrée + légende."""
        d = self.d
        pad = 10
        avail_w = d.content_width * width_ratio
        iw, ih = _img_size(image)
        scale = min((avail_w - 2 * pad) / iw, max_h / ih)
        cap_lines = wrap(caption, d.f.text(400), 9, avail_w - 2 * pad) if caption else []
        extra = 2 * pad + (14 * len(cap_lines) + 6 if cap_lines else 0) + 16
        total = ih * scale + extra
        # élastique : plutôt réduire la capture que laisser une demi-page vide
        if d.page is not None and total > d.space_left():
            room = d.space_left() - extra - 2  # marge de sécurité
            if room >= 0.5 * ih * scale and room > 150:
                scale = room / ih
            else:
                d.ensure(total)
        w, h = iw * scale, ih * scale
        d.ensure(h + extra)
        x = d.x0 + (d.content_width - (w + 2 * pad)) / 2
        top = d.y
        frame = pymupdf.Rect(x, top, x + w + 2 * pad, top + h + 2 * pad)
        d.rect(frame, fill="surface", stroke="line", width=0.8, radius=10)
        p = d.page
        assert p is not None
        irect = pymupdf.Rect(x + pad, top + pad, x + pad + w, top + pad + h)
        p.insert_image(irect, filename=image)
        if hotspots:
            self._hotspots(irect, hotspots)
        if badge:
            bw = d.f.text(700).text_length(badge, 8) + 16
            br = pymupdf.Rect(x + 6, top - 7, x + 6 + bw, top + 9)
            d.rect(br, fill="accent", radius=7)
            d._text(x + 14, top + 4, badge, d.f.text(700), 8, color=hx(d.t.white))
        y = frame.y1 + 12
        for ln in cap_lines:
            lw = d.f.text(400).text_length(ln, 9)
            cx = (x + (frame.width - lw) / 2) if width_ratio < 0.95 else (x + 2)
            d._text(cx, y, ln, d.f.text(400), 9, color="muted")
            y += 13
        d.y = y + 10

    def figure_row(
        self,
        items: Sequence[tuple[str, str]],
        max_h: float = 300,
        numbered: bool = True,
        gap: float = 12,
        hotspots: Sequence[Sequence[tuple[float, float, str]]] = (),
    ) -> None:
        """Plusieurs captures côte à côte, numérotées, avec légende sous chacune.

        items : [(chemin_image, légende), ...]
        """
        d = self.d
        n = len(items)
        cw = (d.content_width - gap * (n - 1)) / n
        pad = 7
        # hauteur commune = la plus petite échelle
        scales = []
        for path, _ in items:
            iw, ih = _img_size(path)
            scales.append(min((cw - 2 * pad) / iw, max_h / ih))
        s = min(scales)
        heights = [_img_size(p)[1] * s for p, _ in items]
        frame_h = max(heights) + 2 * pad
        cap_h = 0
        caps = []
        for _, cap in items:
            lines = wrap(cap, d.f.text(400), 8.8, cw - 4) if cap else []
            caps.append(lines)
            cap_h = max(cap_h, 13 * len(lines))
        need = frame_h + cap_h + 40
        if d.page is not None and need > d.space_left():
            room = d.space_left() - cap_h - 42 - 2 * pad  # marge de sécurité
            if room >= 0.5 * (frame_h - 2 * pad) and room > 150:
                s = s * room / (frame_h - 2 * pad)
                heights = [_img_size(p)[1] * s for p, _ in items]
                frame_h = max(heights) + 2 * pad
        d.ensure(frame_h + cap_h + 40)
        top = d.y + 11
        p = d.page
        assert p is not None
        for i, ((path, _cap), lines) in enumerate(zip(items, caps)):
            x = d.x0 + i * (cw + gap)
            iw, ih = _img_size(path)
            w, h = iw * s, ih * s
            fw = min(cw, w + 2 * pad)
            fx = x + (cw - fw) / 2
            fr = pymupdf.Rect(fx, top, fx + fw, top + frame_h)
            d.rect(fr, fill="surface", stroke="line", width=0.8, radius=9)
            ix = fx + (fw - w) / 2
            irect = pymupdf.Rect(ix, top + pad, ix + w, top + pad + h)
            p.insert_image(irect, filename=path)
            if hotspots and i < len(hotspots) and hotspots[i]:
                self._hotspots(irect, hotspots[i])
            if numbered:
                p.draw_circle((fx + 15, top), 10.5, fill=hx("#FFFFFF"), width=0)
                p.draw_circle((fx + 15, top), 9.5, fill=d.t.c("accent"), width=0)
                lab = str(i + 1)
                lw = d.f.text(700).text_length(lab, 9.5)
                d._text(fx + 15 - lw / 2, top + 3.4, lab, d.f.text(700), 9.5, color=hx(d.t.white))
            y = top + frame_h + 13
            for ln in lines:
                lw2 = d.f.text(400).text_length(ln, 8.8)
                d._text(x + (cw - lw2) / 2, y, ln, d.f.text(400), 8.8, color="muted")
                y += 13
        d.y = top + frame_h + cap_h + 26

    def split(
        self,
        image: str,
        title: str,
        steps: Sequence[str],
        image_side: str = "right",
        image_ratio: float = 0.42,
        max_h: float = 420,
        note: str = "",
        hotspots: Sequence[tuple[float, float, str]] = (),
    ) -> None:
        """Deux colonnes : explication d'un côté, capture de l'autre.

        Le format idéal pour les captures de téléphone (hautes et étroites).
        """
        d = self.d
        gap = 18
        img_w = d.content_width * image_ratio
        txt_w = d.content_width - img_w - gap
        pad = 8
        iw, ih = _img_size(image)
        scale = min((img_w - 2 * pad) / iw, max_h / ih)
        w, h = iw * scale, ih * scale
        frame_h = h + 2 * pad
        # mesure colonne texte
        tl = wrap(title, d.f.text(700), 12, txt_w)
        body_lines = [wrap(s, d.f.text(400), 10, txt_w - 26) for s in steps]
        txt_h = 20 * len(tl) + 6 + sum(16 * len(b) + 8 for b in body_lines)
        if note:
            txt_h += 16 * len(wrap(note, d.f.text(500), 9.4, txt_w - 20)) + 18
        need = max(frame_h, txt_h) + 24
        if d.page is not None and need > d.space_left() and txt_h + 24 <= d.space_left():
            room = d.space_left() - 26
            if room >= 0.55 * frame_h and room > 180:
                scale = (room - 2 * pad) / ih
                w, h = iw * scale, ih * scale
                frame_h = h + 2 * pad
                need = max(frame_h, txt_h) + 24
        d.ensure(min(need, d.bottom - d.s.margin_top))
        top = d.y
        p = d.page
        assert p is not None
        if image_side == "right":
            tx, ix = d.x0, d.x0 + txt_w + gap
        else:
            ix, tx = d.x0, d.x0 + img_w + gap
        # capture
        fw = min(img_w, w + 2 * pad)
        fx = ix + (img_w - fw) / 2
        fr = pymupdf.Rect(fx, top, fx + fw, top + frame_h)
        d.rect(fr, fill="surface", stroke="line", width=0.8, radius=10)
        cx = fx + (fw - w) / 2
        irect = pymupdf.Rect(cx, top + pad, cx + w, top + pad + h)
        p.insert_image(irect, filename=image)
        if hotspots:
            self._hotspots(irect, hotspots)
        # texte
        y = top
        for ln in tl:
            d._text(tx, y + 12, ln, d.f.text(700), 12, color="ink")
            y += 20
        y += 6
        for i, lines in enumerate(body_lines, start=1):
            p.draw_circle((tx + 8, y + 7), 8, fill=d.t.c("accent_soft"), width=0)
            lab = str(i)
            lw = d.f.text(700).text_length(lab, 8.5)
            d._text(tx + 8 - lw / 2, y + 10, lab, d.f.text(700), 8.5, color="accent_deep")
            for ln in lines:
                d._text(tx + 26, y + 10, ln, d.f.text(400), 10, color="body")
                y += 16
            y += 8
        if note:
            nl = wrap(note, d.f.text(500), 9.4, txt_w - 20)
            nh = 12 + 14 * len(nl)
            r = pymupdf.Rect(tx, y, tx + txt_w, y + nh)
            d.rect(r, fill="accent_soft", radius=7)
            yy = y + 9
            for ln in nl:
                d._text(tx + 10, yy + 9.4, ln, d.f.text(500), 9.4, color="accent_deep")
                yy += 14
            y += nh
        d.y = top + max(frame_h, y - top) + 22

    def spacer(self, h: float = 10) -> None:
        self.d.y += h

    def rule(self) -> None:
        d = self.d
        d.ensure(16)
        p = d.page
        assert p is not None
        p.draw_line((d.x0, d.y), (d.s.width - d.x0, d.y), color=d.t.c("line"), width=0.7)
        d.y += 16


def _img_size(path: str) -> tuple[int, int]:
    doc = pymupdf.open(path)
    try:
        r = doc[0].rect
        return int(r.width), int(r.height)
    finally:
        doc.close()


# --------------------------------------------------------------------------
# Blocs avancés : tableaux, cartes, sommaire, phases
# --------------------------------------------------------------------------


class Blocks2(Blocks):
    """Blocs supplémentaires (hérite de tous les blocs de base)."""

    # ---- tableau ---------------------------------------------------------
    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        widths: Sequence[float] | None = None,
        size: float = 9.3,
        zebra: bool = True,
    ) -> None:
        d = self.d
        ncol = len(headers)
        widths = list(widths or [1 / ncol] * ncol)
        cw = [w * d.content_width for w in widths]
        pad = 9
        head_h = 26

        def draw_head(top: float) -> float:
            p = d.page
            assert p is not None
            r = pymupdf.Rect(d.x0, top, d.s.width - d.x0, top + head_h)
            d.rect(r, fill="accent_deep", radius=6)
            x = d.x0
            for i, h in enumerate(headers):
                d._text(x + pad, top + 17, h.upper(), d.f.text(700), 8, color=hx(d.t.white))
                x += cw[i]
            return top + head_h

        d.ensure(head_h + 60)
        y = draw_head(d.y)
        for idx, row in enumerate(rows):
            cells = [
                wrap(str(c), d.f.text(500 if i == 0 else 400), size, cw[i] - 2 * pad)
                for i, c in enumerate(row)
            ]
            h = max(len(c) for c in cells) * (size * 1.42) + 14
            if y + h > d.bottom:
                d.y = d.bottom + 1
                d.ensure(head_h + 60)
                y = draw_head(d.y)
            p = d.page
            assert p is not None
            if zebra and idx % 2 == 0:
                d.rect(pymupdf.Rect(d.x0, y, d.s.width - d.x0, y + h), fill="surface")
            x = d.x0
            for i, lines in enumerate(cells):
                ty = y + 7
                for ln in lines:
                    d._text(
                        x + pad,
                        ty + size,
                        ln,
                        d.f.text(600 if i == 0 else 400),
                        size,
                        color="ink" if i == 0 else "body",
                    )
                    ty += size * 1.42
                x += cw[i]
            p.draw_line(
                (d.x0, y + h), (d.s.width - d.x0, y + h), color=d.t.c("line"), width=0.6
            )
            y += h
        d.y = y + 16

    # ---- cartes ----------------------------------------------------------
    def cards(
        self,
        items: Sequence[tuple[str, str]],
        cols: int = 2,
        numbered: bool = False,
        gap: float = 12,
        size: float = 9.5,
    ) -> None:
        d = self.d
        cw = (d.content_width - gap * (cols - 1)) / cols
        pad = 13
        i = 0
        while i < len(items):
            chunk = items[i : i + cols]
            metrics = []
            for title, text in chunk:
                tl = wrap(title, d.f.text(700), 10.2, cw - 2 * pad - (18 if numbered else 0))
                bl = wrap(text, d.f.text(400), size, cw - 2 * pad) if text else []
                metrics.append((tl, bl))
            h = max(
                16 * len(tl) + (6 if bl else 0) + 14 * len(bl) + 2 * pad for tl, bl in metrics
            )
            d.ensure(h + gap + 6)
            top = d.y
            for j, ((title, _), (tl, bl)) in enumerate(zip(chunk, metrics)):
                x = d.x0 + j * (cw + gap)
                r = pymupdf.Rect(x, top, x + cw, top + h)
                d.rect(r, fill="white", stroke="line", width=0.9, radius=10)
                tx = x + pad
                ty = top + pad
                if numbered:
                    p = d.page
                    assert p is not None
                    p.draw_circle((tx + 7, ty + 7), 8.5, fill=d.t.c("accent_soft"), width=0)
                    lab = str(i + j + 1)
                    lw = d.f.text(700).text_length(lab, 8.5)
                    d._text(tx + 7 - lw / 2, ty + 10.5, lab, d.f.text(700), 8.5, color="accent_deep")
                    tx += 22
                for ln in tl:
                    d._text(tx, ty + 10.2, ln, d.f.text(700), 10.2, color="ink")
                    ty += 16
                ty += 4
                for ln in bl:
                    d._text(x + pad, ty + size, ln, d.f.text(400), size, color="body")
                    ty += 14
            d.y = top + h + gap
            i += cols
        d.y += 6

    # ---- phase (journée type) -------------------------------------------
    def phase(self, chip: str, items: Sequence[str]) -> None:
        d = self.d
        size = 10
        lines = [wrap(s, d.f.text(400), size, d.content_width - 150) for s in items]
        h = max(34, sum(15.5 * len(x) for x in lines) + 16)
        d.ensure(h + 10)
        top = d.y
        p = d.page
        assert p is not None
        cw = 118
        d.rect(pymupdf.Rect(d.x0, top, d.x0 + cw, top + h), fill="accent_soft", radius=8)
        chip_lines = wrap(chip, d.f.text(700), 9.2, cw - 18)
        cy = top + h / 2 - (len(chip_lines) * 12) / 2 + 9
        for ln in chip_lines:
            d._text(d.x0 + 11, cy, ln, d.f.text(700), 9.2, color="accent_deep")
            cy += 12
        y = top + 10
        for grp in lines:
            d._text(d.x0 + cw + 14, y + size, "›", d.f.text(700), size, color="accent")
            for ln in grp:
                d._text(d.x0 + cw + 26, y + size, ln, d.f.text(400), size, color="body")
                y += 15.5
        d.y = top + h + 10

    # ---- bandeau « règle d'or » ------------------------------------------
    def golden_rule(self, steps: Sequence[str], title: str = "LA RÈGLE D'OR") -> None:
        d = self.d
        h = 86
        d.ensure(h + 14)
        top = d.y
        p = d.page
        assert p is not None
        d.rect(pymupdf.Rect(d.x0, top, d.s.width - d.x0, top + h), fill="accent_deep", radius=12)
        d._text(d.x0 + 18, top + 22, title, d.f.text(700), 8.2, color=hx("#9DB6E8"))
        n = len(steps)
        avail = d.content_width - 36
        x = d.x0 + 18
        for i, s in enumerate(steps):
            w = d.f.title(700).text_length(s, 12.5)
            d._text(x, top + 56, s, d.f.title(700), 12.5, color=hx(d.t.white))
            x += w
            if i < n - 1:
                gap = max(8.0, (avail - sum(d.f.title(700).text_length(t, 12.5) for t in steps)) / (n - 1))
                d._text(x + gap / 2 - 4, top + 56, "›", d.f.text(400), 12.5, color=hx("#7FA0DE"))
                x += gap
        d.y = top + h + 16

    # ---- sommaire inséré après la couverture -----------------------------
    def insert_toc(self, title: str = "Sommaire", intro: str = "", at: int = 1) -> None:
        """Crée la page de sommaire à la position `at` (0-based) et décale les repères."""
        d = self.d
        entries = list(d.toc_entries)
        d._page_sections = {
            (k if k <= at else k + 1): v for k, v in d._page_sections.items()
        }
        d._cover_pages = {(k if k <= at else k + 1) for k in d._cover_pages}
        entries = [(n, t, (p if p <= at else p + 1)) for n, t, p in entries]
        page = d.doc.new_page(pno=at, width=d.s.width, height=d.s.height)
        d._cover_pages.add(at + 1)  # pas d'en-tête courant sur le sommaire
        tw_y = d.s.margin_top + 10
        d._text(d.x0, tw_y + 24, title, d.f.title(700), 24, color="ink", page=page)
        page.draw_line(
            (d.x0, tw_y + 44), (d.s.width - d.x0, tw_y + 44), color=d.t.c("line"), width=0.8
        )
        y = tw_y + 76
        if intro:
            for ln in wrap(intro, d.f.text(400), 10.3, d.content_width):
                d._text(d.x0, y, ln, d.f.text(400), 10.3, color="muted", page=page)
                y += 16
            y += 14
        for num, ttl, pno in entries:
            d._text(d.x0, y, num, d.f.text(700), 10.5, color="accent", page=page)
            d._text(d.x0 + 30, y, ttl, d.f.text(500), 11, color="ink", page=page)
            label = str(pno)
            lw = d.f.text(600).text_length(label, 10)
            tw_ = d.f.text(500).text_length(ttl, 11)
            dot_start = d.x0 + 36 + tw_
            dot_end = d.s.width - d.x0 - lw - 8
            if dot_end > dot_start:
                page.draw_line(
                    (dot_start, y - 3),
                    (dot_end, y - 3),
                    color=d.t.c("line"),
                    width=0.7,
                    dashes="[0.6 3] 0",
                )
            d._text(d.s.width - d.x0 - lw, y, label, d.f.text(600), 10, color="muted", page=page)
            y += 25
        d.y = y
        d._toc_page = at + 1
        d.toc_entries = entries
