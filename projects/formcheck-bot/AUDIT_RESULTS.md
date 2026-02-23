# AUDIT FORMCHECK — 24 février 2026

## Issues trouvées et corrigées

### 1. morpho_profiler.py
- [BUG] Side photo: arm_torso_ratio calcul utilise `total_arm` qui peut être 0 si la photo de face n'a pas été analysée avant la photo de profil → division/résultat incorrect
- [BUG] Back photo: modifie `posture.summary` qui peut ne pas exister si la photo de profil n'est pas fournie
- [IMPROVE] Pas de gestion de photos incomplètes (1 ou 2 photos au lieu de 3)
- [IMPROVE] _estimate_height utilise nose→ankle, mais si le sujet porte des chaussures ça fausse
- [OK] Landmarks indices corrects pour Tasks API
- [OK] Ratios et seuils cohérents avec la biomécanique

### 2. angle_calculator.py — Seuils adaptatifs
- [BUG] shoulder_hip_ratio utilisé pour bench flare mais le champ s'appelle `shr` dans la function qui vient de `shoulder_hip_ratio` du profil morpho — OK cohérent
- [IMPROVE] Pas d'adaptation pour curl (biceps court/long devrait affecter ROM attendu)
- [IMPROVE] Pas d'adaptation pour lateral raise
- [OK] Squat, deadlift, bench, RDL, barbell row adaptations correctes
- [OK] Limites min/max empêchent des seuils aberrants

### 3. html_report.py — Section morpho
- [IMPROVE] Silhouette SVG : les bras sont des lignes droites tombantes, pas de coudes → visuellement pauvre
- [IMPROVE] Seulement 3 recommandations affichées ([:3]) alors que le profiler en génère 5-8
- [OK] Couleurs des ratios cohérentes
- [OK] Posture items correctement affichés

### 4. handlers.py — Flow WhatsApp
- [BUG POTENTIEL] _morpho_states et _morpho_photos sont des dicts en mémoire → perdus au restart
- [IMPROVE] Pas de timeout sur le flow morpho — si le client envoie 1 photo et disparaît, le state reste indéfiniment
- [OK] Flow séquentiel correct (front → side → back)
- [OK] CPU-bound analysis correctement déléguée au thread pool
- [OK] Cleanup photos en finally block

### 5. messages.py
- [IMPROVE] Messages fonctionnels mais un peu "bot" — manque la personnalité AchZod
- [IMPROVE] MORPHO_PROFILE_RESULT pourrait inclure les valeurs de shoulder_width et hip_width
- [OK] Instructions photos claires

### 6. biomechanics_levers.py
- [CORRIGÉ] shoulder_width, hip_width, ratios ajoutés
- [OK] Calculs cohérents avec morpho_profiler

### 7. report_generator.py — Prompt LLM
- [OK] Section morpho dans le prompt bien conditionnée
- [OK] Instruction de ne pas pénaliser les adaptations morphologiques
- [OK] Données morpho passées au LLM en JSON

### 8. pipeline.py
- [OK] Charge le profil morpho depuis la config
- [OK] Calcule les seuils adaptés avant l'analyse
- [OK] Passe les données morpho au rapport
