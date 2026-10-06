"""Mini kit d'interface pour reconstituer les écrans EducBest (rendu 2x)."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

S = 2  # facteur d'échelle (rendu 992x2160 pour 496x1080 logiques)
W, H = 496, 1080

FONTS = _os.environ.get("EDUCBEST_FONTS", _os.path.join(_ROOT, "polices"))

BLUE = (75, 110, 190)
BLUE_D = (31, 58, 102)
BLUE_L = (232, 239, 250)
BLUE_T = (58, 94, 178)
BG = (244, 246, 250)
WHITE = (255, 255, 255)
INK = (27, 42, 74)
GREY = (112, 122, 139)
GREY_L = (150, 158, 172)
LINE = (227, 232, 240)
GREEN = (28, 122, 74)
GREEN_D = (22, 96, 58)
GREEN_L = (228, 243, 234)
BEIGE = (242, 239, 233)
RED = (205, 45, 45)
PURPLE = (166, 75, 196)
BLACK = (17, 20, 28)


def font(weight: int = 400, size: int = 14, title: bool = False):
    fam = "Sora" if title else "SpaceGrotesk"
    return ImageFont.truetype(f"{FONTS}/{fam}-{weight}.ttf", int(size * S))


def canvas(bg=BG):
    im = Image.new("RGB", (W * S, H * S), bg)
    return im, ImageDraw.Draw(im)


def sc(box):
    return [int(v * S) for v in box]


def rrect(d, box, radius=12, fill=None, outline=None, width=1):
    d.rounded_rectangle(sc(box), radius=int(radius * S), fill=fill, outline=outline,
                        width=int(width * S))


def rect(d, box, fill=None, outline=None, width=1):
    d.rectangle(sc(box), fill=fill, outline=outline, width=int(width * S))


def circle(d, cx, cy, r, fill=None, outline=None, width=1):
    d.ellipse(sc([cx - r, cy - r, cx + r, cy + r]), fill=fill, outline=outline,
              width=int(width * S))


def line(d, p1, p2, fill=LINE, width=1):
    d.line(sc([p1[0], p1[1], p2[0], p2[1]]), fill=fill, width=int(width * S))


def text(d, xy, s, f, fill=INK, anchor="la"):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)


def tw(d, s, f) -> float:
    return d.textlength(s, font=f) / S


def center_text(d, cx, y, s, f, fill=INK):
    text(d, (cx - tw(d, s, f) / 2, y), s, f, fill)


def wrap_text(d, s, f, max_w):
    out, cur = [], ""
    for word in s.split():
        t = f"{cur} {word}".strip()
        if tw(d, t, f) <= max_w:
            cur = t
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- icônes
def ico(d, kind, cx, cy, r=9, color=GREY, w=1.6):
    """Pictogrammes simplifiés, dessinés au trait."""
    if kind == "bell":
        d.arc(sc([cx - r * .7, cy - r * .9, cx + r * .7, cy + r * .5]), 180, 360, fill=color, width=int(w * S))
        line(d, (cx - r * .7, cy + r * .1), (cx - r * .7, cy + r * .45), color, w)
        line(d, (cx + r * .7, cy + r * .1), (cx + r * .7, cy + r * .45), color, w)
        line(d, (cx - r * .95, cy + r * .45), (cx + r * .95, cy + r * .45), color, w)
        d.arc(sc([cx - r * .28, cy + r * .4, cx + r * .28, cy + r * .95]), 0, 180, fill=color, width=int(w * S))
    elif kind == "chev-left":
        line(d, (cx + r * .35, cy - r * .6), (cx - r * .3, cy), color, w * 1.2)
        line(d, (cx - r * .3, cy), (cx + r * .35, cy + r * .6), color, w * 1.2)
    elif kind == "chev-right":
        line(d, (cx - r * .3, cy - r * .6), (cx + r * .35, cy), color, w * 1.2)
        line(d, (cx + r * .35, cy), (cx - r * .3, cy + r * .6), color, w * 1.2)
    elif kind == "chev-down":
        line(d, (cx - r * .55, cy - r * .25), (cx, cy + r * .35), color, w * 1.2)
        line(d, (cx, cy + r * .35), (cx + r * .55, cy - r * .25), color, w * 1.2)
    elif kind == "chev-up":
        line(d, (cx - r * .55, cy + r * .25), (cx, cy - r * .35), color, w * 1.2)
        line(d, (cx, cy - r * .35), (cx + r * .55, cy + r * .25), color, w * 1.2)
    elif kind == "menu":
        for k in (-1, 0, 1):
            line(d, (cx - r * .8, cy + k * r * .55), (cx + r * .8, cy + k * r * .55), color, w * 1.25)
    elif kind == "person":
        circle(d, cx, cy - r * .28, r * .34, outline=color, width=w)
        d.arc(sc([cx - r * .66, cy + r * .05, cx + r * .66, cy + r * 1.1]), 180, 360, fill=color, width=int(w * S))
    elif kind == "people":
        circle(d, cx - r * .34, cy - r * .3, r * .3, fill=color)
        circle(d, cx + r * .36, cy - r * .3, r * .3, fill=color)
        d.arc(sc([cx - r * .95, cy + r * .02, cx + r * .2, cy + r * 1.0]), 180, 360, fill=color, width=int(w * S))
        d.arc(sc([cx - r * .1, cy + r * .02, cx + r * 1.0, cy + r * 1.0]), 180, 360, fill=color, width=int(w * S))
    elif kind == "lock":
        rrect(d, [cx - r * .6, cy - r * .1, cx + r * .6, cy + r * .72], 2.5, outline=color, width=w)
        d.arc(sc([cx - r * .38, cy - r * .72, cx + r * .38, cy + r * .18]), 180, 360, fill=color, width=int(w * S))
    elif kind == "key":
        circle(d, cx - r * .38, cy, r * .36, outline=color, width=w)
        line(d, (cx - r * .05, cy), (cx + r * .75, cy), color, w)
        line(d, (cx + r * .55, cy), (cx + r * .55, cy + r * .35), color, w)
        line(d, (cx + r * .75, cy), (cx + r * .75, cy + r * .3), color, w)
    elif kind == "check":
        line(d, (cx - r * .45, cy + r * .05), (cx - r * .1, cy + r * .42), color, w * 1.3)
        line(d, (cx - r * .1, cy + r * .42), (cx + r * .5, cy - r * .4), color, w * 1.3)
    elif kind == "check-circle":
        circle(d, cx, cy, r * .85, outline=color, width=w)
        line(d, (cx - r * .38, cy + r * .02), (cx - r * .08, cy + r * .33), color, w * 1.2)
        line(d, (cx - r * .08, cy + r * .33), (cx + r * .42, cy - r * .34), color, w * 1.2)
    elif kind == "eye-off":
        d.arc(sc([cx - r * .85, cy - r * .55, cx + r * .85, cy + r * .55]), 200, 340, fill=color, width=int(w * S))
        d.arc(sc([cx - r * .85, cy - r * .35, cx + r * .85, cy + r * .75]), 20, 160, fill=color, width=int(w * S))
        line(d, (cx - r * .8, cy + r * .7), (cx + r * .8, cy - r * .7), color, w * 1.2)
    elif kind == "cap":  # chapeau de diplômé
        d.polygon([(int((cx - r * .9) * S), int(cy * S)), (int(cx * S), int((cy - r * .5) * S)),
                   (int((cx + r * .9) * S), int(cy * S)), (int(cx * S), int((cy + r * .5) * S))], fill=color)
        line(d, (cx + r * .55, cy + r * .18), (cx + r * .55, cy + r * .7), color, w)
    elif kind == "book":
        rrect(d, [cx - r * .8, cy - r * .62, cx - r * .04, cy + r * .62], 1.5, outline=color, width=w)
        rrect(d, [cx + r * .04, cy - r * .62, cx + r * .8, cy + r * .62], 1.5, outline=color, width=w)
    elif kind == "calendar":
        rrect(d, [cx - r * .75, cy - r * .6, cx + r * .75, cy + r * .72], 2.5, outline=color, width=w)
        line(d, (cx - r * .75, cy - r * .2), (cx + r * .75, cy - r * .2), color, w)
        line(d, (cx - r * .38, cy - r * .85), (cx - r * .38, cy - r * .45), color, w)
        line(d, (cx + r * .38, cy - r * .85), (cx + r * .38, cy - r * .45), color, w)
    elif kind == "clock":
        circle(d, cx, cy, r * .78, outline=color, width=w)
        line(d, (cx, cy - r * .42), (cx, cy), color, w)
        line(d, (cx, cy), (cx + r * .34, cy + r * .16), color, w)
    elif kind == "pin":
        d.ellipse(sc([cx - r * .55, cy - r * .8, cx + r * .55, cy + r * .3]), fill=color)
        d.polygon([(int((cx - r * .33) * S), int((cy + r * .1) * S)),
                   (int((cx + r * .33) * S), int((cy + r * .1) * S)),
                   (int(cx * S), int((cy + r * .95) * S))], fill=color)
        circle(d, cx, cy - r * .3, r * .2, fill=WHITE)
    elif kind == "printer":
        rrect(d, [cx - r * .5, cy - r * .85, cx + r * .5, cy - r * .35], 1.5, outline=color, width=w)
        rrect(d, [cx - r * .85, cy - r * .35, cx + r * .85, cy + r * .35], 2, outline=color, width=w)
        rrect(d, [cx - r * .5, cy + r * .2, cx + r * .5, cy + r * .9], 1.5, outline=color, width=w)
    elif kind == "refresh":
        d.arc(sc([cx - r * .75, cy - r * .75, cx + r * .75, cy + r * .75]), 40, 330, fill=color, width=int(w * S))
        d.polygon([(int((cx + r * .35) * S), int((cy - r * .95) * S)),
                   (int((cx + r * .95) * S), int((cy - r * .5) * S)),
                   (int((cx + r * .3) * S), int((cy - r * .25) * S))], fill=color)
    elif kind == "shield":
        d.polygon([(int((cx - r * .7) * S), int((cy - r * .7) * S)),
                   (int((cx + r * .7) * S), int((cy - r * .7) * S)),
                   (int((cx + r * .7) * S), int((cy + r * .15) * S)),
                   (int(cx * S), int((cy + r * .95) * S)),
                   (int((cx - r * .7) * S), int((cy + r * .15) * S))], outline=color, width=int(w * S))
    elif kind in ("download", "upload"):
        s = 1 if kind == "download" else -1
        line(d, (cx, cy - r * .75 * s), (cx, cy + r * .45 * s), color, w)
        line(d, (cx - r * .4, cy + r * .05 * s), (cx, cy + r * .45 * s), color, w)
        line(d, (cx + r * .4, cy + r * .05 * s), (cx, cy + r * .45 * s), color, w)
        line(d, (cx - r * .7, cy + r * .8), (cx + r * .7, cy + r * .8), color, w)
    elif kind == "send":
        d.polygon([(int((cx - r * .8) * S), int((cy - r * .55) * S)),
                   (int((cx + r * .85) * S), int(cy * S)),
                   (int((cx - r * .8) * S), int((cy + r * .55) * S)),
                   (int((cx - r * .5) * S), int(cy * S))], fill=color)
    elif kind == "edit":
        line(d, (cx - r * .6, cy + r * .55), (cx + r * .55, cy - r * .6), color, w * 1.4)
        line(d, (cx - r * .75, cy + r * .75), (cx - r * .55, cy + r * .5), color, w)
    elif kind == "chart":
        for i, hh in enumerate((.35, .75, .55)):
            x = cx - r * .5 + i * r * .5
            line(d, (x, cy + r * .6), (x, cy + r * .6 - r * hh), color, w * 1.5)
    elif kind == "card":
        rrect(d, [cx - r * .85, cy - r * .6, cx + r * .85, cy + r * .6], 2, outline=color, width=w)
        line(d, (cx - r * .55, cy + r * .2), (cx + r * .3, cy + r * .2), color, w)
        circle(d, cx - r * .4, cy - r * .2, r * .22, outline=color, width=w)
    elif kind == "phone":
        rrect(d, [cx - r * .45, cy - r * .8, cx + r * .45, cy + r * .8], 2.5, outline=color, width=w)
        line(d, (cx - r * .15, cy + r * .55), (cx + r * .15, cy + r * .55), color, w)
    elif kind == "at":
        circle(d, cx, cy, r * .75, outline=color, width=w)
        circle(d, cx, cy, r * .3, outline=color, width=w)
    elif kind == "home":
        d.polygon([(int((cx - r * .8) * S), int(cy * S)), (int(cx * S), int((cy - r * .8) * S)),
                   (int((cx + r * .8) * S), int(cy * S))], fill=color)
        rect(d, [cx - r * .55, cy, cx + r * .55, cy + r * .7], fill=color)
    elif kind == "star":
        pts = []
        import math
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = r * .85 if i % 2 == 0 else r * .36
            pts.append((int((cx + rad * math.cos(ang)) * S), int((cy + rad * math.sin(ang)) * S)))
        d.polygon(pts, fill=color)
    elif kind == "baby":
        circle(d, cx, cy, r * .8, outline=color, width=w)
        circle(d, cx - r * .28, cy - r * .12, r * .09, fill=color)
        circle(d, cx + r * .28, cy - r * .12, r * .09, fill=color)
        d.arc(sc([cx - r * .35, cy - r * .05, cx + r * .35, cy + r * .5]), 0, 180, fill=color, width=int(w * S))
    elif kind == "bank":
        line(d, (cx - r * .85, cy + r * .75), (cx + r * .85, cy + r * .75), color, w * 1.3)
        for k in (-.55, 0, .55):
            line(d, (cx + r * k, cy - r * .2), (cx + r * k, cy + r * .6), color, w)
        d.polygon([(int((cx - r * .95) * S), int((cy - r * .3) * S)), (int(cx * S), int((cy - r * .85) * S)),
                   (int((cx + r * .95) * S), int((cy - r * .3) * S))], fill=color)
    elif kind == "flag":
        line(d, (cx - r * .5, cy - r * .8), (cx - r * .5, cy + r * .8), color, w)
        d.polygon([(int((cx - r * .5) * S), int((cy - r * .8) * S)),
                   (int((cx + r * .7) * S), int((cy - r * .45) * S)),
                   (int((cx - r * .5) * S), int((cy - r * .1) * S))], fill=color)


# ------------------------------------------------------- éléments d'écran
def status_bar(d, time_str="11:30", dark_bg=True, locate=False):
    fg = WHITE if dark_bg else BLACK
    f = font(600, 13)
    text(d, (24, 20), time_str, f, fg)
    if locate:
        ico(d, "send", 62, 27, 6, (90, 160, 255), 1.2)
    rrect(d, [W / 2 - 55, 12, W / 2 + 55, 44], 16, fill=BLACK)
    for i in range(4):
        circle(d, 352 + i * 7, 28, 1.6, fill=fg)
    for i, rr in enumerate((4, 7, 10)):
        d.arc(sc([396 - rr, 32 - rr, 396 + rr, 32 + rr]), 200, 340, fill=fg, width=int(1.6 * S))
    rrect(d, [420, 20, 452, 36], 5, outline=fg, width=1.4)
    rrect(d, [422, 22, 446, 34], 3, fill=fg)


def app_bar(d, title, left="chev-left", bell=True, h=138, color=BLUE, locate=False, time_str="11:30"):
    rect(d, [0, 0, W, h], fill=color)
    status_bar(d, time_str, dark_bg=True, locate=locate)
    cy = 88
    if left == "menu":
        ico(d, "menu", 36, cy, 11, WHITE, 1.8)
    elif left == "chev-circle":
        circle(d, 36, cy, 17, fill=(255, 255, 255, 40), outline=None)
        circle(d, 36, cy, 17, fill=(92, 125, 200))
        ico(d, "chev-left", 36, cy, 10, WHITE, 1.8)
    elif left:
        ico(d, "chev-left", 34, cy, 11, WHITE, 2)
    text(d, (76 if left else 24, cy - 11), title, font(600, 17), WHITE)
    if bell:
        ico(d, "bell", 462, cy, 11, WHITE, 1.7)
    return h


def bottom_nav(d, items, active=0, parent=False):
    y0 = H - 92
    rrect(d, [16, y0, W - 16, H - 24], 32, fill=BLUE)
    n = len(items)
    step = (W - 60) / n
    for i, (label, icon) in enumerate(items):
        cx = 30 + step * (i + .5)
        if i == active:
            circle(d, cx, y0 + 26, 15, fill=BLUE_D)
        ico(d, icon, cx, y0 + 26, 9, WHITE, 1.6)
        center_text(d, cx, y0 + 42, label, font(500, 9.5), WHITE)
        if i == active:
            circle(d, cx, y0 + 60, 2, fill=WHITE)


def card(d, box, radius=14, fill=WHITE, outline=None, shadow=True):
    if shadow:
        rrect(d, [box[0] + 1, box[1] + 2, box[2] + 1, box[3] + 3], radius, fill=(236, 239, 245))
    rrect(d, box, radius, fill=fill, outline=outline, width=1.2 if outline else 1)


def button(d, box, label, fill=BLUE, fg=WHITE, icon=None, radius=14, outline=None, size=14):
    rrect(d, box, radius, fill=fill, outline=outline, width=1.4 if outline else 1)
    cx = (box[0] + box[2]) / 2
    cy = (box[1] + box[3]) / 2
    f = font(600, size)
    lw = tw(d, label, f)
    x = cx - lw / 2
    if icon:
        x += 13
        ico(d, icon, x - 22, cy, 9, fg, 1.6)
    text(d, (x, cy - size * .72), label, f, fg)


def pill(d, x, y, label, fill=BLUE_L, fg=BLUE_T, size=9.5, pad=11, h=22, dot=None, icon=None):
    f = font(700, size)
    w = tw(d, label, f) + pad * 2 + (12 if dot or icon else 0)
    rrect(d, [x, y, x + w, y + h], h / 2, fill=fill)
    tx = x + pad
    if dot:
        circle(d, x + pad + 2, y + h / 2, 3.2, fill=dot)
        tx += 12
    if icon:
        ico(d, icon, x + pad + 3, y + h / 2, 6, fg, 1.3)
        tx += 12
    text(d, (tx, y + h / 2 - size * .72), label, f, fg)
    return w


def select(d, box, label, value, icon=None, border=BLUE, label_bg=WHITE, fill=(246, 248, 251)):
    """Champ de sélection avec libellé flottant."""
    rrect(d, box, 12, fill=fill, outline=border, width=1.3)
    f_lab = font(500, 9.5)
    lw = tw(d, label, f_lab)
    rect(d, [box[0] + 14, box[1] - 6, box[0] + 22 + lw, box[1] + 6], fill=label_bg)
    text(d, (box[0] + 18, box[1] - 6), label, f_lab, BLUE_T)
    cy = (box[1] + box[3]) / 2
    x = box[0] + 16
    if icon:
        ico(d, icon, x + 8, cy, 9, BLUE_D, 1.5)
        x += 26
    text(d, (x, cy - 9), value, font(500, 13), INK)
    ico(d, "chev-down", box[2] - 20, cy, 8, GREY, 1.6)


def input_row(d, box, placeholder, icon, trailing="eye-off", fg=BLUE_T):
    rrect(d, box, 12, fill=(248, 250, 252), outline=LINE, width=1.1)
    cy = (box[1] + box[3]) / 2
    ico(d, icon, box[0] + 22, cy, 9, BLUE_T, 1.6)
    text(d, (box[0] + 42, cy - 8), placeholder, font(500, 12.5), fg)
    if trailing:
        ico(d, trailing, box[2] - 24, cy, 9, (110, 118, 132), 1.5)
