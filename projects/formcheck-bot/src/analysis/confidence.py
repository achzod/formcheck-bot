"""Score de confiance de l'analyse biomécanique.

Combine la qualité des keypoints, le taux d'occlusion, la qualité vidéo,
le nombre de reps et la cohérence du pattern pour donner un score global
avec des suggestions concrètes d'amélioration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from analysis.pose_extractor import ExtractionResult
from analysis.rep_segmenter import RepSegmentation
from analysis.video_validator import VideoValidation

logger = logging.getLogger("formcheck.confidence")


@dataclass
class ConfidenceDimension:
    """Détail d'une dimension du score de confiance."""
    name: str = ""
    score: float = 0.0
    weight: float = 0.0
    weighted_score: float = 0.0
    detail: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {
            "name": self.name,
            "score": round(self.score, 1),
            "weight": self.weight,
            "weighted_score": round(self.weighted_score, 1),
        }
        if self.detail:
            d["detail"] = self.detail
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


@dataclass
class AnalysisConfidence:
    """Score de confiance de l'analyse."""
    overall_score: int = 0
    keypoint_quality: float = 0.0
    occlusion_rate: float = 0.0
    video_quality: int = 0
    rep_count: int = 0
    consistency: float = 0.0
    reliability: str = "limitee"
    limitations: list[str] = field(default_factory=list)
    # Nouvelles métriques
    suggestions: list[str] = field(default_factory=list)
    dimensions: list[ConfidenceDimension] = field(default_factory=list)
    camera_angle: str = "unknown"  # "lateral", "frontal", "3/4", "unknown"
    analyzable_angles: list[str] = field(default_factory=list)
    non_analyzable_angles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "keypoint_quality": round(self.keypoint_quality, 3),
            "occlusion_rate": round(self.occlusion_rate, 3),
            "video_quality": self.video_quality,
            "rep_count": self.rep_count,
            "consistency": round(self.consistency, 3),
            "reliability": self.reliability,
            "limitations": self.limitations,
            "suggestions": self.suggestions,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "camera_angle": self.camera_angle,
            "analyzable_angles": self.analyzable_angles,
            "non_analyzable_angles": self.non_analyzable_angles,
        }


def _detect_camera_angle(extraction: ExtractionResult) -> tuple[str, list[str], list[str]]:
    """Détecte l'angle de caméra et détermine ce qui est analysable.

    Returns:
        (angle, analyzable_angles, non_analyzable_angles)
    """
    if not extraction.frames:
        return "unknown", [], []

    # Échantillonner quelques frames au milieu
    mid = len(extraction.frames) // 2
    sample_range = slice(max(0, mid - 2), min(len(extraction.frames), mid + 3))
    samples = extraction.frames[sample_range]

    shoulder_widths = []
    hip_widths = []

    for frame in samples:
        lms = {lm["name"]: lm for lm in frame.landmarks}
        ls = lms.get("left_shoulder")
        rs = lms.get("right_shoulder")
        lh = lms.get("left_hip")
        rh = lms.get("right_hip")
        if ls and rs:
            shoulder_widths.append(abs(ls["x"] - rs["x"]))
        if lh and rh:
            hip_widths.append(abs(lh["x"] - rh["x"]))

    if not shoulder_widths:
        return "unknown", [], []

    avg_sw = np.mean(shoulder_widths)

    analyzable = []
    non_analyzable = []

    if avg_sw < 0.04:
        # Vue latérale pure
        angle = "lateral"
        analyzable = ["flexion_genou", "flexion_hanche", "flexion_coude", "inclinaison_tronc", "profondeur"]
        non_analyzable = ["valgus_genou", "symetrie_gauche_droite", "abduction_epaule"]
    elif avg_sw < 0.12:
        # Vue 3/4
        angle = "3/4"
        analyzable = ["flexion_genou", "flexion_hanche", "flexion_coude", "inclinaison_tronc", "valgus_partiel"]
        non_analyzable = ["symetrie_precise", "profondeur_laterale"]
    else:
        # Vue frontale
        angle = "frontal"
        analyzable = ["valgus_genou", "symetrie_gauche_droite", "abduction_epaule", "alignement_frontal"]
        non_analyzable = ["profondeur_squat", "inclinaison_tronc_laterale", "flexion_precise"]

    return angle, analyzable, non_analyzable


def compute_confidence(
    extraction: ExtractionResult,
    validation: VideoValidation,
    reps: RepSegmentation,
) -> AnalysisConfidence:
    """Calcule le score de confiance de l'analyse.

    Args:
        extraction: Résultat de l'extraction de pose.
        validation: Résultat de la validation vidéo.
        reps: Résultat de la segmentation en reps.

    Returns:
        AnalysisConfidence avec score, détails et suggestions.
    """
    result = AnalysisConfidence()
    limitations: list[str] = []
    suggestions: list[str] = []
    dimensions: list[ConfidenceDimension] = []

    # ── 1. Qualité keypoints (poids 35%) ────────────────────────────────
    dim_kp = ConfidenceDimension(name="Qualité articulations", weight=0.35)
    if extraction.frames:
        visibilities = [f.avg_visibility for f in extraction.frames]
        result.keypoint_quality = float(np.mean(visibilities))
    kp_score = result.keypoint_quality * 100
    dim_kp.score = kp_score

    if result.keypoint_quality < 0.4:
        limitations.append("Visibilité des articulations très faible — résultats approximatifs")
        dim_kp.detail = f"Visibilité moyenne: {result.keypoint_quality:.0%}"
        dim_kp.suggestion = "Filme en vêtements ajustés et assure-toi que tout ton corps est visible"
        suggestions.append("Porte des vêtements ajustés pour une meilleure détection des articulations")
    elif result.keypoint_quality < 0.6:
        limitations.append("Visibilité des articulations moyenne — certains angles moins fiables")
        dim_kp.detail = f"Visibilité moyenne: {result.keypoint_quality:.0%}"
        dim_kp.suggestion = "Éloigne-toi légèrement de la caméra pour être entièrement visible"
    else:
        dim_kp.detail = f"Bonne visibilité: {result.keypoint_quality:.0%}"

    dim_kp.weighted_score = kp_score * dim_kp.weight
    dimensions.append(dim_kp)

    # ── 2. Taux d'occlusion (poids 20%) ─────────────────────────────────
    dim_occ = ConfidenceDimension(name="Continuité du tracking", weight=0.20)
    if extraction.total_frames > 0:
        expected = extraction.total_frames
        detected = len(extraction.frames)
        result.occlusion_rate = 1.0 - (detected / expected) if expected > 0 else 1.0
    occlusion_score = (1.0 - result.occlusion_rate) * 100
    dim_occ.score = occlusion_score

    if result.occlusion_rate > 0.4:
        limitations.append("Nombreuses frames sans détection — l'analyse est fragmentée")
        dim_occ.detail = f"Seulement {(1-result.occlusion_rate):.0%} des frames détectées"
        dim_occ.suggestion = "Vérifie qu'aucun objet ne passe devant toi pendant le mouvement"
        suggestions.append("Dégage l'espace autour de toi — aucun rack/équipement entre toi et la caméra")
    elif result.occlusion_rate > 0.2:
        limitations.append("Occlusion partielle — certaines phases du mouvement mal couvertes")
        dim_occ.detail = f"{(1-result.occlusion_rate):.0%} des frames détectées"
        dim_occ.suggestion = "Assure-toi que la caméra te filme en entier du début à la fin"
    else:
        dim_occ.detail = f"Excellent tracking: {(1-result.occlusion_rate):.0%} des frames"

    dim_occ.weighted_score = occlusion_score * dim_occ.weight
    dimensions.append(dim_occ)

    # ── 3. Qualité vidéo (poids 20%) ────────────────────────────────────
    dim_vid = ConfidenceDimension(name="Qualité vidéo", weight=0.20)
    result.video_quality = validation.quality_score
    video_score = float(validation.quality_score)
    dim_vid.score = video_score

    if validation.quality_score < 40:
        limitations.append("Qualité vidéo très faible — résultats indicatifs uniquement")
        dim_vid.detail = f"Score qualité: {validation.quality_score}/100"
        dim_vid.suggestion = "Filme en 720p minimum, avec un bon éclairage, pas de contre-jour"
        suggestions.append("Active le mode 1080p sur ton téléphone et assure un bon éclairage")
    elif validation.quality_score < 65:
        dim_vid.detail = f"Score qualité: {validation.quality_score}/100"
        dim_vid.suggestion = "Un meilleur éclairage améliorerait significativement la précision"
    else:
        dim_vid.detail = f"Bonne qualité: {validation.quality_score}/100"

    dim_vid.weighted_score = video_score * dim_vid.weight
    dimensions.append(dim_vid)

    # ── 4. Nombre de reps (poids 15%) ───────────────────────────────────
    dim_rep = ConfidenceDimension(name="Volume analysé", weight=0.15)
    result.rep_count = reps.total_reps
    if reps.total_reps >= 5:
        rep_score = 100.0
        dim_rep.detail = f"{reps.total_reps} reps — excellent volume pour l'analyse"
    elif reps.total_reps >= 3:
        rep_score = 80.0
        dim_rep.detail = f"{reps.total_reps} reps — bon volume"
        dim_rep.suggestion = "5+ reps donneraient une analyse de fatigue plus complète"
    elif reps.total_reps >= 1:
        rep_score = 50.0
        dim_rep.detail = f"Seulement {reps.total_reps} rep(s) détectée(s)"
        dim_rep.suggestion = "Envoie une série de 5-8 reps pour une analyse de fatigue et de régularité"
        suggestions.append("Filme une série complète de 5-8 reps pour un rapport plus complet")
    else:
        rep_score = 10.0
        limitations.append("Aucune répétition détectée — le mouvement est-il complet ?")
        dim_rep.detail = "Aucune rep détectée"
        dim_rep.suggestion = "Vérifie que tu fais au moins 2-3 mouvements complets dans la vidéo"
        suggestions.append("Assure-toi de filmer au moins 2-3 répétitions complètes")

    dim_rep.score = rep_score
    dim_rep.weighted_score = rep_score * dim_rep.weight
    dimensions.append(dim_rep)

    # ── 5. Cohérence du pattern (poids 10%) ─────────────────────────────
    dim_cons = ConfidenceDimension(name="Régularité du mouvement", weight=0.10)
    if reps.total_reps > 1:
        roms = [r.rom for r in reps.reps if r.rom > 0]
        if roms:
            std = float(np.std(roms))
            mean = float(np.mean(roms))
            cv = std / mean if mean > 0 else 1.0
            result.consistency = max(0.0, min(1.0, 1.0 - cv))
    elif reps.total_reps == 1:
        result.consistency = 0.5
    consistency_score = result.consistency * 100
    dim_cons.score = consistency_score

    if result.consistency < 0.5 and reps.total_reps > 1:
        dim_cons.detail = f"Forte variabilité entre les reps (cohérence: {result.consistency:.0%})"
        dim_cons.suggestion = "Essaie de maintenir la même amplitude à chaque rep"
    elif result.consistency >= 0.8:
        dim_cons.detail = f"Très régulier: cohérence {result.consistency:.0%}"
    else:
        dim_cons.detail = f"Cohérence: {result.consistency:.0%}"

    dim_cons.weighted_score = consistency_score * dim_cons.weight
    dimensions.append(dim_cons)

    # ── Détection angle caméra ──────────────────────────────────────────
    cam_angle, analyzable, non_analyzable = _detect_camera_angle(extraction)
    result.camera_angle = cam_angle
    result.analyzable_angles = analyzable
    result.non_analyzable_angles = non_analyzable

    if cam_angle == "lateral":
        limitations.append("Vue latérale — valgus du genou et symétrie non mesurables")
        suggestions.append("Pour analyser le valgus du genou, filme aussi de face")
    elif cam_angle == "frontal":
        limitations.append("Vue frontale — profondeur et inclinaison du buste moins précises")
        suggestions.append("Pour analyser la profondeur, filme aussi de profil (côté)")
    elif cam_angle == "3/4":
        # Vue 3/4 = bon compromis, pas de suggestion particulière
        pass

    # ── Score global pondéré ────────────────────────────────────────────
    overall = sum(d.weighted_score for d in dimensions)
    result.overall_score = max(0, min(100, int(round(overall))))

    # Fiabilité avec plus de granularité
    if result.overall_score >= 80:
        result.reliability = "excellente"
    elif result.overall_score >= 65:
        result.reliability = "haute"
    elif result.overall_score >= 45:
        result.reliability = "moyenne"
    elif result.overall_score >= 25:
        result.reliability = "limitee"
    else:
        result.reliability = "tres_limitee"

    result.limitations = limitations
    result.suggestions = suggestions
    result.dimensions = dimensions

    logger.info(
        "Confiance: %d/100 (%s) — camera=%s, %d limitations, %d suggestions",
        result.overall_score, result.reliability, cam_angle,
        len(limitations), len(suggestions),
    )
    return result
