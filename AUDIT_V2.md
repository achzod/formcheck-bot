# FormCheck Bot — Audit Complet V2
## Date: 2026-02-28 23:10 GMT+4

---

## PROBLÈMES CRITIQUES (P0 — Cassent l'expérience utilisateur)

### P0-1: Key frames envoyées à GPT-4o AVANT la détection d'exercice
**Fichier**: `pipeline.py` lignes 309-340
**Problème**: À l'étape 5 (détection), on envoie les key frames `start/mid/end` à GPT-4o pour identifier l'exercice. MAIS ces key frames ont été calculées à l'étape 2 (extraction) SANS connaître l'exercice → elles utilisent `hip_y` par défaut (fallback). L'étape 5a-bis recalcule les key frames APRÈS la détection, mais c'est trop tard — GPT-4o a déjà vu les mauvaises frames.
**Impact**: GPT-4o voit une frame "mid" qui ne correspond pas au pic de contraction → mauvaise détection.
**Fix**: Faire la détection en 2 passes : 1) pattern matching + candidats, 2) recalculer key frames, 3) envoyer les bonnes frames à GPT-4o.

### P0-2: Multi-personnes — motion tracking a un bug logique
**Fichier**: `pose_extractor.py`
**Problème**: `_prev_landmarks` est le landmarks de la personne trackée au frame précédent. Mais quand on compare le motion de la personne 0 vs personne 1, on compare TOUTES les personnes contre `_prev_landmarks` de la personne trackée → le score de motion des autres personnes est biaisé (comparé aux landmarks d'une autre personne).
**Impact**: Le motion scoring ne fonctionne pas correctement avec >2 personnes.
**Fix**: Stocker les landmarks PAR personne pour calculer le motion correctement.

### P0-3: Pas de cache/réinitialisation entre analyses
**Fichier**: `pose_extractor.py`
**Problème**: `_prev_center`, `_prev_landmarks`, `_motion_scores` sont des variables locales dans `extract_pose()` → OK car réinitialisées à chaque appel. Vérifié OK.

### P0-4: Le pattern matching est fondamentalement inutile
**Fichier**: `exercise_detector.py` lignes 1653+
**Problème**: `detect_by_pattern()` utilise des règles sur les angles pour deviner l'exercice. Résultat : il se trompe presque toujours (détecte squat pour un OHP, leg extension pour un curl). Et ses mauvais candidats EMPOISONNENT GPT-4o.
**Impact**: GPT-4o est biaisé par de mauvais candidats → détection ratée.
**Fix**: DÉSACTIVER le pattern matching pour les candidats. Envoyer TOUJOURS la liste complète des exercices courants à GPT-4o. Le pattern matching ne devrait servir que comme TIE-BREAKER quand GPT-4o hésite.

---

## PROBLÈMES IMPORTANTS (P1 — Dégradent la qualité)

### P1-1: Key frame "end" pas envoyée sur WhatsApp mais dans le rapport
**Fichier**: `handlers.py` ligne ~410
**Problème**: Seul "mid" est envoyé sur WhatsApp. OK c'est voulu. Mais dans le rapport HTML, "start" et "mid" sont montrés → si le squelette est sur la mauvaise personne (P0-2), c'est visible dans le rapport.

### P1-2: sample_every_n adaptatif peut manquer des mouvements
**Fichier**: `pipeline.py` ligne ~235
**Problème**: Pour une vidéo 60fps, `adaptive_sample_n = round(60/10) = 6` → on analyse 1 frame sur 6 (10fps effectif). C'est suffisant pour les angles mais ça perd de la résolution temporelle pour le rep counting.
**Impact**: Mineur car le rep counting est fait par GPT-4o Vision (frames extraites séparément).

### P1-3: L'exercice detection utilise "detail: high" → coûteux
**Fichier**: `exercise_detector.py` ligne ~1875
**Problème**: Envoie 3 frames en "high" detail à GPT-4o pour la détection. Coût ~$0.03-0.04 par détection.
**Fix**: Utiliser "low" detail pour la détection (suffisant pour identifier l'exercice). Garder "high" uniquement pour le rapport.

### P1-4: Markdown stripping peut casser des parties du rapport
**Fichier**: `html_report.py` ligne 117-120
**Problème**: Le stripping supprime TOUS les tirets en début de ligne (`^[\-\*•]\s+`). Si GPT-4o écrit "45-60 secondes" en début de ligne, le "45-" peut être coupé. L'expression `^[\-\*•]\s+` vérifie qu'il y a un espace après, donc "45-60" devrait être OK. Vérifié OK.

### P1-5: Pas de validation du JSON retourné par GPT-4o
**Fichier**: `exercise_detector.py`, `vision_rep_counter.py`
**Problème**: Si GPT-4o retourne un JSON malformé, on a un crash silencieux → fallback à "unknown" ou 0 reps.
**Impact**: Perte d'analyse silencieuse.
**Fix**: Ajouter un retry (1 fois) si le JSON est malformé.

### P1-6: Score breakdown pas toujours cohérent avec le score total
**Fichier**: `report_generator.py`
**Problème**: GPT-4o peut donner un score de 52/100 mais des sous-scores qui font 20+15+10+7 = 52. C'est cohérent ici mais pas garanti.
**Fix**: Ajouter une vérification côté code que la somme des sous-scores == score total.

---

## PROBLÈMES MINEURS (P2 — Nice to fix)

### P2-1: Pas de timeout sur les appels GPT-4o
**Fichier**: `exercise_detector.py`, `vision_rep_counter.py`, `report_generator.py`
**Problème**: Si l'API GPT-4o est lente, le pipeline peut bloquer >60s.
**Fix**: Ajouter `timeout=30` aux appels OpenAI.

### P2-2: Cleanup de fichiers temporaires pas toujours fait
**Fichier**: `handlers.py`
**Problème**: Si le pipeline crash entre le download et le cleanup, les fichiers restent.
**Impact**: Mineur sur Render (tmp est éphémère).

### P2-3: Le profil morpho n'est pas utilisé pour adapter les seuils d'angles
**Fichier**: `pipeline.py` étape 5b
**Problème**: Les seuils adaptés sont calculés et passés au LLM, mais les FRAMES annotées utilisent les seuils par défaut (pas les adaptés).
**Fix**: Passer `adapted_thresholds` à `annotate_key_frames()`.

---

## PLAN D'ACTION PRIORITAIRE

### Fix immédiat (ce soir)
1. **P0-4**: Désactiver les candidats du pattern matching → toujours envoyer la liste complète
2. **P0-1**: Détection en 2 passes (detect d'abord avec frames par défaut, puis re-detect si les frames changent après recalcul)

### Fix court terme (demain)
3. **P0-2**: Multi-personnes — stocker landmarks par personne pour le motion tracking
4. **P1-5**: Retry sur JSON malformé
5. **P1-3**: Passer en "low" detail pour la détection

### Fix moyen terme
6. **P2-1**: Timeouts GPT-4o
7. **P2-3**: Seuils adaptés dans les annotations
8. **P1-6**: Validation score breakdown
