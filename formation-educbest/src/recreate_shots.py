"""
Reconstitution haute définition des 12 écrans EducBest (992 x 2160 px).

Utilisé tant que les captures originales ne sont pas disponibles dans
/home/user/uploads. Chaque écran renvoie aussi la position exacte des repères
numérotés utilisés dans le guide (fractions de l'image).
"""

from __future__ import annotations

import json
import os

from ui_kit import *  # noqa: F403
from ui_kit import _ROOT  # noqa: E402
import os as _os

OUT = _os.path.join(_ROOT, "captures")
HOTSPOTS: dict[str, list[list]] = {}


def save(im, key, spots=None):
    os.makedirs(OUT, exist_ok=True)
    im.save(f"{OUT}/{key}.png")
    if spots:
        HOTSPOTS[key] = [[round(x / W, 4), round(y / H, 4), lab] for x, y, lab in spots]
    return f"{OUT}/{key}.png"


# ---------------------------------------------------------------- 1
def s1_parcours():
    im, d = canvas((245, 247, 250))
    status_bar(d, "11:21", dark_bg=False)
    text(d, (24, 62), "Choisissez votre parcours", font(700, 21), INK)
    text(d, (24, 100), "Sélectionnez l'instance EducBest qui correspond à", font(400, 12.5), GREY)
    text(d, (24, 120), "votre établissement.", font(400, 12.5), GREY)
    cards = [
        ("Maternelle", "baby", ["Suivi des tout-petits,", "présences et communication", "parents."]),
        ("Primaire", "book", ["Notes, cahier de textes", "et scolarité du primaire."]),
        ("Secondaire", "cap", ["Collège et lycée :", "classes, notes, paiements et", "inscriptions."]),
        ("Université", "bank", ["Parcours étudiant,", "enseignants et suivi", "parental."]),
    ]
    cw, ch, gap = 216, 182, 16
    for i, (title, icon, lines) in enumerate(cards):
        col, row = i % 2, i // 2
        x = 24 + col * (cw + gap)
        y = 160 + row * (ch + gap)
        sel = title == "Secondaire"
        card(d, [x, y, x + cw, y + ch], 16, fill=(232, 239, 250) if sel else WHITE,
             outline=BLUE if sel else (238, 241, 246))
        if sel:
            circle(d, x + 46, y + 42, 22, fill=WHITE)
        ico(d, icon, x + 46, y + 42, 13, BLUE, 1.8)
        text(d, (x + 24, y + 78), title, font(700, 16), INK)
        for j, ln in enumerate(lines):
            text(d, (x + 24, y + 108 + j * 18), ln, font(400, 11), GREY)
        if sel:
            spot_card = (x + cw / 2, y + 20)
    button(d, [24, 950, 472, 1012], "Démarrer", BLUE, WHITE, radius=14, size=15)
    return save(im, "1-choix-du-parcours", [(spot_card[0], spot_card[1], "1"), (68, 981, "2")])


# ---------------------------------------------------------------- 2
def s2_accueil():
    im, d = canvas(WHITE)
    rect(d, [0, 0, W, 120], fill=BLUE)
    status_bar(d, "11:28")
    ico(d, "menu", 36, 86, 11, WHITE, 1.8)
    ico(d, "bell", 462, 86, 11, WHITE, 1.7)
    text(d, (24, 146), "Bonjour, Ruby Bowman", font(700, 19), INK)
    text(d, (24, 182), "Ravi de vous retrouver ! Gérez vos classes, notes et", font(400, 12), GREY)
    text(d, (24, 202), "présences", font(400, 12), GREY)
    button(d, [104, 232, 392, 288], "Voir le calendrier scolaire", BLUE, WHITE, icon="calendar", radius=14, size=13.5)
    card(d, [16, 308, 480, 700], 16, fill=WHITE, outline=(238, 241, 246))
    rrect(d, [36, 328, 70, 362], 10, fill=BLUE_L)
    ico(d, "chart", 53, 345, 9, BLUE_T, 1.6)
    text(d, (82, 330), "Effectif des élèves par classe", font(700, 13.5), INK)
    text(d, (82, 350), "1 classe(s) assignée(s)", font(400, 10.5), GREY)
    ico(d, "refresh", 452, 342, 9, BLUE_T, 1.6)
    select(d, [36, 386, 244, 428], "École", "Les BEG Primaire", border=(222, 228, 238), fill=(247, 249, 252))
    select(d, [262, 386, 460, 428], "Année", "2025-2026", border=(222, 228, 238), fill=(247, 249, 252))
    axis = {13: 462, 10: 500, 5: 562, 0: 624}
    for v, y in axis.items():
        text(d, (36, y - 7), str(v), font(400, 10), GREY_L)
        for seg in range(60, 460, 14):
            line(d, (seg, y), (seg + 7, y), (226, 230, 238), 1.2)
    line(d, (58, 624), (460, 624), (214, 219, 228), 1.2)
    rrect(d, [244, 494, 276, 624], 3, fill=PURPLE)
    center_text(d, 260, 634, "CI (CI)", font(400, 10), GREY)
    pill(d, 36, 660, "CI (CI): 10 élève(s)", fill=(250, 234, 252), fg=(126, 48, 150), dot=PURPLE, size=10, h=26)
    bottom_nav(d, [("Accueil", "home"), ("Classes", "book"), ("Notes", "star"),
                   ("Présences", "check-circle"), ("Apprenants", "cap")], active=0)
    return save(im, "2-accueil-enseignant-filtres-ecole-annee",
                [(232, 386, "1"), (448, 386, "2"), (430, 326, "3"), (308, 520, "4")])


# ---------------------------------------------------------------- 3
def s3_liste():
    im, d = canvas()
    app_bar(d, "Élèves de la classe CI", time_str="11:28")
    card(d, [16, 160, 480, 248], 16)
    circle(d, 54, 204, 23, fill=BLUE_L)
    ico(d, "people", 54, 204, 11, BLUE_T, 1.7)
    text(d, (92, 172), "CI", font(700, 19), INK)
    text(d, (92, 202), "5 apprenants • Appuyez pour ouvrir la", font(400, 11.5), GREY)
    text(d, (92, 220), "fiche", font(400, 11.5), GREY)
    noms = [("Fabrice DANSOU", (235, 238, 244)), ("Bill HOUNNOU", (120, 140, 175)),
            ("Tii ABARA", (60, 66, 80)), ("Bato Bill", (60, 66, 80)), ("Miracle HOUNNOU", (205, 210, 220))]
    y = 266
    for nom, av in noms:
        card(d, [16, y, 480, y + 80], 14)
        circle(d, 56, y + 40, 22, fill=av)
        text(d, (94, y + 18), nom, font(700, 14), INK)
        w = pill(d, 94, y + 44, "Non matriculé", fill=(240, 242, 246), fg=(110, 118, 132), size=9)
        pill(d, 94 + w + 8, y + 44, "MASCULIN", fill=(226, 238, 252), fg=BLUE_T, size=9)
        ico(d, "chev-right", 452, y + 40, 9, (150, 158, 172), 1.7)
        y += 92
    return save(im, "3-liste-des-apprenants")


# ---------------------------------------------------------------- 4
def s4_fiche():
    im, d = canvas()
    app_bar(d, "Fiche de l'apprenant", time_str="11:28")
    rrect(d, [16, 158, 480, 306], 18, fill=BLUE_D)
    circle(d, 68, 216, 34, fill=(96, 108, 130), outline=WHITE, width=2)
    text(d, (118, 182), "Fabrice DANSOU", font(700, 17), WHITE)
    ico(d, "cap", 126, 216, 7, (170, 190, 225), 1.3)
    text(d, (140, 208), "CI • Les BEG Primaire", font(400, 11.5), (196, 210, 235))
    ico(d, "flag", 126, 240, 7, (170, 190, 225), 1.3)
    text(d, (140, 232), "4 ans", font(400, 11.5), (196, 210, 235))
    line(d, (36, 262), (460, 262), (70, 96, 140), 1)
    w = pill(d, 36, 274, "Sans matricule", fill=(52, 78, 122), fg=(205, 218, 240), size=9, icon="card")
    pill(d, 36 + w + 10, 274, "MASCULIN", fill=(52, 78, 122), fg=(205, 218, 240), size=9)
    rrect(d, [16, 326, 21, 348], 2, fill=BLUE)
    text(d, (30, 326), "Relevé des notes", font(700, 14.5), INK)
    card(d, [16, 362, 480, 480], 16)
    ico(d, "book", 248, 396, 14, (150, 158, 172), 1.7)
    center_text(d, 248, 416, "Aucune note disponible", font(600, 13.5), INK)
    center_text(d, 248, 440, "Les notes validées apparaîtront automatiquement dans ce", font(400, 10.5), GREY)
    center_text(d, 248, 456, "relevé.", font(400, 10.5), GREY)
    card(d, [16, 496, 480, 1010], 16)
    rrect(d, [36, 516, 70, 550], 10, fill=(240, 242, 247))
    ico(d, "edit", 53, 533, 9, (90, 100, 118), 1.6)
    text(d, (82, 518), "Remarque pour les parents", font(700, 13.5), INK)
    text(d, (82, 538), "Transmettez une observation officielle sur l'élève", font(400, 10), GREY)
    text(d, (36, 578), "Matière concernée", font(500, 11), (70, 80, 98))
    rrect(d, [36, 600, 460, 648], 12, fill=WHITE, outline=(222, 228, 238), width=1.2)
    ico(d, "book", 62, 624, 9, BLUE_T, 1.5)
    text(d, (84, 616), "Choisir un cours...", font(400, 12.5), (130, 138, 152))
    ico(d, "chev-down", 436, 624, 8, GREY, 1.6)
    text(d, (36, 672), "Type d'observation", font(500, 11), (70, 80, 98))
    rrect(d, [36, 694, 460, 742], 12, fill=WHITE, outline=(222, 228, 238), width=1.2)
    ico(d, "send", 62, 718, 8, BLUE_T, 1.4)
    text(d, (84, 710), "Sélectionner le motif...", font(400, 12.5), (130, 138, 152))
    ico(d, "chev-down", 436, 718, 8, GREY, 1.6)
    button(d, [36, 772, 460, 826], "Transmettre la remarque au parent", BLUE_D, WHITE, icon="send", size=13)
    return save(im, "4-fiche-apprenant-remarque")


# ---------------------------------------------------------------- 5
def s5_presence(dim=False):
    im, d = canvas()
    app_bar(d, "Marquer la présence", left="menu", time_str="11:29", locate=True)
    button(d, [16, 158, 480, 214], "Imprimer ma masse horaire", BLUE_D, WHITE, icon="printer", size=13.5)
    select(d, [16, 240, 480, 292], "Sélectionner une classe", "CI — Les BEG Primaire", icon="cap",
           border=BLUE, label_bg=BG, fill=(247, 249, 252))
    card(d, [16, 312, 480, 514], 16)
    text(d, (40, 334), "Confirmer votre présence", font(700, 16), INK)
    ico(d, "pin", 46, 382, 9, (34, 150, 80), 1.6)
    text(d, (66, 373), "Localisation détectée", font(400, 13), (60, 70, 88))
    ico(d, "clock", 46, 420, 9, BLUE_T, 1.6)
    text(d, (66, 411), "Horodatage : 14/9/2026 - 11:29", font(400, 13), (60, 70, 88))
    button(d, [40, 450, 456, 504], "Je débute le cours", BLUE, WHITE, icon="check", size=14)
    bottom_nav(d, [("Accueil", "home"), ("Classes", "book"), ("Notes", "star"),
                   ("Présences", "check-circle"), ("Apprenants", "cap")], active=3)
    return save(im, "5-marquage-presence", [(430, 266, "1"), (226, 379, "2"), (72, 477, "3")])


# ---------------------------------------------------------------- 6
def s6_regles():
    im, d = canvas()
    app_bar(d, "Marquer la présence", time_str="11:31")
    button(d, [16, 158, 480, 214], "Imprimer ma masse horaire", BLUE_D, WHITE, icon="printer", size=13.5)
    button(d, [16, 228, 480, 284], "Historique des présences", (246, 248, 251), (60, 70, 88),
           icon="clock", outline=(222, 228, 238), size=13.5)
    select(d, [16, 310, 480, 362], "Sélectionner une classe", "Choisir la classe", icon="cap",
           border=(200, 208, 222), label_bg=BG, fill=(246, 248, 251))
    # voile sombre
    veil = Image.new("RGBA", im.size, (18, 22, 32, 150))
    im = Image.alpha_composite(im.convert("RGBA"), veil).convert("RGB")
    d = ImageDraw.Draw(im)
    # feuille du bas
    rrect(d, [0, 648, W, H + 40], 26, fill=(248, 248, 252))
    text(d, (28, 676), "NB:", font(700, 17), (20, 24, 34))
    red_lines = [
        "⚠ Attention : Ici, vous notifiez votre présence au",
        "cours en temps réel (géolocalisée), puis vous",
        "marquez les élèves retardataires, absents, et",
        "éventuellement ceux renvoyés pour la scolarité",
        "pendant votre cours.",
    ]
    y = 714
    for i, ln in enumerate(red_lines):
        if i == 0:
            d.polygon([(int(30 * S), int((y + 13) * S)), (int(40 * S), int((y - 2) * S)),
                       (int(50 * S), int((y + 13) * S))], fill=(240, 180, 40))
            text(d, (56, y - 2), ln[2:], font(400, 13), RED)
        else:
            text(d, (28, y - 2), ln, font(400, 13), RED)
        y += 26
    black_lines = [
        "Marquez votre arrivée du début jusqu'à 15 minutes",
        "après, ou ce sera un retard; enregistrez votre",
        "départ dans les 15 dernières minutes; dépasser",
        "ces limites annule le cours et son horaire.",
    ]
    for ln in black_lines:
        text(d, (28, y), ln, font(400, 13), (28, 32, 42))
        y += 26
    button(d, [24, y + 22, 472, y + 82], "D'accord j'ai compris", BLUE, WHITE, size=14)
    return save(im, "6-regles-presence")


# ---------------------------------------------------------------- 7
def s7_matiere():
    im, d = canvas()
    app_bar(d, "Saisie des notes", left="menu", time_str="11:31")
    button(d, [16, 158, 244, 214], "Télécharger modèle", WHITE, (40, 52, 74), icon="download",
           outline=(222, 228, 238), size=12.5)
    button(d, [252, 158, 480, 214], "Importer notes", BLUE_D, WHITE, icon="upload", size=12.5)
    rrect(d, [16, 232, 480, 760], 16, fill=(245, 247, 250))
    text(d, (36, 252), "MATIÈRE & ÉVALUATIONS", font(600, 9.5), (120, 130, 148))
    ico(d, "chev-up", 452, 262, 9, (90, 100, 118), 1.6)
    text(d, (36, 272), "Éducation musicale • 6ème", font(700, 15.5), INK)
    card(d, [32, 310, 464, 388], 13, shadow=False, outline=(230, 234, 242))
    ico(d, "book", 62, 346, 10, GREEN, 1.6)
    text(d, (86, 320), "Matière", font(400, 10), GREY)
    text(d, (86, 338), "Éducation musicale (6ème)", font(600, 13.5), INK)
    text(d, (86, 362), "Les BEG", font(400, 10.5), GREY_L)
    ico(d, "chev-down", 438, 348, 8, GREY, 1.6)
    card(d, [32, 402, 464, 470], 13, shadow=False, outline=(230, 234, 242))
    ico(d, "calendar", 62, 436, 10, GREEN, 1.6)
    text(d, (86, 412), "Trimestre", font(400, 10), GREY)
    text(d, (86, 430), "Trimestre courant (auto)", font(600, 13.5), INK)
    ico(d, "chev-down", 438, 436, 8, GREY, 1.6)
    rows = [("Interrogations", 500, False), ("Devoirs", 566, False), ("Compositions", 632, True)]
    for label, y, disabled in rows:
        text(d, (36, y + 10), label, font(500, 14), (40, 52, 74))
        rrect(d, [330, y, 464, y + 42], 12, fill=WHITE, outline=(230, 234, 242), width=1.1)
        text(d, (348, y + 10), "–", font(500, 15), GREY if not disabled else (205, 210, 220))
        center_text(d, 397, y + 10, "1", font(700, 14), INK)
        text(d, (440, y + 10), "+", font(500, 15), GREY if not disabled else (205, 210, 220))
    x = 108
    for lab, col in (("Interro 1", GREEN_L), ("Devoir 1", GREEN_L), ("Compo 1", GREEN_L)):
        x += pill(d, x, 694, lab, fill=col, fg=(32, 98, 62), size=10.5, h=28) + 10
    button(d, [16, 782, 480, 842], "Vérifier", BLUE, WHITE, icon="check-circle", size=15)
    rrect(d, [16, 856, 480, 900], 10, fill=GREEN_D)
    bottom_nav(d, [("Accueil", "home"), ("Classes", "book"), ("Notes", "star"),
                   ("Présences", "check-circle"), ("Apprenants", "cap")], active=2)
    return save(im, "7-choix-matiere-evaluation",
                [(448, 318, "2"), (448, 410, "2"), (312, 521, "3"), (64, 812, "5")])


# ---------------------------------------------------------------- 8
def s8_tableau():
    im, d = canvas()
    app_bar(d, "Saisie des notes", left="menu", time_str="11:31")
    rrect(d, [16, 146, 480, 176], 12, fill=WHITE, outline=(232, 236, 243))
    text(d, (24, 192), "Entrez les notes pour chaque élève", font(500, 13), BLUE_T)
    rrect(d, [16, 218, 480, 272], 10, fill=GREEN_D)
    rect(d, [16, 252, 480, 272], fill=GREEN_D)
    text(d, (36, 236), "Élève", font(700, 13.5), WHITE)
    for lab, cx in (("I1", 234), ("D1", 324), ("C1", 414)):
        center_text(d, cx, 236, lab, font(700, 13.5), WHITE)
    rows = [("ABIDI", "Camille"), ("AGBIDI", "MARIE"), ("DANSOU", "Pierre"), ("DOSSOU", "Fabrice"),
            ("KAKPO", "Paul"), ("SOSSOU", "Pierre"), ("FIGKO", "gitfii")]
    y = 272
    rect(d, [16, y, 480, y + len(rows) * 66], fill=WHITE)
    for i, (nom, prenom) in enumerate(rows):
        text(d, (36, y + 12), nom, font(700, 13), INK)
        text(d, (36, y + 34), prenom, font(400, 11.5), GREY)
        for cx in (234, 324, 414):
            rrect(d, [cx - 31, y + 16, cx + 31, y + 50], 9, fill=BEIGE, outline=(228, 222, 210), width=1)
        if i < len(rows) - 1:
            line(d, (36, y + 66), (460, y + 66), (235, 238, 244), 1)
        y += 66
    button(d, [16, y + 40, 480, y + 100], "Vérifier", BLUE, WHITE, icon="check-circle", size=15)
    bottom_nav(d, [("Accueil", "home"), ("Classes", "book"), ("Notes", "star"),
                   ("Présences", "check-circle"), ("Apprenants", "cap")], active=2)
    return save(im, "8-tableau-saisie-notes")


# ---------------------------------------------------------------- 9
def s9_calendrier():
    im, d = canvas()
    app_bar(d, "Calendrier Scolaire", left="chev-circle", bell=False, time_str="11:26")
    select(d, [16, 178, 480, 230], "Choisissez une école", "Les BEG Primaire", icon="cap",
           border=BLUE, label_bg=BG, fill=(246, 248, 251))
    card(d, [16, 262, 480, 358], 16)
    ico(d, "calendar", 52, 310, 11, BLUE_T, 1.7)
    text(d, (84, 286), "gfggggggggg", font(700, 15), INK)
    text(d, (84, 314), "Date : 2026-09-03", font(400, 12), GREY)
    return save(im, "9-calendrier-scolaire", [(452, 190, "2"), (452, 276, "3")])


# ---------------------------------------------------------------- 10
def s10_notifs():
    im, d = canvas()
    app_bar(d, "Notifications", bell=False, time_str="11:24")
    items = [
        ("Nouveau commentaire disponible",
         ["Un commentaire concernant HOUNNOU", "Bill pour le cours « Français » est", "disponible."],
         "14 Sep 2026 à 10:05"),
        ("Nouveau commentaire disponible",
         ["Un commentaire concernant HOUNNOU", "Bill pour le cours « Français » est", "disponible."],
         "14 Sep 2026 à 10:04"),
        ("Présence confirmée",
         ["Votre enfant Tii ABARA a été noté(e)", "présent au cours de Mathématiques le", "14/09/2026."],
         "14 Sep 2026 à 09:50"),
        ("Présence confirmée", ["Votre enfant Bato Bill a été noté(e)"], ""),
    ]
    y = 172
    for title, body, date in items:
        h = 172 if date else 110
        card(d, [16, y, 480, y + h], 16)
        circle(d, 60, y + 46, 23, fill=(229, 238, 251))
        ico(d, "bell", 60, y + 46, 10, BLUE_T, 1.6)
        text(d, (98, y + 24), title, font(700, 14), INK)
        for j, ln in enumerate(body):
            text(d, (98, y + 52 + j * 22), ln, font(400, 12), (85, 95, 112))
        if date:
            text(d, (98, y + 128), date, font(400, 10.5), GREY_L)
        y += h + 16
    bottom_nav(d, [("Accueil", "home"), ("Enfants", "people"), ("+", "check"),
                   ("Frais", "card"), ("Présence", "check-circle")], active=4)
    circle(d, 248, H - 66, 24, fill=WHITE)
    line(d, (240, H - 66), (256, H - 66), BLUE, 2.4)
    line(d, (248, H - 74), (248, H - 58), BLUE, 2.4)
    return save(im, "10-notifications")


# ---------------------------------------------------------------- 11
def s11_profil():
    im, d = canvas()
    app_bar(d, "Mon Profil", time_str="11:29")
    rrect(d, [0, 118, W, 500], 30, fill=(60, 95, 176))
    rect(d, [0, 118, W, 200], fill=(60, 95, 176))
    circle(d, 248, 252, 54, fill=(104, 126, 180), outline=WHITE, width=3)
    center_text(d, 248, 232, "WR", font(700, 30), WHITE)
    circle(d, 290, 294, 15, fill=WHITE)
    ico(d, "edit", 290, 294, 8, BLUE, 1.6)
    center_text(d, 248, 326, "Willa Ruby Bowman", font(700, 19), WHITE)
    center_text(d, 248, 358, "enseignant@educbest.com", font(400, 12.5), (205, 218, 240))
    f = font(700, 9.5)
    w1 = tw(d, "ENSEIGNANT", f) + 34
    w2 = tw(d, "PRIMAIRE", f) + 34
    x0 = 248 - (w1 + w2 + 12) / 2
    pill(d, x0, 390, "ENSEIGNANT", fill=(86, 118, 192), fg=WHITE, size=9.5, dot=(46, 196, 120), h=26)
    pill(d, x0 + w1 + 12, 390, "PRIMAIRE", fill=(86, 118, 192), fg=WHITE, size=9.5, icon="cap", h=26)
    card(d, [16, 520, 480, 912], 18)
    rrect(d, [36, 542, 70, 576], 10, fill=BLUE_L)
    ico(d, "card", 53, 559, 9, BLUE_T, 1.5)
    text(d, (82, 548), "Informations du compte", font(700, 14.5), BLUE_T)
    line(d, (36, 592), (460, 592), (233, 237, 244), 1)
    rows = [("person", "Nom complet", "Willa Ruby Bowman"), ("at", "Adresse email", "enseignant@educbest.com"),
            ("phone", "Téléphone", "0196000000"), ("card", "Statut / Rôle", "enseignant")]
    y = 614
    for icon, label, value in rows:
        rrect(d, [36, y, 70, y + 34], 10, fill=(240, 243, 249))
        ico(d, icon, 53, y + 17, 9, BLUE_T, 1.5)
        text(d, (84, y - 2), label, font(400, 10.5), GREY)
        text(d, (84, y + 16), value, font(700, 13.5), INK)
        y += 78
    button(d, [16, 936, 480, 996], "Modifier mes informations", BLUE, WHITE, icon="edit", size=14)
    button(d, [16, 1012, 480, 1072], "Changer de mot de passe", WHITE, BLUE_T, icon="lock",
           outline=(200, 214, 240), size=14)
    return save(im, "11-profil-enseignant")


# ---------------------------------------------------------------- 12
def s12_mdp():
    im, d = canvas()
    app_bar(d, "Modifier le profil", time_str="11:30")
    rrect(d, [20, 162, 476, 258], 14, fill=WHITE, outline=(230, 234, 242))
    ico(d, "person", 136, 196, 9, (110, 118, 132), 1.6)
    center_text(d, 136, 216, "Informations", font(500, 12.5), (95, 104, 120))
    rrect(d, [248, 162, 476, 258], 14, fill=BLUE)
    ico(d, "lock", 362, 196, 9, WHITE, 1.7)
    center_text(d, 362, 216, "Sécurité & Mot de passe", font(700, 12.5), WHITE)
    rrect(d, [20, 286, 476, 392], 14, fill=(234, 241, 253), outline=(214, 228, 248))
    ico(d, "shield", 60, 342, 12, BLUE_T, 1.7)
    text(d, (88, 306), "Sécurisez votre compte", font(700, 14), BLUE_T)
    text(d, (88, 334), "Le nouveau mot de passe doit comporter au minimum", font(400, 11), GREY)
    text(d, (88, 352), "8 caractères.", font(400, 11), GREY)
    card(d, [24, 420, 472, 700], 18)
    input_row(d, [48, 452, 448, 508], "Mot de passe actuel", "key")
    input_row(d, [48, 540, 448, 596], "Nouveau mot de passe", "lock")
    input_row(d, [48, 628, 448, 684], "Confirmer le nouveau mot de pas…", "check-circle")
    button(d, [24, 748, 472, 812], "Mettre à jour le mot de passe", BLUE, WHITE, icon="refresh", size=14.5)
    return save(im, "12-changement-mot-de-passe",
                [(462, 174, "2"), (40, 480, "3"), (40, 568, "4"), (66, 780, "5")])


if __name__ == "__main__":
    for fn in (s1_parcours, s2_accueil, s3_liste, s4_fiche, s5_presence, s6_regles,
               s7_matiere, s8_tableau, s9_calendrier, s10_notifs, s11_profil, s12_mdp):
        print("→", fn())
    with open(f"{OUT}/hotspots.json", "w", encoding="utf-8") as fh:
        json.dump(HOTSPOTS, fh, ensure_ascii=False, indent=1)
    print("repères :", list(HOTSPOTS))
