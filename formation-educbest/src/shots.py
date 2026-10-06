"""
Résolution des captures d'écran.

- Si la vraie capture existe dans UPLOADS (ex. uploads/5-marquage-presence.jpeg),
  c'est elle qui est utilisée, en pleine résolution.
- Sinon, un emplacement réservé est généré automatiquement, au bon format
  (même ratio que les captures d'origine), annoté du nom de fichier attendu.

=> Dès que les vraies captures sont disponibles, il suffit de relancer
   `python build_doc.py` : le document se régénère à l'identique avec les images.
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw

import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

UPLOADS = os.environ.get("EDUCBEST_SHOTS", os.path.join(_ROOT, "captures-originales"))
RECREATED = os.path.join(_ROOT, "captures")
FINAL_DIR = os.path.join(_ROOT, "build", "captures-compactees")
PLACEHOLDER_DIR = os.path.join(_ROOT, "build", "emplacements")
EXTS = (".jpeg", ".jpg", ".png", ".JPEG", ".JPG", ".PNG")

W, H = 496, 1080  # format des captures d'origine

BLUE = (70, 104, 180)
DEEP = (30, 58, 102)
SOFT = (232, 238, 249)
GREY = (205, 211, 221)
MUT = (122, 132, 150)
BG = (246, 248, 251)

# Libellé lisible + points à repérer sur chaque écran
CATALOG: dict[str, tuple[str, list[str]]] = {
    "1-choix-du-parcours": ("Choisissez votre parcours", ["Maternelle", "Primaire", "Secondaire", "Université", "Bouton Démarrer"]),
    "2-accueil-enseignant-filtres-ecole-annee": ("Accueil enseignant", ["Sélecteur École", "Sélecteur Année", "Effectifs par classe", "Actualiser", "Barre de menus"]),
    "3-liste-des-apprenants": ("Élèves de la classe", ["Effectif de la classe", "Carte apprenant", "Flèche = ouvrir la fiche"]),
    "4-fiche-apprenant-remarque": ("Fiche de l'apprenant", ["Identité", "Relevé des notes", "Matière concernée", "Type d'observation", "Transmettre au parent"]),
    "5-marquage-presence": ("Marquer la présence", ["Sélectionner une classe", "Localisation détectée", "Horodatage", "Je débute le cours"]),
    "6-regles-presence": ("Règles de présence", ["Encadré NB", "Fenêtre de 15 minutes", "D'accord j'ai compris"]),
    "7-choix-matiere-evaluation": ("Choix matière et évaluation", ["Télécharger modèle", "Importer notes", "Matière", "Trimestre", "Interro / Devoir / Compo"]),
    "8-tableau-saisie-notes": ("Tableau de saisie des notes", ["Colonnes I1 / D1 / C1", "Une ligne par élève", "Bouton Vérifier"]),
    "9-calendrier-scolaire": ("Calendrier scolaire", ["Choisissez une école", "Événement et sa date"]),
    "10-notifications": ("Centre de notifications", ["Nouveau commentaire", "Présence confirmée", "Date et heure"]),
    "11-profil-enseignant": ("Mon profil", ["Identité et rôle", "Informations du compte", "Modifier mes informations", "Changer de mot de passe"]),
    "12-changement-mot-de-passe": ("Sécurité & Mot de passe", ["Onglet Sécurité", "Mot de passe actuel", "Nouveau mot de passe", "Confirmation", "Mettre à jour"]),
}


def _real(key: str) -> str | None:
    for ext in EXTS:
        p = os.path.join(UPLOADS, key + ext)
        if os.path.exists(p):
            return p
    return None


def _placeholder(key: str) -> str:
    os.makedirs(PLACEHOLDER_DIR, exist_ok=True)
    out = os.path.join(PLACEHOLDER_DIR, key + ".png")
    title, points = CATALOG.get(key, (key, []))
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # barre d'application
    d.rectangle([0, 0, W, 26], fill=DEEP)
    d.rectangle([0, 26, W, 112], fill=BLUE)
    d.rounded_rectangle([20, 60, 20 + 9 * len(title), 80], radius=6, fill=(255, 255, 255))
    # zone « capture à insérer »
    d.rounded_rectangle([18, 136, W - 18, H - 120], radius=18, outline=GREY, width=3)
    for i in range(0, 14):  # trame diagonale légère
        d.line([18, 160 + i * 68, W - 18, 110 + i * 68], fill=(233, 236, 242), width=2)
    d.rounded_rectangle([44, 210, W - 44, 268], radius=12, fill=SOFT)
    d.rounded_rectangle([64, 228, 64 + 7 * len("CAPTURE A INSERER"), 244], radius=5, fill=BLUE)
    d.rounded_rectangle([44, 286, W - 44, 318], radius=8, fill=(255, 255, 255), outline=GREY, width=2)
    d.rounded_rectangle([58, 296, 58 + 6 * len(key + ".jpeg"), 308], radius=4, fill=MUT)
    # repères numérotés
    y = 370
    for i, pt in enumerate(points, start=1):
        d.ellipse([48, y, 76, y + 28], fill=BLUE)
        d.rounded_rectangle([92, y + 8, min(W - 50, 92 + 8 * len(pt)), y + 20], radius=5, fill=GREY)
        y += 50
    # barre de navigation
    d.rounded_rectangle([18, H - 92, W - 18, H - 28], radius=26, fill=BLUE)
    for i in range(5):
        x = 60 + i * 94
        d.ellipse([x - 13, H - 72, x + 13, H - 46], fill=(255, 255, 255) if i == 0 else (150, 174, 220))
    im.save(out)
    return out


def _recreated(key: str) -> str | None:
    p = os.path.join(RECREATED, key + ".png")
    return p if os.path.exists(p) else None




# --------------------------------------------------------------------------
# Compactage : on retire les grandes bandes vides des captures pour que le
# contenu utile s'affiche plus grand dans le document (les repères numérotés
# sont repositionnés automatiquement).
# --------------------------------------------------------------------------

_PREPARED: dict[str, tuple[str, list]] = {}


def _collapse_empty_bands(im: Image.Image, min_run: int = 46, keep: int = 14,
                          protect_top: int = 150, protect_bottom: int = 30):
    """Réduit les suites de lignes uniformes. Renvoie (image, fonction y->y')."""
    g = im.convert("RGB")
    w, h = g.size
    px = g.load()
    step = max(1, w // 60)
    uniform = []
    for y in range(h):
        first = px[0, y]
        same = True
        for x in range(0, w, step):
            c = px[x, y]
            if abs(c[0] - first[0]) + abs(c[1] - first[1]) + abs(c[2] - first[2]) > 14:
                same = False
                break
        uniform.append(same)
    for y in range(min(protect_top, h)):
        uniform[y] = False
    for y in range(max(0, h - protect_bottom), h):
        uniform[y] = False
    keep_rows = [True] * h
    y = 0
    while y < h:
        if uniform[y]:
            j = y
            while j < h and uniform[j]:
                j += 1
            run = j - y
            if run > min_run:
                for k in range(y + keep // 2, j - keep // 2):
                    keep_rows[k] = False
            y = j
        else:
            y += 1
    if all(keep_rows):
        return im, (lambda v: v), h
    rows = [y for y in range(h) if keep_rows[y]]
    out = Image.new("RGB", (w, len(rows)))
    for new_y, old_y in enumerate(rows):
        out.paste(im.crop((0, old_y, w, old_y + 1)), (0, new_y))
    prefix = []
    acc = 0
    for y in range(h):
        prefix.append(acc)
        if keep_rows[y]:
            acc += 1
    return out, (lambda v: prefix[min(int(v), h - 1)]), len(rows)


def prepare(key: str) -> tuple[str, list]:
    """Image prête pour le document + repères repositionnés."""
    if key in _PREPARED:
        return _PREPARED[key]
    src = _real(key) or _recreated(key)
    if src is None:
        _PREPARED[key] = (_placeholder(key), [])
        return _PREPARED[key]
    spots = _raw_hotspots(key)
    im = Image.open(src).convert("RGB")
    h0 = im.size[1]
    out, ymap, h1 = _collapse_empty_bands(im)
    os.makedirs(FINAL_DIR, exist_ok=True)
    dst = os.path.join(FINAL_DIR, key + ".png")
    out.save(dst)
    new_spots = []
    for fx, fy, lab in spots:
        y_new = ymap(fy * h0) / max(h1, 1)
        new_spots.append((fx, round(y_new, 4), lab))
    _PREPARED[key] = (dst, new_spots)
    return _PREPARED[key]


def shot(key: str) -> str:
    """Capture originale si disponible, sinon reconstitution, sinon emplacement réservé."""
    return prepare(key)[0]


_HS: dict | None = None


_FALLBACK: dict[str, list] = {}


def _raw_hotspots(key: str):
    """Repères d'origine : exacts sur les reconstitutions, estimés sur les originales."""
    global _HS
    if _real(key):
        return _FALLBACK.get(key, [])
    if _HS is None:
        p = os.path.join(RECREATED, "hotspots.json")
        _HS = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return [tuple(x) for x in _HS.get(key, [])]


def hotspots(key: str, fallback=()):
    if fallback:
        _FALLBACK[key] = list(fallback)
    return prepare(key)[1]


def is_real(key: str) -> bool:
    return _real(key) is not None


def status() -> str:
    real = [k for k in CATALOG if is_real(k)]
    rec = [k for k in CATALOG if not is_real(k) and _recreated(k)]
    slot = [k for k in CATALOG if not is_real(k) and not _recreated(k)]
    return (f"{len(real)} originale(s), {len(rec)} reconstituée(s), "
            f"{len(slot)} emplacement(s) réservé(s)")
