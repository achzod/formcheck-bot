# FormCheck Bot — Audit Complet & Plan de Fix

## Diagnostic (27 Feb 2026)

### Problèmes Identifiés

#### 🔴 CRITIQUE — Le bot crash sur les vidéos

**P1: Progress callback crash dans thread pool**
- `_progress_cb` est appelé depuis un ThreadPool (via `run_in_executor`)
- Le callback appelle `asyncio.get_event_loop()` + `asyncio.ensure_future()` dans un thread non-async
- Sur Python 3.10+, `get_event_loop()` dans un thread sans loop lève DeprecationWarning ou RuntimeError
- Même avec le try/except, si `ensure_future()` échoue silencieusement → le callback ne crash pas, mais le pipeline n'envoie aucun progress
- **FIX**: Capturer le loop AVANT le run_in_executor, passer `loop.call_soon_threadsafe()` dans le callback

**P2: MediaPipe prend le mauvais personne**
- `pose_landmarks[0]` = toujours la première personne détectée
- Avec spotters/groupes, la première personne n'est PAS forcément le lifter
- Quand MediaPipe prend un spotter → les angles sont absurdes → la détection d'exercice échoue → `result.report = None`
- **FIX**: Sélectionner la personne avec la plus grande surface (bounding box area) dans le cadre

**P3: Pas de gestion timeout/mémoire sur vidéos longues**
- Vidéo 1m29 @ 30fps = 2670 frames → même avec sample_every_3 = 890 frames MediaPipe
- Sur le plan gratuit Render (512MB RAM), ça peut OOM
- **FIX**: Limiter à max 600 frames totales (adapter sample_every_n dynamiquement)

**P4: Fallback GPT-4o peut ne jamais se déclencher**
- Si le pipeline crash à l'étape 2 (extraction) → `result.extraction` est None → `mid_frame` est None → fallback ne se déclenche pas
- **FIX**: Avant le pipeline, extraire une frame "preview" indépendamment. Si le pipeline fail, utiliser cette preview pour le fallback GPT-4o

#### 🟡 IMPORTANT — Qualité & UX

**P5: Messages d'erreur toujours anciens**
- Vérifié : `messages.py` mis à jour ET deploy live
- Le problème : le handler dans `_safe_handle()` (main.py) catch les exceptions avec `msg.ERROR_GENERIC`, pas `msg.ERROR_ANALYSIS_FAILED`
- Si le pipeline lève une exception non-catchée dans `_run_analysis` → le `except` de `_safe_handle()` envoie `ERROR_GENERIC` (pas `ERROR_ANALYSIS_FAILED`)
- Mais les screenshots montrent `ERROR_ANALYSIS_FAILED`... donc le pipeline retourne `result` avec `success=False`, pas une exception
- **VERDICT**: Le pipeline complète sans crash mais `result.report = None` → envoi du message ERROR_ANALYSIS_FAILED (le NOUVEAU message devrait être affiché)
- **POSSIBLE**: Le deploy n'a pas rebuild les .pyc → Python utilise les anciennes versions bytecode. Render devrait rebuild, mais le buildpack cache peut interférer

**P6: Aucun log visible pour debug**
- Pas d'accès aux logs Render via API (format incompatible)
- **FIX**: Ajouter un endpoint `/debug/last-errors` protégé par token pour voir les 10 dernières erreurs

**P7: Le MorphoFlowState table n'existe pas encore en prod**
- Ajouté la table dans le code mais Render utilise SQLite sur le disque ephemeral → perd les données à chaque redémarrage
- `init_db()` fait `create_all()` donc la table sera créée au startup — OK

#### 🟢 MINEUR

**P8: Adaptive sample_every_n recalcule FPS indépendemment**
- On ouvre la vidéo 2x (une fois dans pipeline pour FPS, une fois dans extract_pose)
- Pas un bug, juste du overhead — mineur

## Plan d'Action (Ordre d'exécution)

### Fix 1 — Preview frame + Fallback garanti (P4)
Avant de lancer le pipeline, extraire 1 frame du milieu de la vidéo. Si le pipeline fail, cette frame est utilisée pour le fallback GPT-4o. Garantit TOUJOURS un feedback.

### Fix 2 — Progress callback thread-safe (P1)
Capturer `loop` dans le handler avant `run_pipeline_async`, le passer dans PipelineConfig, utiliser `loop.call_soon_threadsafe()` dans le callback.

### Fix 3 — Sélection personne optimale (P2)
Dans `pose_extractor.py`, si `detection_result.pose_landmarks` contient >1 personne, choisir celle avec le plus grand bounding box (centre du cadre + plus de landmarks visibles).

### Fix 4 — Limite frames maximum (P3)
Dans pipeline, après calcul du `adaptive_sample_n`, vérifier que `total_frames / sample_n < 600`. Si non, augmenter `sample_n`.

### Fix 5 — Endpoint debug (P6)
Ajouter `/debug/last-errors` protégé par un token simple.

### Fix 6 — Clear des .pyc dans le build (P5)
Ajouter `find . -name "*.pyc" -delete` dans le build command Render.
