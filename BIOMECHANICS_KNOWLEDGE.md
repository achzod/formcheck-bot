# FORMCHECK by ACHZOD — Base de Connaissances Biomécanique

> Version 2.0 — Février 2026
> Auteur : ACHZOD (11 certifications : NASM-CPT, NASM-CES, ISSA-CPT, ISSA Glute Specialist, Precision Nutrition L1, Pre-Script Level 1, NASM-PES, ISSA Bodybuilding, NASM-SFS, ISSA Nutrition, Precision Nutrition L2)

---

## TABLE DES MATIÈRES

1. [System Prompt LLM](#section-1--system-prompt-llm)
2. [Principes Universels de Biomécanique](#section-2--principes-universels-de-biomécanique)
3. [Référentiels par Exercice](#section-3--référentiels-par-exercice)
   - 3.1 Jambes — Quadriceps dominants (ex. 1-11)
   - 3.2 Jambes — Postérieur (ex. 12-23)
   - 3.3 Poitrine (ex. 24-31)
   - 3.4 Dos (ex. 32-41)
   - 3.5 Épaules (ex. 42-50)
   - 3.6 Bras (ex. 51-62)
   - 3.7 Core (ex. 63-68)
   - 3.8 Mollets (ex. 69-70)
4. [Scoring Détaillé /100](#section-4--scoring-détaillé-100)
5. [Détection d'Exercice via MediaPipe](#section-5--détection-dexercice-via-mediapipe)

---

# SECTION 1 — GUIDE D'ANALYSE BIOMÉCANIQUE EXPERT

## Philosophie d'Analyse

Tu es un praticien avec 11 certifications internationales. Ton analyse ne se limite pas à "l'angle du genou est bon/mauvais". Tu analyses le MOUVEMENT COMPLET comme un système intégré :

### Les 5 piliers d'une analyse experte

1. AMPLITUDE DE MOUVEMENT (ROM)
- Chaque articulation a un ROM optimal spécifique à l'exercice
- Un ROM incomplet = recrutement musculaire partiel, adaptation raccourcie
- Un ROM excessif sans contrôle = risque articulaire
- Le ROM doit être CONSTANT entre les reps. Une dégradation > 10% indique : charge trop lourde, fatigue technique, ou limitation de mobilité
- Référence : angle articulaire mesuré vs angle optimal de la Section 3

2. TEMPO ET PHASES DU MOUVEMENT
Le tempo révèle le CONTRÔLE NEUROMUSCULAIRE du pratiquant.

Phase excentrique (descente/retour) :
- Durée optimale : 2-4 secondes pour hypertrophie, 1-2s pour force
- Un excentrique < 1 seconde = perte de contrôle, charge trop lourde, ou habitude de "tomber" dans le mouvement
- Le contrôle excentrique protège les tendons (Achille, rotulien, sus-épineux) et les structures passives
- La phase excentrique est responsable de la MAJORITÉ des dommages musculaires mécaniques → principal driver d'hypertrophie

Phase concentrique (effort) :
- Devrait être intentionnellement EXPLOSIVE (intention de vitesse maximale même si la barre bouge lentement)
- Si la concentrique ralentit significativement d'une rep à l'autre → fatigue du système nerveux
- Le sticking point (point le plus lent) révèle la faiblesse musculaire spécifique

Phase isométrique :
- Pause en bas : élimine le stretch-reflex (réflexe myotatique), force un recrutement musculaire pur
- Pause en haut (lockout) : reset respiratoire, re-bracing
- Absence totale de pause + rebond rapide en bas = exploitation du stretch-reflex au détriment du contrôle
- Un temps isométrique > 0 au point bas est un signe de maturité technique

Tempo ratio (excentrique/concentrique) :
- Ratio 2:1 à 3:1 = bon contrôle (2-3x plus lent en descente qu'en montée)
- Ratio 1:1 = manque de contrôle excentrique, "drop and push"
- Ratio > 4:1 = excentrique trop lent (fatigue inutile ou peur)

Consistance inter-reps :
- Le tempo doit être REPRODUCTIBLE. Une variation > 25% entre les reps indique une perte de contrôle technique
- Les dernières reps sont naturellement plus lentes en concentrique (fatigue) — c'est normal
- Mais si l'excentrique ACCÉLÈRE sur les dernières reps = la technique se dégrade sous fatigue

Time Under Tension (TUT) :
- Hypertrophie optimale : 30-60 secondes par série
- Force : 10-20 secondes par série
- Endurance : 60-120 secondes par série
- Un TUT trop court avec beaucoup de reps = tempo trop rapide, perte de stimulus

3. PATTERNS DE COMPENSATION
Les compensations sont les stratégies INVOLONTAIRES que le corps utilise pour contourner une faiblesse ou une limitation de mobilité.

Hip shift (déplacement latéral du bassin) :
- Cause : asymétrie de force entre les abducteurs/adducteurs ou les extenseurs de hanche
- Risque : surcharge unilatérale du rachis, hernie discale à long terme
- Visible quand le bassin se déplace de > 5% de la largeur des hanches

Butt wink (rétroversion pelvienne en bas du squat) :
- Cause : limitation de mobilité de hanche (anatomie du cotyle), raideur des ischio-jambiers, faiblesse des fléchisseurs de hanche profonds
- Risque : flexion lombaire sous compression = position la plus dangereuse pour les disques intervertébraux
- Tolérance : < 10° acceptable si pas de douleur. > 15° = danger, surtout avec charge

Squat morning (hanches montent avant les épaules) :
- Cause : ratio force quadriceps/extenseurs de hanche déséquilibré (quadriceps faibles par rapport aux fessiers/ischio)
- Conséquence : transforme le squat en exercice de dos, stress lombaire x3
- Détection : taux de changement d'angle du genou vs hanche en phase concentrique

Inclinaison latérale du tronc :
- Cause : obliques asymétriques, faiblesse du carré des lombes controlatéral
- Souvent combiné avec un hip shift (compensation croisée)

Élévation scapulaire (épaules qui montent vers les oreilles) :
- Cause : dominance des trapèzes supérieurs par rapport aux trapèzes inférieurs et au serratus anterior
- Fréquent sur : OHP, élévations latérales, développé couché
- Conséquence : impingement sous-acromial, syndrome de conflit d'épaule

4. BRAS DE LEVIER ET MORPHOLOGIE
La morphologie du pratiquant EXPLIQUE pourquoi il bouge comme il bouge. Ne jamais pénaliser une adaptation morphologique légitime.

Ratio fémur/tibia :
- Fémur long + tibia court = le genou avance moins, le torse doit pencher plus
- Ce n'est PAS une erreur technique, c'est de la physique
- Un coach incompétent dirait "redresse-toi". Un coach expert dit "ton inclinaison est normale vu tes proportions"

Ratio torse/fémur :
- Torse long = avantage au squat (moins d'inclinaison), désavantage au deadlift (plus de ROM)
- Torse court = plus d'inclinaison au squat (normal), avantage au deadlift

Bras de levier articulaires (moment arms) :
- Le bras de levier au genou = distance horizontale entre le genou et la verticale passant par la cheville
- Plus il est grand, plus le moment de force sur les quadriceps est élevé
- Important pour comprendre la répartition du stress : quad-dominant vs hip-dominant

5. ANALYSE DE FATIGUE
La technique se dégrade au fil des reps. L'analyse doit comparer les premières et dernières reps.

Signes de fatigue :
- ROM qui diminue (le pratiquant "triche" en réduisant l'amplitude)
- Tempo excentrique qui accélère (perte de contrôle)
- Symétrie qui se dégrade (un côté fatigue avant l'autre)
- Compensations qui apparaissent ou s'aggravent
- Vitesse concentrique qui chute (normal) vs technique qui change (problématique)

Fatigue acceptable vs problématique :
- Concentrique plus lent sur les dernières reps = NORMAL (fatigue métabolique)
- Excentrique plus rapide + compensations = PROBLÉMATIQUE (fatigue technique → arrêter ou réduire la charge)

## Ton et Style du Rapport

- Tutoiement systématique — on parle de coach à élève
- Direct et expert — pas de blabla
- Accessible — terme technique toujours expliqué
- Jamais condescendant
- Professionnel — ZERO emoji, ZERO markdown
- Chaque affirmation est justifiée par une donnée mesurée
- Le rapport doit lire comme un bilan d'expert qui a regardé la vidéo en personne

---

# SECTION 2 — PRINCIPES UNIVERSELS DE BIOMÉCANIQUE

Ces principes s'appliquent à la quasi-totalité des exercices. Le LLM doit les connaître et les appliquer contextuellement.

## 2.1 Respiration et Bracing

### La Manœuvre de Valsalva

La manœuvre de Valsalva consiste à prendre une grande inspiration (environ 70-80% de capacité), bloquer la respiration, et contracter les abdominaux comme si tu allais recevoir un coup au ventre. Cela crée une **pression intra-abdominale (PIA)** qui stabilise la colonne vertébrale comme un corset naturel.

**Quand l'utiliser :**
- Tous les exercices composés lourds (squat, deadlift, bench press, overhead press)
- Phase concentrique ET début de phase excentrique
- Charges > 70% du 1RM

**Quand NE PAS l'utiliser :**
- Exercices d'isolation légers (curls, élévations latérales)
- Personnes avec hypertension non contrôlée (recommander de consulter)
- Séries longues (> 12 reps) — privilégier la respiration rythmique

**Pattern respiratoire standard :**
1. Inspirer en haut du mouvement (position de départ)
2. Bracing (contraction abdominale, Valsalva)
3. Phase excentrique (descente) — maintenir le brace
4. Point bas — toujours en apnée
5. Phase concentrique (montée) — expirer progressivement après le point de difficulté ("sticking point"), ou maintenir jusqu'au lockout puis expirer
6. Reset en haut si nécessaire

**Erreurs de respiration détectables :**
- Épaules qui montent excessivement à l'inspiration → respiration thoracique au lieu de diaphragmatique
- Ventre qui se creuse → aspiration au lieu de bracing (erreur courante chez les femmes à cause du fitness "rentre ton ventre")
- Perte de rigidité visible au milieu de la rep → le brace a lâché

### Respiration Rythmique (exercices légers/isolation)

- Expirer pendant la phase concentrique (effort)
- Inspirer pendant la phase excentrique (retour)
- Ne jamais bloquer la respiration sur des séries longues d'isolation

## 2.2 Tempo et Contrôle Excentrique

### Notation du Tempo

Le tempo s'exprime en 4 chiffres : **Excentrique / Pause bas / Concentrique / Pause haut**
Exemple : 3-1-1-0 = 3 secondes de descente, 1 seconde de pause en bas, 1 seconde de montée, 0 pause en haut.

### Importance du Contrôle Excentrique

- La phase excentrique génère **plus de dommages musculaires** (et donc d'hypertrophie) que la concentrique
- Un excentrique contrôlé (2-4 secondes) assure une meilleure activation des fibres musculaires
- Un excentrique trop rapide (< 1 seconde) = signe de charge trop lourde ou de manque de contrôle
- Un excentrique contrôlé protège les articulations et les tendons

**Détection via MediaPipe :**
- Mesurer le temps entre le début et la fin de la phase excentrique
- Si < 1 seconde sur un squat/bench/deadlift → signaler "excentrique trop rapide"
- Si la vitesse excentrique est irrégulière (accélération en fin de mouvement) → perte de contrôle

### Quand Utiliser un Tempo Lent

- Apprentissage moteur (débutants) : 3-1-2-0
- Hypertrophie : 3-1-1-0 ou 4-0-1-0
- Réhabilitation : 4-2-2-1
- Force : 2-0-X-1 (X = aussi vite que possible en concentrique)

## 2.3 Stabilité Scapulaire

Les omoplates (scapulae) sont la fondation de TOUT mouvement du haut du corps. Leur position détermine la santé de l'épaule et l'efficacité du mouvement.

### Les 4 Positions Scapulaires

1. **Rétraction** (omoplates serrées vers la colonne) — bench press, rows
2. **Protraction** (omoplates écartées, vers l'avant) — push-ups en fin de mouvement, serratus anterior
3. **Dépression** (omoplates tirées vers le bas) — pull-ups, lat pulldown, presque tous les exercices
4. **Élévation** (omoplates montées vers les oreilles) — shrugs uniquement

### Règles Scapulaires par Type d'Exercice

| Type | Position scapulaire |
|------|-------------------|
| Press horizontal (bench, push-up) | Rétraction + dépression |
| Press vertical (OHP) | Rotation vers le haut libre (upward rotation) |
| Tirage horizontal (rows) | Rétraction + dépression à la contraction |
| Tirage vertical (pull-up, pulldown) | Dépression + légère rétraction en bas |
| Isolation épaules (élévations) | Dépression (pas de haussement) |

### Détection via MediaPipe

- **Élévation excessive des épaules** : landmark épaule (11/12) monte au-dessus de sa position de départ de > 3 cm → compensation par les trapèzes supérieurs
- **Asymétrie scapulaire** : différence de hauteur entre épaules G/D > 2 cm → déséquilibre musculaire ou mauvaise habitude
- **Perte de rétraction au bench** : épaules (11/12) avancent vers l'avant pendant la phase concentrique → instabilité, risque pour l'épaule

## 2.4 Neutralité de la Colonne Vertébrale

### Les 3 Segments

**Colonne cervicale (cou) :**
- Position neutre = regard naturellement devant soi ou légèrement vers le bas
- Erreur courante : hyperextension cervicale (regarder le plafond au squat/deadlift) — compresse les disques cervicaux
- Erreur inverse : flexion excessive (menton sur la poitrine) — tire sur la chaîne postérieure
- Détection MediaPipe : angle entre l'oreille (landmarks 7/8), l'épaule (11/12) et la hanche (23/24). Angle < 150° = flexion cervicale excessive. Angle > 190° = hyperextension.

**Colonne thoracique (milieu du dos) :**
- Légère cyphose naturelle (courbure vers l'arrière) est normale
- Cyphose excessive = épaules arrondies vers l'avant → fréquent chez les personnes assises toute la journée
- Extension thoracique = position recherchée au bench press et squat
- Détection : angle entre épaule (11/12), milieu du torse (approximé) et hanche (23/24)

**Colonne lombaire (bas du dos) :**
- Légère lordose naturelle (creux du bas du dos) est NORMALE et SOUHAITÉE
- **Flexion lombaire ("butt wink", arrondissement)** = DANGER sous charge. Les disques lombaires sont en position vulnérable en flexion + compression
- **Hyperextension lombaire** = cambrure excessive, souvent en haut du hip thrust ou du deadlift → compression des facettes articulaires
- Détection MediaPipe : angle entre épaule (11/12), hanche (23/24) et genou (25/26). Changement de cet angle pendant le mouvement = perte de neutralité lombaire. Spécifiquement, si l'angle hanche diminue soudainement en bas du squat → butt wink.

### Tolérance Selon l'Exercice

- **Squat** : léger butt wink (< 10° de flexion lombaire en fin de ROM) tolérable si pas de douleur
- **Deadlift** : ZÉRO flexion lombaire tolérée sous charge maximale
- **Hip Thrust** : ZÉRO hyperextension lombaire en haut — le mouvement finit quand les hanches sont alignées avec le torse
- **Overhead Press** : hyperextension lombaire compensatoire fréquente → signe de charge trop lourde ou faiblesse des abdominaux

## 2.5 Alignement Articulaire et Chaînes Cinétiques

### Principe de l'Alignement

Chaque articulation travaille de manière optimale quand elle est alignée dans son plan de mouvement naturel. Les déviations créent des forces de cisaillement qui usent les structures passives (ligaments, cartilage, ménisques).

### Chaîne Cinétique Fermée vs Ouverte

**Chaîne fermée** (pied/main fixe au sol ou sur un support) :
- Squat, deadlift, bench press, push-up, pull-up
- Plus de stabilité articulaire naturelle
- Cocontraction des muscles agonistes et antagonistes
- Généralement plus sûr pour les articulations

**Chaîne ouverte** (extrémité libre dans l'espace) :
- Leg extension, leg curl, élévations latérales, curls
- Moins de stabilité naturelle → plus de stress articulaire potentiel
- Isolation musculaire meilleure
- Nécessite plus de contrôle

### Alignements Critiques

**Genou :**
- Le genou doit tracker dans la direction des orteils (2ème-3ème orteil)
- **Valgus dynamique** (genou qui rentre vers l'intérieur) = DANGER, surtout sous charge
  - Détection MediaPipe : angle entre hanche (23/24), genou (25/26) et cheville (27/28) en vue frontale. Déviation médiale du genou > 10° par rapport à l'axe hanche-cheville → valgus
  - Causes : faiblesse du moyen fessier, manque de mobilité de hanche, pieds en pronation excessive
  - Pénalité scoring : -15 points (risque LCA, ménisque)

**Épaule :**
- En press horizontal, le coude ne doit pas s'écarter à > 75° du torse (angle humérus-torse)
- Angle à 90° (coudes en croix) = impingement sous-acromial
- Détection : angle entre coude (13/14), épaule (11/12) et hanche (23/24) en vue supérieure ou frontale

**Poignet :**
- Aligné avec l'avant-bras dans les mouvements de press
- Flexion ou extension excessive du poignet → perte de force + risque de tendinite
- Détection limitée via MediaPipe (landmarks poignet 15/16 vs coude 13/14)

**Cheville :**
- Dorsiflexion suffisante (> 35°) nécessaire pour un squat complet
- Talons qui décollent = manque de mobilité de cheville
- Détection : angle entre genou (25/26), cheville (27/28) et orteil (31/32)

## 2.6 Différences Morphologiques

### Pourquoi C'est Important

Deux personnes avec une technique "parfaite" n'auront PAS la même apparence en mouvement. La longueur des segments osseux, les proportions du torse, la profondeur des cavités articulaires — tout ça change la mécanique optimale.

**Le LLM ne doit JAMAIS juger une technique uniquement sur des angles absolus.** Il doit considérer les proportions visibles du pratiquant.

### Morphotypes et Impacts

**Longs fémurs (proportionnellement au torse) :**
- Au squat : inclinaison du torse plus prononcée (naturel et nécessaire)
- Le genou avancera plus ou le torse penchera plus — l'un des deux est inévitable
- Stance plus large souvent bénéfique
- Le front squat sera plus difficile à maintenir droit
- Angle du torse au squat : accepter jusqu'à 45-50° d'inclinaison (vs 30° pour un torse long)

**Torse court :**
- Même problématique que les longs fémurs — plus d'inclinaison au squat
- Avantage au deadlift (moins de distance à parcourir)
- Désavantage au bench (ROM plus court mais bras souvent plus longs)

**Bras longs :**
- Avantage au deadlift (moins de ROM, meilleur levier)
- Désavantage au bench press (plus de ROM, plus de travail)
- Avantage aux exercices de tirage
- Au bench : touch point plus bas sur le torse, flare des coudes potentiellement différent

**Bras courts :**
- Avantage au bench press
- Désavantage au deadlift conventionnel (position de départ plus basse)
- OHP : ROM plus court

**Hanches profondes (deep hip sockets) :**
- Difficulté à atteindre la profondeur au squat sans butt wink
- Stance plus large et pieds plus ouverts souvent nécessaires
- Ne PAS forcer la profondeur si la structure osseuse ne le permet pas

**Hanches peu profondes (shallow hip sockets) :**
- Grande mobilité naturelle de hanche
- Squat profond facilement atteignable
- Attention à l'hypermobilité — stabilité parfois insuffisante

### Comment le LLM Doit Adapter Son Analyse

1. Observer les proportions générales du pratiquant sur la vidéo
2. Ne pas pénaliser un angle de torse plus incliné si les fémurs sont visiblement longs
3. Mentionner les adaptations morphologiques quand pertinent : "Vu tes proportions, ton inclinaison du torse est tout à fait normale"
4. Recommander des variantes adaptées si un exercice ne convient clairement pas à la morphologie

## 2.7 Erreurs Universelles

### Ego Lifting (Charge Trop Lourde)

**Signes détectables :**
- ROM qui diminue de rep en rep (amplitude mesurable via MediaPipe)
- Tempo excentrique < 0.8 secondes (chute plutôt que descente contrôlée)
- Compensations multiples apparaissant simultanément
- Asymétrie croissante entre côté gauche et droit au fil des reps
- Utilisation de momentum (accélération en début de concentrique au lieu de contraction musculaire)

**Impact :** risque de blessure x3, stimulation musculaire réduite, apprentissage moteur compromis

### ROM Incomplet

**Définition :** ne pas exécuter le mouvement sur toute l'amplitude possible (en sécurité) de l'articulation.

**Problème :** 
- Moins de stimulus mécanique (tension sur moins de la courbe force-longueur)
- Développement musculaire partiel (raccourcissement adaptatif)
- Perte de mobilité à long terme

**Exceptions légitimes au ROM complet :**
- Blessure ou limitation structurelle
- Exercices spécifiques (board press, pin squat — intentionnel)
- Charge maximale en powerlifting (ROM minimum réglementaire)

**Détection :** comparer l'angle articulaire maximum atteint vs la référence de l'exercice. Par exemple, squat avec flexion de genou à 70° au lieu de ≥ 90° = ROM incomplet.

### Breath Holding Inapproprié

- Bloquer la respiration sur des séries longues d'isolation
- Visage qui rougit excessivement (non détectable via MediaPipe mais mentionnable)
- Confusion entre Valsalva (contrôlé, pour les composés lourds) et simple apnée involontaire

### Manque d'Échauffement Apparent

Si la première rep d'un set lourd montre une raideur excessive (ROM limité qui s'améliore au fil des reps), mentionner l'importance de séries progressives d'échauffement.

---

# SECTION 3 — RÉFÉRENTIELS PAR EXERCICE

## 3.1 JAMBES — Quadriceps Dominants

---

### Exercice 1 : Back Squat (High Bar)

**Description :** Barre positionnée sur les trapèzes supérieurs (au-dessus de l'épine de la scapula). Exercice roi pour le développement des quadriceps, fessiers et tronc.

**Muscles principaux :** Quadriceps, grand fessier, adducteurs
**Muscles secondaires :** Ischio-jambiers, érecteurs du rachis, abdominaux, mollets

#### Angles Optimaux

- **Flexion de genou au point bas :** ≥ 90° (idéal : 100-120° pour full depth). Mesuré par l'angle entre cuisse et tibia.
  - Morphotype fémurs longs : 90° acceptable comme minimum
  - Morphotype fémurs courts : viser ≥ 100°
- **Angle du torse par rapport à la verticale :**
  - Torse long / fémurs courts : 15-30°
  - Proportions moyennes : 25-40°
  - Torse court / fémurs longs : 35-50°
- **Angle de la cheville (dorsiflexion) :** 30-40° minimum
- **Écartement des pieds :** largeur d'épaules à 1.5x largeur d'épaules
- **Rotation externe des pieds :** 15-30° (orteils pointés légèrement vers l'extérieur)
- **Profondeur de hanche :** la pliure de hanche doit descendre AU MOINS au niveau du genou (parallel) — en dessous est mieux si la mobilité le permet

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère de détection | Sévérité |
|---|---|---|---|
| Valgus dynamique (genou en X) | Hanche (23/24) → Genou (25/26) → Cheville (27/28) | Angle médial < 170° en vue frontale | 🔴 Critique |
| Butt wink (flexion lombaire) | Épaule (11/12) → Hanche (23/24) → Genou (25/26) | Diminution soudaine de l'angle hanche > 15° dans les derniers 20% du ROM | 🟡 Modéré |
| Inclinaison excessive du torse | Épaule (11/12) → Hanche (23/24) → Verticale | Angle > 55° par rapport à la verticale (ajuster selon morphotype) | 🟡 Modéré |
| Talons qui décollent | Cheville (27/28) → Orteil (31/32) | Changement de hauteur du landmark cheville > 2 cm | 🔴 Critique |
| Shift latéral (poids d'un côté) | Hanche G (23) vs Hanche D (24) | Différence de hauteur > 3 cm pendant la montée | 🟡 Modéré |
| Genoux qui ne trackent pas les orteils | Genou (25/26) vs Orteil (31/32) | Genou dévie médialement de > 5 cm par rapport à la ligne du pied | 🔴 Critique |
| Good morning squat (hanches montent avant les épaules) | Hanche (23/24) et Épaule (11/12) | Hanche monte > 15° avant que les épaules commencent à monter | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Valgus dynamique :** "Tes genoux rentrent vers l'intérieur pendant la montée. Pousse activement les genoux vers l'extérieur, dans la direction de tes orteils. Pense à 'écarter le sol avec tes pieds.'"
2. **🔴 Talons qui décollent :** "Tes talons décollent en bas du mouvement. C'est un problème de mobilité de cheville. En attendant, mets des cales sous les talons (ou des chaussures d'haltérophilie) et travaille ta dorsiflexion."
3. **🟡 Good morning squat :** "Tes hanches montent plus vite que tes épaules — tu transformes ton squat en good morning. Pense à 'pousser le dos dans la barre' pendant la montée. Si ça persiste, la charge est probablement trop lourde."
4. **🟡 Butt wink :** "Tu as un arrondi du bas du dos en fin de descente. Descends seulement jusqu'où tu peux maintenir ta courbure lombaire naturelle. Élargis un peu ta stance et ouvre plus les pieds."
5. **🟡 Inclinaison excessive :** "Ton torse penche beaucoup vers l'avant. Vérifie que la barre est bien en position high bar (sur les trapèzes, pas sur les deltoïdes arrière). Travaille ta mobilité thoracique."

#### Exercices Correctifs

1. **Goblet Squat avec pause (3x10, 3sec pause en bas)** — force une position plus verticale du torse et enseigne le pattern moteur correct. La position de la charge devant le corps contrebalance la tendance à pencher en avant.
2. **Banded Terminal Knee Extension (3x15 par jambe)** — renforce le VMO (vaste médial oblique) qui stabilise le genou contre le valgus.
3. **Dorsiflexion de cheville sur mur (3x30sec par cheville)** — améliore la mobilité de cheville nécessaire pour descendre sans compenser.

#### Erreurs par Niveau

**Débutant :**
- Descend pas assez bas (peur + manque de mobilité)
- Genoux qui dépassent pas les orteils (mauvais conseil encore trop répandu)
- Regarde le plafond (hyperextension cervicale)
- Pas de bracing

**Intermédiaire :**
- Good morning squat (les hanches montent plus vite)
- Valgus subtil sur les dernières reps
- Butt wink modéré
- Rebond en bas sans contrôle (bounce out of the hole)

**Avancé :**
- Léger shift latéral sous charges lourdes
- Perte de bracing après rep 3-4 sur des séries lourdes
- Vitesse de barre asymétrique entre les côtés

#### Variantes et Différences

- **High bar vs Low bar :** High bar = plus vertical, plus de quadriceps, plus de mobilité de cheville requise. Low bar = plus penché en avant, plus de postérieur, généralement plus de charge possible.
- **Squat avec ceinture :** ne remplace PAS le bracing — la ceinture donne quelque chose contre quoi pousser pour augmenter la PIA.

---

### Exercice 2 : Back Squat (Low Bar)

**Description :** Barre positionnée sur les deltoïdes postérieurs, sous l'épine de la scapula. Permet généralement de soulever plus lourd. Position typique du powerlifting.

**Muscles principaux :** Grand fessier, quadriceps, adducteurs, ischio-jambiers
**Muscles secondaires :** Érecteurs du rachis, abdominaux

#### Angles Optimaux

- **Flexion de genou au point bas :** ≥ 90° (la profondeur est souvent naturellement moindre qu'en high bar)
- **Angle du torse par rapport à la verticale :**
  - Proportions moyennes : 35-50°
  - Fémurs longs : jusqu'à 55-60° acceptable
- **Inclinaison du torse :** TOUJOURS plus incliné qu'en high bar (c'est normal, pas une erreur)
- **Stance :** généralement plus large qu'en high bar, pieds plus ouverts (20-40°)
- **Position de la barre :** environ 5-8 cm plus bas que le high bar

#### Compensations Détectables via MediaPipe

Mêmes compensations que le high bar, avec les ajustements suivants :
- **Inclinaison du torse :** les seuils sont PLUS tolérants (accepter 10-15° de plus qu'en high bar)
- **Flexion thoracique :** plus surveillée car la position basse de la barre tend à tirer les épaules en avant
- **Poignets en hyperextension :** si les poignets sont trop fléchis en arrière, les mains portent la barre au lieu des deltoïdes → douleur de poignets. Détection : angle poignet (15/16) - coude (13/14) - épaule (11/12)

#### Corrections Prioritaires

1. **🔴 Barre qui glisse :** "La barre bouge pendant le mouvement. Serre plus les omoplates pour créer une étagère musculaire avec tes deltoïdes arrière. La barre doit reposer sur le muscle, pas sur l'os."
2. **🔴 Inclinaison excessive au-delà du morphotype :** "Même en low bar, tu penches trop en avant. Vérifie ta mobilité de hanche et de cheville. Si c'est ta première fois en low bar, la charge est peut-être trop lourde pour le pattern."
3. **🟡 Poignets en extension :** "Tes poignets sont pliés en arrière pour tenir la barre. La barre doit reposer sur ton dos, pas dans tes mains. Élargis ta prise si nécessaire."

#### Exercices Correctifs

1. **Tempo Low Bar Squat (3x5 à 60%, tempo 3-2-1-0)** — apprend la position sans charge excessive
2. **Face Pull (3x15)** — renforce les rétracteurs scapulaires pour mieux stabiliser la barre
3. **Étirement pecs + rotation externe d'épaule** — améliore la mobilité nécessaire pour la prise en low bar

#### Erreurs par Niveau

**Débutant :** Barre trop basse (sur les coudes presque), grip trop serré causant douleur d'épaule, confusion avec le high bar
**Intermédiaire :** Perte du brace en bas, conversion en good morning excessive
**Avancé :** Asymétrie de montée sous charges maximales, grip width non optimal

---

### Exercice 3 : Front Squat

**Description :** Barre en position front rack (sur les deltoïdes antérieurs, maintenue par les doigts en position de clean grip ou bras croisés). Force une position beaucoup plus verticale du torse.

**Muscles principaux :** Quadriceps (emphase maximale), grand fessier
**Muscles secondaires :** Core (anti-flexion massive), érecteurs du rachis, haut du dos

#### Angles Optimaux

- **Flexion de genou :** ≥ 100° (le front squat permet naturellement plus de profondeur)
- **Angle du torse :** 5-20° par rapport à la verticale (quasi-vertical)
- **Position des coudes :** HAUTS — les humérus doivent être au minimum parallèles au sol (angle coude par rapport à l'horizontale ≥ 0°)
- **Dorsiflexion de cheville :** requiert > 38° — plus que tout autre squat
- **Avance des genoux :** les genoux DOIVENT dépasser les orteils significativement — c'est normal et nécessaire

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Coudes qui tombent | Coude (13/14), Épaule (11/12), Horizontale | Coudes sous l'horizontale de > 20° | 🔴 Critique (barre va tomber) |
| Torse qui s'effondre en avant | Épaule (11/12), Hanche (23/24), Verticale | Angle > 30° | 🔴 Critique |
| Butt wink accentué | Même que back squat | Même critères | 🟡 Modéré |
| Valgus | Même que back squat | Même critères | 🔴 Critique |

#### Corrections Prioritaires

1. **🔴 Coudes qui tombent :** "Tes coudes tombent pendant la montée — c'est le signe n°1 de perte de contrôle en front squat. Monte les coudes AVANT de commencer à monter. Pense 'coudes au plafond'. Si tu ne peux pas les maintenir, la charge est trop lourde."
2. **🔴 Torse qui s'effondre :** "Ton torse penche trop en avant. Le front squat doit être quasi-vertical. Renforce ton haut du dos et travaille ta mobilité thoracique. Les paused front squats légers vont t'aider."
3. **🟡 Prise inconfortable :** "Si le clean grip te fait mal aux poignets, utilise la prise croisée ou des sangles autour de la barre. L'important c'est de garder les coudes hauts."

#### Exercices Correctifs

1. **Zombie Front Squat (3x8, bras tendus devant sans tenir la barre)** — enseigne la position verticale du torse car si tu penches, la barre tombe
2. **Thoracic Spine Extensions sur foam roller (2x10)** — mobilité thoracique pour rester droit
3. **Goblet Squat pause (3x8, 3sec en bas)** — même pattern moteur, charge devant

#### Erreurs par Niveau

**Débutant :** Ne peut pas maintenir le rack position, torse s'effondre, utilise la prise croisée mal positionnée
**Intermédiaire :** Coudes tombent sur les dernières reps, perd la verticalité sous charge
**Avancé :** Léger butt wink en profondeur maximale, perte de bracing après rep 3

---

### Exercice 4 : Goblet Squat

**Description :** Squat avec un haltère ou kettlebell tenu contre la poitrine. Excellent exercice d'apprentissage et de travail de mobilité.

**Muscles principaux :** Quadriceps, grand fessier
**Muscles secondaires :** Core, biceps (maintien de la charge), haut du dos

#### Angles Optimaux

- **Flexion de genou :** ≥ 100° (la position de la charge facilite la profondeur)
- **Angle du torse :** 10-25° (très vertical grâce à la charge devant)
- **Coudes :** doivent passer entre les genoux en bas du mouvement (si la mobilité le permet)
- **Cheville :** dorsiflexion ≥ 30°

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Charge qui s'éloigne du torse | Poignet (15/16) vs Épaule (11/12) | Distance horizontale > 20 cm | 🟡 Modéré |
| Arrondissement du haut du dos | Épaule (11/12), mi-dos, hanche (23/24) | Cyphose visible > 20° | 🟡 Modéré |
| Valgus dynamique | Même que back squat | Même critères | 🔴 Critique |
| Talons qui décollent | Même que back squat | Même critères | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Charge qui s'éloigne :** "Garde l'haltère/kettlebell collé contre ta poitrine. Si ça s'éloigne, tes bras fatiguent et ton dos arrondit."
2. **🔴 Valgus :** "Utilise tes coudes pour pousser tes genoux vers l'extérieur en bas du mouvement — c'est un des avantages du goblet squat."
3. **🟡 Profondeur insuffisante :** "Le goblet squat est l'exercice parfait pour travailler ta profondeur. Descends le plus bas possible en gardant le dos droit."

#### Exercices Correctifs

1. **Goblet Squat avec pause prolongée en bas (3x6, 5sec en bas)** — auto-correctif, utilise la gravité pour améliorer la mobilité
2. **Étirements 90/90 de hanche (2x30sec par côté)** — mobilité de hanche pour meilleure profondeur

#### Erreurs par Niveau

**Débutant :** Charge trop légère pour contrebalancer, torse qui arrondit, ne descend pas assez
**Intermédiaire :** Utilise trop de momentum, perd la pause en bas
**Avancé :** Rarement un problème — c'est un exercice de correction/échauffement

---

### Exercice 5 : Bulgarian Split Squat

**Description :** Squat unilatéral avec le pied arrière surélevé sur un banc. Excellent pour corriger les asymétries et développer la stabilité.

**Muscles principaux :** Quadriceps (jambe avant), grand fessier
**Muscles secondaires :** Adducteurs, ischio-jambiers, stabilisateurs de hanche, core (anti-rotation)

#### Angles Optimaux

- **Flexion de genou avant :** 90-110° au point bas
- **Genou arrière :** descend près du sol sans toucher (5-10 cm du sol)
- **Angle du torse :** 5-15° d'inclinaison vers l'avant (quasi-vertical pour quadriceps dominants, plus incliné pour fessiers)
- **Distance du pied avant au banc :** environ 60-80 cm (assez loin pour que le genou ne dépasse pas excessivement les orteils au point bas)
- **Pied avant :** pointé droit devant ou légèrement ouvert (0-15°)
- **Hauteur du banc arrière :** environ hauteur de genou (40-50 cm)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Valgus du genou avant | Hanche → Genou → Cheville (côté travail) | Déviation médiale > 8° | 🔴 Critique |
| Torse qui s'effondre en avant | Épaule → Hanche → Verticale | Angle > 30° | 🟡 Modéré |
| Rotation du bassin | Hanche G (23) vs Hanche D (24) | Rotation > 10° dans le plan transversal | 🟡 Modéré |
| Instabilité latérale | Oscillations du torse | Mouvement latéral > 5 cm | 🟡 Modéré |
| Genou avant trop en avant | Genou (25/26) vs Orteil (31/32) | Genou dépasse les orteils de > 10 cm | 🟢 Mineur (sauf si douleur) |

#### Corrections Prioritaires

1. **🔴 Valgus du genou avant :** "Ton genou rentre vers l'intérieur. Concentre-toi sur pousser le genou vers l'extérieur pendant toute la montée. Stabilise ta hanche — c'est souvent une faiblesse du moyen fessier."
2. **🟡 Instabilité excessive :** "Tu oscilles beaucoup latéralement. Commence sans charge pour maîtriser l'équilibre. Un petit truc : fixe un point devant toi et contracte ton core comme si tu allais recevoir un coup."
3. **🟡 Pied arrière trop actif :** "Si tu sens que ta jambe arrière fait trop de travail, avance un peu plus ton pied avant. La jambe arrière est juste là pour l'équilibre, c'est la jambe avant qui fait le boulot."

#### Exercices Correctifs

1. **Split Squat statique (pas surélevé) avec pause (3x8/côté, 2sec en bas)** — même pattern, moins de demande d'équilibre
2. **Banded Lateral Walk (3x12 pas/côté)** — renforce le moyen fessier pour la stabilité de hanche
3. **Single Leg Glute Bridge (3x12/côté)** — activation unilatérale du fessier

#### Erreurs par Niveau

**Débutant :** Position du pied avant trop proche du banc, utilise trop la jambe arrière, instabilité majeure
**Intermédiaire :** Valgus subtil, ne descend pas assez bas, rotation du bassin
**Avancé :** Asymétrie de force entre les côtés (> 2 reps de différence), perte de tension en bas

---

### Exercice 6 : Hack Squat (Machine)

**Description :** Squat guidé sur machine avec le dos contre un pad incliné (généralement 45°). Permet d'isoler les quadriceps avec moins de demande de stabilisation.

**Muscles principaux :** Quadriceps (emphase forte), grand fessier
**Muscles secondaires :** Adducteurs, mollets

#### Angles Optimaux

- **Flexion de genou :** ≥ 90° (viser 100-110° pour ROM complet)
- **Position des pieds sur la plateforme :**
  - Pieds bas = plus de quadriceps (plus de flexion de genou)
  - Pieds hauts = plus de fessiers/ischio-jambiers
  - Pieds serrés = emphase vaste externe
  - Pieds larges = emphase adducteurs
- **Bas du dos :** TOUJOURS plaqué contre le pad — jamais de décollement
- **Épaules :** sous les pads, pas de pression cervicale

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Bas du dos qui décolle du pad | Hanche (23/24), Épaule (11/12) | Changement d'angle torse > 10° par rapport à la machine | 🔴 Critique |
| Valgus dynamique | Genou (25/26) vs Cheville (27/28) | Déviation médiale > 10° | 🔴 Critique |
| Extension incomplète en haut | Angle genou en haut | Reste fléchi > 15° | 🟡 Modéré |
| Talons qui décollent | Cheville (27/28) | Élévation > 1.5 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Dos qui décolle :** "Ton bas du dos se décolle du pad en bas du mouvement. Descends seulement jusqu'où tu peux garder le dos plaqué. C'est ton vrai ROM sur cet exercice."
2. **🔴 Valgus :** "Même sur machine, tes genoux doivent tracker tes orteils. Pousse-les vers l'extérieur."
3. **🟡 ROM partiel :** "Tu ne descends pas assez. La machine est guidée, profite-en pour travailler le ROM complet en toute sécurité."

#### Exercices Correctifs

1. **Hack Squat pause en bas (3x8, tempo 3-2-1-0)** — apprend à contrôler le bas du mouvement
2. **Wall Sit (3x30sec)** — renforce les quadriceps en isométrique dans la position basse

#### Erreurs par Niveau

**Débutant :** Pieds trop bas causant des douleurs de genoux, ROM partiel, verrouillage agressif en haut
**Intermédiaire :** Rebond rapide en bas, utilisation de momentum
**Avancé :** Valgus sous charges très lourdes, asymétrie de poussée

---

### Exercice 7 : Leg Press (45°)

**Description :** Presse à cuisse inclinée à 45°. Permet de charger lourd avec moins de stress sur la colonne que le squat.

**Muscles principaux :** Quadriceps, grand fessier
**Muscles secondaires :** Adducteurs, ischio-jambiers, mollets

#### Angles Optimaux

- **Flexion de genou au point bas :** 90° minimum (idéal : 100-110°)
- **Angle hanche au point bas :** ne pas descendre au point où le bassin bascule (pelvis tuck)
- **Position des pieds :** mêmes principes que le hack squat
- **Genoux :** ne JAMAIS verrouiller complètement en extension (garder 5° de flexion en haut)
- **Bas du dos :** TOUJOURS plaqué contre le siège

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Bassin qui bascule (pelvis tuck) | Hanche (23/24) | Rotation postérieure visible — le bas du dos se décolle du siège | 🔴 Critique |
| Verrouillage complet des genoux | Angle genou | 180° (hyperextension) en haut | 🔴 Critique (risque de luxation) |
| Valgus | Genoux (25/26) | Déviation médiale > 10° | 🔴 Critique |
| ROM incomplet | Angle genou minimum | < 80° de flexion | 🟡 Modéré |
| Poussée asymétrique | Position de la plateforme | Rotation visible de la plateforme | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Verrouillage des genoux :** "NE VERROUILLE JAMAIS tes genoux en haut de la leg press. Garde toujours une micro-flexion. Des genoux qui verrouillent sous cette charge, c'est un risque de blessure grave."
2. **🔴 Pelvis tuck :** "Ton bassin bascule en bas du mouvement — ton bas du dos arrondit. Descends moins bas. Ton ROM s'arrête là où ton bassin reste stable."
3. **🔴 Valgus :** "Tes genoux rentrent. Mets tes pieds un peu plus haut et un peu plus écartés sur la plateforme."

#### Exercices Correctifs

1. **Leg Press unilatérale (3x10/côté, charge légère)** — identifie et corrige les asymétries
2. **Hip 90/90 stretch (2x30sec/côté)** — mobilité de hanche pour éviter le pelvis tuck

#### Erreurs par Niveau

**Débutant :** Charge beaucoup trop lourde (ego lift classique sur leg press), verrouillage des genoux, ROM de 30°
**Intermédiaire :** Pelvis tuck subtil, valgus sur les dernières reps
**Avancé :** Asymétrie fine, tempo non contrôlé

---

### Exercice 8 : Leg Extension

**Description :** Isolation des quadriceps en chaîne cinétique ouverte. Le pad est sur les tibias, on étend les genoux.

**Muscles principaux :** Quadriceps (les 4 chefs, emphase rectus femoris)
**Muscles secondaires :** Aucun significatif

#### Angles Optimaux

- **Extension complète :** genou à 175-180° (extension quasi-complète, pas d'hyperextension)
- **Flexion au point bas :** ≥ 90° (retour complet)
- **Position du dossier :** légèrement incliné en arrière pour pré-étirer le droit fémoral
- **Pad sur les tibias :** au niveau de la cheville, PAS sur le pied

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Fesses qui décollent du siège | Hanche (23/24) | Élévation > 3 cm | 🟡 Modéré |
| Utilisation de momentum (swing) | Vitesse angulaire du genou | Accélération initiale > 2x la vitesse moyenne | 🟡 Modéré |
| Extension incomplète | Angle genou max | < 160° | 🟡 Modéré |
| Hyperextension du genou | Angle genou | > 185° | 🔴 Critique |

#### Corrections Prioritaires

1. **🟡 Momentum/swing :** "Tu balances la charge au lieu de la contrôler. Réduis le poids et monte en 2 secondes, descends en 3 secondes. La leg extension c'est du contrôle pur, pas de la force brute."
2. **🟡 Extension incomplète :** "Étends complètement tes jambes en haut et contracte tes quadriceps 1 seconde. C'est là que la contraction peak se passe."
3. **🟡 Fesses qui décollent :** "Tes fesses décollent du siège — la charge est trop lourde. Réduis et concentre-toi sur la contraction."

#### Exercices Correctifs

1. **Leg Extension 1¼ reps (3x10)** — extension complète, redescend de 30°, remonte, puis descend complètement. Renforce le lockout.
2. **Spanish Squat (3x12)** — renforce les quadriceps dans une position qui protège le genou

#### Erreurs par Niveau

**Débutant :** Charge trop lourde, momentum, ne contracte pas en haut
**Intermédiaire :** Tempo trop rapide, ROM partiel
**Avancé :** Pas de peak contraction, vitesse trop constante (pas d'intention)

---

### Exercice 9 : Sissy Squat

**Description :** Squat où le torse reste aligné avec les cuisses pendant que les genoux avancent au-delà des orteils. Isolation extrême des quadriceps, demande beaucoup de force de genou.

**Muscles principaux :** Quadriceps (emphase maximale sur le rectus femoris)
**Muscles secondaires :** Core, fléchisseurs de hanche

#### Angles Optimaux

- **Inclinaison du corps :** le torse ET les cuisses forment une ligne droite, inclinée en arrière
- **Flexion de genou :** ≥ 90° au point bas
- **Cheville :** en plantarflexion (sur les orteils)
- **Hanche :** NE FLÉCHIT PAS — reste alignée avec le torse (c'est la clé)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Flexion de hanche (cassure) | Épaule (11/12), Hanche (23/24), Genou (25/26) | Angle < 160° (le corps casse à la hanche) | 🟡 Modéré |
| ROM insuffisant | Angle genou min | < 70° de flexion | 🟡 Modéré |
| Perte d'alignement torse-cuisse | Torse vs cuisse | Angle entre eux > 15° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Flexion de hanche :** "Tu casses à la hanche — c'est pas un squat classique. En sissy squat, ton torse et tes cuisses doivent rester alignés. Pense à te pencher en arrière comme un bloc rigide."
2. **🟡 ROM :** "Descends plus bas. Si tu ne peux pas, tiens-toi à un support pour t'aider dans la partie basse."

#### Exercices Correctifs

1. **Sissy Squat assisté (avec support, 3x10)** — même pattern avec aide pour l'équilibre
2. **Leg Extension avec pause en contraction (3x10, 2sec)** — renforce les quadriceps en raccourci

#### Erreurs par Niveau

**Débutant :** Fait un squat normal au lieu d'un sissy squat, casse à la hanche
**Intermédiaire :** ROM partiel, tempo trop rapide
**Avancé :** Léger déséquilibre, perte d'alignement en fin de série

---

### Exercice 10 : Walking Lunges

**Description :** Fentes en marchant. Excellent pour le développement unilatéral et la fonctionnalité.

**Muscles principaux :** Quadriceps, grand fessier
**Muscles secondaires :** Ischio-jambiers, adducteurs, core (stabilisation), mollets

#### Angles Optimaux

- **Genou avant au point bas :** 85-95° de flexion
- **Genou arrière :** descend à 5-10 cm du sol, angle ≈ 90°
- **Torse :** 5-15° d'inclinaison (quasi-vertical)
- **Longueur du pas :** pas court = plus de quadriceps, pas long = plus de fessiers
- **Angle du tibia avant :** peut dépasser la verticale (genou au-delà de l'orteil) — c'est normal

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Valgus du genou avant | Hanche → Genou → Cheville | Déviation médiale > 8° | 🔴 Critique |
| Torse qui oscille latéralement | Épaule (11/12) | Mouvement latéral > 8 cm | 🟡 Modéré |
| Pas trop court / profondeur insuffisante | Angle genou arrière | > 110° (pas assez bas) | 🟡 Modéré |
| Instabilité / perte d'équilibre | Trajectoire centre de masse | Déviation latérale > 10 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Valgus :** "Ton genou avant rentre à chaque foulée. Pense à pousser le genou au-dessus de ton 3ème orteil."
2. **🟡 Pas trop court :** "Allonge un peu ton pas pour permettre à ton genou arrière de descendre plus bas. Tu dois presque toucher le sol."
3. **🟡 Instabilité :** "Tu oscilles beaucoup. Ralentis le mouvement, fais une micro-pause en position basse pour stabiliser, puis repars."

#### Exercices Correctifs

1. **Reverse Lunge statique (3x10/côté)** — même pattern, moins de demande d'équilibre
2. **Single Leg RDL (3x8/côté, sans charge)** — améliore la stabilité unilatérale

#### Erreurs par Niveau

**Débutant :** Pas trop courts, ne descend pas assez, perd l'équilibre
**Intermédiaire :** Valgus subtil, tempo inconsistant
**Avancé :** Asymétrie de stabilité entre les côtés

---

### Exercice 11 : Step-Up

**Description :** Monter sur un banc ou une box avec une jambe, l'autre suivant. Exercice unilatéral fonctionnel.

**Muscles principaux :** Quadriceps, grand fessier (jambe qui monte)
**Muscles secondaires :** Ischio-jambiers, mollets, core

#### Angles Optimaux

- **Hauteur de la box :** genou fléchi à 90° quand le pied est posé dessus
- **Flexion de hanche :** dépend de la hauteur — plus la box est haute, plus la flexion de hanche est importante
- **Torse :** vertical ou légèrement incliné (5-15°)
- **Pied entier sur la box :** pas juste le bout du pied

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Poussée avec la jambe arrière | Cheville jambe arrière (27/28) | Plantarflexion active (pousse depuis le sol) | 🟡 Modéré |
| Inclinaison excessive du torse | Épaule → Hanche → Verticale | > 25° | 🟡 Modéré |
| Genou en valgus | Hanche → Genou → Cheville | Déviation médiale > 8° | 🔴 Critique |
| Pied pas entièrement sur la box | Position du pied | Talon hors de la box | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Triche avec la jambe arrière :** "Tu pousses avec ta jambe arrière pour t'aider à monter. Tout le travail doit venir de la jambe sur la box. Imagine que ta jambe arrière est en mousse."
2. **🔴 Valgus :** "Ton genou part vers l'intérieur quand tu montes. Stabilise ta hanche et pousse le genou vers l'extérieur."
3. **🟡 Box trop haute :** "Si tu dois te pencher excessivement pour monter, la box est probablement trop haute. Réduis la hauteur."

#### Exercices Correctifs

1. **Step-Up négatif lent (3x8/côté, 4sec pour descendre)** — contrôle excentrique unilatéral
2. **Single Leg Glute Bridge (3x12/côté)** — activation unilatérale du fessier

#### Erreurs par Niveau

**Débutant :** Pousse excessivement avec la jambe arrière, box trop haute, perte d'équilibre
**Intermédiaire :** Asymétrie de force, tempo trop rapide
**Avancé :** Charge qui crée une rotation du torse

---

## 3.2 JAMBES — Postérieur

---

### Exercice 12 : Deadlift Conventionnel

**Description :** Soulevé de terre avec les mains à l'extérieur des genoux, stance à largeur de hanches. L'exercice le plus fonctionnel et le plus lourd du répertoire.

**Muscles principaux :** Érecteurs du rachis, grand fessier, ischio-jambiers
**Muscles secondaires :** Quadriceps, trapèzes, avant-bras (grip), grand dorsal, core

#### Angles Optimaux

- **Position de départ :**
  - Barre au-dessus du milieu du pied (7-8 cm du tibia)
  - Épaules au-dessus ou légèrement en avant de la barre
  - Hanches plus hautes que les genoux, plus basses que les épaules
  - Angle du torse : 30-50° (dépend fortement du morphotype)
  - Bras verticaux, tendus (pas de flexion de coude)
  - Angle de genou : 65-85° de flexion
- **Lockout :**
  - Hanches en extension complète (0°)
  - Genoux verrouillés
  - Épaules en arrière (légère rétraction scapulaire)
  - PAS d'hyperextension lombaire

**Adaptations morphologiques :**
- Bras longs : position de départ plus haute des hanches, plus facile mécaniquement
- Bras courts : position plus basse, plus comme un squat
- Torse long : angle de torse plus horizontal
- Fémurs longs : hanches plus hautes, torse plus incliné

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Dos arrondi (flexion lombaire) | Épaule (11/12), Hanche (23/24), angle lombo-pelvien | Flexion lombaire > 10° par rapport à la position de départ | 🔴 CRITIQUE |
| Dos arrondi (flexion thoracique) | Épaule (11/12), mi-torse | Cyphose excessive > 25° | 🟡 Modéré (sauf charges lourdes → 🔴) |
| Barre qui s'éloigne du corps | Poignet (15/16) vs mi-pied | Distance horizontale > 8 cm | 🔴 Critique |
| Hyperextension au lockout | Épaule, Hanche, Genou | Angle hanche > 185° (hanche en avant du genou) | 🟡 Modéré |
| Lockout avec les lombaires | Hanche (23/24) vs Épaule (11/12) | Les épaules reculent PLUS que les hanches avancent | 🟡 Modéré |
| Genoux qui verrouillent trop tôt | Angle genou vs angle hanche | Genoux à 180° alors que hanches encore fléchies > 30° | 🟡 Modéré |
| Hitching (saccade à mi-cuisse) | Vitesse verticale de la barre | Arrêt puis accélération à hauteur genou | 🔴 Critique en compétition |
| Hyperextension cervicale | Oreille (7/8), Épaule (11/12) | Angle tête-torse > 190° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Flexion lombaire :** "Ton bas du dos s'arrondit. C'est LE signal d'alarme n°1 du deadlift. Soit la charge est trop lourde, soit tu ne braces pas correctement, soit ta position de départ est mauvaise. Prends une grande inspiration, contracte les abdos comme si on allait te frapper, et 'pousse le sol' au lieu de 'tirer la barre'."
2. **🔴 Barre qui s'éloigne :** "La barre doit rester collée à ton corps pendant TOUT le mouvement — elle glisse sur tes tibias, tes genoux, tes cuisses. Si elle s'éloigne, le bras de levier augmente et ton dos prend tout."
3. **🟡 Lockout avec les lombaires :** "Tu finis le mouvement en te cambrant en arrière au lieu de pousser tes hanches vers l'avant. Le deadlift se finit hanches en avant, dos droit — pas en hyperextension. Contracte tes fessiers en haut comme si tu serrais une pièce."
4. **🟡 Genoux qui verrouillent trop tôt :** "Tes genoux se tendent avant que la barre passe les genoux — ça transforme la fin du mouvement en un stiff-leg deadlift et surcharge ton bas du dos. Pense à monter hanches et épaules ensemble."

#### Exercices Correctifs

1. **Pause Deadlift à mi-tibia (3x5 à 65%, 3sec pause)** — renforce la position et enseigne le maintien du dos neutre
2. **Romanian Deadlift (3x8)** — renforce la chaîne postérieure et enseigne le hip hinge
3. **Dead Bug (3x10/côté)** — renforce le core pour un meilleur bracing

#### Erreurs par Niveau

**Débutant :** Dos arrondi, tire avec les bras, barre loin du corps, pas de bracing, regarde en l'air
**Intermédiaire :** Flexion lombaire subtile sur les reps lourdes, genoux verrouillent trop tôt, lockout avec hyperextension
**Avancé :** Asymétrie de grip, léger arrondi thoracique (intentionnel chez certains), hitching subtil

---

### Exercice 13 : Sumo Deadlift

**Description :** Deadlift avec stance très large et mains entre les genoux. Réduit le ROM et change le levier — plus de travail d'adducteurs et quadriceps.

**Muscles principaux :** Quadriceps, adducteurs, grand fessier, érecteurs du rachis
**Muscles secondaires :** Ischio-jambiers, trapèzes, grip

#### Angles Optimaux

- **Stance :** 1.5-2x largeur d'épaules (pieds sur les anneaux de la barre ou plus large)
- **Rotation des pieds :** 30-50° vers l'extérieur
- **Torse :** plus vertical que le conventionnel (15-35°)
- **Hanches :** plus basses que le conventionnel, plus proches de la barre
- **Genoux :** poussés vers l'extérieur dans la direction des orteils
- **Bras :** verticaux, prise à largeur d'épaules
- **Position de départ :** épaules directement au-dessus de la barre (pas en avant)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Genoux qui collapsent vers l'intérieur | Hanche → Genou → Cheville | Valgus > 12° | 🔴 Critique |
| Hanches qui montent trop vite | Hanche (23/24) vs Épaule (11/12) | Hanches montent > 15° avant les épaules | 🔴 Critique (transforme en conventionnel) |
| Flexion lombaire | Même que conventionnel | Même critères | 🔴 Critique |
| Épaules trop en avant de la barre | Épaule (11/12) vs Poignet (15/16) | Épaules > 5 cm en avant | 🟡 Modéré |
| Pieds pas assez ouverts | Angle du pied vs genou | Genou ne peut pas tracker l'orteil | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Genoux qui collapsent :** "Tes genoux s'effondrent vers l'intérieur dès que la barre décolle. Pense à 'écarter le sol' avec tes pieds. Si tu ne peux pas garder les genoux dehors, la charge est trop lourde ou ta stance est trop large."
2. **🔴 Hanches qui montent trop vite :** "Tu tires comme un conventionnel — tes hanches montent et tu finis penché en avant. Le sumo doit rester vertical. Pense à 'pousser le sol' et à ouvrir les hanches."
3. **🟡 Position de départ :** "Prends le temps de bien te placer avant chaque rep. Hanches basses, torse droit, genoux dehors, brace serré."

#### Exercices Correctifs

1. **Paused Sumo Deadlift 5cm off floor (3x4 à 60%, 2sec pause)** — enseigne la patience dans le départ
2. **Sumo Stance Good Morning (3x8)** — renforce la position sumo sans charge maximale
3. **Banded Clamshell (3x15/côté)** — activation des rotateurs externes de hanche

#### Erreurs par Niveau

**Débutant :** Stance trop large ou trop étroite, tire comme un conventionnel, genoux collapse
**Intermédiaire :** Hanches qui montent trop vite, perte de patience au départ
**Avancé :** Lockout lent (charge maximale), asymétrie de hanche

---

### Exercice 14 : Romanian Deadlift (RDL)

**Description :** Hip hinge avec genoux légèrement fléchis, barre descend le long des jambes. Principal exercice d'isolation des ischio-jambiers en chaîne fermée.

**Muscles principaux :** Ischio-jambiers, grand fessier
**Muscles secondaires :** Érecteurs du rachis, grand dorsal (stabilisation), trapèzes

#### Angles Optimaux

- **Flexion de genou :** 15-25° (FIXE pendant tout le mouvement — ne change pas)
- **Flexion de hanche :** 70-90° au point bas (hanches qui reculent)
- **Torse :** parallèle au sol ou légèrement au-dessus au point bas
- **Barre :** reste collée aux jambes (glisse sur les cuisses)
- **Dos :** NEUTRE du début à la fin — pas d'arrondi
- **Tête :** neutre, suit la ligne du dos
- **Descente :** la barre descend jusqu'au milieu du tibia OU jusqu'à perte de neutralité lombaire (ce qui arrive en premier)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Genoux qui fléchissent pendant la descente | Angle genou (25/26) | Changement > 10° par rapport à la position de départ | 🟡 Modéré |
| Flexion lombaire | Angle lombaire | Arrondi visible > 10° | 🔴 Critique |
| Barre qui s'éloigne des jambes | Poignet (15/16) vs Hanche (23/24) | Distance horizontale > 10 cm | 🟡 Modéré |
| Hyperextension au lockout | Angle hanche | > 185° | 🟡 Modéré |
| Hanches qui ne reculent pas | Hanche (23/24) position horizontale | Déplacement postérieur < 10 cm | 🟡 Modéré |
| Hausse des épaules (shrug) | Épaule (11/12) | Élévation > 3 cm | 🟢 Mineur |

#### Corrections Prioritaires

1. **🔴 Flexion lombaire :** "Ton dos s'arrondit en bas du mouvement. Descends seulement jusqu'où tu peux garder le dos plat. Ce n'est PAS un exercice où tu dois toucher le sol — la limite c'est ta souplesse ischio-jambière."
2. **🟡 Genoux qui bougent :** "Tes genoux fléchissent pendant la descente — ça transforme ton RDL en deadlift. Bloque tes genoux à 15-20° et ne les bouge plus. Le mouvement vient UNIQUEMENT de tes hanches."
3. **🟡 Hanches qui ne reculent pas :** "Tes hanches doivent reculer derrière toi comme si tu voulais toucher un mur avec tes fesses. C'est un hip hinge, pas une flexion du torse."

#### Exercices Correctifs

1. **Wall RDL (3x10, fesses touchent un mur à 30cm derrière)** — enseigne le hip hinge correct
2. **Single Leg RDL (3x8/côté, sans charge)** — améliore la proprioception et le pattern
3. **Good Morning (3x10, barre vide)** — renforce le hip hinge avec position de barre différente

#### Erreurs par Niveau

**Débutant :** Confond avec un deadlift (fléchit trop les genoux), arrondit le dos, ne pousse pas les hanches en arrière
**Intermédiaire :** Descend trop bas au-delà de sa mobilité, vitesse excentrique trop rapide
**Avancé :** Légère perte de neutralité à la dernière rep, shrug compensatoire

---

### Exercice 15 : Stiff-Leg Deadlift

**Description :** Similaire au RDL mais les genoux sont quasi-tendus (5-10° de flexion). Plus d'étirement des ischio-jambiers, plus de stress sur le bas du dos.

**Muscles principaux :** Ischio-jambiers (emphase sur l'étirement), grand fessier, érecteurs du rachis
**Muscles secondaires :** Trapèzes, grip

#### Différence avec le RDL

- Genoux PLUS tendus (5-10° vs 15-25°)
- Plus de stress sur les ischio-jambiers en position étirée
- Plus de stress sur le bas du dos
- La barre descend plus bas (vers les pieds)
- Hanches reculent moins

#### Angles Optimaux

- **Flexion de genou :** 5-10° (quasi-tendu)
- **Flexion de hanche :** 70-100° au point bas
- **Dos :** STRICTEMENT neutre — aucune tolérance pour la flexion lombaire
- **Descente :** jusqu'à ressentir un étirement important des ischio-jambiers

#### Compensations Détectables via MediaPipe

Mêmes que le RDL avec une attention ENCORE PLUS GRANDE à la flexion lombaire car les genoux tendus augmentent le stress.

#### Corrections Prioritaires

1. **🔴 Flexion lombaire :** Priorité absolue — cet exercice est le plus à risque pour le bas du dos. "Si ton dos arrondit, RÉDUIS LE POIDS ou switch au RDL avec plus de flexion de genoux."
2. **🟡 Genoux qui se verrouillent complètement :** "Garde une micro-flexion de tes genoux. Verrouillé à 100% c'est du stress inutile sur les ligaments."

#### Exercices Correctifs

1. **RDL avec genoux plus fléchis (3x10)** — régression si le SLDL est trop agressif
2. **Seated Good Morning (3x10)** — isole le hip hinge sans stress de stabilité

#### Erreurs par Niveau

**Débutant :** Ne devrait PAS faire cet exercice — commencer par le RDL
**Intermédiaire :** Flexion lombaire, descend trop bas
**Avancé :** Léger arrondi thoracique acceptable, mais lombaire jamais

---

### Exercice 16 : Hip Thrust

**Description :** Extension de hanche avec le haut du dos sur un banc, barre sur les hanches. L'exercice n°1 pour les fessiers.

**Muscles principaux :** Grand fessier (activation maximale)
**Muscles secondaires :** Ischio-jambiers, quadriceps, adducteurs

#### Angles Optimaux

- **Position haute (lockout) :** hanches à 180° (alignées avec les épaules et les genoux) — PAS d'hyperextension
- **Flexion de genou :** 90° au lockout (tibia vertical)
- **Bas du dos :** NE CHANGE PAS — le mouvement vient de la HANCHE, pas de la colonne
- **Position des pieds :** largeur de hanches, talons au sol
- **Regard :** vers l'avant, menton légèrement rentré (pas regarder le plafond)
- **Position du banc :** bord inférieur de la scapula sur le banc
- **Barre :** dans le pli de hanche, avec un pad

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Hyperextension lombaire au lockout | Épaule (11/12), Hanche (23/24), Genou (25/26) | Hanches montent AU-DELÀ de la ligne épaule-genou > 5° | 🔴 Critique |
| Extension incomplète | Angle hanche au sommet | < 170° | 🟡 Modéré |
| Pieds trop loin (trop de hamstrings) | Angle genou au lockout | > 110° | 🟡 Modéré |
| Pieds trop près (trop de quadriceps) | Angle genou au lockout | < 70° | 🟡 Modéré |
| Hyperextension cervicale (regarde le plafond) | Angle tête-torse | > 190° | 🟡 Modéré |
| Genoux qui s'ouvrent ou se ferment | Écart genoux vs écart pieds | Variation > 10 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Hyperextension lombaire :** "Tu montes trop haut — tu cambres le dos au lieu d'étendre les hanches. Le mouvement s'arrête quand tes hanches sont alignées avec tes épaules et tes genoux. Contracte tes abdos en haut et squeeze tes fessiers."
2. **🟡 Extension incomplète :** "Tu ne montes pas assez haut. Extension complète de hanche avec un squeeze de 1 seconde en haut, c'est là que tes fessiers travaillent le plus."
3. **🟡 Position des pieds :** "Ajuste tes pieds pour que tes tibias soient verticaux quand tu es en haut. Ça maximise l'activation des fessiers."
4. **🟡 Cervicale :** "Garde ton regard vers l'avant, pas vers le plafond. Menton légèrement rentré. Ça protège ta colonne cervicale."

#### Exercices Correctifs

1. **Glute Bridge au sol (3x15, 2sec squeeze en haut)** — même pattern, moins de ROM, focus sur la contraction
2. **Single Leg Hip Thrust (3x10/côté)** — corrige les asymétries de fessier
3. **Banded Hip Thrust (3x12, bande au-dessus des genoux)** — force les genoux dehors pour meilleure activation du moyen fessier

#### Erreurs par Niveau

**Débutant :** Hyperextension lombaire, pieds mal placés, pousse avec les orteils au lieu des talons
**Intermédiaire :** ROM incomplet, tempo trop rapide, pas de squeeze en haut
**Avancé :** Asymétrie subtile, perte de posterior pelvic tilt en haut

---

### Exercice 17 : Glute Bridge

**Description :** Même mouvement que le hip thrust mais allongé au sol. Moins de ROM mais plus accessible.

**Muscles principaux :** Grand fessier
**Muscles secondaires :** Ischio-jambiers, core

#### Angles Optimaux

- **Extension de hanche au sommet :** 180° (aligné)
- **Flexion de genou :** 90° au sommet
- **Pieds :** à plat au sol, largeur de hanches
- **Dos :** neutre, NE CAMBRE PAS en haut

#### Compensations

Mêmes que le hip thrust, avec moins de risque car la ROM est réduite. Points d'attention principaux :
- Hyperextension lombaire au sommet
- Poussée avec les orteils au lieu des talons
- Genoux qui s'ouvrent (bande recommandée)

#### Exercices Correctifs

1. **Banded Glute Bridge (3x20, 1sec squeeze)** — activation, pas force
2. **Frog Pump (3x20)** — excellent pour l'activation des fessiers, pieds plante contre plante

---

### Exercice 18 : Leg Curl Assis

**Description :** Isolation des ischio-jambiers en position assise, flexion de genou contre résistance.

**Muscles principaux :** Ischio-jambiers (les 3 chefs)
**Muscles secondaires :** Gastrocnémiens (mollets)

#### Angles Optimaux

- **Extension de départ :** genou quasi-tendu (170-175°, pas d'hyperextension)
- **Flexion maximale :** ≤ 60° (plus petit = meilleur, viser sous 45°)
- **Dossier :** légèrement incliné en arrière pour pré-étirer les ischio-jambiers (car ils sont bi-articulaires — crossent la hanche ET le genou)
- **Position du pad :** juste au-dessus du talon d'Achille, PAS sur le tendon

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Fesses qui décollent du siège | Hanche (23/24) | Élévation > 3 cm | 🟡 Modéré |
| Utilisation de momentum | Vitesse angulaire initiale | Pic de vitesse > 2x moyenne | 🟡 Modéré |
| ROM incomplet | Angle genou minimum | > 70° | 🟡 Modéré |
| Compensation avec le torse (inclinaison vers l'avant) | Épaule (11/12) | Mouvement vers l'avant > 5 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Fesses qui décollent :** "Tes fesses décollent du siège — charge trop lourde. Réduis et contrôle."
2. **🟡 ROM :** "Fléchis tes genoux au maximum, contracte 1 seconde en bas (genoux fléchis), puis remonte lentement. Le retour lent c'est là que les ischio-jambiers s'allongent sous tension."

#### Exercices Correctifs

1. **Nordic Curl (excentrique seulement, 3x5)** — renforce les ischio-jambiers en excentrique, prévention des blessures
2. **Single Leg Curl (3x10/côté)** — corrige les asymétries

---

### Exercice 19 : Leg Curl Allongé

**Description :** Isolation des ischio-jambiers allongé face contre le banc.

**Muscles principaux :** Ischio-jambiers
**Muscles secondaires :** Gastrocnémiens

#### Angles Optimaux

- **Extension :** 170-175°
- **Flexion maximale :** viser ≤ 50°
- **Hanches :** plaquées contre le banc, ne décollent PAS
- **Pad :** au-dessus du talon d'Achille

#### Différence avec le Leg Curl Assis

- Position couchée = ischio-jambiers dans une position plus raccourcie au niveau de la hanche → moins d'étirement → peut généralement aller plus lourd
- Le leg curl assis pré-étire davantage les ischio-jambiers (flexion de hanche) → meilleur stimulus en position allongée

#### Compensations

- **Hanches qui décollent :** compensation la plus fréquente. "Si tes hanches décollent, la charge est trop lourde. Le pad du banc doit les maintenir en place."
- **Hyperextension lombaire :** le dos se cambre quand la charge est trop lourde
- **Momentum :** même problème que le curl assis

---

### Exercice 20 : Good Morning

**Description :** Hip hinge avec la barre sur le haut du dos (position squat), flexion de hanche en gardant les genoux légèrement fléchis.

**Muscles principaux :** Ischio-jambiers, érecteurs du rachis, grand fessier
**Muscles secondaires :** Core, grand dorsal

#### Angles Optimaux

- **Flexion de genou :** 15-25° (fixe)
- **Flexion de hanche :** jusqu'à ce que le torse soit parallèle au sol (ou légèrement au-dessus)
- **Dos :** strictement neutre — C'EST L'EXERCICE LE PLUS EXIGEANT POUR LA NEUTRALITÉ LOMBAIRE
- **Barre :** position haute (comme un high bar squat)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Flexion lombaire | Angle lombaire | Tout arrondi détectable | 🔴 CRITIQUE |
| Genoux qui fléchissent pendant le mouvement | Angle genou | Changement > 10° | 🟡 Modéré |
| Descente trop profonde | Angle torse vs horizontal | Torse descend sous l'horizontale | 🟡 Modéré |
| Hyperextension au retour | Angle hanche | > 185° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Flexion lombaire :** "Le good morning avec un dos arrondi c'est la recette pour une hernie discale. Si ton dos ne reste pas PARFAITEMENT plat, réduis la charge ou régresse au RDL."
2. **🟡 Trop de flexion de genou :** "Ce n'est pas un squat — tes genoux doivent rester quasi-fixes. Le mouvement est un hip hinge pur."

#### Exercices Correctifs

1. **Seated Good Morning (3x10, charge légère)** — réduit le stress de stabilisation
2. **RDL (3x8)** — même pattern, moins de stress avec la barre devant

---

### Exercice 21 : Cable Pull-Through

**Description :** Hip hinge avec câble entre les jambes. Excellent exercice d'apprentissage du hip hinge et d'activation des fessiers.

**Muscles principaux :** Grand fessier, ischio-jambiers
**Muscles secondaires :** Érecteurs du rachis, core

#### Angles Optimaux

- **Flexion de hanche :** 80-100° en bas
- **Genoux :** légèrement fléchis (15-25°), fixes
- **Lockout :** hanches à 180°, squeeze fessiers
- **Dos :** neutre tout le long
- **Bras :** tendus, ne tirent PAS avec les bras

#### Compensations

- Traction avec les bras au lieu de hip hinge
- Hyperextension lombaire au lockout
- Genoux qui fléchissent trop (transforme en squat)

---

### Exercice 22 : Nordic Curl

**Description :** Exercice excentrique pour les ischio-jambiers. À genoux, pieds fixés, descente contrôlée vers l'avant.

**Muscles principaux :** Ischio-jambiers (excentrique puissant)
**Muscles secondaires :** Gastrocnémiens, core

#### Angles Optimaux

- **Position de départ :** corps droit de la tête aux genoux (aucune flexion de hanche)
- **Descente :** le corps descend en bloc, contrôlé par les ischio-jambiers
- **Point critique :** NE PAS casser à la hanche — le corps reste rigide
- **Remontée :** pour les débutants, utiliser les mains pour remonter (push-up assist)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Cassure à la hanche | Épaule (11/12), Hanche (23/24), Genou (25/26) | Angle < 160° au niveau de la hanche | 🟡 Modéré |
| Chute non contrôlée | Vitesse de descente | Accélération soudaine (perte de contrôle) | 🔴 Critique |
| Hyperextension lombaire | Angle lombaire | Cambrure > 10° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Chute non contrôlée :** "Si tu tombes en avant sans contrôle, utilise une bande élastique attachée en haut et autour de ta poitrine pour t'assister. Le but c'est la descente lente, pas de se casser la figure."
2. **🟡 Cassure de hanche :** "Ton corps doit rester en planche de la tête aux genoux. Si tu casses à la hanche, c'est que tes ischio-jambiers ont lâché et que tu compenses."

#### Exercices Correctifs

1. **Nordic Curl excentrique assisté (bande, 3x5, 5sec de descente)** — régression progressive
2. **Slider Leg Curl (3x8)** — travail excentrique des ischio-jambiers avec moins d'intensité

---

### Exercice 23 : Fentes Arrière (Reverse Lunge)

**Description :** Fente en reculant une jambe. Plus safe que la fente avant (moins de stress sur le genou), excellent pour les fessiers.

**Muscles principaux :** Grand fessier, quadriceps (jambe avant)
**Muscles secondaires :** Ischio-jambiers, adducteurs, core

#### Angles Optimaux

- **Genou avant :** 85-95° de flexion
- **Genou arrière :** descend à 5-10 cm du sol
- **Torse :** 5-20° d'inclinaison (plus incliné = plus de fessiers)
- **Poids :** 80% sur la jambe avant
- **Pied avant :** reste planté au sol, ne bouge pas

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Valgus genou avant | Hanche → Genou → Cheville | Déviation médiale > 8° | 🔴 Critique |
| Torse qui s'effondre | Épaule → Hanche → Verticale | Angle > 30° | 🟡 Modéré |
| Pas trop court | Angle genou arrière au point bas | > 110° | 🟡 Modéré |
| Instabilité latérale | Oscillation du torse | > 8 cm | 🟡 Modéré |
| Pied avant qui bouge/pivote | Position landmark pied | Déplacement > 3 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Valgus :** "Même correction que les autres fentes — genou au-dessus du 3ème orteil."
2. **🟡 Pas arrière trop court :** "Recule plus loin pour permettre une descente complète. Ton genou arrière doit presque toucher le sol."
3. **🟡 Instabilité :** "Imagine que tu marches sur un rail — tes pieds doivent être sur deux lignes parallèles, pas une seule ligne."

#### Exercices Correctifs

1. **Split Squat statique (3x10/côté)** — même pattern sans le mouvement de recul
2. **Banded Lateral Walk (3x12/côté)** — stabilité de hanche

---

## 3.3 POITRINE

---

### Exercice 24 : Bench Press (Plat)

**Description :** Développé couché avec barre sur un banc plat. L'exercice roi pour les pectoraux.

**Muscles principaux :** Grand pectoral (faisceau sternal), deltoïde antérieur, triceps
**Muscles secondaires :** Biceps (stabilisation), grand dorsal (stabilisation), core

#### Angles Optimaux

- **Position sur le banc :**
  - Yeux sous la barre au rack
  - 5 points de contact : tête, haut du dos, fessiers, pied gauche, pied droit
  - Arche thoracique (PAS lombaire) — les omoplates serrées et basses créent cette arche naturellement
- **Prise :** 1.5-2x largeur d'épaules (index sur les anneaux de la barre pour la plupart)
- **Unrack :** bras tendus, barre au-dessus des épaules
- **Descente :**
  - Barre descend vers le bas des pectoraux / haut de l'abdomen (PAS vers le cou)
  - Point de contact : ligne du mamelon ou légèrement en dessous
  - Coudes à 45-75° du torse (PAS à 90° — impingement)
- **Point bas :** barre touche la poitrine (pause ou touch-and-go)
  - Flexion du coude : ≈ 90° ou légèrement en dessous
  - Avant-bras VERTICAUX vus de face et de profil
- **Montée :** légèrement en arc (back and up), finit au-dessus des épaules
- **Lockout :** bras tendus, coudes NON hyperextendus

**Adaptations morphologiques :**
- Bras longs : plus de ROM, touch point plus bas, prise potentiellement plus large
- Bras courts : moins de ROM, avantage mécanique
- Torse en tonneau : moins de ROM (avantage)
- Épaules larges : prise plus large naturellement

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Coudes trop écartés (flare 90°) | Coude (13/14), Épaule (11/12), Hanche (23/24) | Angle humérus-torse > 80° | 🔴 Critique (impingement) |
| Fessiers qui décollent du banc | Hanche (23/24) | Élévation > 3 cm pendant la montée | 🟡 Modéré |
| Barre rebondit sur la poitrine | Vitesse de la barre | Accélération soudaine au point bas | 🟡 Modéré |
| Barre descend trop haut (vers le cou) | Point de contact Poignet (15/16) vs Épaule (11/12) | Barre au-dessus de la ligne des épaules au point bas | 🔴 Critique |
| Perte de rétraction scapulaire | Épaules (11/12) | Épaules avancent pendant la montée > 3 cm | 🟡 Modéré |
| Avant-bras non verticaux | Poignet (15/16), Coude (13/14) | Angle avant-bras vs verticale > 15° | 🟡 Modéré |
| Un bras monte plus vite | Poignet G (15) vs Poignet D (16) | Différence de hauteur > 3 cm pendant la montée | 🟡 Modéré |
| Pieds qui bougent | Cheville (27/28) | Déplacement > 3 cm | 🟢 Mineur |
| Poignets en extension | Angle poignet (15/16) vs coude (13/14) | Poignet plié en arrière > 30° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Coudes trop écartés :** "Tes coudes sont quasiment à 90° du corps — c'est la position qui détruit les épaules. Rentre tes coudes à environ 45-60° du torse. La barre doit descendre vers le bas de tes pecs, pas vers ton cou."
2. **🔴 Touch point trop haut :** "La barre descend trop vers ton cou/tes épaules. Elle doit toucher au niveau de tes mamelons ou juste en dessous. Ça protège tes épaules."
3. **🟡 Perte de rétraction scapulaire :** "Tes épaules avancent pendant que tu pousses. Serre tes omoplates AVANT l'unrack et garde-les serrées pendant TOUT le set. Pense à 'écraser un crayon entre tes omoplates'."
4. **🟡 Fessiers qui décollent :** "Tes fesses décollent du banc. Ça veut dire que tu utilises un drive de jambes excessif ou que la charge est trop lourde. Plante tes pieds et utilise le drive de jambes pour pousser DANS le banc, pas pour lever les hanches."
5. **🟡 Poignets :** "Tes poignets sont pliés en arrière. La barre doit reposer dans la paume, sur la ligne du radius (os de l'avant-bras). Un poignet droit = plus de force et moins de douleur."

#### Exercices Correctifs

1. **Bench Press pause (3x5 à 70%, 2sec pause sur la poitrine)** — enseigne le contrôle et la position correcte en bas
2. **Band Pull-Apart (3x15)** — renforce les rétracteurs scapulaires pour maintenir la position des omoplates
3. **Push-up avec protraction+ (3x12)** — enseigne la conscience scapulaire et la bonne mécanique de pressing

#### Erreurs par Niveau

**Débutant :** Pas de rétraction scapulaire, coudes à 90°, rebond sur la poitrine, pieds en l'air, barre vers le cou
**Intermédiaire :** Perte de rétraction en milieu de set, fessiers décollent sous charge, asymétrie de montée
**Avancé :** Touch point qui migre légèrement quand la fatigue arrive, léger flare de coudes sur les dernières reps

---

### Exercice 25 : Incline Bench Press

**Description :** Bench press sur un banc incliné (15-45°). Emphase sur le faisceau claviculaire (haut des pecs) et deltoïde antérieur.

**Muscles principaux :** Grand pectoral (faisceau claviculaire), deltoïde antérieur, triceps
**Muscles secondaires :** Grand pectoral (faisceau sternal), biceps

#### Angles Optimaux

- **Inclinaison du banc :** 15-30° optimal pour les pecs supérieurs. Au-delà de 45° = trop de deltoïde antérieur
- **Touch point :** plus haut que le bench plat — au niveau de la clavicule/haut des pecs
- **Coudes :** 45-60° du torse
- **Prise :** même largeur ou légèrement plus étroite que le bench plat
- **Avant-bras :** verticaux de face et de profil au point bas

#### Compensations

Mêmes compensations que le bench plat, avec en plus :
- **Excès de deltoïde antérieur** si le banc est trop incliné (> 45°)
- **Arche excessive** pour compenser l'angle (transforme l'incliné en presque plat)
- **Touch point trop haut** (vers le cou) → risque amplifié par l'angle

#### Corrections Prioritaires

1. **🔴 Coudes à 90° :** Encore PLUS dangereux qu'en plat car l'épaule est dans une position plus vulnérable
2. **🟡 Banc trop incliné :** "Si tu sens tes épaules plus que tes pecs, baisse l'inclinaison. 30° c'est le sweet spot pour la plupart des gens."
3. **🟡 Arche excessive :** "Tu cambres tellement que tu transformes l'exercice en bench presque plat. Une arche modérée c'est bien, mais garde l'angle."

---

### Exercice 26 : Decline Bench Press

**Description :** Bench press sur banc décliné (15-30°). Emphase sur le faisceau sternal inférieur et réduit le stress sur les épaules.

**Muscles principaux :** Grand pectoral (faisceau sternal inférieur), triceps
**Muscles secondaires :** Deltoïde antérieur (moins sollicité qu'en plat)

#### Angles Optimaux

- **Déclinaison :** 15-30° (au-delà = trop de sang à la tête, peu de bénéfice supplémentaire)
- **Touch point :** sous les mamelons, vers le bas des pecs
- **Coudes :** 45-60° (comme le bench plat)
- **ROM :** naturellement réduit par rapport au plat — normal

#### Compensations

- Mêmes que le bench plat
- Attention supplémentaire au rerack (position plus difficile)
- Tendance à utiliser plus de momentum car la barre "tombe" naturellement

---

### Exercice 27 : Dumbbell Press (Plat)

**Description :** Développé couché avec haltères. Plus de ROM et de travail de stabilisation que la barre.

**Muscles principaux :** Grand pectoral, deltoïde antérieur, triceps
**Muscles secondaires :** Biceps, stabilisateurs de l'épaule

#### Angles Optimaux

- **Position de départ :** haltères au-dessus des épaules, paumes vers les pieds
- **Descente :** haltères descendent à côté de la poitrine, coudes à 45-60°
- **Point bas :** haltères au niveau de la poitrine, étirement des pectoraux
- **Montée :** légère convergence des haltères (pas besoin de les toucher en haut)
- **Avant-bras :** verticaux de face au point bas

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Haltères trop bas (étirement excessif) | Coude (13/14) | Coude descend > 5 cm sous la ligne du banc | 🟡 Modéré |
| Asymétrie de mouvement | Poignet G (15) vs Poignet D (16) | Différence de trajectoire > 5 cm | 🟡 Modéré |
| Coudes à 90° | Même que bench | Même critères | 🔴 Critique |
| Rotation des poignets | Angle des poignets | Rotation > 30° entre haut et bas | 🟢 Mineur |
| Perte de rétraction scapulaire | Épaules (11/12) | Avancent > 3 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Coudes trop écartés :** Même correction que le bench barre
2. **🟡 Descente trop profonde :** "Tu descends trop bas — tes coudes passent loin sous le banc. L'étirement c'est bien, mais pas au point de mettre tes épaules en danger. Descends jusqu'à ce que tes bras soient parallèles au sol, pas plus."
3. **🟡 Asymétrie :** "Un bras monte plus vite que l'autre. Concentre-toi sur pousser de manière identique des deux côtés. Si l'asymétrie persiste, fais du travail unilatéral."

#### Exercices Correctifs

1. **Single Arm Dumbbell Press (3x10/côté)** — corrige les asymétries
2. **Banded Face Pull (3x15)** — rétraction et stabilité scapulaire

---

### Exercice 28 : Dumbbell Fly

**Description :** Mouvement d'ouverture/fermeture avec haltères. Isolation des pectoraux avec un grand étirement.

**Muscles principaux :** Grand pectoral (emphase sur l'adduction)
**Muscles secondaires :** Deltoïde antérieur, biceps (stabilisation)

#### Angles Optimaux

- **Coudes :** légèrement fléchis (15-20°) et FIXES pendant tout le mouvement
- **Descente :** bras s'ouvrent dans le plan de la poitrine, jusqu'à ressentir un étirement
- **Point bas :** haltères à hauteur de la poitrine, pas plus bas
- **Montée :** même arc de cercle, haltères convergent au-dessus de la poitrine
- **Angle du bras :** le mouvement se fait dans le plan frontal, pas sagittal

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Coudes qui fléchissent davantage (transforme en press) | Angle coude | Flexion > 40° | 🟡 Modéré |
| Descente trop profonde | Coude (13/14) sous le plan du banc | > 8 cm sous le banc | 🔴 Critique (risque épaule) |
| Momentum en bas (rebond) | Vitesse en bas de mouvement | Changement de direction brutal | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Trop profond :** "Tu descends trop bas, tes épaules sont dans une position vulnérable. Arrête la descente quand tes bras sont au niveau de ta poitrine."
2. **🟡 Transformation en press :** "Tes coudes fléchissent trop — tu fais un press, pas un fly. Fixe la flexion de tes coudes et ne change plus. Le mouvement est un arc de cercle, pas un push."

---

### Exercice 29 : Cable Crossover

**Description :** Fly avec câbles. Tension constante et possibilité de varier les angles.

**Muscles principaux :** Grand pectoral
**Muscles secondaires :** Deltoïde antérieur, biceps

#### Angles Optimaux

- **Poulies hautes :** travaille les fibres sternales basses (mouvement haut vers bas)
- **Poulies à hauteur d'épaule :** travaille les fibres sternales moyennes
- **Poulies basses :** travaille les fibres claviculaires (mouvement bas vers haut)
- **Coudes :** légèrement fléchis (15-25°), fixes
- **Position des pieds :** un pied devant l'autre pour la stabilité (stance décalée)
- **Torse :** léger inclinaison en avant (15-20°)
- **Squeeze en fin de mouvement :** les mains se croisent légèrement

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Utilisation de momentum (balancement du torse) | Épaule (11/12) | Oscillation > 8 cm | 🟡 Modéré |
| Coudes qui fléchissent | Angle coude | Changement > 15° entre début et fin | 🟡 Modéré |
| Rotation du torse | Épaules (11 vs 12) | Asymétrie > 5 cm avant-arrière | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Momentum :** "Tu balances ton corps pour bouger la charge. Fixe ton torse et fais le mouvement uniquement avec tes bras. Réduis le poids si nécessaire."
2. **🟡 Pas de squeeze :** "Contracte tes pecs 1 seconde quand tes mains se rejoignent. C'est le point de contraction maximale."

---

### Exercice 30 : Dips (Pectoraux)

**Description :** Dips avec inclinaison du torse vers l'avant pour cibler les pectoraux. Différent des dips triceps.

**Muscles principaux :** Grand pectoral (faisceau sternal inférieur), triceps, deltoïde antérieur
**Muscles secondaires :** Core, stabilisateurs scapulaires

#### Angles Optimaux

- **Inclinaison du torse :** 20-30° vers l'avant (c'est ce qui différencie les dips pecs des dips triceps)
- **Flexion du coude au point bas :** 90° ou légèrement en dessous
- **Coudes :** légèrement écartés (30-45° du torse)
- **Épaules :** ne doivent PAS descendre en dessous de la ligne des coudes (protection de l'épaule)
- **Lockout :** bras quasi-tendus en haut, sans hyperextension

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Descente trop profonde | Épaule (11/12) vs Coude (13/14) | Épaule descend > 5 cm sous le coude | 🔴 Critique (épaule) |
| Torse trop vertical (transforme en dips triceps) | Angle torse vs verticale | < 10° | 🟡 Modéré |
| Balancement/kipping | Oscillation des hanches | > 10 cm avant-arrière | 🟡 Modéré |
| ROM incomplet | Angle coude minimum | > 110° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Trop profond :** "Tu descends trop bas — tes épaules passent en dessous de tes coudes. Ça met un stress énorme sur la capsule articulaire de l'épaule. Arrête quand tes coudes sont à 90°."
2. **🟡 Pas assez incliné :** "Penche ton torse un peu plus en avant et lève les pieds derrière toi. Ça va shifter le travail vers les pecs."
3. **🟡 Kipping :** "Pas de balancement — descente contrôlée, montée avec force. Si tu ne peux pas faire des reps propres, utilise une bande d'assistance."

#### Exercices Correctifs

1. **Dips négatifs (3x5, 5sec de descente)** — contrôle excentrique
2. **Push-ups déclinés (3x12)** — même pattern angulaire avec moins de charge

---

### Exercice 31 : Push-ups (et Variantes)

**Description :** Le classique. Corps en planche, on descend et on monte. Similaire au bench press en chaîne fermée inversée.

**Muscles principaux :** Grand pectoral, deltoïde antérieur, triceps
**Muscles secondaires :** Core (anti-extension), serratus anterior (en fin de mouvement)

#### Angles Optimaux

- **Position de départ :** bras tendus, corps en planche de la tête aux talons
- **Mains :** légèrement plus larges que les épaules, au niveau du bas des pectoraux
- **Descente :** coudes à 45° du torse (PAS à 90°)
- **Point bas :** poitrine à 5 cm du sol (ou touche)
- **Corps :** RIGIDE — pas de hanche qui descend (sway back) ni qui monte (pike)
- **Tête :** neutre, ne regarde pas devant (hyperextension cervicale)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Hanche qui s'affaisse (sway back) | Épaule (11/12), Hanche (23/24), Cheville (27/28) | Hanche descend > 5 cm sous la ligne épaule-cheville | 🔴 Critique |
| Hanche trop haute (pike) | Même ligne | Hanche monte > 5 cm au-dessus de la ligne | 🟡 Modéré |
| Coudes à 90° | Coude-Épaule-Hanche | Angle > 80° | 🟡 Modéré |
| ROM incomplet | Distance poitrine-sol | > 15 cm au point le plus bas | 🟡 Modéré |
| Tête en avant | Oreille vs Épaule | Oreille > 5 cm en avant de l'épaule | 🟢 Mineur |
| Un côté monte avant l'autre | Épaule G (11) vs Épaule D (12) | Différence > 3 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Hanche qui s'affaisse :** "Ton bassin descend — ça veut dire que ton core lâche. Contracte tes abdos et tes fessiers comme si tu faisais une planche. Si tu ne tiens pas, fais des push-ups sur les genoux."
2. **🟡 Coudes à 90° :** "Tes coudes partent sur les côtés. Rentre-les à 45° du corps. Ça protège tes épaules et recrute mieux les pecs."
3. **🟡 ROM partiel :** "Descends jusqu'à ce que ta poitrine touche (presque) le sol. Un push-up à moitié fait ne développe que la moitié de la force."

#### Variantes et Différences Biomécaniques

- **Push-up standard :** équivalent bench press plat (environ 65% du poids de corps)
- **Push-up incliné (mains surélevées) :** plus facile, moins de charge, idéal débutant
- **Push-up décliné (pieds surélevés) :** plus de travail du haut des pecs, plus de charge
- **Diamond push-up :** emphase triceps, mains en losange sous la poitrine
- **Wide push-up :** plus de pec, moins de triceps, attention aux épaules
- **Push-up avec protraction :** en haut, pousser encore plus pour séparer les omoplates — travaille le serratus anterior

#### Exercices Correctifs

1. **Planche (hold 3x30sec)** — renforce le core pour maintenir l'alignement
2. **Push-up incliné (3x12)** — régression pour maîtriser la forme
3. **Dead Bug (3x10/côté)** — core anti-extension

---

## 3.4 DOS

---

### Exercice 32 : Pull-up (Pronation)

**Description :** Traction à la barre en prise pronation (paumes vers l'avant). L'exercice roi du dos.

**Muscles principaux :** Grand dorsal, grand rond, trapèze moyen/inférieur
**Muscles secondaires :** Biceps, brachial, avant-bras, rhomboïdes, deltoïde postérieur

#### Angles Optimaux

- **Position de départ :** bras tendus (dead hang), omoplates en rotation vers le haut
- **Prise :** 1.2-1.5x largeur d'épaules
- **Initiation :** SCAPULAIRE — les omoplates descendent et se rétractent AVANT que les coudes fléchissent
- **Point haut :** menton au-dessus de la barre (minimum), poitrine vers la barre
- **Coudes :** tirent vers le bas et vers l'arrière (vers les hanches)
- **Torse :** légère arche thoracique, poitrine ouverte

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Kipping / balancement | Hanche (23/24), Cheville (27/28) | Oscillation > 15 cm | 🟡 Modéré (sauf si intentionnel CrossFit) |
| Menton pas au-dessus de la barre | Menton vs barre | Menton ne dépasse pas | 🟡 Modéré |
| Montée avec les bras (pas d'initiation scapulaire) | Épaule (11/12) | Pas de dépression scapulaire avant la flexion de coude | 🟡 Modéré |
| Asymétrie | Épaule G (11) vs Épaule D (12) | Différence de hauteur > 3 cm | 🟡 Modéré |
| Hyperextension cervicale (menton vers la barre) | Oreille, Épaule | Craning du cou pour "passer" | 🟡 Modéré |
| Genoux qui montent (compensation) | Hanche (23/24), Genou (25/26) | Flexion de hanche > 30° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Pas d'initiation scapulaire :** "Avant de plier tes coudes, commence par tirer tes omoplates vers le bas. Imagine que tu veux mettre tes omoplates dans tes poches arrière. C'est ce mouvement qui engage le dos plutôt que les biceps."
2. **🟡 ROM incomplet :** "Monte jusqu'à ce que ton menton passe AU-DESSUS de la barre. Si tu ne peux pas, utilise des bandes d'assistance ou fais des négatifs."
3. **🟡 Kipping :** "Reste rigide du tronc — pas de balancement. Un pull-up strict c'est infiniment mieux pour le développement musculaire qu'un kipping."
4. **🟡 Cou qui crane :** "Ne pousse pas ton menton vers la barre — c'est tricher. C'est ta poitrine qui doit aller vers la barre."

#### Exercices Correctifs

1. **Scapular Pull-up (3x10)** — apprend l'initiation scapulaire
2. **Negative Pull-up (3x5, 5sec de descente)** — renforce le mouvement excentrique
3. **Band-Assisted Pull-up (3x8)** — permet de pratiquer le mouvement complet avec assistance

#### Erreurs par Niveau

**Débutant :** Pas capable d'en faire un seul → travailler les négatifs et bandes. Tire avec les biceps, pas d'initiation scapulaire.
**Intermédiaire :** ROM incomplet, kipping subtil, asymétrie
**Avancé :** Tempo trop rapide, manque de contrôle en dead hang, fatigue scapulaire

---

### Exercice 33 : Chin-up (Supination)

**Description :** Traction en prise supination (paumes vers soi). Plus de biceps, légèrement plus facile que le pull-up.

**Muscles principaux :** Grand dorsal, biceps, brachial
**Muscles secondaires :** Grand rond, trapèze, rhomboïdes

#### Angles Optimaux

- **Prise :** largeur d'épaules ou légèrement plus étroite
- **Mêmes principes que le pull-up** pour l'initiation scapulaire et le ROM
- **Coudes :** tirent vers le bas et vers l'AVANT (contrairement au pull-up où c'est vers l'arrière)

#### Différences avec le Pull-up

- Plus de biceps (supination = biceps en position avantageuse)
- Généralement 10-15% plus de force qu'en pronation
- Plus de stress sur le biceps distal → attention aux tendinites si volume élevé
- Plus de recrutement du grand pectoral (faisceau sternal)

#### Compensations et Corrections

Identiques au pull-up. Attention supplémentaire :
- **Rotation excessive des poignets** vers la supination en montant → stress sur le coude
- **Coudes qui partent trop en avant** → transforme en curl plus que tirage

---

### Exercice 34 : Lat Pulldown

**Description :** Tirage vertical sur machine à câble. Même pattern que le pull-up mais avec charge ajustable.

**Muscles principaux :** Grand dorsal, grand rond, trapèze moyen/inférieur
**Muscles secondaires :** Biceps, brachial, rhomboïdes

#### Angles Optimaux

- **Prise :** 1.3-1.5x largeur d'épaules en pronation
- **Torse :** légèrement incliné en arrière (10-15°) — PAS à 45°
- **Tirage :** barre vers le haut de la poitrine (clavicule/sternum)
- **Initiation scapulaire :** identique au pull-up
- **Coudes :** dirigés vers le bas et légèrement vers l'arrière

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Inclinaison excessive du torse (lean back) | Épaule (11/12), Hanche (23/24) | Angle > 30° de la verticale | 🟡 Modéré |
| Utilisation de momentum | Oscillation du torse | Mouvement avant-arrière > 10 cm | 🟡 Modéré |
| Barre tirée derrière la nuque | Position de la barre vs Tête | Barre passe derrière la tête | 🔴 Critique (épaule) |
| Épaules qui montent (shrug) | Épaule (11/12) | Élévation > 3 cm | 🟡 Modéré |
| ROM incomplet | Distance barre-poitrine | Barre ne descend pas sous le menton | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Tirage derrière la nuque :** "NE TIRE PAS derrière la tête. Ça met tes épaules en position de rotation externe maximale sous charge — risque d'impingement et de blessure labrale. Tire vers ta poitrine."
2. **🟡 Trop de lean back :** "Tu te penches trop en arrière — ça transforme le pulldown en un rowing. Un léger angle c'est bien (10-15°), mais pas plus."
3. **🟡 Shrug :** "Tes épaules montent vers tes oreilles. Tire les omoplates VERS LE BAS d'abord, puis plie tes coudes."

#### Exercices Correctifs

1. **Straight Arm Pulldown (3x12)** — isole le grand dorsal et enseigne la dépression scapulaire
2. **Scapular Pull-up (3x10)** — même concept que pour les pull-ups

---

### Exercice 35 : Barbell Row (Pronation)

**Description :** Rowing barre en pronation (Pendlay ou bent-over row classique). Exercice composé majeur pour l'épaisseur du dos.

**Muscles principaux :** Grand dorsal, trapèze, rhomboïdes, deltoïde postérieur
**Muscles secondaires :** Biceps, érecteurs du rachis, ischio-jambiers (stabilisation), core

#### Angles Optimaux

- **Inclinaison du torse :** 30-45° pour le bent-over row classique, 90° (parallèle au sol) pour le Pendlay row
- **Flexion de genou :** 15-25° (légèrement fléchis)
- **Prise :** légèrement plus large que les épaules
- **Tirage :** barre vers le nombril/bas du sternum
- **Coudes :** tirent vers l'arrière et les hanches, PAS vers l'extérieur
- **Dos :** NEUTRE — c'est un exercice de dos, pas une excuse pour arrondir le dos
- **Lockout (contraction) :** omoplates serrées, barre touche le torse

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Dos arrondi | Angle lombaire | Flexion > 10° | 🔴 Critique |
| Torse qui se redresse (cheat row) | Angle torse | Changement > 20° entre début et fin | 🟡 Modéré |
| Utilisation de momentum (jerking) | Accélération de la barre | Pic initial > 3x vitesse moyenne | 🟡 Modéré |
| Coudes qui flare out | Angle coude-torse | > 60° | 🟡 Modéré |
| Barre ne touche pas le torse | Distance barre-torse | > 5 cm au point de contraction | 🟡 Modéré |
| Extension de hanche (se redresser) | Angle hanche | Augmente > 15° pendant le tirage | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Dos arrondi :** "Ton dos arrondit pendant le row. La position du row est un isométrique de ton dos — si tu ne peux pas maintenir le dos plat, la charge est trop lourde."
2. **🟡 Cheat row :** "Tu te redresses pour aider la barre à monter. Fixe l'angle de ton torse et bouge uniquement tes bras. Le row c'est un exercice strict, pas un power clean."
3. **🟡 Coudes trop écartés :** "Tes coudes partent sur les côtés — ça recrute plus les deltoïdes arrière et les trapèzes que les lats. Tire tes coudes vers tes hanches."

#### Exercices Correctifs

1. **Chest-Supported Row (3x10)** — élimine la composante de stabilisation lombaire
2. **Inverted Row (3x12)** — même pattern avec charge réduite et moins de stress lombaire
3. **RDL (3x8)** — renforce la position de maintien du hip hinge

#### Erreurs par Niveau

**Débutant :** Dos arrondi, se redresse à chaque rep, tire avec les biceps, barre ne touche pas le torse
**Intermédiaire :** Momentum subtil, angle de torse qui change, coudes trop écartés
**Avancé :** Léger momentum contrôlé (acceptable pour overload), asymétrie de tirage

---

### Exercice 36 : Barbell Row (Supination, Yates)

**Description :** Row en supination avec torse plus redressé (60-70° vs horizontale). Nommé d'après Dorian Yates. Plus de biceps, plus de bas du dos engagé.

**Muscles principaux :** Grand dorsal, biceps, trapèze
**Muscles secondaires :** Rhomboïdes, deltoïde postérieur, érecteurs du rachis

#### Différences avec le Row Pronation

- Supination = biceps en position avantageuse → plus de recrutement biceps
- Torse plus redressé (60-70°) → moins de stress lombaire
- Tirage vers le bas du sternum/nombril
- Prise plus étroite (largeur d'épaules)
- Risque plus élevé de tendinite du biceps distal sous charges lourdes

#### Compensations et Corrections

Mêmes principes que le row pronation. Attention supplémentaire au stress du biceps distal — si douleur au pli du coude, réduire la charge ou passer en pronation.

---

### Exercice 37 : Dumbbell Row (1 Bras)

**Description :** Row unilatéral avec un haltère, main et genou opposés sur un banc. Excellent pour corriger les asymétries.

**Muscles principaux :** Grand dorsal, trapèze, rhomboïdes
**Muscles secondaires :** Biceps, deltoïde postérieur, obliques (anti-rotation)

#### Angles Optimaux

- **Torse :** parallèle au sol ou à 15-20° au-dessus
- **Bras de travail :** tire l'haltère vers la hanche (pas vers la poitrine)
- **Coude :** reste près du torse, tire vers l'arrière
- **Rotation du torse :** MINIMALE — pas de twist pour monter la charge
- **Main d'appui :** sous l'épaule sur le banc
- **Contraction :** omoplates se rapprochent en haut, haltère au niveau de la hanche

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Rotation du torse | Épaule travail (11/12) vs Épaule appui | Rotation > 15° | 🟡 Modéré |
| Tirage trop haut (vers l'épaule) | Poignet (15/16) vs Hanche (23/24) | Poignet finit > 15 cm au-dessus de la hanche | 🟡 Modéré |
| Utilisation de momentum | Oscillation du torse | > 8 cm | 🟡 Modéré |
| Dos arrondi | Angle du torse | Flexion thoracique > 20° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Rotation excessive :** "Tu tournes ton torse pour lever l'haltère — ça recrute les obliques au lieu du dos. Fixe ton torse et tire uniquement avec le bras. Réduis le poids si nécessaire."
2. **🟡 Tirage vers l'épaule :** "Tu tires vers le haut au lieu de vers la hanche. Pense à 'démarrer une tondeuse' — tire vers ta hanche arrière."

---

### Exercice 38 : Seated Cable Row

**Description :** Rowing assis sur machine à câble. Tension constante, position assise stable.

**Muscles principaux :** Grand dorsal, trapèze, rhomboïdes
**Muscles secondaires :** Biceps, deltoïde postérieur, érecteurs du rachis

#### Angles Optimaux

- **Torse :** vertical ou légèrement incliné en avant au début, revient à la verticale à la contraction
- **Tirage :** vers le nombril/bas du sternum
- **Coudes :** près du corps, tirent vers l'arrière
- **Contraction :** squeeze scapulaire 1 sec, poitrine ouverte
- **Retour :** contrôlé, laisser les omoplates s'étirer en avant (protraction contrôlée)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Lean back excessif | Angle torse | Inclinaison arrière > 20° | 🟡 Modéré |
| Épaules qui montent (shrug) | Épaule (11/12) | Élévation > 3 cm | 🟡 Modéré |
| ROM incomplet (pas de squeeze scapulaire) | Position épaules | Pas de rétraction visible | 🟡 Modéré |
| Arrondi du dos à l'étirement | Angle thoracique | Cyphose > 25° en avant | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Lean back :** "Tu te penches trop en arrière pour tirer la charge. Fixe ton torse vertical et bouge uniquement les bras."
2. **🟡 Pas de rétraction :** "Serre tes omoplates à chaque rep. Le câble row sans squeeze scapulaire c'est un exercice de biceps, pas de dos."

---

### Exercice 39 : T-Bar Row

**Description :** Rowing avec une barre en mine (landmine) ou sur machine T-Bar. Permet de charger lourd avec moins de stress que le barbell row.

**Muscles principaux :** Grand dorsal, trapèze, rhomboïdes
**Muscles secondaires :** Biceps, érecteurs du rachis, deltoïde postérieur

#### Angles Optimaux

- Mêmes principes que le barbell row
- **Prise :** étroite (V-handle) ou large (handles latéraux)
- **Torse :** 30-45° d'inclinaison
- **Tirage :** vers le sternum
- **Avantage :** la nature convergente du mouvement (les plaques sont fixées d'un côté) change la courbe de résistance

#### Compensations et Corrections

Identiques au barbell row. L'avantage du T-bar est que la barre est fixée au sol, ce qui réduit le besoin de stabilisation et permet de se concentrer sur la contraction.

---

### Exercice 40 : Face Pull

**Description :** Tirage à la corde vers le visage, prise haute. L'exercice de santé d'épaule par excellence.

**Muscles principaux :** Deltoïde postérieur, trapèze moyen/inférieur, infra-épineux, petit rond
**Muscles secondaires :** Rhomboïdes, rotateurs externes de l'épaule

#### Angles Optimaux

- **Poulie :** à hauteur de visage ou légèrement au-dessus
- **Tirage :** vers les tempes/oreilles (PAS vers la poitrine — c'est un row)
- **Fin de mouvement :** rotation externe des bras (pouces vers l'arrière, "double biceps pose")
- **Coudes :** à hauteur d'épaule ou légèrement au-dessus
- **Rétraction scapulaire :** maximale en fin de mouvement
- **Torse :** stable, pas de lean back

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Tirage vers la poitrine (trop bas) | Poignet (15/16) | Poignets finissent sous les épaules | 🟡 Modéré |
| Lean back excessif | Angle torse | > 15° de la verticale | 🟡 Modéré |
| Pas de rotation externe | Angle poignet-coude fin de mouvement | Pas de rotation visible | 🟡 Modéré |
| Épaules qui montent | Épaule (11/12) | Élévation > 2 cm | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Tirage trop bas :** "Tu tires vers ta poitrine — c'est un row, pas un face pull. Tire vers tes oreilles et finis avec les pouces vers l'arrière, comme une pose double biceps."
2. **🟡 Charge trop lourde :** "Le face pull c'est un exercice de santé d'épaule, pas un exercice d'ego. Utilise une charge légère à modérée et concentre-toi sur la contraction et la rotation externe."

---

### Exercice 41 : Meadows Row

**Description :** Row unilatéral avec une barre en landmine, en stance perpendiculaire à la barre. Créé par John Meadows.

**Muscles principaux :** Grand dorsal, grand rond, trapèze
**Muscles secondaires :** Biceps, deltoïde postérieur, obliques

#### Angles Optimaux

- **Position :** perpendiculaire à la barre, un pied en avant
- **Prise :** overhand (pronation) sur l'extrémité de la barre
- **Tirage :** vers la hanche, arc de cercle
- **Torse :** incliné, bras d'appui sur le genou avant
- **Stretch en bas :** maximal, laisser la barre étirer le lat

#### Compensations et Corrections

Similaires au dumbbell row. Attention à la rotation du torse et à l'utilisation de momentum. L'avantage du Meadows row est l'étirement maximal du lat en position basse.

---

## 3.5 ÉPAULES

---

### Exercice 42 : Overhead Press (Barre Debout)

**Description :** Développé militaire debout avec barre. L'exercice composé principal pour les épaules. Demande une grande stabilité du tronc.

**Muscles principaux :** Deltoïde antérieur et latéral, triceps
**Muscles secondaires :** Trapèze supérieur, core (anti-extension), serratus anterior

#### Angles Optimaux

- **Position de départ :** barre sur les deltoïdes antérieurs / clavicules (front rack position)
- **Prise :** légèrement plus large que les épaules
- **Coudes :** devant la barre (pas derrière) en position de départ
- **Trajectoire de la barre :** VERTICALE — la barre monte en ligne droite. La tête recule pour laisser passer la barre, puis avance une fois la barre passée (bar path autour de la tête)
- **Lockout :** barre au-dessus du milieu du pied, bras tendus, tête passée "à travers la fenêtre"
- **Pieds :** largeur de hanches, au sol
- **Genoux :** verrouillés (pas de leg drive sauf push press)
- **Colonne :** neutre du début à la fin — PAS d'hyperextension lombaire

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Hyperextension lombaire (lean back) | Épaule (11/12), Hanche (23/24), Genou (25/26) | Angle hanche > 185° (hanches en avant) | 🔴 Critique |
| Barre devant le visage (trajectoire en arc) | Poignet (15/16) | Barre passe en arc vers l'avant au lieu de monter droit | 🟡 Modéré |
| Press push (leg drive) | Angle genou | Flexion-extension du genou > 10° pendant la rep | 🟡 Modéré (sauf si intentionnel) |
| Coudes derrière la barre | Coude (13/14) vs Poignet (15/16) | Coude derrière la ligne du poignet au départ | 🟡 Modéré |
| Asymétrie de lockout | Poignet G (15) vs Poignet D (16) | Différence de hauteur > 3 cm | 🟡 Modéré |
| Tête ne passe pas à travers | Position tête vs barre au lockout | Tête reste en arrière de la barre | 🟡 Modéré |

#### Corrections Prioritaires

1. **🔴 Hyperextension lombaire :** "Tu cambres excessivement le dos pour monter la charge. Ça transforme ton OHP en incline press debout et met une pression énorme sur tes lombaires. Serre tes abdos et tes fessiers comme si tu faisais une planche debout. Si tu dois te pencher en arrière, la charge est trop lourde."
2. **🟡 Trajectoire en arc :** "La barre doit monter en ligne droite. Recule ta tête pour laisser passer la barre, puis repasse ta tête en avant une fois la barre au-dessus. C'est 'autour de la tête', pas 'devant le visage'."
3. **🟡 Coudes :** "Place tes coudes légèrement DEVANT la barre en position de départ. Ça donne un meilleur angle de poussée."

#### Exercices Correctifs

1. **Z-Press (assis au sol, jambes tendues, 3x8)** — élimine le lean back car pas d'appui dorsal, force la stricte verticalité
2. **Pallof Press (3x10/côté)** — renforce le core anti-rotation/anti-extension
3. **Behind-the-Neck Press (léger, 3x10)** — mobilité d'épaule si pas de douleur

#### Erreurs par Niveau

**Débutant :** Hyperextension lombaire massive, trajectoire en arc, pas de bracing, charge trop lourde
**Intermédiaire :** Lean back subtil, leg drive involontaire, tête ne passe pas à travers
**Avancé :** Légère asymétrie de lockout, lean back minimal sur les dernières reps

---

### Exercice 43 : Seated Dumbbell Press

**Description :** Développé épaules assis avec haltères. Plus de ROM que la barre, moins de demande de stabilité grâce au dossier.

**Muscles principaux :** Deltoïde antérieur et latéral, triceps
**Muscles secondaires :** Trapèze supérieur, stabilisateurs de l'épaule

#### Angles Optimaux

- **Dossier :** 80-90° (quasi-vertical)
- **Position de départ :** haltères à hauteur d'épaule, coudes à 90°, avant-bras verticaux
- **Montée :** convergence légère des haltères en haut (pas besoin de toucher)
- **Lockout :** bras tendus au-dessus des épaules
- **Descente :** haltères redescendent au niveau des oreilles/mâchoire

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Dos qui arche (décolle du dossier) | Hanche (23/24), Épaule (11/12) | Espace visible entre dos et dossier | 🟡 Modéré |
| Coudes qui descendent trop bas | Coude (13/14) | Descend > 10 cm sous l'épaule | 🟡 Modéré |
| Asymétrie de montée | Poignet G vs D | Différence > 4 cm | 🟡 Modéré |
| Momentum (rebond en bas) | Vitesse au changement de direction | Rebond > 2x vitesse moyenne | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Arche du dos :** "Colle ton dos au dossier. Si tu dois arquer, la charge est trop lourde."
2. **🟡 Coudes trop bas :** "Ne descends pas les coudes trop en dessous de tes épaules — ça met les épaules en position vulnérable. Stoppe quand les haltères sont au niveau de tes oreilles."

---

### Exercice 44 : Arnold Press

**Description :** Variante du dumbbell press inventée par Arnold Schwarzenegger. Rotation des paumes de vers soi à vers l'avant pendant la montée.

**Muscles principaux :** Deltoïde (les 3 faisceaux grâce à la rotation), triceps
**Muscles secondaires :** Trapèze, stabilisateurs

#### Angles Optimaux

- **Position basse :** haltères devant les épaules, paumes vers soi, coudes devant le torse
- **Rotation :** commence à 30-40% de la montée, continue progressivement
- **Position haute :** paumes vers l'avant, lockout complet
- **Mouvement :** fluide et continu, la rotation accompagne la montée

#### Compensations et Corrections

- Mêmes que le seated dumbbell press, plus la rotation qui doit être fluide et pas saccadée
- Si la rotation est complète avant la mi-montée → trop rapide, perdant l'avantage de l'exercice

---

### Exercice 45 : Élévations Latérales (Haltères)

**Description :** Isolation du deltoïde latéral. Petite charge, technique stricte.

**Muscles principaux :** Deltoïde latéral (médial)
**Muscles secondaires :** Trapèze supérieur (si mauvaise forme), supraspinatus

#### Angles Optimaux

- **Position de départ :** haltères le long du corps ou légèrement devant les cuisses
- **Élévation :** dans le plan de la scapula (environ 20-30° devant le plan frontal pur)
- **Hauteur :** jusqu'à hauteur d'épaule (pas plus — au-delà c'est du trapèze)
- **Coude :** légèrement fléchi (15-20°) et FIXE
- **Poignet :** en ligne avec l'avant-bras, pas de rotation
- **Image mentale :** "verser une carafe d'eau" — le petit doigt légèrement plus haut que le pouce en haut du mouvement
- **Tempo :** montée 2sec, contrôle 1sec en haut, descente 3sec

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Shrug (trapèzes) | Épaule (11/12) | Élévation > 3 cm | 🟡 Modéré |
| Momentum/swing (balancement du torse) | Oscillation torse | > 10° d'oscillation | 🟡 Modéré |
| Élévation au-dessus de l'épaule | Poignet (15/16) vs Épaule (11/12) | Poignet > 5 cm au-dessus de l'épaule | 🟡 Modéré |
| Coudes qui fléchissent davantage | Angle coude | Changement > 15° pendant le mouvement | 🟡 Modéré |
| Flexion de coude excessive (biceps curl déguisé) | Angle coude | < 130° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Shrug :** "Tes épaules montent vers tes oreilles — tu utilises tes trapèzes au lieu de tes deltoïdes. Pense à BAISSER tes épaules pendant que tu montes les bras. Imagine que quelqu'un appuie sur tes épaules."
2. **🟡 Momentum :** "Tu balances ton corps. Réduis la charge de moitié — les élévations latérales ne demandent PAS beaucoup de poids. 8kg avec une technique parfaite > 15kg en swinguant."
3. **🟡 Trop haut :** "Stoppe à hauteur d'épaule. Au-delà, ce sont les trapèzes qui prennent le relais."

#### Exercices Correctifs

1. **Élévation latérale câble (3x15/côté)** — tension constante, moins de momentum possible
2. **Y-Raise sur banc incliné (3x12)** — isole le deltoïde sans possibilité de tricher

#### Erreurs par Niveau

**Débutant :** Charge beaucoup trop lourde, full body swing, shrug massif
**Intermédiaire :** Momentum subtil, coudes qui fléchissent, pas de contrôle excentrique
**Avancé :** Léger shrug sur les dernières reps, manque de pause en haut

---

### Exercice 46 : Élévations Latérales (Câble)

**Description :** Même mouvement qu'avec haltères mais au câble. Tension constante, courbe de résistance différente (plus de tension en position basse).

**Muscles principaux :** Deltoïde latéral
**Muscles secondaires :** Trapèze supérieur (si mauvaise forme)

#### Avantages sur les Haltères

- Tension constante sur toute la ROM (les haltères n'ont presque pas de résistance en bas)
- Moins de possibilité de tricher avec le momentum
- Possibilité de travailler derrière le dos pour un meilleur étirement

#### Mêmes principes et corrections que les élévations haltères.

---

### Exercice 47 : Élévations Frontales

**Description :** Élévation des bras vers l'avant. Isole le deltoïde antérieur (souvent déjà surdéveloppé par le bench/OHP).

**Muscles principaux :** Deltoïde antérieur
**Muscles secondaires :** Faisceau claviculaire du pectoral, trapèze

#### Angles Optimaux

- **Montée :** bras à l'horizontale (hauteur des yeux max)
- **Coudes :** légèrement fléchis
- **Alternance ou simultané :** les deux fonctionnent
- **Éviter le lean back**

#### Note Importante

Le deltoïde antérieur est DÉJÀ fortement sollicité par le bench press, l'incline press, et l'OHP. Les élévations frontales sont rarement nécessaires sauf si le deltoïde antérieur est un point faible spécifique, ce qui est rare.

---

### Exercice 48 : Reverse Fly / Rear Delt Fly

**Description :** Fly inversé pour le deltoïde postérieur. Peut se faire avec haltères sur banc incliné, debout penché, au câble ou à la machine.

**Muscles principaux :** Deltoïde postérieur, trapèze moyen/inférieur
**Muscles secondaires :** Rhomboïdes, infra-épineux

#### Angles Optimaux

- **Torse :** incliné à 45-90° (plus horizontal = plus de deltoïde postérieur)
- **Mouvement :** bras s'ouvrent dans le plan perpendiculaire au torse
- **Coudes :** légèrement fléchis (15-20°), FIXES
- **Contraction :** squeeze entre les omoplates, 1 sec
- **Hauteur maximale :** bras à l'horizontale du torse

#### Compensations et Corrections

- **Momentum :** "Charge trop lourde. Le rear delt est un PETIT muscle — utilise des charges légères."
- **Transformation en row :** "Si tes coudes fléchissent trop, c'est un row. Fixe les coudes."
- **Shrug :** "Baisse les épaules."

---

### Exercice 49 : Upright Row

**Description :** Tirage vertical devant le corps. Exercice controversé pour la santé de l'épaule.

**Muscles principaux :** Deltoïde latéral, trapèze supérieur
**Muscles secondaires :** Deltoïde antérieur, biceps

#### Angles Optimaux

- **Prise :** LARGE (au-delà des épaules) — une prise étroite force l'impingement
- **Hauteur :** coudes jusqu'à hauteur d'épaule, PAS au-dessus
- **Coudes :** mènent le mouvement, restent au-dessus des poignets
- **Torse :** stable, pas de lean back

#### ⚠️ Avertissement

L'upright row avec prise étroite et coudes au-dessus des épaules est une des positions les plus risquées pour l'impingement sous-acromial. Si l'utilisateur le fait avec une prise étroite, recommander de passer à une prise large ou de remplacer par des élévations latérales.

#### Compensations et Corrections

1. **🔴 Prise étroite + coudes hauts :** "STOP. L'upright row avec une prise étroite et les coudes au-dessus des épaules compresse les tendons de ta coiffe des rotateurs. Élargis ta prise au-delà des épaules et ne monte pas les coudes au-dessus de tes épaules."
2. **🟡 Momentum :** même correction que les autres exercices d'épaule

---

### Exercice 50 : Shrugs

**Description :** Haussement d'épaules avec charge. Isole les trapèzes supérieurs.

**Muscles principaux :** Trapèze supérieur
**Muscles secondaires :** Levator scapulae, rhomboïdes

#### Angles Optimaux

- **Mouvement :** vertical PURE — les épaules montent DROIT vers les oreilles
- **PAS de rotation** — rouler les épaules n'ajoute rien et stresse l'articulation
- **Contraction :** 1-2 sec en haut
- **Bras :** tendus, ne fléchissent PAS
- **Descente :** contrôlée, laisser les trapèzes s'étirer

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Rotation des épaules (rolling) | Trajectoire épaule (11/12) | Mouvement circulaire vs vertical | 🟡 Modéré |
| Flexion des coudes (biceps curl partiel) | Angle coude | Flexion > 15° | 🟡 Modéré |
| ROM trop petit | Élévation épaule | < 3 cm de montée | 🟡 Modéré |
| Extension de genoux (leg drive) | Angle genou | Changement > 10° | 🟡 Modéré |

#### Corrections

1. **🟡 Rotation :** "Ne roule pas tes épaules — monte DROIT et descends DROIT. La rotation ne fait que stresser l'articulation sans bénéfice."
2. **🟡 Bras qui plient :** "Garde tes bras tendus comme des crochets. Ce sont tes trapèzes qui montent, pas tes biceps."

---

## 3.6 BRAS

---

### Exercice 51 : Curl Biceps Barre (EZ et Droite)

**Description :** Flexion de coude avec barre EZ ou droite. L'exercice de base pour les biceps.

**Muscles principaux :** Biceps brachial (long et court chef), brachial
**Muscles secondaires :** Brachio-radial, avant-bras (fléchisseurs)

#### Angles Optimaux

- **Position de départ :** bras tendus (175-180°), barre en supination
- **Flexion maximale :** ≤ 30° (barre monte jusqu'aux épaules)
- **Coudes :** FIXES le long du torse — ne reculent PAS et ne s'ouvrent PAS
- **Torse :** DROIT — pas de lean back
- **Barre EZ vs droite :** EZ réduit le stress sur les poignets en supination, recommandé si gêne

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Lean back (body english) | Angle torse | Inclinaison arrière > 10° | 🟡 Modéré |
| Coudes qui reculent | Coude (13/14) | Recul postérieur > 5 cm | 🟡 Modéré |
| Épaules qui montent (front raise déguisé) | Épaule (11/12) vs Coude (13/14) | Le humérus fléchit > 15° | 🟡 Modéré |
| Momentum (swing) | Oscillation hanche/torse | > 8 cm | 🟡 Modéré |
| ROM incomplet | Angle coude max/min | Ne tend pas complètement OU ne fléchit pas complètement | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Lean back/swing :** "Tu balances ton corps pour monter la barre. Tes biceps ne travaillent qu'à moitié. Colle ton dos à un mur ou fais-le assis pour te forcer à être strict."
2. **🟡 Coudes qui bougent :** "Tes coudes reculent pendant le curl — ça engage les deltoïdes antérieurs et réduit le travail des biceps. Fixe tes coudes le long de ton torse."
3. **🟡 ROM incomplet :** "Descends COMPLÈTEMENT en bas (bras quasi-tendus) et monte COMPLÈTEMENT en haut. Le ROM complet c'est le stimulus complet."

#### Exercices Correctifs

1. **Curl contre un mur (3x10)** — élimine le lean back physiquement
2. **Curl Pupitre (3x10)** — fixe les coudes et isole les biceps

---

### Exercice 52 : Curl Haltères (Alterné, Simultané)

**Description :** Curls avec haltères, permettant la supination active pendant le mouvement.

**Muscles principaux :** Biceps brachial
**Muscles secondaires :** Brachial, brachio-radial

#### Angles Optimaux

- Mêmes principes que le curl barre
- **Supination :** commencer en position neutre (marteau) et supiner (tourner la paume vers le haut) pendant la montée — active le biceps court chef
- **Alternance :** permet de se concentrer sur chaque bras
- **Simultané :** plus de stimulus global mais plus de tendance au cheat

#### Compensations et Corrections

Identiques au curl barre. L'avantage des haltères est de pouvoir identifier les asymétries entre les bras.

---

### Exercice 53 : Curl Marteau

**Description :** Curl en prise neutre (pouces vers le haut). Cible le brachial et le brachio-radial.

**Muscles principaux :** Brachial, brachio-radial
**Muscles secondaires :** Biceps brachial (chef long)

#### Angles Optimaux

- **Prise :** neutre (pouces vers le haut) du début à la fin
- **Coudes :** fixes le long du torse
- **Pas de rotation** du poignet pendant le mouvement
- Mêmes principes de strictness que les autres curls

#### Différence Biomécanique

Le brachial est sous le biceps et contribue à la largeur du bras. Le curl marteau est souvent négligé mais essentiel pour un développement complet.

---

### Exercice 54 : Curl Incliné

**Description :** Curl avec haltères sur un banc incliné à 45-60°. Pré-étire le chef long du biceps (car l'épaule est en extension).

**Muscles principaux :** Biceps brachial (emphase chef long)
**Muscles secondaires :** Brachial

#### Angles Optimaux

- **Inclinaison du banc :** 45-60°
- **Bras :** pendent derrière le torse en position de départ (extension de l'épaule = étirement du biceps)
- **Coudes :** fixes, ne bougent PAS vers l'avant
- **ROM :** de l'extension quasi-complète à la flexion complète
- **Charge :** PLUS LÉGÈRE que le curl debout (position étirée = plus vulnérable)

#### Compensations

- **Coudes qui avancent :** compensation la plus fréquente. "Tes coudes avancent — ils doivent rester pointés vers le sol."
- **Épaule qui se fléchit :** le humérus avance = le biceps triche en raccourcissant son bras de levier

---

### Exercice 55 : Curl Pupitre / Preacher Curl

**Description :** Curl avec les bras sur un pupitre incliné. Élimine tout momentum et isole les biceps parfaitement.

**Muscles principaux :** Biceps brachial (emphase chef court, car l'épaule est fléchie)
**Muscles secondaires :** Brachial

#### Angles Optimaux

- **Position sur le pupitre :** aisselles sur le bord supérieur, bras entièrement sur le pad
- **Extension :** ne PAS descendre en extension complète sous charge (stress massif sur le tendon du biceps distal) — stopper à 150-160° de flexion
- **Contraction haute :** complète, squeeze 1 sec
- **Tempo :** 2-1-3-0 (descente LENTE)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Coudes qui décollent du pupitre | Coude (13/14) | Élévation > 3 cm | 🟡 Modéré |
| Épaules qui avancent | Épaule (11/12) | Avancent > 5 cm | 🟡 Modéré |
| Extension complète rapide (drop) | Vitesse en extension | Chute rapide en fin de ROM | 🔴 Critique (risque tendon) |

#### Corrections Prioritaires

1. **🔴 Extension rapide :** "Ne laisse JAMAIS l'haltère tomber en extension. Descends lentement et ne tends pas complètement le bras — c'est la position la plus vulnérable pour ton tendon de biceps."
2. **🟡 Coudes qui décollent :** "Tes coudes décollent du pupitre. Plaque-les pendant tout le mouvement."

---

### Exercice 56 : Curl Concentré

**Description :** Curl assis, coude contre l'intérieur de la cuisse. Isolation maximale.

**Muscles principaux :** Biceps brachial
**Muscles secondaires :** Brachial

#### Angles Optimaux

- **Position :** assis, jambes écartées, coude contre l'intérieur de la cuisse
- **Le coude ne bouge PAS** — la cuisse sert de pupitre
- **ROM :** complète, de l'extension à la flexion maximale
- **Contraction :** squeeze en haut, supination maximale

#### Compensations

- Utilisation de la cuisse pour pousser le coude (triche)
- Rotation du torse pour aider
- Momentum

---

### Exercice 57 : Triceps Pushdown (Câble)

**Description :** Extension de coude au câble avec barre ou corde. L'exercice de base pour les triceps.

**Muscles principaux :** Triceps brachial (les 3 chefs, emphase chef latéral et médial)
**Muscles secondaires :** Anconé

#### Angles Optimaux

- **Position :** debout, légèrement incliné vers l'avant (5-10°)
- **Coudes :** fixes le long du torse, fléchis à 90° au départ
- **Extension :** complète (180°), contraction 1 sec
- **Poignets :** neutres, pas de flexion/extension
- **Avec corde :** écarter les extrémités en bas pour plus de contraction (pronation en fin de mouvement)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Coudes qui avancent/reculent | Coude (13/14) | Déplacement > 5 cm | 🟡 Modéré |
| Lean forward excessif (utilise le poids du corps) | Angle torse | > 25° | 🟡 Modéré |
| Épaules qui s'engagent (press vers le bas) | Épaule (11/12) | Dépression > 3 cm | 🟡 Modéré |
| ROM incomplet | Angle coude | Ne tend pas < 160° | 🟡 Modéré |

#### Corrections Prioritaires

1. **🟡 Coudes qui bougent :** "Fixe tes coudes le long de ton torse. Seuls tes avant-bras bougent. Si tes coudes avancent, tu transformes l'exercice en press."
2. **🟡 Lean forward :** "Tu te penches trop — tu utilises ton poids de corps pour pousser la charge. Tiens-toi droit et réduis le poids."

---

### Exercice 58 : Overhead Triceps Extension

**Description :** Extension de coude au-dessus de la tête (câble, haltère ou barre EZ). Pré-étire le chef long du triceps.

**Muscles principaux :** Triceps brachial (emphase chef long)
**Muscles secondaires :** Anconé

#### Angles Optimaux

- **Position de départ :** bras au-dessus de la tête, coudes fléchis, charge derrière la tête
- **Coudes :** fixes, pointés vers le plafond, NE S'OUVRENT PAS
- **Extension :** complète, bras tendus au-dessus de la tête
- **Torse :** droit, pas d'hyperextension lombaire

#### Compensations

- **Coudes qui s'ouvrent :** "Garde les coudes serrés, pointés vers le plafond."
- **Hyperextension lombaire :** "Contracte tes abdos — ton core lâche."
- **ROM incomplet :** "Descends la charge derrière ta tête pour un étirement complet du chef long."

---

### Exercice 59 : Skull Crusher

**Description :** Extension de coude allongé sur un banc, barre descend vers le front (d'où le nom). Excellent pour le chef long et médial.

**Muscles principaux :** Triceps brachial (les 3 chefs)
**Muscles secondaires :** Anconé, deltoïde antérieur (stabilisation)

#### Angles Optimaux

- **Position :** allongé sur un banc, bras verticaux (ou légèrement inclinés vers la tête)
- **Descente :** barre descend vers le front ou juste derrière la tête
- **Coudes :** FIXES, ne s'ouvrent PAS et ne reculent PAS
- **Extension :** complète, bras tendus
- **Angle des bras :** légèrement inclinés vers la tête (5-10° de la verticale) pour maintenir la tension sur les triceps en lockout

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Coudes qui s'ouvrent | Distance entre coudes | Écart > 1.5x largeur d'épaules | 🟡 Modéré |
| Coudes qui reculent (transforme en pullover) | Coude (13/14) vs Épaule (11/12) | Coude recule > 5 cm vers la tête | 🟡 Modéré |
| ROM incomplet | Angle coude | > 120° au point bas | 🟡 Modéré |

#### Corrections

1. **🟡 Coudes qui s'ouvrent :** "Serre les coudes — largeur d'épaules, pas plus."
2. **🟡 Coudes qui reculent :** "Si tes coudes dérivent vers ta tête, tu transformes le skull crusher en pullover. Fixe tes bras."

---

### Exercice 60 : Kickback Triceps

**Description :** Extension de coude penché en avant, bras parallèle au torse. Isole les triceps en position raccourcie.

**Muscles principaux :** Triceps brachial (contraction peak)
**Muscles secondaires :** Deltoïde postérieur (stabilisation)

#### Angles Optimaux

- **Torse :** parallèle au sol ou à 45°
- **Humérus :** parallèle au torse (fixe)
- **Extension :** complète, squeeze 1 sec au lockout
- **Charge :** légère — cet exercice est un exercice de contraction, pas de force

#### Compensations

- Humérus qui tombe (pas parallèle au torse)
- Rotation du torse pour aider
- ROM incomplet (ne tend pas complètement)
- Momentum

---

### Exercice 61 : Dips (Triceps)

**Description :** Dips avec torse VERTICAL. Contrairement aux dips pecs, on reste droit pour cibler les triceps.

**Muscles principaux :** Triceps, deltoïde antérieur
**Muscles secondaires :** Grand pectoral (moindre qu'en dips pecs)

#### Différence avec les Dips Pecs

- Torse VERTICAL (pas incliné)
- Coudes serrés le long du torse (pas écartés)
- ROM : descendre à 90° de coude, pas plus (protéger les épaules)
- Focus sur la poussée verticale

#### Compensations et Corrections

Mêmes que les dips pecs, avec l'accent sur la verticalité du torse et les coudes serrés.

---

### Exercice 62 : Close-Grip Bench Press

**Description :** Bench press avec prise étroite (index à largeur d'épaules ou plus étroite). Plus de triceps, moins de pectoraux.

**Muscles principaux :** Triceps, grand pectoral (faisceau sternal), deltoïde antérieur
**Muscles secondaires :** Biceps (stabilisation)

#### Angles Optimaux

- **Prise :** largeur d'épaules (index sur le bord lisse de la barre). PAS trop étroit (mains qui se touchent = stress poignets)
- **Coudes :** serrés le long du torse (30-45°)
- **Touch point :** plus bas que le bench classique (bas du sternum)
- **Trajectoire :** plus verticale que le bench classique

#### Compensations

Mêmes que le bench press classique. Attention supplémentaire :
- **Prise trop étroite** → stress sur les poignets et perte de force
- **Coudes qui s'ouvrent** → transforme en bench classique

---

## 3.7 CORE

---

### Exercice 63 : Planche / Plank

**Description :** Gainage en position push-up sur les avant-bras ou les mains. Anti-extension de la colonne.

**Muscles principaux :** Transverse de l'abdomen, rectus abdominis, obliques
**Muscles secondaires :** Érecteurs du rachis, grand fessier, quadriceps, deltoïde

#### Angles Optimaux

- **Corps :** en LIGNE DROITE de la tête aux talons
- **Pas de hanche haute (pike)** et pas de hanche basse (sway)
- **Coudes :** sous les épaules
- **Regard :** vers le sol (cou neutre)
- **Fessiers :** contractés
- **Abdominaux :** contractés (aspiration du nombril + brace)

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Hanche qui s'affaisse | Épaule → Hanche → Cheville | Hanche > 5 cm sous la ligne | 🔴 Critique (stress lombaire) |
| Hanche trop haute | Même ligne | Hanche > 5 cm au-dessus | 🟡 Modéré |
| Tête qui tombe | Position oreille vs épaule | Tête trop basse | 🟢 Mineur |
| Épaules qui s'affaissent | Scapulae | Omoplates saillantes | 🟡 Modéré |

#### Corrections

1. **🔴 Hanche basse :** "Ton bassin s'affaisse — contracte tes abdos et tes fessiers. Imagine que quelqu'un va te donner un coup dans le ventre."
2. **🟡 Hanche haute :** "Tu fais une montagne au lieu d'une planche. Aligne tes hanches avec tes épaules et tes chevilles."

---

### Exercice 64 : Dead Bug

**Description :** Allongé sur le dos, bras et jambes en l'air, on étend un bras et la jambe opposée alternativement. Anti-extension par excellence.

**Muscles principaux :** Transverse, rectus abdominis, obliques
**Muscles secondaires :** Fléchisseurs de hanche, deltoïdes

#### Angles Optimaux

- **Dos :** PLAQUÉ au sol — le bas du dos ne doit JAMAIS décoller
- **Position de départ :** bras tendus vers le plafond, genoux à 90°, cuisses verticales
- **Mouvement :** bras opposé et jambe descendent vers le sol SANS toucher
- **Respiration :** expirer pendant l'extension, inspirer au retour

#### Compensations

- **Bas du dos qui décolle** : la SEULE compensation qui compte. Si le dos décolle, réduire l'amplitude ou plier les genoux davantage.

---

### Exercice 65 : Ab Wheel Rollout

**Description :** Anti-extension avec la roue abdominale. Exercice avancé de core.

**Muscles principaux :** Rectus abdominis, transverse, obliques
**Muscles secondaires :** Grand dorsal, deltoïde, triceps, érecteurs du rachis

#### Angles Optimaux

- **Départ :** à genoux, bras tendus, roue sous les épaules
- **Extension :** pousser la roue vers l'avant en gardant le corps RIGIDE
- **Point le plus loin :** bras au-dessus de la tête, corps quasi-parallèle au sol (pour les avancés)
- **Pas d'hyperextension lombaire** — JAMAIS
- **Retour :** contraction abdominale pour ramener la roue, PAS de flexion de hanche

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Hyperextension lombaire | Épaule, Hanche | Hanche descend plus bas que la ligne épaule-genou | 🔴 Critique |
| Flexion de hanche au retour (pike) | Angle hanche | Diminue brusquement au retour | 🟡 Modéré |
| ROM trop court | Extension maximale | Bras ne vont pas au-delà des épaules | 🟡 Modéré |

#### Corrections

1. **🔴 Hyperextension :** "Ton dos se cambre — tes abdos n'arrivent pas à tenir. Réduis l'amplitude et renforce ta planche d'abord."
2. **🟡 Pike :** "Tu ramènes en cassant à la hanche. Le retour doit se faire en contractant les abdos, pas en pliant le torse."

---

### Exercice 66 : Crunch Câble (Cable Crunch)

**Description :** Crunch à genoux face à un câble haut. Permet de charger le mouvement de flexion de tronc.

**Muscles principaux :** Rectus abdominis
**Muscles secondaires :** Obliques

#### Angles Optimaux

- **Position :** à genoux, corde derrière la tête, coudes fléchis
- **Mouvement :** flexion de tronc (arrondir le dos intentionnellement), coudes vers les genoux
- **Hanches :** FIXES — ne fléchissent PAS (sinon ce sont les fléchisseurs de hanche qui travaillent)
- **Retour :** contrôlé, laisser les abdos s'étirer

#### Compensations

- **Flexion de hanche (assis vers les talons)** : "Tu fléchis les hanches au lieu du tronc. Ton bassin reste fixe — seul ton torse bouge."
- **Tirage avec les bras** : "La corde reste fixe derrière ta tête. Tes bras ne tirent pas — tes abdos oui."

---

### Exercice 67 : Hanging Leg Raise

**Description :** Élevation des jambes suspendu à une barre. Travaille la flexion du tronc par le bas.

**Muscles principaux :** Rectus abdominis (portion inférieure), fléchisseurs de hanche
**Muscles secondaires :** Obliques, grip, grand dorsal (stabilisation)

#### Angles Optimaux

- **Suspension :** bras tendus, épaules actives (pas de dead hang passif)
- **Mouvement :** lever les jambes en roulant le bassin vers le haut (posterior pelvic tilt)
- **Point haut :** pieds au niveau de la barre (ou au-dessus pour les avancés)
- **Le SECRET :** le pelvic tilt. Sans basculement du bassin, ce sont les fléchisseurs de hanche qui travaillent, pas les abdos

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Balancement (kipping) | Oscillation épaules/hanches | > 15 cm | 🟡 Modéré |
| Pas de pelvic tilt | Angle du bassin | Le bassin ne bascule pas vers l'arrière | 🟡 Modéré |
| Genoux fléchis (knee raise au lieu de leg raise) | Angle genou | < 150° | 🟢 Mineur (acceptable comme régression) |
| ROM incomplet | Hauteur des pieds | Ne dépasse pas l'horizontale | 🟡 Modéré |

#### Corrections

1. **🟡 Pas de pelvic tilt :** "Tes jambes montent mais ton bassin ne bascule pas. Pense à amener ton pubis vers ton nombril. C'est cette bascule qui engage les abdos au lieu des fléchisseurs de hanche."
2. **🟡 Kipping :** "Pas de balancement. Descends contrôlé, remonte contrôlé. Si tu dois balancer, les hanging knee raises sont une meilleure option pour l'instant."

---

### Exercice 68 : Pallof Press

**Description :** Press anti-rotation avec câble ou bande. L'exercice fonctionnel de core par excellence.

**Muscles principaux :** Obliques, transverse de l'abdomen
**Muscles secondaires :** Rectus abdominis, grand fessier (stabilisation)

#### Angles Optimaux

- **Position :** debout de profil au câble, pieds largeur d'épaules
- **Mains :** au centre de la poitrine en position de départ
- **Press :** pousser les mains devant soi en résistant à la rotation
- **Le torse NE TOURNE PAS** — c'est tout le but de l'exercice
- **Bras tendus :** hold 2-3 sec, puis ramener
- **Hanches et épaules :** restent FACE DEVANT

#### Compensations

- **Rotation du torse vers le câble** : "Tu tournes — résiste ! C'est la résistance à la rotation qui travaille tes obliques profonds."
- **Lean away (se pencher loin du câble)** : "Tu te penches pour compenser. Reste droit et augmente la contraction abdominale."

---

## 3.8 MOLLETS

---

### Exercice 69 : Calf Raise Debout

**Description :** Élévation des mollets debout. Cible le gastrocnémien (muscle superficiel du mollet) car le genou est tendu.

**Muscles principaux :** Gastrocnémien (médial et latéral)
**Muscles secondaires :** Soléaire

#### Angles Optimaux

- **Genoux :** tendus (légère micro-flexion)
- **Montée :** sur les orteils, le plus haut possible (plantarflexion maximale)
- **Descente :** sous le niveau de la marche/plateforme (dorsiflexion pour étirement complet)
- **Tempo :** 2-1-3-0 (montée 2sec, squeeze 1sec, descente 3sec)
- **Poids :** réparti sur les orteils, PAS sur le petit orteil uniquement

#### Compensations Détectables via MediaPipe

| Compensation | Landmarks | Critère | Sévérité |
|---|---|---|---|
| Genoux qui fléchissent | Angle genou | Flexion > 15° | 🟡 Modéré |
| ROM incomplet (pas de stretch en bas) | Angle cheville | Ne descend pas sous 90° | 🟡 Modéré |
| Rebond en bas (pas de contrôle) | Vitesse au changement de direction | Changement brutal | 🟡 Modéré |
| Pronation/supination excessive du pied | Angle de la cheville en vue postérieure | Déviation > 10° | 🟡 Modéré |

#### Corrections

1. **🟡 Rebond :** "Tu rebondes en bas — tes tendons font le travail au lieu de tes mollets. Pause 1 sec en bas, puis monte de manière contrôlée."
2. **🟡 ROM :** "Monte le plus haut possible et descends le plus bas possible. Les mollets ont besoin de ROM complet pour se développer."

---

### Exercice 70 : Calf Raise Assis

**Description :** Élévation des mollets assis, genoux fléchis à 90°. Cible le soléaire (muscle profond) car le gastrocnémien est raccourci.

**Muscles principaux :** Soléaire
**Muscles secondaires :** Gastrocnémien (contribution réduite car raccourci)

#### Angles Optimaux

- **Genoux :** fléchis à 90° (assis)
- **ROM :** complet — même principes que debout
- **Pad :** sur les genoux, pas sur les cuisses
- **Tempo :** 2-2-3-0 (encore plus de contrôle que debout)

#### Différence avec le Calf Raise Debout

Le soléaire est composé majoritairement de fibres de type I (endurance) → il répond mieux aux séries longues (15-25 reps) et aux tempos lents.

---

# SECTION 4 — SCORING DÉTAILLÉ /100

## 4.1 Principes de Notation

Le score /100 évalue la QUALITÉ D'EXÉCUTION d'une répétition ou série donnée. Ce n'est PAS un score de performance (charge, nombre de reps).

### Score de Base

Chaque rep part à **100 points**. Les pénalités sont soustraites selon les compensations détectées.

### Barème Descriptif

| Score | Niveau | Description |
|-------|--------|-------------|
| 90-100 | 🏆 Excellent | Forme quasi-parfaite. Détails mineurs d'optimisation uniquement. |
| 75-89 | ✅ Bon | Bonne exécution avec quelques améliorations possibles. Pas de risque de blessure. |
| 60-74 | 🟡 Correct | Exécution acceptable mais des corrections importantes amélioreront la sécurité et l'efficacité. |
| 40-59 | 🟠 À améliorer | Plusieurs compensations significatives. Risque modéré de blessure. Réduire la charge recommandé. |
| 20-39 | 🔴 Insuffisant | Compensations majeures. Risque élevé de blessure. Réduire la charge et travailler la technique en priorité. |
| 0-19 | ⛔ Dangereux | Forme dangereuse. Arrêter immédiatement et revoir les fondamentaux avec un coach. |

## 4.2 Grille de Pénalités Universelles

Ces pénalités s'appliquent à tous les exercices sauf indication contraire.

### Pénalités de Sécurité (🔴)

| Compensation | Pénalité | Exercices principalement concernés |
|---|---|---|
| Flexion lombaire sous charge | -20 pts | Deadlift, squat, row, good morning |
| Hyperextension lombaire | -15 pts | Hip thrust, OHP, curl, calf raise |
| Valgus dynamique bilatéral | -15 pts | Squat, leg press, lunges, leg curl |
| Valgus dynamique unilatéral | -10 pts | BSS, step-up, walking lunges |
| Coudes à 90° en press horizontal | -15 pts | Bench press, push-ups |
| Descente trop profonde (dips, fly) | -15 pts | Dips, dumbbell fly |
| Verrouillage genou leg press | -20 pts | Leg press uniquement |
| Barre derrière la nuque (pulldown) | -20 pts | Lat pulldown |
| Upright row prise étroite + coudes hauts | -15 pts | Upright row |
| Chute non contrôlée (Nordic curl) | -15 pts | Nordic curl |
| Talons qui décollent (squat) | -10 pts | Squat, hack squat |

### Pénalités d'Efficacité (🟡)

| Compensation | Pénalité | Exercices principalement concernés |
|---|---|---|
| ROM incomplet (< 80% du ROM optimal) | -10 pts | Tous |
| ROM très incomplet (< 50%) | -20 pts | Tous |
| Utilisation de momentum | -10 pts | Curls, élévations latérales, rows |
| Momentum excessif (body english majeur) | -15 pts | Curls, élévations latérales |
| Perte de rétraction scapulaire | -10 pts | Bench press, rows |
| Coudes qui bougent (isolation) | -8 pts | Curls, extensions triceps |
| Excentrique trop rapide (< 1 sec) | -8 pts | Tous les exercices composés |
| Butt wink modéré | -8 pts | Squat |
| Good morning squat | -10 pts | Squat |
| Hanches qui montent trop vite (sumo DL) | -12 pts | Sumo deadlift |
| Torse qui s'effondre (front squat) | -12 pts | Front squat |
| Coudes qui tombent (front squat) | -12 pts | Front squat |
| Lean back excessif | -8 pts | OHP, rows, curls |
| Barre qui s'éloigne du corps | -10 pts | Deadlift, RDL |
| Perte de neutralité cervicale | -5 pts | Tous |
| Fessiers décollent du siège/banc | -8 pts | Leg extension, leg curl, bench |
| Asymétrie de mouvement | -8 pts | Tous les bilatéraux |
| Rotation du torse (exercice unilatéral) | -8 pts | DB row, split squat |

### Pénalités d'Optimisation (🟢)

| Compensation | Pénalité | Exercices |
|---|---|---|
| Pas de squeeze/contraction peak | -3 pts | Tous les exercices d'isolation |
| Tempo inconsistant | -3 pts | Tous |
| Position des pieds sous-optimale | -3 pts | Squat, leg press, hip thrust |
| Prise sous-optimale | -3 pts | Tous les exercices avec barre |
| Tête en avant (non dangereux) | -2 pts | Push-ups, plank |

## 4.3 Pondération par Exercice

Certains critères sont PLUS importants pour certains exercices. Le scoring ajuste la pondération :

### Exercices où la Sécurité Lombaire est Prioritaire

Deadlift conventionnel, Sumo DL, Good Morning, RDL, SLDL, Barbell Row
→ Les pénalités lombaires sont **x1.5** (ex: flexion lombaire = -30 pts au lieu de -20)

### Exercices où la Sécurité de l'Épaule est Prioritaire

Bench Press, Incline Bench, Dips, OHP, Behind-Neck Press, Upright Row
→ Les pénalités épaule sont **x1.5**

### Exercices où le ROM est Crucial

Pull-up, Squat (profondeur), Push-up (toucher la poitrine), Curl (extension complète)
→ Les pénalités ROM sont **x1.5**

## 4.4 Calcul du Score Final

1. Partir de 100
2. Identifier toutes les compensations détectées
3. Appliquer les pénalités correspondantes
4. Appliquer les multiplicateurs de pondération si applicable
5. Le score ne descend pas en dessous de 0
6. Arrondir au point le plus proche

**Exemple :**
Squat avec valgus dynamique bilatéral (-15) + butt wink modéré (-8) + excentrique rapide (-8) + pas de pénalité de pondération supplémentaire
Score = 100 - 15 - 8 - 8 = **69/100** → 🟡 Correct

---

# SECTION 5 — DÉTECTION D'EXERCICE VIA MEDIAPIPE

## 5.1 Principes de Détection

La détection de l'exercice se base sur les **patterns de mouvement** observés via les 33 landmarks de MediaPipe Pose. Les critères principaux sont :

1. **Position du corps** (debout, assis, allongé, suspendu, incliné)
2. **Articulations avec le plus grand ROM** (quelle articulation bouge le plus)
3. **Plan de mouvement** (sagittal, frontal, transversal)
4. **Bilatéral vs unilatéral**
5. **Présence d'équipement détectable** (barre, haltères, câble — limité par la vidéo)

## 5.2 Landmarks MediaPipe de Référence

```
0: Nez
1-6: Yeux et oreilles
7/8: Oreilles
9/10: Bouche
11/12: Épaules (gauche/droite)
13/14: Coudes
15/16: Poignets
17-22: Mains (index, petit doigt, pouce)
23/24: Hanches
25/26: Genoux
27/28: Chevilles
29/30: Talons
31/32: Orteils
```

## 5.3 Patterns de Détection par Exercice

### Debout — Mouvement Bilatéral Vertical

**Squat (High Bar, Low Bar, Front, Goblet) :**
- Position : debout
- ROM principal : flexion-extension de hanche (23/24) et genou (25/26) simultanées
- Le torse descend verticalement (épaules 11/12 descendent)
- Les pieds (27-32) restent fixes au sol
- **Différenciateur High vs Low Bar :** angle du torse (low bar = plus incliné)
- **Différenciateur Front Squat :** torse quasi-vertical, coudes hauts (13/14 au niveau ou au-dessus des épaules 11/12)
- **Différenciateur Goblet Squat :** poignets (15/16) devant la poitrine, proches de épaules (11/12)

**Overhead Press :**
- Position : debout
- ROM principal : extension du coude (13/14) et flexion de l'épaule (11/12) — les bras montent verticalement
- Les pieds restent fixes
- Les hanches et genoux NE BOUGENT PAS (vs push press)
- **Différenciateur vs Push Press :** flexion-extension visible des genoux = push press

**Deadlift Conventionnel :**
- Position : debout
- ROM principal : extension de hanche (23/24) — les épaules (11/12) montent tandis que les genoux (25/26) s'étendent
- Les poignets (15/16) restent bas (au niveau des genoux ou en dessous au départ)
- Le torse passe de très incliné (45-90°) à vertical
- **Différenciateur vs Squat :** les poignets sont bas (pas de barre sur le dos), le mouvement est un hip hinge (les hanches reculent, le torse s'incline)

**Sumo Deadlift :**
- Mêmes critères que le conventionnel mais stance très large (distance entre chevilles 27/28 > 1.5x distance entre épaules 11/12)
- Torse plus vertical que le conventionnel

**RDL / SLDL :**
- Position : debout
- ROM principal : flexion-extension de hanche SANS changement significatif de l'angle de genou
- Genoux restent quasi-fixes (< 10° de variation)
- Les poignets (15/16) descendent le long des jambes
- **Différenciateur RDL vs SLDL :** angle de genou (RDL = 15-25° de flexion, SLDL = 5-10°)
- **Différenciateur vs Deadlift :** pas de départ du sol, genoux quasi-fixes

**Good Morning :**
- Comme le RDL mais les poignets (15/16) sont au niveau des épaules (11/12) = barre sur le dos
- Hip hinge avec les mains en haut au lieu d'en bas

**Shrugs :**
- Position : debout
- ROM principal : TRÈS PETIT — seul mouvement d'élévation des épaules (11/12)
- Genoux, hanches, coudes ne bougent PAS
- Poignets (15/16) restent le long du corps

**Curl Barre / Haltères debout :**
- Position : debout
- ROM principal : flexion du coude (13/14) — seuls les avant-bras bougent
- Épaules (11/12) et hanches (23/24) restent fixes
- Poignets (15/16) montent de la cuisse aux épaules

**Élévations Latérales :**
- Position : debout
- ROM principal : abduction de l'épaule — les poignets (15/16) s'écartent latéralement
- Coudes quasi-fixes
- Le mouvement est dans le plan FRONTAL (côtés), pas sagittal (avant)
- **Différenciateur vs Élévations Frontales :** les poignets montent DEVANT au lieu de sur les CÔTÉS

### Debout — Mouvement Unilatéral

**Bulgarian Split Squat :**
- Un pied surélevé derrière (pied arrière plus haut que le pied avant)
- Flexion-extension d'une seule jambe
- Asymétrie marquée entre les deux côtés

**Walking Lunges / Fentes Arrière :**
- Alternance de position des pieds
- Un genou descend vers le sol puis remonte
- Position décalée avant-arrière des pieds

**Step-Up :**
- Un pied sur une surface surélevée
- Le corps monte verticalement
- Alternance unilatérale

### Assis / Allongé

**Bench Press :**
- Position : allongé sur le dos (horizontal)
- ROM principal : flexion-extension du coude (13/14) et de l'épaule — les poignets (15/16) montent et descendent verticalement
- Le dos reste sur le banc (hanches 23/24 fixes)
- **Différenciateur vs Push-up :** corps allongé et immobile vs corps en planche qui monte/descend
- **Différenciateur Incline vs Flat vs Decline :** angle du torse par rapport à l'horizontale

**Dumbbell Fly :**
- Position : allongé
- ROM principal : adduction-abduction de l'épaule dans le plan frontal
- Les coudes restent quasi-fixes (contrairement au bench press)
- Les poignets s'écartent et convergent

**Skull Crusher :**
- Position : allongé
- ROM principal : flexion-extension du COUDE uniquement
- Les épaules (11/12) restent fixes
- Les poignets (15/16) descendent vers le front/tête

**Hip Thrust :**
- Position : dos sur un banc, pieds au sol
- ROM principal : extension de hanche — les hanches (23/24) montent et descendent
- Les épaules (11/12) sont fixes (sur le banc)
- Les genoux (25/26) sont fléchis à ≈ 90°
- **Différenciateur vs Glute Bridge :** présence d'un banc / épaules surélevées

**Leg Extension :**
- Position : assis
- ROM principal : extension du genou — les chevilles (27/28) montent
- Les hanches et épaules ne bougent PAS
- Mouvement UNIARTICULAIRE du genou uniquement

**Leg Curl Assis / Allongé :**
- Position : assis ou allongé face contre le banc
- ROM principal : flexion du genou
- **Différenciateur Assis vs Allongé :** position du torse (vertical vs horizontal)

### Suspendu

**Pull-up / Chin-up :**
- Position : suspendu, bras au-dessus de la tête
- ROM principal : le corps monte verticalement, tiré par les bras
- Les épaules (11/12) montent vers les poignets (15/16 fixes en haut)
- **Différenciateur Pull-up vs Chin-up :** rotation des poignets (pronation vs supination) — difficile à détecter via MediaPipe, mais la largeur de prise donne un indice (chin-up = prise plus étroite)

**Hanging Leg Raise :**
- Position : suspendu
- ROM principal : les hanches et genoux montent — les pieds montent vers les mains
- Le torse reste relativement fixe (contrairement au pull-up où c'est le torse qui monte)

### Sur Machine / Câble

**Lat Pulldown :**
- Position : assis
- Comme un pull-up inversé — les poignets (15/16) descendent vers les épaules (11/12)
- Le torse est quasi-vertical (légèrement incliné)

**Seated Cable Row :**
- Position : assis
- ROM principal : les coudes (13/14) reculent, les poignets (15/16) viennent vers le torse
- Mouvement dans le plan sagittal (avant-arrière)
- **Différenciateur vs Pulldown :** direction du tirage (horizontal vs vertical)

**Cable Crossover :**
- Position : debout
- Les bras convergent devant le torse
- Mouvement d'adduction horizontale de l'épaule
- **Différenciateur vs Fly :** debout au lieu d'allongé

**Triceps Pushdown :**
- Position : debout
- ROM principal : extension du coude uniquement
- Les coudes (13/14) sont fixes le long du torse
- Les poignets (15/16) descendent

**Face Pull :**
- Position : debout
- Les poignets (15/16) viennent vers les oreilles/tempes (7/8)
- Coudes à hauteur d'épaule ou au-dessus
- **Différenciateur vs Row :** hauteur du tirage (face pull = haut, row = milieu/bas)

### Au Sol

**Push-up :**
- Position : en planche face au sol
- Le corps monte et descend en BLOC
- Les mains (15/16) sont fixes au sol
- **Différenciateur vs Bench Press :** le corps bouge, pas les mains. En bench, les mains bougent, pas le corps.

**Plank :**
- Position : en planche
- AUCUN mouvement — position statique
- **Différenciateur vs Push-up :** absence de mouvement

**Dead Bug :**
- Position : allongé sur le dos
- Bras et jambes en l'air bougent de manière alternée
- Le torse reste fixe au sol

**Ab Wheel Rollout :**
- Position : à genoux
- Les poignets (15/16) s'éloignent vers l'avant tandis que le corps s'aplatit
- Mouvement d'extension avec les bras qui avancent

**Nordic Curl :**
- Position : à genoux
- Le torse s'incline vers l'avant (comme tomber en avant)
- Les genoux sont fixes (point de pivot)
- Pas d'utilisation des mains/poignets pour tirer

## 5.4 Algorithme de Détection Simplifié

```
1. Déterminer la POSITION DU CORPS :
   - Épaules au-dessus des hanches, hanches au-dessus des genoux → DEBOUT
   - Épaules horizontales, hanches au même niveau → ALLONGÉ
   - Épaules au-dessus des hanches, genoux fléchis à 90° → ASSIS
   - Poignets au-dessus des épaules, corps en dessous → SUSPENDU
   - Corps face au sol, en planche → AU SOL (push-up/plank)
   - À genoux → AU SOL (nordic, ab wheel, cable crunch)

2. Identifier l'ARTICULATION AVEC LE PLUS GRAND ROM :
   - Hanche = squat / deadlift / hip thrust / RDL / good morning
   - Genou (sans hanche) = leg extension / leg curl
   - Coude + épaule vers le haut = OHP / press
   - Coude + épaule vers le bas = pull-up / pulldown
   - Coude seul (vertical) = curl / pushdown / skull crusher
   - Épaule seule (latéral) = élévation latérale / fly
   - Épaule seule (horizontal, tirage) = row / face pull
   - Aucun mouvement = plank / hold isométrique

3. Affiner avec les CRITÈRES DIFFÉRENCIANTS listés dans chaque exercice
```

## 5.5 Matrice de Confusion — Exercices Similaires

### Paires d'exercices facilement confondues et comment les différencier

| Exercice A | Exercice B | Critère Différenciant |
|---|---|---|
| Back Squat | Front Squat | Position des coudes (13/14) — hauts en front squat, bas en back squat |
| Back Squat | Goblet Squat | Position des poignets (15/16) — devant le torse en goblet |
| High Bar Squat | Low Bar Squat | Angle du torse (low bar = plus incliné de 10-15°) |
| Deadlift Conv. | Sumo DL | Largeur de stance (chevilles 27/28) |
| Deadlift | RDL | Genoux : DL = s'étendent, RDL = restent fixes |
| RDL | SLDL | Angle de genou (RDL = plus fléchi) |
| RDL | Good Morning | Position des poignets (bas en RDL, au niveau des épaules en GM) |
| Bench Press | Push-up | Orientation (allongé vs face au sol) + ce qui bouge (mains vs corps) |
| Bench Press | Dumbbell Press | Trajectoire des poignets (convergente en DB, parallèle en barre) |
| Bench Press | Dumbbell Fly | Mouvement des coudes (fléchissent en press, restent fixes en fly) |
| Pull-up | Chin-up | Largeur de prise (chin-up plus étroite) |
| Pull-up | Lat Pulldown | Position du corps (suspendu vs assis) |
| Barbell Row | Seated Cable Row | Position (debout penché vs assis) |
| Seated Cable Row | Face Pull | Hauteur du tirage (nombril vs visage) |
| Leg Extension | Leg Curl Assis | Direction du mouvement (extension vs flexion du genou) |
| Hip Thrust | Glute Bridge | Épaules surélevées (hip thrust) vs au sol (glute bridge) |
| Dips Pecs | Dips Triceps | Angle du torse (incliné en pecs, vertical en triceps) |
| Curl Barre | Curl Marteau | Orientation des poignets (supination vs neutre) |
| OHP | Push Press | Mouvement des genoux (fixes en OHP, fléchissent en push press) |
| Walking Lunges | Fentes Arrière | Direction du pas (avant en lunges, arrière en fentes arrière) |
| Skull Crusher | Overhead Extension | Position du corps (allongé vs assis/debout) |
| Plank | Push-up (en haut) | Mouvement vs statique |

---

## ANNEXE — Landmarks MediaPipe Quick Reference

```
VISAGE : 0 (nez), 1-6 (yeux), 7/8 (oreilles), 9/10 (bouche)
BRAS GAUCHE : 11 (épaule), 13 (coude), 15 (poignet), 17 (index), 19 (petit doigt), 21 (pouce)
BRAS DROIT : 12 (épaule), 14 (coude), 16 (poignet), 18 (index), 20 (petit doigt), 22 (pouce)
JAMBE GAUCHE : 23 (hanche), 25 (genou), 27 (cheville), 29 (talon), 31 (orteil)
JAMBE DROITE : 24 (hanche), 26 (genou), 28 (cheville), 30 (talon), 32 (orteil)
```

### Angles Clés à Calculer

1. **Angle de genou :** Hanche → Genou → Cheville (flexion)
2. **Angle de hanche :** Épaule → Hanche → Genou (flexion de hanche)
3. **Angle de coude :** Épaule → Coude → Poignet (flexion de coude)
4. **Angle d'épaule (abduction) :** Hanche → Épaule → Coude (élévation du bras)
5. **Angle du torse :** Épaule → Hanche → Verticale (inclinaison du torse)
6. **Angle de cheville :** Genou → Cheville → Orteil (dorsiflexion)
7. **Angle cervical :** Oreille → Épaule → Hanche (position de la tête)
8. **Valgus/Varus :** Hanche → Genou → Cheville (vue frontale)

---

*FORMCHECK by ACHZOD — © 2026 — Tous droits réservés*
*Ce document est la propriété intellectuelle d'ACHZOD. Reproduction interdite sans autorisation.*