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

_ACHZOD_LOGO_DATA_URI = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAASABIAAD/4QBARXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAABAKADAAQAAAABAAABAAAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmACZjs+EJ+/8AAEQgBAAEAAwERAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/bAEMAAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAf/bAEMBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAf/dAAQAIP/aAAwDAQACEQMRAD8A/nT/AOCqn/BUn9ov/go3+0p8T/GHjD4neKV+Bln4w8RaT8FPg7peu6lZ/Dvwj8ObHVJbTw5Kvhy3lttN1bxRrml2djq/irxVqlnNq2r6tO8ccllotjo2j6aAflXQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFAH6p/8ErP+CpP7Rf/AATl/aU+GHi/wf8AE7xUfgbeeMPDulfGv4Paprmo3vw78XfDq91SK08RyN4cuZbnTdJ8UaJpd5fat4V8U6XZwatpGqwJG8t5ot7rGkakAf/Q/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/R/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/S/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/T/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/U/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/V/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/W/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/X/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/Q/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/R/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/S/h/oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKAP/T/h/oAKACgAoA/Zr/AIIU/wDBNr4Zf8FSf219T/Z5+MfiP4k+Ffhr4Z+CXjv4t+JdY+FOq+GdF8YR/wDCO674K8KaNb2upeLvCPjjRIbS417xvpi3yTeH555rdWjtp7WQ+bQB/Yj/AMQb3/BMf/ouv7d//hzv2fv/AKGOgD+C3/go/wDst6N+xT+3R+07+yz4Zv8AxHqv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k/6Fp1z488O2cjLFd3z3EKS6RcAH8LHxY+KvxC+OfxM8dfGL4seKtV8cfEr4leJ9X8Y+NfFetTCbUdb8Qa5dyXl/dy7Fjgt4fMk8qzsLOG3sNNsorfT9PtbWxtre3QA89oAKACgAoAKACgAoAKAP/9P+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9T+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9X+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9b+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9f+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9D+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9H+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9L+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9P+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9T+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9X+H+gAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoA/9b+cn/gqP8A8EtP2k/+CcX7RPxH8GePPhl4ok+C1x4r1/Ufg38ZdI0PUr74ceNPh9dalLceHmj8RwRXOnaR4m0rTLqx07xT4T1W8h1jRdVjciO90e80fWNSAPy1oAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgAoAKACgD9Sv+CXH/BLT9pP/go7+0V8OPBngT4Z+J4/gtb+KtA1L4yfGXV9D1Ox+HHgv4fWupRXHiEyeI54bfTtX8T6tplrfab4W8J6VeTaxrWqyIWSy0az1jWdLAP/2Q=="

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


def _sanitize_breakdown_line(line: str) -> str:
    raw = (line or "").strip()
    if not raw:
        return raw

    norm = (
        raw.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("&", "et")
    )
    max_value: int | None = None
    if "securite" in norm:
        max_value = 40
    elif "efficacite" in norm:
        max_value = 30
    elif "controle" in norm or "tempo" in norm:
        max_value = 20
    elif "symetrie" in norm or "symmetry" in norm:
        max_value = 10

    if max_value is None:
        return raw

    match = re.search(r"(-?\d{1,3})\s*/\s*(\d{1,3})", raw)
    if not match:
        return raw

    try:
        value = int(match.group(1))
    except Exception:
        value = 0
    value = max(0, min(max_value, value))

    return "{}{}/{}{}".format(
        raw[: match.start()],
        value,
        max_value,
        raw[match.end() :],
    )


# Titres de sections attendus du rapport LLM
_SECTION_TITLES = [
    "ANALYSE BIOMECANIQUE",
    "RESUME",
    "AMPLITUDE DE MOUVEMENT",
    "POINTS POSITIFS",
    "CORRECTIONS PRIORITAIRES",
    "ANALYSE DU TEMPO ET DES PHASES",
    "ANALYSE DU TEMPO ET DES REPETITIONS",
    "ANALYSE REP PAR REP",
    "ANALYSE REPETITION PAR REPETITION",
    "INTENSITE DE SERIE",
    "COMPENSATIONS ET BIOMECANIQUE AVANCEE",
    "PROFIL MORPHOLOGIQUE",
    "EXERCICES CORRECTIFS",
    "DECOMPOSITION DU SCORE",
    "ANALYSE AVANCEE",
    "POINT BIOMECANIQUE",
    "RECOMMANDATION POUR LA PROCHAINE VIDEO",
    "RECOMMANDATION",
    "PLAN ACTION",
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
    "REP PAR REP": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
    "PLAN D'ACTION": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4"/><path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.4 0 2.73.32 3.9.89"/></svg>',
}

_SECTION_DISPLAY_TITLES: dict[str, str] = {
    "ANALYSE BIOMECANIQUE": "Analyse Biomecanique",
    "RESUME": "Synthese de Serie",
    "AMPLITUDE DE MOUVEMENT": "Amplitude de Mouvement",
    "POINTS POSITIFS": "Points Forts",
    "CORRECTIONS PRIORITAIRES": "Corrections Prioritaires",
    "ANALYSE DU TEMPO ET DES PHASES": "Tempo et Phases",
    "ANALYSE DU TEMPO ET DES REPETITIONS": "Tempo et Repetitions",
    "ANALYSE REP PAR REP": "Analyse Rep par Rep",
    "ANALYSE REPETITION PAR REPETITION": "Analyse Rep par Rep",
    "INTENSITE DE SERIE": "Intensite et Densite",
    "INTENSITE DE SERIE (DENSITE)": "Intensite et Densite",
    "COMPENSATIONS ET BIOMECANIQUE AVANCEE": "Compensations et Biomecanique Avancee",
    "PROFIL MORPHOLOGIQUE": "Profil Morphologique",
    "EXERCICES CORRECTIFS": "Exercices Correctifs",
    "DECOMPOSITION DU SCORE": "Score Detaille",
    "ANALYSE AVANCEE": "Analyse Avancee",
    "POINT BIOMECANIQUE": "Point Biomecanique Cle",
    "RECOMMANDATION POUR LA PROCHAINE VIDEO": "Prochaine Video",
    "RECOMMANDATION": "Recommandation",
    "PLAN ACTION": "Plan d'Action",
    "PLAN D'ACTION": "Plan d'Action",
}

_REPORT_NOISE_MARKERS = (
    "format de sortie obligatoire",
    "rapport markdown attendu",
    "ne mets rien avant",
    "pas de preambule",
    "pas de thinking process",
    "tu t'adresses directement au client",
    "the user wants me to",
    "the user is asking me to",
    "l'utilisateur me demande",
    "fais exactement une ligne numerotee",
    "une ligne numerotee par repetition",
    "si une information est invisible",
    "si une donnee n'est pas mesurable",
    "titre | pourquoi | impact | cue",
    "action 1",
    "action 2",
    "action 3",
    "completed command line execution",
    "ongoing command line execution",
    "current process",
    "thinking process",
    "task failed",
    "view all files",
    "start chat",
    "invoke motion-analysis skill",
    "invoke frame-extraction skill",
)

_MINIMAX_WRAPPER_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*<\s*/?\s*formcheck_report_md\s*>\s*$", re.IGNORECASE),
    re.compile(r"^\s*```(?:markdown|md|json)?\s*$", re.IGNORECASE),
)

_MINIMAX_FRONTMATTER_PREFIXES = (
    "formcheck",
    "exercice:",
    "exercise:",
    "exercice slug:",
    "display_name_fr:",
    "display_name:",
    "confiance exercice:",
    "confidence:",
    "score global:",
    "score:",
    "repetitions detectees:",
    "repetitions completes:",
    "repetitions partielles:",
    "reps_total:",
    "reps_complete:",
    "reps_partial:",
    "intensite:",
    "intensity_score:",
    "intensity_label:",
    "repos inter-reps moyen:",
    "repos inter reps moyen:",
    "avg_inter_rep_rest_s:",
)

_AI_STYLE_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bdans cette analyse[, ]*", re.IGNORECASE), ""),
    (re.compile(r"\bil est important de noter que\s*", re.IGNORECASE), ""),
    (re.compile(r"\bde maniere generale[, ]*", re.IGNORECASE), ""),
    (re.compile(r"\bglobalement[, ]*", re.IGNORECASE), ""),
    # Vouvoiement → tutoiement
    (re.compile(r"\bvous devez\b", re.IGNORECASE), "tu dois"),
    (re.compile(r"\bvous devriez\b", re.IGNORECASE), "tu devrais"),
    (re.compile(r"\bvous pouvez\b", re.IGNORECASE), "tu peux"),
    (re.compile(r"\bvous pourriez\b", re.IGNORECASE), "tu pourrais"),
    (re.compile(r"\bvous avez\b", re.IGNORECASE), "tu as"),
    (re.compile(r"\bvous etes\b", re.IGNORECASE), "tu es"),
    (re.compile(r"\bvous êtes\b", re.IGNORECASE), "tu es"),
    (re.compile(r"\bvos muscles\b", re.IGNORECASE), "tes muscles"),
    (re.compile(r"\bvos bras\b", re.IGNORECASE), "tes bras"),
    (re.compile(r"\bvos jambes\b", re.IGNORECASE), "tes jambes"),
    (re.compile(r"\bvos epaules\b", re.IGNORECASE), "tes epaules"),
    (re.compile(r"\bvotre\b", re.IGNORECASE), "ton"),
    (re.compile(r"\bvos\b", re.IGNORECASE), "tes"),
)

# MiniMax foreign word → French replacements.  Keyed by lowercase foreign word.
_FOREIGN_WORD_MAP: dict[str, str] = {
    # English
    "noticeable": "perceptible", "maintained": "maintenue", "compensate": "compenser",
    "overuse": "surutilisation", "shortcuts": "raccourcis", "shortcut": "raccourci",
    "window": "fenetre", "superior": "superieur", "hold": "tenue", "holding": "tenue",
    "loss": "perte", "pattern": "schema", "patterns": "schemas",
    "increase": "augmente", "increases": "augmente", "increasing": "croissante",
    "decrease": "diminue", "decreases": "diminue",
    "either": "soit", "neither": "ni", "whether": "si",
    "however": "cependant", "although": "bien que", "though": "bien que",
    "preferable": "preferable", "preferably": "de preference",
    "emphasis": "accent", "emphasize": "accentuer",
    "noticeable": "perceptible", "notably": "notamment",
    "powerfully": "puissamment", "powerful": "puissant",
    "breathing": "respiration", "breathe": "respire",
    "instead": "plutot", "rather": "plutot",
    "commendable": "remarquable", "remarkable": "remarquable",
    "locker": "verrouiller", "locking": "verrouillage", "locked": "verrouille",
    "compensated": "compense", "compensating": "compensatoire",
    "stabilize": "stabiliser", "stabilized": "stabilise", "stabilizing": "stabilisant",
    "stretch": "etirement", "stretching": "etirement",
    "feedback": "retour", "output": "resultat", "input": "apport",
    "workout": "seance", "training": "entrainement",
    "recovery": "recuperation", "recover": "recuperer",
    "overload": "surcharge", "overloading": "surcharge",
    "challenge": "defi", "challenging": "exigeant",
    "weakness": "faiblesse", "weakness": "faiblesse",
    "strength": "force", "strong": "fort", "stronger": "plus fort",
    "improve": "ameliorer", "improved": "ameliore", "improvement": "amelioration",
    "properly": "correctement", "properly": "correctement",
    "throughout": "tout au long", "overall": "globalement",
    "fatigue": "fatigue",  # same in both languages
    "squeeze": "contraction", "squeezing": "contraction",
    "engaged": "engage", "engagement": "engagement",
    "range": "amplitude", "full range": "amplitude complete",
    "setup": "mise en place", "set up": "mise en place",
    "lockout": "verrouillage", "lock out": "verrouillage", "locked out": "verrouille",
    "observed": "observe", "observing": "observant",
    "target": "cible", "targeting": "ciblant", "targeted": "cible",
    "rotate": "tourne", "rotates": "tourne", "rotating": "en rotation",
    "dangerous": "dangereux",
    "connection": "connexion", "connections": "connexions",
    "mind-muscle connection": "connexion neuromusculaire",
    "recommend": "recommande", "recommende": "recommande", "recommends": "recommande",
    "transferts": "transfere",
    "failure": "echec", "until failure": "jusqu'a l'echec",
    "resting": "repos", "rest": "repos",
    "spotter": "pareur", "spotting": "parade",
    "benchmark": "reference", "baseline": "reference",
    "tracking": "suivi", "track": "suivre",
    "peak": "pic", "peaked": "atteint un pic",
    "pushing": "poussee", "pulling": "traction",
    "gripping": "prise", "grip": "prise",
    # Spanish/Portuguese
    "beneficios": "benefique", "beneficio": "benefice",
    "tener": "garder", "ayudar": "aider", "ayudarte": "t'aider",
    "reducir": "reduire", "correcta": "correcte", "correcto": "correct",
    "fisiologicamente": "physiologiquement", "fisiologiquement": "physiologiquement",
    "muscular": "musculaire", "articular": "articulaire",
    "estabilizar": "stabiliser",
    # More English/Spanish from reports #55-#61
    "adjustment": "ajustement", "adjustments": "ajustements",
    "exercises": "exercices", "exercise": "exercice",
    "grind": "effort intense", "grinding": "effort intense",
    "muscle fibers": "fibres musculaires", "muscle fiber": "fibre musculaire",
    "aumentar": "augmenter", "aumenter": "augmenter",
    "locking": "verrouillage",
    "pousséer": "pousser", "pousséant": "poussant",
    "weights": "charge", "weight": "charge",
    "transferred": "transfere", "transfer": "transferer",
    "accumulate": "accumuler", "accumulated": "accumulee",
    "adequate": "adequat", "adequately": "adequatement",
    "movement": "mouvement", "movements": "mouvements",
    "compromet": "compromet",  # already French, keep
    "deductionnels": "deduits",
    "sticking point": "point de blocage",
    "rep range": "fourchette de repetitions",
    "time under tension": "temps sous tension",
    "mind-muscle": "neuromusculaire",
    "burnout": "epuisement", "burn-out": "epuisement",
    # Common English glue words
    "instead of": "au lieu de", "rather than": "plutot que",
    "in order to": "afin de", "due to": "en raison de",
    "as well as": "ainsi que", "such as": "comme",
    # Hybrid / invented
    "propush": "poussee", "beurreinstead of": "beurre au lieu de",
    "beurreinstead": "beurre plutot que",
    # Italian/Portuguese/invented
    "skiper": "sauter", "skipper": "sauter", "skiper": "sauter",
    "apoio": "appui", "apoyo": "appui",
    "isometriche": "isometrique", "isometrica": "isometrique",
    "ressentiraís": "ressentirais", "sentirías": "sentirais",
}

_FOREIGN_WORD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b{}\b".format(re.escape(word)), re.IGNORECASE), repl)
    for word, repl in _FOREIGN_WORD_MAP.items()
]
# Catch-all: strip words ending in obvious English suffixes not shared with French
_ENGLISH_SUFFIX_CLEANUP = re.compile(
    r"\b\w+(?:ingly|ously|fully|edly|ness|ship)\b", re.IGNORECASE
)
_CJK_CHAR_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")


def _get_section_icon(title: str) -> str:
    upper = title.upper()
    for key, icon in _SECTION_ICONS.items():
        if key in upper:
            return icon
    return ""


def _contains_cjk_characters(text: str) -> bool:
    return bool(_CJK_CHAR_PATTERN.search(str(text or "")))


def _md_inline_to_html(text: str) -> str:
    """Convert inline markdown (bold, italic) to HTML. Input must already be html-escaped."""
    # **bold** or __bold__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # *italic* or _italic_ (but not inside words)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'<em>\1</em>', text)
    return text


def _normalize_section_title(raw_title: str) -> str:
    upper = raw_title.strip().upper()
    for canonical, display in _SECTION_DISPLAY_TITLES.items():
        if upper.startswith(canonical):
            return display
    return raw_title.strip()


_ORPHAN_NUM_RE = re.compile(r"^(\d+)\.\s*$")
_NUMBERED_LINE_RE = re.compile(r"^(\d+)\.\s+(.*)")
_SECTION_HEADER_RE = re.compile(
    r"^(?:#{1,4}\s+)?(" + "|".join(re.escape(t) for t in _SECTION_TITLES) + r")",
    re.IGNORECASE,
)
_TIMESTAMP_PLACEHOLDER_RE = re.compile(r"\b0{1,2}:00\s*[-–]\s*0{1,2}:00\b")


def _merge_orphan_numbered_lines(lines: list[str]) -> list[str]:
    """Merge orphan numbered lines ('1.\\n content') into a single line ('1. content').

    MiniMax sometimes outputs the number on its own line followed by the content
    on the next line.  This pass merges them so downstream parsers see a proper
    numbered entry.
    """
    merged: list[str] = []
    i = 0
    while i < len(lines):
        m = _ORPHAN_NUM_RE.match(lines[i])
        if m:
            num = m.group(1)
            # Look ahead for the content line (skip blank lines).
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and not _ORPHAN_NUM_RE.match(lines[j]) and not _SECTION_HEADER_RE.match(lines[j]):
                merged.append(f"{num}. {lines[j].strip()}")
                i = j + 1
                continue
            # Orphan number with no following content — drop it.
            i += 1
            continue
        merged.append(lines[i])
        i += 1
    return merged


def _remove_empty_numbered_entries(lines: list[str]) -> list[str]:
    """Remove numbered entries that have no meaningful content after the number."""
    out: list[str] = []
    for line in lines:
        m = _NUMBERED_LINE_RE.match(line)
        if m:
            content = m.group(2).strip()
            # Consider empty if content is just punctuation/whitespace/pipe
            if not content or re.fullmatch(r"[\s|.:,;_\-–—]*", content):
                continue
        out.append(line)
    return out


def _cap_plan_action_items(lines: list[str], max_items: int = 3) -> list[str]:
    """Truncate numbered items in PLAN ACTION / PLAN D'ACTION section to *max_items*."""
    out: list[str] = []
    in_plan = False
    plan_item_count = 0
    for line in lines:
        upper = line.strip().upper()
        # Detect section transitions
        if _SECTION_HEADER_RE.match(line):
            if "PLAN" in upper and "ACTION" in upper:
                in_plan = True
                plan_item_count = 0
            else:
                in_plan = False
            out.append(line)
            continue
        if in_plan and _NUMBERED_LINE_RE.match(line):
            plan_item_count += 1
            if plan_item_count > max_items:
                continue  # drop excess items
        out.append(line)
    return out


_ANY_TIMESTAMP_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})\b")


def _fix_placeholder_timestamps(lines: list[str]) -> list[str]:
    """Fix bad timestamps in rep-by-rep lines.

    Handles two cases:
    1. All zeros (00:00-00:00) — replace with ~3s/rep estimates.
    2. Unrealistically short durations (<2s per rep) — replace with ~3s/rep estimates.
    """
    # First pass: detect if timestamps are unrealistic across all reps
    rep_durations: list[float] = []
    for line in lines:
        m = _NUMBERED_LINE_RE.match(line)
        if not m:
            continue
        ts = _ANY_TIMESTAMP_RE.search(line)
        if not ts:
            continue
        start_s = int(ts.group(1)) * 60 + int(ts.group(2))
        end_s = int(ts.group(3)) * 60 + int(ts.group(4))
        dur = end_s - start_s
        if dur >= 0:
            rep_durations.append(dur)

    # If 25%+ of reps have <2s duration or are all zeros, regenerate all timestamps
    needs_regen = (
        not rep_durations
        or (sum(1 for d in rep_durations if d < 2) > len(rep_durations) * 0.25)
    )

    out: list[str] = []
    for line in lines:
        m = _NUMBERED_LINE_RE.match(line)
        if m and needs_regen:
            ts_match = _ANY_TIMESTAMP_RE.search(line) or _TIMESTAMP_PLACEHOLDER_RE.search(line)
            if ts_match:
                num = int(m.group(1))
                start_s = (num - 1) * 3
                end_s = num * 3
                start_ts = f"{start_s // 60}:{start_s % 60:02d}"
                end_ts = f"{end_s // 60}:{end_s % 60:02d}"
                line = line[:ts_match.start()] + f"{start_ts} - {end_ts}" + line[ts_match.end():]
        elif m and _TIMESTAMP_PLACEHOLDER_RE.search(line):
            # Individual zero timestamps even if overall durations are OK
            num = int(m.group(1))
            start_s = (num - 1) * 3
            end_s = num * 3
            start_ts = f"{start_s // 60}:{start_s % 60:02d}"
            end_ts = f"{end_s // 60}:{end_s % 60:02d}"
            line = _TIMESTAMP_PLACEHOLDER_RE.sub(f"{start_ts} - {end_ts}", line, count=1)
        out.append(line)
    return out


def _renumber_after_cleanup(lines: list[str]) -> list[str]:
    """Re-number items sequentially within each section after items have been removed.

    This ensures that if items 2 and 5 were dropped, the remaining items are
    numbered 1, 2, 3... instead of having gaps.
    """
    out: list[str] = []
    current_counter = 0
    in_numbered_section = False
    for line in lines:
        # Section header resets numbering
        if _SECTION_HEADER_RE.match(line):
            current_counter = 0
            in_numbered_section = False
            out.append(line)
            continue
        m = _NUMBERED_LINE_RE.match(line)
        if m:
            if not in_numbered_section:
                in_numbered_section = True
                current_counter = 0
            current_counter += 1
            content = m.group(2)
            out.append(f"{current_counter}. {content}")
            continue
        # Non-numbered line inside a section — keep numbering state
        out.append(line)
    return out


def _remove_empty_sections(lines: list[str]) -> list[str]:
    """Remove section headers that have no content between them and the next header.

    A section is considered empty if there are no non-blank lines between its
    header and the next section header (or end of document).
    """
    # Identify section header indices
    header_indices: list[int] = []
    for i, line in enumerate(lines):
        if _SECTION_HEADER_RE.match(line):
            header_indices.append(i)

    if not header_indices:
        return lines

    # Find which headers have no content
    empty_header_indices: set[int] = set()
    for idx_pos, header_idx in enumerate(header_indices):
        # Find next header or end
        next_boundary = header_indices[idx_pos + 1] if idx_pos + 1 < len(header_indices) else len(lines)
        # Check if any non-blank content exists between this header and the next
        has_content = any(
            lines[j].strip()
            for j in range(header_idx + 1, next_boundary)
        )
        if not has_content:
            empty_header_indices.add(header_idx)

    if not empty_header_indices:
        return lines

    return [line for i, line in enumerate(lines) if i not in empty_header_indices]


def _clean_report_text_for_rendering(report_text: str) -> str:
    raw_lines = [str(line or "") for line in str(report_text or "").splitlines()]
    out_lines: list[str] = []
    for raw_line in raw_lines:
        if any(pattern.match(raw_line) for pattern in _MINIMAX_WRAPPER_LINE_PATTERNS):
            continue

        line = raw_line.strip()
        if _contains_cjk_characters(line):
            continue
        # Strip entire words containing Arabic/Hebrew/Cyrillic characters (MiniMax glitch)
        line = re.sub(r'\S*[\u0400-\u04FF\u0600-\u06FF\u0590-\u05FF]+\S*', '', line).strip()
        if not line:
            continue
        low = line.lower()
        low_normalized = re.sub(r"^[\-\*•#\s]+", "", low).strip()
        # Drop obvious technical traces and code artifacts.
        if "```" in line:
            continue
        if re.search(r"[A-Za-z0-9_/.-]+\.py:\d+", line):
            continue
        if line.startswith("Traceback (most recent call last):"):
            continue
        if line.startswith("{") and line.endswith("}"):
            continue
        # Remove raw JSON debris or orphan braces from bad generations.
        if line in {"{", "}", "[", "]"}:
            continue
        if low_normalized in {"formcheck", "# formcheck"}:
            continue
        if any(low_normalized.startswith(prefix) for prefix in _MINIMAX_FRONTMATTER_PREFIXES):
            continue
        if any(marker in low for marker in _REPORT_NOISE_MARKERS):
            continue
        if re.match(r"^[\-\*]\s*(point|action)\s+\d+\s*$", low):
            continue
        if re.match(r"^#\s*formcheck$", low):
            continue
        if low in {"x/40", "x/30", "x/20", "x/10"}:
            continue
        # Keep semantic value while avoiding a raw placeholder.
        line = re.sub(r"\bNON\s+MESURABLE\b", "Non mesurable sur cette prise", line, flags=re.IGNORECASE)
        for pattern, replacement in _AI_STYLE_REWRITES:
            line = pattern.sub(replacement, line)
        # Fix merged words (MiniMax drops spaces: "Tumaintiens" → "Tu maintiens")
        line = re.sub(r'\b([A-ZÀ-Ü][a-zà-ü]{1,3})(maintien|gardes?|reste|semble|montre|utilis|commenc|augment|cherch|accept|perme|termin)', r'\1 \2', line)
        line = re.sub(r'\b(tes|ses|les|des|nos|vos|ces|mes)(appui|articul|abdomi|omo|muscle|bras|pied|jambe|genou|hanche|épaul)', r'\1 \2', line)
        # Replace foreign words with French equivalents
        for pattern, replacement in _FOREIGN_WORD_PATTERNS:
            line = pattern.sub(replacement, line)
        # Strip remaining obvious English-suffix words
        line = _ENGLISH_SUFFIX_CLEANUP.sub("", line)
        line = re.sub(r"^\s*(?:[-–—]{2,}|[-*•])\s*", "", line)
        line = re.sub(r"\s{2,}", " ", line).strip(" -–—_")
        if re.fullmatch(r"[\s\-–—_=:|.]+", line or ""):
            continue
        if not line:
            continue
        out_lines.append(line)

    # --- Post-processing passes on collected lines ---
    out_lines = _merge_orphan_numbered_lines(out_lines)
    out_lines = _remove_empty_numbered_entries(out_lines)
    out_lines = _cap_plan_action_items(out_lines, max_items=3)
    out_lines = _fix_placeholder_timestamps(out_lines)
    out_lines = _renumber_after_cleanup(out_lines)
    out_lines = _remove_empty_sections(out_lines)

    return "\n".join(out_lines).strip()


def _is_known_section_header(line: str) -> bool:
    upper = str(line or "").strip().upper()
    if not upper:
        return False
    return any(upper.startswith(title) for title in _SECTION_TITLES)


def _extract_minimax_frontmatter(report_text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    key_aliases = {
        "exercice": "exercise_display",
        "exercise": "exercise_display",
        "exercice slug": "exercise_slug",
        "exercise slug": "exercise_slug",
        "confiance exercice": "confidence",
        "confidence": "confidence",
        "score global": "score",
        "score": "score",
        "repetitions detectees": "reps_detected",
        "repetitions completes": "reps_complete",
        "repetitions partielles": "reps_partial",
        "reps_total": "reps_detected",
        "reps_complete": "reps_complete",
        "reps_partial": "reps_partial",
        "intensite": "intensity",
        "intensity_score": "intensity",
        "intensity_label": "intensity_label",
        "repos inter-reps moyen": "avg_rest",
        "repos inter reps moyen": "avg_rest",
        "avg_inter_rep_rest_s": "avg_rest",
    }

    for raw_line in str(report_text or "").splitlines():
        line = re.sub(r"^\s*[-*•]\s*", "", str(raw_line or "")).strip()
        if not line:
            continue
        if any(pattern.match(line) for pattern in _MINIMAX_WRAPPER_LINE_PATTERNS):
            continue
        upper_line = re.sub(r"^[#\s]+", "", line).strip().upper()
        if _is_known_section_header(upper_line):
            break
        if ":" not in line:
            continue
        raw_key, raw_value = line.split(":", 1)
        key = raw_key.strip().lower().replace("é", "e").replace("è", "e")
        value = raw_value.strip()
        canonical = key_aliases.get(key)
        if not canonical or not value:
            continue
        metrics[canonical] = value

    score_text = str(metrics.get("score", "") or "")
    score_match = re.search(r"(-?\d{1,3})\s*/\s*100", score_text)
    if score_match:
        metrics["score"] = max(0, min(100, int(score_match.group(1))))

    confidence_text = str(metrics.get("confidence", "") or "")
    confidence_match = re.search(r"(-?\d+(?:[.,]\d+)?)", confidence_text)
    if confidence_match:
        confidence_val = float(confidence_match.group(1).replace(",", "."))
        if confidence_val <= 1.0:
            confidence_val *= 100.0
        metrics["confidence"] = max(0, min(100, int(round(confidence_val))))

    for key in ("reps_detected", "reps_complete", "reps_partial"):
        number_text = str(metrics.get(key, "") or "")
        number_match = re.search(r"(-?\d+)", number_text)
        if number_match:
            metrics[key] = max(0, int(number_match.group(1)))

    intensity_text = str(metrics.get("intensity", "") or "")
    intensity_match = re.search(r"(-?\d{1,3})\s*/\s*100(?:\s*\(([^)]+)\))?", intensity_text)
    if intensity_match:
        metrics["intensity_score"] = max(0, min(100, int(intensity_match.group(1))))
        label = (intensity_match.group(2) or "").strip()
        if label:
            metrics["intensity_label"] = label
    elif intensity_text:
        number_match = re.search(r"(-?\d{1,3})", intensity_text)
        if number_match:
            metrics["intensity_score"] = max(0, min(100, int(number_match.group(1))))

    rest_text = str(metrics.get("avg_rest", "") or "")
    rest_match = re.search(r"(-?\d+(?:[.,]\d+)?)", rest_text)
    if rest_match:
        metrics["avg_rest"] = max(0.0, float(rest_match.group(1).replace(",", ".")))

    return metrics


def _extract_section_excerpt(report_text: str, section_title: str) -> str:
    cleaned = _clean_report_text_for_rendering(report_text)
    if not cleaned:
        return ""

    target = section_title.strip().upper()
    lines = [line.strip() for line in cleaned.splitlines()]
    collecting = False
    buffer: list[str] = []

    for line in lines:
        if not line:
            if collecting and buffer:
                break
            continue
        upper = line.upper()
        if upper.startswith(target):
            collecting = True
            continue
        if collecting and _is_known_section_header(line):
            break
        if collecting:
            buffer.append(line)
            if len(buffer) >= 2:
                break

    return " ".join(buffer[:2]).strip()


def _coerce_metric_int(value: Any, default: int = 0, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        if isinstance(value, str):
            match = re.search(r"-?\d+(?:[.,]\d+)?", value)
            if not match:
                raise ValueError("no numeric token")
            value = match.group(0).replace(",", ".")
        out = int(round(float(value)))
    except Exception:
        out = int(default)
    if minimum is not None:
        out = max(minimum, out)
    if maximum is not None:
        out = min(maximum, out)
    return out


def _coerce_metric_float(value: Any, default: float = 0.0, *, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        if isinstance(value, str):
            match = re.search(r"-?\d+(?:[.,]\d+)?", value)
            if not match:
                raise ValueError("no numeric token")
            value = match.group(0).replace(",", ".")
        out = float(value)
    except Exception:
        out = float(default)
    if minimum is not None:
        out = max(minimum, out)
    if maximum is not None:
        out = min(maximum, out)
    return out


def _format_report_html(report_text: str) -> str:
    """Convertit le texte du rapport LLM en HTML propre, parse par sections."""
    text = html.escape(html.unescape(_clean_report_text_for_rendering(report_text)), quote=False)
    # Strip ALL markdown artifacts aggressively
    text = re.sub(r'^[\-\*•]\s+', '', text, flags=re.MULTILINE)     # bullet lists
    text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)      # headers
    text = re.sub(r'^-{2,}$', '', text, flags=re.MULTILINE)         # --- separators
    text = text.replace(' — ', '. ')                                  # em dashes to periods
    text = text.replace(' -- ', '. ')                                 # double dashes to periods
    lines = text.split("\n")
    html_parts: list[str] = []
    in_section = False
    section_count = 0
    current_section_title = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div style="height:8px"></div>')
            continue

        # Skip --- separators
        if re.match(r"^-{3,}$", stripped):
            continue

        # Check if this is a section header
        header_candidate = html.unescape(stripped).strip()
        upper = header_candidate.upper()
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
            current_section_title = upper
            icon = _get_section_icon(header_candidate)
            display_title = html.escape(_normalize_section_title(header_candidate))
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
                f'<div class="section-header">{icon_html}{display_title}</div>'
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
            safe_line = _sanitize_breakdown_line(stripped)
            html_parts.append(f'<p class="score-cat">{safe_line}</p>')
            continue

        # Numbered items (corrections, exercices)
        num_match = re.match(r"^(\d+)\.\s*(.*)", stripped)
        if num_match:
            num = num_match.group(1)
            rest_raw = num_match.group(2).strip()
            # Safety net: skip empty numbered items that survived cleaning
            if not rest_raw or re.fullmatch(r"[\s|.:,;_\-–—]*", rest_raw):
                continue
            if "|" in rest_raw:
                segments = [seg.strip() for seg in rest_raw.split("|") if seg.strip()]
                if len(segments) >= 2:
                    lead = segments[0]
                    timing = segments[1]
                    comment = " | ".join(segments[2:]).strip() if len(segments) > 2 else ""
                    if re.search(r"\brep", lead, re.IGNORECASE) or re.search(r"\d{2}:\d{2}", timing):
                        rep_title = _md_inline_to_html(lead)
                        rep_timing = _md_inline_to_html(timing)
                        rep_comment = _md_inline_to_html(comment)
                        rep_raw_line = "{} | {}{}".format(
                            lead,
                            timing,
                            (" | " + comment) if comment else "",
                        )
                        rep_comment_html = (
                            f'<div class="rep-comment">{rep_comment}</div>'
                            if rep_comment
                            else ""
                        )
                        html_parts.append(
                            f'<div class="numbered-item rep-item">'
                            f'<span class="item-num">{num}</span>'
                            f'<div class="rep-main">'
                            f'<div class="rep-title">{rep_title}</div>'
                            f'<div class="rep-time">{rep_timing}</div>'
                            f"{rep_comment_html}"
                            f'<span style="display:none">{html.escape(rep_raw_line)}</span>'
                            f"</div>"
                            f"</div>"
                        )
                        continue
                    if "CORRECTIONS PRIORITAIRES" in current_section_title:
                        observation = timing
                        impact = segments[2] if len(segments) > 2 else ""
                        cue = segments[3] if len(segments) > 3 else ""
                        detail_rows: list[str] = []
                        if observation:
                            detail_rows.append(
                                '<div class="correction-detail"><span class="correction-detail-label">Observation</span>{}</div>'.format(
                                    _md_inline_to_html(observation)
                                )
                            )
                        if impact:
                            detail_rows.append(
                                '<div class="correction-detail"><span class="correction-detail-label">Impact</span>{}</div>'.format(
                                    _md_inline_to_html(impact)
                                )
                            )
                        if cue:
                            detail_rows.append(
                                '<div class="correction-detail"><span class="correction-detail-label">Cue</span>{}</div>'.format(
                                    _md_inline_to_html(cue)
                                )
                            )
                        html_parts.append(
                            f'<div class="numbered-item correction-item">'
                            f'<span class="item-num">{num}</span>'
                            f'<div class="correction-main">'
                            f'<div class="correction-title">{_md_inline_to_html(lead)}</div>'
                            f'{"".join(detail_rows)}'
                            f"</div>"
                            f"</div>"
                        )
                        continue
            rest = _md_inline_to_html(rest_raw)
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
        aliases: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
            ("Securite", (("securite",),)),
            ("Efficacite technique", (("efficacite", "technique"), ("efficacite",), ("technique",))),
            ("Controle et tempo", (("controle", "tempo"), ("controle",), ("tempo",))),
            ("Symetrie", (("symetrie",), ("symmetry",))),
        )
        for canonical, token_groups in aliases:
            value = None
            for key, raw_val in report.score_breakdown.items():
                norm_key = str(key).lower().replace("é", "e").replace("è", "e")
                if any(all(token in norm_key for token in group) for group in token_groups):
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
    model_used = str(getattr(report, "model_used", "") or "").strip().lower()
    source_metrics = _extract_minimax_frontmatter(report.report_text) if "minimax" in model_used else {}

    score = _coerce_metric_int(report.score if report.score is not None else source_metrics.get("score", 0), int(report.score or 0), minimum=0, maximum=100)
    exercise_name = str(
        report.exercise_display
        or source_metrics.get("exercise_display")
        or "Exercice"
    ).strip()
    summary_line = _extract_section_excerpt(report.report_text, "RESUME")

    reps_total = _coerce_metric_int(source_metrics.get("reps_detected", 0), 0, minimum=0)
    intensity_score = _coerce_metric_int(source_metrics.get("intensity_score", 0), 0, minimum=0, maximum=100)
    intensity_label = str(source_metrics.get("intensity_label", "") or "").strip()
    avg_rest = _coerce_metric_float(source_metrics.get("avg_rest", 0.0), 0.0, minimum=0.0)
    detection_conf = _coerce_metric_int(source_metrics.get("confidence", 0), 0, minimum=0, maximum=100)

    if not source_metrics and pipeline_result and getattr(pipeline_result, "reps", None):
        reps = pipeline_result.reps
        reps_total = int(getattr(reps, "total_reps", 0) or 0)
        intensity_score = int(getattr(reps, "intensity_score", 0) or 0)
        intensity_label = str(getattr(reps, "intensity_label", "indeterminee") or "indeterminee")
        avg_rest = float(getattr(reps, "avg_inter_rep_rest_s", 0.0) or 0.0)
    if not source_metrics and pipeline_result and getattr(pipeline_result, "detection", None):
        detection_conf = int(round(float(getattr(pipeline_result.detection, "confidence", 0.0) or 0.0) * 100.0))

    metric_chips: list[str] = [
        '<div class="metric-chip"><span class="metric-chip-label">Score global</span><span class="metric-chip-value">{}/100</span></div>'.format(
            max(0, min(100, score))
        )
    ]
    if reps_total > 0:
        metric_chips.append(
            '<div class="metric-chip"><span class="metric-chip-label">Repetitions</span><span class="metric-chip-value">{} detectees</span></div>'.format(
                reps_total
            )
        )
    if intensity_score > 0:
        intensity_value = "{} /100".format(max(0, min(100, intensity_score)))
        if intensity_label:
            intensity_value = "{} ({})".format(intensity_value, html.escape(intensity_label))
        metric_chips.append(
            '<div class="metric-chip"><span class="metric-chip-label">Intensite</span><span class="metric-chip-value">{}</span></div>'.format(
                intensity_value
            )
        )
    if ("avg_rest" in source_metrics) or avg_rest > 0:
        metric_chips.append(
            '<div class="metric-chip"><span class="metric-chip-label">Repos inter-reps</span><span class="metric-chip-value">{:.2f}s</span></div>'.format(
                avg_rest
            )
        )
    if detection_conf > 0:
        metric_chips.append(
            '<div class="metric-chip"><span class="metric-chip-label">Confiance exo</span><span class="metric-chip-value">{}%</span></div>'.format(
                max(0, min(100, detection_conf))
            )
        )

    summary_html = (
        '<p class="report-p intro-summary">{}</p>'.format(_md_inline_to_html(html.escape(summary_line)))
        if summary_line
        else ""
    )

    return """
    <div class="card fade-in client-intro" style="animation-delay:0.18s">
        <div class="card-header">Synthese de serie</div>
        <p class="report-p"><strong>{exercise}</strong></p>
        {summary_html}
        <div class="metric-chips">{metric_chips}</div>
    </div>
    """.format(
        exercise=html.escape(exercise_name),
        summary_html=summary_html,
        metric_chips="".join(metric_chips),
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

    greeting = "Voici la lecture de ta serie."

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
    lines.append("ANALYSE BIOMECANIQUE: {}".format(exercise))
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


def _should_keep_minimax_raw_report(report_text: str) -> bool:
    """Accept short but structurally valid MiniMax reports instead of forcing generic fallback."""
    cleaned = _clean_report_text_for_rendering(report_text)
    if not cleaned:
        return False

    sections = _count_known_sections(cleaned)
    rep_lines = len(
        re.findall(
            r"(?im)^\s*\d+\.\s*(?:rep(?:etition)?|r[eé]p[eé]tition)\b",
            cleaned,
        )
    )
    has_resume = bool(re.search(r"(?im)^\s*resume\b", cleaned))
    has_tempo = bool(re.search(r"(?im)^\s*analyse du tempo", cleaned))
    has_plan = bool(re.search(r"(?im)^\s*plan(?:\s+d['’]action|\s+action)\b", cleaned))

    # Typical short valid structure: RESUME + ANALYSE REP PAR REP + at least one rep line.
    if sections >= 2 and rep_lines >= 1:
        return True
    # Medium valid structure even without rep-by-rep.
    if sections >= 3 and (has_resume or has_tempo or has_plan):
        return True
    # Long-enough cleaned narrative with at least one canonical section.
    if len(cleaned) >= 220 and sections >= 1:
        return True
    return False


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

    # ── Logo ACHZOD (base64 embedded) ─────────────────────────────────────
    logo_data_uri = _ACHZOD_LOGO_DATA_URI

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
        normalized = _normalized_breakdown(report)
        gauges = []
        for label, key, max_val, description in breakdown_config:
            val = int(normalized.get(label, 0) or 0)
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

    # ── Rapport client: MiniMax garde strictement son fond, fallback local reserve aux autres modes ──
    raw_report_text = (report.report_text or "").strip()
    model_used = str(getattr(report, "model_used", "") or "").strip().lower()
    use_minimax_raw = ("minimax" in model_used)
    if use_minimax_raw:
        use_deterministic_fallback = False
    else:
        quality_score = _report_quality_score(raw_report_text)
        threshold = 30 if use_minimax_raw else 56
        use_deterministic_fallback = quality_score < threshold
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
<title>FORMCHECK | {html.escape(exercise_name)}</title>
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
.metric-chips{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
    gap:10px;
    margin-top:16px
}}
.metric-chip{{
    background:#e5e0d5;
    border:1px solid #d5cfc5;
    border-radius:12px;
    padding:12px 14px
}}
.metric-chip-label{{
    display:block;
    font-size:0.74em;
    text-transform:uppercase;
    letter-spacing:1.2px;
    color:#8a8070;
    margin-bottom:4px
}}
.metric-chip-value{{
    display:block;
    font-size:0.95em;
    line-height:1.4;
    color:#1a1a1a;
    font-weight:700
}}
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
.correction-item{{align-items:flex-start}}
.correction-main{{display:flex;flex-direction:column;gap:8px;min-width:0}}
.correction-title{{font-weight:700;color:#1a1a1a;font-size:0.96em;line-height:1.45}}
.correction-detail{{
    font-size:0.9em;
    line-height:1.65;
    color:#1a1a1a;
    padding-left:12px;
    border-left:2px solid #d5cfc5
}}
.correction-detail-label{{
    display:block;
    color:#5a4a3a;
    font-size:0.76em;
    font-weight:700;
    letter-spacing:0.8px;
    text-transform:uppercase;
    margin-bottom:2px
}}
.rep-item{{align-items:flex-start;margin:12px 0}}
.rep-main{{display:flex;flex-direction:column;gap:2px;min-width:0}}
.rep-title{{font-weight:700;color:#1a1a1a;font-size:0.95em;line-height:1.4}}
.rep-time{{font-size:0.83em;color:#5a4a3a;font-weight:600;letter-spacing:0.2px}}
.rep-comment{{font-size:0.93em;color:#1a1a1a;line-height:1.65;margin-top:2px}}

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
    <img src="{logo_data_uri}" alt="ACHZOD" style="width:60px;height:60px;border-radius:12px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,0.1)">
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
    <img src="{logo_data_uri}" alt="ACHZOD" style="width:40px;height:40px;border-radius:8px;margin-bottom:12px;opacity:0.8">
    <div class="footer-brand">FORMCHECK by ACHZOD</div>
    <div class="footer-sub" style="margin-top:6px">
        <a href="https://achzodcoaching.com" class="footer-link">achzodcoaching.com</a>
    </div>
    <div class="footer-sub" style="margin-top:4px">
        <a href="https://instagram.com/achzod" class="footer-link">@achzod</a> | <a href="mailto:coaching@achzodcoaching.com" class="footer-link">coaching@achzodcoaching.com</a>
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
        <div class="card-header">Courbe d'angle : {html.escape(label)}</div>
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
        <div class="card-header">Timeline des repetitions : {reps.total_reps} reps</div>
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
