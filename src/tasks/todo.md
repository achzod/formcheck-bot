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
- [ ] Verifier que le job en queue est bien repris par le worker Render live

## Review
- Cause racine 1 confirmee: un worker local `MacBook-Pro-de-achkan.local-*` utilisait encore le token interne et claimait la queue prod.
- Cause racine 2 confirmee: le worker Render recevait `MINIMAX_REMOTE_WORKER_ID=auto`, ce qui le faisait lui aussi rejeter apres le garde-fou serveur.
- Cause racine 3 confirmee: le worker Render utilisait un secret interne different de celui accepte par le web (`Invalid internal token`), alors que l architecture supporte a la fois `MINIMAX_REMOTE_WORKER_TOKEN` et `RENDER_API_KEY`.
- Cause racine 4 confirmee: le wrapper `xvfb-run` peut laisser le service Render `live` alors que le vrai process Python worker n est plus present, ce qui vide la queue sans consumer.
- Correctifs appliques: garde-fou serveur sur les `worker_id`, fallback du worker Render sur son hostname `srv-*` quand l env vaut `auto`, acceptation cote web des deux secrets internes valides, puis demarrage direct de `Xvfb` depuis le process Python worker au lieu d un reexec `xvfb-run`.
- Validation locale: `162 passed, 2 skipped`.
