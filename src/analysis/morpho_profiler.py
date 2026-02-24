"""Profilage morphologique par photos statiques — FORMCHECK by ACHZOD.

Analyse 3 photos statiques (face, dos, profil) via MediaPipe pour creer
un profil morphologique complet :
- Mesures anthropometriques normalisees (clavicules, hanches, femur, tibia, torse, bras)
- Ratios cles (femur/tibia, torse/femur, bras/torse, epaules/hanches, bras_sup/avant-bras)
- Bilan postural automatique (lordose, cyphose, epaules enroulees, antéversion, tete en avant)
- Type morphologique (ectomorphe/mesomorphe/endomorphe estimation)
- Detection insertions musculaires (biceps court/long)
- Recommandations personnalisees (stance squat, prise bench, sumo vs conventional)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

logger = logging.getLogger("formcheck.morpho_profiler")

# Model path (same as pose_extractor)
_MODEL_DIR = Path(__file__).resolve().parent / "models"
_MODEL_PATH = _MODEL_DIR / "pose_landmarker_heavy.task"

# Landmark indices (same numbering as legacy mp.solutions.pose)
class _LM:
    NOSE = 0
    LEFT_EAR = 7
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

# ── Helpers geometriques ─────────────────────────────────────────────────────


def _get_lm(landmarks, idx: int) -> dict:
    """Extrait un landmark MediaPipe par index (Tasks API NormalizedLandmark)."""
    lm = landmarks[idx]
    return {
        "x": lm.x,
        "y": lm.y,
        "z": lm.z,
        "visibility": getattr(lm, "visibility", getattr(lm, "presence", 1.0)),
    }


def _dist_2d(a: dict, b: dict) -> float:
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)


def _dist_3d(a: dict, b: dict) -> float:
    return math.sqrt(
        (a["x"] - b["x"]) ** 2
        + (a["y"] - b["y"]) ** 2
        + (a["z"] - b["z"]) ** 2
    )


def _mid(a: dict, b: dict) -> dict:
    return {
        "x": (a["x"] + b["x"]) / 2,
        "y": (a["y"] + b["y"]) / 2,
        "z": (a["z"] + b["z"]) / 2,
    }


def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    return num / den if abs(den) > 1e-9 else default


# ── Dataclass principale ─────────────────────────────────────────────────────


@dataclass
class PostureAssessment:
    """Bilan postural depuis la photo de profil."""
    lordose_severity: float = 0.0           # 0 = normal, 1 = severe
    cyphose_severity: float = 0.0
    epaules_enroulees: bool = False
    epaules_enroulees_severity: float = 0.0
    antéversion_bassin: bool = False
    antéversion_severity: float = 0.0
    tete_en_avant: bool = False
    tete_en_avant_severity: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "lordose_severity": round(self.lordose_severity, 2),
            "cyphose_severity": round(self.cyphose_severity, 2),
            "epaules_enroulees": self.epaules_enroulees,
            "epaules_enroulees_severity": round(self.epaules_enroulees_severity, 2),
            "antéversion_bassin": self.antéversion_bassin,
            "antéversion_severity": round(self.antéversion_severity, 2),
            "tete_en_avant": self.tete_en_avant,
            "tete_en_avant_severity": round(self.tete_en_avant_severity, 2),
            "summary": self.summary,
        }


@dataclass
class MorphoProfile:
    """Profil morphologique complet d'un client."""
    # Mesures normalisees (par rapport a la taille estimee)
    shoulder_width: float = 0.0
    hip_width: float = 0.0
    femur_length: float = 0.0
    tibia_length: float = 0.0
    torso_length: float = 0.0
    upper_arm_length: float = 0.0
    forearm_length: float = 0.0
    total_arm_length: float = 0.0

    # Ratios
    femur_tibia_ratio: float = 1.0
    torso_femur_ratio: float = 1.0
    arm_torso_ratio: float = 1.0
    shoulder_hip_ratio: float = 1.0
    upper_arm_forearm_ratio: float = 1.0

    # Type morphologique
    morpho_type: str = "mesomorphe"         # ectomorphe / mesomorphe / endomorphe
    morpho_confidence: float = 0.0

    # Insertions musculaires
    biceps_type: str = "moyen"              # court / moyen / long
    biceps_ratio: float = 0.0

    # Posture
    posture: PostureAssessment = field(default_factory=PostureAssessment)

    # Squat type predit
    squat_type: str = "balanced"            # hip_dominant / quad_dominant / balanced
    deadlift_type: str = "conventional"     # conventional / sumo
    bench_grip: str = "moyen"               # etroit / moyen / large

    # Recommandations
    recommendations: list[str] = field(default_factory=list)

    # Resume textuel
    summary: str = ""

    # Qualite de l'analyse
    analysis_quality: float = 0.0           # 0-1, moyenne de visibilite des landmarks
    photos_analyzed: list[str] = field(default_factory=list)  # ["front", "side", "back"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "shoulder_width": round(self.shoulder_width, 4),
            "hip_width": round(self.hip_width, 4),
            "femur_length": round(self.femur_length, 4),
            "tibia_length": round(self.tibia_length, 4),
            "torso_length": round(self.torso_length, 4),
            "upper_arm_length": round(self.upper_arm_length, 4),
            "forearm_length": round(self.forearm_length, 4),
            "total_arm_length": round(self.total_arm_length, 4),
            "femur_tibia_ratio": round(self.femur_tibia_ratio, 3),
            "torso_femur_ratio": round(self.torso_femur_ratio, 3),
            "arm_torso_ratio": round(self.arm_torso_ratio, 3),
            "shoulder_hip_ratio": round(self.shoulder_hip_ratio, 3),
            "upper_arm_forearm_ratio": round(self.upper_arm_forearm_ratio, 3),
            "morpho_type": self.morpho_type,
            "morpho_confidence": round(self.morpho_confidence, 2),
            "biceps_type": self.biceps_type,
            "biceps_ratio": round(self.biceps_ratio, 3),
            "posture": self.posture.to_dict(),
            "squat_type": self.squat_type,
            "deadlift_type": self.deadlift_type,
            "bench_grip": self.bench_grip,
            "recommendations": self.recommendations,
            "summary": self.summary,
            "analysis_quality": round(self.analysis_quality, 2),
            "photos_analyzed": self.photos_analyzed,
        }


# ── Extraction des landmarks depuis une photo ────────────────────────────────


def _ensure_model() -> str:
    """Ensure the pose landmarker model is downloaded."""
    import urllib.request
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not _MODEL_PATH.exists():
        logger.info("Downloading pose landmarker model to %s...", _MODEL_PATH)
        urllib.request.urlretrieve(MODEL_URL, str(_MODEL_PATH))
        logger.info("Download complete.")
    return str(_MODEL_PATH)


def _extract_landmarks_from_image(image_path: str) -> tuple[Any | None, float]:
    """Extrait les landmarks MediaPipe Pose depuis une photo statique (Tasks API).

    Returns:
        (landmarks, avg_visibility) ou (None, 0.0) si echec.
    """
    img = cv2.imread(image_path)
    if img is None:
        logger.error("Impossible de lire l'image : %s", image_path)
        return None, 0.0

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

    model_path = _ensure_model()
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(mp_image)

    if not result.pose_landmarks or len(result.pose_landmarks) == 0:
        logger.warning("Aucun landmark detecte dans : %s", image_path)
        return None, 0.0

    landmarks = result.pose_landmarks[0]  # First (only) person
    # Calculer la visibilite moyenne
    vis_sum = sum(
        getattr(lm, "visibility", getattr(lm, "presence", 1.0))
        for lm in landmarks
    )
    avg_vis = vis_sum / len(landmarks) if landmarks else 0.0

    return landmarks, avg_vis


def _estimate_height(landmarks) -> float:
    """Estime la hauteur du sujet (nose → mid_ankle) en coords normalisees."""
    nose = _get_lm(landmarks, _LM.NOSE)
    la = _get_lm(landmarks, _LM.LEFT_ANKLE)
    ra = _get_lm(landmarks, _LM.RIGHT_ANKLE)
    mid_ankle_y = (la["y"] + ra["y"]) / 2
    h = abs(mid_ankle_y - nose["y"])
    return max(h, 0.01)


# ── Analyse photo de face ─────────────────────────────────────────────────────


def _analyze_front(landmarks, height: float, profile: MorphoProfile) -> None:
    """Analyse la photo de face : largeur clavicules, hanches, symetrie."""
    ls = _get_lm(landmarks, _LM.LEFT_SHOULDER)
    rs = _get_lm(landmarks, _LM.RIGHT_SHOULDER)
    lh = _get_lm(landmarks, _LM.LEFT_HIP)
    rh = _get_lm(landmarks, _LM.RIGHT_HIP)

    # Largeur clavicules (distance epaule G ↔ epaule D normalisee)
    shoulder_w = _dist_2d(ls, rs)
    profile.shoulder_width = _safe_div(shoulder_w, height)

    # Largeur hanches
    hip_w = _dist_2d(lh, rh)
    profile.hip_width = _safe_div(hip_w, height)

    # Ratio epaules/hanches
    profile.shoulder_hip_ratio = _safe_div(shoulder_w, hip_w, 1.0)

    # Bras depuis la face (moyenne G/D)
    le = _get_lm(landmarks, _LM.LEFT_ELBOW)
    re = _get_lm(landmarks, _LM.RIGHT_ELBOW)
    lw = _get_lm(landmarks, _LM.LEFT_WRIST)
    rw = _get_lm(landmarks, _LM.RIGHT_WRIST)

    # Upper arm
    ua_l = _dist_2d(ls, le)
    ua_r = _dist_2d(rs, re)
    ua_avg = (ua_l + ua_r) / 2
    profile.upper_arm_length = _safe_div(ua_avg, height)

    # Forearm
    fa_l = _dist_2d(le, lw)
    fa_r = _dist_2d(re, rw)
    fa_avg = (fa_l + fa_r) / 2
    profile.forearm_length = _safe_div(fa_avg, height)

    profile.total_arm_length = profile.upper_arm_length + profile.forearm_length
    profile.upper_arm_forearm_ratio = _safe_div(
        profile.upper_arm_length, profile.forearm_length, 1.0
    )


# ── Analyse photo de profil ──────────────────────────────────────────────────


def _analyze_side(landmarks, height: float, profile: MorphoProfile) -> None:
    """Analyse la photo de profil : segments, ratios, posture."""
    lh = _get_lm(landmarks, _LM.LEFT_HIP)
    rh = _get_lm(landmarks, _LM.RIGHT_HIP)
    lk = _get_lm(landmarks, _LM.LEFT_KNEE)
    rk = _get_lm(landmarks, _LM.RIGHT_KNEE)
    la = _get_lm(landmarks, _LM.LEFT_ANKLE)
    ra = _get_lm(landmarks, _LM.RIGHT_ANKLE)
    ls = _get_lm(landmarks, _LM.LEFT_SHOULDER)
    rs = _get_lm(landmarks, _LM.RIGHT_SHOULDER)
    nose = _get_lm(landmarks, _LM.NOSE)
    le_ear = _get_lm(landmarks, _LM.LEFT_EAR)

    # Femur (hanche → genou) — moyenne G/D
    fem_l = _dist_2d(lh, lk)
    fem_r = _dist_2d(rh, rk)
    fem_avg = (fem_l + fem_r) / 2
    profile.femur_length = _safe_div(fem_avg, height)

    # Tibia (genou → cheville)
    tib_l = _dist_2d(lk, la)
    tib_r = _dist_2d(rk, ra)
    tib_avg = (tib_l + tib_r) / 2
    profile.tibia_length = _safe_div(tib_avg, height)

    # Torse (milieu hanches → milieu epaules)
    mid_hip = _mid(lh, rh)
    mid_sh = _mid(ls, rs)
    torso_raw = _dist_2d(mid_hip, mid_sh)
    profile.torso_length = _safe_div(torso_raw, height)

    # Ratios principaux
    profile.femur_tibia_ratio = _safe_div(
        profile.femur_length, profile.tibia_length, 1.0
    )
    profile.torso_femur_ratio = _safe_div(
        profile.torso_length, profile.femur_length, 1.0
    )
    # Recalculer total_arm et arm_torso_ratio seulement si on a des données de bras
    # (les bras sont mesurés depuis la photo de face, pas le profil)
    total_arm = profile.upper_arm_length + profile.forearm_length
    profile.total_arm_length = max(profile.total_arm_length, total_arm)
    if profile.total_arm_length > 0:
        profile.arm_torso_ratio = _safe_div(profile.total_arm_length, profile.torso_length, 1.0)

    # ── Bilan postural ────────────────────────────────────────────────────
    posture = PostureAssessment()

    # Tete en avant : distance horizontale oreille vs epaule
    ear_shoulder_dx = abs(le_ear["x"] - ls["x"])
    ear_shoulder_norm = _safe_div(ear_shoulder_dx, height)
    # Seuil : > 0.03 = tete en avant moderee, > 0.06 = severe
    if ear_shoulder_norm > 0.03:
        posture.tete_en_avant = True
        posture.tete_en_avant_severity = min(1.0, (ear_shoulder_norm - 0.03) / 0.05)

    # Epaules enroulees : epaule en avant de la hanche (axe x profil)
    mid_sh_x = (ls["x"] + rs["x"]) / 2
    mid_hip_x = (lh["x"] + rh["x"]) / 2
    shoulder_forward = mid_sh_x - mid_hip_x  # positif = epaules en avant (si sujet face droite)
    shoulder_norm = abs(_safe_div(shoulder_forward, height))
    if shoulder_norm > 0.02:
        posture.epaules_enroulees = True
        posture.epaules_enroulees_severity = min(1.0, (shoulder_norm - 0.02) / 0.04)

    # Antéversion du bassin : angle bassin
    # Approximation : difference de hauteur entre ASIS (hanche) et le sacrum (pas dispo)
    # On utilise l'angle torse vs verticale comme proxy
    trunk_vec = np.array([mid_sh["x"] - mid_hip["x"], mid_sh["y"] - mid_hip["y"]])
    vertical = np.array([0.0, -1.0])  # y pointe vers le bas en MediaPipe
    cos_angle = np.dot(trunk_vec, vertical) / (np.linalg.norm(trunk_vec) * np.linalg.norm(vertical) + 1e-9)
    trunk_angle = math.degrees(math.acos(np.clip(cos_angle, -1.0, 1.0)))

    # Un trunk_angle > 5° en position debout peut indiquer une anterversion
    if trunk_angle > 8:
        posture.antéversion_bassin = True
        posture.antéversion_severity = min(1.0, (trunk_angle - 8) / 15)

    # Lordose / Cyphose (estimation simplifiee via la courbure du dos)
    # On estime la lordose par l'ecart entre la courbe lombaire et la ligne droite
    # Approximation : si anterversion + trunk_angle eleve → lordose probable
    if posture.antéversion_bassin:
        posture.lordose_severity = min(1.0, posture.antéversion_severity * 0.8)

    # Cyphose : si epaules enroulees + tete en avant → cyphose probable
    if posture.epaules_enroulees and posture.tete_en_avant:
        posture.cyphose_severity = min(
            1.0,
            (posture.epaules_enroulees_severity + posture.tete_en_avant_severity) / 2,
        )

    # Resume postural
    issues = []
    if posture.lordose_severity > 0.3:
        issues.append(f"lordose lombaire (severite {posture.lordose_severity:.0%})")
    if posture.cyphose_severity > 0.3:
        issues.append(f"cyphose thoracique (severite {posture.cyphose_severity:.0%})")
    if posture.epaules_enroulees:
        issues.append("epaules enroulees vers l'avant")
    if posture.antéversion_bassin:
        issues.append("antéversion du bassin")
    if posture.tete_en_avant:
        issues.append("tete en position avancee (forward head)")

    if issues:
        posture.summary = "Desequilibres posturaux detectes : " + ", ".join(issues) + "."
    else:
        posture.summary = "Posture globalement equilibree — pas de desequilibre majeur detecte."

    profile.posture = posture


# ── Analyse photo de dos ──────────────────────────────────────────────────────


def _analyze_back(landmarks, height: float, profile: MorphoProfile) -> None:
    """Analyse la photo de dos : position omoplates, asymetries."""
    ls = _get_lm(landmarks, _LM.LEFT_SHOULDER)
    rs = _get_lm(landmarks, _LM.RIGHT_SHOULDER)
    lh = _get_lm(landmarks, _LM.LEFT_HIP)
    rh = _get_lm(landmarks, _LM.RIGHT_HIP)

    # Confirmer la largeur clavicules depuis le dos (si pas deja mesuree ou pour moyenner)
    shoulder_w_back = _dist_2d(ls, rs)
    back_shoulder = _safe_div(shoulder_w_back, height)
    if profile.shoulder_width > 0:
        profile.shoulder_width = (profile.shoulder_width + back_shoulder) / 2
    else:
        profile.shoulder_width = back_shoulder

    # Asymetrie epaules (hauteur relative)
    shoulder_asym = abs(ls["y"] - rs["y"])
    # Integrer dans le resume postural si significatif
    if _safe_div(shoulder_asym, height) > 0.015:
        if not profile.posture.summary:
            profile.posture.summary = "Legere asymetrie des epaules detectee (vue de dos)."
        else:
            if not profile.posture.summary.endswith("."):
                profile.posture.summary += "."
            profile.posture.summary += " Legere asymetrie des epaules detectee (vue de dos)."

    # Confirmer hip width depuis le dos (moyenne si deja mesure)
    if lh and rh:
        hip_w_back = _dist_2d(lh, rh)
        back_hip = _safe_div(hip_w_back, height)
        if profile.hip_width > 0:
            profile.hip_width = (profile.hip_width + back_hip) / 2
        else:
            profile.hip_width = back_hip


# ── Determination du type morphologique ───────────────────────────────────────


def _determine_morpho_type(profile: MorphoProfile) -> None:
    """Estime le type morphologique (somatotype simplifie)."""
    # Indices utilisés :
    # - Ratio epaules/hanches (ecto = etroit, endo = large)
    # - Longueur des segments (ecto = segments longs, endo = courts)
    # - Largeur de structure

    score_ecto = 0.0
    score_meso = 0.0
    score_endo = 0.0

    # Epaules/hanches : ecto < 1.2, meso 1.2-1.4, endo variable mais hanches larges
    shr = profile.shoulder_hip_ratio
    if shr > 1.35:
        score_meso += 2.0
    elif shr > 1.2:
        score_meso += 1.0
        score_ecto += 0.5
    elif shr > 1.0:
        score_ecto += 1.5
    else:
        score_endo += 1.5

    # Segments longs → ectomorphe
    if profile.femur_length > 0.28:  # Femur long normalise
        score_ecto += 1.0
    elif profile.femur_length < 0.24:
        score_endo += 0.5
        score_meso += 0.5

    # Bras longs
    if profile.total_arm_length > 0.38:
        score_ecto += 1.0
    elif profile.total_arm_length < 0.32:
        score_endo += 0.5

    # Epaules larges → mesomorphe
    if profile.shoulder_width > 0.24:
        score_meso += 1.5
    elif profile.shoulder_width < 0.2:
        score_ecto += 1.0

    # Hanches larges → endomorphe
    if profile.hip_width > 0.19:
        score_endo += 1.0

    total = score_ecto + score_meso + score_endo
    if total > 0:
        if score_ecto >= score_meso and score_ecto >= score_endo:
            profile.morpho_type = "ectomorphe"
            profile.morpho_confidence = score_ecto / total
        elif score_meso >= score_ecto and score_meso >= score_endo:
            profile.morpho_type = "mesomorphe"
            profile.morpho_confidence = score_meso / total
        else:
            profile.morpho_type = "endomorphe"
            profile.morpho_confidence = score_endo / total
    else:
        profile.morpho_type = "mesomorphe"
        profile.morpho_confidence = 0.3


# ── Detection des insertions musculaires ──────────────────────────────────────


def _detect_biceps_insertion(profile: MorphoProfile) -> None:
    """Estime le type d'insertion biceps (court/moyen/long) via le ratio bras."""
    # Le ratio upper_arm/forearm donne une indication :
    # - Bras superieur long vs avant-bras court → biceps long (insertion haute)
    # - Bras superieur court vs avant-bras long → biceps court (pic plus haut)
    r = profile.upper_arm_forearm_ratio
    profile.biceps_ratio = r

    if r > 1.15:
        profile.biceps_type = "long"
    elif r < 0.9:
        profile.biceps_type = "court"
    else:
        profile.biceps_type = "moyen"


# ── Recommandations personnalisees ────────────────────────────────────────────


def _generate_recommendations(profile: MorphoProfile) -> None:
    """Genere des recommandations de stance/prise basees sur la morpho."""
    recs = []

    # ── Squat ─────────────────────────────────────────────────────────────
    ftr = profile.femur_tibia_ratio
    tfr = profile.torso_femur_ratio

    if ftr > 1.1 and tfr < 0.95:
        profile.squat_type = "hip_dominant"
        recs.append(
            "SQUAT : Tes femurs sont longs par rapport a ton torse — "
            "une inclinaison du tronc plus prononcee est normale et attendue. "
            "Stance moyenne a large, orteils tournes 20-30 degres. "
            "Privilegier le low-bar squat qui s'adapte mieux a cette morphologie."
        )
    elif tfr > 1.1:
        profile.squat_type = "quad_dominant"
        recs.append(
            "SQUAT : Ton torse long te permet de rester naturellement plus vertical. "
            "Tu peux utiliser un high-bar squat ou front squat avec une stance "
            "moyenne. Profite de cet avantage pour travailler la profondeur."
        )
    else:
        profile.squat_type = "balanced"
        recs.append(
            "SQUAT : Proportions equilibrees — tu peux utiliser aussi bien le "
            "high-bar que le low-bar. Stance largeur des epaules, orteils tournes 15-25 degres."
        )

    # Largeur de stance basee sur les hanches
    if profile.hip_width > 0.19:
        recs.append(
            "STANCE SQUAT : Tes hanches larges suggerent une stance un peu plus "
            "large que la moyenne (pieds largeur des epaules + 10-15cm). "
            "Ca permet une meilleure ouverture de hanches et plus de profondeur."
        )

    # ── Deadlift ──────────────────────────────────────────────────────────
    if profile.hip_width > 0.19 and ftr < 1.05:
        profile.deadlift_type = "sumo"
        recs.append(
            "DEADLIFT : Tes hanches larges et femurs proportionnes te donnent "
            "un avantage en sumo. Le levier de la hanche est reduit et tu "
            "peux garder le torse plus vertical."
        )
    elif ftr > 1.1:
        profile.deadlift_type = "conventional"
        recs.append(
            "DEADLIFT : Tes femurs longs rendent le sumo moins efficace. "
            "Le conventional te permet un meilleur setup avec les bras a l'exterieur "
            "des genoux."
        )
    else:
        profile.deadlift_type = "conventional"
        recs.append(
            "DEADLIFT : Proportions adaptees au conventional. "
            "Teste aussi le sumo pour comparer tes sensations."
        )

    # ── Bench Press ───────────────────────────────────────────────────────
    shr = profile.shoulder_hip_ratio
    if profile.shoulder_width > 0.24:
        profile.bench_grip = "large"
        recs.append(
            "BENCH PRESS : Tes clavicules larges permettent une prise large "
            "(1.5-1.8x largeur biacromiale). Plus de recrutement pec, "
            "plus de stretch en bas du mouvement."
        )
    elif profile.shoulder_width < 0.2:
        profile.bench_grip = "etroit"
        recs.append(
            "BENCH PRESS : Clavicules etroites — privilegier une prise moyenne "
            "(1.2-1.4x largeur biacromiale). Bien serrer les omoplates pour "
            "compenser le levier plus court."
        )
    else:
        profile.bench_grip = "moyen"
        recs.append(
            "BENCH PRESS : Largeur d'epaules standard — prise a 1.3-1.6x "
            "la largeur biacromiale. Ajuste selon ta sensation d'etirement pec en bas."
        )

    # Bras longs = impact bench et deadlift
    if profile.total_arm_length > 0.38:
        recs.append(
            "BRAS LONGS : Avantage deadlift (moins de ROM), mais plus de ROM au "
            "bench press. Ne te compare pas aux gars avec des bras courts au bench — "
            "ton ROM est naturellement plus grand. Utilise un arch raisonnable."
        )

    # ── Posture ───────────────────────────────────────────────────────────
    if profile.posture.epaules_enroulees:
        recs.append(
            "POSTURE : Epaules enroulees detectees — integre des face pulls "
            "et du band pull-apart en echauffement (3x15). Etirement pec mineur "
            "30s apres chaque seance."
        )
    if profile.posture.tete_en_avant:
        recs.append(
            "POSTURE : Tete en position avancee — renforcement des flechisseurs "
            "profonds du cou (chin tucks 3x12) et etirement du SCM et des trap sup."
        )
    if profile.posture.antéversion_bassin:
        recs.append(
            "POSTURE : Antéversion du bassin detectee — etirement psoas/quad "
            "(30s x 3 par cote) et renforcement des fessiers (glute bridge 3x15). "
            "Attention au squat : pense a 'rentrer le bassin' en bas du mouvement."
        )

    # Biceps
    if profile.biceps_type == "court":
        recs.append(
            "BICEPS : Insertion courte estimee — pic de biceps potentiellement "
            "plus prononce. Privilegier les curls en etirement (incline curl) "
            "pour maximiser la croissance."
        )
    elif profile.biceps_type == "long":
        recs.append(
            "BICEPS : Insertion longue estimee — le muscle remplit bien le bras. "
            "Privilege les curls en contraction (concentration curl, preacher curl)."
        )

    profile.recommendations = recs


# ── Construction du resume textuel ────────────────────────────────────────────


def _build_summary(profile: MorphoProfile) -> None:
    """Construit un resume textuel du profil morpho."""
    parts = []

    parts.append(f"Type morphologique estime : {profile.morpho_type} (confiance {profile.morpho_confidence:.0%}).")

    # Proportions
    if profile.femur_tibia_ratio > 1.1:
        parts.append("Femurs relativement longs par rapport aux tibias.")
    elif profile.femur_tibia_ratio < 0.9:
        parts.append("Tibias relativement longs par rapport aux femurs.")

    if profile.torso_femur_ratio > 1.1:
        parts.append("Torse long par rapport aux femurs — avantage squat vertical.")
    elif profile.torso_femur_ratio < 0.95:
        parts.append("Torse court par rapport aux femurs — inclinaison du tronc naturelle au squat.")

    if profile.shoulder_hip_ratio > 1.35:
        parts.append("Structure epaules larges (bon ratio epaules/hanches).")
    elif profile.shoulder_hip_ratio < 1.1:
        parts.append("Structure hanches larges par rapport aux epaules.")

    # Posture
    if profile.posture.summary:
        parts.append(profile.posture.summary)

    # Reco principale
    parts.append(f"Squat recommande : {profile.squat_type.replace('_', ' ')}.")
    parts.append(f"Deadlift recommande : {profile.deadlift_type}.")
    parts.append(f"Prise bench recommandee : {profile.bench_grip}.")

    profile.summary = " ".join(parts)


# ── POINT D'ENTREE PRINCIPAL ──────────────────────────────────────────────────


def analyze_morphology(
    front_image_path: str | None = None,
    side_image_path: str | None = None,
    back_image_path: str | None = None,
) -> MorphoProfile:
    """Analyse 1 a 3 photos statiques et retourne un MorphoProfile complet.

    Args:
        front_image_path: Photo de face (debout, bras le long du corps).
        side_image_path: Photo de profil (laterale).
        back_image_path: Photo de dos.

    Returns:
        MorphoProfile avec toutes les mesures, ratios, posture et recommandations.
    """
    profile = MorphoProfile()
    quality_scores: list[float] = []

    # ── Photo de face ─────────────────────────────────────────────────────
    if front_image_path and Path(front_image_path).exists():
        logger.info("Analyse morpho — photo de face : %s", front_image_path)
        landmarks, vis = _extract_landmarks_from_image(front_image_path)
        if landmarks:
            height = _estimate_height(landmarks)
            _analyze_front(landmarks, height, profile)
            quality_scores.append(vis)
            profile.photos_analyzed.append("front")
            logger.info("  → Face analysee (visibilite: %.0f%%)", vis * 100)
        else:
            logger.warning("  → Echec extraction face")

    # ── Photo de profil ───────────────────────────────────────────────────
    if side_image_path and Path(side_image_path).exists():
        logger.info("Analyse morpho — photo de profil : %s", side_image_path)
        landmarks, vis = _extract_landmarks_from_image(side_image_path)
        if landmarks:
            height = _estimate_height(landmarks)
            _analyze_side(landmarks, height, profile)
            quality_scores.append(vis)
            profile.photos_analyzed.append("side")
            logger.info("  → Profil analyse (visibilite: %.0f%%)", vis * 100)
        else:
            logger.warning("  → Echec extraction profil")

    # ── Photo de dos ──────────────────────────────────────────────────────
    if back_image_path and Path(back_image_path).exists():
        logger.info("Analyse morpho — photo de dos : %s", back_image_path)
        landmarks, vis = _extract_landmarks_from_image(back_image_path)
        if landmarks:
            height = _estimate_height(landmarks)
            _analyze_back(landmarks, height, profile)
            quality_scores.append(vis)
            profile.photos_analyzed.append("back")
            logger.info("  → Dos analyse (visibilite: %.0f%%)", vis * 100)
        else:
            logger.warning("  → Echec extraction dos")

    # ── Post-traitement ───────────────────────────────────────────────────
    if quality_scores:
        profile.analysis_quality = sum(quality_scores) / len(quality_scores)

    _determine_morpho_type(profile)
    _detect_biceps_insertion(profile)
    _generate_recommendations(profile)
    _build_summary(profile)

    logger.info(
        "Profil morpho complet — type=%s, squat=%s, deadlift=%s, qualite=%.0f%%, photos=%s",
        profile.morpho_type, profile.squat_type, profile.deadlift_type,
        profile.analysis_quality * 100, profile.photos_analyzed,
    )

    return profile
