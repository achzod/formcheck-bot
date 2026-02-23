"""Générateur de rapport HTML premium autonome pour FORMCHECK by ACHZOD.

Produit un fichier HTML 100% autonome (inline CSS, images base64)
avec dark theme premium, responsive, ouvrable offline.
"""

from __future__ import annotations

import base64
import html
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


# Section titles we expect from the LLM report
_SECTION_TITLES = [
    "ANALYSE BIOMECANIQUE",
    "RESUME",
    "POINTS POSITIFS",
    "CORRECTIONS PRIORITAIRES",
    "AMPLITUDE DE MOUVEMENT",
    "ANALYSE DU TEMPO ET DES PHASES",
    "ANALYSE DU TEMPO ET DES REPETITIONS",
    "EXERCICES CORRECTIFS",
    "DECOMPOSITION DU SCORE",
    "ANALYSE AVANCEE",
    "POINT BIOMECANIQUE",
]


def _format_report_html(report_text: str) -> str:
    """Convertit le texte du rapport LLM en HTML propre, parsé par sections."""
    text = html.escape(report_text)
    lines = text.split("\n")
    html_parts: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div style="height:10px"></div>')
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

        # Also match "Score : XX/100" as part of header area
        if re.match(r"^Score\s*:", stripped, re.IGNORECASE):
            html_parts.append(
                f'<p style="color:#00d4ff;font-size:1.05em;font-weight:700;margin:4px 0">{stripped}</p>'
            )
            continue

        if is_header:
            if in_section:
                html_parts.append("</div>")  # close previous section
            html_parts.append(
                f'<div style="margin:24px 0 12px">'
                f'<div style="font-size:1.1em;color:#00d4ff;text-transform:uppercase;'
                f'letter-spacing:2px;font-weight:700;border-bottom:1px solid #1a1a2e;'
                f'padding-bottom:8px;margin-bottom:12px">{stripped}</div>'
            )
            in_section = True
            continue

        # Sub-headers like "Donnee mesuree :", "Impact biomecanique :", "Correction :", "Cible :", "Execution :"
        if re.match(r"^(Donnee mesuree|Impact biomecanique|Correction|Cible|Execution|Phase excentrique|Phase concentrique|Phase isometrique|Tempo ratio|Consistance du tempo|Time Under Tension)\s*:", stripped):
            label_match = re.match(r"^(.+?)\s*:\s*(.*)$", stripped)
            if label_match:
                label = label_match.group(1)
                rest = label_match.group(2)
                html_parts.append(
                    f'<p style="margin:8px 0 2px;color:#00d4ff;font-weight:600;font-size:0.95em">{label} :</p>'
                    f'<p style="margin:2px 0 8px 12px;color:#d0d0e0;line-height:1.65">{rest}</p>'
                )
                continue

        # Score breakdown lines like "Securite : XX/40"
        if re.match(r"^(Securite|Efficacite|Controle|Symetrie)", stripped, re.IGNORECASE) and "/" in stripped:
            html_parts.append(
                f'<p style="margin:6px 0;color:#e0e0f0;font-weight:600">{stripped}</p>'
            )
            continue

        # Numbered items
        if re.match(r"^\d+\.", stripped):
            html_parts.append(
                f'<p style="margin:14px 0 4px;font-weight:700;color:#fff;font-size:1.0em">{stripped}</p>'
            )
            continue

        # Default paragraph
        html_parts.append(
            f'<p style="margin:3px 0;line-height:1.65;color:#d0d0e0">{stripped}</p>'
        )

    if in_section:
        html_parts.append("</div>")

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
) -> tuple[str, str, str]:
    """Génère un rapport HTML premium autonome.

    Args:
        report: Rapport d'analyse du LLM.
        annotated_frames: Dict {label: chemin_image} des frames annotées.
        analysis_id: ID unique de l'analyse. Auto-généré si None.

    Returns:
        Tuple (html_content, analysis_id, token).
    """
    if not analysis_id:
        analysis_id = uuid.uuid4().hex[:12]
    token = uuid.uuid4().hex[:16]

    score = report.score
    score_col = _score_color(score)
    exercise_name = report.exercise_display
    now = datetime.now().strftime("%d/%m/%Y a %H:%M")

    # ── Score breakdown bars ─────────────────────────────────────────────
    breakdown_html = ""
    breakdown_config = [
        ("Securite", "securite", 40),
        ("Efficacite technique", "efficacite", 30),
        ("Controle et tempo", "controle", 20),
        ("Symetrie", "symetrie", 10),
    ]

    if report.score_breakdown:
        bars = []
        for label, key, max_val in breakdown_config:
            val = 0
            for k, v in report.score_breakdown.items():
                norm_k = k.lower().replace("é", "e").replace("è", "e").replace("&", "et")
                if key in norm_k:
                    val = v
                    break
            pct = min(100, int(val / max_val * 100)) if max_val else 0
            color = _bar_color(key)
            bars.append(f'''
            <div style="margin:10px 0">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="color:#d0d0e0;font-size:0.9em">{label}</span>
                    <span style="color:{color};font-weight:700;font-size:0.9em">{val}/{max_val}</span>
                </div>
                <div style="background:#1a1a2e;border-radius:8px;height:10px;overflow:hidden">
                    <div style="width:{pct}%;height:100%;background:{color};border-radius:8px;transition:width 0.5s"></div>
                </div>
            </div>''')
        breakdown_html = f'''
        <div style="margin:24px 0;padding:20px;background:#10102a;border-radius:12px;border:1px solid #1a1a2e">
            <div style="font-size:1.1em;color:#00d4ff;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-bottom:14px">Decomposition du score</div>
            {"".join(bars)}
        </div>'''

    # ── Frames HTML ──────────────────────────────────────────────────────
    frames_html = ""
    if annotated_frames:
        frame_items = []
        for label, path in annotated_frames.items():
            if not Path(path).exists():
                continue
            b64 = _img_to_base64(path)
            caption = _FRAME_LABELS.get(label, label.replace("_", " ").title())
            frame_items.append(f'''
            <div style="flex:1;min-width:240px;max-width:350px">
                <img src="{b64}" style="width:100%;border-radius:12px;border:2px solid #1a1a2e" alt="{html.escape(caption)}">
                <p style="text-align:center;color:#8888aa;font-size:0.85em;margin-top:6px">{html.escape(caption)}</p>
            </div>''')

        if frame_items:
            frames_html = f'''
        <div style="margin:30px 0">
            <div style="font-size:1.1em;color:#00d4ff;text-transform:uppercase;letter-spacing:2px;font-weight:700;border-bottom:1px solid #1a1a2e;padding-bottom:8px;margin-bottom:16px">Frames cles annotees</div>
            <div style="display:flex;flex-wrap:wrap;gap:16px;justify-content:center">
                {"".join(frame_items)}
            </div>
        </div>'''

    # ── Report text formatted ────────────────────────────────────────────
    report_html = _format_report_html(report.report_text)

    # ── Full HTML ────────────────────────────────────────────────────────
    html_content = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>FORMCHECK — {html.escape(exercise_name)}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a14;color:#e0e0f0;font-family:Inter,system-ui,-apple-system,sans-serif;line-height:1.6}}
.container{{max-width:800px;margin:0 auto;padding:24px 16px}}
@media(max-width:600px){{.container{{padding:12px 10px}}}}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div style="text-align:center;padding:36px 0 24px;border-bottom:2px solid #1a1a2e">
    <div style="font-size:0.8em;letter-spacing:4px;color:#8888aa;text-transform:uppercase;margin-bottom:8px">Analyse biomecanique</div>
    <h1 style="font-size:2.2em;font-weight:800;margin-bottom:4px">
        <span style="color:#00d4ff">FORM</span><span style="color:#fff">CHECK</span>
    </h1>
    <div style="color:#8888aa;font-size:0.8em;letter-spacing:2px;margin-bottom:24px">by ACHZOD</div>
    <div style="font-size:1.4em;color:#fff;font-weight:600;margin-bottom:8px">{html.escape(exercise_name)}</div>
    <div style="font-size:3.8em;font-weight:900;color:{score_col};margin:12px 0">{score}<span style="font-size:0.4em;color:#8888aa">/100</span></div>
    <div style="color:#8888aa;font-size:0.85em">{now}</div>
</div>

<!-- Score breakdown -->
{breakdown_html}

<!-- Frames -->
{frames_html}

<!-- Analyse detaillee -->
<div style="margin:30px 0">
    <div style="font-size:1.1em;color:#00d4ff;text-transform:uppercase;letter-spacing:2px;font-weight:700;border-bottom:1px solid #1a1a2e;padding-bottom:8px;margin-bottom:16px">Analyse detaillee</div>
    <div style="background:#10102a;border-radius:12px;padding:24px;border:1px solid #1a1a2e">
        {report_html}
    </div>
</div>

<!-- Footer -->
<div style="text-align:center;padding:30px 0 20px;border-top:1px solid #1a1a2e;margin-top:30px">
    <p style="color:#00d4ff;font-weight:700;font-size:0.95em">FORMCHECK by ACHZOD</p>
    <p style="color:#8888aa;font-size:0.8em;margin-top:4px">Analyse biomecanique experte</p>
    <p style="color:#8888aa;font-size:0.8em;margin-top:8px">Instagram <a href="https://instagram.com/achzod" style="color:#00d4ff;text-decoration:none">@achzod</a></p>
</div>

</div>
</body>
</html>'''

    return html_content, analysis_id, token
