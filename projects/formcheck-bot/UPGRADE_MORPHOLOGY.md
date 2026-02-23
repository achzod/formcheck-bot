# UPGRADE CRITIQUE — Adaptation Morphologique (APPROCHE PHOTOS STATIQUES)

## NOUVELLE ARCHITECTURE : PROFIL MORPHOLOGIQUE PAR PHOTOS

### Concept
Au lieu d'estimer la morphologie à partir des vidéos d'exercice (imprécis, un seul angle, corps en mouvement), on demande au client 3 PHOTOS STATIQUES à l'inscription :
- **Face** : debout, bras le long du corps → largeur clavicules, hanches, proportions bras, symétrie G/D
- **Profil (côté)** : debout → ratios fémur/tibia/torse, posture (lordose, cyphose, antéversion bassin, tête en avant)
- **Dos** : debout → position omoplates, asymétries, posture scapulaire

MediaPipe sur un corps IMMOBILE = précision 10x supérieure.
Le profil est stocké en DB et réutilisé pour TOUTES les analyses vidéo futures.

### Nouveau module à créer : `src/analysis/morpho_profiler.py`
- Analyse les 3 photos statiques
- Extrait tous les ratios anthropométriques avec haute précision
- Génère un bilan postural (lordose, cyphose, épaules enroulées, antéversion bassin)
- Stocke le profil en DB (table `morpho_profiles`)
- Retourne un résumé textuel + données JSON pour le client

### Nouveau flow WhatsApp (src/app/messages.py + handlers.py)
1. Premier contact → welcome + demande de 3 photos pour profil morpho
2. Instructions PRÉCISES pour les 3 photos (vêtements ajustés, fond neutre, lumière, distance)
3. Client envoie photos → analyse morpho → profil créé
4. Bot envoie bilan postural + profil morpho au client (valeur perçue = hook d'acquisition)
5. Client envoie vidéos d'exercice → analyses personnalisées à SA morphologie

### Adaptation des seuils (angle_calculator.py)
- Les seuils d'angles ne sont plus fixes mais FONCTIONS du profil morpho
- Ex: trunk_lean_threshold au squat = f(femur_tibia_ratio, torso_femur_ratio)
- Ex: ROM_bench = adapté à arm_length + shoulder_width
- Le score reflète la qualité RELATIVE à la morphologie du client

### Base de données (database.py)
- Nouvelle table `morpho_profiles` : user_id, shoulder_width, hip_width, femur_length, tibia_length, torso_length, upper_arm_length, forearm_length, femur_tibia_ratio, torso_femur_ratio, arm_torso_ratio, posture_notes, squat_type, created_at
- Le pipeline charge le profil morpho avant chaque analyse vidéo

### Section "Profil Morphologique" dans le rapport HTML
- Silhouette avec proportions annotées
- Explication de comment la morpho impacte l'exercice analysé
- Recommandations personnalisées (stance, prise, variantes)

---

## CE QUI EXISTE DÉJÀ (biomechanics_levers.py)
- Mesure fémur, tibia, torse, bras, avant-bras (normalisé à la taille)
- Ratios : fémur/tibia, torse/fémur, bras/torse
- Détection fémur long → squat hip-dominant
- Détection torse long → squat quad-dominant
- Note morphologique dans le rapport

## CE QUI MANQUE — À AJOUTER

### 1. Largeur de clavicules (shoulder_width)
- Calculer la distance épaule gauche ↔ épaule droite normalisée
- Impact : bench press (prise optimale, levier pec), développé militaire, dips
- Si clavicules larges → prise plus large conseillée, plus de stretch pec en bas
- Si clavicules étroites → prise moyenne, focus serrage omoplates

### 2. Ratio bras/avant-bras (upper_arm / forearm ratio)
- Impact curl : avant-bras long = plus de levier = curl plus dur
- Impact triceps : bras long = plus de ROM au skull crusher
- Biceps court vs long : estimable par l'angle de flexion max du coude sous charge
- Recommandations de variantes d'exercices selon le ratio

### 3. Largeur de hanches (hip_width)
- Distance hanche gauche ↔ hanche droite normalisée
- Impact : stance de squat optimale (hanches larges = stance plus large naturellement)
- Sumo deadlift vs conventionnel (hanches larges = avantage sumo)
- Valgus dynamique plus fréquent si hanches larges + fémurs longs

### 4. Longueur des bras vs torse pour le deadlift/bench
- Bras longs = avantage deadlift (moins de ROM), désavantage bench (plus de ROM)
- Adapter les seuils d'angle et les attentes en conséquence
- Ne PAS pénaliser un gars avec des bras longs pour un ROM plus grand au bench

### 5. ADAPTATION DES SEUILS PAR MORPHOLOGIE (CRITIQUE)
- Un fémur long = inclinaison tronc NORMALE au squat → ne pas pénaliser le score
- Un torse court = forward lean naturel au squat → adapter le seuil "trunk_lean"
- Des bras longs = ROM plus grand au bench → ajuster le seuil de "depth" 
- Intégrer les ratios anthropométriques dans le calcul du score final
- Le score doit refléter la QUALITÉ relative à la morphologie, pas un standard absolu

### 6. Recommandations de stance/prise personnalisées
- Squat : stance width basée sur largeur hanches + longueur fémur
- Deadlift : sumo vs conventional basé sur fémur/torse ratio + largeur hanches
- Bench : prise basée sur largeur épaules + longueur bras
- OHP : prise basée sur largeur épaules

### 7. Section "Profil Morphologique" dans le rapport
- Ajouter une section dédiée dans le rapport HTML et le rapport texte
- Résumé visuel des proportions du client
- Explication de comment sa morphologie impacte l'exercice analysé
- Conseils personnalisés (pas génériques)

## FICHIERS À MODIFIER
- `src/analysis/biomechanics_levers.py` — ajouter les nouvelles métriques
- `src/analysis/report_generator.py` — inclure les données morpho dans le prompt LLM
- `src/analysis/html_report.py` — section visuelle "Profil Morphologique"
- `src/analysis/pipeline.py` — s'assurer que les nouvelles données sont passées au rapport
- `src/analysis/angle_calculator.py` — adapter les seuils en fonction de la morpho
