# PLAN — Bibliothèque d'Exercices FORMCHECK

## Phase 1 : Inventaire Complet (TOUS les exos de salle)

### PECTORAUX (12)
1. bench_press — Développé Couché Barre
2. incline_bench — Développé Incliné Barre
3. decline_bench — Développé Décliné Barre
4. dumbbell_bench — Développé Couché Haltères
5. dumbbell_incline — Développé Incliné Haltères
6. chest_fly — Écarté Haltères / Machine
7. cable_crossover — Vis-à-vis Poulie (Cable Crossover)
8. chest_dip — Dips Pectoraux (buste penché)
9. push_up — Pompes
10. machine_chest_press — Presse Pectorale Machine
11. svend_press — Svend Press
12. landmine_press — Landmine Press

### DOS (14)
13. pullup — Tractions Pronation
14. chinup — Tractions Supination
15. lat_pulldown — Tirage Vertical Poulie Haute
16. close_grip_pulldown — Tirage Vertical Prise Serrée
17. barbell_row — Rowing Barre Pronation
18. dumbbell_row — Rowing Haltère Unilatéral
19. pendlay_row — Pendlay Row
20. tbar_row — T-Bar Row
21. cable_row — Tirage Horizontal Poulie Basse
22. cable_pullover — Pullover Poulie Haute (Straight-Arm Pulldown)
23. pullover — Pullover Haltère (Allongé)
24. face_pull — Face Pull
25. reverse_fly — Oiseau / Reverse Fly
26. seal_row — Seal Row (Rowing Allongé)

### ÉPAULES (10)
27. ohp — Développé Militaire Barre
28. dumbbell_ohp — Développé Haltères Assis/Debout
29. arnold_press — Arnold Press
30. lateral_raise — Élévations Latérales
31. cable_lateral_raise — Élévations Latérales Poulie
32. front_raise — Élévations Frontales
33. upright_row — Tirage Menton
34. shrug — Shrugs (Haussements d'Épaules)
35. rear_delt_fly — Oiseau Arrière (Rear Delt Fly)
36. lu_raise — Lu Raise / Y-Raise

### BICEPS (8)
37. curl — Curl Barre EZ/Droite
38. dumbbell_curl — Curl Haltères Alternés
39. hammer_curl — Curl Marteau
40. preacher_curl — Curl Pupitre (Preacher)
41. incline_curl — Curl Incliné (Haltères banc incliné)
42. cable_curl — Curl Poulie Basse
43. concentration_curl — Curl Concentration
44. spider_curl — Spider Curl

### TRICEPS (8)
45. tricep_extension — Extension Triceps Poulie Haute (Pushdown)
46. skull_crusher — Barre au Front (Skull Crusher)
47. overhead_tricep — Extension Triceps au-dessus de la Tête
48. dip — Dips Triceps (buste droit)
49. kickback — Kickback Triceps
50. close_grip_bench — Développé Couché Prise Serrée
51. diamond_pushup — Pompes Diamant
52. cable_overhead_tricep — Extension Triceps Poulie Basse (overhead)

### QUADRICEPS (10)
53. squat — Back Squat
54. front_squat — Front Squat
55. goblet_squat — Goblet Squat
56. hack_squat — Hack Squat Machine
57. leg_press — Presse à Cuisses
58. leg_extension — Leg Extension
59. sissy_squat — Sissy Squat
60. bulgarian_split_squat — Fente Bulgare
61. lunge — Fente (Lunge)
62. walking_lunge — Fente Marchée

### ISCHIO-JAMBIERS (6)
63. rdl — Romanian Deadlift (RDL)
64. leg_curl — Leg Curl (Allongé/Assis)
65. nordic_curl — Nordic Curl
66. good_morning — Good Morning
67. single_leg_rdl — RDL Unilatéral
68. glute_ham_raise — GHR (Glute Ham Raise)

### FESSIERS (5)
69. hip_thrust — Hip Thrust
70. cable_kickback — Kickback Fessier Poulie
71. glute_bridge — Pont Fessier
72. sumo_deadlift — Sumo Deadlift
73. step_up — Step-Up

### DEADLIFT (3)
74. deadlift — Deadlift Conventionnel
75. sumo_deadlift — Sumo Deadlift
76. trap_bar_deadlift — Trap Bar Deadlift

### MOLLETS (2)
77. calf_raise — Mollets Debout
78. seated_calf_raise — Mollets Assis

### ABDOS (6)
79. crunch — Crunch
80. cable_crunch — Crunch Poulie Haute
81. hanging_leg_raise — Relevé de Jambes Suspendu
82. ab_wheel — Ab Wheel (Roue Abdominale)
83. plank — Planche (Gainage)
84. woodchop — Woodchop Poulie (Rotation)

### FULL BODY / FONCTIONNEL (5)
85. clean — Épaulé (Clean)
86. snatch — Arraché (Snatch)
87. thruster — Thruster
88. kettlebell_swing — Kettlebell Swing
89. battle_rope — Battle Rope

**TOTAL : ~89 exercices**

---

## Phase 2 : Architecture de Détection

### Problème actuel
Le pattern matcher par angles est NUL pour identifier les exercices :
- MediaPipe capte mal le upper body de profil
- Les patterns d'angles se chevauchent entre exercices
- Trop de faux positifs (pullover → lunge)

### Nouvelle architecture : VISION-FIRST + KNOWLEDGE BASE

```
Video → Extract mid-frame → GPT-4o Vision (PRIMARY)
                                    ↓
                              Exercise ID + confidence
                                    ↓
                          Pattern matching (VALIDATION)
                                    ↓
                      Knowledge Base → Report Generator
```

1. **GPT-4o Vision = détecteur primaire** (DÉJÀ FAIT)
   - Prompt expert avec rules spécifiques
   - `detail: high` pour voir l'équipement
   - Alias mapping (50+ synonymes)

2. **Pattern matching = validation/refinement**
   - Confirme ou infirme la vision
   - Ajoute des métriques spécifiques à l'exercice

3. **Knowledge Base par exercice** (NOUVEAU)
   - Chaque exercice a sa fiche : muscles ciblés, erreurs courantes, angles critiques, corrections
   - Injectée dans le prompt du report generator
   - Le rapport devient EXPERT et spécifique au mouvement

---

## Phase 3 : Knowledge Base Bioméca

### Structure par exercice
```python
EXERCISE_KB = {
    "cable_pullover": {
        "muscles": ["grand dorsal", "petit rond", "triceps long"],
        "common_errors": [
            "Flexion excessive des coudes (doit rester bras quasi tendus)",
            "Mouvement initié par les bras au lieu du dos",
            "Tronc trop droit (léger hinge avant nécessaire)",
            "Amplitude insuffisante (bras doivent monter au-dessus de la tête)",
            "Compensation en extension lombaire"
        ],
        "key_angles": {
            "shoulder_flexion": {"optimal_rom": [120, 160], "unit": "deg"},
            "elbow_flexion": {"max_allowed": 30, "note": "bras quasi tendus"},
            "trunk_inclination": {"optimal": [15, 35]}
        },
        "corrections": [
            "Verrouille les coudes en légère flexion et ne bouge plus",
            "Initie le mouvement par la contraction du dos, pas des bras",
            "Contrôle la phase excentrique 2-3 sec (bras remontent)",
            "Expire en tirant vers le bas, inspire en remontant",
            "Penche-toi légèrement en avant (15-20°) pour optimiser l'étirement du grand dorsal"
        ],
        "cues": ["Tire avec les coudes, pas les mains", "Imagine pousser la barre vers tes cuisses"]
    }
}
```

---

## Phase 4 : Plan de Dev

### Sprint 1 — Enum + Vision (EN COURS)
- [x] 44 exercices dans l'enum
- [x] Vision-first detection
- [x] Expert vision prompt
- [x] Alias mapping
- [ ] **Étendre à 89 exercices** dans l'enum + display names + aliases
- [ ] **Ajouter les angle_attrs** pour les nouveaux exos dans html_report.py

### Sprint 2 — Knowledge Base
- [ ] Créer `src/analysis/exercise_knowledge.py`
- [ ] Fiche bioméca pour chaque exercice (muscles, erreurs, corrections, angles)
- [ ] Injecter la KB dans le prompt du report generator
- [ ] Le rapport cite les corrections SPÉCIFIQUES au mouvement

### Sprint 3 — Report Generator Upgrade
- [ ] Prompt du rapport basé sur la KB de l'exercice
- [ ] Sections adaptatives (pas les mêmes sections pour un curl vs un squat)
- [ ] Scoring adapté par exercice (pas les mêmes critères pour tous)

### Sprint 4 — Tests & Polish
- [ ] Tester avec 10+ vidéos de différents exercices
- [ ] Ajuster les prompts selon les retours
- [ ] Optimiser les coûts API (cache, batch)
