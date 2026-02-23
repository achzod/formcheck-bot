"""Templates de messages WhatsApp en francais — branding ACHZOD.

Regles :
- Pas d'emojis dans les rapports d'analyse
- Emojis OK dans les messages conversationnels (welcome, menu, etc.)
- Ton pro mais accessible
- C'est Achzod seul (pas "nous", pas "notre equipe")
"""

WELCOME = (
    "Bienvenue sur *FORMCHECK by ACHZOD*\n\n"
    "Envoie-moi une video de ton exercice de musculation "
    "et je te fais une analyse biomecanique complete :\n\n"
    "- Detection automatique de l'exercice\n"
    "- Score de forme detaille sur 100\n"
    "- Analyse rep par rep\n"
    "- Corrections prioritaires avec explications\n"
    "- Exercices correctifs personnalises\n"
    "- Rapport complet avec images annotees\n\n"
    "*1 analyse offerte* pour tester.\n\n"
    "Tape *guide* pour savoir comment bien filmer."
)

FILMING_GUIDE = (
    "*GUIDE DE TOURNAGE — Comment bien filmer*\n\n"
    "Pour une analyse precise, respecte ces regles :\n\n"
    "*Angle de camera :*\n"
    "- De *profil* (lateral) = le meilleur angle pour la plupart des exos\n"
    "- De *face* (frontal) pour verifier la symetrie\n"
    "- Evite de filmer de dos — les articulations ne sont pas visibles\n"
    "- Evite les angles en diagonale — ca fausse les mesures\n\n"
    "*Position du telephone :*\n"
    "- Pose-le sur un support ou demande a quelqu'un de filmer\n"
    "- A hauteur de hanche environ\n"
    "- Camera *fixe* — pas de mouvement pendant la serie\n"
    "- Distance : recule assez pour que ton *corps entier* soit visible (tete aux pieds)\n\n"
    "*Conditions :*\n"
    "- Bonne luminosite (pas dans le noir)\n"
    "- Vetements ajustes si possible (pas de jogging ultra large)\n"
    "- Personne ne passe entre toi et la camera\n\n"
    "*La video :*\n"
    "- Filme une serie complete (3 a 8 reps)\n"
    "- 1080p suffit, pas besoin de 4K\n"
    "- Duree : 10 secondes a 3 minutes\n\n"
    "Plus la video est propre, plus l'analyse sera precise."
)

VIDEO_RECEIVED = (
    "Video recue. Analyse en cours.\n"
    "Resultat dans 2-3 minutes."
)

VIDEO_QUALITY_WARNING = (
    "Video recue. J'ai detecte quelques limites :\n"
    "{warnings}\n\n"
    "Je lance l'analyse quand meme, mais la precision sera reduite.\n"
    "Tape *guide* pour les conseils de tournage."
)

ANALYSIS_REPORT_SHORT = (
    "*FORMCHECK — {exercise}*\n"
    "Score : {score}/100\n"
    "Confiance : {confidence}\n"
    "Reps detectees : {reps}\n\n"
    "Rapport complet :\n{report_url}"
)

NO_CREDITS = (
    "Tu n'as plus de credits d'analyse.\n\n"
    "Choisis un forfait pour continuer :"
)

PLAN_STARTER = "Starter — 5 analyses pour 29,99 EUR"
PLAN_PRO = "Pro — 20 analyses pour 59,99 EUR"
PLAN_UNLIMITED = "Illimite — Analyses illimitees pendant 1 an pour 99,99 EUR"

PAYMENT_CONFIRMED_CREDITS = (
    "Paiement recu. {credits} analyses ajoutees a ton compte.\n"
    "Envoie ta prochaine video quand tu veux."
)

PAYMENT_CONFIRMED_UNLIMITED = (
    "Paiement recu. Acces illimite active pendant 1 an.\n"
    "Envoie autant de videos que tu veux."
)

CREDITS_STATUS = "Il te reste {credits} analyse(s)."

CREDITS_UNLIMITED = "Tu as un acces illimite."

UNSUPPORTED_MESSAGE = (
    "Envoie-moi une *video* de ton exercice pour recevoir ton analyse.\n"
    "Tape *menu* pour voir les options."
)

ERROR_GENERIC = (
    "Erreur technique. Reessaie dans quelques instants.\n"
    "Si ca persiste, ecris-moi sur Instagram @achzod."
)

ERROR_ANALYSIS_FAILED = (
    "L'analyse n'a pas abouti.\n\n"
    "Verifie que :\n"
    "- Ton corps est visible en entier (tete aux pieds)\n"
    "- Tu es filme de profil ou de face\n"
    "- La lumiere est suffisante\n"
    "- La camera est fixe\n\n"
    "Tape *guide* pour les conseils de tournage detailles."
)

ERROR_VIDEO_QUALITY = (
    "La qualite de cette video ne permet pas une analyse fiable.\n\n"
    "{errors}\n\n"
    "Tape *guide* pour les conseils de tournage."
)

ERROR_VIDEO_TOO_LARGE = (
    "Video trop lourde (max 25 MB). Filme en 1080p, pas en 4K."
)

ERROR_VIDEO_TOO_SHORT = (
    "Video trop courte ou corrompue. Minimum 3 secondes."
)

RATE_LIMIT = (
    "Une analyse est deja en cours. Attends le resultat."
)

HELP_TEXT = (
    "Envoie-moi une *video* de ton exercice.\n"
    "Tape *menu* pour les options, *guide* pour les conseils de tournage."
)

MENU_TEXT = (
    "*FORMCHECK by ACHZOD*\n\n"
    "*Envoie une video* — Analyse biomecanique complete\n\n"
    "*Commandes :*\n"
    "- *menu* — Ce message\n"
    "- *guide* — Comment bien filmer\n"
    "- *credits* — Tes analyses restantes\n"
    "- *forfaits* — Les offres\n\n"
    "*Forfaits :*\n"
    "- Starter — 5 analyses — 29,99 EUR\n"
    "- Pro — 20 analyses — 59,99 EUR\n"
    "- Illimite — 1 an — 99,99 EUR\n\n"
    "70+ exercices supportes.\n"
    "Filme-toi de profil, corps entier visible, camera fixe."
)
