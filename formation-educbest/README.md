# EducBest Mobile — Guide du professeur (v2)

Refonte du support de formation destiné aux enseignants : typographie **Sora** (grands
titres) + **Space Grotesk** (tout le reste), explications raccourcies, et nouvelle
disposition des captures d'écran.

## 📄 Le document

**[`Formation_EducBest_Mobile_Professeurs_v2.pdf`](Formation_EducBest_Mobile_Professeurs_v2.pdf)**
— 21 pages, A4 portrait, polices embarquées, sommaire cliquable et signets PDF.

Pour le télécharger depuis GitHub : ouvrir le fichier, puis bouton **Download** (ou
*Raw*) en haut à droite.

## 🖼️ Les captures

`captures/` contient les 12 écrans en pleine résolution (992 × 2160 px) :

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

`captures/hotspots.json` donne la position des repères numérotés posés sur chaque écran.

> **À savoir :** les captures originales n'ayant pas pu être transférées dans
> l'environnement de travail, ces 12 écrans ont été **reconstitués à l'identique**
> (mêmes libellés, mêmes couleurs, mêmes positions) à partir des captures fournies.
> Voir ci-dessous pour les remplacer par les originales.

## 🔁 Régénérer le PDF

```bash
pip install pymupdf pillow
python src/build_doc.py          # écrit le PDF à la racine du dossier
```

### Utiliser les captures d'origine

Déposer les fichiers dans `captures-originales/` (noms identiques au tableau ci-dessus,
extension `.jpeg`, `.jpg` ou `.png`), puis relancer `python src/build_doc.py`.
Ordre de priorité : **capture originale > reconstitution > emplacement réservé**.

Chaque capture est automatiquement **compactée** (suppression des grandes bandes vides)
pour que le contenu utile s'affiche plus grand ; les repères numérotés sont repositionnés
en conséquence.

## 🧩 Structure

```
formation-educbest/
├── Formation_EducBest_Mobile_Professeurs_v2.pdf   ← le document
├── captures/                                      ← les 12 écrans (PNG)
├── polices/                                       ← Sora + Space Grotesk (SIL OFL 1.1)
└── src/
    ├── build_doc.py        contenu du guide (textes, étapes, encadrés, tableaux)
    ├── engine.py           moteur de composition PDF (blocs, pagination, sommaire)
    ├── shots.py            résolution / compactage des captures, repères numérotés
    ├── ui_kit.py           primitives de dessin des écrans
    └── recreate_shots.py   reconstitution des 12 écrans
```

## 🎨 Régler l'apparence

Dans `src/build_doc.py` :

- `Theme(...)` — `accent` (bleu EducBest `#4668B4`), `accent_deep`, `ok` / `warn` pour
  les encadrés ;
- `PageSetup(...)` — format de page (A4 portrait par défaut) et marges ;
- chaque section est un appel lisible : `b.section(...)`, `b.step(...)`, `b.split(...)`,
  `b.figure_row(...)`, `b.callout(...)`, `b.table(...)`, `b.cards(...)`.

## 📚 Plan du document

1. Ce que vous saurez faire · 2. Choisir son parcours, puis se connecter ·
3. École + Année : le réflexe n° 1 · 4. L'accueil et ses 5 menus ·
5. Mes classes, mes apprenants · 6. Faire l'appel · 7. Saisir les notes ·
8. Le calendrier scolaire · 9. Les notifications · 10. Mon profil et ma sécurité ·
11. Ma journée type · 12. Dépannage express · 13. S'entraîner : 5 exercices ·
14. Mémo à garder

## ⚖️ Licences

Polices **Sora** et **Space Grotesk** : SIL Open Font License 1.1
(`polices/LICENSE-Sora.txt`, `polices/LICENSE-SpaceGrotesk.txt`).
