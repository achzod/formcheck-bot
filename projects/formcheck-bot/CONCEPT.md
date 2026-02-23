# FORMCHECK by ACHZOD — Bot WhatsApp d'Analyse Biomécanique

## Le Concept

Un bot WhatsApp où tes clients envoient une vidéo de leur exercice de musculation et reçoivent en retour une analyse biomécanique complète : angles articulaires, compensations, erreurs techniques, corrections personnalisées et exercices correctifs. Le tout basé sur ta méthode et tes 11 certifications.

Le client paie d'abord (lien Stripe ou paiement intégré), puis il a accès à un nombre d'analyses selon son forfait.

---

## Pourquoi c'est le bon moment

La technologie est mûre. On a maintenant deux outils complémentaires qui n'existaient pas il y a 2 ans.

**MediaPipe Pose Landmarker (Google)** détecte 33 points anatomiques en 3D sur une vidéo à partir d'une simple caméra de smartphone. On parle des épaules, coudes, poignets, hanches, genoux, chevilles, et même les pieds et les mains. Ça tourne en temps réel. À partir de ces 33 landmarks, on peut calculer tous les angles articulaires frame par frame : flexion du genou au squat, inclinaison du tronc au deadlift, abduction de l'épaule au développé militaire. Et surtout, on peut détecter les asymétries gauche-droite, les compensations et les déviations par rapport aux patterns optimaux.

**Les modèles de vision IA (GPT-4 Vision, Claude Vision, Gemini)** permettent d'analyser visuellement une vidéo image par image et de produire une interprétation qualitative experte. On peut leur donner un contexte biomécanique complet (ta formation, tes critères d'analyse par exercice) et ils produisent un retour structuré, pertinent et personnalisé.

L'approche hybride — données quantitatives de MediaPipe + interprétation qualitative du LLM — c'est ce qui fait la différence entre un gadget et un vrai outil de coach.

---

## Architecture Technique

### Pipeline d'analyse (ce qui se passe quand un client envoie une vidéo)

**Étape 1 — Réception.** Le client envoie sa vidéo via WhatsApp. Le bot la récupère via l'API WhatsApp Business (Meta Cloud API ou Twilio). La vidéo est stockée temporairement sur un serveur sécurisé.

**Étape 2 — Détection de l'exercice.** Un premier passage du LLM vision identifie automatiquement l'exercice : squat, bench press, deadlift, curl, etc. Si le modèle hésite, il demande confirmation au client. Ça permet de charger le bon référentiel biomécanique.

**Étape 3 — Extraction des landmarks.** MediaPipe Pose Landmarker traite la vidéo frame par frame et extrait les 33 points anatomiques en 3D. Les 33 landmarks incluent le nez, les yeux, les oreilles, les épaules, les coudes, les poignets, les hanches, les genoux, les chevilles, les talons, les orteils et les index des pieds. On obtient les coordonnées x, y, z et un score de confiance pour chaque point.

**Étape 4 — Calcul des métriques biomécaniques.** À partir des landmarks, le système calcule automatiquement les angles articulaires clés pour l'exercice identifié. Par exemple, pour un squat : angle de flexion du genou au point le plus bas, angle de flexion de la hanche, inclinaison du tronc par rapport à la verticale, position du genou par rapport aux orteils (en x), symétrie gauche-droite de la descente, valgus dynamique (déviation médiale du genou par rapport à la hanche et la cheville), et la trajectoire du centre de masse estimé.

**Étape 5 — Analyse IA experte.** Toutes les données quantitatives sont envoyées à un LLM (GPT-4 ou Claude) avec un prompt système qui contient ta méthode biomécanique complète : les critères d'exécution optimale par exercice, les compensations fréquentes, les corrections prioritaires, les exercices correctifs, et le ton de communication. Le LLM produit un rapport personnalisé.

**Étape 6 — Génération du rapport.** Le rapport est envoyé au client via WhatsApp sous forme de messages structurés, avec éventuellement une image annotée (frames clés avec les angles superposés) et un résumé audio si on veut aller plus loin.

### Stack technique

**Backend :** Python (FastAPI) ou Node.js (Express). Python est préférable parce que MediaPipe, OpenCV et les bibliothèques de calcul d'angles (NumPy) sont natifs Python.

**Pose estimation :** MediaPipe Pose Landmarker (gratuit, open source, fonctionne en local ou sur serveur). Alternative plus précise mais payante : MoveNet Thunder (TensorFlow) ou les modèles de BodyVision.

**Vision IA :** GPT-4 Vision (OpenAI API) pour l'identification de l'exercice et l'analyse qualitative des frames clés. Alternative : Claude Vision (Anthropic) ou Gemini Pro Vision (Google).

**LLM pour le rapport :** GPT-4 / Claude avec un system prompt massif contenant toute ta méthode biomécanique. C'est le cœur de la valeur ajoutée. Le prompt inclut tes critères d'analyse pour chaque exercice, tes corrections favorites, tes analogies, ton style de communication.

**WhatsApp :** Meta WhatsApp Business Cloud API (gratuit pour les réponses dans les 24h, payant au-delà) ou Twilio WhatsApp API (plus simple à intégrer, légèrement plus cher).

**Paiement :** Stripe Checkout. Le client reçoit un lien de paiement. Après paiement, son numéro WhatsApp est activé dans la base de données avec un crédit d'analyses.

**Base de données :** PostgreSQL ou Supabase pour stocker les profils clients, les crédits, l'historique des analyses et les métriques de suivi.

**Hébergement :** Un VPS (Hetzner, DigitalOcean) ou un cloud (AWS, GCP). Le traitement vidéo MediaPipe peut tourner sur CPU standard, pas besoin de GPU dédié pour le volume initial.

**Stockage vidéo :** S3 ou équivalent, avec suppression automatique après 30 jours (RGPD).

---

## Base de connaissances biomécanique (le vrai avantage compétitif)

C'est ici que ta formation intervient. Le bot n'est pas générique. Il a été entraîné (via prompting) avec TA méthode. Concrètement, on construit un fichier de référence par exercice qui contient tout ce que le bot doit savoir.

### Exemple : Squat (Back Squat)

**Critères d'exécution optimale :**
Position des pieds (largeur, rotation externe 15-30°), engagement du core (pression intra-abdominale, bracing 360°), descente (hanche initie le mouvement, genoux trackent au-dessus des 2e-3e orteils, profondeur relative à la mobilité de hanche et de cheville), position du tronc (inclinaison acceptable selon la morphologie fémorale), alignement cervical (neutre, regard droit ou légèrement vers le bas), position de la barre (high bar vs low bar, impact sur l'angle du tronc).

**Compensations fréquentes (et ce que MediaPipe détecte) :**
Valgus dynamique → déviation médiale des genoux (landmarks genoux vs hanches vs chevilles en x). Butt wink → rotation postérieure du bassin en fin de course (angle hanche vs angle lombo-pelvien). Shift latéral → asymétrie gauche-droite des landmarks hanche et épaule. Forward lean excessif → angle du tronc dépasse le seuil pour le type de squat. Talons qui décollent → landmark talon perd son ancrage au sol (coordonnée z).

**Corrections prioritaires (ordonnées) :**
1. Stabilité du core (si absente, rien d'autre ne fonctionne)
2. Mobilité de cheville (Knee-to-Wall < 10cm = restriction)
3. Contrôle du valgus (activation fessier moyen, drill "screw the foot")
4. Profondeur vs mobilité (ne pas forcer au-delà de la mobilité disponible)
5. Tempo et contrôle excentrique

**Exercices correctifs associés :**
Goblet squat avec pause, squat à la boîte, mobilisation cheville avec bande, activation fessier moyen en decubitus latéral, dead bug pour le core.

On fait le même fichier pour chaque exercice majeur. Tu as déjà tout le contenu dans ta formation biomécanique (les 23 chapitres). C'est littéralement le contenu de la formation converti en base de connaissances pour le bot.

### Exercices couverts au lancement (V1)

Squat (back, front, goblet), deadlift (conventionnel, sumo, roumain), bench press (plat, incliné), overhead press (debout, assis), rowing (barre, haltère), pull-up et lat pulldown, curl biceps (barre, haltère), extension triceps, hip thrust, leg press, leg curl, leg extension, développé épaules, élévations latérales.

Ça couvre 90% de ce que les gens font en salle.

---

## Expérience Utilisateur (Flow Client)

### Premier contact

Le client découvre le bot via un lien sur ton Instagram, ta chaîne YouTube, ton site, ou via le bouche-à-oreille. Il envoie un message au numéro WhatsApp du bot.

Le bot répond avec un message de bienvenue qui explique le concept en 3 phrases et propose les forfaits. Le client choisit son forfait et reçoit un lien Stripe pour payer.

### Après paiement

Le bot confirme l'activation et explique comment ça marche : "Envoie-moi une vidéo de ton exercice (de profil c'est le mieux, ou de face pour certains exos). Précise le nom de l'exercice si tu veux, sinon je le détecte automatiquement."

### Envoi d'une vidéo

Le client filme son set et envoie la vidéo via WhatsApp. Le bot accuse réception : "Vidéo reçue, j'analyse ton squat. Résultat dans 60 à 90 secondes."

Le bot traite la vidéo, extrait les données, génère le rapport et l'envoie.

### Le rapport (ce que le client reçoit)

**Message 1 — Résumé visuel.** Une ou deux images des frames clés avec les angles articulaires superposés en overlay (comme un screenshot de motion capture simplifié). Le client voit visuellement où sont les problèmes.

**Message 2 — Analyse détaillée.** Un texte structuré qui couvre ce qui est bien (toujours commencer par le positif), ce qui doit être corrigé (classé par priorité), les compensations détectées avec explication de pourquoi c'est un problème, et les corrections concrètes à appliquer dès la prochaine séance.

**Message 3 — Exercices correctifs.** 2 à 3 exercices correctifs ciblés avec description ou lien vers une démonstration (possibilité de linker vers tes vidéos YouTube).

**Message 4 (optionnel) — Score global.** Un score de 0 à 100 sur l'exécution, avec les sous-scores par critère. Les gens adorent les scores, ça gamifie l'expérience et ça les motive à renvoyer une vidéo après correction.

---

## Business Model

### Forfaits proposés

**Essai gratuit — 1 analyse.** Le client peut tester une fois gratuitement. C'est le hook d'acquisition. L'analyse gratuite est identique à la payante (pas de version dégradée).

**Pack Découverte — 5 analyses — 19€.** Pour ceux qui veulent tester sur plusieurs exercices.

**Pack Standard — 15 analyses — 39€.** Le sweet spot. Un mois d'entraînement avec 3-4 analyses par semaine.

**Pack Premium — 40 analyses — 79€.** Pour les sérieux qui veulent analyser chaque exercice de leur programme.

**Abonnement mensuel — Illimité — 29€/mois.** Analyses illimitées. Le modèle récurrent qui génère du MRR (Monthly Recurring Revenue).

### Coûts par analyse (estimés)

Traitement MediaPipe (CPU) : quasi nul (0.01€). API Vision (identification exercice, 2-3 frames) : ~0.05€. API LLM (génération du rapport, ~2000 tokens out) : ~0.03€. WhatsApp Business API (message sortant) : ~0.05€. Stockage vidéo temporaire : négligeable.

**Coût total par analyse : environ 0.15€.** Même au forfait le moins cher (19€ pour 5 analyses = 3.80€/analyse), la marge est énorme.

### Potentiel de revenus

Avec 200 clients actifs à 29€/mois d'abonnement = 5 800€/mois de MRR. Avec 1000 clients = 29 000€/mois. Et ça scale tout seul — le bot tourne 24/7 sans que tu lèves le petit doigt.

---

## Avantage concurrentiel — Pourquoi personne ne peut te copier

Les apps de form check qui existent (Tempo, Kemtai, VAF) utilisent la pose estimation basique et donnent des retours génériques du style "genoux pas assez fléchis". Aucune n'a une vraie intelligence biomécanique derrière.

Toi, tu as 11 certifications dont Pre-Script (biomécanique avancée), NASM, ISSA, Precision Nutrition. Tu as 10 ans d'expérience et des milliers de clients transformés. Ta méthode est codifiée dans 23 chapitres de formation. C'est cette base de connaissances qui donne au bot une capacité d'analyse que personne d'autre ne peut reproduire.

Le bot ne remplace pas le coaching humain. Il le démocratise. Ceux qui n'ont pas les moyens de payer un coaching premium à 200€/mois peuvent quand même avoir accès à une analyse biomécanique de qualité pour 29€/mois. Et ceux qui sont déjà tes clients premium peuvent l'utiliser entre les sessions pour vérifier leur exécution en autonomie.

---

## Roadmap

### Phase 1 — MVP (4-6 semaines)

Bot WhatsApp fonctionnel avec paiement Stripe. Analyse vidéo hybride (MediaPipe + LLM vision). Base de connaissances pour les 5 exercices principaux (squat, deadlift, bench, OHP, rowing). Rapport texte + image annotée. Forfaits packs (pas encore d'abonnement).

### Phase 2 — Expansion (mois 2-3)

Ajout de 15 exercices supplémentaires. Système d'abonnement mensuel. Score de forme et historique de progression (le client voit son score s'améliorer au fil du temps). Dashboard web simple pour que tu puisses voir les stats (nombre d'analyses, revenus, exercices les plus analysés).

### Phase 3 — Scale (mois 4-6)

Analyse en temps réel (le client filme en live et reçoit le feedback en temps réel via le stream vidéo WhatsApp — techniquement possible mais plus complexe). Programme correctif automatique (le bot génère un programme de 4 semaines basé sur les faiblesses détectées). Intégration avec ta plateforme APEXLABS. Version en anglais pour le marché international. API ouverte pour que d'autres coachs puissent utiliser le moteur avec leur propre base de connaissances (SaaS B2B).

### Phase 4 — Moat (mois 6-12)

Modèle de pose estimation custom fine-tuné sur des données de musculation (plus précis que MediaPipe générique). Base de données de patterns de compensation issue des milliers d'analyses réalisées (data moat). Certification "FormCheck Approved" pour les coachs qui utilisent la plateforme. Programme d'affiliation pour les influenceurs fitness.

---

## Risques et solutions

**Qualité vidéo variable.** Les clients filment avec des angles de merde, en contre-jour, avec le téléphone qui bouge. Solution : le bot guide le client avant l'envoi ("filme-toi de profil, à hauteur de hanche, avec un éclairage correct") et refuse les vidéos inexploitables avec un message explicatif.

**Exercices non reconnus.** Le client fait un exercice exotique que le bot ne connaît pas. Solution : le bot dit "Je ne reconnais pas cet exercice. Tu peux me dire ce que c'est ?" et si l'exercice n'est pas dans la base, il fait une analyse générale basée sur les principes biomécaniques universels (alignement, symétrie, tempo, ROM).

**Responsabilité médicale/juridique.** Un client se blesse et accuse le bot. Solution : disclaimer clair dans les conditions d'utilisation. Le bot ne donne pas de conseils médicaux. Il analyse la technique et suggère des corrections. En cas de douleur, il recommande de consulter un professionnel de santé.

**Concurrence.** D'autres coachs copient le concept. Solution : la base de connaissances biomécanique est ton moat. Elle est issue de tes 11 certifications et de ta formation complète. Un concurrent peut copier le pipeline technique, pas l'expertise.

---

## Stack technique détaillé

```
WhatsApp Business Cloud API (Meta)
        ↓
Webhook → FastAPI (Python) 
        ↓
Stripe Checkout (paiement)
        ↓
Téléchargement vidéo → Stockage S3
        ↓
MediaPipe Pose Landmarker (extraction 33 landmarks)
        ↓
Module calcul angles (NumPy) → JSON métriques
        ↓
GPT-4 Vision → Identification exercice (frames clés)
        ↓
Claude/GPT-4 + System Prompt biomécanique + métriques JSON
        ↓
Rapport généré → Images annotées (OpenCV overlay)
        ↓
Envoi WhatsApp → Client
        ↓
PostgreSQL (profils, crédits, historique)
```

---

## Nom et branding

Suggestions :

**FORMCHECK by ACHZOD** — Direct, clair, associé à ta marque personnelle.

**BIOMOVE** — Plus technique, sonne bien.

**ACHZOD VISION** — Lie ta marque à la technologie vision.

**MOVELAB** — Labo du mouvement, cohérent avec APEXLABS.

**REPCHECK** — Rep par rep, check par check.

Je recommande **FORMCHECK by ACHZOD** pour le lancement parce que ça capitalise sur ta notoriété existante et c'est immédiatement compréhensible.

---

## Prochaine étape

Valide le concept, le pricing et le nom. Ensuite on attaque le prototype technique.
