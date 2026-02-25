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
        return "#00ff88"
    elif score >= 60:
        return "#ff6b35"
    return "#ff3366"


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
        "securite": "#ff3366",
        "efficacite": "#00d4ff",
        "controle": "#ff6b35",
        "symetrie": "#00ff88",
    }
    norm = category.lower().replace("é", "e").replace("è", "e")
    for key, color in colors.items():
        if key in norm:
            return color
    return "#00d4ff"


# Titres de sections attendus du rapport LLM
_SECTION_TITLES = [
    "ANALYSE BIOMECANIQUE",
    "RESUME",
    "AMPLITUDE DE MOUVEMENT",
    "POINTS POSITIFS",
    "CORRECTIONS PRIORITAIRES",
    "ANALYSE DU TEMPO ET DES PHASES",
    "ANALYSE DU TEMPO ET DES REPETITIONS",
    "COMPENSATIONS ET BIOMECANIQUE AVANCEE",
    "PROFIL MORPHOLOGIQUE",
    "EXERCICES CORRECTIFS",
    "DECOMPOSITION DU SCORE",
    "ANALYSE AVANCEE",
    "POINT BIOMECANIQUE",
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
}


def _get_section_icon(title: str) -> str:
    upper = title.upper()
    for key, icon in _SECTION_ICONS.items():
        if key in upper:
            return icon
    return ""


def _format_report_html(report_text: str) -> str:
    """Convertit le texte du rapport LLM en HTML propre, parse par sections."""
    text = html.escape(report_text)
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
            html_parts.append(
                f'<div class="report-section fade-in" style="animation-delay:{section_count * 0.05}s">'
                f'<div class="section-header">{icon_html}{stripped}</div>'
                f'<div class="section-body">'
            )
            in_section = True
            continue

        # Sub-headers
        sub_match = re.match(
            r"^(Donnee mesuree|Impact biomecanique|Correction|Cible|Execution|"
            r"Phase excentrique|Phase concentrique|Phase isometrique|Tempo ratio|"
            r"Consistance du tempo|Consistance|Time Under Tension)\s*:\s*(.*)$",
            stripped,
        )
        if sub_match:
            label = sub_match.group(1)
            rest = sub_match.group(2)
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
            rest = num_match.group(2)
            html_parts.append(
                f'<div class="numbered-item">'
                f'<span class="item-num">{num}</span>'
                f'<span class="item-text">{rest}</span>'
                f'</div>'
            )
            continue

        # Default paragraph
        html_parts.append(f'<p class="report-p">{stripped}</p>')

    if in_section:
        html_parts.append("</div></div>")

    return "\n".join(html_parts)


_FRAME_LABELS = {
    "start": "Position de depart",
    "mid": "Point bas du mouvement",
    "end": "Phase de remontee",
    "quarter": "Descente (1/4)",
    "three_quarter": "Remontee (3/4)",
}


def generate_html_report(
    report: Report,
    annotated_frames: dict[str, str],
    analysis_id: str | None = None,
    pipeline_result: Any | None = None,
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
    <svg viewBox="0 0 120 120" style="width:180px;height:180px;margin:0 auto;display:block">
        <circle cx="60" cy="60" r="54" fill="none" stroke="#1a1a2e" stroke-width="8"/>
        <circle cx="60" cy="60" r="54" fill="none" stroke="{score_col}" stroke-width="8"
            stroke-linecap="round" stroke-dasharray="{gauge_circumference}"
            stroke-dashoffset="{gauge_offset}"
            transform="rotate(-90 60 60)"
            style="transition:stroke-dashoffset 1.5s ease-out"/>
        <text x="60" y="55" text-anchor="middle" fill="{score_col}"
            font-size="28" font-weight="900" font-family="Inter,system-ui,sans-serif">{score}</text>
        <text x="60" y="72" text-anchor="middle" fill="#8888aa"
            font-size="10" font-family="Inter,system-ui,sans-serif">/100</text>
    </svg>'''

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

            # Mini gauge SVG
            mini_circ = 2 * 3.14159 * 20  # r=20
            mini_offset = mini_circ * (1 - pct / 100)

            gauges.append(f'''
            <div class="sub-gauge">
                <svg viewBox="0 0 50 50" style="width:56px;height:56px">
                    <circle cx="25" cy="25" r="20" fill="none" stroke="#1a1a2e" stroke-width="4"/>
                    <circle cx="25" cy="25" r="20" fill="none" stroke="{color}" stroke-width="4"
                        stroke-linecap="round" stroke-dasharray="{mini_circ}"
                        stroke-dashoffset="{mini_offset}"
                        transform="rotate(-90 25 25)"
                        style="transition:stroke-dashoffset 1.2s ease-out"/>
                    <text x="25" y="28" text-anchor="middle" fill="{color}"
                        font-size="11" font-weight="700" font-family="Inter,system-ui,sans-serif">{val}</text>
                </svg>
                <div class="sub-gauge-info">
                    <div class="sub-gauge-label">{label}</div>
                    <div class="sub-gauge-bar">
                        <div class="sub-gauge-fill" style="width:{pct}%;background:{color}"></div>
                    </div>
                    <div class="sub-gauge-desc">{description}</div>
                </div>
                <div class="sub-gauge-max">/{max_val}</div>
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
        for label, path in annotated_frames.items():
            if not Path(path).exists():
                continue
            b64 = _img_to_base64(path)
            caption = _FRAME_LABELS.get(label, label.replace("_", " ").title())
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

    # ── Report text formatted ─────────────────────────────────────────────
    report_html = _format_report_html(report.report_text)

    # ── Full HTML ─────────────────────────────────────────────────────────
    html_content = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=5.0">
<title>FORMCHECK — {html.escape(exercise_name)}</title>
<style>
/* ── Reset & Base ─────────────────────────────────────────── */
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{
    background:#08081a;
    color:#d0d0e0;
    font-family:Inter,-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
    line-height:1.65;
    -webkit-font-smoothing:antialiased;
    -moz-osx-font-smoothing:grayscale
}}

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
    border-bottom:1px solid #1a1a2e;
    position:relative
}}
.header::before{{
    content:'';
    position:absolute;
    top:0;left:50%;transform:translateX(-50%);
    width:200px;height:2px;
    background:linear-gradient(90deg,transparent,#00d4ff,transparent);
    border-radius:1px
}}
.brand-label{{
    font-size:0.75em;letter-spacing:5px;color:#6868aa;
    text-transform:uppercase;margin-bottom:10px
}}
.brand-name{{font-size:2em;font-weight:800;margin-bottom:2px}}
.brand-name .fc{{color:#00d4ff}}
.brand-name .ch{{color:#fff}}
.brand-by{{color:#6868aa;font-size:0.78em;letter-spacing:3px;margin-bottom:24px}}
.exercise-name{{font-size:1.35em;color:#fff;font-weight:700;margin-bottom:16px}}
.score-label{{color:#8888aa;font-size:0.82em;margin-top:12px;letter-spacing:1px}}
.header-date{{color:#6868aa;font-size:0.78em;margin-top:16px}}

/* ── Cards ────────────────────────────────────────────────── */
.card{{
    background:#0e0e24;
    border:1px solid #1a1a2e;
    border-radius:16px;
    padding:24px;
    margin:20px 0;
    overflow:hidden
}}
.card-header{{
    font-size:0.95em;
    color:#00d4ff;
    text-transform:uppercase;
    letter-spacing:2.5px;
    font-weight:700;
    padding-bottom:14px;
    margin-bottom:16px;
    border-bottom:1px solid #151530
}}

/* ── Sub-gauges ───────────────────────────────────────────── */
.sub-gauge{{
    display:flex;
    align-items:center;
    gap:14px;
    padding:12px 0;
    border-bottom:1px solid #12122a
}}
.sub-gauge:last-child{{border-bottom:none}}
.sub-gauge-info{{flex:1;min-width:0}}
.sub-gauge-label{{color:#e0e0f0;font-weight:600;font-size:0.9em;margin-bottom:6px}}
.sub-gauge-bar{{
    height:6px;background:#151530;border-radius:3px;overflow:hidden;margin-bottom:4px
}}
.sub-gauge-fill{{
    height:100%;border-radius:3px;transition:width 1s ease-out
}}
.sub-gauge-desc{{color:#6868aa;font-size:0.75em}}
.sub-gauge-max{{color:#6868aa;font-size:0.85em;font-weight:600;min-width:30px;text-align:right}}

/* ── Frames ───────────────────────────────────────────────── */
.frames-grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:16px
}}
.frame-item img{{
    width:100%;border-radius:12px;border:2px solid #1a1a2e;
    transition:transform 0.2s;cursor:pointer
}}
.frame-item img:hover{{transform:scale(1.02)}}
.frame-caption{{
    text-align:center;color:#8888aa;font-size:0.82em;margin-top:8px;font-weight:500
}}

/* ── Report sections ──────────────────────────────────────── */
.report-section{{
    margin:20px 0;
    background:#0e0e24;
    border:1px solid #1a1a2e;
    border-radius:16px;
    overflow:hidden
}}
.section-header{{
    font-size:0.92em;
    color:#00d4ff;
    text-transform:uppercase;
    letter-spacing:2px;
    font-weight:700;
    padding:18px 24px;
    background:#0a0a20;
    border-bottom:1px solid #151530;
    display:flex;
    align-items:center
}}
.section-body{{padding:20px 24px}}
@media(max-width:600px){{
    .section-body{{padding:16px 14px}}
    .section-header{{padding:14px 14px}}
}}

/* ── Report text elements ─────────────────────────────────── */
.report-p{{margin:4px 0;line-height:1.7;color:#c8c8e0}}
.score-line{{color:#00d4ff;font-size:1.05em;font-weight:700;margin:6px 0}}
.score-cat{{margin:8px 0;color:#e0e0f0;font-weight:600}}
.sub-label{{color:#00d4ff;font-weight:600;font-size:0.9em;margin:10px 0 2px}}
.sub-content{{margin:2px 0 10px 0;color:#c8c8e0;line-height:1.7}}
.numbered-item{{
    display:flex;
    gap:12px;
    margin:14px 0 6px;
    align-items:flex-start
}}
.item-num{{
    background:#1a1a3a;
    color:#00d4ff;
    width:28px;height:28px;
    border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:0.85em;
    flex-shrink:0;
    margin-top:1px
}}
.item-text{{font-weight:700;color:#fff;font-size:0.95em;line-height:1.5}}

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
    font-size:0.7em;color:#6868aa;white-space:nowrap
}}

/* ── Angle chart (canvas placeholder for inline SVG) ──────── */
.angle-chart{{
    width:100%;height:160px;
    background:#0a0a1a;
    border-radius:12px;
    padding:12px;
    margin:12px 0;
    overflow:hidden;
    position:relative
}}
.chart-line{{fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}}
.chart-grid{{stroke:#151530;stroke-width:0.5}}

/* ── Footer ───────────────────────────────────────────────── */
.footer{{
    text-align:center;
    padding:32px 0 24px;
    border-top:1px solid #1a1a2e;
    margin-top:32px
}}
.footer-brand{{color:#00d4ff;font-weight:700;font-size:0.92em}}
.footer-sub{{color:#6868aa;font-size:0.78em;margin-top:4px}}
.footer-link{{color:#00d4ff;text-decoration:none}}
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
.confidence-haute{{background:#00ff8820;color:#00ff88;border:1px solid #00ff8840}}
.confidence-moyenne{{background:#ff6b3520;color:#ff6b35;border:1px solid #ff6b3540}}
.confidence-limitee{{background:#ff336620;color:#ff3366;border:1px solid #ff336640}}

/* ── Morpho profile ──────────────────────────────────────── */
.morpho-ratio{{
    background:#0a0a1a;border-radius:8px;padding:8px 10px;
    text-align:center
}}
.morpho-ratio-label{{color:#8888aa;font-size:0.72em;margin-bottom:2px}}
.morpho-ratio-val{{color:#e0e0f0;font-weight:700;font-size:1.05em}}
.morpho-tag{{
    background:#1a1a3a;color:#00d4ff;padding:3px 10px;border-radius:12px;
    font-size:0.78em;font-weight:600
}}
.morpho-posture-item{{
    padding:6px 12px;margin:4px 0;font-size:0.88em;color:#e0e0f0;
    border-radius:4px;background:#0a0a1a
}}
.morpho-rec{{
    display:flex;gap:10px;align-items:flex-start;margin:8px 0
}}
.morpho-rec-num{{
    background:#1a1a3a;color:#00d4ff;width:22px;height:22px;
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:0.75em;flex-shrink:0;margin-top:2px
}}
.morpho-rec-text{{color:#c8c8e0;font-size:0.85em;line-height:1.5}}
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
    <div class="footer-sub">Analyse biomecanique experte — 11 certifications</div>
    <div class="footer-sub" style="margin-top:8px">
        Instagram <a href="https://instagram.com/achzod" class="footer-link">@achzod</a>
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
        grid_lines += f'<text x="{padding_x - 6}" y="{gy + 4:.1f}" text-anchor="end" fill="#6868aa" font-size="9">{gval:.0f}</text>'

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
                        <stop offset="0%" stop-color="#00d4ff" stop-opacity="0.3"/>
                        <stop offset="100%" stop-color="#00d4ff" stop-opacity="0.02"/>
                    </linearGradient>
                </defs>
                {grid_lines}
                <path d="{area_d}" fill="url(#areaGrad)"/>
                <path d="{path_d}" class="chart-line" stroke="#00d4ff"/>
                <circle cx="{min_x:.1f}" cy="{min_y:.1f}" r="4" fill="#ff3366"/>
                <text x="{min_x:.1f}" y="{min_y - 8:.1f}" text-anchor="middle" fill="#ff3366" font-size="9" font-weight="700">{min(values):.0f}deg</text>
                <circle cx="{max_x:.1f}" cy="{max_y:.1f}" r="4" fill="#00ff88"/>
                <text x="{max_x:.1f}" y="{max_y - 8:.1f}" text-anchor="middle" fill="#00ff88" font-size="9" font-weight="700">{max(values):.0f}deg</text>
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
            return "#ff6b35"
        elif val > high:
            return "#00d4ff"
        return "#00ff88"

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
        <circle cx="{cx}" cy="{head_y}" r="12" fill="none" stroke="#00d4ff" stroke-width="1.5"/>
        <!-- Torse -->
        <line x1="{cx}" y1="{head_y + 12}" x2="{cx}" y2="{hip_y}" stroke="#00d4ff" stroke-width="2"/>
        <!-- Epaules -->
        <line x1="{cx - s_w/2}" y1="{shoulder_y}" x2="{cx + s_w/2}" y2="{shoulder_y}" stroke="#00d4ff" stroke-width="2"/>
        <!-- Bras G (upper arm + forearm) -->
        <line x1="{cx - s_w/2}" y1="{shoulder_y}" x2="{cx - s_w/2 - 6}" y2="{shoulder_y + t_h * 0.55}" stroke="#6868aa" stroke-width="1.5"/>
        <line x1="{cx - s_w/2 - 6}" y1="{shoulder_y + t_h * 0.55}" x2="{cx - s_w/2 - 2}" y2="{hip_y + 5}" stroke="#6868aa" stroke-width="1.5"/>
        <circle cx="{cx - s_w/2 - 6}" cy="{shoulder_y + t_h * 0.55}" r="2" fill="#6868aa"/>
        <!-- Bras D (upper arm + forearm) -->
        <line x1="{cx + s_w/2}" y1="{shoulder_y}" x2="{cx + s_w/2 + 6}" y2="{shoulder_y + t_h * 0.55}" stroke="#6868aa" stroke-width="1.5"/>
        <line x1="{cx + s_w/2 + 6}" y1="{shoulder_y + t_h * 0.55}" x2="{cx + s_w/2 + 2}" y2="{hip_y + 5}" stroke="#6868aa" stroke-width="1.5"/>
        <circle cx="{cx + s_w/2 + 6}" cy="{shoulder_y + t_h * 0.55}" r="2" fill="#6868aa"/>
        <!-- Hanches -->
        <line x1="{cx - h_w/2}" y1="{hip_y}" x2="{cx + h_w/2}" y2="{hip_y}" stroke="#00d4ff" stroke-width="2"/>
        <!-- Femur G -->
        <line x1="{cx - h_w/2}" y1="{hip_y}" x2="{cx - h_w/3}" y2="{knee_y}" stroke="#ff6b35" stroke-width="2"/>
        <!-- Femur D -->
        <line x1="{cx + h_w/2}" y1="{hip_y}" x2="{cx + h_w/3}" y2="{knee_y}" stroke="#ff6b35" stroke-width="2"/>
        <!-- Tibia G -->
        <line x1="{cx - h_w/3}" y1="{knee_y}" x2="{cx - h_w/4}" y2="{ankle_y}" stroke="#00ff88" stroke-width="2"/>
        <!-- Tibia D -->
        <line x1="{cx + h_w/3}" y1="{knee_y}" x2="{cx + h_w/4}" y2="{ankle_y}" stroke="#00ff88" stroke-width="2"/>
        <!-- Joints -->
        <circle cx="{cx - s_w/2}" cy="{shoulder_y}" r="2.5" fill="#00d4ff" opacity="0.7"/>
        <circle cx="{cx + s_w/2}" cy="{shoulder_y}" r="2.5" fill="#00d4ff" opacity="0.7"/>
        <circle cx="{cx - h_w/2}" cy="{hip_y}" r="2.5" fill="#00d4ff" opacity="0.7"/>
        <circle cx="{cx + h_w/2}" cy="{hip_y}" r="2.5" fill="#00d4ff" opacity="0.7"/>
        <circle cx="{cx - h_w/3}" cy="{knee_y}" r="2.5" fill="#ff6b35" opacity="0.7"/>
        <circle cx="{cx + h_w/3}" cy="{knee_y}" r="2.5" fill="#ff6b35" opacity="0.7"/>
        <circle cx="{cx - h_w/4}" cy="{ankle_y}" r="2.5" fill="#00ff88" opacity="0.7"/>
        <circle cx="{cx + h_w/4}" cy="{ankle_y}" r="2.5" fill="#00ff88" opacity="0.7"/>
        <!-- Annotations -->
        <text x="12" y="{(shoulder_y + hip_y) / 2}" fill="#8888aa" font-size="8" font-family="Inter,system-ui">Torse</text>
        <text x="12" y="{(hip_y + knee_y) / 2}" fill="#8888aa" font-size="8" font-family="Inter,system-ui">Femur</text>
        <text x="12" y="{(knee_y + ankle_y) / 2}" fill="#8888aa" font-size="8" font-family="Inter,system-ui">Tibia</text>
        <!-- Largeur epaules -->
        <text x="{cx}" y="{shoulder_y - 6}" text-anchor="middle" fill="#00d4ff" font-size="7" font-family="Inter,system-ui">{shoulder_w:.3f}</text>
        <!-- Largeur hanches -->
        <text x="{cx}" y="{hip_y + 12}" text-anchor="middle" fill="#00d4ff" font-size="7" font-family="Inter,system-ui">{hip_w:.3f}</text>
    </svg>'''

    # Posture
    posture = morpho.get("posture", {})
    posture_items = []
    posture_summary = posture.get("summary", "")
    if posture.get("lordose_severity", 0) > 0.3:
        sev = posture["lordose_severity"]
        posture_items.append(f'<div class="morpho-posture-item" style="border-left:3px solid #ff6b35">Lordose lombaire <span style="color:#ff6b35;font-weight:600">{sev:.0%}</span></div>')
    if posture.get("cyphose_severity", 0) > 0.3:
        sev = posture["cyphose_severity"]
        posture_items.append(f'<div class="morpho-posture-item" style="border-left:3px solid #ff6b35">Cyphose thoracique <span style="color:#ff6b35;font-weight:600">{sev:.0%}</span></div>')
    if posture.get("epaules_enroulees"):
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #ff6b35">Epaules enroulees</div>')
    if posture.get("tete_en_avant"):
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #ff6b35">Tete en avant</div>')
    if posture.get("antéversion_bassin") or posture.get("anteversion_bassin"):
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #ff6b35">Antéversion du bassin</div>')
    if not posture_items:
        posture_items.append('<div class="morpho-posture-item" style="border-left:3px solid #00ff88">Posture equilibree</div>')

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

    return f'''
    <div class="card fade-in" style="animation-delay:0.42s">
        <div class="card-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px;vertical-align:middle;opacity:0.8"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            Profil Morphologique
        </div>

        <!-- Type + silhouette -->
        <div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap">
            <div style="flex:1;min-width:200px">
                <div style="font-size:1.1em;color:#fff;font-weight:700;margin-bottom:12px">{morpho_type}</div>

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
        <div style="margin-top:16px;padding-top:14px;border-top:1px solid #151530">
            <div style="color:#8888aa;font-size:0.82em;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px">Bilan postural</div>
            {posture_html}
        </div>

        <!-- Recommandations -->
        {"" if not recs_html else f'''
        <div style="margin-top:16px;padding-top:14px;border-top:1px solid #151530">
            <div style="color:#8888aa;font-size:0.82em;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px">Recommandations personnalisees</div>
            {recs_html}
        </div>
        '''}
    </div>'''


def _build_reps_timeline(reps: Any) -> str:
    """Construit une timeline visuelle des reps."""
    if not reps or not reps.reps:
        return ""

    rep_list = reps.reps
    if not rep_list:
        return ""

    # Trouver le max ROM pour normaliser la hauteur des barres
    max_rom = max(r.rom for r in rep_list) if rep_list else 1
    if max_rom < 1:
        max_rom = 1

    bars = []
    for r in rep_list:
        h_pct = min(100, int(r.rom / max_rom * 100))
        # Couleur basee sur le tempo ratio
        if r.tempo_ratio >= 1.5:
            color = "#00ff88"  # bon controle excentrique
        elif r.tempo_ratio >= 0.8:
            color = "#00d4ff"  # equilibre
        else:
            color = "#ff6b35"  # concentrique dominant

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

    return f'''
    <div class="card fade-in" style="animation-delay:0.38s">
        <div class="card-header">Timeline des repetitions — {len(rep_list)} reps</div>
        <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap">
            <div style="font-size:0.82em;color:#8888aa">Tempo moyen : <span style="color:#e0e0f0;font-weight:600">{avg_ecc:.1f}s ecc / {avg_conc:.1f}s conc</span></div>
            <div style="font-size:0.82em;color:#8888aa">Consistance : <span style="color:#e0e0f0;font-weight:600">{reps.tempo_consistency:.0%}</span></div>
        </div>
        <div class="reps-bar" style="margin-bottom:28px">
            {"".join(bars)}
        </div>
        <div style="display:flex;gap:16px;font-size:0.72em;color:#6868aa;flex-wrap:wrap">
            <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#00ff88;margin-right:4px"></span>Bon controle excentrique</div>
            <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#00d4ff;margin-right:4px"></span>Tempo equilibre</div>
            <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#ff6b35;margin-right:4px"></span>Concentrique dominant</div>
        </div>
    </div>'''
