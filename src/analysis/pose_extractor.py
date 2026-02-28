"""Extraction de landmarks via MediaPipe Pose Landmarker (tasks API).

Traite une vidéo frame par frame, extrait les 33 landmarks de pose,
et identifie les frames clés (début, milieu/point bas, fin du mouvement).
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# ── Modèle pose ─────────────────────────────────────────────────────────

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "pose_landmarker_heavy.task"

LANDMARK_NAMES: list[str] = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]


def _ensure_model() -> str:
    """Download the pose landmarker model if not present."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        print(f"Downloading pose landmarker model to {MODEL_PATH}...")
        urllib.request.urlretrieve(MODEL_URL, str(MODEL_PATH))
        print("Download complete.")
    return str(MODEL_PATH)


@dataclass
class FrameLandmarks:
    frame_index: int
    timestamp_ms: float
    landmarks: list[dict[str, float]]
    avg_visibility: float = 0.0


@dataclass
class ExtractionResult:
    video_path: str
    fps: float
    total_frames: int
    width: int
    height: int
    frames: list[FrameLandmarks] = field(default_factory=list)
    key_frame_indices: dict[str, int] = field(default_factory=dict)
    key_frame_images: dict[str, str] = field(default_factory=dict)


def _landmark_to_dict(lm: Any, name: str) -> dict[str, float]:
    return {
        "name": name,
        "x": float(lm.x),
        "y": float(lm.y),
        "z": float(lm.z),
        "visibility": float(lm.visibility) if hasattr(lm, "visibility") else 1.0,
    }


def _compute_hip_y(landmarks: list[dict[str, float]]) -> float:
    left_hip = next((lm for lm in landmarks if lm["name"] == "left_hip"), None)
    right_hip = next((lm for lm in landmarks if lm["name"] == "right_hip"), None)
    if left_hip and right_hip:
        return (left_hip["y"] + right_hip["y"]) / 2.0
    return 0.0


def _detect_key_frames(frames: list[FrameLandmarks], exercise: str = "") -> dict[str, int]:
    """Detect key frames using exercise-specific landmark tracking.
    
    Uses the ExercisePhase database to know WHICH body part to track
    and in WHICH direction the peak contraction occurs.
    
    Example: upright_row tracks WRISTS going UP (min_y = peak contraction)
             squat tracks HIPS going DOWN (max_y = peak contraction)
    """
    if not frames:
        return {"start": 0, "mid": 0, "end": 0}
    valid = [f for f in frames if f.avg_visibility > 0.3]
    if not valid:
        valid = frames

    # Try to get exercise-specific phase data
    phase = None
    if exercise:
        try:
            from analysis.exercise_phases import get_phase, get_tracking_y
            phase = get_phase(exercise)
        except ImportError:
            pass

    if phase:
        # Exercise-specific: track the correct landmark(s)
        tracking_values = [get_tracking_y(f.landmarks, phase) for f in valid]
        
        if phase.peak_direction == "min_y":
            mid_idx_pos = int(np.argmin(tracking_values))
        else:
            mid_idx_pos = int(np.argmax(tracking_values))
    else:
        # Fallback: use hip_y (original behavior)
        tracking_values = [_compute_hip_y(f.landmarks) for f in valid]
        mid_idx_pos = int(np.argmax(tracking_values))

    mid_idx = valid[mid_idx_pos].frame_index

    # Start: frame at ~10% (skip setup)
    start_pos = max(0, len(valid) // 10)
    start_idx = valid[start_pos].frame_index

    # End: find the return position after peak contraction
    end_idx = valid[-1].frame_index  # fallback
    if mid_idx_pos < len(valid) - 1:
        post_mid = tracking_values[mid_idx_pos:]
        if post_mid:
            # Return = opposite direction from peak
            if phase and phase.peak_direction == "min_y":
                local_opp_pos = int(np.argmax(post_mid))
            elif phase and phase.peak_direction == "max_y":
                local_opp_pos = int(np.argmin(post_mid))
            else:
                local_opp_pos = int(np.argmin(post_mid))
            if local_opp_pos > 0:
                end_pos = mid_idx_pos + local_opp_pos
                end_idx = valid[min(end_pos, len(valid) - 1)].frame_index

    return {"start": start_idx, "mid": mid_idx, "end": end_idx}


def _save_key_frame(video_path: str, frame_index: int, label: str, output_dir: Path) -> str:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return ""
    output_path = output_dir / f"key_frame_{label}_{frame_index}.jpg"
    cv2.imwrite(str(output_path), frame)
    return str(output_path)


def extract_pose(
    video_path: str,
    output_dir: str | None = None,
    model_complexity: int = 2,
    min_detection_confidence: float = 0.3,
    min_tracking_confidence: float = 0.3,
    sample_every_n: int = 1,
) -> ExtractionResult:
    """Extract pose landmarks from a video using MediaPipe Tasks API."""
    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Vidéo introuvable : {video_path}")

    out_dir = Path(output_dir) if output_dir else video.parent / "formcheck_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = _ensure_model()

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo : {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    result = ExtractionResult(
        video_path=str(video), fps=fps, total_frames=total_frames,
        width=width, height=height,
    )

    # Create PoseLandmarker
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        frame_idx = 0
        _prev_center: tuple[float, float] | None = None
        _prev_landmarks: list[Any] | None = None
        _motion_scores: dict[int, float] = {}  # person_idx → cumulative motion
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_every_n != 0:
                frame_idx += 1
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int((frame_idx / fps) * 1000) if fps > 0 else frame_idx * 33

            detection_result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
                # Multi-person: pick the person closest to the previous frame's tracked person
                # (temporal consistency). First frame uses largest bounding box.
                lms = detection_result.pose_landmarks[0]
                if len(detection_result.pose_landmarks) > 1:
                    best_idx = 0
                    if _prev_center is not None and _prev_landmarks is not None:
                        # Pick person whose landmarks are closest to previous AND
                        # accumulate motion score for each person
                        best_score = float("inf")
                        for p_idx, p_lms in enumerate(detection_result.pose_landmarks):
                            cx = float(np.mean([p_lms[i].x for i in range(min(len(p_lms), 33))]))
                            cy = float(np.mean([p_lms[i].y for i in range(min(len(p_lms), 33))]))
                            dist = (cx - _prev_center[0]) ** 2 + (cy - _prev_center[1]) ** 2
                            if dist < best_score:
                                best_score = dist
                                best_idx = p_idx
                    elif _motion_scores and frame_idx > 30:
                        # After 30 frames, pick person with MOST motion (the one exercising)
                        best_idx = max(_motion_scores, key=_motion_scores.get)
                    else:
                        # First frames: pick largest bounding box
                        best_area = 0.0
                        for p_idx, p_lms in enumerate(detection_result.pose_landmarks):
                            xs = [p_lms[i].x for i in range(min(len(p_lms), 33))]
                            ys = [p_lms[i].y for i in range(min(len(p_lms), 33))]
                            area = (max(xs) - min(xs)) * (max(ys) - min(ys))
                            if area > best_area:
                                best_area = area
                                best_idx = p_idx
                    lms = detection_result.pose_landmarks[best_idx]
                # Accumulate motion scores for multi-person tracking
                if len(detection_result.pose_landmarks) > 1 and _prev_landmarks is not None:
                    for p_idx, p_lms in enumerate(detection_result.pose_landmarks):
                        # Calculate total landmark displacement vs previous frame
                        motion = 0.0
                        for li in range(min(len(p_lms), 33)):
                            if _prev_landmarks and li < len(_prev_landmarks):
                                dx = p_lms[li].x - _prev_landmarks[li].x
                                dy = p_lms[li].y - _prev_landmarks[li].y
                                motion += dx * dx + dy * dy
                        _motion_scores[p_idx] = _motion_scores.get(p_idx, 0.0) + motion
                _prev_landmarks = lms

                # Update tracked center for next frame
                _prev_center = (
                    float(np.mean([lms[i].x for i in range(min(len(lms), 33))])),
                    float(np.mean([lms[i].y for i in range(min(len(lms), 33))])),
                )
                landmarks = [
                    _landmark_to_dict(lms[i], LANDMARK_NAMES[i])
                    for i in range(min(len(lms), len(LANDMARK_NAMES)))
                ]
                avg_vis = float(np.mean([lm["visibility"] for lm in landmarks]))
                fl = FrameLandmarks(
                    frame_index=frame_idx,
                    timestamp_ms=float(timestamp_ms),
                    landmarks=landmarks,
                    avg_visibility=avg_vis,
                )
                result.frames.append(fl)

            frame_idx += 1

    cap.release()

    result.key_frame_indices = _detect_key_frames(result.frames)
    for label, fidx in result.key_frame_indices.items():
        path = _save_key_frame(str(video), fidx, label, out_dir)
        if path:
            result.key_frame_images[label] = path

    return result


def extraction_to_json(result: ExtractionResult) -> dict[str, Any]:
    return {
        "video_path": result.video_path,
        "fps": result.fps,
        "total_frames": result.total_frames,
        "resolution": {"width": result.width, "height": result.height},
        "extracted_frames": len(result.frames),
        "key_frame_indices": result.key_frame_indices,
        "key_frame_images": result.key_frame_images,
        "frames": [
            {
                "frame_index": f.frame_index,
                "timestamp_ms": round(f.timestamp_ms, 1),
                "avg_visibility": round(f.avg_visibility, 3),
                "landmarks": [
                    {k: round(v, 5) if isinstance(v, float) else v for k, v in lm.items()}
                    for lm in f.landmarks
                ],
            }
            for f in result.frames
        ],
    }


def save_extraction_json(result: ExtractionResult, output_path: str) -> str:
    data = extraction_to_json(result)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(path)
