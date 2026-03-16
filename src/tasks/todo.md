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
- Cause racine 1 confirmee: un worker local `MacBook-Pro-de-achkan.local-*` utilisait encore le token interne et claimait la queue prod.
- Cause racine 2 confirmee: le worker Render recevait `MINIMAX_REMOTE_WORKER_ID=auto`, ce qui le faisait lui aussi rejeter apres le garde-fou serveur.
- Correctifs appliques: garde-fou serveur sur les `worker_id` + fallback du worker Render sur son hostname `srv-*` quand l env vaut `auto`.
- Validation locale: `160 passed, 2 skipped`.
