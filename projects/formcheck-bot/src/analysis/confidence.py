"""Score de confiance de l'analyse biomécanique.

Combine la qualité des keypoints, le taux d'occlusion, la qualité vidéo,
le nombre de reps et la cohérence du pattern pour donner un score global.
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
        }


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
        AnalysisConfidence avec score et détails.
    """
    result = AnalysisConfidence()
    limitations: list[str] = []

    # 1. Qualité keypoints (poids 40%)
    if extraction.frames:
        visibilities = [f.avg_visibility for f in extraction.frames]
        result.keypoint_quality = float(np.mean(visibilities))
    kp_score = result.keypoint_quality * 100

    if result.keypoint_quality < 0.5:
        limitations.append("Visibilité des articulations faible — résultats moins fiables")

    # 2. Taux d'occlusion (poids 20%)
    if extraction.total_frames > 0:
        expected = extraction.total_frames
        detected = len(extraction.frames)
        result.occlusion_rate = 1.0 - (detected / expected) if expected > 0 else 1.0
    occlusion_score = (1.0 - result.occlusion_rate) * 100

    if result.occlusion_rate > 0.3:
        limitations.append("Nombreuses frames sans détection — occlusion fréquente")

    # 3. Qualité vidéo (poids 20%)
    result.video_quality = validation.quality_score
    video_score = float(validation.quality_score)

    if validation.quality_score < 60:
        limitations.append("Qualité vidéo insuffisante — privilégie un bon éclairage et une résolution >= 720p")

    # 4. Nombre de reps (poids 10%)
    result.rep_count = reps.total_reps
    if reps.total_reps >= 5:
        rep_score = 100.0
    elif reps.total_reps >= 3:
        rep_score = 80.0
    elif reps.total_reps >= 1:
        rep_score = 50.0
    else:
        rep_score = 10.0
        limitations.append("Aucune répétition détectée — vérifie que le mouvement est complet")

    if reps.total_reps < 3:
        limitations.append("Moins de 3 reps — envoie une série plus longue pour une meilleure analyse")

    # 5. Cohérence du pattern (poids 10%)
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

    # Limitations caméra
    # Vérifier si la vue est latérale (difficile de mesurer valgus)
    if extraction.frames:
        sample = extraction.frames[len(extraction.frames) // 2]
        lms = {lm["name"]: lm for lm in sample.landmarks}
        ls = lms.get("left_shoulder")
        rs = lms.get("right_shoulder")
        if ls and rs:
            shoulder_width = abs(ls["x"] - rs["x"])
            if shoulder_width < 0.05:
                limitations.append("Angle de caméra latéral — valgus du genou non mesurable")

    # Score global pondéré
    overall = (
        kp_score * 0.40
        + occlusion_score * 0.20
        + video_score * 0.20
        + rep_score * 0.10
        + consistency_score * 0.10
    )
    result.overall_score = max(0, min(100, int(round(overall))))

    # Fiabilité
    if result.overall_score >= 70:
        result.reliability = "haute"
    elif result.overall_score >= 45:
        result.reliability = "moyenne"
    else:
        result.reliability = "limitee"

    result.limitations = limitations

    logger.info(
        "Confiance: %d/100 (%s) — kp=%.0f occ=%.0f vid=%.0f rep=%.0f cons=%.0f",
        result.overall_score, result.reliability,
        kp_score, occlusion_score, video_score, rep_score, consistency_score,
    )
    return result
