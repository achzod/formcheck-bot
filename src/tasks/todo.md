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
- [ ] Deployer et verifier que la queue prod n est plus parasitee

## Review
- Cause racine confirmee: un worker local `MacBook-Pro-de-achkan.local-*` utilisait encore le token interne et claimait la queue prod.
- Correctif applique: en prod, seuls les `worker_id` autorises peuvent claim les jobs MiniMax; par defaut, les workers Render (`srv-*`) sont acceptes.
- Validation locale: `159 passed, 2 skipped`.
