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
