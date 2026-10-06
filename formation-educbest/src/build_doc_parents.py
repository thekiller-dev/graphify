#!/usr/bin/env python
"""
EducBest Mobile — Guide du parent.

Titres  : Sora
Texte   : Space Grotesk
Captures: captures-parents-originales/ si présentes, sinon reconstitutions

Lancer :  python src/build_doc_parents.py
Sortie :  Formation_EducBest_Mobile_Parents_v2.pdf (racine du dossier)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import Blocks2, Doc, PageSetup, Theme  # noqa: E402
from shots_parents import hotspots, shot, status  # noqa: E402

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Formation_EducBest_Mobile_Parents_v2.pdf",
)

theme = Theme(
    accent="#4668B4",       # bleu de l'application
    accent_soft="#E8EEF9",
    accent_deep="#1E3A66",
    ink="#131A26",
    body="#333C4C",
    muted="#6E7788",
    line="#E1E6EE",
    surface="#F5F7FB",
    ok="#19754F",
    ok_soft="#E7F4ED",
    warn="#B4541A",
    warn_soft="#FDF1E7",
)

d = Doc(setup=PageSetup(), theme=theme, footer_label="EducBest Mobile — Guide du parent")
b = Blocks2(d)


def hs(key: str, spots):
    """Repères numérotés : positions exactes (reconstitutions) ou estimées (originales)."""
    return hotspots(key, spots)


RULE = ["Cycle", "Enfant", "Année", "Action", "Confirmation"]

# ===========================================================================
# Couverture
# ===========================================================================
b.cover(
    kicker="Formation pratique · Application mobile",
    title_lines=["EducBest Mobile", "Guide du parent"],
    subtitle="Suivre la scolarité de votre enfant depuis votre téléphone : présences, notes, "
    "documents, paiements. Un geste par ligne, et le repère correspondant sur la capture.",
    meta=[
        ("Pour qui", "Parents et tuteurs · Tous les cycles"),
        ("Durée", "30 min + exercices"),
        ("Version", "Octobre 2026"),
    ],
    badge="EDUCBEST",
)

b.spacer(14)
b.golden_rule(RULE, title="LE RÉFLEXE À GARDER EN TÊTE")
b.bullets(
    [
        "Un geste par ligne : un verbe, pas de jargon.",
        "Les écrans de l'application, exactement comme sur votre téléphone.",
        "Une fiche mémo et 5 exercices pour s'entraîner en fin de guide.",
    ]
)

# ===========================================================================
# 1. Ce que vous saurez faire
# ===========================================================================
b.section("1", "Ce que vous saurez faire", "Les 8 gestes du quotidien, rien de plus.")
b.lead("À la fin de cette formation, vous réalisez seul, sur votre téléphone :")
b.cards(
    [
        ("Me connecter", "Avec les identifiants remis par l'établissement."),
        ("Régler cycle et année", "Le réflexe avant toute consultation."),
        ("Lire mon tableau de bord", "Enfants, moyenne, assiduité, frais."),
        ("Ouvrir la fiche d'un enfant", "Emploi du temps, notes, remarques."),
        ("Suivre les présences", "Cours par cours, enfant par enfant."),
        ("Payer la scolarité", "Enfant, année, montant, confirmation."),
        ("Demander un document", "Certificat, bulletin, attestation."),
        ("Écrire à l'école", "Une préoccupation, une réponse tracée."),
    ],
    cols=2,
    numbered=True,
)

b.h2("Avant de commencer")
b.checklist(
    [
        "Un téléphone chargé et une connexion Internet au moment d'envoyer.",
        "Les identifiants remis par l'établissement (e-mail ou numéro).",
        "Le cycle de votre enfant : Maternelle, Primaire, Secondaire ou Université.",
        "Le nom exact de l'école et l'année scolaire ouverte.",
        "Les notifications autorisées, pour ne rien manquer.",
    ]
)
b.callout(
    "warn",
    "",
    "Vos identifiants sont personnels : ils donnent accès au dossier de vos enfants. "
    "Ne les partagez avec personne, pas même avec un autre parent de la classe.",
)

# ===========================================================================
# 2. Parcours et connexion
# ===========================================================================
b.section("2", "Choisir son parcours, puis se connecter", "Une seule fois, au tout premier démarrage.")
b.lead("Le parcours choisi détermine les menus affichés. Prenez 5 secondes pour ne pas vous tromper.")
b.split(
    shot("1-choix-du-parcours"),
    "Au premier lancement",
    [
        "Touchez le cycle de votre enfant : Maternelle, Primaire, Secondaire ou Université.",
        "Touchez Démarrer.",
        "Autorisez les notifications quand l'application le demande.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Un enfant au primaire et un autre au secondaire ? Choisissez le cycle que vous "
    "consultez le plus souvent : le changement reste possible depuis l'accueil.",
    hotspots=hs("1-choix-du-parcours", [(0.27, 0.545, "1"), (0.50, 0.905, "2")]),
)
b.split(
    shot("2-connexion-parent"),
    "Sur l'écran de connexion",
    [
        "Touchez le profil Parent — pas Enseignant.",
        "Saisissez l'e-mail ou l'identifiant reçu.",
        "Saisissez le mot de passe (l'œil permet de le relire).",
        "Touchez Se connecter.",
    ],
    image_side="left",
    image_ratio=0.52,
    max_h=430,
    note="Mot de passe oublié ? Utilisez le lien sous le champ, ou appelez l'assistance "
    "affichée en bas de l'écran.",
    hotspots=hs(
        "2-connexion-parent",
        [(0.73, 0.37, "1"), (0.09, 0.517, "2"), (0.09, 0.608, "3"), (0.14, 0.711, "4")],
    ),
)
b.callout(
    "info",
    "ASSISTANCE",
    "Le numéro affiché en bas de l'écran de connexion fonctionne en appel et sur WhatsApp : "
    "+229 01 41 63 80 78. Gardez-le, c'est le canal le plus rapide pour un problème d'accès.",
)

# ===========================================================================
# 3. L'accueil
# ===========================================================================
b.section("3", "L'accueil : votre tableau de bord", "Tout se vérifie depuis cette page.")
b.golden_rule(RULE)
b.split(
    shot("3-accueil-parent"),
    "Les 5 zones à connaître",
    [
        "Le cycle, en haut : vérifiez qu'il est bon.",
        "L'année scolaire : touchez la carte pour la changer.",
        "Toutes les sections & démarches : le bouton bleu qui ouvre tous les services.",
        "Les 4 indicateurs : enfants, moyenne, assiduité, frais.",
        "La barre du bas : Accueil, Enfants, Frais, Présence.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Le bloc « Suivi de l'assiduité » résume les présences de tous vos enfants. "
    "S'il reste à zéro, c'est que les enseignants n'ont pas encore validé de cours.",
    hotspots=hs(
        "3-accueil-parent",
        [(0.60, 0.065, "1"), (0.24, 0.219, "2"), (0.66, 0.306, "3"), (0.14, 0.383, "4"),
         (0.50, 0.926, "5")],
    ),
)
b.h2("Lire les 4 indicateurs")
b.cards(
    [
        ("Enfants", "Le nombre d'enfants rattachés à votre compte. S'il en manque un, signalez-le à l'école."),
        ("Moyenne", "La moyenne publiée. Un tiret signifie qu'aucune note n'est encore validée."),
        ("Assiduité", "Le taux de présence calculé sur les cours déjà enregistrés."),
        ("Frais", "« À jour » ou le montant restant dû, selon ce que l'école a enregistré."),
    ],
    cols=2,
)
b.callout(
    "info",
    "",
    "Les captures de ce guide affichent 2025-2026 : c'est un exemple. "
    "Choisissez toujours l'année réellement ouverte par l'établissement.",
)
b.callout(
    "warn",
    "",
    "Un tableau vide ou des chiffres surprenants ? Avant d'appeler l'école, vérifiez le cycle, "
    "puis l'année scolaire. Neuf fois sur dix, le problème vient de là.",
)
b.h3("Changer de cycle ou d'année")
b.bullets(
    [
        "Le cycle se change en touchant son nom, en haut de l'écran, à côté de la cloche.",
        "L'année se change en touchant la carte « Année scolaire », puis en choisissant dans la liste.",
        "Après chaque changement, attendez le rechargement complet avant de lire les chiffres.",
    ]
)

# ===========================================================================
# 4. Trouver un service
# ===========================================================================
b.section("4", "Trouver un service en deux gestes", "Deux portes d'entrée, et c'est tout.")
b.lead(
    "Tout ce que propose EducBest s'ouvre depuis l'une de ces deux pages. Repérez-les une fois, "
    "vous ne chercherez plus jamais."
)
b.figure_row(
    [
        (shot("4-sections-et-raccourcis"), "Sections & Raccourcis : les démarches et le suivi scolaire."),
        (shot("5-menu-parent"), "Le menu (bouton à trois traits) : échanges, abonnements et compte."),
    ],
    max_h=400,
)
b.table(
    ["Où toucher", "Ce que vous y trouvez"],
    [
        [
            "Toutes les sections & démarches",
            "Demande de document · Mes documents · Statut des inscriptions · Inscrire un enfant · "
            "Notes & Bulletins · Emploi du temps · Fournitures · Calendrier scolaire · Finances.",
        ],
        [
            "Le menu, en haut à gauche",
            "Préoccupation & Aide · Remarques enseignants · Abonnez-vous (scolarité) · "
            "Cantine scolaire · À propos · Confidentialité · Compte & session.",
        ],
        [
            "La barre du bas",
            "Accueil · Enfants · Frais · Présence. Elle reste affichée partout dans l'application.",
        ],
    ],
    widths=[0.32, 0.68],
)
b.callout(
    "tip",
    "",
    "Perdu dans une page ? Touchez Accueil dans la barre du bas : vous revenez toujours au "
    "tableau de bord, sans rien perdre.",
)

# ===========================================================================
# 5. Mes enfants
# ===========================================================================
b.section("5", "Mes enfants et leur fiche de suivi", "Trois appuis pour tout savoir d'un enfant.")
b.step(1, "Touchez Enfants dans la barre du bas", "La liste affiche tous les enfants rattachés à votre compte.")
b.step(2, "Touchez Fiche de suivi sous le bon enfant", "La recherche est utile si vous suivez plusieurs enfants.")
b.step(3, "Choisissez un onglet", "Emploi, Notes ou Remarques.")
b.figure_row(
    [
        (shot("6-mes-enfants"), "Mes enfants : une carte par enfant, avec sa classe et l'accès à sa fiche."),
        (shot("7-fiche-suivi-emploi-du-temps"), "La fiche : trois onglets, et le planning de la semaine."),
    ],
    max_h=400,
    numbered=False,
    hotspots=[
        hs("6-mes-enfants", [(0.30, 0.904, "1"), (0.08, 0.439, "2")]),
        hs("7-fiche-suivi-emploi-du-temps", [(0.15, 0.154, "3")]),
    ],
)
b.h2("Les trois onglets de la fiche")
b.table(
    ["Onglet", "Ce que vous y lisez", "Quand le consulter"],
    [
        ["Emploi", "Les jours de cours, leur nombre et les horaires", "En début de semaine"],
        ["Notes", "Les notes publiées par les enseignants", "Après une évaluation"],
        ["Remarques", "Les observations transmises par l'enseignant", "Dès qu'une notification arrive"],
    ],
    widths=[0.18, 0.49, 0.33],
)
b.callout(
    "info",
    "",
    "Un jour affiché « Aucun cours » signifie qu'aucun cours n'est programmé ce jour-là dans "
    "l'emploi du temps de l'école : ce n'est pas une absence de votre enfant.",
)

# ===========================================================================
# 6. Présences
# ===========================================================================
b.section("6", "Les présences de mon enfant", "Ce que l'enseignant valide, vous le voyez.")
b.split(
    shot("14-presences-enfant"),
    "Vérifier une présence",
    [
        "Touchez Présence dans la barre du bas.",
        "Touchez la vignette de l'enfant concerné.",
        "Lisez les lignes affichées : date, cours, statut.",
        "Changez d'enfant en touchant une autre vignette.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Les statuts possibles sont ceux saisis par l'enseignant : présent, retard, absent ou renvoyé.",
    hotspots=hs("14-presences-enfant", [(0.26, 0.193, "2"), (0.74, 0.193, "4"), (0.34, 0.56, "3")]),
)
b.callout(
    "info",
    "« AUCUNE PRÉSENCE ENREGISTRÉE »",
    "Ce message ne veut pas dire que votre enfant est absent. Il veut dire qu'aucune ligne "
    "n'a encore été saisie pour lui : le cours n'a pas commencé, ou l'enseignant n'a pas "
    "encore validé l'appel.",
)
b.bullets(
    [
        "Chaque présence validée déclenche une notification : vous n'avez pas à surveiller la page.",
        "Une absence qui vous semble fausse se signale à l'enseignant ou au secrétariat, pas dans l'application.",
        "Avant de réagir, vérifiez trois choses : le bon enfant, la bonne année, la bonne date.",
    ]
)

# ===========================================================================
# 7. Inscription
# ===========================================================================
b.section("7", "Le dossier d'inscription", "Savoir où en est le dossier, sans se déplacer.")
b.split(
    shot("8-statut-inscription-paiement"),
    "Suivre un dossier",
    [
        "Ouvrez Sections & démarches, puis Statut des inscriptions.",
        "Touchez la vignette de l'enfant.",
        "Lisez la mention affichée à côté de son nom.",
        "Contrôlez les informations du dossier, ligne par ligne.",
        "Touchez Payer la scolarité si le dossier est validé.",
    ],
    image_side="left",
    image_ratio=0.52,
    max_h=430,
    note="Une information fausse (date de naissance, classe demandée) se corrige auprès du "
    "secrétariat : elle n'est pas modifiable depuis l'application.",
    hotspots=hs(
        "8-statut-inscription-paiement",
        [(0.18, 0.17, "2"), (0.38, 0.368, "3"), (0.86, 0.49, "4"), (0.20, 0.742, "5")],
    ),
)
b.h3("Ce que disent les mentions")
b.table(
    ["Mention affichée", "Ce que cela veut dire", "Ce que vous faites"],
    [
        ["Validé", "Le dossier est accepté par l'établissement", "Rien : vous pouvez payer la scolarité"],
        ["Matricule en cours d'attribution", "Le numéro n'est pas encore généré", "Patientez, il s'affichera ici"],
        ["Aucune pièce fournie", "Aucun justificatif n'a encore été déposé", "Déposez les pièces au secrétariat"],
    ],
    widths=[0.28, 0.38, 0.34],
)

# ===========================================================================
# 8. Paiement
# ===========================================================================
b.section("8", "Payer la scolarité", "Quatre champs, dans cet ordre, et une confirmation.")
b.split(
    shot("9-paiement-scolarite"),
    "Le règlement pas à pas",
    [
        "Ouvrez Frais dans la barre du bas.",
        "Sélectionnez l'enfant concerné.",
        "Sélectionnez l'année scolaire.",
        "Saisissez le montant à régler (FCFA).",
        "Touchez Valider le paiement, puis attendez la confirmation.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Le bouton Payer la scolarité, présent sur le dossier d'inscription, ouvre exactement "
    "le même écran.",
    hotspots=hs(
        "9-paiement-scolarite",
        [(0.75, 0.513, "2"), (0.75, 0.591, "3"), (0.75, 0.669, "4"), (0.24, 0.747, "5")],
    ),
)
b.checklist(
    [
        "Vérifier le nom de l'enfant avant de valider.",
        "Vérifier l'année : un paiement enregistré sur la mauvaise année ne s'impute pas au bon dossier.",
        "Saisir le montant exact communiqué par l'établissement.",
        "Ne pas fermer l'application pendant la validation.",
        "Conserver le message de confirmation : c'est votre preuve.",
    ]
)
b.keyline("Indicateur Frais de l'accueil", "mis à jour après confirmation")
b.callout(
    "warn",
    "",
    "Ne réglez jamais la scolarité depuis un lien reçu par message. Passez toujours par "
    "l'application, connecté à votre propre compte.",
)

# ===========================================================================
# 9. Fournitures, emploi du temps, calendrier
# ===========================================================================
b.section("9", "Fournitures, emploi du temps, calendrier", "Trois raccourcis dans la même feuille.")
b.figure(
    shot("10-fournitures-scolaires"),
    caption="Le bloc « Vie scolaire & suivi » de la feuille Sections & Raccourcis.",
    width_ratio=0.9,
    max_h=270,
    hotspots=hs("10-fournitures-scolaires", [(0.74, 0.55, "1"), (0.26, 0.55, "2"), (0.74, 0.24, "3"), (0.88, 0.79, "4")]),
)
b.bullets(
    [
        "Fournitures : la liste des articles à acheter, classe par classe. À consulter avant la rentrée.",
        "Emploi du temps : le planning hebdomadaire, le même que dans la fiche de l'enfant.",
        "Notes & Bulletins : les relevés trimestriels publiés par l'établissement.",
        "Calendrier scolaire : vacances, examens et dates importantes, en lecture seule.",
    ]
)
b.callout(
    "tip",
    "",
    "Les listes de fournitures et le calendrier sont les deux pages à montrer à votre enfant "
    "en début de trimestre : elles évitent la moitié des oublis.",
)

# ===========================================================================
# 10. Demande de document
# ===========================================================================
b.section("10", "Demander un document officiel", "Certificat, bulletin, attestation : la même procédure.")
b.split(
    shot("11-demande-document"),
    "Le formulaire en 4 champs",
    [
        "Ouvrez Sections & démarches, puis Demande de document.",
        "Choisissez l'enfant concerné.",
        "Choisissez l'année scolaire.",
        "Choisissez le type de document.",
        "Touchez Envoyer la demande.",
    ],
    image_side="left",
    image_ratio=0.52,
    max_h=430,
    note="Les trois champs marqués d'une étoile sont obligatoires : tant qu'ils ne sont pas "
    "remplis, l'envoi reste bloqué.",
    hotspots=hs(
        "11-demande-document",
        [(0.75, 0.444, "2"), (0.75, 0.519, "3"), (0.75, 0.593, "4"), (0.43, 0.669, "5")],
    ),
)
b.callout(
    "warn",
    "L'ORDRE DES CHAMPS EST IMPOSÉ",
    "« Sélectionnez d'abord un enfant » : tant que l'enfant n'est pas choisi, la liste des "
    "années reste vide, et tant que l'année n'est pas choisie, aucun type de document "
    "n'apparaît. Remplissez de haut en bas.",
)
b.bullets(
    [
        "« Aucun type disponible » signifie que l'établissement n'a pas encore ouvert de document pour cette année.",
        "Réinitialiser vide le formulaire : utile si vous vous êtes trompé d'enfant.",
        "Une fois la demande envoyée, suivez-la dans Mes documents, et attendez la notification.",
    ]
)

# ===========================================================================
# 11. Préoccupations
# ===========================================================================
b.section("11", "Écrire à l'école", "Une préoccupation écrite laisse une trace, un appel non.")
b.split(
    shot("12-preoccupations"),
    "Poser une préoccupation",
    [
        "Ouvrez le menu, puis Préoccupation & Aide.",
        "Touchez Poser une préoccupation.",
        "Écrivez votre message, puis envoyez.",
        "Pour un nouvel échange, utilisez Nouveau message, en bas à droite.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="La page reste vide tant que vous n'avez rien envoyé : c'est normal. "
    "La réponse de l'établissement s'affiche ensuite dans cette même page.",
    hotspots=hs("12-preoccupations", [(0.28, 0.711, "2"), (0.57, 0.906, "4")]),
)
b.callout(
    "tip",
    "UNE DEMANDE BIEN ÉCRITE",
    "Nom de l'enfant · classe · le fait, avec sa date · ce que vous demandez. "
    "Exemple : « Fabrice DANSOU, CI. Absence notée le 14/09 alors qu'il était en classe. "
    "Merci de vérifier auprès de l'enseignant. »",
)
b.bullets(
    [
        "Un sujet par message : une réponse par sujet, c'est plus rapide.",
        "Les échanges restent dans l'application : vous les retrouvez plus tard.",
        "Pour un problème de connexion, préférez le numéro d'assistance.",
    ]
)

# ===========================================================================
# 12. Notifications
# ===========================================================================
b.section("12", "Les notifications", "La cloche en haut à droite : tout ce qui vous concerne.")
b.split(
    shot("13-notifications"),
    "Lire une notification",
    [
        "Le titre dit de quoi il s'agit : commentaire, présence, information.",
        "La date et l'heure permettent de recouper avec l'emploi du temps.",
        "« Présence confirmée » ne demande aucune action de votre part.",
        "Un commentaire se lit en entier dans l'onglet Remarques de l'enfant.",
    ],
    image_side="left",
    image_ratio=0.52,
    max_h=430,
    note="Chaque notification porte la date et l'heure : c'est ce qui permet de la recouper "
    "avec l'emploi du temps de la journée.",
    hotspots=hs("13-notifications", [(0.12, 0.181, "1"), (0.12, 0.270, "2"), (0.12, 0.563, "3")]),
)
b.bullets(
    [
        "La pastille rouge sur la cloche indique le nombre de nouveautés non lues.",
        "Une notification de présence ne demande aucune action : c'est une confirmation.",
        "Un commentaire d'enseignant se lit en entier dans l'onglet Remarques de la fiche de l'enfant.",
    ]
)
b.callout(
    "tip",
    "",
    "Ouvrez les notifications une fois par jour, le soir : en deux minutes, vous savez "
    "ce qui s'est passé pour chacun de vos enfants.",
)

# ===========================================================================
# 13. Profil et sécurité
# ===========================================================================
b.section("13", "Mon profil et ma sécurité", "Vos informations, votre photo, votre mot de passe.")
b.split(
    shot("15-mon-profil"),
    "Vérifier mes informations",
    [
        "Ouvrez le menu, puis Mon profil.",
        "Contrôlez le nom, l'e-mail et le téléphone.",
        "Touchez le crayon pour changer la photo.",
        "Enregistrez vos modifications.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Le rôle (parent) et le cycle sont affichés sous votre nom. Ils sont fixés par "
    "l'établissement et ne se modifient pas depuis le téléphone.",
    hotspots=hs("15-mon-profil", [(0.50, 0.182, "1"), (0.50, 0.336, "2"), (0.12, 0.508, "3")]),
)
b.h2("Changer mon mot de passe")
b.step(1, "Ouvrez Mon profil")
b.step(2, "Allez dans la partie Sécurité & Mot de passe")
b.step(3, "Saisissez le mot de passe actuel")
b.step(4, "Saisissez le nouveau, puis confirmez-le")
b.step(5, "Validez la mise à jour")
b.keyline("Longueur minimale exigée", "8 caractères")
b.callout(
    "warn",
    "",
    "Un numéro de téléphone faux, et vous ne recevrez plus les alertes importantes. "
    "Vérifiez-le une fois par trimestre.",
)

# ===========================================================================
# 14. Semaine type
# ===========================================================================
b.section("14", "Ma semaine type", "Cinq minutes par jour suffisent.")
b.phase(
    "Chaque jour",
    [
        "Ouvrir les notifications.",
        "Vérifier les présences du jour.",
        "Lire les remarques éventuelles.",
    ],
)
b.phase(
    "En début de semaine",
    ["Ouvrir la fiche de chaque enfant.", "Regarder l'emploi du temps de la semaine."],
)
b.phase(
    "Après une évaluation",
    ["Ouvrir l'onglet Notes.", "Comparer avec la moyenne affichée sur l'accueil."],
)
b.phase(
    "Avant une échéance",
    ["Vérifier l'indicateur Frais.", "Payer la scolarité.", "Conserver la confirmation."],
)
b.phase(
    "Dès qu'une pièce est nécessaire",
    ["Envoyer une demande de document.", "Suivre l'avancement dans Mes documents."],
)

# ===========================================================================
# 15. Dépannage
# ===========================================================================
b.section("15", "Dépannage express", "Le symptôme à gauche, le geste à droite.")
b.table(
    ["Symptôme", "Ce qu'il faut faire"],
    [
        ["Je n'arrive pas à me connecter", "Vérifier le profil choisi (Parent), l'identifiant et le mot de passe. Utiliser « Mot de passe oublié ». Sinon, appeler l'assistance au +229 01 41 63 80 78."],
        ["Mon tableau de bord est vide", "Vérifier le cycle en haut, puis l'année scolaire. Attendre le rechargement avant de conclure."],
        ["Il manque un de mes enfants", "Le rattachement est fait par l'établissement : contacter le secrétariat avec le nom et la classe de l'enfant."],
        ["L'année scolaire n'apparaît pas", "Elle n'est peut-être pas encore ouverte. Actualiser, se déconnecter puis se reconnecter."],
        ["« Aucune présence enregistrée »", "Le cours n'a pas commencé, ou l'appel n'est pas validé. Revenir en fin de journée."],
        ["Une absence me semble fausse", "Vérifier l'enfant, la date et le cours, puis poser une préoccupation en citant la date."],
        ["Aucune note ne s'affiche", "Les notes apparaissent après validation par l'enseignant. Vérifier aussi l'année et le trimestre."],
        ["« Aucun type disponible » sur une demande", "Choisir d'abord l'enfant, puis l'année. Si la liste reste vide, l'école n'a pas ouvert de document."],
        ["Le paiement n'est pas pris en compte", "Vérifier l'enfant, l'année et le montant. Conserver la confirmation et la présenter au secrétariat."],
        ["Je ne reçois plus de notifications", "Vérifier les autorisations du téléphone pour EducBest, et le numéro enregistré dans Mon profil."],
    ],
    widths=[0.33, 0.67],
)

# ===========================================================================
# 16. Exercices
# ===========================================================================
b.section("16", "S'entraîner : 5 exercices", "À faire pendant la formation, sur votre propre compte.")
b.cards(
    [
        ("Se repérer", "Se connecter en profil Parent, nommer les 4 boutons de la barre du bas, vérifier le cycle et l'année."),
        ("Lire un tableau de bord", "Dire combien d'enfants sont rattachés, quel est le taux d'assiduité et l'état des frais."),
        ("Ouvrir une fiche", "Aller jusqu'à l'onglet Emploi d'un enfant, puis citer le nombre de cours de mercredi."),
        ("Suivre une présence", "Ouvrir Présence, changer d'enfant, expliquer ce que signifie « Aucune présence enregistrée »."),
        ("Faire une démarche", "Remplir une demande de document jusqu'au bouton d'envoi, puis poser une préoccupation de test."),
    ],
    cols=1,
    numbered=True,
)
b.callout(
    "tip",
    "",
    "Faites les exercices dans l'ordre : chacun réutilise ce que le précédent a montré. "
    "Un parent qui réussit les cinq sait se servir de l'application sans aide.",
)
b.keyline("Objectif de durée pour les 5 exercices", "15 minutes")

# ===========================================================================
# 17. Mémo
# ===========================================================================
b.section("17", "Mémo à garder", "Une page, cinq réflexes.", new_page=True)
b.golden_rule(RULE)
b.lead("Avant toute action dans l'application, posez-vous les cinq questions dans cet ordre :")
b.bullets(
    [
        "Suis-je dans le bon cycle ?",
        "Est-ce le bon enfant qui est sélectionné ?",
        "Est-ce la bonne année scolaire ?",
        "Mon action est-elle terminée (bouton touché, message affiché) ?",
        "La confirmation est-elle bien apparue à l'écran ?",
    ]
)
b.h2("Demander de l'aide efficacement")
b.para("Pour que l'établissement traite votre demande du premier coup, donnez ces six éléments :")
b.cards(
    [
        ("Votre nom", "Tel qu'il apparaît dans l'application."),
        ("Le nom de l'enfant", "Et sa classe."),
        ("L'école et le cycle", "Ceux affichés en haut de l'accueil."),
        ("L'année scolaire", "Celle affichée au moment du problème."),
        ("Une capture d'écran", "Du message d'erreur, lisible."),
        ("La date et l'heure", "Du problème constaté."),
    ],
    cols=2,
)
b.keyline("Assistance (appel & WhatsApp)", "+229 01 41 63 80 78")

# ===========================================================================
# Sommaire + sortie
# ===========================================================================
b.insert_toc(
    title="Sommaire",
    intro="17 étapes, dans l'ordre d'une vraie semaine de suivi. Lisez d'une traite, "
    "ou allez directement au geste qui vous intéresse.",
)

path = d.finish(
    OUT,
    title="EducBest Mobile — Guide du parent",
    author="EducBest",
)
print("PDF écrit :", path)
print("Captures  :", status())
