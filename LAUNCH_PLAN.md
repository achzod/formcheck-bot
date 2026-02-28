# LAUNCH PLAN — 3 JOURS (1-3 Mars 2026)

## Problèmes critiques à résoudre

### P0 — Détection d'exercice (BLOQUANT)
- GPT-4o identifie la mauvaise personne dans les frames
- Résultat : mauvais exercice détecté (curl barre → cable curl)
- **FIX** : Envoyer des frames RAW sans dépendre de MediaPipe + améliorer prompt
- **FIX RADICAL** : Si le gym est bondé, accepter que la détection peut se tromper et ajouter un bouton "Ce n'est pas le bon exercice" dans le rapport

### P0 — MediaPipe track la mauvaise personne (BLOQUANT)
- Le squelette, les angles, les reps — tout est calculé sur la mauvaise personne
- **FIX** : Accepter les limites de MediaPipe single-person dans un gym bondé
- **FIX** : Ne PAS montrer le squelette/frames annotées (déjà fait)
- **FIX** : Le rapport GPT-4o utilise ses propres frames visuelles, pas les données MediaPipe corrompues

### P1 — Rapport HTML 
- Design à améliorer (responsive, lisibilité mobile)
- Score gauge, sections, frames

### P1 — Rep counting
- GPT-4o Vision est primary — vérifier la fiabilité
- Signal processing = backup seulement

### P2 — WhatsApp UX
- Messages nettoyés ✅
- Tester le flow complet

## Stratégie

### APPROCHE RADICALE : GPT-4o fait TOUT, MediaPipe = bonus

Au lieu de dépendre de MediaPipe (qui fail dans les gyms bondés), faire :
1. Extraire 10-15 frames à intervalles réguliers de la vidéo
2. Envoyer TOUTES à GPT-4o en une seule requête
3. GPT-4o fait : détection exercice + comptage reps + analyse biomécanique + score
4. MediaPipe = bonus optionnel pour les graphiques d'angles (quand fiable)

Avantage : Plus de problème de "mauvaise personne" car GPT-4o a le contexte visuel complet
Coût : ~$0.10-0.15 par analyse (acceptable pour un service premium)
