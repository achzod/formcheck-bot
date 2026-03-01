"""Génération de rapport biomécanique via LLM (Claude / GPT-4).

Charge le référentiel biomécanique depuis BIOMECHANICS_KNOWLEDGE.md,
combine avec les métriques d'angles et l'exercice détecté, et envoie
le tout à Claude (Anthropic) ou GPT-4 (OpenAI) pour produire un rapport
structuré avec score /100.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analysis.angle_calculator import AngleResult, angles_to_dict
from analysis.exercise_detector import (
    DetectionResult,
    Exercise,
    EXERCISE_DISPLAY_NAMES,
)
from analysis.rep_segmenter import RepSegmentation
from analysis.confidence import AnalysisConfidence
# format_kb_for_prompt removed — using get_kb_prompt_section locally


@dataclass
class Report:
    """Rapport d'analyse biomécanique structuré."""
    exercise: str
    exercise_display: str
    score: int                              # /100
    report_text: str                        # Rapport complet formaté
    positives: list[str] = field(default_factory=list)
    corrections: list[dict[str, str]] = field(default_factory=list)
    corrective_exercises: list[str] = field(default_factory=list)
    score_breakdown: dict[str, int] = field(default_factory=dict)
    raw_llm_response: str = ""
    model_used: str = ""


# ── Chargement de la base de connaissances ───────────────────────────────────

def load_biomechanics_knowledge(
    knowledge_path: str | None = None,
) -> str:
    """Charge le contenu de BIOMECHANICS_KNOWLEDGE.md.

    Cherche dans l'ordre :
    1. Chemin explicite
    2. Racine du projet (../BIOMECHANICS_KNOWLEDGE.md par rapport à ce fichier)
    3. Répertoire courant
    """
    if knowledge_path and Path(knowledge_path).exists():
        return Path(knowledge_path).read_text(encoding="utf-8")

    # Chercher par rapport au fichier actuel
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent
    candidates = [
        project_root / "BIOMECHANICS_KNOWLEDGE.md",
        Path.cwd() / "BIOMECHANICS_KNOWLEDGE.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    raise FileNotFoundError(
        "BIOMECHANICS_KNOWLEDGE.md introuvable. Vérifiez que le fichier "
        "existe à la racine du projet."
    )


# ── Construction du prompt ───────────────────────────────────────────────────

_REFUSAL_PATTERNS = [
    "i'm sorry",
    "i cannot",
    "i can't",
    "i am unable",
    "i'm unable",
    "as an ai",
    "i apologize",
    "cannot assist",
    "can't assist",
    "not able to",
    "i'm not able",
    "against my guidelines",
    "violates",
    "inappropriate",
]


def _is_refusal(text: str) -> bool:
    """Detect if GPT-4o refused to generate the report (content policy)."""
    if not text or len(text) < 10:
        return True
    lower = text.lower().strip()
    # Very short response + refusal pattern = refusal
    if len(text) < 300:
        for pattern in _REFUSAL_PATTERNS:
            if pattern in lower:
                return True
    # Check if there's no score (which means no real report)
    if len(text) < 200 and "/100" not in text:
        return True
    return False


_SYSTEM_INSTRUCTIONS = """CONTEXT: This is a professional biomechanical analysis tool (FORMCHECK by ACHZOD) used by certified fitness coaches to help clients improve their exercise form and prevent injuries. The video frames show standard gym exercises. Analyzing exercise form is the core purpose of this tool.

Tu es un coach biomecanique expert avec 11 certifications (Pre-Script, NASM, ISSA, Precision Nutrition, etc.) et 10 ans d'experience. Tu analyses des videos de musculation pour FORMCHECK by ACHZOD.

Utilise TOUTES les donnees fournies dans le JSON pour rediger un rapport d'analyse biomecanique complet. Le guide d'analyse expert dans le system prompt te donne les principes — applique-les aux donnees mesurees.

NIVEAU D'EXPERTISE EXIGE — CE RAPPORT DOIT IMPRESSIONNER :
Ce rapport sera lu par des pratiquants qui PAIENT pour une analyse experte. Il doit donner l'impression qu'un coach Pre-Script Level 1 certifie a regarde la video pendant 20 minutes, pas qu'un algorithme a genere du texte en 5 secondes. Chaque paragraphe doit contenir des informations que le client ne trouverait PAS en tapant "comment faire un curl" sur Google.

PROFONDEUR BIOMECANIQUE OBLIGATOIRE :
Pour CHAQUE correction, tu dois expliquer la CHAINE CINEMATIQUE complete. Pas juste "tes coudes bougent" mais POURQUOI ils bougent (fatigue du brachial, charge trop lourde, compensation du deltoide anterieur), QUELS muscles sont decharges et lesquels sont surcharges, QUEL est le mecanisme de blessure a long terme (tendinopathie du long biceps, impingement de l'epaule, etc.), et COMMENT le corps compense en cascade (tronc qui balance → rachis lombaire en hyperextension → compression discale L4-L5).

ANALOGIES CONCRETES OBLIGATOIRES :
Chaque correction doit inclure une analogie que le client peut visualiser. Exemple : "Ton tronc s'incline trop en avant — imagine que tu portes un plateau avec des verres, tu veux le garder le plus horizontal possible pour ne rien renverser. C'est pareil pour ta colonne : plus elle reste droite, mieux la charge est repartie sur les bons muscles."

ANALYSE VISUELLE DES FRAMES :
Tu recois des frames extraites de la video. OBSERVE-LES attentivement et commente ce que tu VOIS reellement : position des pieds, grip, trajectoire de la barre/haltere, expression faciale (effort/facilite), position de la tete, engagement du core visible ou non, position des omoplates, supination/pronation des poignets. Ne te contente pas des donnees chiffrees — les frames sont ta source primaire d'information.

PSYCHOLOGIE : Commence TOUJOURS par le positif. Le client doit d'abord voir ce qu'il fait bien avant les corrections. Ca renforce la confiance et l'adhesion aux corrections. Mais les points positifs doivent aussi etre profonds, pas generiques.

FORMAT STRICT DU RAPPORT :

ANALYSE BIOMECANIQUE — [NOM EXERCICE]
Score : [XX]/100

---

RESUME
[5-6 phrases. Resume factuel et dense. Cite les metriques cles mesures — ROM, compensations, symetrie. Donne le diagnostic global : quel est le PATTERN principal du client ? Est-ce un probleme de charge trop lourde, de technique non maitrisee, de mobilite insuffisante, ou de fatigue technique ? Ce paragraphe doit donner au client une vision claire de sa situation en 10 secondes de lecture.]

---

POINTS POSITIFS

1. [Titre court]
[3-4 phrases DENSES. Cite la donnee mesuree. Explique POURQUOI c'est bien biomecaniquement avec le mecanisme precis (quel muscle est recrute, quel leverage est optimise, quel risque est evite). Ne dis pas juste "bonne extension" — explique que l'extension complete permet un etirement maximal du chef long du biceps et un recrutement des fibres a leur longueur optimale sur la courbe tension-longueur.]

2. [Titre court]
[Meme profondeur. Trouve au moins 2-3 points positifs, meme sur une mauvaise execution. Les points positifs doivent etre SPECIFIQUES a ce que tu observes, pas generiques.]

---

AMPLITUDE DE MOUVEMENT (ROM)
[Cite les angles mesures pour chaque articulation cle : genou (min/max/range), hanche, coude, epaule selon l'exercice.]
[Compare chaque angle au referentiel optimal de l'exercice (Section 3 du knowledge base).]
[ROM complet ou incomplet ? Consequences pour le recrutement musculaire.]
[Si les donnees de fatigue montrent une degradation du ROM entre les reps, commente.]
[Analogie concrete : "Un ROM incomplet au squat, c'est comme faire un demi push-up — tu recrutes la moitie des fibres musculaires pour le meme effort articulaire."]

---

CORRECTIONS PRIORITAIRES

1. [Titre]

Donnee mesuree : [Chiffre exact du JSON — angle, degres, pourcentage]
Pourquoi c'est important : [3-4 phrases ACCESSIBLES avec analogie concrete. Explique la consequence pour le client : perte de gains, risque de blessure, pattern de compensation. Le client doit COMPRENDRE pourquoi c'est un probleme, pas juste qu'on lui dit de changer.]
Impact biomecanique : [4-5 phrases PRECISES et TECHNIQUES. Nomme les muscles concernes (chef long, chef court, brachial, brachio-radial, etc.), le mecanisme de blessure exact (tendinopathie, impingement, compression discale), les compensations en chaine cinematique (si le coude bouge → le deltoi de anterieur prend le relai → stress sur le sus-epineux → risque d'impingement sous-acromial). Chaque correction doit montrer que tu comprends l'anatomie fonctionnelle en profondeur.]
Correction : [Cue verbal entre guillemets que le client peut se repeter pendant l'exercice. Puis 3-4 phrases de modification technique avec des reperes tactiles ("sens le contact de tes bras contre tes cotes") et proprioceptifs ("concentre-toi sur la sensation de brulure dans le pic du biceps, pas dans l'epaule").]

2. [Titre]
[Meme structure]

---

ANALYSE DU TEMPO ET DES PHASES

IMPORTANT SUR LE TEMPO : Les donnees de tempo par rep ont ete RETIREES car la mesure automatique n'est pas fiable. NE CITE AUCUNE duree en secondes pour les phases excentrique/concentrique. A la place, base ton analyse sur ce que tu observes dans les frames video. Decris qualitativement : le mouvement est-il controle avec une descente volontaire, ou balistique avec du momentum ? Y a-t-il une pause isometrique en position de contraction maximale (squeeze) ? Le stretch-reflex est-il exploite en bas du mouvement (rebond) ou y a-t-il un arret controle ? L'acceleration est-elle constante ou y a-t-il un sticking point visible ? Commente la qualite du controle moteur global, la stabilite articulaire dynamique, et la coherence du tempo entre les reps (les dernieres reps sont-elles plus rapides/chaotiques que les premieres, signe de fatigue technique ?). Si le Time Under Tension (TUT) total est disponible dans les donnees, cite-le et compare aux normes (30-70s pour l'hypertrophie).

[Si pas de donnees de reps : "Donnees de repetitions insuffisantes pour cette video."]

---

COMPENSATIONS ET BIOMECANIQUE AVANCEE
[UNIQUEMENT si des donnees avancees sont fournies]
[Analyse chaque compensation detectee avec sa valeur mesuree.]
[Bras de levier : pattern quad-dominant ou hip-dominant ? Ratio mesure.]
[Anthropometrie : le ratio femur/torse explique-t-il l'inclinaison du tronc ? Precise si c'est une compensation technique ou une adaptation morphologique normale.]
[Sticking point : angle et implication musculaire. Quel muscle est le facteur limitant ?]
[Sequencage : synchronise ou pattern pathologique (squat morning, good morning) ?]
[Profondeur : par rapport au parallele, consistance inter-reps.]
[Position cervicale et distribution du poids.]

---

PROFIL MORPHOLOGIQUE
[UNIQUEMENT si un profil morphologique est fourni dans les donnees]
[Resume du type morphologique du client et de ses ratios cles]
[Explique comment sa morphologie impacte SPECIFIQUEMENT l'exercice analyse]
[Recommandations de stance/prise personnalisees basees sur ses proportions]
[Si pas de profil morpho fourni, OMETS cette section entierement]

---

EXERCICES CORRECTIFS

1. [Nom de l'exercice] — [Sets x Reps ou duree]
Cible : [Quel probleme detecte dans l'analyse]
Execution detaillee : [3-4 phrases. Position de depart, mouvement, respiration, erreur courante a eviter. Le client doit pouvoir faire l'exercice sans autre reference.]
Quand le faire : [Echauffement, entre les series, en fin de seance, ou jour off]

2. [Meme structure]

3. [Meme structure]

---

DECOMPOSITION DU SCORE
IMPORTANT : cette section est la SEULE exception au format paragraphes. Chaque sous-score DOIT etre sur sa propre ligne au format EXACT "Categorie : XX/YY" suivi d'un saut de ligne puis du paragraphe de justification. Ne fusionne PAS les scores dans le texte.

Securite : [XX]/40
[Justification avec donnee. Alignement articulaire, stabilite, risque de blessure.]

Efficacite technique : [XX]/30
[Justification — cite le ROM, l'amplitude, le recrutement musculaire.]

Controle et tempo : [XX]/20
[Justification — cite le tempo mesure, les phases, le TUT, la constance. Si les donnees de tempo sont absentes ou insuffisantes, attribue un score base sur l'observation visuelle des frames.]

Symetrie : [XX]/10
[Justification — cite le ratio de symetrie mesure. Si la video est filmee de profil et que la symetrie n'est pas evaluable, attribue 5/10 par defaut et mentionne que l'angle ne permet pas une evaluation complete.]

---

POINT BIOMECANIQUE
[8-12 phrases. C'est TA section signature. Insight profond specifique a CET exercice que le client n'a jamais lu nulle part. Parle des chaines musculaires impliquees (chaine anterieure superficielle, ligne brachiale anterieure), des leverages specifiques a l'exercice, de la courbe force-longueur du muscle cible, de l'innervation (nerf musculo-cutane pour le biceps, C5-C6), de la relation entre la position de l'epaule et le recrutement du chef long vs chef court, de l'impact de la supination du poignet sur l'activation du biceps vs le brachio-radial. Mentionne les fascias si pertinent (fascia antebrachial, septum intermusculaire). Si applicable, explique comment la morphologie du client (longueur d'avant-bras, insertion du biceps haute vs basse) impacte sa biomecanique. Ce paragraphe doit impressionner un kinesitherapeute ou un osteopathe qui lirait le rapport.]

RECOMMANDATION D'ANGLE DE CAMERA :
A la fin du rapport, ajoute une section courte :

---

RECOMMANDATION POUR LA PROCHAINE VIDEO
[Indique l'angle de camera optimal pour CET exercice specifique. Exemples :
 Squat/deadlift : vue de profil (laterale) a hauteur de hanche, 2-3 metres de distance
 Bench press : vue laterale + optionnellement vue de dessus pour la trajectoire de la barre
 Curl/lateral raise : vue de face pour la symetrie ET vue de profil pour l'amplitude
 Pull-up/lat pulldown : vue de face pour la symetrie des bras et le valgus
Si la video analysee a ete filmee sous un angle suboptimal, dis-le clairement et explique pourquoi un meilleur angle aurait permis une analyse plus precise.]

CALIBRATION DU SCORE — SOIS INTRANSIGEANT :
Le score doit refleter la REALITE de l'execution. Un score au-dessus de 80 = execution quasi parfaite.
Bareme indicatif :
 90-100 : Execution de competition, quasi parfaite. Reserve aux athletes confirmes.
 75-89 : Bonne execution avec des points a ameliorer. La plupart des pratiquants intermediaires.
 60-74 : Execution passable avec des corrections importantes necessaires.
 40-59 : Execution problematique avec risques de blessure.
 0-39 : Execution dangereuse, stop immediat recommande.
NE GONFLE PAS le score. Un squat avec les genoux qui rentrent (valgus) NE PEUT PAS avoir plus de 65.
Un deadlift avec le dos rond NE PEUT PAS avoir plus de 55. Sois honnete — le client paie pour la verite.

REGLES ABSOLUES :
1. ZERO emoji. ZERO asterisque/markdown. ZERO tiret comme puce (— ou -). Pas de listes a puces. Tout en PARAGRAPHES DENSES. Les seuls numeros autorises sont pour les corrections (1. 2. 3.) et les exercices correctifs. Le reste = prose continue.
2. Tutoie le client.
3. NE CITE QUE les donnees presentes dans le JSON.
4. NE CONCLUS JAMAIS a un valgus du genou a partir de donnees 2D laterales SAUF si la video est filmee de face.
5. Chaque correction justifiee par une donnee mesuree avec le chiffre exact.
6. 2500-4000 mots MINIMUM. Sois EXHAUSTIF. Le client paie pour cette analyse. Un rapport de moins de 2500 mots est INSUFFISANT. Chaque section doit etre dense et riche en information. Pas de phrases de remplissage — chaque phrase doit apporter une information nouvelle ou un angle d'analyse different.
7. L'amplitude (ROM) est OBLIGATOIRE — cite les angles et compare aux normes.
8. Le tempo doit etre analyse qualitativement (controle, momentum, vitesse apparente) — NE CITE PAS de durees en secondes car les mesures automatiques ne sont pas fiables.
9. Les exercices correctifs doivent etre decrits assez precisement pour etre executes sans video.
10. Au moins une analogie concrete par correction pour rendre le rapport accessible.
11. Les POINTS POSITIFS viennent AVANT les corrections. Toujours.
12. Le rapport doit donner l'impression qu'un coach expert a regarde la video en personne, pas qu'un algorithme a genere du texte.
13. Si l'angle de camera ne permet pas d'analyser un parametre, DIS-LE au lieu d'inventer. Honnetete > completude."""


def _estimate_camera_angle(angles: AngleResult) -> str:
    """Estimate the camera angle from landmark positions.
    
    Uses the relative X positions of left vs right body parts.
    If left_shoulder.x ≈ right_shoulder.x → lateral/profile view
    If they're far apart → frontal view
    If one is partially visible → 3/4 view
    """
    if not angles or not angles.frames:
        return "Angle de camera indetermine (pas assez de donnees)"
    
    # Sample frames
    sample = angles.frames[::max(1, len(angles.frames) // 5)]
    shoulder_diffs = []
    hip_diffs = []
    
    for frame in sample:
        # Check shoulder spread
        ls = getattr(frame, 'left_shoulder_abduction', None)
        rs = getattr(frame, 'right_shoulder_abduction', None)
        # We'll use a different approach — look at the raw x-spread
        # from the stats instead
        pass
    
    # Use angle stats (dict[str, AngleStats]) to infer camera angle
    stats = angles.stats if hasattr(angles, 'stats') else {}
    if stats:
        # If both left and right angles have similar ROM → frontal view
        # If one side has much less ROM → profile view (far side occluded)
        l_knee_s = stats.get('left_knee_flexion')
        r_knee_s = stats.get('right_knee_flexion')
        l_elbow_s = stats.get('left_elbow_flexion')
        r_elbow_s = stats.get('right_elbow_flexion')
        
        l_knee = l_knee_s.range_of_motion if l_knee_s else 0
        r_knee = r_knee_s.range_of_motion if r_knee_s else 0
        l_elbow = l_elbow_s.range_of_motion if l_elbow_s else 0
        r_elbow = r_elbow_s.range_of_motion if r_elbow_s else 0
        
        knee_diff = abs(l_knee - r_knee) if l_knee and r_knee else 0
        elbow_diff = abs(l_elbow - r_elbow) if l_elbow and r_elbow else 0
        
        max_rom = max(l_knee, r_knee, l_elbow, r_elbow, 1)
        asymmetry = max(knee_diff, elbow_diff) / max_rom
        
        if asymmetry > 0.4:
            return "Vue LATERALE (profil). Un cote du corps est partiellement masque. Bonne vue pour les exercices bilateraux sagittaux (squat, deadlift, bench). Ne permet PAS de juger le valgus du genou."
        elif asymmetry > 0.15:
            return "Vue 3/4 (semi-profil). Les deux cotes visibles mais a des distances differentes. Analyse de symetrie limitee."
        else:
            return "Vue FRONTALE (face). Les deux cotes du corps sont egalement visibles. Bonne pour detecter la symetrie et le valgus du genou."
    
    return "Angle de camera indetermine"


def _build_analysis_prompt(
    exercise: DetectionResult,
    angles: AngleResult,
    knowledge: str,
    reps: RepSegmentation | None = None,
    confidence: AnalysisConfidence | None = None,
    advanced: Any = None,
    levers: Any = None,
    morpho_profile: dict | None = None,
    adapted_thresholds: dict | None = None,
) -> tuple[str, str]:
    """Construit le system prompt et le user prompt pour l'analyse.

    Returns:
        Tuple (system_prompt, user_prompt).
    """
    angles_data = angles_to_dict(angles)

    # Inject exercise-specific knowledge base
    from analysis.exercise_knowledge import get_kb_prompt_section
    exercise_kb_section = get_kb_prompt_section(exercise.exercise.value) if exercise else ""
    
    system_prompt = knowledge + "\n\n" + _SYSTEM_INSTRUCTIONS
    if exercise_kb_section:
        system_prompt += "\n\n" + exercise_kb_section

    # Build reps section
    reps_section = ""
    if reps and reps.total_reps > 0:
        reps_data = reps.to_dict()
        reps_section = f"""

### Donnees de repetitions
```json
{json.dumps(reps_data, indent=2, ensure_ascii=False)}
```"""

    # Build confidence section
    confidence_section = ""
    if confidence:
        conf_data = confidence.to_dict()
        confidence_section = f"""

### Score de confiance de l'analyse
```json
{json.dumps(conf_data, indent=2, ensure_ascii=False)}
```"""

    # Build advanced biomechanics section
    advanced_section = ""
    if advanced:
        try:
            adv_data = advanced.to_dict()
            # Remove per-frame arrays to save tokens — keep only aggregated metrics
            for section in adv_data.values():
                if isinstance(section, dict):
                    keys_to_remove = [k for k in section if k.endswith("_per_frame")]
                    for k in keys_to_remove:
                        del section[k]
            advanced_section = f"""

### Analyse biomecanique avancee (compensations, colonne, dorsiflexion, centre de masse, bar path, fatigue, TUT)
```json
{json.dumps(adv_data, indent=2, ensure_ascii=False)}
```"""
        except Exception:
            pass

    # Build lever biomechanics section
    levers_section = ""
    if levers:
        try:
            lev_data = levers.to_dict()
            # Remove per-frame arrays
            for section in lev_data.values():
                if isinstance(section, dict):
                    keys_to_remove = [k for k in section if k.endswith("_per_frame")]
                    for k in keys_to_remove:
                        del section[k]
            levers_section = f"""

### Bras de levier, anthropometrie, sticking point, sequencage, profondeur, lockout, position cervicale, distribution du poids
```json
{json.dumps(lev_data, indent=2, ensure_ascii=False)}
```"""
        except Exception:
            pass

    # Build morpho profile section
    morpho_section = ""
    if morpho_profile:
        # Filtrer les champs pertinents pour le LLM
        morpho_for_llm = {
            k: v for k, v in morpho_profile.items()
            if k not in ("photos_analyzed", "analysis_quality", "full_json")
        }
        morpho_section = f"""

### PROFIL MORPHOLOGIQUE DU CLIENT
Le client a un profil morphologique enregistre. Les seuils d'angles ont ete adaptes a sa morphologie.
IMPORTANT : ne penalise PAS les adaptations morphologiques normales (ex: trunk lean prononce si femurs longs).
```json
{json.dumps(morpho_for_llm, indent=2, ensure_ascii=False)}
```"""

    # Build adapted thresholds section
    thresholds_section = ""
    if adapted_thresholds:
        thresholds_section = f"""

### Seuils d'angles adaptes a la morphologie
Ces seuils sont personnalises pour CE client. Utilise-les comme reference au lieu des seuils generiques.
```json
{json.dumps(adapted_thresholds, indent=2, ensure_ascii=False)}
```"""

    # Detect camera angle from landmarks
    camera_angle = _estimate_camera_angle(angles)
    
    user_prompt = f"""Analyse cette video de {exercise.display_name}.

### Angle de camera estime
{camera_angle}

## Donnees de pose estimation

### Statistiques des angles articulaires (toutes les frames)
```json
{json.dumps(angles_data["stats"], indent=2, ensure_ascii=False)}
```

### Detection d'exercice
Exercice detecte : {exercise.display_name}
Confiance : {exercise.confidence:.0%}
Raisonnement : {exercise.reasoning}
{reps_section}
{confidence_section}
{advanced_section}
{levers_section}
{morpho_section}
{thresholds_section}

### Angles frame par frame (echantillon)
```json
{json.dumps(_sample_frames(angles_data["frames"]), indent=2, ensure_ascii=False)}
```

Redige le rapport complet en suivant EXACTEMENT le format demande dans les instructions."""

    return system_prompt, user_prompt


def _sample_frames(frames: list[dict[str, Any]], max_frames: int = 15) -> list[dict[str, Any]]:
    """Échantillonne les frames pour ne pas dépasser la limite de tokens.

    Prend les premières frames, les dernières, et quelques-unes au milieu.
    """
    if len(frames) <= max_frames:
        return frames

    n = len(frames)
    # 5 premières, 5 dernières, 5 réparties au milieu
    indices = set()
    for i in range(min(5, n)):
        indices.add(i)
    for i in range(max(0, n - 5), n):
        indices.add(i)
    step = max(1, n // 5)
    for i in range(0, n, step):
        indices.add(i)
        if len(indices) >= max_frames:
            break

    return [frames[i] for i in sorted(indices)]


# ── Génération via Claude (Anthropic) ────────────────────────────────────────

def generate_report_claude(
    exercise: DetectionResult,
    angles: AngleResult,
    knowledge: str,
    reps: RepSegmentation | None = None,
    confidence: AnalysisConfidence | None = None,
    advanced: Any = None,
    levers: Any = None,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    morpho_profile: dict | None = None,
    adapted_thresholds: dict | None = None,
) -> Report:
    """Génère le rapport via l'API Anthropic (Claude)."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError(
            "Clé API Anthropic requise. Définissez ANTHROPIC_API_KEY."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=key)
    system_prompt, user_prompt = _build_analysis_prompt(
        exercise, angles, knowledge, reps=reps, confidence=confidence,
        advanced=advanced, levers=levers,
        morpho_profile=morpho_profile, adapted_thresholds=adapted_thresholds,
    )

    message = client.messages.create(
        model=model,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_response = message.content[0].text
    return _parse_report(raw_response, exercise, model_name=f"claude:{model}")


def generate_report_openai(
    exercise: DetectionResult,
    angles: AngleResult,
    knowledge: str,
    reps: RepSegmentation | None = None,
    confidence: AnalysisConfidence | None = None,
    advanced: Any = None,
    levers: Any = None,
    api_key: str | None = None,
    model: str = "gpt-4o",
    morpho_profile: dict | None = None,
    adapted_thresholds: dict | None = None,
    video_frames: list[str] | None = None,
) -> Report:
    """Génère le rapport via l'API OpenAI (GPT-4o) — AVEC frames visuelles.
    
    video_frames: list of file paths to raw video frames (JPEG).
    When provided, GPT-4o sees the actual video and can analyze form visually,
    independent of MediaPipe data quality.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("Clé API OpenAI requise. Définissez OPENAI_API_KEY.")

    import base64
    import openai
    import logging
    _logger = logging.getLogger("formcheck.report")

    client = openai.OpenAI(api_key=key)
    system_prompt, user_prompt = _build_analysis_prompt(
        exercise, angles, knowledge, reps=reps, confidence=confidence,
        advanced=advanced, levers=levers,
        morpho_profile=morpho_profile, adapted_thresholds=adapted_thresholds,
    )

    # Build message content — text + optional frames
    user_content = []
    
    # Add video frames if available (GPT-4o Vision)
    if video_frames:
        user_content.append({
            "type": "text",
            "text": (
                "VOICI {} FRAMES DE LA VIDEO (dans l'ordre chronologique). "
                "Utilise-les pour VOIR l'execution reelle du mouvement. "
                "Les donnees numeriques ci-dessous sont issues de MediaPipe et peuvent etre "
                "IMPRECISES (mauvaise personne trackee en gym bonde). "
                "En cas de contradiction entre ce que tu VOIS et les chiffres, "
                "fais confiance a ce que tu VOIS sur les frames. "
                "Analyse la personne au PREMIER PLAN (la plus proche de la camera)."
            ).format(len(video_frames)),
        })
        for i, fpath in enumerate(video_frames):
            try:
                with open(fpath, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/jpeg;base64," + b64,
                        "detail": "low",  # Cost-efficient: ~$0.003 per frame
                    },
                })
            except Exception as e:
                _logger.warning("Failed to load frame %s: %s", fpath, e)
        _logger.info("Sending %d frames to GPT-4o for report generation", len(video_frames))
    
    # Add the text analysis prompt
    user_content.append({"type": "text", "text": user_prompt})
    
    # Attempt with frames first, retry without if GPT-4o refuses
    for attempt in range(2):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=8000,
            temperature=0.3,
            timeout=120,
        )

        raw_response = response.choices[0].message.content or ""
        
        # Detect GPT-4o refusal (content policy)
        if _is_refusal(raw_response):
            _logger.warning(
                "GPT-4o REFUSED report generation (attempt %d): %s",
                attempt + 1, raw_response[:200],
            )
            if attempt == 0 and video_frames:
                # Retry WITHOUT frames — text-only analysis
                _logger.info("Retrying report WITHOUT video frames...")
                user_content = [{"type": "text", "text": user_prompt}]
                continue
            # If still refusing without frames, fall through to return
        break

    return _parse_report(raw_response, exercise, model_name=f"openai:{model}")


def generate_report(
    exercise: DetectionResult,
    angles: AngleResult,
    reps: RepSegmentation | None = None,
    confidence: AnalysisConfidence | None = None,
    advanced: Any = None,
    levers: Any = None,
    knowledge_path: str | None = None,
    provider: str = "auto",
    morpho_profile: dict | None = None,
    adapted_thresholds: dict | None = None,
    video_frames: list[str] | None = None,
) -> Report:
    """Point d'entrée principal pour la génération de rapport.

    Charge la base de connaissances et délègue au provider choisi.
    En mode "auto", essaie Anthropic puis fallback sur OpenAI.
    """
    knowledge = load_biomechanics_knowledge(knowledge_path)

    kwargs = dict(
        exercise=exercise,
        angles=angles,
        knowledge=knowledge,
        reps=reps,
        confidence=confidence,
        advanced=advanced,
        levers=levers,
        morpho_profile=morpho_profile,
        adapted_thresholds=adapted_thresholds,
    )

    if provider == "auto":
        # GPT-4o en priorité — plus fiable et centralise tout sur une seule API
        if os.environ.get("OPENAI_API_KEY", "").strip():
            import logging as _log_mod
            _auto_logger = _log_mod.getLogger("formcheck.report")
            report = generate_report_openai(**kwargs, video_frames=video_frames)
            # If GPT-4o refused, fallback to Claude
            if _is_refusal(report.report_text) and os.environ.get("ANTHROPIC_API_KEY", "").strip():
                _auto_logger.warning("GPT-4o refused → falling back to Claude for report")
                report = generate_report_claude(**kwargs)
            return report
        elif os.environ.get("ANTHROPIC_API_KEY", "").strip():
            return generate_report_claude(**kwargs)
        else:
            raise ValueError("Aucune clé API configurée. Définissez OPENAI_API_KEY ou ANTHROPIC_API_KEY.")
    elif provider == "anthropic":
        return generate_report_claude(**kwargs)
    elif provider == "openai":
        return generate_report_openai(**kwargs)
    else:
        raise ValueError(f"Provider inconnu: {provider}. Utilisez 'auto', 'anthropic' ou 'openai'.")


# ── Parsing du rapport ───────────────────────────────────────────────────────

def _parse_report(
    raw_text: str,
    exercise: DetectionResult,
    model_name: str = "",
) -> Report:
    """Parse le texte brut du LLM en Report structuré.

    Extrait le score, les points positifs, corrections, exercices correctifs.
    """
    report = Report(
        exercise=exercise.exercise.value,
        exercise_display=exercise.display_name,
        score=0,
        report_text=raw_text,
        raw_llm_response=raw_text,
        model_used=model_name,
    )

    lines = raw_text.split("\n")
    current_section = ""

    for line in lines:
        stripped = line.strip()

        # Détection du score — header line "Score : XX/100"
        if "/100" in stripped:
            match = re.search(r"(\d{1,3})\s*/\s*100", stripped)
            if match and report.score == 0:
                report.score = int(match.group(1))

        # Sections
        upper = stripped.upper()
        if "POINTS POSITIFS" in upper or "CE QUI EST BIEN" in upper or "CE QUE TU FAIS BIEN" in upper:
            current_section = "positives"
            continue
        elif "CORRECTIONS PRIORITAIRES" in upper or ("CORRECTION" in upper and "EXERCICE" not in upper):
            current_section = "corrections"
            continue
        elif "EXERCICES CORRECTIFS" in upper or ("EXERCICE" in upper and "CORRECTIF" in upper):
            current_section = "corrective"
            continue
        elif "DECOMPOSITION DU SCORE" in upper or "DECOMPOSITION" in upper:
            current_section = "score"
            continue
        elif "ANALYSE DU TEMPO" in upper:
            current_section = "tempo"
            continue
        elif "COMPENSATIONS" in upper and "AVANCEE" in upper:
            current_section = "advanced"
            continue
        elif "AMPLITUDE" in upper and "MOUVEMENT" in upper:
            current_section = "rom"
            continue
        elif "POINT BIOMECANIQUE" in upper:
            current_section = "biomecanique"
            continue
        elif "RESUME" in upper and len(stripped) < 20:
            current_section = "resume"
            continue

        # Collecter le contenu
        if stripped.startswith(("-", "•")) or (stripped and stripped[0].isdigit() and "." in stripped[:3]):
            clean = stripped.lstrip("-•0123456789. ").strip()
            if not clean:
                continue

            if current_section == "positives":
                report.positives.append(clean)
            elif current_section == "corrections":
                report.corrections.append({"text": clean})
            elif current_section == "corrective":
                report.corrective_exercises.append(clean)

        # Décomposition du score
        if current_section == "score" and ":" in stripped and "/" in stripped:
            score_match = re.search(r"(.+?)\s*:\s*(\d{1,2})\s*/\s*(\d{1,2})", stripped)
            if score_match:
                category = score_match.group(1).strip()
                value = int(score_match.group(2))
                report.score_breakdown[category] = value

    return report


def report_to_dict(report: Report) -> dict[str, Any]:
    """Convertit un Report en dict JSON-sérialisable."""
    return {
        "exercise": report.exercise,
        "exercise_display": report.exercise_display,
        "score": report.score,
        "report_text": report.report_text,
        "positives": report.positives,
        "corrections": report.corrections,
        "corrective_exercises": report.corrective_exercises,
        "score_breakdown": report.score_breakdown,
        "model_used": report.model_used,
    }
