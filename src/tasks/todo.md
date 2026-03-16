# Todo

- [x] Reconstituer le symptome prod MiniMax (logs/runtime/endpoints)
- [x] Auditer la queue job -> worker -> MiniMax browser -> livraison WhatsApp
- [x] Identifier la cause racine du dernier echec
- [x] Corriger le code ou la configuration minimale necessaire
- [x] Verifier par tests + checks prod + audit final
- [x] Inspecter le nouveau test en attente dans la prod
- [x] Identifier ou le job bloque (webhook, queue, claim, browser, completion, livraison)
- [x] Bloquer cote serveur les workers non Render sur le claim MiniMax
- [x] Ajouter les tests de regression associes
- [x] Deployer et verifier que la queue prod n est plus parasitee
- [x] Corriger la derive d auth interne web/worker sur les endpoints MiniMax
- [x] Identifier pourquoi le worker live ne consomme pas la queue
- [x] Identifier pourquoi un job worker valide echoue en `404 /video`
- [x] Identifier pourquoi le dernier job crash sur le profil navigateur MiniMax
- [x] Verifier que le job en queue est bien repris par le worker Render live
- [x] Verifier le dernier test utilisateur apres fix profil navigateur
- [x] Identifier pourquoi le dernier run MiniMax timeoute alors que la queue est saine
- [x] Corriger le nouveau bloqueur overlay MiniMax `MaxClaw Team Mode`
- [x] Ajouter la regression test associee
- [x] Deployer le fix overlay et recontroler le prochain run
- [x] Inspecter le run prod casse apres deploy overlay
- [x] Identifier la panne active restante
- [x] Corriger le code ou la config necessaire
- [ ] Revalider localement, deployer, puis suivre un run prod sain

## Review
- Incident repris apres le deploy `2637bdf`: la queue Render et le worker etaient sains, mais certains runs MiniMax partaient en timeout alors que l envoi video avait bien eu lieu.
- Cause racine retenue: la strategie d attente browser etait trop passive pour les videos longues/lourdes. Si l UI MiniMax cessait de rafraichir activement le chat apres l envoi, le worker attendait jusqu au timeout global sans reouvrir le chat cible.
- Correctif local: attente d attachement video adaptee a la taille du fichier, attente du bouton d envoi plus tolerante, refresh actif du chat envoye quand l UI devient silencieuse, timeout effectif adapte a la duree et a la taille de la video, traces de `wait_refreshes` ajoutees au metadata.
- Validation locale: `pytest -q tests/test_minimax_motion_coach.py` -> `94 passed`, `pytest -q tests/test_remote_minimax_worker_flow.py tests/test_runtime_config.py` -> `26 passed`, `pytest -q` -> `169 passed, 2 skipped`.
- Reste a faire: pousser le correctif, verifier le deploy Render, puis suivre un run prod sain sur une nouvelle video WhatsApp.
