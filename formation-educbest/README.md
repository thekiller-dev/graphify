# EducBest Mobile — supports de formation (v2)

Refonte des supports de formation à l'application mobile EducBest : typographie
**Sora** (grands titres) + **Space Grotesk** (tout le reste), explications
raccourcies, nouvelle disposition des captures d'écran avec repères numérotés.

Deux documents, même charte, même moteur :

| Document | Public | Pages | Captures |
|---|---|---|---|
| **[`Formation_EducBest_Mobile_Professeurs_v2.pdf`](Formation_EducBest_Mobile_Professeurs_v2.pdf)** | Enseignants | 21 | 12 écrans |
| **[`Formation_EducBest_Mobile_Parents_v2.pdf`](Formation_EducBest_Mobile_Parents_v2.pdf)** | Parents et tuteurs | 21 | 15 écrans |

A4 portrait, polices embarquées, sommaire cliquable et signets PDF.
Pour télécharger depuis GitHub : ouvrir le fichier, puis bouton **Download** (ou *Raw*).

---

## 🖼️ Les captures

Pleine résolution, 992 × 2160 px.

### `captures/` — parcours **professeur** (12 écrans)

| Fichier | Écran |
|---|---|
| `1-choix-du-parcours.png` | Choisissez votre parcours |
| `2-accueil-enseignant-filtres-ecole-annee.png` | Accueil + sélecteurs école / année |
| `3-liste-des-apprenants.png` | Élèves de la classe |
| `4-fiche-apprenant-remarque.png` | Fiche élève + remarque aux parents |
| `5-marquage-presence.png` | Marquer la présence |
| `6-regles-presence.png` | Encadré NB (règle des 15 minutes) |
| `7-choix-matiere-evaluation.png` | Matière / trimestre / évaluation |
| `8-tableau-saisie-notes.png` | Tableau de saisie des notes |
| `9-calendrier-scolaire.png` | Calendrier scolaire |
| `10-notifications.png` | Centre de notifications |
| `11-profil-enseignant.png` | Mon profil |
| `12-changement-mot-de-passe.png` | Sécurité & mot de passe |

### `captures-parents/` — parcours **parent** (15 écrans)

| Fichier | Écran |
|---|---|
| `1-choix-du-parcours.png` | Choisissez votre parcours |
| `2-connexion-parent.png` | Connexion (profil Parent) |
| `3-accueil-parent.png` | Tableau de bord parent |
| `4-sections-et-raccourcis.png` | Feuille « Sections & Raccourcis » |
| `5-menu-parent.png` | Menu latéral (préoccupations, abonnements, compte) |
| `6-mes-enfants.png` | Mes enfants |
| `7-fiche-suivi-emploi-du-temps.png` | Fiche de suivi — onglet Emploi |
| `8-statut-inscription-paiement.png` | Statut de l'inscription |
| `9-paiement-scolarite.png` | Paiement de la scolarité |
| `10-fournitures-scolaires.png` | Détail « Vie scolaire & suivi » (fournitures) |
| `11-demande-document.png` | Demande de document |
| `12-preoccupations.png` | Mes préoccupations |
| `13-notifications.png` | Notifications |
| `14-presences-enfant.png` | Suivi des présences d'un enfant |
| `15-mon-profil.png` | Mon profil (parent) |

Chaque dossier contient un `hotspots.json` : la position exacte des repères
numérotés posés sur les écrans, en fractions de l'image.

> **État des captures.** Les captures originales n'ayant pas pu être transférées
> dans l'environnement de travail, ces écrans ont été **reconstitués à l'identique**
> (mêmes libellés, mêmes couleurs, mêmes positions) à partir des captures fournies.
> Voir ci-dessous pour les remplacer par les originales.

---

## 🔁 Régénérer les PDF

```bash
pip install pymupdf pillow

python src/build_doc.py           # guide du professeur
python src/build_doc_parents.py   # guide du parent
```

Les PDF sont écrits à la racine du dossier. Les fichiers intermédiaires vont dans
`build/`, qui est ignoré par Git.

### Utiliser les captures d'origine

Déposer les fichiers dans :

- `captures-originales/` pour le guide **professeur** ;
- `captures-parents-originales/` pour le guide **parent**.

Noms identiques aux tableaux ci-dessus, extension `.jpeg`, `.jpg` ou `.png`, puis
relancer le script de build correspondant. Ordre de priorité :
**capture originale > reconstitution > emplacement réservé**.

Chaque capture est automatiquement **compactée** (suppression des grandes bandes
vides) pour que le contenu utile s'affiche plus grand ; les repères numérotés sont
repositionnés en conséquence.

### Reconstituer les écrans

```bash
python src/recreate_shots.py           # 12 écrans professeur  -> captures/
python src/recreate_shots_parents.py   # 15 écrans parent      -> captures-parents/
```

---

## 🧩 Structure

```
formation-educbest/
├── Formation_EducBest_Mobile_Professeurs_v2.pdf   ← guide professeur
├── Formation_EducBest_Mobile_Parents_v2.pdf       ← guide parent
├── captures/                                      ← 12 écrans professeur (PNG)
├── captures-parents/                              ← 15 écrans parent (PNG)
├── polices/                                       ← Sora + Space Grotesk (SIL OFL 1.1)
└── src/
    ├── engine.py                 moteur de composition PDF (blocs, pagination, sommaire)
    ├── ui_kit.py                 primitives de dessin des écrans
    ├── build_doc.py              contenu du guide professeur
    ├── shots.py                  résolution / compactage des captures professeur
    ├── recreate_shots.py         reconstitution des 12 écrans professeur
    ├── build_doc_parents.py      contenu du guide parent
    ├── shots_parents.py          résolution / compactage des captures parent
    └── recreate_shots_parents.py reconstitution des 15 écrans parent
```

## 🎨 Régler l'apparence

Dans `src/build_doc.py` ou `src/build_doc_parents.py` :

- `Theme(...)` — `accent` (bleu EducBest `#4668B4`), `accent_deep`, `ok` / `warn` pour
  les encadrés ;
- `PageSetup(...)` — format de page (A4 portrait par défaut) et marges ;
- chaque section est un appel lisible : `b.section(...)`, `b.step(...)`, `b.split(...)`,
  `b.figure_row(...)`, `b.callout(...)`, `b.table(...)`, `b.cards(...)`.

## 📚 Plan des documents

**Professeur** — 1. Ce que vous saurez faire · 2. Choisir son parcours, puis se
connecter · 3. École + Année : le réflexe n° 1 · 4. L'accueil et ses 5 menus ·
5. Mes classes, mes apprenants · 6. Faire l'appel · 7. Saisir les notes ·
8. Le calendrier scolaire · 9. Les notifications · 10. Mon profil et ma sécurité ·
11. Ma journée type · 12. Dépannage express · 13. S'entraîner : 5 exercices ·
14. Mémo à garder

**Parent** — 1. Ce que vous saurez faire · 2. Choisir son parcours, puis se
connecter · 3. L'accueil : votre tableau de bord · 4. Trouver un service en deux
gestes · 5. Mes enfants et leur fiche de suivi · 6. Les présences de mon enfant ·
7. Le dossier d'inscription · 8. Payer la scolarité · 9. Fournitures, emploi du
temps, calendrier · 10. Demander un document officiel · 11. Écrire à l'école ·
12. Les notifications · 13. Mon profil et ma sécurité · 14. Ma semaine type ·
15. Dépannage express · 16. S'entraîner : 5 exercices · 17. Mémo à garder

Règle d'or rappelée dans chaque document :
**École › Année › Classe › Action › Vérification** (professeur) et
**Cycle › Enfant › Année › Action › Confirmation** (parent).

## ⚖️ Licences

Polices **Sora** et **Space Grotesk** : SIL Open Font License 1.1
(`polices/LICENSE-Sora.txt`, `polices/LICENSE-SpaceGrotesk.txt`).
