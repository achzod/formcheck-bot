"""Generateur de rapport HTML premium autonome pour FORMCHECK by ACHZOD.

Produit un fichier HTML 100% autonome (inline CSS, images base64)
avec dark theme premium, gauges visuelles, graphiques d'angles,
animations CSS, responsive mobile-first, ouvrable offline.
"""

from __future__ import annotations

import base64
import html
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis.report_generator import Report


def _img_to_base64(image_path: str) -> str:
    """Encode une image en data URI base64."""
    data = Path(image_path).read_bytes()
    b64 = base64.b64encode(data).decode()
    ext = Path(image_path).suffix.lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64,{b64}"


def _score_color(score: int) -> str:
    if score >= 80:
        return "#2d7a4f"
    elif score >= 60:
        return "#c45a2d"
    return "#c4302d"


def _score_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Tres bien"
    elif score >= 70:
        return "Bien"
    elif score >= 60:
        return "Correct"
    elif score >= 45:
        return "A ameliorer"
    return "Insuffisant"


def _bar_color(category: str) -> str:
    colors = {
        "securite": "#c4302d",
        "efficacite": "#2d5f7a",
        "controle": "#c45a2d",
        "symetrie": "#2d7a4f",
    }
    norm = category.lower().replace("é", "e").replace("è", "e")
    for key, color in colors.items():
        if key in norm:
            return color
    return "#5a4a3a"


# Titres de sections attendus du rapport LLM
_SECTION_TITLES = [
    "ANALYSE BIOMECANIQUE",
    "RESUME",
    "AMPLITUDE DE MOUVEMENT",
    "POINTS POSITIFS",
    "CORRECTIONS PRIORITAIRES",
    "ANALYSE DU TEMPO ET DES PHASES",
    "ANALYSE DU TEMPO ET DES REPETITIONS",
    "INTENSITE DE SERIE",
    "COMPENSATIONS ET BIOMECANIQUE AVANCEE",
    "PROFIL MORPHOLOGIQUE",
    "EXERCICES CORRECTIFS",
    "DECOMPOSITION DU SCORE",
    "ANALYSE AVANCEE",
    "POINT BIOMECANIQUE",
    "RECOMMANDATION POUR LA PROCHAINE VIDEO",
    "RECOMMANDATION",
    "PLAN D'ACTION",
]

# Icones SVG inline par section (petites, legeres, pas d'emojis)
_SECTION_ICONS: dict[str, str] = {
    "RESUME": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "POINTS POSITIFS": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "CORRECTIONS PRIORITAIRES": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    "AMPLITUDE DE MOUVEMENT": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "EXERCICES CORRECTIFS": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>',
    "POINT BIOMECANIQUE": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "PROFIL MORPHOLOGIQUE": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "RECOMMANDATION": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="15" rx="2" ry="2"/><polyline points="17 2 12 7 7 2"/></svg>',
    "INTENSITE DE SERIE": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="13 2 13 9 20 9"/><path d="M13 2L5 12h6v10l8-10h-6z"/></svg>',
    "PLAN D'ACTION": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4"/><path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.4 0 2.73.32 3.9.89"/></svg>',
}


def _get_section_icon(title: str) -> str:
    upper = title.upper()
    for key, icon in _SECTION_ICONS.items():
        if key in upper:
            return icon
    return ""


def _extract_first_name(client_name: str | None) -> str:
    if not client_name:
        return ""
    raw = str(client_name).strip()
    if not raw:
        return ""
    token = raw.split()[0].strip(" -_.,;:()[]{}")
    return token[:32]


def _md_inline_to_html(text: str) -> str:
    """Convert inline markdown (bold, italic) to HTML. Input must already be html-escaped."""
    # **bold** or __bold__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # *italic* or _italic_ (but not inside words)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'<em>\1</em>', text)
    return text


def _format_report_html(report_text: str) -> str:
    """Convertit le texte du rapport LLM en HTML propre, parse par sections."""
    text = html.escape(report_text)
    # Strip ALL markdown artifacts aggressively
    text = re.sub(r'^[\-\*•]\s+', '', text, flags=re.MULTILINE)     # bullet lists
    text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)      # headers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)                     # **bold** → plain
    text = re.sub(r'__(.+?)__', r'\1', text)                         # __bold__ → plain
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)           # *italic* → plain
    text = re.sub(r'`(.+?)`', r'\1', text)                           # `code` → plain
    lines = text.split("\n")
    html_parts: list[str] = []
    in_section = False
    section_count = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div style="height:8px"></div>')
            continue

        # Skip --- separators
        if re.match(r"^-{3,}$", stripped):
            continue

        # Check if this is a section header
        upper = stripped.upper()
        is_header = False
        for title in _SECTION_TITLES:
            if upper.startswith(title):
                is_header = True
                break

        # Score : XX/100
        if re.match(r"^Score\s*:", stripped, re.IGNORECASE):
            html_parts.append(
                f'<p class="score-line">{stripped}</p>'
            )
            continue

        if is_header:
            if in_section:
                html_parts.append("</div></div>")
            section_count += 1
            icon = _get_section_icon(stripped)
            icon_html = f'<span style="margin-right:8px;vertical-align:middle;opacity:0.8">{icon}</span>' if icon else ""
            # Section accent class
            section_cls = "report-section fade-in"
            if "CORRECTIONS" in upper:
                section_cls += " section-corrections"
            elif "CORRECTIFS" in upper or "CORRECTIF" in upper:
                section_cls += " section-correctifs"
            elif "POSITIF" in upper or "RESUME" in upper or "BIOMECANIQUE" in upper:
                section_cls += " section-positive"
            html_parts.append(
                f'<div class="{section_cls}" style="animation-delay:{section_count * 0.05}s">'
                f'<div class="section-header">{icon_html}{stripped}</div>'
                f'<div class="section-body">'
            )
            in_section = True
            continue

        # Sub-headers
        sub_match = re.match(
            r"^(Donnee mesuree|Pourquoi c'est important|Impact biomecanique|Correction|Cible|Execution|Execution detaillee|"
            r"Quand le faire|Phase excentrique|Phase concentrique|Phase isometrique|Tempo ratio|"
            r"Consistance du tempo|Consistance|Time Under Tension)\s*:\s*(.*)$",
            stripped,
        )
        if sub_match:
            label = sub_match.group(1)
            rest = _md_inline_to_html(sub_match.group(2))
            html_parts.append(
                f'<div class="sub-label">{label} :</div>'
                f'<div class="sub-content">{rest}</div>'
            )
            continue

        # Score breakdown lines
        if re.match(r"^(Securite|Efficacite|Controle|Symetrie)", stripped, re.IGNORECASE) and "/" in stripped:
            html_parts.append(f'<p class="score-cat">{stripped}</p>')
            continue

        # Numbered items (corrections, exercices)
        num_match = re.match(r"^(\d+)\.\s*(.*)", stripped)
        if num_match:
            num = num_match.group(1)
            rest = _md_inline_to_html(num_match.group(2))
            html_parts.append(
                f'<div class="numbered-item">'
                f'<span class="item-num">{num}</span>'
                f'<span class="item-text">{rest}</span>'
                f'</div>'
            )
            continue

        # Default paragraph
        html_parts.append(f'<p class="report-p">{_md_inline_to_html(stripped)}</p>')

    if in_section:
        html_parts.append("</div></div>")

    return "\n".join(html_parts)


def _count_known_sections(report_text: str) -> int:
    if not report_text:
        return 0
    count = 0
    for raw_line in report_text.splitlines():
        line = raw_line.strip().upper()
        if not line:
            continue
        for title in _SECTION_TITLES:
            if line.startswith(title):
                count += 1
                break
    return count


def _estimate_breakdown(score: int) -> dict[str, int]:
    total = max(0, min(100, int(score or 0)))
    sec = min(40, int(round(total * 0.40)))
    eff = min(30, int(round(total * 0.30)))
    ctrl = min(20, int(round(total * 0.20)))
    sym = max(0, min(10, total - sec - eff - ctrl))
    return {
        "Securite": sec,
        "Efficacite technique": eff,
        "Controle et tempo": ctrl,
        "Symetrie": sym,
    }


def _normalized_breakdown(report: Report) -> dict[str, int]:
    if report.score_breakdown:
        normalized: dict[str, int] = {}
        aliases = (
            ("Securite", ("securite",)),
            ("Efficacite technique", ("efficacite", "technique")),
            ("Controle et tempo", ("controle", "tempo")),
            ("Symetrie", ("symetrie", "symmetry")),
        )
        for canonical, keys in aliases:
            value = None
            for key, raw_val in report.score_breakdown.items():
                norm_key = str(key).lower().replace("é", "e").replace("è", "e")
                if all(token in norm_key for token in keys):
                    try:
                        value = int(raw_val)
                    except Exception:
                        value = 0
                    break
            if value is None:
                value = 0
            max_value = 40 if canonical == "Securite" else 30 if canonical == "Efficacite technique" else 20 if canonical == "Controle et tempo" else 10
            normalized[canonical] = max(0, min(max_value, int(value)))
        return normalized
    return _estimate_breakdown(report.score)


def _build_client_intro_card(
    report: Report,
    pipeline_result: Any | None,
    client_name: str | None,
) -> str:
    first_name = _extract_first_name(client_name)
    if first_name:
        intro = "Salut {}, voici ton rapport personnalise, section par section.".format(html.escape(first_name))
    else:
        intro = "Salut, voici ton rapport personnalise, section par section."

    reps_total = 0
    intensity_score = 0
    intensity_label = "indeterminee"
    avg_rest = 0.0
    confidence_score = 0
    detection_conf = 0.0

    if pipeline_result and getattr(pipeline_result, "reps", None):
        reps = pipeline_result.reps
        reps_total = int(getattr(reps, "total_reps", 0) or 0)
        intensity_score = int(getattr(reps, "intensity_score", 0) or 0)
        intensity_label = str(getattr(reps, "intensity_label", "indeterminee") or "indeterminee")
        avg_rest = float(getattr(reps, "avg_inter_rep_rest_s", 0.0) or 0.0)
    if pipeline_result and getattr(pipeline_result, "confidence", None):
        confidence_score = int(getattr(pipeline_result.confidence, "overall_score", 0) or 0)
    if pipeline_result and getattr(pipeline_result, "detection", None):
        detection_conf = float(getattr(pipeline_result.detection, "confidence", 0.0) or 0.0)

    metrics: list[str] = []
    if reps_total > 0:
        metrics.append("{} reps detectees".format(reps_total))
    if intensity_score > 0:
        metrics.append("Intensite {} /100 ({})".format(intensity_score, html.escape(intensity_label)))
    elif reps_total >= 2:
        metrics.append("Intensite limitee sur cette prise")
    if avg_rest > 0:
        metrics.append("Repos inter-reps moyen {:.2f}s".format(avg_rest))
    if confidence_score > 0:
        metrics.append("Confiance analyse {} /100".format(confidence_score))
    if detection_conf > 0:
        metrics.append("Confiance detection {:.0f}%".format(detection_conf * 100.0))

    key_metrics = " | ".join(metrics) if metrics else "Analyse complete generee a partir de ta video."

    return """
    <div class="card fade-in client-intro" style="animation-delay:0.18s">
        <div class="card-header">Synthese Client</div>
        <p class="report-p" style="margin-top:4px">{intro}</p>
        <p class="report-p">{exercise} — score global <strong>{score}/100</strong>.</p>
        <p class="report-p" style="color:#5a4a3a">{key_metrics}</p>
    </div>
    """.format(
        intro=intro,
        exercise=html.escape(report.exercise_display or "Exercice"),
        score=max(0, min(100, int(report.score or 0))),
        key_metrics=key_metrics,
    )


def _build_deterministic_report_text(
    report: Report,
    pipeline_result: Any | None,
    client_name: str | None,
) -> str:
    def _safe_num(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except Exception:
            return default

    def _rom(stats: dict[str, Any], key: str) -> float:
        item = stats.get(key)
        if not item:
            return 0.0
        return _safe_num(getattr(item, "range_of_motion", 0.0), 0.0)

    def _max(stats: dict[str, Any], key: str) -> float:
        item = stats.get(key)
        if not item:
            return 0.0
        return _safe_num(getattr(item, "max_value", 0.0), 0.0)

    def _exercise_profile(slug: str) -> str:
        low = slug.lower()
        if any(k in low for k in ("squat", "lunge", "deadlift", "rdl", "hip_thrust")):
            return "lower"
        if any(k in low for k in ("press", "curl", "row", "pulldown", "pullup", "dip", "raise", "tricep")):
            return "upper"
        return "mixed"

    first_name = _extract_first_name(client_name)
    greeting = "Salut {},".format(first_name) if first_name else "Salut,"

    reps_total = 0
    reps_complete = 0
    reps_partial = 0
    intensity_score = 0
    intensity_label = "indeterminee"
    avg_rest = 0.0
    intensity_confidence = ""
    if pipeline_result and getattr(pipeline_result, "reps", None):
        reps = pipeline_result.reps
        reps_total = int(getattr(reps, "total_reps", 0) or 0)
        reps_complete = int(getattr(reps, "complete_reps", 0) or 0)
        reps_partial = int(getattr(reps, "partial_reps", 0) or 0)
        intensity_score = int(getattr(reps, "intensity_score", 0) or 0)
        intensity_label = str(getattr(reps, "intensity_label", "indeterminee") or "indeterminee")
        avg_rest = float(getattr(reps, "avg_inter_rep_rest_s", 0.0) or 0.0)
        intensity_confidence = str(getattr(reps, "intensity_confidence", "") or "")
    tempo_consistency = 0.0
    avg_rom = 0.0
    rom_degradation = 0.0
    if pipeline_result and getattr(pipeline_result, "reps", None):
        rep_obj = pipeline_result.reps
        tempo_consistency = _safe_num(getattr(rep_obj, "tempo_consistency", 0.0), 0.0)
        avg_rom = _safe_num(getattr(rep_obj, "avg_rom", 0.0), 0.0)
        rom_degradation = _safe_num(getattr(rep_obj, "rom_degradation", 0.0), 0.0)

    confidence_score = 0
    if pipeline_result and getattr(pipeline_result, "confidence", None):
        confidence_score = _safe_int(getattr(pipeline_result.confidence, "overall_score", 0), 0)

    angle_stats: dict[str, Any] = {}
    if pipeline_result and getattr(pipeline_result, "angles", None):
        angle_stats = getattr(pipeline_result.angles, "stats", {}) or {}

    knee_rom = max(_rom(angle_stats, "left_knee_flexion"), _rom(angle_stats, "right_knee_flexion"))
    hip_rom = max(_rom(angle_stats, "left_hip_flexion"), _rom(angle_stats, "right_hip_flexion"))
    elbow_rom = max(_rom(angle_stats, "left_elbow_flexion"), _rom(angle_stats, "right_elbow_flexion"))
    shoulder_flex_rom = max(_rom(angle_stats, "left_shoulder_flexion"), _rom(angle_stats, "right_shoulder_flexion"))
    shoulder_abd_rom = max(_rom(angle_stats, "left_shoulder_abduction"), _rom(angle_stats, "right_shoulder_abduction"))
    trunk_rom = _rom(angle_stats, "trunk_inclination")
    max_knee_valgus = max(_max(angle_stats, "left_knee_valgus"), _max(angle_stats, "right_knee_valgus"))

    hip_shift = 0.0
    lateral_lean = 0.0
    butt_wink_deg = 0.0
    tut_s = 0.0
    fatigue_index = 0.0
    if pipeline_result and getattr(pipeline_result, "advanced", None):
        advanced = pipeline_result.advanced
        hip_shift = _safe_num(getattr(getattr(advanced, "compensations", None), "max_hip_shift", 0.0), 0.0)
        lateral_lean = _safe_num(getattr(getattr(advanced, "compensations", None), "max_lateral_lean", 0.0), 0.0)
        butt_wink_deg = _safe_num(getattr(getattr(advanced, "compensations", None), "butt_wink_degrees", 0.0), 0.0)
        tut_ms = _safe_num(getattr(getattr(advanced, "time_under_tension", None), "total_tut_ms", 0.0), 0.0)
        tut_s = tut_ms / 1000.0 if tut_ms > 0 else 0.0
        fatigue_index = _safe_num(getattr(getattr(advanced, "fatigue", None), "fatigue_index", 0.0), 0.0)

    lever_ratio = 0.0
    sticking_depth_pct = 0.0
    sequencing_pattern = ""
    if pipeline_result and getattr(pipeline_result, "levers", None):
        levers = pipeline_result.levers
        lever_ratio = _safe_num(
            getattr(getattr(levers, "levers", None), "knee_hip_lever_ratio", 0.0),
            0.0,
        )
        sticking_depth_pct = _safe_num(getattr(getattr(levers, "sticking_point", None), "sticking_point_depth_pct", 0.0), 0.0)
        sequencing_pattern = str(getattr(getattr(levers, "sequencing", None), "pattern", "") or "")

    positives = [item.strip() for item in report.positives if item and item.strip()]
    if not positives:
        positives = []
        if reps_total >= 4:
            positives.append(
                "Tu as une serie exploitable ({}/{} reps completes), ce qui permet une lecture fiable du pattern moteur."
                .format(reps_complete or reps_total, reps_total)
            )
        if tempo_consistency > 0:
            positives.append(
                "La constance de tempo est correcte ({:.0f}%), bon signe de controle neuromusculaire."
                .format(tempo_consistency * 100.0)
            )
        if confidence_score >= 70:
            positives.append(
                "La confiance d'analyse est elevee ({}/100), donc les recommandations sont actionnables des la prochaine seance."
                .format(confidence_score)
            )
        if not positives:
            positives = [
                "Tu as une base technique exploitable sur cet exercice.",
                "La serie reste lisible, ce qui permet des corrections efficaces des la prochaine seance.",
            ]

    corrections: list[dict[str, str]] = []
    for item in report.corrections:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "") or "").strip()
        issue = str(item.get("issue", "") or item.get("why", "") or item.get("text", "") or "").strip()
        impact = str(item.get("impact", "") or "").strip()
        fix = str(item.get("fix", "") or item.get("cue", "") or "").strip()
        if title or issue or impact or fix:
            corrections.append(
                {
                    "title": title or "Correction technique",
                    "issue": issue,
                    "impact": impact,
                    "fix": fix,
                }
            )
    if not corrections:
        profile = _exercise_profile(report.exercise or report.exercise_display)
        corrections = []
        if profile == "lower":
            if max_knee_valgus > 8:
                corrections.append(
                    {
                        "title": "Alignement genou",
                        "issue": "Valgus dynamique observe jusqu'a {:.1f} deg.".format(max_knee_valgus),
                        "impact": "Le genou qui rentre surcharge le compartiment interne et deplace la contrainte hors de l'axe de force ideal.",
                        "fix": "Cue: pousse le sol et garde le genou dans l'axe du 2e orteil sur toute la descente.",
                    }
                )
            if lateral_lean > 8:
                corrections.append(
                    {
                        "title": "Stabilite du tronc",
                        "issue": "Inclinaison laterale max {:.1f} deg.".format(lateral_lean),
                        "impact": "Le tronc qui penche transfere la charge sur un cote et cree une asymetrie cumulative.",
                        "fix": "Cue: verrouille le gainage avant chaque rep et garde les cotes symetriques.",
                    }
                )
            if butt_wink_deg > 8:
                corrections.append(
                    {
                        "title": "Controle bassin en bas de mouvement",
                        "issue": "Retroversion en bas de rep ({:.1f} deg).".format(butt_wink_deg),
                        "impact": "La bascule pelvienne en profondeur augmente le stress lombaire si elle apparait sous charge lourde.",
                        "fix": "Cue: coupe 2-3 cm d'amplitude si necessaire et garde le bassin neutre sous controle.",
                    }
                )
        elif profile == "upper":
            if trunk_rom > 15:
                corrections.append(
                    {
                        "title": "Compensation du tronc",
                        "issue": "Tronc mobile (ROM {:.1f} deg).".format(trunk_rom),
                        "impact": "Le balancier du tronc decharge le muscle cible et augmente la charge de cisaillement sur la zone lombaire.",
                        "fix": "Cue: verrouille le bassin et laisse bouger uniquement l'articulation cible.",
                    }
                )
            if elbow_rom > 0 and elbow_rom < 35 and "press" not in (report.exercise or ""):
                corrections.append(
                    {
                        "title": "Amplitude active",
                        "issue": "ROM coude limite ({:.1f} deg).".format(elbow_rom),
                        "impact": "Une amplitude partielle limite le temps sous tension efficace et peut freiner la progression hypertrophique.",
                        "fix": "Cue: garde une excentrique plus longue pour atteindre une amplitude plus complete sans tricher.",
                    }
                )
        if not corrections:
            corrections = [
                {
                    "title": "Regularite de trajectoire",
                    "issue": "La trajectoire varie entre les repetitions.",
                    "impact": "La variation de trajectoire reduit la tension utile sur le muscle cible et augmente la compensation.",
                    "fix": "Cue: garde exactement la meme ligne sur chaque rep, sans deviation.",
                },
                {
                    "title": "Controle du tempo",
                    "issue": "Le rythme n'est pas assez stable entre debut et fin de serie.",
                    "impact": "Un tempo instable diminue le temps sous tension utile et degrade la qualite mecanique.",
                    "fix": "Cue: ralentis la phase excentrique et verrouille la position avant la rep suivante.",
                },
            ]

    breakdown = _normalized_breakdown(report)
    exercise = report.exercise_display or "Exercice"
    score = max(0, min(100, int(report.score or 0)))
    profile = _exercise_profile(report.exercise or report.exercise_display)

    lines: list[str] = []
    lines.append("ANALYSE BIOMECANIQUE — {}".format(exercise))
    lines.append("Score : {}/100".format(score))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("RESUME")
    resume = "{} tu as realise une video de {} avec un score de {}/100.".format(greeting, exercise, score)
    if reps_total > 0:
        resume += " {} repetitions detectees ({} completes, {} partielles).".format(reps_total, reps_complete, reps_partial)
    if intensity_score > 0:
        resume += " Intensite {} /100 ({})".format(intensity_score, intensity_label)
        if avg_rest > 0:
            resume += ", repos moyen {:.2f}s.".format(avg_rest)
        else:
            resume += "."
    metric_bits: list[str] = []
    if knee_rom > 0:
        metric_bits.append("ROM genou {:.1f} deg".format(knee_rom))
    if hip_rom > 0:
        metric_bits.append("ROM hanche {:.1f} deg".format(hip_rom))
    if elbow_rom > 0 and profile == "upper":
        metric_bits.append("ROM coude {:.1f} deg".format(elbow_rom))
    if shoulder_flex_rom > 0 and profile == "upper":
        metric_bits.append("ROM epaule {:.1f} deg".format(max(shoulder_flex_rom, shoulder_abd_rom)))
    if metric_bits:
        resume += " Mesures cles: {}.".format(", ".join(metric_bits[:3]))
    lines.append(resume)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("POINTS POSITIFS")
    for idx, item in enumerate(positives[:4], start=1):
        lines.append("{}. {}".format(idx, item))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("AMPLITUDE DE MOUVEMENT")
    if profile == "lower":
        rom_sentence = "ROM bas du corps: genou {:.1f} deg, hanche {:.1f} deg.".format(knee_rom, hip_rom)
    elif profile == "upper":
        shoulder_ref = max(shoulder_flex_rom, shoulder_abd_rom)
        rom_sentence = "ROM haut du corps: coude {:.1f} deg, epaule {:.1f} deg.".format(elbow_rom, shoulder_ref)
    else:
        rom_sentence = "ROM observe: genou {:.1f} deg, hanche {:.1f} deg, coude {:.1f} deg.".format(knee_rom, hip_rom, elbow_rom)
    lines.append(rom_sentence)
    if avg_rom > 0:
        lines.append("ROM moyen par rep {:.1f} deg avec degradation {:.1f}% sur la fin de serie.".format(avg_rom, rom_degradation))
    else:
        lines.append("Objectif: stabiliser l'amplitude sur toutes les repetitions pour conserver une tension musculaire constante.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("CORRECTIONS PRIORITAIRES")
    for idx, corr in enumerate(corrections[:4], start=1):
        lines.append("{}. {}".format(idx, corr.get("title", "Correction")))
        if corr.get("issue"):
            lines.append("Donnee mesuree: {}".format(corr["issue"]))
        if corr.get("impact"):
            lines.append("Impact biomecanique: {}".format(corr["impact"]))
        if corr.get("fix"):
            lines.append("Correction: {}".format(corr["fix"]))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("ANALYSE DU TEMPO ET DES PHASES")
    tempo_line = "Le focus est une execution reguliere: excentrique controlee, transition propre, concentrique sans perte d'alignement."
    if tempo_consistency > 0:
        tempo_line += " Consistance mesuree {:.0f}%.".format(tempo_consistency * 100.0)
    if tut_s > 0:
        tempo_line += " TUT total {:.1f}s.".format(tut_s)
    lines.append(tempo_line)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("INTENSITE DE SERIE (DENSITE)")
    if intensity_score > 0:
        text = "Intensite estimee a {}/100 ({})".format(intensity_score, intensity_label)
        if avg_rest > 0:
            text += ", repos inter-reps moyen {:.2f}s".format(avg_rest)
        if intensity_confidence:
            text += " (confiance: {})".format(intensity_confidence)
        text += "."
        lines.append(text)
    else:
        lines.append("Intensite non estimable de facon robuste sur cette video.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("COMPENSATIONS ET BIOMECANIQUE AVANCEE")
    comp_bits: list[str] = []
    if hip_shift > 0:
        comp_bits.append("hip shift max {:.3f}".format(hip_shift))
    if lateral_lean > 0:
        comp_bits.append("lean lateral {:.1f} deg".format(lateral_lean))
    if butt_wink_deg > 0:
        comp_bits.append("butt wink {:.1f} deg".format(butt_wink_deg))
    if fatigue_index > 0:
        comp_bits.append("fatigue index {:.2f}".format(fatigue_index))
    if sticking_depth_pct > 0:
        comp_bits.append("sticking point {:.0f}% de l'amplitude".format(sticking_depth_pct))
    if comp_bits:
        lines.append("Compensations a surveiller: {}.".format(", ".join(comp_bits[:5])))
    else:
        lines.append(
            "Compensations a surveiller: variation de trajectoire, perte de controle en fin de serie, et baisse de stabilite quand la fatigue augmente."
        )
    if sequencing_pattern:
        lines.append("Sequencage detecte: {}.".format(sequencing_pattern.replace("_", " ")))

    if report.corrective_exercises:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("EXERCICES CORRECTIFS")
        for idx, item in enumerate(report.corrective_exercises[:4], start=1):
            lines.append("{}. {}".format(idx, item))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("DECOMPOSITION DU SCORE")
    lines.append("Securite: {}/40".format(breakdown.get("Securite", 0)))
    lines.append("Justification: score base sur alignement et risque articulaire observe.")
    lines.append("Efficacite technique: {}/30".format(breakdown.get("Efficacite technique", 0)))
    lines.append("Justification: score base sur qualite du mouvement et exploitation du ROM.")
    lines.append("Controle et tempo: {}/20".format(breakdown.get("Controle et tempo", 0)))
    lines.append("Justification: score base sur regularite d'execution sur l'ensemble de la serie.")
    lines.append("Symetrie: {}/10".format(breakdown.get("Symetrie", 0)))
    lines.append("Justification: score base sur l'equilibre global gauche/droite visible sur la prise.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("POINT BIOMECANIQUE")
    biomech = (
        "Ta progression depend de la constance mecanique: meme trajectoire, meme amplitude, meme intention motrice a chaque rep. "
        "C'est ce qui permet de charger plus sans compenser et de reduire le risque de surcharge articulaire."
    )
    if lever_ratio > 0:
        biomech += " Ratio levier genou/hanche {:.2f}: il guide la repartition quadriceps/chaine posterieure et explique ton pattern dominant.".format(
            lever_ratio
        )
    if profile == "upper" and trunk_rom > 0:
        biomech += " Quand le tronc bouge de {:.1f} deg, la tension quitte le muscle cible et part vers la compensation.".format(trunk_rom)
    if profile == "lower" and max_knee_valgus > 0:
        biomech += " Le valgus max {:.1f} deg doit rester sous controle pour proteger l'axe genou-cheville sous fatigue.".format(max_knee_valgus)
    lines.append(biomech)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("PLAN D'ACTION")
    if profile == "lower":
        lines.append("1. Verrouille le gainage avant chaque rep pour garder bassin et tronc stables.")
        lines.append("2. Controle la descente et maintiens le genou dans l'axe du pied sur toute l'amplitude.")
        lines.append("3. Garde la meme amplitude de la rep 1 a la rep finale pour limiter la derive de fatigue.")
    elif profile == "upper":
        lines.append("1. Fixe le tronc et elimine tout momentum pour isoler le muscle cible.")
        lines.append("2. Ralentis l'excentrique et marque une transition propre avant de repartir.")
        lines.append("3. Maintiens la trajectoire identique sur chaque rep pour eviter la compensation articulaire.")
    else:
        lines.append("1. Garde exactement la meme execution sur toutes les reps de la prochaine serie.")
        lines.append("2. Ralentis volontairement la phase excentrique pour mieux controler la tension.")
        lines.append("3. Filme une nouvelle serie avec angle fixe pour valider la correction.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("RECOMMANDATION POUR LA PROCHAINE VIDEO")
    if profile == "upper":
        lines.append("Camera fixe, vue de face ou 3/4 face pour la symetrie scapulaire, coudes et trajectoire des bras.")
    else:
        lines.append("Camera fixe, corps entier visible, angle lateral a hauteur de hanche pour une lecture biomecanique plus precise.")
    return "\n".join(lines).strip()


def _report_quality_score(report_text: str) -> int:
    text = (report_text or "").strip()
    if not text:
        return 0
    sections = _count_known_sections(text)
    numeric_tokens = len(re.findall(r"\b\d+(?:[.,]\d+)?(?:\s*(?:%|s|deg|/100))?\b", text))
    length_score = min(24, len(text) // 120)
    section_score = min(56, sections * 7)
    numeric_score = min(20, numeric_tokens)
    return int(section_score + numeric_score + length_score)


_FRAME_LABELS = {
    "start": "Position de depart",
    "mid": "Pic de contraction / Amplitude max",
    "end": "Lockout / Retour position haute",
    "quarter": "Descente (1/4)",
    "three_quarter": "Remontee (3/4)",
}


def generate_html_report(
    report: Report,
    annotated_frames: dict[str, str],
    analysis_id: str | None = None,
    pipeline_result: Any | None = None,
    client_name: str | None = None,
) -> tuple[str, str, str]:
    """Genere un rapport HTML premium autonome.

    Args:
        report: Rapport d'analyse du LLM.
        annotated_frames: Dict {label: chemin_image} des frames annotees.
        analysis_id: ID unique de l'analyse. Auto-genere si None.
        pipeline_result: Resultat du pipeline (optionnel, pour graphiques).

    Returns:
        Tuple (html_content, analysis_id, token).
    """
    if not analysis_id:
        analysis_id = uuid.uuid4().hex[:12]
    token = uuid.uuid4().hex[:16]

    score = report.score
    score_col = _score_color(score)
    score_lbl = _score_label(score)
    exercise_name = report.exercise_display
    now = datetime.now().strftime("%d/%m/%Y a %H:%M")

    # ── Gauge SVG pour le score principal ─────────────────────────────────
    gauge_pct = min(100, max(0, score))
    gauge_circumference = 2 * 3.14159 * 54  # r=54
    gauge_offset = gauge_circumference * (1 - gauge_pct / 100)

    gauge_svg = f'''
    <div style="position:relative;width:200px;height:200px;margin:0 auto">
        <div style="position:absolute;inset:0;border-radius:50%;box-shadow:0 0 40px {score_col}20,0 0 80px {score_col}10;pointer-events:none"></div>
        <svg viewBox="0 0 120 120" style="width:200px;height:200px;display:block">
            <circle cx="60" cy="60" r="54" fill="none" stroke="#d5cfc5" stroke-width="8"/>
            <circle cx="60" cy="60" r="54" fill="none" stroke="{score_col}" stroke-width="8"
                stroke-linecap="round" stroke-dasharray="{gauge_circumference}"
                stroke-dashoffset="{gauge_offset}"
                transform="rotate(-90 60 60)"
                style="transition:stroke-dashoffset 1.5s ease-out;filter:drop-shadow(0 0 6px {score_col}80)"/>
            <text x="60" y="53" text-anchor="middle" fill="{score_col}"
                font-size="30" font-weight="900" font-family="Inter,system-ui,sans-serif">{score}</text>
            <text x="60" y="70" text-anchor="middle" fill="#8a8070"
                font-size="10" font-family="Inter,system-ui,sans-serif">/100</text>
        </svg>
    </div>'''

    # ── Sub-score gauges ──────────────────────────────────────────────────
    breakdown_html = ""
    breakdown_config = [
        ("Securite", "securite", 40, "Alignement, risque blessure, stabilite"),
        ("Efficacite technique", "efficacite", 30, "ROM, amplitude, recrutement musculaire"),
        ("Controle et tempo", "controle", 20, "Temps excentrique/concentrique, constance"),
        ("Symetrie", "symetrie", 10, "Equilibre gauche/droite"),
    ]

    if report.score_breakdown:
        gauges = []
        for label, key, max_val, description in breakdown_config:
            val = 0
            for k, v in report.score_breakdown.items():
                norm_k = k.lower().replace("é", "e").replace("è", "e").replace("&", "et")
                if key in norm_k:
                    val = v
                    break
            pct = min(100, int(val / max_val * 100)) if max_val else 0
            color = _bar_color(key)

            gauges.append(f'''
            <div class="sub-gauge">
                <div class="sub-gauge-info">
                    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">
                        <div class="sub-gauge-label">{label}</div>
                        <div style="color:{color};font-weight:700;font-size:0.95em">{val}<span style="color:#8a8070;font-weight:400;font-size:0.85em">/{max_val}</span> <span style="color:#8a8070;font-size:0.8em">{pct}%</span></div>
                    </div>
                    <div class="sub-gauge-bar">
                        <div class="sub-gauge-fill" style="width:{pct}%;background:linear-gradient(90deg,{color},{color}cc)"></div>
                    </div>
                    <div class="sub-gauge-desc">{description}</div>
                </div>
            </div>''')

        breakdown_html = f'''
        <div class="card fade-in" style="animation-delay:0.2s">
            <div class="card-header">Decomposition du score</div>
            {"".join(gauges)}
        </div>'''

    # ── Frames HTML ───────────────────────────────────────────────────────
    frames_html = ""
    if annotated_frames:
        frame_items = []
        # Show mid (peak contraction) first, then end (lockout/return), skip start
        ordered_labels = ["mid", "end"]
        for label in ordered_labels:
            path = annotated_frames.get(label)
            if not path:
                continue
            if not Path(path).exists():
                continue
            b64 = _img_to_base64(path)
            # Try exercise-specific labels from phase database
            caption = _FRAME_LABELS.get(label, label.replace("_", " ").title())
            try:
                from analysis.exercise_phases import get_phase
                _ex_val = ""
                if pipeline_result and hasattr(pipeline_result, 'detection'):
                    _ex_val = pipeline_result.detection.exercise.value
                _phase = get_phase(_ex_val) if _ex_val else None
                if _phase:
                    if label == "mid":
                        caption = _phase.peak_label
                    elif label == "end":
                        caption = _phase.return_label
            except (ImportError, Exception):
                pass
            frame_items.append(f'''
            <div class="frame-item">
                <img src="{b64}" alt="{html.escape(caption)}" loading="lazy">
                <div class="frame-caption">{html.escape(caption)}</div>
            </div>''')

        if frame_items:
            frames_html = f'''
        <div class="card fade-in" style="animation-delay:0.3s">
            <div class="card-header">Frames cles annotees</div>
            <div class="frames-grid">
                {"".join(frame_items)}
            </div>
        </div>'''

    # ── Graphique d'angle par rep (si donnees disponibles) ────────────────
    angle_chart_html = ""
    if pipeline_result and hasattr(pipeline_result, 'angles') and pipeline_result.angles:
        angle_chart_html = _build_angle_chart(pipeline_result)

    # ── Reps timeline (si donnees disponibles) ────────────────────────────
    reps_timeline_html = ""
    if pipeline_result and hasattr(pipeline_result, 'reps') and pipeline_result.reps:
        reps_timeline_html = _build_reps_timeline(pipeline_result.reps)

    # ── Section Profil Morphologique (si donnees disponibles) ─────────────
    morpho_html = ""
    morpho_data = None
    if pipeline_result and hasattr(pipeline_result, 'morpho_profile') and pipeline_result.morpho_profile:
        morpho_data = pipeline_result.morpho_profile
    if morpho_data:
        morpho_html = _build_morpho_section(morpho_data)

    # ── Rapport client: fallback deterministic si sortie LLM trop faible ──
    raw_report_text = (report.report_text or "").strip()
    quality_score = _report_quality_score(raw_report_text)
    use_deterministic_fallback = quality_score < 56
    report_text = (
        _build_deterministic_report_text(report, pipeline_result, client_name)
        if use_deterministic_fallback
        else raw_report_text
    )
    report_html = _format_report_html(report_text)
    client_intro_html = _build_client_intro_card(report, pipeline_result, client_name)

    # ── Full HTML ─────────────────────────────────────────────────────────
    html_content = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=5.0">
<title>FORMCHECK — {html.escape(exercise_name)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
/* ── Reset & Base ─────────────────────────────────────────── */
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{
    background:#f5f0e8;
    color:#1a1a1a;
    font-family:'Inter',system-ui,-apple-system,BlinkMacSystemFont,sans-serif;
    line-height:1.75;
    font-size:15px;
    -webkit-font-smoothing:antialiased;
    -moz-osx-font-smoothing:grayscale
}}
@media(max-width:600px){{body{{font-size:14px;line-height:1.7}}}}

/* ── Container ────────────────────────────────────────────── */
.container{{max-width:780px;margin:0 auto;padding:24px 20px}}
@media(max-width:600px){{.container{{padding:16px 12px}}}}

/* ── Animations ───────────────────────────────────────────── */
@keyframes fadeIn{{
    from{{opacity:0;transform:translateY(12px)}}
    to{{opacity:1;transform:translateY(0)}}
}}
@keyframes pulse{{
    0%,100%{{opacity:1}}
    50%{{opacity:0.7}}
}}
.fade-in{{animation:fadeIn 0.5s ease-out both}}

/* ── Header ───────────────────────────────────────────────── */
.header{{
    text-align:center;
    padding:40px 0 28px;
    border-bottom:1px solid #d5cfc5;
    position:relative
}}
.header::before{{
    content:'';
    position:absolute;
    top:0;left:50%;transform:translateX(-50%);
    width:200px;height:2px;
    background:linear-gradient(90deg,transparent,#1a1a1a,transparent);
    border-radius:1px
}}
.brand-label{{
    font-size:0.75em;letter-spacing:5px;color:#8a8070;
    text-transform:uppercase;margin-bottom:10px
}}
.brand-name{{font-size:2em;font-weight:800;margin-bottom:2px;letter-spacing:2px}}
.brand-name .fc{{color:#1a1a1a}}
.brand-name .ch{{color:#1a1a1a}}
.brand-by{{color:#8a8070;font-size:0.78em;letter-spacing:3px;margin-bottom:24px}}
.exercise-name{{font-size:1.35em;color:#1a1a1a;font-weight:700;margin-bottom:16px}}
.score-label{{color:#8a8070;font-size:0.82em;margin-top:12px;letter-spacing:1px}}
.header-date{{color:#8a8070;font-size:0.78em;margin-top:16px}}

/* ── Cards ────────────────────────────────────────────────── */
.card{{
    background:#ece7dd;
    border:1px solid #d5cfc5;
    border-radius:16px;
    padding:24px;
    margin:20px 0;
    overflow:hidden
}}
.client-intro{{border-left:3px solid #5a4a3a}}
.card-header{{
    font-size:0.95em;
    color:#1a1a1a;
    text-transform:uppercase;
    letter-spacing:2.5px;
    font-weight:700;
    padding-bottom:14px;
    margin-bottom:16px;
    border-bottom:1px solid #d5cfc5
}}

/* ── Sub-gauges ───────────────────────────────────────────── */
.sub-gauge{{
    display:flex;
    align-items:center;
    gap:14px;
    padding:12px 0;
    border-bottom:1px solid #d5cfc5
}}
.sub-gauge:last-child{{border-bottom:none}}
.sub-gauge-info{{flex:1;min-width:0}}
.sub-gauge-label{{color:#1a1a1a;font-weight:600;font-size:0.9em}}
.sub-gauge-bar{{
    height:8px;background:#d5cfc5;border-radius:4px;overflow:hidden;margin-bottom:4px
}}
.sub-gauge-fill{{
    height:100%;border-radius:4px;transition:width 1s ease-out
}}
.sub-gauge-desc{{color:#8a8070;font-size:0.75em}}

/* ── Frames ───────────────────────────────────────────────── */
.frames-grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:16px
}}
.frame-item img{{
    width:100%;border-radius:12px;border:2px solid #d5cfc5;
    transition:transform 0.2s;cursor:pointer
}}
.frame-item img:hover{{transform:scale(1.02)}}
.frame-caption{{
    text-align:center;color:#8a8070;font-size:0.82em;margin-top:8px;font-weight:500
}}

/* ── Report sections ──────────────────────────────────────── */
.report-section{{
    margin:20px 0;
    background:#ece7dd;
    border:1px solid #d5cfc5;
    border-left:3px solid #1a1a1a;
    border-radius:16px;
    overflow:hidden
}}
.report-section.section-positive{{border-left-color:#2d7a4f}}
.report-section.section-corrections{{border-left-color:#c45a2d}}
.report-section.section-correctifs{{border-left-color:#2d7a4f}}
.section-header{{
    font-size:0.92em;
    color:#1a1a1a;
    text-transform:uppercase;
    letter-spacing:2px;
    font-weight:700;
    padding:18px 24px;
    background:#e5e0d5;
    border-bottom:1px solid #d5cfc5;
    display:flex;
    align-items:center
}}
.section-body{{padding:20px 24px}}
@media(max-width:600px){{
    .section-body{{padding:16px 14px}}
    .section-header{{padding:14px 14px}}
}}

/* ── Report text elements ─────────────────────────────────── */
.report-p{{margin:6px 0;line-height:1.75;color:#1a1a1a;font-size:0.95em}}
.score-line{{color:#1a1a1a;font-size:1.05em;font-weight:700;margin:6px 0}}
.score-cat{{margin:8px 0;color:#1a1a1a;font-weight:600}}
.sub-label{{color:#5a4a3a;font-weight:600;font-size:0.88em;margin:14px 0 4px;text-transform:uppercase;letter-spacing:0.5px}}
.sub-content{{margin:2px 0 12px 0;color:#1a1a1a;line-height:1.75;padding-left:12px;border-left:2px solid #d5cfc5}}
.numbered-item{{
    display:flex;
    gap:12px;
    margin:14px 0 6px;
    align-items:flex-start
}}
.item-num{{
    background:#d5cfc5;
    color:#1a1a1a;
    width:28px;height:28px;
    border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:0.85em;
    flex-shrink:0;
    margin-top:1px
}}
.item-text{{font-weight:700;color:#1a1a1a;font-size:0.95em;line-height:1.5}}

/* ── Reps timeline ────────────────────────────────────────── */
.reps-bar{{
    display:flex;gap:6px;align-items:flex-end;
    height:80px;padding:0 4px;margin:12px 0
}}
.rep-col{{
    flex:1;
    border-radius:6px 6px 0 0;
    min-width:20px;
    transition:height 0.5s ease-out;
    position:relative;
    cursor:default
}}
.rep-col:hover{{opacity:0.85}}
.rep-label{{
    position:absolute;bottom:-22px;left:50%;transform:translateX(-50%);
    font-size:0.7em;color:#8a8070;white-space:nowrap
}}

/* ── Angle chart (canvas placeholder for inline SVG) ──────── */
.angle-chart{{
    width:100%;height:160px;
    background:#e5e0d5;
    border-radius:12px;
    padding:12px;
    margin:12px 0;
    overflow:hidden;
    position:relative
}}
.chart-line{{fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}}
.chart-grid{{stroke:#d5cfc5;stroke-width:0.5}}

/* ── Footer ───────────────────────────────────────────────── */
.footer{{
    text-align:center;
    padding:32px 0 24px;
    border-top:1px solid #d5cfc5;
    margin-top:32px
}}
.footer-brand{{color:#1a1a1a;font-weight:700;font-size:0.92em}}
.footer-sub{{color:#8a8070;font-size:0.78em;margin-top:4px}}
.footer-link{{color:#5a4a3a;text-decoration:none}}
.footer-link:hover{{text-decoration:underline}}

/* ── Confidence badge ─────────────────────────────────────── */
.confidence-badge{{
    display:inline-block;
    padding:4px 12px;
    border-radius:20px;
    font-size:0.78em;
    font-weight:600;
    letter-spacing:0.5px
}}
.confidence-haute{{background:#2d7a4f20;color:#2d7a4f;border:1px solid #2d7a4f40}}
.confidence-moyenne{{background:#c45a2d20;color:#c45a2d;border:1px solid #c45a2d40}}
.confidence-limitee{{background:#c4302d20;color:#c4302d;border:1px solid #c4302d40}}

/* ── Morpho profile ──────────────────────────────────────── */
.morpho-ratio{{
    background:#e5e0d5;border-radius:8px;padding:8px 10px;
    text-align:center
}}
.morpho-ratio-label{{color:#8a8070;font-size:0.72em;margin-bottom:2px}}
.morpho-ratio-val{{color:#1a1a1a;font-weight:700;font-size:1.05em}}
.morpho-tag{{
    background:#d5cfc5;color:#1a1a1a;padding:3px 10px;border-radius:12px;
    font-size:0.78em;font-weight:600
}}
.morpho-posture-item{{
    padding:6px 12px;margin:4px 0;font-size:0.88em;color:#1a1a1a;
    border-radius:4px;background:#e5e0d5
}}
.morpho-rec{{
    display:flex;gap:10px;align-items:flex-start;margin:8px 0
}}
.morpho-rec-num{{
    background:#d5cfc5;color:#1a1a1a;width:22px;height:22px;
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:0.75em;flex-shrink:0;margin-top:2px
}}
.morpho-rec-text{{color:#1a1a1a;font-size:0.85em;line-height:1.5}}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header fade-in">
    <div class="brand-label">Analyse biomecanique</div>
    <div class="brand-name">
        <span class="fc">FORM</span><span class="ch">CHECK</span>
    </div>
    <div class="brand-by">by ACHZOD</div>
    <div class="exercise-name">{html.escape(exercise_name)}</div>
    {gauge_svg}
    <div class="score-label">{score_lbl}</div>
    <div class="header-date">{now}</div>
</div>

<!-- Score breakdown -->
{breakdown_html}

<!-- Client intro -->
{client_intro_html}

<!-- Frames -->
{frames_html}

<!-- Angle chart -->
{angle_chart_html}

<!-- Reps timeline -->
{reps_timeline_html}

<!-- Profil morphologique -->
{morpho_html}

<!-- Analyse detaillee -->
<div class="fade-in" style="animation-delay:0.4s">
    {report_html}
</div>

<!-- Footer -->
<div class="footer fade-in" style="animation-delay:0.5s">
    <div class="footer-brand">FORMCHECK by ACHZOD</div>
    <div class="footer-sub" style="margin-top:6px">
        <a href="https://achzodcoaching.com" class="footer-link">achzodcoaching.com</a>
    </div>
    <div class="footer-sub" style="margin-top:4px">
        Instagram <a href="https://instagram.com/achzod" class="footer-link">@achzod</a> | <a href="mailto:coaching@achzodcoaching.com" class="footer-link">coaching@achzodcoaching.com</a>
    </div>
    <div class="footer-sub" style="margin-top:12px;font-size:0.7em;color:#444">
        ID: {analysis_id}
    </div>
</div>

</div>
</body>
</html>'''

    return html_content, analysis_id, token


# ── Helpers pour graphiques internes ──────────────────────────────────────────

def _build_angle_chart(pipeline_result: Any) -> str:
    """Construit un graphique SVG inline des angles par frame."""
    angles = pipeline_result.angles
    if not angles or not angles.frames:
        return ""

    # Choisir l'angle principal en fonction de l'exercice detecte
    exercise = ""
    if pipeline_result.detection:
        exercise = pipeline_result.detection.exercise.value

    angle_attrs = {
        "squat": ("left_knee_flexion", "Genou"),
        "front_squat": ("left_knee_flexion", "Genou"),
        "deadlift": ("left_hip_flexion", "Hanche"),
        "rdl": ("left_hip_flexion", "Hanche"),
        "bench_press": ("left_elbow_flexion", "Coude"),
        "ohp": ("left_elbow_flexion", "Coude"),
        "curl": ("left_elbow_flexion", "Coude"),
        "hip_thrust": ("left_hip_flexion", "Hanche"),
        "barbell_row": ("left_elbow_flexion", "Coude"),
        "lateral_raise": ("left_shoulder_abduction", "Epaule"),
        "upright_row": ("left_shoulder_abduction", "Epaule"),
        "cable_row": ("left_elbow_flexion", "Coude"),
        "cable_curl": ("left_elbow_flexion", "Coude"),
        "tricep_extension": ("left_elbow_flexion", "Coude"),
        "pullup": ("left_elbow_flexion", "Coude"),
        "goblet_squat": ("left_knee_flexion", "Genou"),
        "bulgarian_split_squat": ("left_knee_flexion", "Genou"),
        "lunge": ("left_knee_flexion", "Genou"),
        "sumo_deadlift": ("left_hip_flexion", "Hanche"),
        "leg_press": ("left_knee_flexion", "Genou"),
        "dumbbell_row": ("left_elbow_flexion", "Coude"),
        "incline_bench": ("left_elbow_flexion", "Coude"),
        "face_pull": ("left_elbow_flexion", "Coude"),
        "lat_pulldown": ("left_elbow_flexion", "Coude"),
        "pullover": ("left_shoulder_flexion", "Epaule"),
        "cable_pullover": ("left_shoulder_flexion", "Epaule"),
        "dip": ("left_elbow_flexion", "Coude"),
        "shrug": ("left_shoulder_abduction", "Epaule"),
        "calf_raise": ("left_knee_flexion", "Cheville"),
    }

    attr, label = angle_attrs.get(exercise, ("left_knee_flexion", "Angle principal"))

    # Extraire les valeurs
    values = []
    for f in angles.frames:
        val = getattr(f, attr, None)
        if val is not None:
            values.append(val)

    if len(values) < 5:
        return ""

    # Construire le SVG path
    chart_w = 700
    chart_h = 130
    padding_x = 40
    padding_y = 20
    usable_w = chart_w - 2 * padding_x
    usable_h = chart_h - 2 * padding_y

    min_val = min(values) - 5
    max_val = max(values) + 5
    val_range = max(max_val - min_val, 1)

    points = []
    for i, v in enumerate(values):
        x = padding_x + (i / max(len(values) - 1, 1)) * usable_w
        y = padding_y + (1 - (v - min_val) / val_range) * usable_h
        points.append(f"{x:.1f},{y:.1f}")

    path_d = "M" + " L".join(points)

    # Area fill (gradient under the line)
    first_x = padding_x
    last_x = padding_x + usable_w
    area_d = path_d + f" L{last_x:.1f},{chart_h - padding_y} L{first_x:.1f},{chart_h - padding_y} Z"

    # Grid lines
    grid_lines = ""
    n_grid = 4
    for i in range(n_grid + 1):
        gy = padding_y + (i / n_grid) * usable_h
        gval = max_val - (i / n_grid) * val_range
        grid_lines += f'<line x1="{padding_x}" y1="{gy:.1f}" x2="{chart_w - padding_x}" y2="{gy:.1f}" class="chart-grid"/>'
        grid_lines += f'<text x="{padding_x - 6}" y="{gy + 4:.1f}" text-anchor="end" fill="#8a8070" font-size="9">{gval:.0f}</text>'

    # Min/max markers
    min_idx = values.index(min(values))
    max_idx = values.index(max(values))
    min_x = padding_x + (min_idx / max(len(values) - 1, 1)) * usable_w
    min_y = padding_y + (1 - (min(values) - min_val) / val_range) * usable_h
    max_x = padding_x + (max_idx / max(len(values) - 1, 1)) * usable_w
    max_y = padding_y + (1 - (max(values) - min_val) / val_range) * usable_h

    return f'''
    <div class="card fade-in" style="animation-delay:0.35s">
        <div class="card-header">Courbe d'angle — {html.escape(label)}</div>
        <div class="angle-chart">
            <svg viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="none" style="width:100%;height:100%">
                <defs>
                    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#5a4a3a" stop-opacity="0.3"/>
                        <stop offset="100%" stop-color="#5a4a3a" stop-opacity="0.02"/>
                    </linearGradient>
                </defs>
                {grid_lines}
                <path d="{area_d}" fill="url(#areaGrad)"/>
                <path d="{path_d}" class="chart-line" stroke="#5a4a3a"/>
                <circle cx="{min_x:.1f}" cy="{min_y:.1f}" r="4" fill="#c4302d"/>
                <text x="{min_x:.1f}" y="{min_y - 8:.1f}" text-anchor="middle" fill="#c4302d" font-size="9" font-weight="700">{min(values):.0f}deg</text>
                <circle cx="{max_x:.1f}" cy="{max_y:.1f}" r="4" fill="#2d7a4f"/>
                <text x="{max_x:.1f}" y="{max_y - 8:.1f}" text-anchor="middle" fill="#2d7a4f" font-size="9" font-weight="700">{max(values):.0f}deg</text>
            </svg>
        </div>
    </div>'''


def _build_morpho_section(morpho: dict) -> str:
    """Construit la section visuelle du profil morphologique avec silhouette SVG."""
    morpho_type = morpho.get("morpho_type", "?").capitalize()
    squat_type = morpho.get("squat_type", "?").replace("_", " ")
    deadlift_type = morpho.get("deadlift_type", "?")
    bench_grip = morpho.get("bench_grip", "?")

    ftr = morpho.get("femur_tibia_ratio", 1.0)
    tfr = morpho.get("torso_femur_ratio", 1.0)
    atr = morpho.get("arm_torso_ratio", 1.0)
    shr = morpho.get("shoulder_hip_ratio", 1.0)
    uafr = morpho.get("upper_arm_forearm_ratio", 1.0)

    # Couleurs des ratios
    def _ratio_color(val: float, low: float, high: float) -> str:
        if val < low:
            return "#c45a2d"
        elif val > high:
            return "#5a4a3a"
        return "#2d7a4f"

    ftr_col = _ratio_color(ftr, 0.95, 1.1)
    tfr_col = _ratio_color(tfr, 0.95, 1.1)
    shr_col = _ratio_color(shr, 1.15, 1.35)

    # Silhouette SVG simplifiee avec proportions annotees
    # Les longueurs de segments sont normalisees pour la silhouette
    shoulder_w = morpho.get("shoulder_width", 0.22)
    hip_w = morpho.get("hip_width", 0.16)
    femur_l = morpho.get("femur_length", 0.26)
    tibia_l = morpho.get("tibia_length", 0.24)
    torso_l = morpho.get("torso_length", 0.28)

    # Normaliser les segments pour la silhouette (total = 300px de haut)
    total_seg = torso_l + femur_l + tibia_l
    if total_seg < 0.01:
        total_seg = 0.78
    scale = 240 / total_seg
    t_h = torso_l * scale
    f_h = femur_l * scale
    ti_h = tibia_l * scale
    s_w = shoulder_w * scale * 2.5
    h_w = hip_w * scale * 2.5

    # Points de la silhouette
    head_y = 20
    shoulder_y = head_y + 30
    hip_y = shoulder_y + t_h
    knee_y = hip_y + f_h
    ankle_y = knee_y + ti_h
    cx = 100  # centre x

    silhouette_svg = f'''
    <svg viewBox="0 0 200 {int(ankle_y + 30)}" style="width:140px;height:auto;margin:0 auto;display:block">
        <!-- Tete -->
        <circle cx="{cx}" cy="{head_y}" r="12" fill="none" stroke="#5a4a3a" stroke-width="1.5"/>
        <!-- Torse -->
        <line x1="{cx}" y1="{head_y + 12}" x2="{cx}" y2="{hip_y}" stroke="#5a4a3a" stroke-width="2"/>
        <!-- Epaules -->
        <line x1="{cx - s_w/2}" y1="{shoulder_y}" x2="{cx + s_w/2}" y2="{shoulder_y}" stroke="#5a4a3a" stroke-width="2"/>
        <!-- Bras G (upper arm + forearm) -->
        <line x1="{cx - s_w/2}" y1="{shoulder_y}" x2="{cx - s_w/2 - 6}" y2="{shoulder_y + t_h * 0.55}" stroke="#8a8070" stroke-width="1.5"/>
        <line x1="{cx - s_w/2 - 6}" y1="{shoulder_y + t_h * 0.55}" x2="{cx - s_w/2 - 2}" y2="{hip_y + 5}" stroke="#8a8070" stroke-width="1.5"/>
        <circle cx="{cx - s_w/2 - 6}" cy="{shoulder_y + t_h * 0.55}" r="2" fill="#8a8070"/>
        <!-- Bras D (upper arm + forearm) -->
        <line x1="{cx + s_w/2}" y1="{shoulder_y}" x2="{cx + s_w/2 + 6}" y2="{shoulder_y + t_h * 0.55}" stroke="#8a8070" stroke-width="1.5"/>
        <line x1="{cx + s_w/2 + 6}" y1="{shoulder_y + t_h * 0.55}" x2="{cx + s_w/2 + 2}" y2="{hip_y + 5}" stroke="#8a8070" stroke-width="1.5"/>
        <circle cx="{cx + s_w/2 + 6}" cy="{shoulder_y + t_h * 0.55}" r="2" fill="#8a8070"/>
        <!-- Hanches -->
        <line x1="{cx - h_w/2}" y1="{hip_y}" x2="{cx + h_w/2}" y2="{hip_y}" stroke="#5a4a3a" stroke-width="2"/>
        <!-- Femur G -->
        <line x1="{cx - h_w/2}" y1="{hip_y}" x2="{cx - h_w/3}" y2="{knee_y}" stroke="#c45a2d" stroke-width="2"/>
        <!-- Femur D -->
        <line x1="{cx + h_w/2}" y1="{hip_y}" x2="{cx + h_w/3}" y2="{knee_y}" stroke="#c45a2d" stroke-width="2"/>
        <!-- Tibia G -->
        <line x1="{cx - h_w/3}" y1="{knee_y}" x2="{cx - h_w/4}" y2="{ankle_y}" stroke="#2d7a4f" stroke-width="2"/>
        <!-- Tibia D -->
        <line x1="{cx + h_w/3}" y1="{knee_y}" x2="{cx + h_w/4}" y2="{ankle_y}" stroke="#2d7a4f" stroke-width="2"/>
        <!-- Joints -->
        <circle cx="{cx - s_w/2}" cy="{shoulder_y}" r="2.5" fill="#5a4a3a" opacity="0.7"/>
        <circle cx="{cx + s_w/2}" cy="{shoulder_y}" r="2.5" fill="#5a4a3a" opacity="0.7"/>
        <circle cx="{cx - h_w/2}" cy="{hip_y}" r="2.5" fill="#5a4a3a" opacity="0.7"/>
        <circle cx="{cx + h_w/2}" cy="{hip_y}" r="2.5" fill="#5a4a3a" opacity="0.7"/>
        <circle cx="{cx - h_w/3}" cy="{knee_y}" r="2.5" fill="#c45a2d" opacity="0.7"/>
        <circle cx="{cx + h_w/3}" cy="{knee_y}" r="2.5" fill="#c45a2d" opacity="0.7"/>
        <circle cx="{cx - h_w/4}" cy="{ankle_y}" r="2.5" fill="#2d7a4f" opacity="0.7"/>
        <circle cx="{cx + h_w/4}" cy="{ankle_y}" r="2.5" fill="#2d7a4f" opacity="0.7"/>
        <!-- Annotations -->
        <text x="12" y="{(shoulder_y + hip_y) / 2}" fill="#8a8070" font-size="8" font-family="Inter,system-ui">Torse</text>
        <text x="12" y="{(hip_y + knee_y) / 2}" fill="#8a8070" font-size="8" font-family="Inter,system-ui">Femur</text>
        <text x="12" y="{(knee_y + ankle_y) / 2}" fill="#8a8070" font-size="8" font-family="Inter,system-ui">Tibia</text>
        <!-- Largeur epaules -->
        <text x="{cx}" y="{shoulder_y - 6}" text-anchor="middle" fill="#5a4a3a" font-size="7" font-family="Inter,system-ui">{shoulder_w:.3f}</text>
        <!-- Largeur hanches -->
        <text x="{cx}" y="{hip_y + 12}" text-anchor="middle" fill="#5a4a3a" font-size="7" font-family="Inter,system-ui">{hip_w:.3f}</text>
    </svg>'''

    # Posture
    posture = morpho.get("posture", {})
    posture_items = []
    posture_summary = posture.get("summary", "")
    if posture.get("lordose_severity", 0) > 0.3:
        sev = posture["lordose_severity"]
        posture_items.append(f'<div class="morpho-posture-item" style="border-left:3px solid #c45a2d">Lordose lombaire <span style="color:#c45a2d;font-weight:600">{sev:.0%}</span></div>')
    if posture.get("cyphose_severity", 0) > 0.3:
        sev = posture["cyphose_severity"]
        posture_items.append(f'<div class="morpho-posture-item" style="border-left:3px solid #c45a2d">Cyphose thoracique <span style="color:#c45a2d;font-weight:600">{sev:.0%}</span></div>')
    if posture.get("epaules_enroulees"):
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #c45a2d">Epaules enroulees</div>')
    if posture.get("tete_en_avant"):
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #c45a2d">Tete en avant</div>')
    if posture.get("antéversion_bassin") or posture.get("anteversion_bassin"):
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #c45a2d">Antéversion du bassin</div>')
    if not posture_items:
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #2d7a4f">Posture equilibree</div>')

    posture_html = "\n".join(posture_items)

    # Recommendations (top 5)
    recs = morpho.get("recommendations", [])[:5]
    recs_html = ""
    if recs:
        rec_items = []
        for i, r in enumerate(recs):
            rec_items.append(
                f'<div class="morpho-rec">'
                f'<span class="morpho-rec-num">{i+1}</span>'
                f'<span class="morpho-rec-text">{html.escape(r)}</span>'
                f'</div>'
            )
        recs_html = "\n".join(rec_items)

    # Build recs section outside the f-string to avoid nested f-string issues (Python 3.11)
    recs_section = ""
    if recs_html:
        recs_section = '''
        <div style="margin-top:16px;padding-top:14px;border-top:1px solid #d5cfc5">
            <div style="color:#8a8070;font-size:0.82em;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px">Recommandations personnalisees</div>
            ''' + recs_html + '''
        </div>'''

    return f'''
    <div class="card fade-in" style="animation-delay:0.42s">
        <div class="card-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px;vertical-align:middle;opacity:0.8"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            Profil Morphologique
        </div>

        <!-- Type + silhouette -->
        <div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap">
            <div style="flex:1;min-width:200px">
                <div style="font-size:1.1em;color:#1a1a1a;font-weight:700;margin-bottom:12px">{morpho_type}</div>

                <!-- Ratios -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">
                    <div class="morpho-ratio">
                        <div class="morpho-ratio-label">Femur/Tibia</div>
                        <div class="morpho-ratio-val" style="color:{ftr_col}">{ftr:.2f}</div>
                    </div>
                    <div class="morpho-ratio">
                        <div class="morpho-ratio-label">Torse/Femur</div>
                        <div class="morpho-ratio-val" style="color:{tfr_col}">{tfr:.2f}</div>
                    </div>
                    <div class="morpho-ratio">
                        <div class="morpho-ratio-label">Epaules/Hanches</div>
                        <div class="morpho-ratio-val" style="color:{shr_col}">{shr:.2f}</div>
                    </div>
                    <div class="morpho-ratio">
                        <div class="morpho-ratio-label">Bras/Torse</div>
                        <div class="morpho-ratio-val">{atr:.2f}</div>
                    </div>
                    <div class="morpho-ratio">
                        <div class="morpho-ratio-label">Bras sup/Avant-bras</div>
                        <div class="morpho-ratio-val">{uafr:.2f}</div>
                    </div>
                </div>

                <!-- Preferences -->
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
                    <span class="morpho-tag">Squat: {squat_type}</span>
                    <span class="morpho-tag">Deadlift: {deadlift_type}</span>
                    <span class="morpho-tag">Bench: {bench_grip}</span>
                </div>
            </div>

            <!-- Silhouette -->
            <div style="flex-shrink:0">
                {silhouette_svg}
            </div>
        </div>

        <!-- Posture -->
        <div style="margin-top:16px;padding-top:14px;border-top:1px solid #d5cfc5">
            <div style="color:#8a8070;font-size:0.82em;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px">Bilan postural</div>
            {posture_html}
        </div>

        <!-- Recommandations -->
        {recs_section}
    </div>'''


def _build_reps_timeline(reps: Any) -> str:
    """Construit une timeline visuelle des reps."""
    if not reps or reps.total_reps < 1:
        return ""

    rep_list = reps.reps

    # If peak detection found a wildly different number than the authoritative count,
    # don't show per-rep bars (they'd be misleading). Just show the count.
    if not rep_list or abs(len(rep_list) - reps.total_reps) > 2:
        intensity_score = int(getattr(reps, "intensity_score", 0) or 0)
        intensity_label = str(getattr(reps, "intensity_label", "indeterminee"))
        avg_rest = float(getattr(reps, "avg_inter_rep_rest_s", 0.0) or 0.0)
        if intensity_score > 0:
            intensity_line = (
                'Intensite serie : <span style="color:#1a1a1a;font-weight:700">{}/100 ({})</span> '
                '• Repos inter-reps moyen : <span style="color:#1a1a1a;font-weight:600">{:.2f}s</span>'
            ).format(intensity_score, intensity_label, avg_rest)
        else:
            intensity_line = (
                'Intensite serie : <span style="color:#1a1a1a;font-weight:700">non estimable</span> '
                '• Donnees rep-par-rep insuffisantes'
            )
        return '''
    <div class="card fade-in" style="animation-delay:0.38s">
        <div class="card-header">{} repetitions detectees</div>
        <div style="font-size:0.9em;color:#8a8070;padding:12px 0">
            Comptage par analyse vidéo avancée.
        </div>
        <div style="font-size:0.82em;color:#8a8070">
            {}
        </div>
    </div>'''.format(reps.total_reps, intensity_line)

    # Trouver le max ROM pour normaliser la hauteur des barres
    max_rom = max(r.rom for r in rep_list) if rep_list else 1
    if max_rom < 1:
        max_rom = 1

    bars = []
    for r in rep_list:
        h_pct = min(100, int(r.rom / max_rom * 100))
        # Couleur basee sur le tempo ratio
        if r.tempo_ratio >= 1.5:
            color = "#2d7a4f"  # bon controle excentrique
        elif r.tempo_ratio >= 0.8:
            color = "#5a4a3a"  # equilibre
        else:
            color = "#c45a2d"  # concentrique dominant

        ecc_s = r.eccentric_duration_ms / 1000
        conc_s = r.concentric_duration_ms / 1000

        bars.append(
            f'<div class="rep-col" style="height:{max(10, h_pct)}%;background:{color}" '
            f'title="Rep {r.rep_number}: ROM {r.rom:.0f}deg, Ecc {ecc_s:.1f}s, Conc {conc_s:.1f}s">'
            f'<span class="rep-label">R{r.rep_number}</span>'
            f'</div>'
        )

    avg_ecc = sum(r.eccentric_duration_ms for r in rep_list) / len(rep_list) / 1000
    avg_conc = sum(r.concentric_duration_ms for r in rep_list) / len(rep_list) / 1000
    intensity_score = int(getattr(reps, "intensity_score", 0) or 0)
    intensity_label = str(getattr(reps, "intensity_label", "indeterminee"))
    avg_rest = float(getattr(reps, "avg_inter_rep_rest_s", 0.0) or 0.0)
    intensity_conf = str(getattr(reps, "intensity_confidence", "faible"))

    if intensity_score <= 0:
        intensity_color = "#8a8070"
        intensity_display = "non estimable"
    elif intensity_score >= 80:
        intensity_color = "#2d7a4f"
        intensity_display = f"{intensity_score}/100 ({intensity_label})"
    elif intensity_score >= 60:
        intensity_color = "#8a6a2f"
        intensity_display = f"{intensity_score}/100 ({intensity_label})"
    else:
        intensity_color = "#c45a2d"
        intensity_display = f"{intensity_score}/100 ({intensity_label})"

    return f'''
    <div class="card fade-in" style="animation-delay:0.38s">
        <div class="card-header">Timeline des repetitions — {reps.total_reps} reps</div>
        <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap">
            <div style="font-size:0.82em;color:#8a8070">Tempo moyen : <span style="color:#1a1a1a;font-weight:600">{avg_ecc:.1f}s ecc / {avg_conc:.1f}s conc</span></div>
            <div style="font-size:0.82em;color:#8a8070">Consistance : <span style="color:#1a1a1a;font-weight:600">{reps.tempo_consistency:.0%}</span></div>
            <div style="font-size:0.82em;color:#8a8070">Intensite serie : <span style="color:{intensity_color};font-weight:700">{intensity_display}</span></div>
            <div style="font-size:0.82em;color:#8a8070">Repos inter-reps : <span style="color:#1a1a1a;font-weight:600">{avg_rest:.2f}s</span> <span style="color:#b5a998">({intensity_conf})</span></div>
        </div>
        <div class="reps-bar" style="margin-bottom:28px">
            {"".join(bars)}
        </div>
        <div style="display:flex;gap:16px;font-size:0.72em;color:#8a8070;flex-wrap:wrap">
            <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#2d7a4f;margin-right:4px"></span>Bon controle excentrique</div>
            <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#5a4a3a;margin-right:4px"></span>Tempo equilibre</div>
            <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#c45a2d;margin-right:4px"></span>Concentrique dominant</div>
        </div>
    </div>'''
