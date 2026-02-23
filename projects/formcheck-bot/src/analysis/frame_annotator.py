"""Annotation visuelle des frames cles avec overlay d'angles articulaires.

Dessine les angles mesures directement sur les images extraites.
Code couleur :
- Vert (#00C853)  : angle dans la norme
- Orange (#FF9100) : warning (proche des limites)
- Rouge (#FF1744)  : probleme detecte

Squelette epure avec gradient de couleur, arcs d'angle visuels,
labels positionnes intelligemment pour eviter le chevauchement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from analysis.angle_calculator import AngleResult, FrameAngles
from analysis.exercise_detector import Exercise
from analysis.pose_extractor import ExtractionResult, FrameLandmarks

logger = logging.getLogger(__name__)

# ── Couleurs ─────────────────────────────────────────────────────────────────
# BGR pour OpenCV, RGB pour PIL

COLOR_GREEN_BGR = (83, 200, 0)
COLOR_ORANGE_BGR = (0, 145, 255)
COLOR_RED_BGR = (68, 23, 255)
COLOR_WHITE_BGR = (255, 255, 255)
COLOR_GRAY_BGR = (120, 120, 140)
COLOR_SKELETON_BGR = (160, 160, 180)
COLOR_BLACK_BGR = (0, 0, 0)
COLOR_CYAN_BGR = (255, 212, 0)  # #00D4FF en BGR

COLOR_GREEN_RGB = (0, 200, 83)
COLOR_ORANGE_RGB = (255, 145, 0)
COLOR_RED_RGB = (255, 23, 68)
COLOR_WHITE_RGB = (255, 255, 255)
COLOR_BLACK_RGB = (0, 0, 0)
COLOR_CYAN_RGB = (0, 212, 255)

# ── Font loading ─────────────────────────────────────────────────────────────


def _load_font(size: int = 18) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Charge une font systeme qui gere l'UTF-8 (accents francais)."""
    font_candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    logger.warning("Aucune font systeme trouvee, fallback sur font par defaut PIL")
    return ImageFont.load_default()


def _load_font_bold(size: int = 18) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Charge une font bold."""
    bold_candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in bold_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return _load_font(size)


# Cache fonts
_FONT_LABEL = _load_font(15)
_FONT_BADGE = _load_font_bold(20)
_FONT_SMALL = _load_font(12)
_FONT_BRAND = _load_font_bold(11)

# ── Seuils par exercice ─────────────────────────────────────────────────────
# (min_ok, max_ok, min_warn, max_warn) — dans cette plage, c'est vert/orange/rouge

ANGLE_THRESHOLDS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "squat": {
        "knee_flexion": (85, 125, 65, 145),
        "hip_flexion": (65, 105, 50, 120),
        "trunk_inclination": (0, 45, 0, 55),
    },
    "front_squat": {
        "knee_flexion": (85, 125, 65, 145),
        "hip_flexion": (65, 105, 50, 120),
        "trunk_inclination": (0, 30, 0, 40),
    },
    "deadlift": {
        "hip_flexion": (55, 85, 45, 95),
        "knee_flexion": (125, 155, 115, 165),
        "trunk_inclination": (25, 50, 15, 60),
    },
    "rdl": {
        "hip_flexion": (55, 85, 45, 95),
        "knee_flexion": (150, 175, 140, 180),
        "trunk_inclination": (30, 55, 20, 65),
    },
    "bench_press": {
        "elbow_flexion": (75, 105, 65, 115),
        "shoulder_abduction": (40, 75, 30, 85),
    },
    "ohp": {
        "trunk_inclination": (0, 15, 0, 25),
        "elbow_flexion": (65, 180, 55, 180),
    },
    "barbell_row": {
        "trunk_inclination": (25, 50, 15, 65),
        "elbow_flexion": (40, 170, 30, 180),
    },
    "hip_thrust": {
        "knee_flexion": (75, 105, 65, 115),
        "hip_flexion": (100, 180, 85, 180),
    },
    "curl": {
        "elbow_flexion": (25, 175, 15, 180),
        "trunk_inclination": (0, 10, 0, 18),
    },
    "lateral_raise": {
        "shoulder_abduction": (0, 95, 0, 105),
        "trunk_inclination": (0, 10, 0, 18),
    },
    "bulgarian_split_squat": {
        "knee_flexion": (80, 120, 65, 140),
        "hip_flexion": (65, 110, 50, 125),
        "trunk_inclination": (0, 35, 0, 45),
    },
    "lunge": {
        "knee_flexion": (80, 120, 65, 140),
        "hip_flexion": (65, 110, 50, 125),
        "trunk_inclination": (0, 30, 0, 40),
    },
    "leg_press": {
        "knee_flexion": (85, 120, 70, 140),
    },
    "leg_extension": {
        "knee_flexion": (40, 180, 30, 180),
    },
    "leg_curl": {
        "knee_flexion": (40, 170, 30, 180),
    },
    "tricep_extension": {
        "elbow_flexion": (40, 180, 30, 180),
    },
    "pullup": {
        "elbow_flexion": (40, 170, 30, 180),
        "shoulder_abduction": (10, 60, 0, 75),
    },
    "lat_pulldown": {
        "elbow_flexion": (40, 170, 30, 180),
        "shoulder_abduction": (30, 80, 20, 90),
    },
}

# ── Angles prioritaires par exercice ────────────────────────────────────────

PRIORITY_ANGLES: dict[str, list[str]] = {
    "squat": [
        "left_knee_flexion", "right_knee_flexion",
        "left_hip_flexion", "right_hip_flexion",
    ],
    "front_squat": [
        "left_knee_flexion", "right_knee_flexion",
        "left_hip_flexion", "right_hip_flexion",
    ],
    "deadlift": [
        "left_hip_flexion", "right_hip_flexion",
        "left_knee_flexion", "right_knee_flexion",
    ],
    "rdl": [
        "left_hip_flexion", "right_hip_flexion",
        "left_knee_flexion", "right_knee_flexion",
    ],
    "bench_press": [
        "left_elbow_flexion", "right_elbow_flexion",
        "left_shoulder_abduction", "right_shoulder_abduction",
    ],
    "ohp": [
        "left_elbow_flexion", "right_elbow_flexion",
        "left_shoulder_flexion", "right_shoulder_flexion",
    ],
    "barbell_row": [
        "left_elbow_flexion", "right_elbow_flexion",
    ],
    "hip_thrust": [
        "left_knee_flexion", "right_knee_flexion",
        "left_hip_flexion", "right_hip_flexion",
    ],
    "curl": [
        "left_elbow_flexion", "right_elbow_flexion",
    ],
    "lateral_raise": [
        "left_shoulder_abduction", "right_shoulder_abduction",
    ],
    "bulgarian_split_squat": [
        "left_knee_flexion", "right_knee_flexion",
        "left_hip_flexion", "right_hip_flexion",
    ],
    "lunge": [
        "left_knee_flexion", "right_knee_flexion",
        "left_hip_flexion", "right_hip_flexion",
    ],
    "leg_press": [
        "left_knee_flexion", "right_knee_flexion",
    ],
    "leg_extension": [
        "left_knee_flexion", "right_knee_flexion",
    ],
    "leg_curl": [
        "left_knee_flexion", "right_knee_flexion",
    ],
    "tricep_extension": [
        "left_elbow_flexion", "right_elbow_flexion",
    ],
    "pullup": [
        "left_elbow_flexion", "right_elbow_flexion",
    ],
    "lat_pulldown": [
        "left_elbow_flexion", "right_elbow_flexion",
    ],
}

# ── Connexions squelette MediaPipe Pose ──────────────────────────────────────

SKELETON_CONNECTIONS: list[tuple[str, str]] = [
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("left_ankle", "left_heel"),
    ("left_ankle", "left_foot_index"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("right_ankle", "right_heel"),
    ("right_ankle", "right_foot_index"),
]

# Config d'affichage des angles
ANGLE_DISPLAY_CONFIG: dict[str, dict[str, Any]] = {
    "left_knee_flexion": {
        "landmarks": ("left_hip", "left_knee", "left_ankle"),
        "label": "Genou G",
        "threshold_key": "knee_flexion",
    },
    "right_knee_flexion": {
        "landmarks": ("right_hip", "right_knee", "right_ankle"),
        "label": "Genou D",
        "threshold_key": "knee_flexion",
    },
    "left_hip_flexion": {
        "landmarks": ("left_shoulder", "left_hip", "left_knee"),
        "label": "Hanche G",
        "threshold_key": "hip_flexion",
    },
    "right_hip_flexion": {
        "landmarks": ("right_shoulder", "right_hip", "right_knee"),
        "label": "Hanche D",
        "threshold_key": "hip_flexion",
    },
    "left_elbow_flexion": {
        "landmarks": ("left_shoulder", "left_elbow", "left_wrist"),
        "label": "Coude G",
        "threshold_key": "elbow_flexion",
    },
    "right_elbow_flexion": {
        "landmarks": ("right_shoulder", "right_elbow", "right_wrist"),
        "label": "Coude D",
        "threshold_key": "elbow_flexion",
    },
    "left_shoulder_abduction": {
        "landmarks": ("left_hip", "left_shoulder", "left_elbow"),
        "label": "Epaule G",
        "threshold_key": "shoulder_abduction",
    },
    "right_shoulder_abduction": {
        "landmarks": ("right_hip", "right_shoulder", "right_elbow"),
        "label": "Epaule D",
        "threshold_key": "shoulder_abduction",
    },
    "left_shoulder_flexion": {
        "landmarks": ("left_hip", "left_shoulder", "left_elbow"),
        "label": "Epaule G flex",
        "threshold_key": "shoulder_flexion",
    },
    "right_shoulder_flexion": {
        "landmarks": ("right_hip", "right_shoulder", "right_elbow"),
        "label": "Epaule D flex",
        "threshold_key": "shoulder_flexion",
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_color_for_angle(
    value: float,
    thresholds: tuple[float, float, float, float],
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Retourne (bgr_color, rgb_color) selon la valeur et les seuils."""
    min_ok, max_ok, min_warn, max_warn = thresholds
    if min_ok <= value <= max_ok:
        return COLOR_GREEN_BGR, COLOR_GREEN_RGB
    elif min_warn <= value <= max_warn:
        return COLOR_ORANGE_BGR, COLOR_ORANGE_RGB
    else:
        return COLOR_RED_BGR, COLOR_RED_RGB


def _landmark_pixel(
    landmarks: list[dict[str, float]],
    name: str,
    width: int,
    height: int,
) -> tuple[int, int] | None:
    """Convertit les coordonnees normalisees d'un landmark en pixels."""
    for lm in landmarks:
        if lm["name"] == name:
            return (int(lm["x"] * width), int(lm["y"] * height))
    return None


def _cv2_to_pil(img: np.ndarray) -> Image.Image:
    """Convertit une image OpenCV BGR en PIL RGB."""
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def _pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
    """Convertit une image PIL RGB en OpenCV BGR."""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int],
    radius: int = 6,
    outline_width: int = 2,
) -> None:
    """Dessine un rectangle arrondi semi-transparent avec bord colore."""
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=outline_width)
    except AttributeError:
        draw.rectangle(xy, fill=fill, outline=outline, width=outline_width)


# ── Zone-based label layout ─────────────────────────────────────────────────

@dataclass
class _LabelInfo:
    text: str
    color_bgr: tuple[int, int, int]
    color_rgb: tuple[int, int, int]
    anchor_pt: tuple[int, int]


def _layout_labels(
    labels: list[_LabelInfo],
    img_w: int,
    img_h: int,
) -> list[tuple[_LabelInfo, tuple[int, int]]]:
    """Positionne les labels pour eviter le chevauchement.

    Gauche de l'image = labels gauche, droite = labels droite.
    """
    left_labels: list[_LabelInfo] = []
    right_labels: list[_LabelInfo] = []
    mid_x = img_w // 2

    for lbl in labels:
        if lbl.anchor_pt[0] < mid_x:
            left_labels.append(lbl)
        else:
            right_labels.append(lbl)

    left_labels.sort(key=lambda l: l.anchor_pt[1])
    right_labels.sort(key=lambda l: l.anchor_pt[1])

    result: list[tuple[_LabelInfo, tuple[int, int]]] = []
    margin = 10
    label_h = 26
    gap = 5

    # Colonne gauche
    y = 55
    for lbl in left_labels:
        result.append((lbl, (margin, y)))
        y += label_h + gap

    # Colonne droite
    y = 55
    label_w_approx = 140
    for lbl in right_labels:
        result.append((lbl, (img_w - label_w_approx - margin, y)))
        y += label_h + gap

    return result


# ── Annotation principale ───────────────────────────────────────────────────

def annotate_frame(
    image_path: str,
    frame_landmarks: FrameLandmarks,
    frame_angles: FrameAngles,
    exercise: str,
    label: str = "",
) -> np.ndarray:
    """Annote une frame avec le squelette et les angles.

    Args:
        image_path: Chemin vers l'image de la frame.
        frame_landmarks: Landmarks de la frame.
        frame_angles: Angles calcules pour la frame.
        exercise: Nom de l'exercice (pour les seuils de couleur).
        label: Label a afficher sur l'image (ex: "Point bas").

    Returns:
        Image annotee (numpy array BGR).
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image introuvable: {image_path}")

    h, w = img.shape[:2]
    landmarks = frame_landmarks.landmarks

    # ── 1. Darkened background pour contraste ─────────────────────────────
    overlay = img.copy()
    darken = np.zeros_like(img)
    cv2.addWeighted(img, 0.75, darken, 0.25, 0, overlay)

    # ── 2. Squelette epure (OpenCV) ───────────────────────────────────────
    for lm_a, lm_b in SKELETON_CONNECTIONS:
        pt_a = _landmark_pixel(landmarks, lm_a, w, h)
        pt_b = _landmark_pixel(landmarks, lm_b, w, h)
        if pt_a and pt_b:
            # Ligne semi-transparente via overlay
            cv2.line(overlay, pt_a, pt_b, COLOR_SKELETON_BGR, 2, cv2.LINE_AA)

    # Points aux articulations — petits cercles avec contour
    for lm in landmarks:
        if lm["visibility"] > 0.5:
            px, py = int(lm["x"] * w), int(lm["y"] * h)
            cv2.circle(overlay, (px, py), 5, COLOR_BLACK_BGR, -1, cv2.LINE_AA)
            cv2.circle(overlay, (px, py), 3, COLOR_WHITE_BGR, -1, cv2.LINE_AA)

    cv2.addWeighted(overlay, 0.8, img, 0.2, 0, img)

    # ── 3. Arcs d'angle colores sur les articulations ─────────────────────
    thresholds = ANGLE_THRESHOLDS.get(exercise, {})
    priority = PRIORITY_ANGLES.get(exercise, list(ANGLE_DISPLAY_CONFIG.keys())[:6])

    label_infos: list[_LabelInfo] = []

    for angle_attr in priority:
        config = ANGLE_DISPLAY_CONFIG.get(angle_attr)
        if not config:
            continue

        value = getattr(frame_angles, angle_attr, None)
        if value is None:
            continue

        lm_names = config["landmarks"]
        pt_a = _landmark_pixel(landmarks, lm_names[0], w, h)
        pt_center = _landmark_pixel(landmarks, lm_names[1], w, h)
        pt_b = _landmark_pixel(landmarks, lm_names[2], w, h)
        if not all([pt_a, pt_center, pt_b]):
            continue

        # Couleur
        threshold_key = config["threshold_key"]
        if threshold_key in thresholds:
            color_bgr, color_rgb = _get_color_for_angle(value, thresholds[threshold_key])
        else:
            color_bgr, color_rgb = COLOR_WHITE_BGR, COLOR_WHITE_RGB

        # Lignes de l'angle (plus epaisses, colorees)
        cv2.line(img, pt_a, pt_center, color_bgr, 3, cv2.LINE_AA)
        cv2.line(img, pt_center, pt_b, color_bgr, 3, cv2.LINE_AA)

        # Point central marque
        cv2.circle(img, pt_center, 6, color_bgr, -1, cv2.LINE_AA)
        cv2.circle(img, pt_center, 3, COLOR_BLACK_BGR, -1, cv2.LINE_AA)

        # Arc visuel
        radius = max(20, min(35, int(min(w, h) * 0.04)))
        vec_a = np.array(pt_a) - np.array(pt_center)
        vec_b = np.array(pt_b) - np.array(pt_center)
        start_angle = np.degrees(np.arctan2(vec_a[1], vec_a[0]))
        end_angle = np.degrees(np.arctan2(vec_b[1], vec_b[0]))
        if end_angle < start_angle:
            start_angle, end_angle = end_angle, start_angle
        if end_angle - start_angle > 180:
            start_angle, end_angle = end_angle, start_angle + 360
        cv2.ellipse(img, pt_center, (radius, radius), 0, start_angle, end_angle, color_bgr, 2, cv2.LINE_AA)

        # Preparer le label
        text = f"{config['label']}: {value:.0f}°"
        label_infos.append(_LabelInfo(text=text, color_bgr=color_bgr, color_rgb=color_rgb, anchor_pt=pt_center))

    # ── 4. Texte via PIL (UTF-8 safe) ─────────────────────────────────────
    pil_img = _cv2_to_pil(img).convert("RGBA")
    txt_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Badge titre (DEBUT / POINT BAS / FIN)
    if label:
        label_map = {
            "start": "DEBUT",
            "mid": "POINT BAS",
            "end": "FIN",
            "quarter": "DESCENTE",
            "three_quarter": "REMONTEE",
        }
        display_label = label_map.get(label, label.upper())
        bbox = draw.textbbox((0, 0), display_label, font=_FONT_BADGE)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 12, 6
        _draw_rounded_rect(
            draw,
            (8, 8, 8 + tw + 2 * pad_x, 8 + th + 2 * pad_y),
            fill=(0, 0, 0, 220),
            outline=(0, 212, 255),
            radius=8,
            outline_width=2,
        )
        draw.text((8 + pad_x, 8 + pad_y), display_label, font=_FONT_BADGE, fill=(0, 212, 255, 255))

    # Labels d'angles positionnes intelligemment
    positioned = _layout_labels(label_infos, w, h)
    for lbl_info, (lx, ly) in positioned:
        text = lbl_info.text
        bbox = draw.textbbox((0, 0), text, font=_FONT_LABEL)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 8, 4
        _draw_rounded_rect(
            draw,
            (lx, ly, lx + tw + 2 * pad_x, ly + th + 2 * pad_y),
            fill=(10, 10, 20, 200),
            outline=lbl_info.color_rgb,
            radius=6,
            outline_width=2,
        )
        draw.text((lx + pad_x, ly + pad_y), text, font=_FONT_LABEL, fill=(*lbl_info.color_rgb, 255))

        # Ligne de connexion
        badge_center_x = lx + (tw + 2 * pad_x) // 2
        badge_bottom_y = ly + th + 2 * pad_y
        draw.line(
            [(badge_center_x, badge_bottom_y), lbl_info.anchor_pt],
            fill=(*lbl_info.color_rgb, 80),
            width=1,
        )

    # Symetrie (en bas)
    sym = frame_angles.knee_flexion_symmetry
    if sym is not None:
        if sym > 0.9:
            sym_color = COLOR_GREEN_RGB
        elif sym > 0.8:
            sym_color = COLOR_ORANGE_RGB
        else:
            sym_color = COLOR_RED_RGB
        sym_text = f"Symetrie genoux: {sym:.0%}"
        bbox = draw.textbbox((0, 0), sym_text, font=_FONT_SMALL)
        tw = bbox[2] - bbox[0]
        sx = w - tw - 20
        sy = h - 30
        _draw_rounded_rect(
            draw, (sx - 6, sy - 4, sx + tw + 6, sy + 18),
            fill=(10, 10, 20, 180), outline=sym_color, radius=4, outline_width=1,
        )
        draw.text((sx, sy), sym_text, font=_FONT_SMALL, fill=(*sym_color, 255))

    # Branding discret en bas a gauche
    brand_text = "FORMCHECK by ACHZOD"
    draw.text((10, h - 22), brand_text, font=_FONT_BRAND, fill=(100, 100, 140, 150))

    # Composite et retour en OpenCV
    result = Image.alpha_composite(pil_img, txt_layer)
    return _pil_to_cv2(result.convert("RGB"))


def annotate_key_frames(
    extraction: ExtractionResult,
    angles: AngleResult,
    exercise: str,
    output_dir: str | None = None,
) -> dict[str, str]:
    """Annote toutes les frames cles et sauvegarde les images.

    Args:
        extraction: Resultat de l'extraction de pose.
        angles: Resultat du calcul d'angles.
        exercise: Nom de l'exercice.
        output_dir: Dossier de sortie.

    Returns:
        Dict {label: chemin_image_annotee}.
    """
    out_dir = Path(output_dir) if output_dir else Path(extraction.video_path).parent / "formcheck_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    angles_by_frame: dict[int, FrameAngles] = {
        fa.frame_index: fa for fa in angles.frames
    }
    landmarks_by_frame: dict[int, FrameLandmarks] = {
        fl.frame_index: fl for fl in extraction.frames
    }

    annotated_paths: dict[str, str] = {}

    for label, frame_idx in extraction.key_frame_indices.items():
        image_path = extraction.key_frame_images.get(label)
        if not image_path or not Path(image_path).exists():
            continue

        frame_lm = landmarks_by_frame.get(frame_idx)
        frame_ang = angles_by_frame.get(frame_idx)

        if not frame_lm or not frame_ang:
            closest_idx = min(
                angles_by_frame.keys(),
                key=lambda x: abs(x - frame_idx),
                default=None,
            )
            if closest_idx is not None:
                frame_ang = angles_by_frame[closest_idx]
                frame_lm = landmarks_by_frame.get(closest_idx, frame_lm)
            if not frame_lm or not frame_ang:
                continue

        annotated = annotate_frame(image_path, frame_lm, frame_ang, exercise, label)

        output_path = out_dir / f"annotated_{label}_{frame_idx}.jpg"
        cv2.imwrite(str(output_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        annotated_paths[label] = str(output_path)

    return annotated_paths
