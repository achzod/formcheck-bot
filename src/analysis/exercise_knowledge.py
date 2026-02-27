"""Knowledge Base biomecanique pour FORMCHECK.

Chaque exercice a sa fiche : muscles, erreurs courantes, corrections,
cues coaching, angles critiques. Utilisee par le report generator
pour produire des rapports experts.

Source : 11 certifications (NASM, ISSA, Precision Nutrition, Pre-Script),
biomecanique appliquee, Delavier, Contreras, Schoenfeld.
"""

from __future__ import annotations

# Type alias
ExerciseKB = dict[str, dict]


EXERCISE_KB: ExerciseKB = {

    # ══════════════════════════════════════════════════════════════════════
    # PECTORAUX
    # ══════════════════════════════════════════════════════════════════════

    "bench_press": {
        "muscles_primary": ["grand pectoral (faisceau sternal)"],
        "muscles_secondary": ["deltoides anterieurs", "triceps brachial"],
        "common_errors": [
            "Rebond sur la poitrine au lieu d'un tempo controle",
            "Fesses qui decollent du banc (pont excessif)",
            "Coudes trop ouverts a 90 deg (stress acromio-claviculaire)",
            "Barre descendue trop haut (vers le cou) au lieu de la ligne des tetons",
            "Omoplates non retractees (epaules en protraction)",
        ],
        "corrections": [
            "Retracte et abaisse les omoplates AVANT de decrocher la barre",
            "Coudes a 45-75 deg du torse, pas 90 deg",
            "Descends la barre vers la ligne basse des pectoraux",
            "Controle la descente 2-3 sec, pause 1 sec sur la poitrine",
            "Pieds bien ancres au sol, arche naturelle du dos",
        ],
        "cues": [
            "Casse la barre en deux (rotation externe)",
            "Pousse le sol avec les pieds",
            "Serre les omoplates dans ta poche arriere",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 120], "note": "ROM complet sans hyperextension"},
            "shoulder_abduction": {"optimal": [45, 75], "note": "angle coude-torse"},
        },
        "safety_notes": "Ne jamais verrouiller les coudes en haut. Utiliser un spotter ou des safety pins.",
    },

    "incline_bench": {
        "muscles_primary": ["grand pectoral (faisceau claviculaire)", "deltoides anterieurs"],
        "muscles_secondary": ["triceps brachial"],
        "common_errors": [
            "Banc trop incline (>45 deg) — devient un developpe epaules",
            "Trajectoire identique au developpe couche (barre trop basse)",
            "Epaules qui roulent en avant en haut du mouvement",
            "Pas de retraction scapulaire",
        ],
        "corrections": [
            "Inclinaison du banc entre 30 et 45 deg, pas plus",
            "Descends la barre vers le haut des pectoraux (clavicules)",
            "Meme retraction scapulaire que le couche",
            "Controle excentrique 2-3 sec",
        ],
        "cues": [
            "Pousse vers le plafond, pas vers tes pieds",
            "Omoplates collees au banc en permanence",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 110]},
        },
        "safety_notes": "Meme consignes de securite que le bench press. Attention a la surcharge des deltoides anterieurs.",
    },

    "dumbbell_bench": {
        "muscles_primary": ["grand pectoral"],
        "muscles_secondary": ["deltoides anterieurs", "triceps brachial", "stabilisateurs scapulaires"],
        "common_errors": [
            "Halteres qui descendent trop bas (hyperextension de l'epaule)",
            "Rotation interne des epaules en bas du mouvement",
            "Trajectoire trop large (ecarte au lieu de developpe)",
            "Omoplates non retractees",
        ],
        "corrections": [
            "Descends jusqu'a l'alignement des coudes avec le torse, pas plus",
            "Garde une rotation neutre ou legere externe des poignets",
            "Trajectoire en arc: large en bas, resserree en haut",
            "Serre les omoplates AVANT de prendre les halteres",
        ],
        "cues": [
            "Comme si tu serrais un tonneau entre tes bras",
            "Coudes a 45 deg, pas en croix",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 120]},
        },
        "safety_notes": "Utiliser les genoux pour monter les halteres en position (kick-up).",
    },

    "chest_fly": {
        "muscles_primary": ["grand pectoral (etirement maximal)"],
        "muscles_secondary": ["deltoides anterieurs", "biceps brachial (stabilisation)"],
        "common_errors": [
            "Bras trop tendus (stress articulaire coude)",
            "Descente trop profonde (hyperextension epaule anterieure)",
            "Mouvement saccade sans controle excentrique",
            "Charge trop lourde — perd la forme et transforme en developpe",
        ],
        "corrections": [
            "Garde une legere flexion du coude (15-20 deg) fixe tout le mouvement",
            "Descends jusqu'a sentir l'etirement sans douleur (ligne des epaules max)",
            "3 sec excentrique minimum — c'est un exercice d'isolation",
            "Charge legere, 12-15 reps, le pec travaille en etirement pas en force",
        ],
        "cues": [
            "Imagine serrer un arbre entre tes bras",
            "Les coudes ne bougent pas — seules les epaules pivotent",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal": [150, 170], "note": "quasi tendu"},
        },
        "safety_notes": "Ne jamais forcer l'amplitude si douleur anterieure de l'epaule.",
    },

    "cable_crossover": {
        "muscles_primary": ["grand pectoral"],
        "muscles_secondary": ["deltoides anterieurs", "serratus anterior"],
        "common_errors": [
            "Tronc trop penche en avant (compense avec le poids du corps)",
            "Mouvement initie par les bras au lieu des pectoraux",
            "Pas de squeeze en fin de concentrique",
            "Position des poulies inadaptee a la zone ciblee",
        ],
        "corrections": [
            "Leger pas en avant, buste stable a 10-15 deg d'inclinaison",
            "Initie par la contraction du pec, les mains suivent",
            "Squeeze 1-2 sec en position croisee",
            "Poulie haute = pec bas, poulie basse = pec haut, poulie milieu = sternal",
        ],
        "cues": [
            "Croise les bras comme si tu serrais quelqu'un",
            "Pense a rapprocher les coudes, pas les mains",
        ],
        "key_angles": {},
        "safety_notes": "Garder les pieds stables, ne pas se laisser tirer par les cables.",
    },

    "push_up": {
        "muscles_primary": ["grand pectoral", "triceps brachial", "deltoides anterieurs"],
        "muscles_secondary": ["serratus anterior", "core"],
        "common_errors": [
            "Hanches qui s'affaissent (pas de gainage)",
            "Coudes trop ouverts a 90 deg",
            "Amplitude incomplete (surtout en bas)",
            "Tete qui tombe en avant",
        ],
        "corrections": [
            "Corps en planche rigide de la tete aux talons",
            "Coudes a 45 deg du torse",
            "Poitrine touche le sol a chaque rep",
            "Regard vers le sol, nuque neutre",
        ],
        "cues": [
            "Serre les fesses et le ventre comme si on allait te frapper",
            "Pousse le sol loin de toi",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 120]},
        },
        "safety_notes": "Adapter avec les genoux au sol si necessaire. Pas de pompes avec le dos cambre.",
    },

    "dip": {
        "muscles_primary": ["triceps brachial", "grand pectoral (partie basse)"],
        "muscles_secondary": ["deltoides anterieurs"],
        "common_errors": [
            "Descente trop profonde (stress capsule anterieure epaule)",
            "Epaules qui remontent vers les oreilles",
            "Balancement du corps (kipping)",
            "Coudes qui partent sur les cotes",
        ],
        "corrections": [
            "Descends jusqu'a ce que le bras soit parallele au sol, pas plus",
            "Abaisse les epaules en permanence (depression scapulaire)",
            "Corps stable, pas de balancement",
            "Coudes pointes vers l'arriere, pas sur les cotes",
        ],
        "cues": [
            "Epaules dans les poches",
            "Penche-toi pour les pecs, reste droit pour les triceps",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [70, 110]},
        },
        "safety_notes": "Deconseille si douleur a l'epaule. Limiter l'amplitude si antecedent de luxation.",
    },

    "svend_press": {
        "muscles_primary": ["grand pectoral (faisceau sternal)"],
        "muscles_secondary": ["deltoides anterieurs", "serratus anterior"],
        "common_errors": [
            "Poids trop lourd — les epaules compensent",
            "Bras qui descendent trop bas (perte de tension pectorale)",
            "Pas de squeeze isometrique en extension",
            "Mouvement saccade au lieu de fluide",
        ],
        "corrections": [
            "Leger (5-10 kg) — c'est un exercice de contraction, pas de force",
            "Garde les mains au niveau du sternum pendant tout le mouvement",
            "Squeeze les disques FORT pendant toute la rep, surtout bras tendus",
            "Tempo lent et controle: 2 sec pousse, 2 sec squeeze, 2 sec retour",
        ],
        "cues": [
            "Ecrase les disques l'un contre l'autre en permanence",
            "Pousse droit devant toi, pas vers le bas",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [20, 90], "note": "quasi tendu en fin de mouvement"},
        },
        "safety_notes": "Exercice d'isolation legere. Si douleur a l'epaule, reduire l'amplitude.",
    },

    "chest_dip": {
        "muscles_primary": ["grand pectoral (partie basse)", "deltoides anterieurs"],
        "muscles_secondary": ["triceps brachial", "serratus anterior", "core"],
        "common_errors": [
            "Descente trop profonde (stress capsule anterieure de l'epaule)",
            "Torse trop vertical (transforme en dip triceps au lieu de pec)",
            "Epaules qui remontent vers les oreilles en position basse",
            "Balancement du corps (kipping) pour remonter",
            "Coudes qui partent trop sur les cotes",
        ],
        "corrections": [
            "Penche le torse a 30-45 deg en avant pour cibler les pectoraux",
            "Descends jusqu'a ce que les bras soient paralleles au sol, pas plus",
            "Depression scapulaire: epaules basses en PERMANENCE",
            "Mouvement strict sans balancement — controle excentrique 2-3 sec",
            "Coudes legerement ecartes (30-45 deg) pour activer les pectoraux",
        ],
        "cues": [
            "Penche-toi vers l'avant, regard vers le sol",
            "Epaules dans les poches arriere",
            "Ecrase les barres vers l'interieur (activation pectorale)",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [70, 110]},
            "trunk_inclination": {"optimal": [30, 50], "note": "penche en avant pour les pecs"},
        },
        "safety_notes": "Deconseille si douleur a l'epaule ou instabilite anterieure. Limiter l'amplitude en bas si antecedent de luxation.",
    },

    "decline_bench": {
        "muscles_primary": ["grand pectoral (faisceau sternal inferieur)"],
        "muscles_secondary": ["triceps brachial", "deltoides anterieurs"],
        "common_errors": [
            "Descendre la barre trop haut sur la poitrine (vers le cou)",
            "Rebond sur la poitrine au lieu d'un tempo controle",
            "Omoplates non retractees (epaules en protraction)",
            "Arc excessif du dos qui annule l'angle de declinaison",
            "Pieds mal cales — glissement sur le banc",
        ],
        "corrections": [
            "Descends la barre vers le bas des pectoraux (ligne des tetons ou plus bas)",
            "Controle la descente 2-3 sec, pause legere en bas",
            "Retracte et abaisse les omoplates AVANT de decrocher la barre",
            "Arche naturelle du dos, pas excessive — l'inclinaison du banc fait le travail",
            "Pieds bien cales dans les supports, fessiers colles au banc",
        ],
        "cues": [
            "Casse la barre en deux (rotation externe)",
            "Omoplates serrees, poitrine haute",
            "Pousse vers le plafond, pas vers tes pieds",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 120]},
            "shoulder_abduction": {"optimal": [45, 75], "note": "angle coude-torse"},
        },
        "safety_notes": "Toujours un spotter ou des safety pins. La position declinee rend le rerack plus difficile. Ne pas rester longtemps la tete en bas si hypertension.",
    },

    "dumbbell_incline": {
        "muscles_primary": ["grand pectoral (faisceau claviculaire)"],
        "muscles_secondary": ["deltoides anterieurs", "triceps brachial", "stabilisateurs scapulaires"],
        "common_errors": [
            "Banc trop incline (>45 deg) — devient un developpe epaules",
            "Halteres qui descendent trop bas (hyperextension de l'epaule)",
            "Rotation interne des epaules en bas du mouvement",
            "Omoplates non retractees — epaules en protraction",
            "Trajectoire trop ecartee (ecarte au lieu de developpe)",
        ],
        "corrections": [
            "Inclinaison du banc entre 30 et 45 deg, pas plus",
            "Descends jusqu'a l'alignement des coudes avec le torse, pas plus bas",
            "Rotation neutre ou legere externe des poignets en bas",
            "Retracte les omoplates AVANT de prendre les halteres",
            "Trajectoire en arc convergent: large en bas, resserree en haut",
        ],
        "cues": [
            "Pousse vers le plafond en resserrant les halteres",
            "Omoplates collees au banc comme des timbres",
            "Les coudes a 45 deg du torse, pas en croix",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 120]},
        },
        "safety_notes": "Utiliser les genoux pour monter les halteres en position (kick-up). Variante plus safe que la barre pour les epaules grace a la liberte de trajectoire.",
    },

    "machine_chest_press": {
        "muscles_primary": ["grand pectoral"],
        "muscles_secondary": ["deltoides anterieurs", "triceps brachial"],
        "common_errors": [
            "Regler le siege trop haut ou trop bas (poignees pas au niveau des pecs)",
            "Epaules qui roulent vers l'avant au lieu de rester retractees",
            "Verrouillage agressif des coudes en extension",
            "Utiliser l'inertie (saccades) au lieu d'un mouvement controle",
            "Dos qui decolle du dossier",
        ],
        "corrections": [
            "Regle le siege: poignees alignees avec la ligne basse des pectoraux",
            "Retracte les omoplates AVANT de pousser — epaules collees au dossier",
            "Extension quasi complete mais pas de verrouillage — garde une micro-flexion",
            "Tempo controle: 2 sec pousse, 3 sec retour",
            "Dos et fessiers colles au dossier en permanence",
        ],
        "cues": [
            "Pousse avec les pectoraux, pas les epaules",
            "Serre les omoplates dans le dossier",
            "Controle le retour, ne laisse pas la machine te ramener",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [70, 120]},
        },
        "safety_notes": "Machine guidee = plus safe pour les debutants. Excellent pour finishers haute reps apres les mouvements libres. Pas de spotter necessaire.",
    },

    "pendlay_row": {
        "muscles_primary": ["grand dorsal", "rhomboides", "trapeze moyen"],
        "muscles_secondary": ["biceps brachial", "erecteurs spinaux", "deltoides posterieurs"],
        "common_errors": [
            "Dos rond sous la charge (flexion lombaire)",
            "La barre ne repose pas au sol entre chaque rep (perd l'aspect explosif)",
            "Trop d'extension du torse — tricher avec le momentum",
            "Tirer vers le nombril au lieu du sternum/bas des cotes",
            "Genoux trop tendus (manque de base stable)",
        ],
        "corrections": [
            "Dos PLAT en permanence — neutre strict, zero arrondi",
            "La barre part du sol a chaque rep — dead stop, zero stretch reflex",
            "Le torse reste quasi parallele au sol (plus strict que le barbell row)",
            "Tire la barre vers le bas du sternum de maniere explosive",
            "Genoux legerement flechis pour une base solide et un dos neutre",
        ],
        "cues": [
            "La barre part du sol, explose vers le sternum",
            "Le dos est un mur horizontal — il ne bouge PAS",
            "Serre les omoplates a chaque rep comme un etau",
        ],
        "key_angles": {
            "trunk_inclination": {"optimal": [60, 80], "note": "torse quasi parallele au sol"},
            "elbow_flexion": {"optimal_rom": [30, 110]},
        },
        "safety_notes": "Plus strict que le barbell row classique. Reduit la triche par design. Stop si le dos arrondit.",
    },

    "sissy_squat": {
        "muscles_primary": ["quadriceps (rectus femoris accent)"],
        "muscles_secondary": ["core (stabilisation)", "tibialis anterior"],
        "common_errors": [
            "Se pencher en avant au lieu de se pencher en arriere",
            "Genoux qui ne depassent pas suffisamment les orteils (manque d'amplitude)",
            "Pieds pas sur la pointe (perte d'equilibre)",
            "Descente trop rapide sans controle (stress rotulien)",
            "Hanches qui flechissent au lieu de rester alignees",
        ],
        "corrections": [
            "Penche-toi EN ARRIERE depuis les genoux — le corps forme une ligne droite des genoux aux epaules",
            "Les genoux avancent LOIN devant les orteils — c'est le but de l'exercice",
            "Monte sur la pointe des pieds, tiens-toi a un support si besoin",
            "Excentrique ultra lent (4-5 sec) — l'exercice est dur sur les tendons",
            "Hanches en extension complete — ne casse PAS a la hanche",
        ],
        "cues": [
            "Imagine que tu es une porte qui s'ouvre — le pivot est aux genoux",
            "Corps droit des genoux aux epaules",
            "Descends lentement, les genoux avancent",
        ],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [60, 130], "note": "grande amplitude pour cibler le rectus femoris"},
        },
        "safety_notes": "Exercice avance. Tres haute charge sur le tendon rotulien. Deconseille si douleur aux genoux. Commencer en s'aidant d'un support. Progression tres lente.",
    },

    "landmine_press": {
        "muscles_primary": ["grand pectoral (faisceau claviculaire)", "deltoides anterieurs"],
        "muscles_secondary": ["triceps brachial", "serratus anterior", "core"],
        "common_errors": [
            "Trop de cambrure lombaire pour compenser la charge",
            "Rotation du torse au lieu d'un press propre",
            "Coude qui part trop en lateral (stress articulaire)",
            "Pas de controle excentrique — la barre retombe",
        ],
        "corrections": [
            "Sangle abdominale engagee a fond, cotes basses",
            "Le coude reste proche du corps a 30-45 deg d'abduction",
            "Controle la descente 2-3 sec, pousse explosive",
            "Position split ou genoux pour stabiliser le bassin",
        ],
        "cues": [
            "Pousse en arc vers le haut, pas droit devant",
            "Le coude glisse le long des cotes",
            "Verrouille le core avant chaque rep",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [60, 160]},
            "shoulder_flexion": {"optimal": [80, 130], "note": "arc naturel de la landmine"},
        },
        "safety_notes": "Excellent pour les epaules sensibles. Trajectoire naturelle grace a l'arc de la barre.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # DOS
    # ══════════════════════════════════════════════════════════════════════

    "pullup": {
        "muscles_primary": ["grand dorsal", "grand rond"],
        "muscles_secondary": ["biceps brachial", "brachial", "rhomboides", "trapeze inferieur"],
        "common_errors": [
            "Kipping (balancement pour monter)",
            "Demi-amplitude (menton ne passe pas la barre)",
            "Pas d'extension complete en bas (bras jamais tendus)",
            "Epaules qui montent vers les oreilles en position basse",
        ],
        "corrections": [
            "Initie par la depression scapulaire avant de flechir les coudes",
            "Menton au-dessus de la barre a chaque rep",
            "Extension complete en bas (bras quasi tendus, scapula en upward rotation)",
            "Controle la descente 2-3 sec",
        ],
        "cues": [
            "Tire tes coudes vers tes hanches",
            "Poitrine vers la barre",
            "Mets la barre dans tes poches",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [90, 140]},
            "shoulder_abduction": {"optimal_rom": [30, 60]},
        },
        "safety_notes": "Ne pas forcer le kipping si pas la force stricte. Utiliser des bandes elastiques.",
    },

    "lat_pulldown": {
        "muscles_primary": ["grand dorsal"],
        "muscles_secondary": ["biceps brachial", "grand rond", "rhomboides"],
        "common_errors": [
            "Tirer derriere la nuque (stress cervical et epaules)",
            "Se pencher excessivement en arriere (transforme en rowing)",
            "Utiliser l'inertie (saccades)",
            "Prise trop large ou trop serree",
        ],
        "corrections": [
            "TOUJOURS tirer devant, vers la clavicule",
            "Leger recul du torse (10-15 deg), pas plus",
            "Controle complet, 2 sec concentrique, 3 sec excentrique",
            "Prise a 1.5x largeur d'epaules",
        ],
        "cues": [
            "Tire tes coudes vers le sol, pas vers l'arriere",
            "Bombe le torse vers la barre",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 130]},
        },
        "safety_notes": "Ne jamais tirer derriere la nuque.",
    },

    "barbell_row": {
        "muscles_primary": ["grand dorsal", "rhomboides", "trapeze moyen"],
        "muscles_secondary": ["biceps brachial", "erecteurs spinaux", "deltoides posterieurs"],
        "common_errors": [
            "Dos rond (flexion lombaire sous charge)",
            "Trop de mouvement du torse (tricher avec l'inertie)",
            "Tirer vers le nombril au lieu du bas des cotes",
            "Extension des genoux pour aider (leg drive)",
        ],
        "corrections": [
            "Dos plat/neutre en permanence — hip hinge correct",
            "Torse fixe a 45-60 deg d'inclinaison",
            "Tire la barre vers le bas des cotes/sternum",
            "Genoux legerement flechis et fixes",
        ],
        "cues": [
            "Serre les omoplates a chaque rep en haut",
            "Tire les coudes vers le plafond",
            "Le torse est un mur — il ne bouge pas",
        ],
        "key_angles": {
            "trunk_inclination": {"optimal": [30, 60], "note": "hip hinge stable"},
            "elbow_flexion": {"optimal_rom": [70, 110]},
        },
        "safety_notes": "Stop immediatement si le dos arrondit. Reduire la charge.",
    },

    "dumbbell_row": {
        "muscles_primary": ["grand dorsal", "rhomboides"],
        "muscles_secondary": ["biceps brachial", "trapeze moyen", "deltoides posterieurs"],
        "common_errors": [
            "Rotation excessive du torse pour monter la charge",
            "Amplitude incomplete (pas de squeeze scapulaire)",
            "Coude qui part trop sur le cote",
            "Mouvement trop rapide sans controle excentrique",
        ],
        "corrections": [
            "Torse quasi parallele au sol et FIXE",
            "Tire le coude vers la hanche, pas vers le plafond",
            "Squeeze 1 sec en haut, controle 2-3 sec la descente",
            "Le coude frole le corps",
        ],
        "cues": [
            "Comme si tu demarrais une tondeuse",
            "Le coude monte, pas la main",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [60, 100]},
        },
        "safety_notes": "Garder le dos neutre. Appui solide sur le banc.",
    },

    "cable_pullover": {
        "muscles_primary": ["grand dorsal", "petit rond"],
        "muscles_secondary": ["triceps long chef", "grand pectoral (partie sternale)"],
        "common_errors": [
            "Flexion excessive des coudes (transforme en pushdown triceps)",
            "Mouvement initie par les bras au lieu du grand dorsal",
            "Tronc trop droit (pas assez de hip hinge)",
            "Amplitude insuffisante (bras ne remontent pas au-dessus de la tete)",
            "Compensation en extension lombaire (cambrure)",
        ],
        "corrections": [
            "Verrouille les coudes en legere flexion (15-20 deg) et ne bouge PLUS",
            "Initie le mouvement par la contraction du dos, pas les bras",
            "Penche-toi 15-25 deg en avant, hanches en arriere",
            "Bras montent jusqu'au-dessus de la tete en excentrique",
            "Expire en tirant vers les cuisses, inspire en remontant",
        ],
        "cues": [
            "Tire avec les coudes, pas les mains",
            "Imagine pousser la barre vers tes cuisses",
            "Etire-toi completement en haut comme si tu priais",
        ],
        "key_angles": {
            "shoulder_flexion": {"optimal_rom": [120, 160]},
            "elbow_flexion": {"max_allowed": 30, "note": "bras quasi tendus"},
            "trunk_inclination": {"optimal": [15, 35]},
        },
        "safety_notes": "Ne pas cambrer le dos. Reduire la charge si les coudes flechissent.",
    },

    "pullover": {
        "muscles_primary": ["grand dorsal", "grand pectoral (partie sternale)"],
        "muscles_secondary": ["triceps long chef", "serratus anterior"],
        "common_errors": [
            "Flexion excessive des coudes pendant la descente",
            "Descente trop profonde (stress epaule anterieure)",
            "Hanches qui descendent (pont instable)",
            "Pas de controle excentrique",
        ],
        "corrections": [
            "Coudes en legere flexion fixe tout le mouvement",
            "Descends jusqu'a sentir l'etirement du dos sans douleur",
            "Hanches hautes et stables",
            "3 sec excentrique, controle total",
        ],
        "cues": [
            "Arc de cercle avec les bras, pas une flexion",
            "Le poids descend derriere ta tete, pas devant",
        ],
        "key_angles": {
            "shoulder_flexion": {"optimal_rom": [100, 150]},
        },
        "safety_notes": "Deconseille si douleur d'epaule. Commencer leger.",
    },

    "face_pull": {
        "muscles_primary": ["deltoides posterieurs", "trapeze moyen", "rhomboides"],
        "muscles_secondary": ["infraspineux", "petit rond", "coiffe des rotateurs"],
        "common_errors": [
            "Tirer trop bas (vers le menton au lieu du front)",
            "Utiliser l'inertie du corps (se pencher en arriere)",
            "Pas de rotation externe en fin de mouvement",
            "Charge trop lourde — perd la forme",
        ],
        "corrections": [
            "Tire vers le front/les yeux, pas le menton",
            "Corps stable, sangle abdominale engagee",
            "En haut: rotation externe, pouces vers l'arriere",
            "Leger, 15-20 reps, c'est un exercice de sante articulaire",
        ],
        "cues": [
            "Fais un double biceps en tirant la corde",
            "Ecarte les mains en fin de mouvement",
        ],
        "key_angles": {},
        "safety_notes": "Exercice essentiel pour la sante des epaules. Ne jamais charger lourd.",
    },

    "cable_row": {
        "muscles_primary": ["grand dorsal", "rhomboides", "trapeze moyen"],
        "muscles_secondary": ["biceps brachial", "erecteurs spinaux"],
        "common_errors": [
            "Trop de mouvement du torse (balancement avant/arriere)",
            "Epaules qui montent vers les oreilles",
            "Amplitude incomplete (pas de squeeze scapulaire)",
            "Tirer avec les biceps au lieu du dos",
        ],
        "corrections": [
            "Torse quasi vertical avec tres leger mouvement (5-10 deg max)",
            "Depression scapulaire: epaules basses en permanence",
            "Squeeze 1-2 sec en fin de traction, omoplates serrees",
            "Pense a tirer les coudes vers l'arriere, pas les mains",
        ],
        "cues": [
            "Bombe le torse vers la poignee",
            "Les coudes depassent le dos",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [60, 110]},
            "trunk_inclination": {"optimal": [75, 90], "note": "quasi vertical"},
        },
        "safety_notes": "Ne pas arrondir le bas du dos en extension complete.",
    },

    "tbar_row": {
        "muscles_primary": ["grand dorsal", "rhomboides", "trapeze"],
        "muscles_secondary": ["biceps brachial", "erecteurs spinaux"],
        "common_errors": [
            "Dos rond sous charge",
            "Trop d'extension du torse a chaque rep",
            "Tirer trop haut (stress epaule)",
        ],
        "corrections": [
            "Meme rigueur que le barbell row: dos neutre",
            "Torse fixe a 45-60 deg",
            "Tire vers le sternum, squeeze scapulaire en haut",
        ],
        "cues": ["Poitrine fiere, dos plat", "Coudes vers le plafond"],
        "key_angles": {
            "trunk_inclination": {"optimal": [30, 60]},
            "elbow_flexion": {"optimal_rom": [60, 110]},
        },
        "safety_notes": "Meme consignes de dos neutre que tout rowing.",
    },

    "reverse_fly": {
        "muscles_primary": ["deltoides posterieurs", "rhomboides"],
        "muscles_secondary": ["trapeze moyen", "infraspineux"],
        "common_errors": [
            "Utiliser l'inertie au lieu du controle",
            "Bras trop tendus (stress coude)",
            "Tronc qui bouge",
        ],
        "corrections": [
            "Legere flexion du coude fixe",
            "Mouvement lent et controle, 3 sec chaque phase",
            "Serre les omoplates en haut, 1 sec de squeeze",
        ],
        "cues": ["Ouvre les bras comme des ailes", "Squeeze les omoplates"],
        "key_angles": {},
        "safety_notes": "Exercice leger, 12-20 reps. Pas un mouvement de force.",
    },

    "chinup": {
        "muscles_primary": ["grand dorsal", "biceps brachial"],
        "muscles_secondary": ["brachial", "grand rond", "rhomboides"],
        "common_errors": [
            "Kipping ou balancement pour finir les reps",
            "Demi-amplitude — bras pas completement tendus en bas",
            "Menton qui pousse en avant au lieu de monter le torse",
            "Coudes qui partent vers l'exterieur",
        ],
        "corrections": [
            "Full ROM: bras quasi tendus en bas, menton au-dessus de la barre en haut",
            "Monte la poitrine vers la barre, pas le menton vers le ciel",
            "Coudes drives vers le bas et DEVANT toi, pas sur les cotes",
            "Controle la descente 2-3 sec, pas de chute libre",
        ],
        "cues": [
            "Tire la barre vers ta clavicule",
            "Serre les biceps en haut",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [20, 130]},
        },
        "safety_notes": "Supination met plus de stress sur les biceps que le pullup. Ajouter du lest progressivement.",
    },

    "close_grip_pulldown": {
        "muscles_primary": ["grand dorsal", "grand rond"],
        "muscles_secondary": ["biceps brachial", "brachial", "rhomboides"],
        "common_errors": [
            "Tirer avec les bras au lieu d'initier avec le dos",
            "Se pencher trop en arriere (devient un rowing)",
            "Lacher la contraction en haut — poids qui remonte d'un coup",
            "Poignets qui cassent",
        ],
        "corrections": [
            "Initie le mouvement en deprimant les omoplates AVANT de tirer",
            "Legere inclinaison arriere (10-15 deg max) et fixe",
            "Controle le retour 2-3 sec, etirement complet en haut",
            "Poignets neutres, tire avec les coudes pas les mains",
        ],
        "cues": [
            "Coudes dans les poches",
            "Serre le dos en bas du mouvement",
            "Etire-toi completement en haut",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 150]},
            "shoulder_extension": {"optimal": [0, 45]},
        },
        "safety_notes": "Prise serree met plus de stress sur les bras. Alterner avec prise large.",
    },

    "seal_row": {
        "muscles_primary": ["grand dorsal", "rhomboides", "trapeze moyen"],
        "muscles_secondary": ["biceps brachial", "deltoides posterieurs", "infraspinatus"],
        "common_errors": [
            "Tricher avec le momentum (soulever le torse du banc)",
            "Tirer trop haut et perdre la retraction scapulaire",
            "Amplitude incomplete en bas (pas d'etirement)",
            "Prise trop serree ou trop large pour le ciblage voulu",
        ],
        "corrections": [
            "Le torse reste COLLE au banc a chaque rep — zero triche possible",
            "Tire les coudes vers les hanches, squeeze les omoplates 1 sec",
            "Laisse les bras s'etendre completement en bas a chaque rep",
            "Prise a largeur d'epaules pour un ciblage equilibre dos/rhomboides",
        ],
        "cues": [
            "Ventre colle au banc en permanence",
            "Tire les coudes, pas les mains",
            "Squeeze les omoplates comme si tu tenais un crayon entre elles",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 120]},
        },
        "safety_notes": "Le banc sureleve elimine toute triche lombaire. Exercice ideal pour isoler le dos.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # EPAULES
    # ══════════════════════════════════════════════════════════════════════

    "ohp": {
        "muscles_primary": ["deltoides (portion moyenne et anterieure)"],
        "muscles_secondary": ["triceps brachial", "trapeze superieur", "serratus anterior"],
        "common_errors": [
            "Cambrure excessive du dos (compensation lombaire)",
            "Barre qui passe devant le visage au lieu de monter droit",
            "Pas de lock-out complet en haut",
            "Coudes qui partent en avant au lieu de rester sous la barre",
        ],
        "corrections": [
            "Sangle abdominale engagee, fessiers serres, ZERO cambrure",
            "La barre monte en ligne droite — bouge la tete, pas la barre",
            "Lock-out complet: bras tendus, barre au-dessus du milieu du pied",
            "Coudes legerement devant la barre en position basse",
        ],
        "cues": [
            "Pousse ta tete a travers la fenetre des bras",
            "Serre les fesses comme si tu retenais un billet",
            "La barre monte verticalement, point final",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [70, 160]},
            "trunk_inclination": {"max_allowed": 10, "note": "quasi vertical"},
        },
        "safety_notes": "Ne pas faire avec antecedent de conflit sous-acromial. Echauffement coiffe des rotateurs obligatoire.",
    },

    "lateral_raise": {
        "muscles_primary": ["deltoides (portion moyenne)"],
        "muscles_secondary": ["trapeze superieur", "supraspinatus"],
        "common_errors": [
            "Monter au-dessus de la ligne des epaules (impingement)",
            "Utiliser l'inertie (balancer les halteres)",
            "Rotation interne des poignets en haut (pouce vers le bas)",
            "Shrug au lieu d'abduction (trapezes prennent le relais)",
        ],
        "corrections": [
            "Monte jusqu'a la ligne des epaules (90 deg abduction), pas plus",
            "Leger coude (15-20 deg) et rotation neutre ou externe du poignet",
            "Tempo: 2 sec monte, 1 sec pause, 3 sec descente",
            "Abaisse les epaules AVANT de monter les bras",
        ],
        "cues": [
            "Verse de l'eau avec les verres (legere inclinaison des mains)",
            "Les coudes montent, pas les mains",
            "Epaules basses en permanence",
        ],
        "key_angles": {
            "shoulder_abduction": {"optimal_rom": [60, 90], "note": "pas au-dessus de 90"},
        },
        "safety_notes": "Ne pas monter au-dessus de 90 deg si conflit sous-acromial. Charge legere obligatoire.",
    },

    "upright_row": {
        "muscles_primary": ["deltoides (portion moyenne)", "trapeze superieur"],
        "muscles_secondary": ["biceps brachial", "brachial"],
        "common_errors": [
            "Tirer trop haut (au-dessus du menton — impingement)",
            "Prise trop serree (conflit sous-acromial)",
            "Utiliser l'inertie du corps",
            "Rotation interne forcee en haut du mouvement",
        ],
        "corrections": [
            "Monte jusqu'a la ligne des clavicules MAX, pas plus",
            "Prise largeur d'epaules minimum (plus large = plus safe)",
            "Corps stable, sangle engagee, pas de lean back",
            "Les coudes montent plus haut que les mains",
        ],
        "cues": [
            "Les coudes guident le mouvement, pas les mains",
            "Arrete au niveau des clavicules",
        ],
        "key_angles": {
            "shoulder_abduction": {"optimal_rom": [50, 90]},
            "elbow_flexion": {"optimal_rom": [40, 90]},
        },
        "safety_notes": "Exercice controverse pour les epaules. A eviter si conflit sous-acromial. Preferer les laterales.",
    },

    "shrug": {
        "muscles_primary": ["trapeze superieur"],
        "muscles_secondary": ["levator scapulae", "rhomboides"],
        "common_errors": [
            "Rouler les epaules (rotation = stress articulaire)",
            "Amplitude trop faible (demi-reps)",
            "Flechir les coudes (biceps prennent le relais)",
            "Tete en avant",
        ],
        "corrections": [
            "Mouvement VERTICAL uniquement — pas de rotation",
            "Monte les epaules aussi haut que possible, squeeze 2 sec",
            "Bras completement tendus tout le mouvement",
            "Tete neutre, regard droit devant",
        ],
        "cues": ["Monte les epaules vers les oreilles", "Squeeze en haut comme si tu haussais les epaules au telephone"],
        "key_angles": {},
        "safety_notes": "Ne jamais rouler les epaules. Mouvement vertical strict.",
    },

    "front_raise": {
        "muscles_primary": ["deltoides (faisceaux anterieurs)"],
        "muscles_secondary": ["grand pectoral (faisceau claviculaire)"],
        "common_errors": [
            "Monter au-dessus de la ligne des epaules",
            "Balancer le corps pour tricher",
            "Bras completement tendus (stress coude)",
        ],
        "corrections": [
            "Monte a hauteur des yeux, pas plus",
            "Corps stable, pas de lean back",
            "Legere flexion du coude fixe",
        ],
        "cues": ["Monte les poings a hauteur des yeux", "Controle la descente"],
        "key_angles": {
            "shoulder_flexion": {"optimal_rom": [80, 110]},
        },
        "safety_notes": "Les deltoides anterieurs sont souvent deja surcharges par les developpes. A doser.",
    },

    "arnold_press": {
        "muscles_primary": ["deltoides (toutes portions)"],
        "muscles_secondary": ["triceps brachial", "trapeze"],
        "common_errors": [
            "Rotation trop rapide (pas de controle)",
            "Cambrure lombaire",
            "Pas de rotation complete (supination en bas)",
        ],
        "corrections": [
            "Rotation fluide et lente pendant la montee",
            "Gainage strict, pas de cambrure",
            "Position basse: paume vers toi, position haute: paume vers l'avant",
        ],
        "cues": ["Ouvre les portes en montant", "Rotation progressive, pas brusque"],
        "key_angles": {},
        "safety_notes": "Charge moderee. La rotation ajoute du stress a l'epaule.",
    },

    "dumbbell_ohp": {
        "muscles_primary": ["deltoides anterieurs", "deltoides lateraux"],
        "muscles_secondary": ["triceps brachial", "trapeze superieur", "serratus anterior"],
        "common_errors": [
            "Cambrure lombaire excessive pour compenser la charge",
            "Halteres qui partent trop en avant (pas d'alignement)",
            "Coudes qui descendent trop bas (stress sur la coiffe)",
            "Verrouillage brutal des coudes en haut",
        ],
        "corrections": [
            "Cotes basses, sangle engagee — ZERO cambrure",
            "Halteres alignees au-dessus des epaules en haut, pas devant",
            "Descends les coudes a hauteur d'epaule (90 deg), pas plus",
            "Extension complete mais fluide, sans claquer les coudes",
        ],
        "cues": [
            "Pousse droit vers le plafond",
            "Serre les abdos comme si tu allais prendre un coup",
            "Les halteres se rapprochent en haut",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [80, 170]},
            "shoulder_abduction": {"optimal": [80, 100]},
        },
        "safety_notes": "Debout demande plus de core que assis. Si cambrure, passer assis ou reduire la charge.",
    },

    "cable_lateral_raise": {
        "muscles_primary": ["deltoides lateraux"],
        "muscles_secondary": ["trapeze superieur", "supraspinatus"],
        "common_errors": [
            "Tirer avec le trapeze (hausser les epaules)",
            "Balancer le corps pour monter la charge",
            "Bras trop tendus (stress coude)",
            "Monter au-dessus de 90 deg (trapeze prend le relais)",
        ],
        "corrections": [
            "Epaules BASSES en permanence — deprime les omoplates",
            "Corps fixe, seul le bras bouge. S'accrocher a un support si besoin",
            "Legere flexion du coude (15-20 deg) et fixe",
            "Monte jusqu'a l'horizontale, pas plus haut",
        ],
        "cues": [
            "Verse la bouteille d'eau (petit doigt plus haut)",
            "Epaule basse, coude monte",
        ],
        "key_angles": {
            "shoulder_abduction": {"optimal_rom": [0, 90]},
        },
        "safety_notes": "Cable = tension constante. Leger (5-12 kg). Ideal en finisher haute reps.",
    },

    "rear_delt_fly": {
        "muscles_primary": ["deltoides posterieurs"],
        "muscles_secondary": ["rhomboides", "trapeze moyen", "infraspinatus"],
        "common_errors": [
            "Utiliser le momentum au lieu d'isoler le deltoide posterieur",
            "Bras trop tendus (coudes verrouilles = stress articulaire)",
            "Trop de retraction scapulaire (rhomboides volent le travail)",
            "Torse qui bouge au lieu de rester fixe",
        ],
        "corrections": [
            "Leger et controle — c'est de l'isolation, pas de la force",
            "Legere flexion du coude (20-30 deg) fixe pendant tout le mouvement",
            "Focus sur le deltoide post: ouvre les bras en arc, pas en tirant les omoplates",
            "Penche a 45-60 deg et FIXE le torse, ou utiliser un banc incline",
        ],
        "cues": [
            "Ouvre les bras en eventail",
            "Les coudes montent, pas les mains",
        ],
        "key_angles": {
            "shoulder_abduction": {"optimal_rom": [0, 90]},
            "trunk_inclination": {"optimal": [45, 70]},
        },
        "safety_notes": "Ne pas forcer l'amplitude. Si douleur posterieure d'epaule, verifier la mobilite.",
    },

    "lu_raise": {
        "muscles_primary": ["deltoides lateraux", "deltoides anterieurs"],
        "muscles_secondary": ["trapeze superieur", "supraspinatus"],
        "common_errors": [
            "Charge trop lourde — mouvement degrade des la premiere rep",
            "Pas de distinction entre les deux phases (lateral puis overhead)",
            "Coudes qui tombent pendant la phase overhead",
            "Cambrure pour compenser en haut du mouvement",
        ],
        "corrections": [
            "Tres leger (2-5 kg) — c'est un exercice de qualite articulaire",
            "Phase 1: lateral raise jusqu'a 90 deg. Phase 2: rotation vers le haut",
            "Les coudes restent a hauteur d'epaule pendant la rotation",
            "Core engage, zero cambrure, mouvement lent et controle",
        ],
        "cues": [
            "Monte lateral, puis tourne vers le ciel",
            "Les coudes sont le pivot, ils ne bougent pas",
            "Lent a la montee, lent a la descente",
        ],
        "key_angles": {
            "shoulder_abduction": {"optimal_rom": [0, 90], "note": "phase laterale"},
            "shoulder_flexion": {"optimal_rom": [90, 180], "note": "phase overhead"},
        },
        "safety_notes": "Exercice avance de mobilite/force. Deconseille si instabilite d'epaule. Toujours tres leger.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # BICEPS
    # ══════════════════════════════════════════════════════════════════════

    "curl": {
        "muscles_primary": ["biceps brachial"],
        "muscles_secondary": ["brachial", "brachio-radial"],
        "common_errors": [
            "Balancement du corps (cheat curl involontaire)",
            "Coudes qui avancent (deltoides prennent le relais)",
            "Extension incomplete en bas (demi-reps)",
            "Flexion des poignets en haut",
        ],
        "corrections": [
            "Dos contre un mur ou un poteau si tu triches",
            "Coudes COLLES au corps et FIXES",
            "Extension quasi complete en bas (pas de verouillage)",
            "Poignets neutres/droits en permanence",
        ],
        "cues": [
            "Les coudes sont des charnières — ils ne bougent pas",
            "Squeeze le biceps en haut 1 sec",
            "Descends lentement — 3 sec",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 140]},
        },
        "safety_notes": "Ne pas verrouiller les coudes en extension complete. Risque de tendinite du biceps distal.",
    },

    "hammer_curl": {
        "muscles_primary": ["brachial", "brachio-radial"],
        "muscles_secondary": ["biceps brachial"],
        "common_errors": [
            "Memes erreurs que le curl classique",
            "Poignets qui tournent en supination (c'est pas un curl normal)",
            "Balancement excessif",
        ],
        "corrections": [
            "Prise neutre (pouces vers le haut) du debut a la fin",
            "Coudes fixes, zero mouvement des epaules",
            "Controle excentrique 3 sec",
        ],
        "cues": ["Tiens un marteau, tape le clou", "Pouces vers le plafond"],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 130]},
        },
        "safety_notes": "Moins de stress sur le biceps distal que le curl supination.",
    },

    "preacher_curl": {
        "muscles_primary": ["biceps brachial (chef court)"],
        "muscles_secondary": ["brachial"],
        "common_errors": [
            "Extension trop rapide en bas (stress tendon bicipital)",
            "Decoller les bras du pupitre",
            "Hyperextension du coude en bas",
        ],
        "corrections": [
            "Excentrique TRES lent (4 sec) — surtout en bas du mouvement",
            "Bras colles au pupitre tout le temps",
            "Ne verrouille JAMAIS le coude en bas — garde 10 deg de flexion",
        ],
        "cues": ["Le pupitre controle ton bras", "Ralentis en descendant"],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [20, 130]},
        },
        "safety_notes": "ATTENTION en position basse — risque de rupture du tendon bicipital. Toujours controler la descente.",
    },

    "cable_curl": {
        "muscles_primary": ["biceps brachial"],
        "muscles_secondary": ["brachial", "brachio-radial"],
        "common_errors": [
            "Se pencher en arriere pour tricher",
            "Coudes qui avancent",
            "Pas de tension constante (avantage du cable perdu)",
        ],
        "corrections": [
            "Corps droit, coudes fixes au corps",
            "Profite de la tension constante — pas d'acceleration",
            "Squeeze en haut 1-2 sec (le cable maintient la tension)",
        ],
        "cues": ["Tension constante = muscle constant", "Coudes rivetes"],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 140]},
        },
        "safety_notes": "Ideal pour les finishers grace a la tension constante.",
    },

    "dumbbell_curl": {
        "muscles_primary": ["biceps brachial"],
        "muscles_secondary": ["brachial", "brachioradial"],
        "common_errors": [
            "Balancement du corps pour monter la charge (cheat curl involontaire)",
            "Coudes qui avancent devant le torse",
            "Supination absente (poignets en neutre tout le mouvement)",
            "Descente trop rapide sans controle excentrique",
        ],
        "corrections": [
            "Coudes COLLES au corps, seuls les avant-bras bougent",
            "Commencer en neutre en bas, supiner progressivement en montant",
            "Excentrique 3 sec, concentrique 1-2 sec",
            "Si le corps bouge, la charge est trop lourde — baisse",
        ],
        "cues": [
            "Tourne les petits doigts vers toi en haut",
            "Les coudes sont cloues a tes cotes",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [20, 140]},
        },
        "safety_notes": "Charge raisonnable. Le biceps est un petit muscle, pas besoin de charger comme un squat.",
    },

    "incline_curl": {
        "muscles_primary": ["biceps brachial (longue portion)"],
        "muscles_secondary": ["brachial"],
        "common_errors": [
            "Banc pas assez incline (perte de l'etirement de la longue portion)",
            "Coudes qui avancent pendant la flexion",
            "Epaules qui roulent en avant",
            "Charge trop lourde — triche avec le momentum",
        ],
        "corrections": [
            "Banc a 45-60 deg d'inclinaison pour etirer la longue portion",
            "Coudes fixes, pointent vers le sol TOUT le mouvement",
            "Epaules retractees, dos colle au banc",
            "Leger — l'etirement rend l'exercice plus dur a charge egale",
        ],
        "cues": [
            "Laisse les bras pendre verticalement, puis monte",
            "Les coudes ne bougent pas, ils pointent vers le sol",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [10, 130]},
        },
        "safety_notes": "Position d'etirement intense sur la longue portion. Ne pas forcer en bas si douleur bicipitale.",
    },

    "concentration_curl": {
        "muscles_primary": ["biceps brachial (courte portion)"],
        "muscles_secondary": ["brachial"],
        "common_errors": [
            "Utiliser l'epaule pour lever la charge",
            "Coude qui glisse sur la cuisse",
            "Mouvement trop rapide sans squeeze en haut",
            "Torse qui se redresse pour tricher",
        ],
        "corrections": [
            "Le coude est verrouille DANS la face interne de la cuisse — fixe",
            "Seul l'avant-bras bouge, tout le reste est une statue",
            "Squeeze 2 sec en haut a chaque rep",
            "Penche-toi vers l'avant, le torse ne bouge plus",
        ],
        "cues": [
            "Le coude est plante dans la cuisse",
            "Squeeze le biceps comme une orange en haut",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [20, 140]},
        },
        "safety_notes": "Exercice d'isolation pure. Leger et controle. Parfait pour la connexion muscle-cerveau.",
    },

    "spider_curl": {
        "muscles_primary": ["biceps brachial (courte portion)"],
        "muscles_secondary": ["brachial"],
        "common_errors": [
            "Coudes qui reculent pendant la flexion",
            "Balancement des bras (momentum)",
            "Pas d'etirement complet en bas",
            "Banc trop incline ou pas assez (mauvais angle)",
        ],
        "corrections": [
            "Poitrine collee au banc incline (45 deg), bras pendants devant",
            "Les coudes pointent droit vers le sol et ne bougent PAS",
            "Full extension en bas, squeeze en haut",
            "La gravite fait le travail — zero momentum possible si bien execute",
        ],
        "cues": [
            "Les bras pendent dans le vide, seuls les avant-bras montent",
            "Squeeze en haut, etire en bas",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [15, 140]},
        },
        "safety_notes": "Position anti-triche par design. Ideal pour les gens qui cheat curl tout le temps.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # TRICEPS
    # ══════════════════════════════════════════════════════════════════════

    "tricep_extension": {
        "muscles_primary": ["triceps brachial"],
        "muscles_secondary": [],
        "common_errors": [
            "Coudes qui s'ecartent sur les cotes",
            "Se pencher en avant pour tricher",
            "Amplitude incomplete (surtout en extension)",
            "Mouvement trop rapide",
        ],
        "corrections": [
            "Coudes colles au corps, pointes vers le sol",
            "Corps droit, sangle engagee",
            "Extension COMPLETE — verrouille en bas, squeeze 1 sec",
            "3 sec excentrique (remontee lente et controlee)",
        ],
        "cues": ["Les coudes sont des charnieres — fixes", "Verrouille en bas"],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 130]},
        },
        "safety_notes": "Ne pas charger trop lourd — l'isolation prime sur la force.",
    },

    "skull_crusher": {
        "muscles_primary": ["triceps brachial (chef long surtout)"],
        "muscles_secondary": [],
        "common_errors": [
            "Coudes qui s'ecartent",
            "Barre qui descend vers le front au lieu de derriere la tete",
            "Epaules qui bougent (transforme en pullover)",
        ],
        "corrections": [
            "Coudes fixes, largeur d'epaules",
            "Descends la barre vers le sommet du crane ou derriere",
            "Seuls les avant-bras bougent autour du coude",
        ],
        "cues": ["Ne t'ecrase pas le crane", "Les coudes sont des pivots fixes"],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [40, 140]},
        },
        "safety_notes": "Utiliser la barre EZ pour reduire le stress sur les poignets.",
    },

    "kickback": {
        "muscles_primary": ["triceps brachial"],
        "muscles_secondary": [],
        "common_errors": [
            "Bras qui tombe (pas parallele au sol)",
            "Extension incomplete",
            "Mouvement du coude/epaule",
        ],
        "corrections": [
            "Bras parallele au sol en permanence",
            "Extension complete — squeeze 1 sec",
            "Seul l'avant-bras bouge",
        ],
        "cues": ["Le coude est un pivot fixe", "Squeeze comme si tu faisais un salut militaire"],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 130]},
        },
        "safety_notes": "Exercice leger d'isolation. Pas un mouvement de force.",
    },

    "overhead_tricep": {
        "muscles_primary": ["triceps brachial (longue portion)"],
        "muscles_secondary": ["anconeus"],
        "common_errors": [
            "Coudes qui s'ecartent lateralement",
            "Cambrure lombaire quand la charge monte au-dessus de la tete",
            "Amplitude incomplete — pas d'etirement en bas",
            "Mouvement saccade avec le momentum",
        ],
        "corrections": [
            "Coudes serres, pointes vers le plafond en PERMANENCE",
            "Core engage, cotes basses — le dos ne cambre pas",
            "Descends jusqu'a l'etirement complet de la longue portion (derriere la tete)",
            "Tempo controle: 2-3 sec excentrique, extension explosive",
        ],
        "cues": [
            "Les coudes pointent le plafond et ne bougent pas",
            "Etire bien derriere la tete puis explose en haut",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [30, 140]},
        },
        "safety_notes": "Position overhead = stress sur les epaules. Si douleur, passer a une variante neutre.",
    },

    "close_grip_bench": {
        "muscles_primary": ["triceps brachial", "grand pectoral (faisceau sternal)"],
        "muscles_secondary": ["deltoides anterieurs"],
        "common_errors": [
            "Prise trop serree (poignets en souffrance, instable)",
            "Coudes qui s'ecartent comme un bench classique",
            "Barre qui descend trop haut sur la poitrine",
            "Pas de retraction scapulaire",
        ],
        "corrections": [
            "Prise a largeur d'epaules — pas besoin de plus serre",
            "Coudes COLLES au corps, 20-30 deg d'abduction max",
            "La barre descend vers le bas de la poitrine / sternum",
            "Meme setup que le bench: omoplates retractees, pieds ancres",
        ],
        "cues": [
            "Coudes le long du corps",
            "Pousse la barre vers le plafond, pas vers tes pieds",
            "C'est un bench avec les coudes rentres",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [70, 160]},
            "shoulder_abduction": {"optimal": [15, 35], "note": "coudes proches du corps"},
        },
        "safety_notes": "Memes regles de securite que le bench press. Spotter ou safety pins obligatoires.",
    },

    "diamond_pushup": {
        "muscles_primary": ["triceps brachial"],
        "muscles_secondary": ["grand pectoral", "deltoides anterieurs", "core"],
        "common_errors": [
            "Mains trop ecartees (devient un pushup normal)",
            "Hanches qui s'affaissent (pont inverse)",
            "Coudes qui partent sur les cotes au lieu de rester serres",
            "Amplitude incomplete",
        ],
        "corrections": [
            "Index et pouces se touchent pour former un losange sous la poitrine",
            "Corps gainee de la tete aux pieds — les fesses ne montent pas, ne descendent pas",
            "Coudes glissent le long du torse, pas en croix",
            "Descends jusqu'a ce que la poitrine touche les mains",
        ],
        "cues": [
            "Forme un diamant avec tes mains",
            "Coudes le long du corps, pas en aile de poulet",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [60, 140]},
        },
        "safety_notes": "Exercice poids de corps. Si trop dur, commencer sur les genoux.",
    },

    "cable_overhead_tricep": {
        "muscles_primary": ["triceps brachial (longue portion)"],
        "muscles_secondary": ["anconeus", "core"],
        "common_errors": [
            "Coudes qui s'ecartent sous la charge du cable",
            "Se pencher trop en avant (le dos travaille)",
            "Pas d'etirement complet derriere la tete",
            "Cambrure lombaire",
        ],
        "corrections": [
            "Coudes fixes a cote de la tete, serres",
            "Position split stable, torse incline a 30-45 deg et FIXE",
            "Laisse le cable etirer les triceps a fond derriere la tete",
            "Sangle abdominale engagee, zero cambrure",
        ],
        "cues": [
            "Les coudes sont des charnieres fixes",
            "Etire bien derriere, pousse fort devant",
        ],
        "key_angles": {
            "elbow_flexion": {"optimal_rom": [20, 140]},
        },
        "safety_notes": "Le cable offre une tension constante. Ideal pour la longue portion en etirement.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # QUADRICEPS
    # ══════════════════════════════════════════════════════════════════════

    "squat": {
        "muscles_primary": ["quadriceps", "fessiers"],
        "muscles_secondary": ["ischio-jambiers", "erecteurs spinaux", "core"],
        "common_errors": [
            "Butt wink (retroversion du bassin en bas du squat)",
            "Genoux qui rentrent en valgus (collapse interne)",
            "Talons qui decollent du sol",
            "Flexion excessive du tronc (good morning squat)",
            "Profondeur insuffisante (au-dessus du parallele)",
        ],
        "corrections": [
            "Travaille la mobilite de cheville et de hanche si butt wink",
            "Pousse les genoux vers l'exterieur (en ligne avec les orteils)",
            "Talons ANCRES au sol — mets des cales si mobilite limitee",
            "Bombe le torse, regard droit devant, coudes sous la barre",
            "Descends au minimum cuisses paralleles au sol",
        ],
        "cues": [
            "Assieds-toi entre tes jambes, pas derriere",
            "Pousse le sol avec les pieds — ecrase le sol",
            "Poitrine fiere, regard droit",
        ],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [70, 120], "note": "parallele minimum"},
            "hip_flexion": {"optimal_rom": [60, 100]},
            "trunk_inclination": {"optimal": [15, 45]},
        },
        "safety_notes": "Echauffement obligatoire. Utiliser un safety rack. Ne pas arrondir le bas du dos.",
    },

    "front_squat": {
        "muscles_primary": ["quadriceps (accent)", "fessiers"],
        "muscles_secondary": ["core (anti-flexion)", "erecteurs spinaux"],
        "common_errors": [
            "Coudes qui tombent (barre roule)",
            "Tronc qui s'incline en avant",
            "Genoux en valgus",
            "Manque de mobilite thoracique/poignet",
        ],
        "corrections": [
            "Coudes HAUTS en permanence — au-dessus du parallele",
            "Torse quasi vertical (plus que le back squat)",
            "Genoux tracking sur les orteils",
            "Si mobilite limitee: prise en croix ou sangles",
        ],
        "cues": [
            "Les coudes montent vers le plafond",
            "Le torse est un mur vertical",
        ],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [70, 120]},
            "trunk_inclination": {"optimal": [5, 25], "note": "plus vertical que back squat"},
        },
        "safety_notes": "La barre peut tomber en avant — utiliser les safety pins. Mobilite thoracique essentielle.",
    },

    "hack_squat": {
        "muscles_primary": ["quadriceps"],
        "muscles_secondary": ["fessiers"],
        "common_errors": [
            "Pieds trop haut sur la plateforme (fessiers dominent)",
            "Genoux qui depassent trop les orteils sans controle",
            "Verouillage agressif des genoux en haut",
        ],
        "corrections": [
            "Pieds au milieu de la plateforme, largeur d'epaules",
            "Descends profond mais controle",
            "Ne verrouille pas completement les genoux en haut",
        ],
        "cues": ["Pousse la plateforme avec tout le pied", "Descends aussi bas que ta mobilite le permet"],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [80, 120]},
        },
        "safety_notes": "Machine guidee = plus safe, mais ne pas abuser de l'amplitude.",
    },

    "leg_press": {
        "muscles_primary": ["quadriceps", "fessiers"],
        "muscles_secondary": ["ischio-jambiers"],
        "common_errors": [
            "Bas du dos qui decolle du dossier en bas du mouvement",
            "Verouillage complet des genoux en haut",
            "Pieds trop bas sur la plateforme",
            "Amplitude insuffisante",
        ],
        "corrections": [
            "Le bas du dos reste COLLE au dossier — stop avant qu'il decolle",
            "Ne verrouille JAMAIS les genoux completement",
            "Pieds au milieu, largeur d'epaules",
            "Descends jusqu'a 90 deg de flexion du genou minimum",
        ],
        "cues": ["Le dos reste colle", "Stop avant que les fesses decollent"],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [80, 110]},
        },
        "safety_notes": "DANGER si les genoux se verrouillent sous charge. Toujours garder une legere flexion en haut.",
    },

    "leg_extension": {
        "muscles_primary": ["quadriceps (rectus femoris accent)"],
        "muscles_secondary": [],
        "common_errors": [
            "Decoller les fesses du siege",
            "Extension trop explosive (stress rotulien)",
            "Charge trop lourde pour de l'isolation",
        ],
        "corrections": [
            "Fesses collees, dos contre le dossier",
            "Extension controlee, squeeze 1-2 sec en haut",
            "Charge moderee, 12-15 reps, tempo lent",
        ],
        "cues": ["Squeeze le quad en haut", "Monte lentement, descends encore plus lentement"],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [60, 150]},
        },
        "safety_notes": "Stress sur le tendon rotulien. Contre-indique si douleur au genou. Excentrique lent obligatoire.",
    },

    "bulgarian_split_squat": {
        "muscles_primary": ["quadriceps", "fessiers"],
        "muscles_secondary": ["ischio-jambiers", "stabilisateurs hanche"],
        "common_errors": [
            "Pied avant trop pres du banc",
            "Genou avant qui depasse excessivement les orteils",
            "Tronc qui s'incline trop en avant",
            "Pied arriere qui pousse au lieu de stabiliser",
        ],
        "corrections": [
            "Pied avant assez loin pour que le genou reste au-dessus de la cheville",
            "Le poids est sur le pied AVANT, le pied arriere juste pour l'equilibre",
            "Torse droit, regard devant",
            "Descends jusqu'a ce que le genou arriere frole le sol",
        ],
        "cues": [
            "80% du poids sur le pied avant",
            "Le genou arriere descend vers le sol",
        ],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [60, 110]},
        },
        "safety_notes": "Excellent pour corriger les asymetries. Commencer au poids de corps.",
    },

    "lunge": {
        "muscles_primary": ["quadriceps", "fessiers"],
        "muscles_secondary": ["ischio-jambiers", "stabilisateurs"],
        "common_errors": [
            "Pas trop court (genou depasse les orteils)",
            "Genou en valgus (rentre vers l'interieur)",
            "Tronc penche en avant",
        ],
        "corrections": [
            "Grand pas — le genou avant reste au-dessus de la cheville",
            "Genou tracking sur le 2e orteil",
            "Torse droit, gainage engage",
        ],
        "cues": ["Grand pas, torse droit", "Le genou arriere descend vers le sol"],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [60, 100]},
        },
        "safety_notes": "Commencer sans charge pour maitriser l'equilibre.",
    },

    "goblet_squat": {
        "muscles_primary": ["quadriceps", "fessiers"],
        "muscles_secondary": ["core", "deltoides anterieurs (maintien)"],
        "common_errors": [
            "Coudes qui tombent",
            "Genoux en valgus",
            "Manque de profondeur",
        ],
        "corrections": [
            "Coudes entre les genoux en bas — ils poussent les genoux dehors",
            "Descends aussi bas que possible (ass to grass)",
            "Torse ultra vertical grace a la charge devant",
        ],
        "cues": ["Les coudes ecartent les genoux", "Assieds-toi dans la position la plus basse"],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [80, 130]},
        },
        "safety_notes": "Exercice ideal pour apprendre le squat. Leger.",
    },

    "walking_lunge": {
        "muscles_primary": ["quadriceps", "fessiers"],
        "muscles_secondary": ["ischio-jambiers", "adducteurs", "core"],
        "common_errors": [
            "Genou avant qui depasse largement les orteils a chaque pas",
            "Pas trop court (le genou arriere ne descend pas assez)",
            "Torse penche en avant (perte d'equilibre)",
            "Genou arriere qui tape violemment le sol",
            "Valgus du genou avant (genou qui rentre vers l'interieur)",
        ],
        "corrections": [
            "Grand pas: le tibia avant reste quasi vertical",
            "Le genou arriere descend a 2-3 cm du sol, controle",
            "Torse droit, regard devant, epaules au-dessus des hanches",
            "Pousse avec le talon du pied avant pour avancer",
            "Le genou avant suit la direction du pied — pas de valgus",
        ],
        "cues": [
            "Grand pas, genou arriere frole le sol",
            "Pousse avec le talon avant pour te relever",
            "Torse droit comme un piquet",
        ],
        "key_angles": {
            "knee_flexion_front": {"optimal": [80, 100], "note": "genou avant a ~90 deg"},
            "knee_flexion_rear": {"optimal_rom": [80, 120]},
            "trunk_inclination": {"optimal": [0, 15], "note": "quasi vertical"},
        },
        "safety_notes": "Demande de l'equilibre. Commencer sans charge. Attention au valgus du genou.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # ISCHIO-JAMBIERS
    # ══════════════════════════════════════════════════════════════════════

    "rdl": {
        "muscles_primary": ["ischio-jambiers", "fessiers"],
        "muscles_secondary": ["erecteurs spinaux", "grand dorsal"],
        "common_errors": [
            "Dos rond (flexion lombaire)",
            "Genoux trop flechis (transforme en deadlift)",
            "Barre qui s'eloigne du corps",
            "Pas assez de hip hinge (descente insuffisante)",
        ],
        "corrections": [
            "Dos PLAT en permanence — maintenir la courbure lombaire naturelle",
            "Genoux en legere flexion FIXE (15-20 deg) — seules les hanches bougent",
            "La barre glisse le long des cuisses",
            "Descends jusqu'a sentir l'etirement max des ischio sans perdre le dos",
        ],
        "cues": [
            "Pousse les fesses vers le mur derriere toi",
            "La barre te caresse les cuisses",
            "Etire les ischio, ne plie pas les genoux",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [40, 90]},
            "knee_flexion": {"optimal": [10, 25], "note": "quasi tendus"},
            "trunk_inclination": {"optimal": [30, 70]},
        },
        "safety_notes": "Stop immediatement si le dos arrondit. La charge doit etre maitrisee.",
    },

    "deadlift": {
        "muscles_primary": ["fessiers", "ischio-jambiers", "erecteurs spinaux"],
        "muscles_secondary": ["quadriceps", "trapeze", "grand dorsal", "core"],
        "common_errors": [
            "Dos rond (la blessure classique)",
            "Hanches qui montent avant le torse (stiff-leg involontaire)",
            "Barre qui s'eloigne du corps",
            "Hyperextension en haut (cambrure excessive)",
            "Regarder le plafond (hyperextension cervicale)",
        ],
        "corrections": [
            "Engage les dorsaux AVANT de tirer — la barre ne decolle pas avec un dos rond",
            "Le torse et les hanches montent ensemble — meme angle",
            "La barre reste contre les tibias et cuisses tout le mouvement",
            "En haut: debout droit, hanches verrouilees, PAS de cambrure",
            "Regard neutre — 3m devant toi au sol",
        ],
        "cues": [
            "Pousse le sol avec les pieds — ne tire pas avec le dos",
            "Protege tes aisselles (engage les dorsaux)",
            "La barre te rase les tibias",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [50, 100]},
            "knee_flexion": {"optimal_rom": [20, 50]},
            "trunk_inclination": {"optimal_rom": [30, 70]},
        },
        "safety_notes": "L'exercice le plus risque si mal execute. Dos neutre NON NEGOCIABLE. Ceinture recommandee pour les charges lourdes.",
    },

    "sumo_deadlift": {
        "muscles_primary": ["fessiers", "adducteurs", "quadriceps"],
        "muscles_secondary": ["ischio-jambiers", "erecteurs spinaux"],
        "common_errors": [
            "Genoux qui rentrent en valgus",
            "Hanches qui montent trop vite",
            "Pieds trop ecartes (perd de la puissance)",
        ],
        "corrections": [
            "Genoux tracking sur les orteils — pousse-les dehors",
            "Poitrine haute, hanches et torse montent ensemble",
            "Ecartement: tibias verticaux quand tu es en bas",
        ],
        "cues": ["Ecarte le sol avec tes pieds", "Poitrine haute"],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [40, 80]},
            "knee_flexion": {"optimal_rom": [30, 60]},
        },
        "safety_notes": "Mobilite de hanche necessaire. Ne pas forcer l'ecartement.",
    },

    "leg_curl": {
        "muscles_primary": ["ischio-jambiers"],
        "muscles_secondary": ["gastrocnemiens"],
        "common_errors": [
            "Decoller les hanches du banc",
            "Extension trop rapide (excentrique negligee)",
            "Amplitude incomplete",
        ],
        "corrections": [
            "Hanches COLLEES au banc",
            "Excentrique 3-4 sec — c'est la que le muscle travaille",
            "Extension quasi complete en bas, flexion complete en haut",
        ],
        "cues": ["Flechis lentement", "Hanches collees"],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [30, 130]},
        },
        "safety_notes": "Risque de crampe si deshydrate. Bien s'hydrater avant.",
    },

    "good_morning": {
        "muscles_primary": ["ischio-jambiers", "erecteurs spinaux"],
        "muscles_secondary": ["fessiers"],
        "common_errors": [
            "Dos rond",
            "Descente trop profonde",
            "Charge trop lourde",
        ],
        "corrections": [
            "Dos plat en PERMANENCE",
            "Hip hinge: les fesses reculent, le torse descend",
            "Commencer leger — c'est un exercice d'assistance pas de force",
        ],
        "cues": ["C'est un RDL avec la barre sur le dos", "Fesses vers le mur"],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [30, 70]},
            "trunk_inclination": {"optimal": [30, 60]},
        },
        "safety_notes": "Exercice avance. Maitriser le RDL avant. Charge legere.",
    },

    "nordic_curl": {
        "muscles_primary": ["ischio-jambiers (excentrique)"],
        "muscles_secondary": ["gastrocnemiens", "fessiers"],
        "common_errors": [
            "Casser a la hanche au lieu de descendre avec le corps droit",
            "Descente non controlee (chute libre)",
            "Pas d'utilisation des ischio pour freiner la descente",
            "Se relever avec les bras au lieu des ischio",
        ],
        "corrections": [
            "Corps DROIT de la tete aux genoux — une seule ligne rigide",
            "Descends le plus lentement possible en freinant avec les ischio",
            "Utilise les mains pour te rattraper en bas, puis remonte avec les ischio",
            "Commence avec des excentriques seulement si tu ne peux pas remonter",
        ],
        "cues": [
            "Ton corps est une planche — ne casse pas a la hanche",
            "Freine la descente le plus longtemps possible",
        ],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [10, 90]},
        },
        "safety_notes": "Risque de blessure aux ischio si progression trop rapide. Commencer par des excentriques lentes.",
    },

    "single_leg_rdl": {
        "muscles_primary": ["ischio-jambiers", "fessiers"],
        "muscles_secondary": ["erecteurs spinaux", "stabilisateurs de hanche"],
        "common_errors": [
            "Hanche qui s'ouvre (rotation du bassin)",
            "Dos rond parce que la mobilite manque",
            "Genou d'appui qui verrouille completement",
            "Perte d'equilibre a chaque rep",
            "Pas assez de hip hinge (descente insuffisante)",
        ],
        "corrections": [
            "Les deux hanches restent PARALLELES au sol — pas de rotation",
            "Dos plat: arrete la descente avant que le dos arrondisse",
            "Legere flexion du genou d'appui (10-20 deg) et fixe",
            "Regard fixe sur un point au sol a 2m devant toi",
            "La jambe arriere monte EN MEME TEMPS que le torse descend — contrepoids",
        ],
        "cues": [
            "Tu es une balancoire: la jambe arriere monte quand le torse descend",
            "Hanches paralleles au sol en permanence",
            "Pousse les fesses vers le mur derriere",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [30, 90]},
            "knee_flexion": {"optimal": [10, 25], "note": "jambe d'appui quasi tendue"},
        },
        "safety_notes": "Exercice d'equilibre et de stabilite. Commencer sans charge. Maitriser le RDL bilateral d'abord.",
    },

    "glute_ham_raise": {
        "muscles_primary": ["ischio-jambiers", "fessiers"],
        "muscles_secondary": ["erecteurs spinaux", "gastrocnemiens"],
        "common_errors": [
            "Extension lombaire au lieu de l'extension de hanche",
            "Pas de squeeze des fessiers en position haute",
            "Descente trop rapide (phase excentrique negligee)",
            "Utiliser les bras pour se relever",
        ],
        "corrections": [
            "Le mouvement commence par l'extension de hanche (fessiers) PUIS extension du genou (ischio)",
            "Squeeze les fessiers 1-2 sec en position haute, corps aligne",
            "Controle la descente 3 sec minimum — c'est la ou l'hypertrophie se fait",
            "Les bras sont croises sur la poitrine ou derriere la tete",
        ],
        "cues": [
            "Fesses d'abord, puis deplie les genoux",
            "Controle la descente, ne tombe pas",
            "Corps droit en haut, squeeze les fesses",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [0, 90]},
            "knee_flexion": {"optimal_rom": [20, 90]},
        },
        "safety_notes": "Exercice avance. Utiliser l'assistance (bande elastique) si necessaire au debut.",
    },

    "trap_bar_deadlift": {
        "muscles_primary": ["quadriceps", "fessiers", "ischio-jambiers"],
        "muscles_secondary": ["erecteurs spinaux", "trapeze", "core"],
        "common_errors": [
            "Dos rond (meme probleme que le deadlift conventionnel)",
            "Hanches trop hautes au depart (stiff-leg involontaire)",
            "Tirer avec les bras au lieu de pousser le sol",
            "Hyperextension en haut",
            "Se pencher en avant au lieu de rester centre dans la barre",
        ],
        "corrections": [
            "Poitrine haute, dos plat, omoplates engagees avant de tirer",
            "Hanches entre les genoux et les epaules — position mi-squat mi-deadlift",
            "POUSSE le sol avec les pieds, ne tire pas la barre",
            "En haut: debout droit, hanches verrouillees, pas de cambrure",
            "Centre de gravite au milieu de la trap bar, pas devant",
        ],
        "cues": [
            "Pousse le sol, ne tire pas la barre",
            "Reste au centre de la barre",
            "Poitrine haute, dos plat",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [40, 90]},
            "knee_flexion": {"optimal_rom": [60, 110]},
            "trunk_inclination": {"optimal": [20, 50], "note": "plus vertical qu'un deadlift classique"},
        },
        "safety_notes": "Plus safe que le deadlift conventionnel (charge centree). Excellent pour debutants en deadlift.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # FESSIERS
    # ══════════════════════════════════════════════════════════════════════

    "hip_thrust": {
        "muscles_primary": ["fessiers (grand gluteal)"],
        "muscles_secondary": ["ischio-jambiers", "quadriceps"],
        "common_errors": [
            "Hyperextension lombaire en haut",
            "Pieds trop loin ou trop pres",
            "Pas de squeeze en haut",
            "Menton qui remonte (hyperextension cervicale)",
        ],
        "corrections": [
            "En haut: hanches verrouillees, ZERO cambrure — PPT (posterior pelvic tilt)",
            "Pieds places pour avoir les tibias verticaux en position haute",
            "Squeeze les fesses 2 sec en haut de chaque rep",
            "Menton rentre (regard vers les genoux en haut)",
        ],
        "cues": [
            "Serre les fesses comme si tu retenais un billet",
            "Pousse le plafond avec les hanches",
            "Le menton suit le mouvement — regard vers les genoux",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [40, 90]},
            "knee_flexion": {"optimal": [80, 100]},
        },
        "safety_notes": "Utiliser un pad de protection pour la barre. Ne pas hyperetendre le dos.",
    },

    "glute_bridge": {
        "muscles_primary": ["fessiers"],
        "muscles_secondary": ["ischio-jambiers"],
        "common_errors": [
            "Extension lombaire au lieu de l'extension de hanche",
            "Pas de squeeze en haut",
        ],
        "corrections": [
            "PPT en haut — bascule le bassin pour activer les fessiers",
            "Squeeze 2-3 sec en haut",
        ],
        "cues": ["Serre les fesses", "Le mouvement vient des hanches pas du dos"],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [30, 80]},
        },
        "safety_notes": "Exercice safe. Ideal pour l'activation.",
    },

    "step_up": {
        "muscles_primary": ["quadriceps", "fessiers"],
        "muscles_secondary": ["ischio-jambiers", "stabilisateurs"],
        "common_errors": [
            "Pousser avec le pied arriere au lieu du pied avant",
            "Pencher le torse en avant",
            "Box trop haute",
        ],
        "corrections": [
            "TOUT le travail se fait avec le pied sur la box",
            "Torse droit",
            "Hauteur: genou a 90 deg max",
        ],
        "cues": ["Pousse avec le pied d'en haut", "Le pied au sol ne t'aide pas"],
        "key_angles": {
            "knee_flexion": {"optimal_rom": [60, 100]},
        },
        "safety_notes": "Commencer sans charge pour maitriser l'equilibre.",
    },

    "cable_kickback": {
        "muscles_primary": ["fessiers (grand gluteal)"],
        "muscles_secondary": ["ischio-jambiers"],
        "common_errors": [
            "Cambrure lombaire pour donner plus d'amplitude",
            "Mouvement trop rapide sans contraction en haut",
            "La hanche s'ouvre (rotation externe pour tricher)",
            "Charge trop lourde — tout le corps compense",
        ],
        "corrections": [
            "Sangle abdominale engagee, dos NEUTRE en permanence",
            "Squeeze le fessier 1-2 sec en extension complete",
            "La hanche reste parallele au sol, zero rotation",
            "Leger — c'est de l'isolation, 12-20 reps",
        ],
        "cues": [
            "Pousse le talon vers le mur derriere",
            "Squeeze la fesse en haut comme si tu serrais une piece",
        ],
        "key_angles": {
            "hip_extension": {"optimal_rom": [0, 30], "note": "pas besoin de grande amplitude"},
        },
        "safety_notes": "Exercice d'isolation. La charge ne devrait jamais forcer une compensation lombaire.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # MOLLETS
    # ══════════════════════════════════════════════════════════════════════

    "calf_raise": {
        "muscles_primary": ["gastrocnemiens"],
        "muscles_secondary": ["soleaire"],
        "common_errors": [
            "Amplitude incomplete (demi-reps)",
            "Rebond en bas sans pause",
            "Genoux flechis (soleaire au lieu de gastrocnemiens)",
        ],
        "corrections": [
            "Full ROM: etirement COMPLET en bas, montee COMPLETE en haut",
            "Pause 1 sec en bas (etirement), squeeze 1 sec en haut",
            "Jambes quasi tendues pour cibler les gastrocnemiens",
        ],
        "cues": ["Monte sur la pointe le plus haut possible", "Etire-toi completement en bas"],
        "key_angles": {},
        "safety_notes": "Les mollets repondent aux hautes reps (15-25) et au tempo lent.",
    },

    "seated_calf_raise": {
        "muscles_primary": ["soleaire"],
        "muscles_secondary": ["gastrocnemiens (reduit car genoux flechis)"],
        "common_errors": [
            "Rebond en bas au lieu d'un etirement controle",
            "Amplitude incomplete (demi-reps chroniques)",
            "Charge sur la pointe des pieds au lieu de l'avant-pied",
            "Tempo trop rapide sans contraction en haut",
        ],
        "corrections": [
            "Pause 2 sec en etirement COMPLET en bas, pause 1 sec en contraction en haut",
            "Full ROM a chaque rep — etirement max en bas, montee max en haut",
            "Avant-pieds sur la plateforme, talons dans le vide",
            "Tempo lent: 2 sec montee, 1 sec squeeze, 3 sec descente",
        ],
        "cues": [
            "Etire-toi completement en bas, monte le plus haut possible",
            "Lent et controle — les mollets repondent au temps sous tension",
        ],
        "key_angles": {},
        "safety_notes": "Genoux flechis = soleaire cible. Hautes reps (15-30). Complement indispensable du calf raise debout.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # ABDOS
    # ══════════════════════════════════════════════════════════════════════

    "crunch": {
        "muscles_primary": ["rectus abdominis"],
        "muscles_secondary": ["obliques"],
        "common_errors": [
            "Tirer sur la nuque avec les mains",
            "Monter trop haut (psoas prend le relais)",
            "Mouvement trop rapide sans contraction",
        ],
        "corrections": [
            "Mains derriere la tete SANS tirer — ou croisees sur la poitrine",
            "Decolle les omoplates du sol seulement (15-20 deg)",
            "Squeeze 1-2 sec en haut, excentrique controle",
        ],
        "cues": ["Rapproche les cotes du bassin", "Ne tire pas sur ta tete"],
        "key_angles": {},
        "safety_notes": "Pas recommande si hernie discale. Preferer le gainage.",
    },

    "hanging_leg_raise": {
        "muscles_primary": ["rectus abdominis (partie basse)", "psoas"],
        "muscles_secondary": ["obliques", "grip"],
        "common_errors": [
            "Balancement du corps",
            "Utiliser l'inertie au lieu des abdos",
            "Ne monter que les genoux sans basculer le bassin",
        ],
        "corrections": [
            "Corps stable — zero balancement",
            "Mouvement lent et controle",
            "La CLE: basculer le bassin (PPT) en haut pour activer les abdos",
        ],
        "cues": ["Bascule le bassin en haut", "Le secret c'est le PPT pas les jambes"],
        "key_angles": {},
        "safety_notes": "Exercice avance. Maitriser le crunch inverse au sol avant.",
    },

    "cable_crunch": {
        "muscles_primary": ["rectus abdominis"],
        "muscles_secondary": ["obliques"],
        "common_errors": [
            "Flechir les hanches au lieu de la colonne",
            "Tirer avec les bras",
        ],
        "corrections": [
            "Le mouvement vient de la flexion de la colonne, pas des hanches",
            "Les bras sont fixes — la corde reste au niveau de la tete",
        ],
        "cues": ["Rapproche les cotes du bassin", "Les bras ne bougent pas"],
        "key_angles": {},
        "safety_notes": "Bonne option pour charger les abdos progressivement.",
    },

    "ab_wheel": {
        "muscles_primary": ["rectus abdominis", "obliques"],
        "muscles_secondary": ["grand dorsal", "deltoides", "hip flexors"],
        "common_errors": [
            "Cambrure lombaire en extension (le bas du dos lache)",
            "Hanches qui descendent en premier au lieu du torse",
            "Amplitude trop grande pour le niveau (s'effondrer en extension)",
            "Retour en tirant avec les bras au lieu des abdos",
        ],
        "corrections": [
            "PPT (bassin en retroversion) AVANT de commencer a rouler",
            "Le mouvement part des epaules: les bras s'eloignent en avant",
            "Commence avec une amplitude reduite, progresse sur des semaines",
            "Pour revenir: contracte les abdos pour ramener la roue, pas les bras",
        ],
        "cues": [
            "Rentre le nombril vers la colonne en permanence",
            "Pousse le sol loin de toi puis ramene-le avec les abdos",
            "Si le dos cambre, tu es alle trop loin",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [30, 170], "note": "de flechis a quasi aligne"},
            "shoulder_flexion": {"optimal_rom": [90, 180]},
        },
        "safety_notes": "Exercice avance. Maitriser le dead bug et le plank avant. Stop si douleur lombaire.",
    },

    "plank": {
        "muscles_primary": ["rectus abdominis", "transverse abdominis"],
        "muscles_secondary": ["obliques", "erecteurs spinaux", "deltoides", "fessiers"],
        "common_errors": [
            "Hanches trop hautes (en tente)",
            "Hanches qui s'affaissent (cambrure lombaire)",
            "Tete qui pend ou qui regarde devant",
            "Respiration bloquee",
        ],
        "corrections": [
            "Corps aligne de la tete aux talons — UNE SEULE LIGNE",
            "Serre les fessiers ET les abdos en meme temps",
            "Tete dans le prolongement de la colonne — regard vers le sol",
            "Respirer normalement en maintenant le gainage",
        ],
        "cues": [
            "Imagine une planche rigide de la tete aux pieds",
            "Serre les fesses et rentre le ventre",
        ],
        "key_angles": {
            "trunk_alignment": {"optimal": [170, 180], "note": "corps quasi rectiligne"},
        },
        "safety_notes": "Si douleur lombaire, les hanches sont probablement trop basses. Commencer par des series courtes (20-30 sec).",
    },

    "woodchop": {
        "muscles_primary": ["obliques", "rectus abdominis"],
        "muscles_secondary": ["deltoides", "core", "fessiers", "quadriceps"],
        "common_errors": [
            "Tirer avec les bras au lieu de tourner avec le tronc",
            "Pieds qui ne pivotent pas (torsion lombaire forcee)",
            "Mouvement trop rapide sans controle",
            "Flexion lombaire au lieu de rotation",
        ],
        "corrections": [
            "Le mouvement vient de la ROTATION du tronc, les bras suivent",
            "Les pieds et les hanches pivotent avec le mouvement — pas de torsion forcee",
            "Controle le mouvement dans les deux sens, surtout le retour",
            "Le tronc tourne, il ne flechit pas — reste grand",
        ],
        "cues": [
            "Tourne le torse, les bras sont juste des leviers",
            "Les pieds suivent la rotation",
            "Explose en rotation, controle le retour",
        ],
        "key_angles": {
            "trunk_rotation": {"optimal_rom": [0, 60], "note": "rotation controlee"},
        },
        "safety_notes": "Ne pas forcer la rotation si manque de mobilite thoracique. Commencer leger au cable.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # FULL BODY / FONCTIONNEL
    # ══════════════════════════════════════════════════════════════════════

    "kettlebell_swing": {
        "muscles_primary": ["fessiers", "ischio-jambiers"],
        "muscles_secondary": ["erecteurs spinaux", "core", "deltoides"],
        "common_errors": [
            "Squat au lieu de hip hinge",
            "Tirer avec les bras/epaules",
            "Hyperextension en haut",
            "Dos rond en bas",
        ],
        "corrections": [
            "C'est un HIP HINGE pas un squat — les hanches reculent",
            "Les bras sont des cordes — la puissance vient des hanches",
            "En haut: debout droit, fesses serrees, pas de cambrure",
            "Dos plat en permanence",
        ],
        "cues": [
            "Casse-toi en deux comme une charniere",
            "Explose avec les hanches",
            "Les bras ne tirent pas",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [40, 80]},
        },
        "safety_notes": "Apprendre le hip hinge avant. Risque lombaire si mal execute.",
    },

    "clean": {
        "muscles_primary": ["quadriceps", "fessiers", "trapeze", "deltoides"],
        "muscles_secondary": ["ischio-jambiers", "erecteurs spinaux", "biceps"],
        "common_errors": [
            "Tirer avec les bras trop tot",
            "Dos rond au premier pull",
            "Pas de triple extension (chevilles, genoux, hanches)",
        ],
        "corrections": [
            "Premier pull = deadlift, deuxieme pull = explosion des hanches",
            "Dos plat, poitrine haute",
            "Triple extension explosive PUIS reception sous la barre",
        ],
        "cues": ["Pousse le sol", "Les bras tirent APRES les hanches"],
        "key_angles": {},
        "safety_notes": "Exercice technique avance. Apprendre avec un coach. Commencer a la barre vide.",
    },

    "thruster": {
        "muscles_primary": ["quadriceps", "fessiers", "deltoides", "triceps"],
        "muscles_secondary": ["core", "erecteurs spinaux"],
        "common_errors": [
            "Separer le squat du press (deux mouvements au lieu d'un)",
            "Coudes qui tombent en bas du squat",
            "Cambrure en haut du press",
        ],
        "corrections": [
            "Un seul mouvement fluide: squat → press sans pause",
            "Coudes hauts comme un front squat",
            "Sangle engagee en haut, pas de cambrure",
        ],
        "cues": ["Explose du squat directement dans le press", "Un mouvement fluide"],
        "key_angles": {},
        "safety_notes": "Cardio intense. Bien maitriser front squat et OHP separement.",
    },

    "snatch": {
        "muscles_primary": ["quadriceps", "fessiers", "deltoides", "trapeze"],
        "muscles_secondary": ["ischio-jambiers", "erecteurs spinaux", "triceps", "core"],
        "common_errors": [
            "Tirer avec les bras trop tot (pas de triple extension)",
            "Dos rond au premier pull",
            "Reception bras pas verrouilles overhead",
            "Barre qui part en avant au lieu de rester proche du corps",
            "Pas de squat de reception (starfish au lieu de OHS)",
        ],
        "corrections": [
            "Premier pull = deadlift lent. Deuxieme pull = explosion des hanches. Troisieme pull = se tirer SOUS la barre",
            "Dos plat, poitrine haute, epaules au-dessus de la barre au depart",
            "Reception avec les bras VERROUILLES, barre au-dessus du centre de gravite",
            "La barre reste proche: elle frole le torse pendant le pull",
            "Se tirer sous la barre en position overhead squat",
        ],
        "cues": [
            "Pousse le sol, puis EXPLOSE des hanches",
            "Tire-toi sous la barre, ne la tire pas vers le haut",
            "Bras verrouilles en reception, pieds a plat",
        ],
        "key_angles": {
            "hip_flexion": {"optimal_rom": [30, 170]},
            "knee_flexion": {"optimal_rom": [60, 170]},
        },
        "safety_notes": "Exercice TRES technique. Coaching obligatoire. Apprendre les progressions (muscle snatch, power snatch, hang snatch) avant le full snatch.",
    },

    "battle_rope": {
        "muscles_primary": ["deltoides", "core"],
        "muscles_secondary": ["biceps brachial", "avant-bras", "fessiers", "quadriceps"],
        "common_errors": [
            "Bouger avec les epaules seulement (pas d'implication du corps)",
            "Dos rond et epaules voutees",
            "Amplitude trop petite (ondes qui ne voyagent pas)",
            "Rester debout jambes tendues",
        ],
        "corrections": [
            "Le mouvement vient des hanches et du core, pas juste des bras",
            "Position athletique: genoux flechis, dos neutre, poitrine haute",
            "Grandes ondes puissantes qui voyagent jusqu'au point d'ancrage",
            "Quart de squat, pieds largeur d'epaules, centre de gravite bas",
        ],
        "cues": [
            "Reste bas, bouge fort",
            "Les ondes doivent toucher le point d'ancrage",
            "Tout le corps travaille, pas juste les bras",
        ],
        "key_angles": {
            "knee_flexion": {"optimal": [20, 40], "note": "position athletique flechie"},
        },
        "safety_notes": "Exercice cardio intense. Commencer par des intervalles courts (20 sec ON / 40 sec OFF).",
    },
}


def get_exercise_kb(exercise_name: str) -> dict | None:
    """Retourne la fiche KB d'un exercice ou None si inconnu."""
    return EXERCISE_KB.get(exercise_name)


def get_kb_prompt_section(exercise_name: str) -> str:
    """Genere une section de prompt avec les infos KB pour le report generator."""
    kb = get_exercise_kb(exercise_name)
    if not kb:
        return ""

    parts = []
    parts.append("=== BASE DE CONNAISSANCES BIOMECANIQUE ===")
    parts.append("Muscles principaux : {}".format(", ".join(kb.get("muscles_primary", []))))
    parts.append("Muscles secondaires : {}".format(", ".join(kb.get("muscles_secondary", []))))

    errors = kb.get("common_errors", [])
    if errors:
        parts.append("\nERREURS COURANTES A VERIFIER :")
        for i, e in enumerate(errors, 1):
            parts.append("{}. {}".format(i, e))

    corrections = kb.get("corrections", [])
    if corrections:
        parts.append("\nCORRECTIONS A PROPOSER SI PERTINENT :")
        for i, c in enumerate(corrections, 1):
            parts.append("{}. {}".format(i, c))

    cues = kb.get("cues", [])
    if cues:
        parts.append("\nCUES COACHING :")
        for c in cues:
            parts.append("- {}".format(c))

    safety = kb.get("safety_notes", "")
    if safety:
        parts.append("\nSECURITE : {}".format(safety))

    parts.append("=== FIN KB ===")
    return "\n".join(parts)
