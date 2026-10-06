#!/usr/bin/env python
"""
EducBest Mobile — Guide du professeur (version révisée).

Titres  : Sora
Texte   : Space Grotesk
Captures: réutilisées telles quelles depuis /home/user/uploads (cf. shots.py)

Lancer :  python build_doc.py
Sortie :  build/Formation_EducBest_Mobile_Professeurs_v2.pdf
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import Blocks2, Doc, PageSetup, Theme  # noqa: E402
from shots import hotspots, is_real, shot, status  # noqa: E402

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Formation_EducBest_Mobile_Professeurs_v2.pdf",
)

theme = Theme(
    accent="#4668B4",       # bleu de l'application
    accent_soft="#E8EEF9",
    accent_deep="#1E3A66",  # bleu nuit des boutons
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

d = Doc(setup=PageSetup(), theme=theme, footer_label="EducBest Mobile — Guide du professeur")
b = Blocks2(d)


def hs(key: str, spots):
    """Repères numérotés : positions exactes (reconstitutions) ou estimées (originales)."""
    return hotspots(key, spots)


# ===========================================================================
# Couverture
# ===========================================================================
b.cover(
    kicker="Formation pratique · Application mobile",
    title_lines=["EducBest Mobile", "Guide du professeur"],
    subtitle="Faire l'appel, saisir les notes et suivre vos élèves depuis votre téléphone. "
    "Chaque geste tient en une ligne et renvoie au repère correspondant sur la capture.",
    meta=[
        ("Pour qui", "Enseignants · Maternelle, Primaire, Secondaire"),
        ("Durée", "45 min + exercices"),
        ("Version", "Octobre 2026"),
    ],
    badge="EDUCBEST",
)

b.spacer(14)
b.golden_rule(["École", "Année", "Classe", "Action", "Vérification"], title="LE RÉFLEXE À GARDER EN TÊTE")
b.bullets(
    [
        "Un geste par ligne : verbe d'action, pas de jargon.",
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
        ("Me connecter", "Avec les identifiants remis par l'administration."),
        ("Régler école et année", "Le réflexe avant toute saisie."),
        ("Ouvrir mes classes", "Effectif, liste et fiche de chaque élève."),
        ("Démarrer et clore un cours", "Avec la localisation : c'est ce qui calcule votre masse horaire."),
        ("Faire l'appel", "Présent, retard, absent, renvoyé."),
        ("Saisir ou importer les notes", "À la main, ou avec le modèle à remplir."),
        ("Écrire aux parents", "Une remarque officielle depuis la fiche élève."),
        ("Gérer mon compte", "Mes informations et mon mot de passe."),
    ],
    cols=2,
    numbered=True,
)

b.h2("Avant de commencer")
b.checklist(
    [
        "Téléphone chargé : vous l'utilisez au début et à la fin de chaque cours.",
        "Connexion Internet, au moins au moment d'envoyer.",
        "Localisation (GPS) activée : sans elle, impossible de débuter un cours.",
        "Identifiants reçus de l'administration.",
        "Classes, matières et horaires confirmés par l'administration.",
    ]
)
b.callout(
    "warn",
    "",
    "Vos identifiants sont personnels. Ne les partagez jamais avec un collègue ou un élève : "
    "toutes les saisies sont enregistrées à votre nom.",
)

# ===========================================================================
# 2. Choisir son parcours et se connecter
# ===========================================================================
b.section("2", "Choisir son parcours, puis se connecter", "Une seule fois, au tout premier démarrage.")
b.lead("Le parcours choisi détermine les menus affichés. Prenez 5 secondes pour ne pas vous tromper.")
b.split(
    shot("1-choix-du-parcours"),
    "Au premier lancement",
    [
        "Touchez le parcours de votre établissement.",
        "Maternelle, Primaire, Secondaire ou Université.",
        "Touchez Démarrer.",
        "Saisissez l'identifiant fourni (e-mail ou téléphone).",
        "Saisissez le mot de passe, puis Se connecter.",
        "Acceptez les notifications et la localisation.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Mauvais parcours = menus qui ne vous concernent pas. Vous pourrez le changer, "
    "mais attendez la fin du chargement avant d'ouvrir une autre page.",
    hotspots=hs("1-choix-du-parcours", [(0.27, 0.545, "1"), (0.50, 0.905, "2")]),
)
b.callout(
    "tip",
    "",
    "Cochez l'autorisation de localisation dès maintenant : c'est elle qui débloquera le bouton "
    "« Je débute le cours » tout à l'heure.",
)

# ===========================================================================
# 3. École + Année
# ===========================================================================
b.section("3", "École + Année : le réflexe n° 1", "Le geste qui évite 9 problèmes sur 10.")
b.golden_rule(["École", "Année", "Classe", "Action", "Vérification"])
b.split(
    shot("2-accueil-enseignant-filtres-ecole-annee"),
    "Sur l'écran d'accueil",
    [
        "Touchez le sélecteur École, choisissez votre établissement.",
        "Touchez le sélecteur Année, choisissez l'année ouverte.",
        "Attendez le rechargement des classes et du graphique.",
        "Vérifiez que les classes affichées sont bien les vôtres.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Le graphique « Effectif des élèves par classe » est votre contrôle : "
    "s'il est vide ou faux, l'école ou l'année n'est pas la bonne.",
    hotspots=hs(
        "2-accueil-enseignant-filtres-ecole-annee",
        [(0.28, 0.437, "1"), (0.72, 0.437, "2"), (0.50, 0.72, "4")],
    ),
)
b.callout(
    "warn",
    "",
    "Une note saisie dans la mauvaise année part dans le mauvais bulletin. "
    "Vérifiez les deux sélecteurs à chaque ouverture de l'application.",
)
b.callout(
    "info",
    "",
    "Les captures de ce guide affichent 2025-2026 : c'est un exemple. "
    "Choisissez toujours l'année réellement ouverte par l'administration.",
)

# ===========================================================================
# 4. L'accueil et ses 5 menus
# ===========================================================================
b.section("4", "L'accueil et ses 5 menus", "La barre du bas ne change jamais.")
b.table(
    ["Menu", "À quoi il sert", "Quand l'utiliser"],
    [
        ["Accueil", "École, année, effectifs, calendrier scolaire", "En ouvrant l'application"],
        ["Classes", "Vos classes et la liste des élèves", "Pour consulter une fiche"],
        ["Notes", "Saisie, import et vérification des notes", "Après une évaluation"],
        ["Présences", "Début et fin de cours, appel, masse horaire", "À chaque cours"],
        ["Apprenants", "Fiches et suivi individuel", "Pour une remarque aux parents"],
    ],
    widths=[0.20, 0.47, 0.33],
)
b.callout(
    "info",
    "",
    "Les intitulés varient légèrement entre Maternelle, Primaire et Secondaire. La logique reste la même.",
)

# ===========================================================================
# 5. Classes et apprenants
# ===========================================================================
b.section("5", "Mes classes, mes apprenants", "Trois appuis pour arriver à la fiche d'un élève.")
b.step(1, "Ouvrez Classes", "La liste n'affiche que les classes qui vous sont affectées.")
b.step(2, "Touchez la classe", "L'effectif s'affiche en haut de la liste.")
b.step(3, "Touchez un élève", "Sa fiche s'ouvre : identité, relevé de notes, remarques.")
b.figure_row(
    [
        (shot("3-liste-des-apprenants"), "Liste de la classe : l'effectif en haut, une carte par élève."),
        (shot("4-fiche-apprenant-remarque"), "Fiche élève : identité, relevé de notes, puis remarque aux parents."),
    ],
    max_h=400,
)

b.h2("Transmettre une remarque aux parents")
b.step(1, "Ouvrez la fiche de l'élève")
b.step(2, "Descendez jusqu'à « Remarque pour les parents »")
b.step(3, "Choisissez la matière, puis le type d'observation")
b.step(4, "Écrivez une phrase factuelle", "Un fait, une date, une conséquence.")
b.step(5, "Touchez Transmettre la remarque au parent")
b.callout(
    "tip",
    "EXEMPLE DE BONNE REMARQUE",
    "« Devoir de mathématiques non rendu le 14/09. À rattraper avant vendredi. » "
    "Court, daté, vérifiable : le parent sait quoi faire.",
)
b.callout(
    "warn",
    "",
    "La remarque est officielle et conservée. Pas d'appréciation personnelle, pas de jugement : "
    "des faits utiles au suivi.",
)

b.h3("En 10 secondes")
b.checklist(
    [
        "Classes, puis la classe, puis l'élève : la fiche s'ouvre en trois appuis.",
        "Une remarque utile = un fait + une date + une conséquence.",
        "Les notes validées apparaissent automatiquement dans le relevé de l'élève.",
    ]
)

# ===========================================================================
# 6. Présences
# ===========================================================================
b.section("6", "Faire l'appel", "Le cœur de l'application : 4 gestes, du début à la fin du cours.")
b.split(
    shot("5-marquage-presence"),
    "Étape 1 · Démarrer le cours",
    [
        "Ouvrez Présences, choisissez la classe.",
        "Vérifiez « Localisation détectée » et l'horodatage.",
        "Touchez Je débute le cours.",
        "Attendez le message de confirmation.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="Bouton inactif ? Vous n'êtes pas dans la zone de l'établissement, le GPS est coupé, "
    "ou l'horaire du cours n'est pas encore ouvert.",
    hotspots=hs("5-marquage-presence", [(0.50, 0.255, "1"), (0.33, 0.443, "2"), (0.50, 0.498, "3")]),
)
b.callout(
    "warn",
    "LA RÈGLE DES 15 MINUTES",
    "Marquez votre arrivée dans les 15 minutes qui suivent le début du cours, et votre départ "
    "dans les 15 dernières minutes. Hors de ces fenêtres, le cours et son horaire sont annulés.",
)
b.figure(
    shot("6-regles-presence"),
    caption="L'encadré NB s'affiche au premier passage : lisez-le une fois, il conditionne votre masse horaire.",
    width_ratio=0.66,
    max_h=420,
)

b.h2("Étape 2 · Qualifier chaque élève")
b.para("Un seul statut par élève, choisi au fil du cours :")
b.cards(
    [
        ("Présent", "L'élève est en classe à l'appel."),
        ("Retard", "Arrivé après le début du cours."),
        ("Absent", "Pas en classe, sans justificatif à cet instant."),
        ("Renvoyé", "Sorti du cours — si l'option s'applique chez vous."),
    ],
    cols=2,
)
b.callout(
    "tip",
    "",
    "Classe nombreuse ? Utilisez la recherche pour aller vite, puis redescendez toute la liste "
    "avant de valider : un élève oublié reste sans statut.",
)

b.h2("Étape 3 · Valider les présences")
b.step(1, "Relisez les statuts de toute la liste")
b.step(2, "Touchez Valider les présences")
b.step(3, "Attendez le message de confirmation", "Ne fermez pas l'application pendant l'envoi.")

b.h2("Étape 4 · Terminer le cours")
b.step(1, "Revenez sur l'écran Présences")
b.step(2, "Vérifiez que la bonne classe est sélectionnée")
b.step(3, "Touchez Je termine le cours", "Puis attendez la confirmation.")
b.keyline("Masse horaire comptabilisée", "début marqué + fin marquée")
b.callout(
    "warn",
    "",
    "Tant que la fin du cours n'est pas enregistrée, la masse horaire n'est pas calculée. "
    "C'est l'oubli le plus fréquent.",
)

b.h2("Historique et impression")
b.bullets(
    [
        "Historique des présences : vérifier ce qui est déjà enregistré.",
        "Imprimer ma masse horaire : relevé téléchargeable, par école et par année.",
    ]
)

# ===========================================================================
# 7. Notes
# ===========================================================================
b.section("7", "Saisir les notes", "Deux méthodes : à la main, ou par import du modèle.")
b.split(
    shot("7-choix-matiere-evaluation"),
    "À la main, depuis le téléphone",
    [
        "Ouvrez Notes.",
        "Choisissez la matière et le trimestre.",
        "Choisissez l'évaluation : Interro, Devoir ou Compo.",
        "Saisissez une note par élève.",
        "Touchez Vérifier, corrigez ce qui est signalé.",
        "Enregistrez la saisie.",
    ],
    image_side="right",
    image_ratio=0.52,
    max_h=430,
    note="L'évaluation est obligatoire : sans elle, les cases de saisie restent inactives.",
    hotspots=hs(
        "7-choix-matiere-evaluation",
        [(0.50, 0.345, "2"), (0.50, 0.483, "2"), (0.50, 0.74, "3"), (0.50, 0.808, "5")],
    ),
)
b.figure(
    shot("8-tableau-saisie-notes"),
    caption="Le tableau de saisie : une ligne par élève, une colonne par évaluation (I1 = interro 1, D1 = devoir 1, C1 = compo 1).",
    width_ratio=0.66,
    max_h=420,
)

b.h2("Par import d'un fichier")
b.step(1, "Touchez Télécharger modèle")
b.step(2, "Remplissez le modèle", "Sans renommer ni déplacer les colonnes.")
b.step(3, "Touchez Importer notes")
b.step(4, "Contrôlez l'aperçu et les erreurs signalées")
b.step(5, "Touchez Vérifier, puis enregistrez")
b.callout(
    "warn",
    "",
    "N'importez jamais deux fois le même fichier sans avoir vérifié le résultat du premier import.",
)
b.h3("Les 5 réflexes notes")
b.checklist(
    [
        "Choisir l'évaluation avant de commencer la saisie.",
        "Ne jamais mélanger deux classes ou deux années.",
        "Conserver le fichier source jusqu'à la confirmation d'enregistrement.",
        "Relire les valeurs avant de valider.",
        "Vérifier que les notes validées apparaissent dans la fiche de l'élève.",
    ]
)

# ===========================================================================
# 8. Calendrier
# ===========================================================================
b.section("8", "Le calendrier scolaire", "Les dates officielles de l'établissement, en lecture seule.")
b.split(
    shot("9-calendrier-scolaire"),
    "Depuis l'accueil",
    [
        "Touchez Voir le calendrier scolaire.",
        "Choisissez l'école si plusieurs vous sont proposées.",
        "Consultez les événements et leurs dates.",
        "Revenez à l'accueil avec la flèche.",
    ],
    image_side="left",
    image_ratio=0.50,
    max_h=400,
    note="Le calendrier n'enregistre aucune présence. Pour le suivi d'un cours et la masse horaire, "
    "passez toujours par le menu Présences.",
    hotspots=hs("9-calendrier-scolaire", [(0.50, 0.205, "2"), (0.50, 0.305, "3")]),
)

# ===========================================================================
# 9. Notifications
# ===========================================================================
b.section("9", "Les notifications", "La cloche en haut à droite : tout ce qui vous concerne.")
b.split(
    shot("10-notifications"),
    "Ce que vous y trouvez",
    [
        "Les remarques publiées sur un élève.",
        "Les présences confirmées.",
        "Les informations de l'administration.",
        "Les mises à jour pédagogiques.",
    ],
    image_side="right",
    image_ratio=0.50,
    max_h=400,
    note="Ouvrez les notifications au moins une fois par jour : certaines demandent une réponse "
    "de votre part.",
)

# ===========================================================================
# 10. Profil et sécurité
# ===========================================================================
b.section("10", "Mon profil et ma sécurité", "Vos informations, votre photo, votre mot de passe.")
b.figure_row(
    [
        (shot("11-profil-enseignant"), "Mon profil : identité, rôle, coordonnées et accès aux deux boutons d'action."),
        (shot("12-changement-mot-de-passe"), "Onglet Sécurité & Mot de passe : actuel, nouveau, confirmation."),
    ],
    max_h=400,
)
b.h2("Modifier mes informations")
b.step(1, "Ouvrez Mon profil")
b.step(2, "Touchez Modifier mes informations")
b.step(3, "Corrigez ce qui est autorisé", "Téléphone, photo… Le rôle et la classe dépendent de l'administration.")
b.step(4, "Touchez Enregistrer les modifications")

b.h2("Changer mon mot de passe")
b.step(1, "Ouvrez Modifier le profil")
b.step(2, "Allez dans l'onglet Sécurité & Mot de passe")
b.step(3, "Saisissez le mot de passe actuel")
b.step(4, "Saisissez le nouveau, puis confirmez-le")
b.step(5, "Touchez Mettre à jour le mot de passe")
b.keyline("Longueur minimale exigée", "8 caractères")
b.callout(
    "warn",
    "",
    "Votre mot de passe ne s'écrit ni dans un groupe de discussion, ni sur un cahier partagé.",
)

# ===========================================================================
# 11. Journée type
# ===========================================================================
b.section("11", "Ma journée type", "Le même enchaînement, tous les jours.")
b.phase(
    "Avant le 1er cours",
    [
        "Se connecter.",
        "Vérifier l'école et l'année.",
        "Ouvrir Présences et autoriser la localisation.",
        "Vérifier la classe et l'horaire du jour.",
    ],
)
b.phase(
    "Au début du cours",
    ["Toucher Je débute le cours.", "Attendre la confirmation.", "Vérifier que la liste des élèves s'affiche."],
)
b.phase(
    "Pendant le cours",
    ["Noter les retards et absences au fil de l'eau.", "Réserver les remarques aux faits utiles au suivi."],
)
b.phase(
    "À la fin du cours",
    [
        "Relire les statuts.",
        "Valider les présences.",
        "Toucher Je termine le cours.",
        "Vérifier l'enregistrement dans l'historique.",
    ],
)
b.phase(
    "Après une évaluation",
    [
        "Saisir ou importer les notes.",
        "Vérifier, puis enregistrer.",
        "Contrôler que les notes apparaissent dans la fiche de l'élève.",
    ],
)

# ===========================================================================
# 12. Dépannage
# ===========================================================================
b.section("12", "Dépannage express", "Le symptôme à gauche, le geste à droite.")
b.table(
    ["Symptôme", "Ce qu'il faut faire"],
    [
        ["L'année scolaire n'apparaît pas", "Vérifier le parcours choisi, actualiser, se déconnecter puis se reconnecter. Si elle manque toujours : l'administration doit vérifier votre affectation."],
        ["Mes classes sont vides", "Vérifier l'école et l'année, puis actualiser. L'administrateur confirme l'affectation de la classe."],
        ["Les données semblent mélangées", "Revenir à l'accueil, resélectionner école puis année, attendre le chargement complet avant toute saisie."],
        ["« Je débute le cours » est inactif", "Vérifier la localisation, la connexion, la classe sélectionnée et l'horaire. Le cours est peut-être trop tôt, trop tard ou déjà clos."],
        ["La localisation n'est pas détectée", "Activer le GPS, autoriser l'accès pour EducBest, se placer dans la zone de l'établissement."],
        ["La validation des présences échoue", "Contrôler la connexion, vérifier que chaque élève a un statut, relancer une seule fois."],
        ["Impossible de saisir les notes", "Choisir une matière et surtout une évaluation. Vérifier l'école et l'année."],
        ["Les notes importées sont rejetées", "Utiliser le modèle téléchargé, ne pas renommer les colonnes, corriger les lignes signalées."],
        ["La remarque n'est pas envoyée", "Vérifier la matière, le motif, le texte et la connexion Internet."],
        ["Mot de passe oublié", "Utiliser la procédure de récupération de l'application, ou contacter l'administration."],
    ],
    widths=[0.34, 0.66],
)

# ===========================================================================
# 13. Exercices
# ===========================================================================
b.section("13", "S'entraîner : 5 exercices", "À faire sur une classe de test, pendant la formation.")
b.cards(
    [
        ("Se repérer", "Choisir son parcours, se connecter, nommer les 5 menus, sélectionner école et année."),
        ("Gérer une présence", "Débuter un cours, marquer un présent, un retard, un absent, valider, terminer le cours."),
        ("Saisir une note", "Choisir matière et évaluation, saisir 3 notes, Vérifier, corriger une erreur volontaire, enregistrer."),
        ("Suivre un apprenant", "Ouvrir une classe, ouvrir une fiche, lire le relevé, envoyer une remarque de test."),
        ("Sécuriser son compte", "Vérifier ses informations, repérer l'onglet Sécurité et le bouton de déconnexion."),
    ],
    cols=1,
    numbered=True,
)

# ===========================================================================
# 14. Mémo
# ===========================================================================
b.section("14", "Mémo à garder", "Une page, cinq réflexes.", new_page=True)
b.golden_rule(["École", "Année", "Classe", "Action", "Vérification"])
b.lead("Avant toute action pédagogique, posez-vous les cinq questions dans cet ordre :")
b.bullets(
    [
        "Suis-je dans la bonne école ?",
        "Suis-je dans la bonne année scolaire ?",
        "Est-ce la bonne classe, la bonne matière ?",
        "Mon action est-elle terminée (bouton touché, message affiché) ?",
        "L'enregistrement est-il confirmé à l'écran ?",
    ]
)
b.h2("Demander de l'aide efficacement")
b.para("Pour que l'administration traite votre demande du premier coup, envoyez ces six éléments :")
b.cards(
    [
        ("Votre nom", "Tel qu'il apparaît dans l'application."),
        ("Niveau et école", "Le parcours et l'établissement sélectionnés."),
        ("Année scolaire", "Celle affichée au moment du problème."),
        ("Classe ou matière", "Concernée par le blocage."),
        ("Capture d'écran", "Du message d'erreur, lisible."),
        ("Date et heure", "Du problème constaté."),
    ],
    cols=2,
)

# ===========================================================================
# Sommaire (inséré après la couverture) + sortie
# ===========================================================================
b.insert_toc(
    title="Sommaire",
    intro="14 étapes, dans l'ordre d'une vraie journée de cours. Lisez d'une traite, "
    "ou allez directement au geste qui vous intéresse.",
)

path = d.finish(
    OUT,
    title="EducBest Mobile — Guide du professeur",
    author="EducBest",
)
print("PDF écrit :", path)
print("Captures  :", status())
