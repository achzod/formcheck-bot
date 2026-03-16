# Session State

*Mise a jour : 2026-03-16 16:04 +04*

## Tache en cours
Incident prod critique Formcheck: finaliser le correctif MiniMax browser pour les videos longues/lourdes, pousser, puis verifier le deploy Render et suivre le prochain run utilisateur.

## Contexte immediat
1. La chaine webhook -> queue -> worker Render -> browser MiniMax est saine apres les correctifs queue/auth/Xvfb/media/profil navigateur.
2. Le dernier bloqueur actif n etait plus la queue mais un timeout MiniMax cote browser alors que l envoi video avait deja reussi.
3. Le code local a ete durci pour attendre l attachement selon la taille du fichier, tolerer davantage l envoi, rafraichir activement le chat MiniMax envoye quand l UI se fige, et etendre le timeout effectif selon duree+taille de la video.
4. Validation locale en cours terminee avec succes: `94 passed` sur la suite MiniMax et `169 passed, 2 skipped` sur la suite complete.

## Plan actif
1. Auditer le diff final du correctif timeout/chat refresh.
2. Committer et pousser le correctif.
3. Verifier le deploy web+worker sur Render.
4. Surveiller un nouveau run prod WhatsApp.

## Prochaine action immediate
Committer et pousser le correctif MiniMax, puis verifier que le deploy Render devient `live` avant nouveau test utilisateur.
