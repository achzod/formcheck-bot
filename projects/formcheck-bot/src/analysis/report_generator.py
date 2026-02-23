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

_SYSTEM_INSTRUCTIONS = """Utilise TOUTES les donnees fournies dans le JSON pour rediger un rapport d'analyse biomecanique complet. Le guide d'analyse expert dans le system prompt te donne les principes — applique-les aux donnees mesurees.

FORMAT STRICT DU RAPPORT :

ANALYSE BIOMECANIQUE — [NOM EXERCICE]
Score : [XX]/100

---

RESUME
[3-4 phrases. Resume factuel. Cite les metriques cles mesures — ROM, tempo, compensations, symetrie. Pas de flatterie.]

---

AMPLITUDE DE MOUVEMENT (ROM)
[Cite les angles mesures pour chaque articulation cle : genou (min/max/range), hanche, coude, epaule selon l'exercice.]
[Compare chaque angle au referentiel optimal de l'exercice (Section 3 du knowledge base).]
[ROM complet ou incomplet ? Consequences pour le recrutement musculaire.]
[Si les donnees de fatigue montrent une degradation du ROM entre les reps, commente.]

---

POINTS POSITIFS

1. [Titre court]
[2-3 phrases. Cite la donnee mesuree. Explique POURQUOI c'est bien biomecaniquement.]

2. [Titre court]
[Meme structure]

---

CORRECTIONS PRIORITAIRES

1. [Titre]

Donnee mesuree : [Chiffre exact du JSON]
Impact biomecanique : [3-4 phrases. Muscles concernes, mecanisme de blessure, pattern de compensation. Sois PRECIS — cite les muscles par leur nom anatomique.]
Correction : [Cue verbal entre guillemets + modification technique en 2-3 phrases.]

2. [Titre]
[Meme structure]

---

ANALYSE DU TEMPO ET DES PHASES

Phase excentrique : [Duree en secondes. Controlee ou trop rapide ? Compare au referentiel (2-4s hypertrophie, 1-2s force). Constante ou degradation inter-reps ?]

Phase concentrique : [Duree. Explosive ou lente ? Evolution au fil des reps.]

Phase isometrique : [Pause en bas ? En haut ? Duree. Presence ou absence de stretch-reflex exploitation.]

Tempo ratio : [Chiffre. Compare a 2:1 / 3:1 optimal. Qu'est-ce que ca revele sur le controle ?]

Consistance : [Variation entre les reps. Degradation = fatigue technique.]

Time Under Tension : [Total si disponible. Compare aux normes (30-60s hypertrophie).]

[Si pas de donnees de reps : "Donnees de repetitions insuffisantes pour cette video."]

---

COMPENSATIONS ET BIOMECANIQUE AVANCEE
[UNIQUEMENT si des donnees avancees sont fournies]
[Analyse chaque compensation detectee avec sa valeur mesuree.]
[Bras de levier : pattern quad-dominant ou hip-dominant ? Ratio mesure.]
[Anthropometrie : le ratio femur/torse explique-t-il l'inclinaison du tronc ?]
[Sticking point : angle et implication musculaire.]
[Sequencage : synchronise ou pattern pathologique (squat morning, good morning) ?]
[Profondeur : par rapport au parallele, consistance inter-reps.]
[Position cervicale et distribution du poids.]

---

EXERCICES CORRECTIFS

1. [Exercice] — [Sets x Reps]
Cible : [Quel probleme detecte]
Execution : [2 phrases precises]

2. [Meme structure]

3. [Meme structure]

---

DECOMPOSITION DU SCORE

Securite : [XX]/40
[Justification avec donnee]

Efficacite technique : [XX]/30
[Justification — cite le ROM, l'amplitude]

Controle et tempo : [XX]/20
[Justification — cite le tempo mesure, les phases, le TUT]

Symetrie : [XX]/10
[Justification — cite le ratio]

---

POINT BIOMECANIQUE
[4-6 phrases. Insight profond specifique a CET exercice. Chaines musculaires, leverages, morphologie, fascias, innervation. Montre que tu as 11 certifications, pas juste un diplome basique.]

REGLES ABSOLUES :
- ZERO emoji. ZERO asterisque/markdown. ZERO tiret comme puce. Numeros uniquement.
- Tutoie le client.
- NE CITE QUE les donnees presentes dans le JSON.
- NE CONCLUS JAMAIS a un valgus du genou a partir de donnees 2D laterales.
- Chaque correction justifiee par une donnee mesuree avec le chiffre exact.
- 1500-2500 mots minimum. Sois exhaustif.
- L'amplitude (ROM) est OBLIGATOIRE — cite les angles et compare aux normes.
- Le tempo DOIT etre analyse phase par phase avec durees en secondes.
- Le rapport doit donner l'impression qu'un coach avec 11 certifications a regarde la video en personne."""


def _build_analysis_prompt(
    exercise: DetectionResult,
    angles: AngleResult,
    knowledge: str,
    reps: RepSegmentation | None = None,
    confidence: AnalysisConfidence | None = None,
    advanced: Any = None,
    levers: Any = None,
) -> tuple[str, str]:
    """Construit le system prompt et le user prompt pour l'analyse.

    Returns:
        Tuple (system_prompt, user_prompt).
    """
    angles_data = angles_to_dict(angles)

    system_prompt = knowledge + "\n\n" + _SYSTEM_INSTRUCTIONS

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

    user_prompt = f"""Analyse cette video de {exercise.display_name}.

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
    )

    message = client.messages.create(
        model=model,
        max_tokens=6000,
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
) -> Report:
    """Génère le rapport via l'API OpenAI (GPT-4)."""
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("Clé API OpenAI requise. Définissez OPENAI_API_KEY.")

    import openai

    client = openai.OpenAI(api_key=key)
    system_prompt, user_prompt = _build_analysis_prompt(
        exercise, angles, knowledge, reps=reps, confidence=confidence,
        advanced=advanced, levers=levers,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=6000,
        temperature=0.3,
    )

    raw_response = response.choices[0].message.content or ""
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
    )

    if provider == "auto":
        if os.environ.get("ANTHROPIC_API_KEY", "").strip():
            return generate_report_claude(**kwargs)
        elif os.environ.get("OPENAI_API_KEY", "").strip():
            return generate_report_openai(**kwargs)
        else:
            raise ValueError("Aucune clé API configurée. Définissez ANTHROPIC_API_KEY ou OPENAI_API_KEY.")
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
        if "POINTS POSITIFS" in upper or "CE QUI EST BIEN" in upper:
            current_section = "positives"
            continue
        elif "CORRECTIONS PRIORITAIRES" in upper or ("CORRECTION" in upper and "EXERCICE" not in upper):
            current_section = "corrections"
            continue
        elif "EXERCICES CORRECTIFS" in upper or ("EXERCICE" in upper and "CORRECTIF" in upper):
            current_section = "corrective"
            continue
        elif "DECOMPOSITION DU SCORE" in upper or ("SCORE" in upper and ("SECURITE" in upper or ":" in stripped)):
            current_section = "score"
            continue
        elif "ANALYSE DU TEMPO" in upper:
            current_section = "tempo"
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
