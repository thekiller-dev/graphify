"""
Reconstitution haute définition des 15 écrans EducBest — espace PARENT
(992 x 2160 px, soit 496 x 1080 logiques).

Même principe que recreate_shots.py (côté professeur) : tant que les captures
originales ne sont pas déposées dans captures-parents-originales/, ce module
génère des reconstitutions fidèles, ainsi que la position exacte des repères
numérotés utilisés dans le guide (fractions de l'image).
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw

from ui_kit import *  # noqa: F403
from ui_kit import _ROOT  # noqa: E402

OUT = os.path.join(_ROOT, "captures-parents")
HOTSPOTS: dict[str, list[list]] = {}

ORANGE = (214, 124, 56)
ORANGE_L = (253, 237, 224)
YELLOW = (190, 150, 30)
YELLOW_L = (253, 245, 219)
PINK = (203, 62, 112)
PINK_L = (253, 228, 236)
TEAL = (46, 160, 110)
CARD_L = (248, 249, 252)
CARD_B = (234, 238, 245)
NAVY = (27, 42, 74)


def save(im, key, spots=None):
    os.makedirs(OUT, exist_ok=True)
    im.save(f"{OUT}/{key}.png")
    if spots:
        HOTSPOTS[key] = [[round(x / W, 4), round(y / H, 4), lab] for x, y, lab in spots]
    return f"{OUT}/{key}.png"


# ---------------------------------------------------------------- icônes +
def ico2(d, kind, cx, cy, r=9, color=GREY, w=1.6):
    """Pictogrammes complémentaires (délègue à ui_kit.ico pour les autres)."""
    if kind == "grid":
        for dx in (-1, 1):
            for dy in (-1, 1):
                rrect(d, [cx + dx * r * .62 - r * .34, cy + dy * r * .62 - r * .34,
                          cx + dx * r * .62 + r * .34, cy + dy * r * .62 + r * .34], 1.8, fill=color)
    elif kind == "headset":
        d.arc(sc([cx - r * .85, cy - r * .9, cx + r * .85, cy + r * .6]), 180, 360,
              fill=color, width=int(w * S))
        rrect(d, [cx - r * .95, cy - r * .18, cx - r * .45, cy + r * .6], 2, fill=color)
        rrect(d, [cx + r * .45, cy - r * .18, cx + r * .95, cy + r * .6], 2, fill=color)
    elif kind == "file":
        rrect(d, [cx - r * .62, cy - r * .85, cx + r * .62, cy + r * .85], 2, outline=color, width=w)
        for k in (-.3, 0, .3):
            line(d, (cx - r * .32, cy + r * k), (cx + r * .32, cy + r * k), color, w * .9)
    elif kind == "file-plus":
        rrect(d, [cx - r * .62, cy - r * .85, cx + r * .62, cy + r * .85], 2, outline=color, width=w)
        line(d, (cx, cy - r * .3), (cx, cy + r * .4), color, w)
        line(d, (cx - r * .35, cy + r * .05), (cx + r * .35, cy + r * .05), color, w)
    elif kind == "chat":
        rrect(d, [cx - r * .85, cy - r * .7, cx + r * .85, cy + r * .45], 4, outline=color, width=w)
        d.polygon([(int((cx - r * .45) * S), int((cy + r * .4) * S)),
                   (int((cx - r * .05) * S), int((cy + r * .4) * S)),
                   (int((cx - r * .45) * S), int((cy + r * .95) * S))], fill=color)
    elif kind == "cutlery":
        line(d, (cx - r * .45, cy - r * .8), (cx - r * .45, cy + r * .85), color, w)
        line(d, (cx - r * .72, cy - r * .8), (cx - r * .72, cy - r * .2), color, w)
        line(d, (cx - r * .18, cy - r * .8), (cx - r * .18, cy - r * .2), color, w)
        d.arc(sc([cx + r * .1, cy - r * .85, cx + r * .8, cy + r * .15]), 0, 360,
              fill=color, width=int(w * S))
        line(d, (cx + r * .45, cy + r * .05), (cx + r * .45, cy + r * .85), color, w)
    elif kind == "info":
        circle(d, cx, cy, r * .85, outline=color, width=w)
        circle(d, cx, cy - r * .4, r * .1, fill=color)
        line(d, (cx, cy - r * .1), (cx, cy + r * .45), color, w * 1.2)
    elif kind == "plus":
        line(d, (cx - r * .7, cy), (cx + r * .7, cy), color, w * 1.5)
        line(d, (cx, cy - r * .7), (cx, cy + r * .7), color, w * 1.5)
    elif kind == "list-check":
        rrect(d, [cx - r * .85, cy - r * .8, cx + r * .85, cy + r * .8], 2.5, outline=color, width=w)
        line(d, (cx - r * .5, cy - r * .3), (cx - r * .22, cy - r * .02), color, w)
        line(d, (cx - r * .22, cy - r * .02), (cx + r * .25, cy - r * .5), color, w)
        line(d, (cx - r * .5, cy + r * .42), (cx + r * .5, cy + r * .42), color, w)
    elif kind == "user-plus":
        circle(d, cx - r * .25, cy - r * .3, r * .32, outline=color, width=w)
        d.arc(sc([cx - r * .9, cy + r * .0, cx + r * .4, cy + r * 1.1]), 180, 360,
              fill=color, width=int(w * S))
        line(d, (cx + r * .45, cy - r * .35), (cx + r * .95, cy - r * .35), color, w)
        line(d, (cx + r * .7, cy - r * .6), (cx + r * .7, cy - r * .1), color, w)
    elif kind == "search":
        circle(d, cx - r * .15, cy - r * .15, r * .55, outline=color, width=w)
        line(d, (cx + r * .27, cy + r * .27), (cx + r * .8, cy + r * .8), color, w * 1.2)
    elif kind == "id":
        rrect(d, [cx - r * .85, cy - r * .6, cx + r * .85, cy + r * .6], 2.5, outline=color, width=w)
        circle(d, cx - r * .38, cy - r * .12, r * .22, outline=color, width=w)
        line(d, (cx + r * .05, cy - r * .22), (cx + r * .6, cy - r * .22), color, w * .9)
        line(d, (cx + r * .05, cy + r * .1), (cx + r * .6, cy + r * .1), color, w * .9)
        d.arc(sc([cx - r * .66, cy + r * .05, cx - r * .1, cy + r * .6]), 180, 360,
              fill=color, width=int(w * S))
    elif kind == "box":
        rrect(d, [cx - r * .85, cy - r * .5, cx + r * .85, cy + r * .8], 2, outline=color, width=w)
        line(d, (cx - r * .85, cy - r * .1), (cx + r * .85, cy - r * .1), color, w)
        line(d, (cx, cy - r * .5), (cx, cy - r * .1), color, w)
    else:
        ico(d, kind, cx, cy, r, color, w)


# ------------------------------------------------- éléments « parent »
def pill_right(d, x_right, y, label, fill=BLUE_L, fg=BLUE_T, size=10, pad=11, h=26, icon=None,
               dot=None):
    f = font(700, size)
    w = tw(d, label, f) + pad * 2 + (12 if (icon or dot) else 0)
    return pill(d, x_right - w, y, label, fill=fill, fg=fg, size=size, pad=pad, h=h,
                icon=icon, dot=dot)


def cycle_chip(d, cx=330, cy=86):
    """« Primaire ▾ » au centre de la barre bleue."""
    f = font(600, 13.5)
    label = "Primaire"
    lw = tw(d, label, f)
    total = 22 + lw + 20
    x = cx - total / 2
    ico2(d, "cap", x + 9, cy, 9, (72, 196, 128), 1.6)
    text(d, (x + 24, cy - 9), label, f, WHITE)
    ico2(d, "chev-down", x + 30 + lw, cy + 1, 8, WHITE, 1.7)


def bell_badge(d, cx=452, cy=86, n=2):
    ico2(d, "bell", cx, cy, 11, WHITE, 1.7)
    if n:
        circle(d, cx + 9, cy - 10, 8, fill=(222, 56, 56))
        center_text(d, cx + 9, cy - 16, str(n), font(700, 9), WHITE)


def pbar(d, title="", left="chev-left", h=120, chip=True, badge=2, bell=True,
         center_title=False, time_str="11:23"):
    rect(d, [0, 0, W, h], fill=BLUE)
    status_bar(d, time_str, dark_bg=True)
    cy = 86
    if left == "menu":
        ico2(d, "menu", 36, cy, 11, WHITE, 1.8)
    elif left:
        ico2(d, "chev-left", 34, cy, 11, WHITE, 2)
    if title:
        if center_title:
            center_text(d, W / 2, cy - 10, title, font(600, 16), WHITE)
        else:
            text(d, (76, cy - 11), title, font(600, 16.5), WHITE)
    if chip:
        cycle_chip(d, cx=348 if title else 300, cy=cy)
    if bell:
        bell_badge(d, 452, cy, badge)
    return h


def bottom_nav_parent(d, active=0):
    items = [("Accueil", "home"), ("Enfants", "people"), ("+", "plus"),
             ("Frais", "card"), ("Présence", "check-circle")]
    y0 = H - 92
    rrect(d, [16, y0, W - 16, H - 24], 32, fill=BLUE)
    step = (W - 60) / 5
    for i, (label, icon) in enumerate(items):
        cx = 30 + step * (i + .5)
        if i == 2:
            circle(d, cx, y0 + 24, 20, fill=WHITE)
            ico2(d, "plus", cx, y0 + 24, 10, BLUE, 2)
            center_text(d, cx, y0 + 42, "+", font(500, 9.5), WHITE)
            continue
        if i == active:
            circle(d, cx, y0 + 26, 15, fill=BLUE_D)
        ico2(d, icon, cx, y0 + 26, 9, WHITE, 1.6)
        center_text(d, cx, y0 + 42, label, font(500, 9.5), WHITE)
        if i == active:
            circle(d, cx, y0 + 60, 2, fill=WHITE)


def tile(d, box, icon, icon_bg, icon_fg, title, sub, chevron=False):
    rrect(d, box, 14, fill=(250, 251, 253), outline=CARD_B, width=1.1)
    x, y = box[0] + 16, box[1] + 14
    rrect(d, [x, y, x + 34, y + 34], 10, fill=icon_bg)
    ico2(d, icon, x + 17, y + 17, 9, icon_fg, 1.7)
    text(d, (x, box[1] + 60), title, font(700, 11.5), INK)
    text(d, (x, box[1] + 80), sub, font(400, 9.5), GREY)
    if chevron:
        ico2(d, "chev-right", box[2] - 20, (box[1] + box[3]) / 2, 9, GREY_L, 1.7)


def wide_tile(d, box, icon, icon_bg, icon_fg, title, sub):
    rrect(d, box, 14, fill=(250, 251, 253), outline=CARD_B, width=1.1)
    cy = (box[1] + box[3]) / 2
    rrect(d, [box[0] + 16, cy - 17, box[0] + 50, cy + 17], 10, fill=icon_bg)
    ico2(d, icon, box[0] + 33, cy, 9, icon_fg, 1.7)
    text(d, (box[0] + 64, cy - 18), title, font(700, 11.5), INK)
    text(d, (box[0] + 64, cy + 2), sub, font(400, 9.5), GREY)
    ico2(d, "chev-right", box[2] - 22, cy, 9, GREY_L, 1.7)


def avatar(d, cx, cy, r, kind="blank"):
    """Pastille d'avatar (photo floutée ou initiale)."""
    if kind == "blank":
        circle(d, cx, cy, r, fill=(228, 233, 242))
    elif kind == "photo":
        circle(d, cx, cy, r, fill=(78, 104, 150))
        circle(d, cx, cy - r * .22, r * .34, fill=(196, 160, 128))
        d.chord(sc([cx - r * .72, cy + r * .12, cx + r * .72, cy + r * 1.5]), 180, 360,
                fill=(62, 118, 186))
    elif kind == "dark":
        circle(d, cx, cy, r, fill=(44, 48, 58))
        circle(d, cx, cy - r * .2, r * .32, fill=(30, 33, 40))
        d.chord(sc([cx - r * .7, cy + r * .1, cx + r * .7, cy + r * 1.45]), 180, 360,
                fill=(24, 27, 33))


# ================================================================== 1
def s1_parcours():
    """Écran de choix du parcours (identique côté parent et professeur)."""
    import recreate_shots as rs
    rs.OUT, rs.HOTSPOTS = OUT, HOTSPOTS
    return rs.s1_parcours()


# ================================================================== 2
def s2_connexion():
    im, d = canvas((244, 246, 250))
    status_bar(d, "11:22", dark_bg=False)
    rrect(d, [24, 62, 70, 108], 15, fill=WHITE, outline=(234, 238, 245))
    ico2(d, "chev-left", 47, 85, 10, INK, 2)
    pill_right(d, 472, 71, "PRIMAIRE", fill=(226, 236, 251), fg=BLUE_T, icon="cap", h=30, size=10.5)

    rrect(d, [200, 182, 296, 278], 24, fill=WHITE, outline=(236, 240, 247))
    ico2(d, "cap", 248, 218, 14, BLUE_T, 2)
    center_text(d, 248, 234, "EDUC BEST", font(700, 7.5), BLUE_T)

    center_text(d, 248, 292, "Bienvenue", font(700, 25), BLUE_T)
    center_text(d, 248, 336, "Connectez-vous à votre espace EducBest", font(400, 12), GREY)

    text(d, (24, 366), "Sélectionnez votre profil", font(700, 12), BLUE_T)
    # Profil PARENT sélectionné (c'est le parcours décrit dans ce guide)
    rrect(d, [24, 392, 240, 486], 16, fill=WHITE, outline=(230, 235, 243), width=1.3)
    circle(d, 132, 424, 19, fill=(233, 239, 250))
    ico2(d, "id", 132, 424, 9, BLUE_T, 1.7)
    center_text(d, 132, 450, "Enseignant", font(600, 12.5), BLUE_T)
    rrect(d, [256, 392, 472, 486], 16, fill=BLUE)
    circle(d, 364, 424, 19, fill=(104, 134, 205))
    ico2(d, "people", 364, 424, 9, WHITE, 1.7)
    center_text(d, 364, 450, "Parent", font(700, 12.5), WHITE)

    text(d, (24, 508), "Email ou identifiant", font(700, 11.5), BLUE_T)
    input_row(d, [24, 530, 472, 586], "Ex: jean.dupont@email.com", "at", trailing=None, fg=GREY_L)
    text(d, (24, 606), "Mot de passe", font(700, 11.5), BLUE_T)
    input_row(d, [24, 628, 472, 684], "Votre mot de passe", "lock", trailing="eye-off", fg=GREY_L)

    f = font(600, 11)
    lab = "Mot de passe oublié ?"
    lw = tw(d, lab, f)
    text(d, (472 - lw, 700), lab, f, BLUE_T)
    ico2(d, "key", 472 - lw - 16, 707, 8, BLUE_T, 1.5)

    rrect(d, [24, 736, 472, 800], 16, fill=BLUE)
    fb = font(700, 14.5)
    lb = "Se connecter"
    bw = tw(d, lb, fb)
    text(d, (248 - bw / 2 - 10, 760), lb, fb, WHITE)
    ico2(d, "chev-right", 248 + bw / 2 + 8, 768, 9, WHITE, 2)

    card(d, [24, 824, 472, 912], 16)
    circle(d, 60, 868, 19, fill=(226, 243, 233))
    ico2(d, "headset", 60, 868, 9, (34, 130, 86), 1.7)
    text(d, (94, 846), "Besoin d'aide pour vous connecter ?", font(700, 11.5), BLUE_T)
    text(d, (94, 870), "Assistance : +229 01 41 63 80 78 (Appel & WhatsApp)", font(400, 10), GREY)
    return save(im, "2-connexion-parent",
                [(452, 404, "1"), (44, 558, "2"), (44, 656, "3"), (68, 768, "4")])


# ================================================================== 3
def draw_home(d, time_str="11:23"):
    pbar(d, "", left="menu", h=120, chip=True, badge=2, time_str=time_str)
    text(d, (24, 142), "Lundi 14 septembre", font(400, 11), GREY)
    text(d, (24, 164), "Bonjour, Parent", font(700, 19), INK)
    pill_right(d, 476, 140, "PRIMAIRE", fill=(226, 236, 251), fg=BLUE_T, icon="cap", h=28, size=10)
    text(d, (24, 198), "Tableau de bord de vos enfants en temps réel", font(400, 11), GREY_L)

    card(d, [16, 226, 480, 300], 16)
    rrect(d, [36, 246, 72, 282], 11, fill=(233, 239, 250))
    ico2(d, "calendar", 54, 264, 9, BLUE_T, 1.7)
    text(d, (88, 242), "Année scolaire", font(400, 10), GREY)
    text(d, (88, 262), "Les BEG Primaire · 2025-2026", font(700, 13), INK)
    ico2(d, "chev-down", 452, 266, 9, GREY, 1.8)

    rrect(d, [16, 316, 480, 388], 16, fill=BLUE)
    circle(d, 54, 352, 19, fill=WHITE)
    ico2(d, "plus", 54, 352, 9, BLUE, 2)
    text(d, (88, 330), "Toutes les sections & démarches", font(700, 13), WHITE)
    text(d, (88, 352), "Documents, notes, emploi du temps, calendrier…", font(400, 9.5), (206, 221, 248))
    ico2(d, "chev-right", 456, 352, 9, WHITE, 1.8)

    stats = [("4", "Enfants", "people", (233, 239, 250), BLUE_T),
             ("-", "Moyenne", "chart", (228, 243, 234), (34, 130, 86)),
             ("100%", "Assiduité", "check-circle", (233, 239, 250), BLUE_T),
             ("À jour", "Frais", "card", (253, 240, 222), ORANGE)]
    cw, gap = 107, 11
    for i, (val, lab, icon, bg, fg) in enumerate(stats):
        x = 16 + i * (cw + gap)
        card(d, [x, 404, x + cw, 496], 14)
        circle(d, x + cw / 2, 430, 15, fill=bg)
        ico2(d, icon, x + cw / 2, 430, 8, fg, 1.6)
        center_text(d, x + cw / 2, 448, val, font(700, 14.5), INK)
        center_text(d, x + cw / 2, 470, lab, font(400, 9.5), GREY)

    card(d, [16, 512, 480, 726], 16)
    text(d, (36, 532), "Suivi de l'assiduité", font(700, 13.5), INK)
    pill_right(d, 460, 530, "Global", fill=(240, 242, 246), fg=(110, 118, 132), size=9.5, h=22)
    circle(d, 110, 628, 48, fill=(26, 160, 94))
    circle(d, 110, 628, 25, fill=WHITE)
    line(d, (110, 628), (162, 628), WHITE, 3)
    rows = [("Présences enregistrées", "0 cours", (26, 160, 94)),
            ("Absences constatées", "0 cours", (222, 56, 56)),
            ("Taux de présence", "100%", BLUE)]
    for i, (lab, val, col) in enumerate(rows):
        y = 596 + i * 32
        circle(d, 190, y + 6, 4.5, fill=col)
        text(d, (204, y), lab, font(400, 10.5), GREY)
        fv = font(700, 10.5)
        text(d, (458 - tw(d, val, fv), y), val, fv, INK)

    text(d, (24, 750), "Enfants suivis (4)", font(700, 14), INK)
    f = font(400, 10)
    text(d, (474 - tw(d, "Touchez pour voir le profil", f), 754), "Touchez pour voir le profil", f, GREY)
    card(d, [16, 780, 480, 884], 16)
    avatar(d, 248, 824, 26, "blank")
    center_text(d, 248, 858, "Fabrice DANSOU", font(700, 13), INK)


def s3_accueil():
    im, d = canvas()
    draw_home(d)
    bottom_nav_parent(d, active=0)
    return save(im, "3-accueil-parent",
                [(258, 70, "1"), (120, 236, "2"), (330, 330, "3"), (70, 414, "4"), (52, 1000, "5")])


# ================================================================== 4
def draw_sections(d, time_str="11:23"):
    rect(d, [0, 0, W, 72], fill=NAVY)
    status_bar(d, time_str, dark_bg=True)
    rrect(d, [0, 58, W, H + 60], 26, fill=WHITE)
    rrect(d, [228, 72, 268, 78], 3, fill=(214, 219, 228))

    rrect(d, [20, 96, 60, 136], 12, fill=(233, 239, 250))
    ico2(d, "grid", 40, 116, 9, BLUE_T, 1.7)
    text(d, (72, 96), "Sections & Raccourcis", font(700, 16), BLUE_T)
    text(d, (72, 122), "Accédez rapidement à tous les services", font(400, 10.5), GREY)
    f = font(400, 18)
    text(d, (444, 104), "×", f, (110, 118, 132))
    line(d, (0, 158), (W, 158), (238, 241, 246), 1.2)

    text(d, (24, 178), "DOCUMENTS & DÉMARCHES", font(700, 9.5), GREY_L)
    tile(d, [20, 200, 244, 292], "file-plus", (233, 239, 250), BLUE_T,
         "Demande de document", "Certificats, bulletins…")
    tile(d, [252, 200, 476, 292], "check", (233, 239, 250), BLUE_T,
         "Mes documents", "Suivre et télécharger")
    wide_tile(d, [20, 304, 476, 376], "id", (233, 239, 250), BLUE_T,
              "Statut des inscriptions", "Consulter la validation des dossiers d'inscription")

    text(d, (24, 404), "VIE SCOLAIRE & SUIVI", font(700, 9.5), GREY_L)
    tile(d, [20, 426, 244, 518], "user-plus", (233, 239, 250), BLUE_T,
         "Inscrire un enfant", "Nouvelle inscription")
    tile(d, [252, 426, 476, 518], "star", (228, 243, 234), (26, 140, 92),
         "Notes & Bulletins", "Relevés trimestriels")
    tile(d, [20, 530, 244, 622], "clock", (240, 234, 252), (138, 86, 196),
         "Emploi du temps", "Planning hebdomadaire")
    tile(d, [252, 530, 476, 622], "box", (253, 236, 224), ORANGE,
         "Fournitures", "Listes par classe")
    wide_tile(d, [20, 634, 476, 706], "calendar", (226, 240, 252), (38, 124, 184),
              "Calendrier scolaire", "Vacances, examens et dates importantes")

    text(d, (24, 736), "FINANCES & COMMUNICATION", font(700, 9.5), GREY_L)
    tile(d, [20, 960, 244, 1052], "card", (233, 239, 250), BLUE_T,
         "Paiement de la scolarité", "Frais et reçus")
    tile(d, [252, 960, 476, 1052], "headset", (253, 237, 224), ORANGE,
         "Préoccupation & Aide", "Écrire au support")


def s4_sections():
    im, d = canvas(WHITE)
    draw_sections(d)
    bottom_nav_parent(d, active=0)
    return save(im, "4-sections-et-raccourcis",
                [(132, 206, "1"), (132, 432, "2"), (364, 432, "3"), (132, 640, "4")])


def s10_fournitures():
    """Détail de la feuille Sections : le bloc « Vie scolaire & suivi »."""
    im, d = canvas(WHITE)
    draw_sections(d)
    crop = im.crop((int(10 * S), int(392 * S), int(486 * S), int(716 * S)))
    os.makedirs(OUT, exist_ok=True)
    crop.save(f"{OUT}/10-fournitures-scolaires.png")
    cw, ch = crop.size
    def fx(x):
        return round((x - 10) * S / cw, 4)

    def fy(y):
        return round((y - 392) * S / ch, 4)

    HOTSPOTS["10-fournitures-scolaires"] = [
        [fx(364), fy(574), "1"], [fx(132), fy(574), "2"],
        [fx(364), fy(470), "3"], [fx(430), fy(648), "4"],
    ]
    return f"{OUT}/10-fournitures-scolaires.png"


# ================================================================== 5
def s5_menu():
    im, d = canvas()
    draw_home(d, "11:26")
    bottom_nav_parent(d, active=0)
    im = Image.blend(im, Image.new("RGB", im.size, (18, 28, 52)), 0.42)
    d = ImageDraw.Draw(im)

    DW = 378
    rect(d, [0, 0, DW, 250], fill=BLUE)
    status_bar(d, "11:26", dark_bg=True)
    ico2(d, "cap", 40, 70, 10, (186, 208, 246), 1.6)
    center_text(d, 40, 78, "EDUC BEST", font(700, 5), (186, 208, 246))
    text(d, (316, 62), "×", font(400, 18), WHITE)
    circle(d, 54, 130, 29, fill=(104, 134, 205))
    center_text(d, 54, 116, "D", font(700, 22), WHITE)
    text(d, (98, 112), "DEMO", font(700, 16), WHITE)
    text(d, (98, 136), "Cycle PRIMAIRE", font(400, 10.5), (206, 221, 248))
    w = pill(d, 98, 160, "Parent", fill=(104, 134, 205), fg=WHITE, size=10, h=24, dot=(72, 206, 128))
    ico2(d, "chev-right", 98 + w + 6, 172, 7, (206, 221, 248), 1.6)

    rect(d, [0, 250, DW, H], fill=WHITE)

    def row(y, icon, bg, fg, title, sub, badge=None):
        rrect(d, [20, y, 56, y + 36], 11, fill=bg)
        ico2(d, icon, 38, y + 18, 9, fg, 1.7)
        text(d, (70, y - 1), title, font(700, 12), BLUE_T)
        text(d, (70, y + 20), sub, font(400, 9.5), GREY)
        ico2(d, "chev-right", 352, y + 18, 8, GREY_L, 1.6)
        if badge:
            fb = font(700, 8.5)
            bw2 = tw(d, badge, fb) + 18
            rrect(d, [344 - bw2, y + 2, 344, y + 22], 10, fill=(226, 56, 86))
            center_text(d, 344 - bw2 / 2, y + 7, badge, fb, WHITE)

    row(276, "headset", ORANGE_L, ORANGE, "Préoccupation & Aide", "Écrire au support ou poser une question")
    text(d, (22, 352), "SUIVI PARENT", font(700, 9.5), GREY_L)
    row(378, "edit", YELLOW_L, YELLOW, "Remarques enseignants", "Observations sur vos enfants")
    row(450, "card", PINK_L, PINK, "Abonnez-vous", "Paiement de scolarité", badge="Scolarité")
    row(522, "cutlery", (226, 246, 234), (26, 140, 92), "Cantine scolaire", "Souscriptions repas")
    line(d, (20, 596), (358, 596), (235, 238, 245), 1.2)
    text(d, (22, 616), "INFORMATIONS", font(700, 9.5), GREY_L)
    row(642, "info", (238, 241, 247), (108, 118, 134), "À propos d'EducBest", "Version et vision de la plateforme")
    row(714, "shield", (238, 241, 247), (108, 118, 134), "Confidentialité", "Politique de protection des données")
    line(d, (20, 788), (358, 788), (235, 238, 245), 1.2)
    text(d, (22, 808), "COMPTE & SESSION", font(700, 9.5), GREY_L)

    bottom_nav_parent(d, active=0)
    return save(im, "5-menu-parent",
                [(38, 272, "1"), (38, 374, "2"), (38, 446, "3"), (38, 518, "4")])


# ================================================================== 6
def s6_enfants():
    im, d = canvas()
    pbar(d, "Mes enfants", left="menu", time_str="11:23")
    text(d, (24, 148), "Mes enfants", font(700, 17), INK)
    text(d, (24, 176), "4 enfants inscrits", font(400, 10.5), GREY)
    button(d, [276, 152, 480, 214], "Inscrire un enfant", BLUE, WHITE, icon="user-plus",
           radius=14, size=12)
    rrect(d, [16, 240, 480, 298], 14, fill=WHITE, outline=(230, 235, 243), width=1.2)
    ico2(d, "search", 46, 269, 9, GREY_L, 1.7)
    text(d, (70, 260), "Rechercher...", font(400, 12), GREY_L)

    kids = [("Fabrice DANSOU", "blank"), ("Bill HOUNNOU", "photo"),
            ("Tii ABARA", "dark"), ("Bato Bill", "dark")]
    cw, chh, gap = 228, 178, 8
    for i, (nom, av) in enumerate(kids):
        x = 16 + (i % 2) * (cw + gap)
        y = 320 + (i // 2) * (chh + 14)
        card(d, [x, y, x + cw, y + chh], 16)
        avatar(d, x + cw / 2, y + 48, 29, av)
        center_text(d, x + cw / 2, y + 90, nom, font(700, 12.5), BLUE_T)
        pf = font(700, 9.5)
        pw = tw(d, "CI", pf) + 22
        pill(d, x + cw / 2 - pw / 2, y + 112, "CI", fill=(238, 241, 247), fg=(108, 118, 134), size=9.5, h=20)
        rrect(d, [x + 16, y + 142, x + cw - 16, y + 166], 12, fill=BLUE)
        fb = font(600, 11)
        lb = "Fiche de suivi"
        lw = tw(d, lb, fb)
        text(d, (x + cw / 2 - lw / 2 - 7, y + 147), lb, fb, WHITE)
        ico2(d, "chev-right", x + cw / 2 + lw / 2 + 8, y + 154, 7, WHITE, 1.7)

    bottom_nav_parent(d, active=1)
    return save(im, "6-mes-enfants",
                [(150, 976, "1"), (40, 474, "2")])


# ================================================================== 7
def s7_fiche():
    im, d = canvas()
    pbar(d, "Détails – Fabrice", left="chev-left", time_str="11:23")
    circle(d, 40, 190, 18, fill=BLUE)
    ico2(d, "chev-left", 40, 190, 9, WHITE, 1.9)
    rrect(d, [70, 164, 480, 216], 14, fill=(238, 241, 247))
    rrect(d, [76, 170, 234, 210], 11, fill=WHITE, outline=(228, 233, 242))
    center_text(d, 155, 182, "Emploi", font(700, 12.5), INK)
    center_text(d, 290, 182, "Notes", font(500, 12.5), (116, 125, 142))
    center_text(d, 414, 182, "Remarques", font(500, 12.5), (116, 125, 142))

    rrect(d, [16, 242, 480, 352], 16, fill=BLUE)
    rrect(d, [38, 272, 80, 314], 12, fill=(104, 134, 205))
    ico2(d, "calendar", 59, 293, 10, WHITE, 1.8)
    text(d, (96, 266), "Emploi du temps", font(700, 15), WHITE)
    text(d, (96, 294), "Touchez un jour pour consulter les cours", font(400, 10.5), (206, 221, 248))
    text(d, (96, 314), "prévus.", font(400, 10.5), (206, 221, 248))

    jours = [("Lundi", "3 cours", "10:00 – 19:21"), ("Mardi", "4 cours", "12:00 – 19:30"),
             ("Mercredi", "6 cours", "08:30 – 17:41"), ("Jeudi", "2 cours", "14:00 – 16:00"),
             ("Vendredi", None, None), ("Samedi", None, None)]
    cw, chh, gx, gy = 228, 116, 8, 12
    for i, (jour, n, horaire) in enumerate(jours):
        x = 16 + (i % 2) * (cw + gx)
        y = 372 + (i // 2) * (chh + gy)
        actif = n is not None
        rrect(d, [x, y, x + cw, y + chh], 14, fill=CARD_L if actif else (246, 247, 249),
              outline=CARD_B, width=1.1)
        ico2(d, "calendar", x + 26, y + 26, 9, BLUE_T if actif else GREY_L, 1.7)
        ico2(d, "chev-up", x + cw - 26, y + 26, 9, (120, 130, 146) if actif else GREY_L, 1.7)
        text(d, (x + 18, y + 46), jour, font(700, 15), INK if actif else (90, 99, 115))
        if actif:
            text(d, (x + 18, y + 74), n, font(600, 11.5), BLUE_T)
            text(d, (x + 18, y + 92), horaire, font(400, 10.5), GREY)
        else:
            text(d, (x + 18, y + 74), "Aucun cours", font(400, 11), GREY_L)

    bottom_nav_parent(d, active=1)
    return save(im, "7-fiche-suivi-emploi-du-temps",
                [(76, 166, "3")])


# ================================================================== 8
def s8_inscription():
    im, d = canvas()
    pbar(d, "Statut Inscripti…", left="chev-left", badge=0, time_str="11:25")
    text(d, (24, 148), "Sélectionnez un enfant", font(600, 12), BLUE_T)
    chips = [("Fabrice DANSOU", "blank", True), ("Bill HOUNNOU", "photo", False),
             ("Tii ABARA", "dark", False)]
    for i, (nom, av, sel) in enumerate(chips):
        x = 16 + i * 166
        rrect(d, [x, 176, x + 150, 306], 14, fill=WHITE,
              outline=BLUE if sel else (232, 236, 243), width=1.6 if sel else 1.1)
        avatar(d, x + 75, 226, 28, av)
        center_text(d, x + 75, 262, nom, font(700, 11), BLUE_T)
        center_text(d, x + 75, 282, "CI", font(400, 10), GREY)

    card(d, [16, 326, 480, 884], 16)
    avatar(d, 64, 382, 27, "blank")
    text(d, (108, 360), "Fabrice DANSOU", font(700, 15), INK)
    pill(d, 108, 388, "Validé", fill=(224, 244, 233), fg=(22, 124, 80), size=10, h=24)
    line(d, (36, 432), (460, 432), (235, 238, 245), 1.2)
    text(d, (36, 454), "Informations du dossier", font(700, 12.5), BLUE_T)
    infos = [("Classe demandée", "CI"), ("Matricule", "En cours d'attribution"),
             ("Date de naissance", "2022-09-10"), ("Lieu de naissance", "Cotonou · Bénin"),
             ("Nationalité", "Beninoise")]
    for i, (lab, val) in enumerate(infos):
        y = 492 + i * 34
        text(d, (36, y), lab, font(400, 10.5), GREY)
        text(d, (232, y), val, font(500, 10.5), BLUE_T)
    rrect(d, [36, 686, 460, 742], 10, fill=(253, 236, 238), outline=(248, 214, 219), width=1.1)
    text(d, (54, 706), "Aucune pièce fournie pour ce dossier.", font(400, 10.5), (186, 58, 70))
    button(d, [36, 768, 460, 836], "Payer la scolarité", BLUE, WHITE, icon="card", radius=14, size=13.5)
    return save(im, "8-statut-inscription-paiement",
                [(91, 184, "2"), (190, 400, "3"), (430, 528, "4"), (100, 802, "5")])


# ================================================================== 9
def s9_paiement():
    im, d = canvas()
    pbar(d, "Paiement scol…", left="menu", time_str="11:24")
    for r, col in ((68, (120, 206, 162)), (58, (74, 184, 140)), (46, (44, 166, 124))):
        circle(d, 248, 286, r, fill=col)
    ico2(d, "card", 248, 282, 22, WHITE, 2.6)
    circle(d, 296, 330, 15, fill=(26, 150, 92))
    circle(d, 296, 330, 15, outline=WHITE, width=2)
    ico2(d, "check", 296, 330, 9, WHITE, 1.8)

    center_text(d, 248, 392, "Paiement de la scolarité", font(700, 19), BLUE_T)
    center_text(d, 248, 432, "Choisissez un enfant, l'année et effectuez votre", font(400, 11), GREY)
    center_text(d, 248, 452, "règlement sécurisé.", font(400, 11), GREY)

    card(d, [24, 496, 472, 868], 18)
    select(d, [48, 526, 448, 582], "Sélectionner un enfant", "Sélectionnez...", icon="baby",
           border=(226, 232, 242))
    select(d, [48, 610, 448, 666], "Année scolaire", "Sélectionnez...", icon="calendar",
           border=(226, 232, 242))
    rrect(d, [48, 694, 448, 750], 12, fill=(248, 250, 252), outline=(230, 235, 243), width=1.2)
    ico2(d, "card", 78, 722, 9, BLUE_D, 1.6)
    text(d, (102, 713), "Montant à régler (FCFA)", font(500, 12.5), INK)
    button(d, [48, 776, 448, 838], "Valider le paiement", BLUE, WHITE, icon="card", radius=14, size=13.5)

    bottom_nav_parent(d, active=3)
    return save(im, "9-paiement-scolarite",
                [(372, 554, "2"), (372, 638, "3"), (372, 722, "4"), (120, 807, "5")])


# ================================================================== 11
def s11_document():
    im, d = canvas()
    pbar(d, "Demande de document", left="chev-left", chip=False, bell=False,
         center_title=True, time_str="11:25")
    rrect(d, [24, 244, 472, 364], 16, fill=(92, 124, 196))
    rrect(d, [48, 272, 104, 328], 14, fill=(118, 146, 212))
    ico2(d, "file", 76, 300, 12, WHITE, 1.9)
    text(d, (120, 272), "Démarche administrative", font(400, 10), (212, 224, 248))
    text(d, (120, 292), "Demande de pièce officielle", font(700, 14), WHITE)
    text(d, (120, 320), "Certificats, bulletins, relevés et attestations.", font(400, 10), (206, 219, 245))

    card(d, [24, 388, 472, 768], 18)
    text(d, (48, 412), "Formulaire de demande", font(700, 12.5), INK)
    select(d, [48, 452, 448, 508], "Enfant concerné *", "Sélectionnez votre enfant", icon="baby",
           border=(226, 232, 242))
    select(d, [48, 532, 448, 588], "Année scolaire *", "Sélectionnez d'abord un", icon="calendar",
           border=(226, 232, 242))
    select(d, [48, 612, 448, 668], "Type de document *", "Aucun type disponible", icon="file",
           border=(226, 232, 242))
    button(d, [48, 696, 170, 748], "Réinitialiser", WHITE, (96, 105, 122), radius=12,
           outline=(226, 232, 242), size=11.5)
    button(d, [186, 696, 448, 748], "ENVOYER LA DEMANDE", BLUE, WHITE, icon="send", radius=12, size=11.5)
    return save(im, "11-demande-document",
                [(372, 480, "2"), (372, 560, "3"), (372, 640, "4"), (214, 722, "5")])


# ================================================================== 12
def s12_preoccupations():
    im, d = canvas()
    pbar(d, "Mes préoccupations", left="chev-left", chip=False, bell=False,
         center_title=True, time_str="11:26")
    circle(d, 248, 502, 68, fill=(233, 237, 246))
    ico2(d, "chat", 248, 500, 30, BLUE_T, 2.4)
    center_text(d, 248, 606, "Aucune préoccupation", font(700, 17), INK)
    for i, ln in enumerate(["Vous n'avez pas encore envoyé de préoccupation",
                            "ou réclamation. Touchez le bouton ci-dessous pour",
                            "initier un échange."]):
        center_text(d, 248, 650 + i * 22, ln, font(400, 11), GREY)
    button(d, [122, 736, 374, 800], "Poser une préoccupation", BLUE, WHITE, icon="plus",
           radius=14, size=13)
    rrect(d, [262, 944, 472, 1012], 14, fill=BLUE)
    rrect(d, [284, 968, 308, 992], 6, fill=(118, 146, 212))
    ico2(d, "plus", 296, 980, 7, WHITE, 1.8)
    text(d, (318, 970), "Nouveau message", font(700, 12.5), WHITE)
    return save(im, "12-preoccupations",
                [(140, 768, "2"), (284, 978, "4")])


# ================================================================== 13
def s13_notifications():
    im, d = canvas()
    pbar(d, "Notifications", left="chev-left", chip=False, bell=False,
         center_title=True, time_str="11:24")
    notes = [("Nouveau commentaire disponible",
              ["Un commentaire concernant HOUNNOU", "Bill pour le cours « Français » est", "disponible."],
              "14 Sep 2026 à 10:05"),
             ("Nouveau commentaire disponible",
              ["Un commentaire concernant HOUNNOU", "Bill pour le cours « Français » est", "disponible."],
              "14 Sep 2026 à 10:04"),
             ("Présence confirmée",
              ["Votre enfant Tii ABARA a été noté(e)", "présent(e) au cours de Mathématiques le", "14/09/2026."],
              "14 Sep 2026 à 09:50"),
             ("Présence confirmée",
              ["Votre enfant Bato Bill a été noté(e)", "présent(e) au cours de Mathématiques le", "14/09/2026."],
              "14 Sep 2026 à 09:48")]
    y = 152
    for titre, corps, quand in notes:
        card(d, [16, y, 480, y + 190], 16)
        circle(d, 58, y + 44, 21, fill=(233, 238, 249))
        ico2(d, "bell", 58, y + 44, 10, BLUE_T, 1.7)
        text(d, (96, y + 28), titre, font(700, 12.5), INK)
        for i, ln in enumerate(corps):
            text(d, (96, y + 58 + i * 20), ln, font(400, 10.5), GREY)
        text(d, (96, y + 140), quand, font(400, 9.5), GREY_L)
        y += 206
    bottom_nav_parent(d, active=4)
    return save(im, "13-notifications",
                [(58, 196, "1"), (58, 292, "2"), (58, 608, "3")])


# ================================================================== 14
def s14_presences():
    im, d = canvas()
    pbar(d, "Suivi des prése…", left="menu", time_str="11:24")
    rrect(d, [24, 142, 60, 178], 11, fill=(233, 239, 250))
    ico2(d, "people", 42, 160, 9, BLUE_T, 1.7)
    text(d, (72, 152), "Sélectionnez un enfant", font(600, 12), INK)

    rrect(d, [16, 200, 244, 276], 14, fill=BLUE)
    avatar(d, 56, 238, 22, "blank")
    text(d, (90, 222), "DANSOU Fabrice", font(700, 11.5), WHITE)
    text(d, (90, 244), "CI", font(400, 10), (206, 221, 248))
    rrect(d, [252, 200, 480, 276], 14, fill=WHITE, outline=(230, 235, 243), width=1.2)
    avatar(d, 292, 238, 22, "photo")
    text(d, (326, 222), "HOUNNOU Bill", font(700, 11.5), INK)
    text(d, (326, 244), "CI", font(400, 10), GREY)
    rrect(d, [488, 200, 560, 276], 14, fill=WHITE, outline=(230, 235, 243), width=1.2)

    circle(d, 248, 604, 58, fill=(233, 237, 246))
    ico2(d, "list-check", 248, 604, 26, BLUE_T, 2.2)
    center_text(d, 248, 690, "Aucune présence enregistrée", font(700, 15), BLUE_T)
    center_text(d, 248, 726, "Aucune ligne de présence n'a été saisie pour cet enfant", font(400, 11), GREY)
    center_text(d, 248, 748, "actuellement.", font(400, 11), GREY)
    bottom_nav_parent(d, active=4)
    return save(im, "14-presences-enfant",
                [(130, 208, "2"), (366, 208, "4"), (170, 604, "3")])


# ================================================================== 15
def s15_profil():
    im, d = canvas()
    pbar(d, "Mon Profil", left="chev-left", badge=0, time_str="11:27")
    rect(d, [0, 118, W, 372], fill=BLUE)
    rrect(d, [0, 320, W, 404], 28, fill=BLUE)
    circle(d, 248, 232, 58, fill=(104, 134, 205), outline=WHITE, width=3)
    center_text(d, 248, 214, "JD", font(700, 30), WHITE)
    circle(d, 290, 272, 15, fill=WHITE)
    ico2(d, "edit", 290, 272, 8, BLUE, 1.7)
    center_text(d, 248, 304, "Jean DANSOU", font(700, 17), WHITE)
    center_text(d, 248, 332, "parent@educbest.com", font(400, 11), (208, 222, 248))
    f = font(700, 9.5)
    w1 = tw(d, "PARENT", f) + 34
    w2 = tw(d, "PRIMAIRE", f) + 34
    x0 = 248 - (w1 + w2 + 10) / 2
    pill(d, x0, 356, "PARENT", fill=(104, 134, 205), fg=WHITE, size=9.5, h=24, dot=(72, 206, 128))
    pill(d, x0 + w1 + 10, 356, "PRIMAIRE", fill=(104, 134, 205), fg=WHITE, size=9.5, h=24, icon="cap")

    card(d, [16, 436, 480, 876], 16)
    rrect(d, [40, 458, 76, 494], 11, fill=(233, 239, 250))
    ico2(d, "id", 58, 476, 9, BLUE_T, 1.7)
    text(d, (88, 466), "Informations du compte", font(700, 13), BLUE_T)
    line(d, (40, 514), (456, 514), (235, 238, 245), 1.2)
    rows = [("person", "Nom complet", "Jean DANSOU"), ("at", "Adresse email", "parent@educbest.com"),
            ("phone", "Téléphone", "0197911250"), ("id", "Statut / Rôle", "parent")]
    for i, (icon, lab, val) in enumerate(rows):
        y = 540 + i * 84
        rrect(d, [40, y, 76, y + 36], 11, fill=(240, 243, 249))
        ico2(d, icon, 58, y + 18, 9, (104, 114, 132), 1.6)
        text(d, (92, y - 2), lab, font(400, 9.5), GREY)
        text(d, (92, y + 18), val, font(700, 11.5), INK)
    bottom_nav_parent(d, active=0)
    return save(im, "15-mon-profil",
                [(318, 262, "3"), (58, 548, "2")])


SCREENS = (s1_parcours, s2_connexion, s3_accueil, s4_sections, s5_menu, s6_enfants,
           s7_fiche, s8_inscription, s9_paiement, s10_fournitures, s11_document,
           s12_preoccupations, s13_notifications, s14_presences, s15_profil)


if __name__ == "__main__":
    for fn in SCREENS:
        print("→", fn())
    with open(f"{OUT}/hotspots.json", "w", encoding="utf-8") as fh:
        json.dump(HOTSPOTS, fh, ensure_ascii=False, indent=1)
    print("repères :", list(HOTSPOTS))
