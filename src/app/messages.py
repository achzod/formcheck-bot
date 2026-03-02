"""Templates de messages WhatsApp en francais — branding ACHZOD.

Regles :
1. Pas d'emojis nulle part
2. Ton pro mais accessible
3. C'est Achzod seul (pas "nous", pas "notre equipe", pas "on")
4. Pas de tirets comme puces (numeros ou phrases)
"""

# ── MESSAGE DE BIENVENUE ────────────────────────────────────────────────────
# Inclut directement les instructions essentielles de tournage
# pour que le client filme correctement DES le premier envoi.

WELCOME = (
    "*FORMCHECK by ACHZOD*\n\n"
    "Analyse biomecanique experte de tes exercices.\n"
    "Envoie une video, recois un rapport complet.\n\n"
    "Comment filmer :\n"
    "1. De profil, corps entier visible\n"
    "2. Camera fixe, bon eclairage\n"
    "3. 3 a 8 reps completes\n"
    "4. Video max 16 MB sur WhatsApp (desactive HD/4K)\n"
    "5. Si plus lourd, coupe en 2-4 clips plus courts\n"
    "6. Envoie-les en notant 1/3, 2/3, 3/3\n\n"
    "*1 analyse offerte.* Envoie ta video."
)

# ── GUIDE DE TOURNAGE DETAILLE ───────────────────────────────────────────────

FILMING_GUIDE = (
    "*GUIDE DE TOURNAGE — Comment bien filmer*\n\n"
    "*ANGLE DE CAMERA PAR EXERCICE :*\n\n"
    "*Squat / Front Squat / Goblet Squat :*\n"
    "De *profil* pour l'angle du tronc, profondeur, genou vs orteils.\n"
    "De *face* en complement pour la symetrie et le valgus du genou.\n"
    "Hauteur camera : *au niveau de la hanche*.\n\n"
    "*Deadlift / RDL / Sumo :*\n"
    "De *profil* obligatoire — position du dos, hip hinge, trajectoire barre.\n"
    "Hauteur camera : *au sol ou legerement au-dessus*.\n\n"
    "*Bench Press / Developpe Incline :*\n"
    "De *profil* a hauteur du banc.\n"
    "Tu vois le trajet de la barre, l'angle des coudes, l'arche.\n\n"
    "*Developpe Militaire (OHP) :*\n"
    "De *profil* — tu verifies l'inclinaison du tronc et le lockout.\n"
    "Camera a hauteur de la taille.\n\n"
    "*Curl / Extensions / Isolations :*\n"
    "De *profil* pour voir l'amplitude complete.\n"
    "Bien cadrer le bras entier (epaule a main).\n\n"
    "*Hip Thrust :*\n"
    "De *profil* a hauteur du banc ou legerement en-dessous.\n\n"
    "*Fentes / Bulgarian Split Squat :*\n"
    "De *profil* ou en diagonale 45 degres.\n"
    "Camera a hauteur de la hanche.\n\n"
    "--- --- ---\n\n"
    "*REGLES GENERALES :*\n\n"
    "1. *Support fixe* — Pose ton tel contre un poids, un sac, ou utilise un mini-trepied\n"
    "2. *Distance* — Recule de 2 a 3 metres pour cadrer le corps entier\n"
    "3. *Luminosite* — Face a la lumiere, jamais en contre-jour\n"
    "4. *Vetements* — Ajustes si possible (pas de jogging ultra large qui cache les genoux)\n"
    "5. *Personne* — Pas de passage entre toi et la camera\n"
    "6. *Resolution* — 1080p suffit, pas besoin de 4K\n"
    "7. *Duree* — 10 secondes a 3 minutes (une serie complete)\n"
    "8. *Taille fichier* — Maximum 16 MB sur WhatsApp (sinon WhatsApp bloque)\n"
    "9. *Video lourde* — Coupe ta serie en plusieurs clips sur WhatsApp\n\n"
    "Plus la video est propre, plus l'analyse sera precise et detaillee."
)

# ── PROFIL MORPHOLOGIQUE ─────────────────────────────────────────────────────
# Flow d'acquisition des 3 photos statiques pour le profil morpho.

MORPHO_WELCOME = (
    "*PROFIL MORPHOLOGIQUE*\n\n"
    "Avant de lancer ta premiere analyse, je vais creer ton "
    "profil morpho. 2 minutes, 3 photos, et ensuite toutes tes "
    "analyses seront calibrees sur TES proportions.\n\n"
    "Ce que ca change concretement :\n"
    "1. Les seuils d'angles sont adaptes a tes segments (femurs, torse, bras)\n"
    "2. Les recommandations de stance et de prise sont personnalisees\n"
    "3. Tu recois un bilan postural complet\n"
    "4. Le score reflete ta technique RELATIVE a ta morphologie\n\n"
    "J'ai besoin de 3 photos debout :\n"
    "1. De *face*\n"
    "2. De *profil* (cote)\n"
    "3. De *dos*\n\n"
    "Envoie ta photo de *face* pour commencer.\n\n"
    "Tape *skip* si tu veux passer direct a l'analyse video "
    "(les seuils seront generiques)."
)

MORPHO_INSTRUCTIONS_FRONT = (
    "*Photo 1/3 — DE FACE*\n\n"
    "Instructions :\n"
    "1. Debout, bras le long du corps, pieds largeur des epaules\n"
    "2. Vetements ajustes (pas de jogging large)\n"
    "3. Fond neutre (mur uni de preference)\n"
    "4. Bonne lumiere (face a une fenetre ou lampe)\n"
    "5. Corps entier visible (tete aux pieds)\n"
    "6. Camera a hauteur de la taille, a 2-3 metres\n\n"
    "Envoie la photo quand tu es pret."
)

MORPHO_INSTRUCTIONS_SIDE = (
    "*Photo 2/3 — DE PROFIL (cote)*\n\n"
    "Tourne-toi sur le cote (gauche ou droit, peu importe).\n"
    "Memes regles : debout naturellement, bras le long du corps, "
    "corps entier visible.\n\n"
    "Cette photo permet de mesurer tes segments (femur, tibia, torse) "
    "et d'analyser ta posture.\n\n"
    "Envoie la photo."
)

MORPHO_INSTRUCTIONS_BACK = (
    "*Photo 3/3 — DE DOS*\n\n"
    "Tourne-toi dos a la camera.\n"
    "Memes regles : debout, bras le long du corps, corps entier visible.\n\n"
    "Cette photo permet de verifier la symetrie et la position des omoplates.\n\n"
    "Envoie la photo."
)

MORPHO_ANALYZING = (
    "Photos recues. Analyse morphologique en cours...\n"
    "Resultat dans quelques secondes."
)

MORPHO_PROFILE_RESULT = (
    "*TON PROFIL MORPHOLOGIQUE*\n\n"
    "*Type :* {morpho_type}\n\n"
    "*Tes proportions changent tout :*\n"
    "Femur/Tibia : {femur_tibia_ratio}\n"
    "Torse/Femur : {torso_femur_ratio}\n"
    "Epaules/Hanches : {shoulder_hip_ratio}\n\n"
    "*Ce que ca implique pour toi :*\n"
    "Squat : {squat_type}\n"
    "Deadlift : {deadlift_type}\n"
    "Bench : prise {bench_grip}\n\n"
    "{summary}\n\n"
    "A partir de maintenant, chaque analyse video que tu m'envoies "
    "sera calibree sur TES proportions. Les scores et les corrections "
    "tiennent compte de ta morphologie.\n\n"
    "Envoie ta premiere video."
)

MORPHO_POSTURE_REPORT = (
    "*BILAN POSTURAL*\n\n"
    "{posture_summary}\n\n"
    "*Recommandations :*\n"
    "{recommendations}"
)

MORPHO_SKIPPED = (
    "Profil morpho ignore — pas de probleme.\n"
    "Les analyses utiliseront des seuils generiques.\n"
    "Tu pourras creer ton profil plus tard en tapant *morpho*.\n\n"
    "Envoie ta video quand tu veux."
)

MORPHO_ALREADY_EXISTS = (
    "Tu as deja un profil morphologique.\n"
    "Tape *morpho reset* pour en creer un nouveau, "
    "ou envoie directement ta video."
)

MORPHO_PHOTO_RECEIVED = "Photo recue ({step}/3). {next_instruction}"

MORPHO_ERROR = (
    "Je n'ai pas reussi a analyser cette photo.\n"
    "Assure-toi que ton corps entier est visible, debout, "
    "avec un bon eclairage.\n"
    "Renvoie la photo."
)

# ── MESSAGES RECEPTION VIDEO ─────────────────────────────────────────────────

VIDEO_RECEIVED = "Analyse en cours..."

VIDEO_QUALITY_WARNING = (
    "Video recue. J'ai detecte quelques limites :\n"
    "{warnings}\n\n"
    "Je lance l'analyse quand meme — la precision sera reduite sur certains points.\n"
    "Pour un resultat optimal, tape *guide* pour les conseils de tournage."
)

# ── MESSAGES DE SUIVI POST-ANALYSE ──────────────────────────────────────────

FOLLOWUP_ANGLE_SUGGESTION = (
    "Pour completer cette analyse, tu peux aussi m'envoyer une video de *{exercise}* "
    "filmee *{suggested_angle}*.\n\n"
    "Ca me permettra de verifier {what_it_checks}."
)

FOLLOWUP_REFILM = (
    "La confiance de cette analyse est de {confidence}%. "
    "Pour un resultat plus precis, tu peux refilmer en suivant ces conseils :\n\n"
    "{tips}\n\n"
    "Tape *guide* pour le guide complet."
)

FOLLOWUP_PROGRESS = (
    "C'est ta {count}e analyse de *{exercise}*.\n\n"
    "Progression :\n"
    "Premiere analyse : {first_score}/100\n"
    "Aujourd'hui : {current_score}/100\n"
    "{trend_message}"
)

FOLLOWUP_CORRECTIVE_REMINDER = (
    "N'oublie pas les exercices correctifs de ta derniere analyse.\n"
    "Fais-les en echauffement pendant 2-3 semaines, puis renvoie une video "
    "pour voir ta progression."
)

# ── RAPPORT D'ANALYSE ────────────────────────────────────────────────────────

ANALYSIS_REPORT_SHORT = (
    "*FORMCHECK — {exercise}*\n"
    "Score : *{score}/100*\n"
    "Confiance : {confidence}\n"
    "Reps detectees : {reps}\n\n"
    "Rapport complet :\n{report_url}"
)

ANALYSIS_REPORT_SUMMARY = (
    "*FORMCHECK — {exercise}*\n"
    "Score : *{score}/100*\n\n"
    "*Decomposition :*\n"
    "Securite : {safety}/40\n"
    "Efficacite technique : {efficiency}/30\n"
    "Controle et tempo : {control}/20\n"
    "Symetrie : {symmetry}/10\n\n"
    "*Top corrections :*\n"
    "{top_corrections}\n\n"
    "Rapport complet avec images annotees :\n{report_url}"
)

# ── CREDITS & PAIEMENTS ─────────────────────────────────────────────────────

NO_CREDITS = (
    "Tu n'as plus de credits d'analyse.\n\n"
    "Choisis un forfait pour continuer :"
)

PLAN_ESSENTIALS = "Essentials — 5 analyses pour 19,99 EUR"
PLAN_PERFORMANCE = "Performance — 15 analyses pour 49,99 EUR"
PLAN_ELITE = "Elite — Analyses illimitees pour 29,99 EUR/mois"

PAYMENT_CONFIRMED_CREDITS = (
    "Paiement recu. {credits} analyses ajoutees a ton compte.\n"
    "Envoie ta prochaine video quand tu veux."
)

PAYMENT_CONFIRMED_UNLIMITED = (
    "Paiement recu. Acces illimite active pendant 1 an.\n"
    "Envoie autant de videos que tu veux."
)

CREDITS_STATUS = "Il te reste *{credits}* analyse(s)."

CREDITS_UNLIMITED = "Tu as un *acces illimite*."

# ── MESSAGES GENERIQUES ──────────────────────────────────────────────────────

UNSUPPORTED_MESSAGE = (
    "Envoie-moi une *video* de ton exercice pour recevoir ton analyse.\n"
    "Tape *menu* pour voir les options."
)

HELP_TEXT = (
    "Envoie-moi une *video* de ton exercice (max 16 MB).\n"
    "Tape *menu* pour les options et *guide* pour les conseils de tournage.\n"
    "Si ta video est lourde, coupe-la en clips 1/3, 2/3, 3/3.\n"
    "Tape *clips* pour le mode multi-clips."
)

MENU_TEXT = (
    "*FORMCHECK by ACHZOD*\n\n"
    "Envoie une *video* pour une analyse (max 16 MB).\n\n"
    "*guide* — Conseils de tournage\n"
    "*clips* — Mode multi-clips (1/3, 2/3, 3/3)\n"
    "*upload* — Rappel des regles pour videos lourdes sur WhatsApp\n"
    "*credits* — Analyses restantes\n"
    "*forfaits* — Recharger\n"
    "*morpho* — Profil morphologique"
)

UPLOAD_INSTRUCTIONS = (
    "Mode 100% WhatsApp pour videos longues/lourdes:\n\n"
    "1. Coupe ta serie en 2 a 4 clips de 10 a 30 sec\n"
    "2. Desactive HD/4K, reste en 720p ou 1080p\n"
    "3. Ecris le numero du clip dans le message: 1/3 puis 2/3 puis 3/3\n"
    "4. J'attends tous les clips puis je fais un seul rapport final"
)

CLIPS_INSTRUCTIONS = (
    "Mode multi-clips WhatsApp:\n\n"
    "1. Coupe ta serie en 2 a 4 clips\n"
    "2. Envoie-les avec numerotation: 1/3, 2/3, 3/3\n"
    "3. J'assemble les clips et je lance une seule analyse finale\n\n"
    "Important: garde le meme angle/cadrage entre les clips."
)

# ── ERREURS ──────────────────────────────────────────────────────────────────

ERROR_GENERIC = (
    "Erreur technique. Reessaie dans quelques instants.\n"
    "Si ca persiste, ecris-moi sur Instagram @achzod."
)

ERROR_ANALYSIS_FAILED = (
    "L'analyse n'a pas pu etre completee sur cette video.\n\n"
    "Ca arrive quand :\n"
    "- Plusieurs personnes dans le cadre (spotters, partenaires)\n"
    "- Camera trop loin ou en diagonale\n"
    "- Eclairage insuffisant\n\n"
    "Essaie de renvoyer la video. Si ca persiste, tape *guide*."
)

ERROR_VIDEO_QUALITY = (
    "La qualite de cette video ne permet pas une analyse fiable.\n\n"
    "{errors}\n\n"
    "Voici comment ameliorer :\n"
    "{suggestions}\n\n"
    "Tape *guide* pour le guide complet."
)

ERROR_VIDEO_TOO_LARGE = (
    "Video bloquee: limite WhatsApp API = 16 MB.\n"
    "Desactive HD/4K, filme en 720p/1080p et reduis la duree.\n"
    "Si besoin, coupe la serie en 2-4 clips et envoie-les sur WhatsApp."
)

UPLOAD_AUTO_FALLBACK = (
    "WhatsApp a bloque ta video (limite 16 MB via API).\n"
    "Renvoie-la en 720p/1080p sans HD, ou coupe-la en 2-4 clips.\n"
    "Je reste en mode 100% WhatsApp."
)

ERROR_VIDEO_TOO_SHORT = (
    "Video trop courte ou corrompue.\n"
    "Minimum 3 secondes — filme au moins 2-3 reps completes."
)

RATE_LIMIT = (
    "Une analyse est deja en cours. Attends le resultat avant d'envoyer une autre video."
)

# ── HELPERS POUR GENERER LES MESSAGES DE SUIVI ──────────────────────────────

# Angles de camera suggeres par exercice
EXERCISE_FILMING_TIPS: dict[str, dict[str, str]] = {
    "squat": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "la symetrie et l'alignement des genoux (valgus)",
        "camera_height": "au niveau de la hanche",
        "tips": "Recule de 2-3m, corps entier visible tete aux pieds.",
    },
    "front_squat": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "l'alignement des coudes et la symetrie",
        "camera_height": "au niveau de la hanche",
        "tips": "Meme conseils que le back squat.",
    },
    "deadlift": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "la symetrie des epaules et la position de la barre",
        "camera_height": "au sol ou legerement au-dessus",
        "tips": "Filme depuis le depart (barre au sol) jusqu'au lockout complet.",
    },
    "rdl": {
        "primary_angle": "de profil",
        "secondary_angle": "en leger 3/4",
        "secondary_checks": "la trajectoire de la barre et l'alignement du dos",
        "camera_height": "au niveau de la hanche",
        "tips": "Descente lente et controlee pour mieux analyser le tempo.",
    },
    "bench_press": {
        "primary_angle": "de profil (cote de la tete)",
        "secondary_angle": "a 45 degres depuis les pieds",
        "secondary_checks": "la trajectoire de la barre et l'angle des coudes",
        "camera_height": "au niveau du banc",
        "tips": "Cadre bien du debut a la fin, y compris le rack/unrack.",
    },
    "ohp": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "la symetrie des bras et le lockout overhead",
        "camera_height": "au niveau de la taille",
        "tips": "Filme debout, corps entier visible.",
    },
    "hip_thrust": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "la symetrie des hanches et l'alignement des genoux",
        "camera_height": "au niveau du banc ou legerement en-dessous",
        "tips": "Cadre bien les hanches, genoux et pieds.",
    },
    "curl": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "la symetrie des bras et le mouvement du tronc",
        "camera_height": "au niveau de la taille",
        "tips": "Bras entier visible (epaule a main).",
    },
    "barbell_row": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "la rotation du tronc et la symetrie",
        "camera_height": "au niveau de la hanche",
        "tips": "Montre bien l'angle du tronc et le mouvement complet.",
    },
    "lateral_raise": {
        "primary_angle": "de face",
        "secondary_angle": "de profil",
        "secondary_checks": "l'amplitude du mouvement et la triche du tronc",
        "camera_height": "au niveau de la taille",
        "tips": "Cadre le haut du corps complet.",
    },
    "bulgarian_split_squat": {
        "primary_angle": "de profil",
        "secondary_angle": "en leger 3/4 avant",
        "secondary_checks": "l'alignement du genou avant et la stabilite du bassin",
        "camera_height": "au niveau de la hanche",
        "tips": "Filme le cote du pied avant, corps entier visible.",
    },
    "lunge": {
        "primary_angle": "de profil",
        "secondary_angle": "de face",
        "secondary_checks": "la symetrie et l'alignement des genoux",
        "camera_height": "au niveau de la hanche",
        "tips": "Si fentes marchees, recule assez pour garder le cadre.",
    },
}


def get_followup_angle_message(exercise: str) -> str | None:
    """Genere un message suggerant un angle de camera complementaire."""
    tips = EXERCISE_FILMING_TIPS.get(exercise)
    if not tips:
        return None
    return FOLLOWUP_ANGLE_SUGGESTION.format(
        exercise=exercise.replace("_", " ").title(),
        suggested_angle=tips["secondary_angle"],
        what_it_checks=tips["secondary_checks"],
    )


def get_refilm_tips(exercise: str, issues: list[str]) -> str:
    """Genere des tips specifiques pour refilmer en corrigeant les problemes detectes."""
    tips_list: list[str] = []

    ex_tips = EXERCISE_FILMING_TIPS.get(exercise, {})

    for issue in issues:
        issue_lower = issue.lower()
        if "sombre" in issue_lower or "luminosite" in issue_lower:
            tips_list.append("Eclairage : place-toi face a la source de lumiere, evite le contre-jour")
        elif "resolution" in issue_lower or "basse" in issue_lower:
            tips_list.append("Resolution : filme en 1080p minimum dans les reglages de ta camera")
        elif "occlusion" in issue_lower or "visible" in issue_lower:
            tips_list.append("Cadrage : recule de 2-3m, assure-toi que ton corps entier est visible")
        elif "camera" in issue_lower or "bouge" in issue_lower:
            tips_list.append("Stabilite : pose ton tel sur un support fixe (poids, sac, trepied)")
        elif "lateral" in issue_lower or "angle" in issue_lower:
            primary = ex_tips.get("primary_angle", "de profil")
            tips_list.append("Angle : filme " + primary + " pour cet exercice")

    if not tips_list:
        tips_list.append("Filme de profil, corps entier visible, camera fixe, bon eclairage")

    if ex_tips.get("tips"):
        tips_list.append("Specifique a l'exercice : " + ex_tips["tips"])

    return "\n".join(str(i) + ". " + tip for i, tip in enumerate(tips_list, 1))


def get_progress_message(
    exercise: str,
    count: int,
    first_score: int,
    current_score: int,
) -> str:
    """Genere un message de progression pour les clients recurrents."""
    diff = current_score - first_score
    if diff > 10:
        trend = "Progression de +" + str(diff) + " points. Continue comme ca."
    elif diff > 0:
        trend = "Legere amelioration (+" + str(diff) + "). Les exercices correctifs font effet."
    elif diff == 0:
        trend = "Score stable. Concentre-toi sur les corrections prioritaires."
    else:
        trend = (
            "Score en baisse (" + str(diff) + "). Ca peut etre la fatigue ou une charge plus lourde. "
            "Verifie les corrections du dernier rapport."
        )

    return FOLLOWUP_PROGRESS.format(
        count=count,
        exercise=exercise.replace("_", " ").title(),
        first_score=first_score,
        current_score=current_score,
        trend_message=trend,
    )


def get_quality_suggestions(errors: list[str]) -> str:
    """Genere des suggestions specifiques a partir des erreurs de qualite video."""
    suggestions: list[str] = []

    for error in errors:
        error_lower = error.lower()
        if "sombre" in error_lower or "luminosite" in error_lower:
            suggestions.append(
                "Eclairage : filme face a une fenetre ou sous un bon eclairage. "
                "Evite le contre-jour (lumiere derriere toi)."
            )
        elif "courte" in error_lower or "duree" in error_lower:
            suggestions.append(
                "Duree : filme au moins 3 repetitions completes. "
                "Lance la camera avant de commencer et arrete apres."
            )
        elif "longue" in error_lower:
            suggestions.append(
                "Duree : envoie seulement ta serie (10s a 1min30), "
                "pas toute la seance."
            )
        elif "resolution" in error_lower:
            suggestions.append(
                "Resolution : verifie que ta camera est reglee en 1080p minimum. "
                "Parametres > Camera > Resolution video."
            )
        elif "personne" in error_lower or "detecter" in error_lower:
            suggestions.append(
                "Cadrage : recule de 2-3 metres, assure-toi que ton corps entier "
                "est visible de la tete aux pieds. Porte des vetements ajustes."
            )

    if not suggestions:
        suggestions.append(
            "Profil, corps entier visible, camera fixe, bon eclairage, "
            "3 a 8 reps completes."
        )

    return "\n".join(str(i) + ". " + s for i, s in enumerate(suggestions, 1))
