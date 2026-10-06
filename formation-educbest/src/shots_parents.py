"""
Résolution des captures d'écran — espace PARENT.

Même mécanique que shots.py (côté professeur), mais sur les dossiers parents :

- capture originale : captures-parents-originales/<clé>.jpeg (ou .jpg/.png)
- sinon reconstitution : captures-parents/<clé>.png
- sinon emplacement réservé généré automatiquement

Dès que les vraies captures sont déposées, relancer `python src/build_doc_parents.py`
régénère le document à l'identique avec les images d'origine.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shots  # noqa: E402
from ui_kit import _ROOT  # noqa: E402

shots.UPLOADS = os.environ.get(
    "EDUCBEST_SHOTS_PARENTS", os.path.join(_ROOT, "captures-parents-originales")
)
shots.RECREATED = os.path.join(_ROOT, "captures-parents")
shots.FINAL_DIR = os.path.join(_ROOT, "build", "captures-parents-compactees")
shots.PLACEHOLDER_DIR = os.path.join(_ROOT, "build", "emplacements-parents")
shots.CATALOG = {
    "1-choix-du-parcours": ("Choisissez votre parcours", ["Maternelle", "Primaire", "Secondaire", "Université", "Bouton Démarrer"]),
    "2-connexion-parent": ("Connexion", ["Profil Parent", "Email ou identifiant", "Mot de passe", "Se connecter", "Assistance"]),
    "3-accueil-parent": ("Accueil parent", ["Cycle", "Année scolaire", "Sections & démarches", "Indicateurs", "Barre du bas"]),
    "4-sections-et-raccourcis": ("Sections & Raccourcis", ["Documents & démarches", "Vie scolaire & suivi", "Finances & communication"]),
    "5-menu-parent": ("Menu parent", ["Préoccupation & Aide", "Remarques enseignants", "Abonnez-vous", "Cantine scolaire"]),
    "6-mes-enfants": ("Mes enfants", ["Inscrire un enfant", "Recherche", "Fiche de suivi"]),
    "7-fiche-suivi-emploi-du-temps": ("Fiche de suivi", ["Onglet Emploi", "Onglet Notes", "Onglet Remarques", "Carte du jour"]),
    "8-statut-inscription-paiement": ("Statut de l'inscription", ["Choix de l'enfant", "Statut du dossier", "Informations", "Payer la scolarité"]),
    "9-paiement-scolarite": ("Paiement de la scolarité", ["Enfant", "Année scolaire", "Montant", "Valider le paiement"]),
    "10-fournitures-scolaires": ("Fournitures et vie scolaire", ["Fournitures", "Emploi du temps", "Notes & Bulletins"]),
    "11-demande-document": ("Demande de document", ["Enfant concerné", "Année scolaire", "Type de document", "Envoyer la demande"]),
    "12-preoccupations": ("Mes préoccupations", ["Poser une préoccupation", "Nouveau message"]),
    "13-notifications": ("Notifications", ["Titre de l'alerte", "Date et heure", "Présence confirmée"]),
    "14-presences-enfant": ("Suivi des présences", ["Enfant sélectionné", "Autre enfant", "Zone de résultat"]),
    "15-mon-profil": ("Mon profil", ["Photo", "Rôle et cycle", "Informations du compte"]),
}
shots._PREPARED.clear()
shots._HS = None

shot = shots.shot
hotspots = shots.hotspots
is_real = shots.is_real
status = shots.status
prepare = shots.prepare
