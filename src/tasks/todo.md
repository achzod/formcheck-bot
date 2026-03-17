- [x] Verifier l etat exact du dernier run prod utilisateur (Twilio -> analyse -> job -> delivery)
- [x] Lire les logs worker du run courant et identifier la panne active exacte
- [x] Corriger uniquement la cause racine confirmee si le code est en cause
- [x] Valider par tests puis verifier le nouvel etat prod
- [ ] Deployer et revalider le job utilisateur en prod

Review:
- Cause structurelle confirmee: le worker executait MiniMax/Playwright dans son propre process. Si ce run se fige, le job reste en processing et plus rien n est renvoye au client.
- Correctif applique: isolation de chaque analyse dans un sous-processus avec hard timeout et kill du groupe de processus en cas de blocage.
- Validation locale: py_compile OK, tests worker+runtime OK, tests cibles MiniMax overlay/fallback OK.
