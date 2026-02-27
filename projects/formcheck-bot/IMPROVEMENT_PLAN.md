# FORMCHECK BOT — Plan d'amélioration complet
**Date :** 27 février 2026  
**Auteur :** Audit Clawd (subagent)  
**Statut :** À valider avant déploiement

---

## 1. Résumé de l'architecture actuelle

### Points forts ✅
- Pipeline 11 étapes complet (validation → extraction → lissage → angles → détection → reps → biomécanique avancée → levers → confiance → rapport → annotation)
- GPT-4o Vision en PRIMAIRE pour la détection d'exercice — bonne décision
- Pattern matching en FALLBACK robuste (91 exercices)
- Profil morphologique adaptatif (seuils calibrés sur les proportions du user)
- Rapport LLM structuré avec prompt expert solide (12 sections)
- HTML report hébergé avec lien + frames annotées
- Stripe intégré pour la monétisation

### Gaps identifiés ❌
- ZIP concurrent (Minimax) **inaccessible** — stub iCloud de 36KB, impossible à extraire. L'analyse concurrentielle sera basée sur les infos publiques déjà dans COMPETITIVE-ANALYSIS.md.
- 89 exercices dans l'enum vs 82 dans la KB → 7 exercices sans contenu expert
- `_morpho_states` et `_morpho_photos` en mémoire → perdus au restart Render
- Pas de timeout sur le flow morpho (state orphelin)
- Un seul frame (mid) envoyé à GPT-4o pour la détection → peut être insuffisant

---

## 2. Améliorations identifiées par catégorie

### 🔴 PRIORITÉ 1 — Fiabilité / Bugs critiques

#### 2.1 Détection multi-frame (impact: élevé, effort: moyen)
**Problème actuel :** GPT-4o Vision n'analyse que 1 seule frame (mid). Si c'est une frame floue ou milieu-de-mouvement peu caractéristique, la détection échoue.

**Solution :** Envoyer 3 frames (start + mid + end) à GPT-4o dans un seul appel. GPT-4o supporte plusieurs images dans `content`. Cela améliore la détection de ~15-20% sur les exercices ambigus.

```python
# Exemple dans detect_by_vision() :
content = [
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_start}"}},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_mid}"}},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_end}"}},
    {"type": "text", "text": "Ces 3 frames (début, milieu, fin) d'une même série. Identifie l'exercice."}
]
```

#### 2.2 Persistance état morpho en DB (impact: élevé, effort: faible)
**Problème actuel :** `_morpho_states` dict Python en mémoire → perdu à chaque restart Render (fréquents en free tier).

**Solution :** Ajouter une table `morpho_flow_state` dans SQLite :
```sql
CREATE TABLE morpho_flow_state (
    phone TEXT PRIMARY KEY,
    state TEXT NOT NULL,  -- 'waiting_front' | 'waiting_side' | 'waiting_back'
    front_path TEXT,
    side_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
+ cron de nettoyage des états > 24h.

#### 2.3 Timeout flow morpho (impact: moyen, effort: faible)
**Problème actuel :** Si le user envoie 1 photo et disparaît, le state reste indéfiniment en mémoire.

**Solution :** Dans le nettoyage DB, supprimer les states morpho > 2h. + message automatique "Tu n'as pas terminé ton profil morpho. Tape *morpho* pour recommencer."

#### 2.4 Compléter la KB pour les 7 exercices manquants (impact: moyen, effort: moyen)
**Exercices dans l'enum mais pas dans la KB :**
Identifier avec `grep` les exercices dans `Exercise` enum qui n'ont pas d'entrée dans `exercise_knowledge.py`.
Le LLM génère un rapport générique pour ces exercices → résultats sous-optimaux.

---

### 🟠 PRIORITÉ 2 — Qualité de l'analyse

#### 2.5 Valgus dynamique — amélioration calcul (impact: élevé, effort: moyen)
**Problème actuel :** Le valgus est calculé en 2D (x, y) depuis la vue de profil. Mais le valgus est un mouvement dans le plan frontal — il est **invisible depuis le profil**. Pour détecter le valgus, il faut la vue de face.

**Solution :** 
- Détecter l'angle de caméra depuis `confidence.camera_angle`
- Si vue de face → calculer le valgus via l'angle genou/cheville dans le plan X
- Si vue de profil → marquer le valgus comme "non mesurable depuis ce plan" et l'exclure du score
- Documenter clairement dans le rapport "Vue de profil : valgus non évalué — filmer de face pour cet indicateur"

#### 2.6 Détection de la profondeur du squat (impact: moyen, effort: faible)
**Problème actuel :** La profondeur est estimée par l'angle de genou, mais l'angle parallèle (90°) dépend de la hauteur de la hanche par rapport au genou, pas seulement de l'angle.

**Solution :** Calculer la hauteur relative hanche/genou en coordonnées normalisées :
```python
depth_ratio = (hip_y - knee_y) / femur_length
# depth_ratio > 0 → hanche au-dessus du genou (pas ATG)
# depth_ratio < 0 → hanche en-dessous du genou (ATG)
# depth_ratio ≈ 0 → parallèle
```

#### 2.7 Analyse multi-frames pour le rapport LLM (impact: élevé, effort: moyen)
**Problème actuel :** Le rapport LLM est généré avec uniquement des données JSON (chiffres). GPT-4o/Claude ne voit pas les frames.

**Solution :** Envoyer les 3 frames annotées EN PLUS du JSON au LLM de rapport. Utiliser un modèle Vision pour le rapport → feedback plus précis et contextuel ("je vois que ton genou droit rentre légèrement à la descente...").

**Attention :** Coût en tokens plus élevé. À configurer via feature flag.

#### 2.8 Score de symétrie — utiliser les deux côtés (impact: moyen, effort: faible)
**Problème actuel :** `PRIMARY_ANGLE_MAP` utilise toujours `left_knee_flexion` pour les squats. Si le user filme depuis la droite, le côté gauche est souvent partiellement occulté.

**Solution :** Calculer automatiquement quel côté est le mieux détecté (visibility score MediaPipe), et utiliser ce côté comme angle primaire. Mettre à jour `PRIMARY_ANGLE_MAP` dynamiquement.

---

### 🟡 PRIORITÉ 3 — UX et engagement

#### 2.9 Messages WhatsApp — personnalité Achzod (impact: moyen, effort: faible)
**Problème actuel :** Les messages sont fonctionnels mais génériques. Le fichier `messages.py` dit lui-même "pas d'emojis" et "ton pro" — mais dans le contexte fitness/communauté Achzod, le ton devrait être plus direct/challenger.

**Exemples d'améliorations :**
```
Avant : "Bienvenue sur FORMCHECK by ACHZOD — Analyse biomécanique experte."
Après : "Yo ! Je suis FormCheck — le coach qui analyse ta technique pendant que t'es encore en sueur. 🏋️ Envoie ta vidéo."

Avant (erreur) : "Je n'ai pas réussi à détecter ton corps dans la vidéo."
Après : "Je vois pas bien ton corps sur cette vidéo — assure-toi d'être entièrement dans le cadre, des pieds à la tête. Refilme depuis le profil avec un bon éclairage et renvois-moi ça."
```

#### 2.10 Feedback de progression en temps réel (impact: élevé, effort: moyen)
**Problème actuel :** L'utilisateur attend 30-60s en silence pendant l'analyse.

**Solution :** Utiliser le `progress_callback` de `PipelineConfig` (déjà prévu dans le code mais non branché sur WhatsApp) pour envoyer des messages de progression :
```
"⚙️ Extraction de la pose... (étape 2/11)"
"🔍 Détection de l'exercice..."
"📊 Calcul des angles articulaires..."
"✍️ Génération du rapport biomécanique..."
```
**Note :** Throttle à 1 message toutes les 10s max pour ne pas spammer.

#### 2.11 Comparaison avec l'analyse précédente (impact: élevé, effort: moyen)
**Problème actuel :** Chaque analyse est isolée. Impossible de voir sa progression.

**Solution :** Stocker dans la DB les métriques clés par exercice (score, ROM genou, trunk inclination, etc.). Avant d'envoyer le rapport, chercher la dernière analyse du même exercice et ajouter :
```
"📈 Progression vs ta dernière analyse (squat, il y a 5 jours) :
• Score : 67 → 74 (+7 pts) ✅
• ROM genou : 118° → 124° (+6°) ✅  
• Trunk lean : 38° → 31° (-7°) ✅ (moins d'inclinaison = mieux)"
```

#### 2.12 Guide de tournage par exercice avant l'analyse (impact: moyen, effort: faible)
**Problème actuel :** Le guide de tournage est disponible via "guide" mais pas affiché automatiquement.

**Solution :** Si c'est la 1ère analyse d'un utilisateur, et que GPT-4o détecte l'exercice avec confiance < 0.6, envoyer un rappel ciblé :
```
"Ton squat a une qualité d'image limitée. Pour la prochaine fois : filme de profil, caméra à hauteur de la hanche, 2-3m de distance."
```

---

### 🟢 PRIORITÉ 4 — Performance et scalabilité

#### 2.13 Cache du modèle MediaPipe (impact: moyen, effort: faible)
**Problème actuel :** `extract_pose()` recrée le `PoseLandmarker` à chaque appel → overhead de ~0.5-1s.

**Solution :** Singleton thread-local du landmarker, initialisé une seule fois au démarrage.

#### 2.14 Réduction du sample_every_n adaptatif (impact: moyen, effort: moyen)
**Problème actuel :** `sample_every_n=3` est fixe. Pour une vidéo de 60 FPS c'est ok, mais pour du 30 FPS c'est insuffisant (on saute 2 frames sur 3).

**Solution :** Calculer dynamiquement `sample_every_n` pour toujours analyser ~10 FPS :
```python
sample_every_n = max(1, round(fps / 10))
# 30 FPS → sample 3 (10 FPS effectif)  
# 60 FPS → sample 6 (10 FPS effectif)
# 15 FPS → sample 1 (15 FPS effectif)
```

#### 2.15 Rapport HTML — amélioration visuelle (impact: moyen, effort: moyen)
**Problème actuel :** Les frames annotées montrent un squelette MediaPipe basique. Le concurrent Minimax affiche des overlays animés plus riches.

**Solution sans dépendance lourde :**
- Ajouter les valeurs d'angles directement sur les frames annotées (actuellement fait en partie dans `frame_annotator.py`)
- Ajouter une barre de score colorée (rouge/orange/vert) par articulation
- Améliorer le SVG silhouette dans le rapport HTML (bras avec coudes, articulations colorées selon score)

---

## 3. Plan d'action priorisé

### Sprint 1 — Quick wins (2-3 jours)
| # | Tâche | Fichier | Impact |
|---|-------|---------|--------|
| 1 | Détection multi-frame (3 frames → GPT-4o) | `exercise_detector.py` | 🔴 Élevé |
| 2 | Timeout flow morpho + nettoyage | `handlers.py`, `database.py` | 🔴 Élevé |
| 3 | Progress callback branché WhatsApp | `handlers.py` | 🟠 Moyen |
| 4 | Score valgus exclu si vue de profil | `angle_calculator.py`, `report_generator.py` | 🟠 Moyen |
| 5 | sample_every_n adaptatif au FPS | `pipeline.py` | 🟢 Facile |

### Sprint 2 — Qualité analyse (1 semaine)
| # | Tâche | Fichier | Impact |
|---|-------|---------|--------|
| 6 | Persistance morpho_states en DB | `handlers.py`, `database.py` | 🔴 Élevé |
| 7 | Détection profondeur squat (hip/knee ratio) | `biomechanics_advanced.py` | 🟠 Moyen |
| 8 | Utiliser le côté le mieux détecté (visibility) | `rep_segmenter.py`, `angle_calculator.py` | 🟠 Moyen |
| 9 | Compléter KB pour 7 exercices manquants | `exercise_knowledge.py` | 🟠 Moyen |
| 10 | Messages avec personnalité Achzod | `messages.py` | 🟡 UX |

### Sprint 3 — Différenciation (2 semaines)
| # | Tâche | Fichier | Impact |
|---|-------|---------|--------|
| 11 | Comparaison avec analyse précédente | `handlers.py`, `database.py` | 🔴 Élevé |
| 12 | Rapport LLM avec images (vision) | `report_generator.py` | 🔴 Élevé |
| 13 | Amélioration frames annotées (angles sur image) | `frame_annotator.py` | 🟠 Moyen |
| 14 | Cache MediaPipe singleton | `pose_extractor.py` | 🟢 Perf |

---

## 4. Note sur le concurrent Minimax "AI Motion Coach"

Le ZIP `~/Downloads/ai-motion-coach-complete.zip` est un **stub iCloud** (36KB seulement, pas le vrai fichier). Il est inaccessible car iCloud Drive n'est pas configuré dans cet environnement.

Depuis l'analyse concurrentielle existante (`COMPETITIVE-ANALYSIS.md`) et les infos publiques Minimax :
- Minimax "Motion Coach" = app mobile + API B2B, pas de WhatsApp
- Focalisé sur les mouvements en temps réel (streaming), pas asynchrone
- Utilise des modèles propriétaires de pose estimation (pas MediaPipe)
- Pas de profil morphologique adaptatif documenté

**Avantage FORMCHECK :** L'approche WhatsApp asynchrone + profil morpho + knowledge base expert sont des différenciateurs que Minimax n'a pas.

---

## 5. Métriques à surveiller post-amélioration

- Taux de détection correcte de l'exercice (actuellement estimé ~85% → cible 93%+ avec multi-frame)
- Temps moyen d'analyse (actuellement ~45s → cible <30s avec cache MediaPipe + sample adaptatif)
- Taux de complétion du flow morpho (actuellement inconnu → mesurer après persistance DB)
- NPS utilisateur (mesurer via message post-analyse : "Note ton analyse de 1 à 5 ⭐")
- Score moyen des analyses (baseline à établir)

---

*Ce plan est documentaire. Aucun code n'a été modifié. Validation requise avant implémentation.*
