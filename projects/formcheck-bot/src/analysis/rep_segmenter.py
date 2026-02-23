"""Détection automatique des répétitions individuelles.

Segmente le signal angulaire principal en reps via détection
de pics et vallées, puis calcule tempo, ROM, vitesse, fatigue
et détection de triche pour chaque rep.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from analysis.angle_calculator import AngleResult, FrameAngles

logger = logging.getLogger("formcheck.rep_segmenter")

# Mapping exercice → attribut d'angle principal pour la segmentation
PRIMARY_ANGLE_MAP: dict[str, str] = {
    # Jambes / squat
    "squat": "left_knee_flexion",
    "front_squat": "left_knee_flexion",
    "goblet_squat": "left_knee_flexion",
    "bulgarian_split_squat": "left_knee_flexion",
    "lunge": "left_knee_flexion",
    "leg_press": "left_knee_flexion",
    "leg_extension": "left_knee_flexion",
    "leg_curl": "left_knee_flexion",
    # Hanches / deadlift
    "deadlift": "left_hip_flexion",
    "sumo_deadlift": "left_hip_flexion",
    "rdl": "left_hip_flexion",
    "hip_thrust": "left_hip_flexion",
    # Bras / poussée-tirage
    "bench_press": "left_elbow_flexion",
    "incline_bench": "left_elbow_flexion",
    "ohp": "left_elbow_flexion",
    "curl": "left_elbow_flexion",
    "tricep_extension": "left_elbow_flexion",
    "barbell_row": "left_elbow_flexion",
    "dumbbell_row": "left_elbow_flexion",
    "pullup": "left_elbow_flexion",
    "lat_pulldown": "left_elbow_flexion",
    "face_pull": "left_elbow_flexion",
    # Épaules
    "lateral_raise": "left_shoulder_abduction",
}

# Exercices lents nécessitant des paramètres de détection adaptatifs
SLOW_EXERCISES: set[str] = {
    "rdl", "hip_thrust", "leg_curl", "leg_extension",
    "lateral_raise", "face_pull", "tricep_extension",
}

# Angle secondaire pour la détection de triche (mouvement parasite du tronc)
CHEAT_ANGLE_MAP: dict[str, str] = {
    "curl": "torso_inclination",
    "barbell_row": "torso_inclination",
    "dumbbell_row": "torso_inclination",
    "ohp": "torso_inclination",
    "lateral_raise": "torso_inclination",
    "bench_press": "torso_inclination",
    "squat": "torso_inclination",
    "front_squat": "torso_inclination",
    "deadlift": "torso_inclination",
}

# Seuils de triche : variation max acceptable du tronc pendant une rep (degrés)
CHEAT_THRESHOLD: dict[str, float] = {
    "curl": 10.0,
    "barbell_row": 12.0,
    "dumbbell_row": 12.0,
    "ohp": 8.0,
    "lateral_raise": 8.0,
    "bench_press": 5.0,
    "squat": 15.0,
    "front_squat": 12.0,
    "deadlift": 20.0,
}


@dataclass
class Rep:
    """Une répétition individuelle."""
    rep_number: int = 0
    start_frame: int = 0
    end_frame: int = 0
    bottom_frame: int = 0
    eccentric_frames: tuple[int, int] = (0, 0)
    concentric_frames: tuple[int, int] = (0, 0)
    eccentric_duration_ms: float = 0.0
    concentric_duration_ms: float = 0.0
    tempo_ratio: float = 0.0
    rom: float = 0.0
    peak_velocity: float = 0.0
    # Fatigue
    fatigue_index: float = 0.0  # 0 = frais, 1 = fatigue significative
    rom_vs_first: float = 1.0  # ratio ROM cette rep / rep 1
    velocity_vs_first: float = 1.0  # ratio vitesse / rep 1
    # Triche / momentum
    cheat_detected: bool = False
    cheat_score: float = 0.0  # 0 = clean, 1 = triche flagrante
    cheat_details: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {
            "rep_number": self.rep_number,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "bottom_frame": self.bottom_frame,
            "eccentric_frames": list(self.eccentric_frames),
            "concentric_frames": list(self.concentric_frames),
            "eccentric_duration_ms": round(self.eccentric_duration_ms, 0),
            "concentric_duration_ms": round(self.concentric_duration_ms, 0),
            "tempo_ratio": round(self.tempo_ratio, 2),
            "rom": round(self.rom, 1),
            "peak_velocity": round(self.peak_velocity, 1),
            "fatigue_index": round(self.fatigue_index, 3),
            "rom_vs_first": round(self.rom_vs_first, 3),
            "velocity_vs_first": round(self.velocity_vs_first, 3),
        }
        if self.cheat_detected:
            d["cheat_detected"] = True
            d["cheat_score"] = round(self.cheat_score, 2)
            d["cheat_details"] = self.cheat_details
        return d


@dataclass
class RepSegmentation:
    """Résultat de la segmentation en répétitions."""
    reps: list[Rep] = field(default_factory=list)
    total_reps: int = 0
    avg_tempo: str = "0:0:0"
    tempo_consistency: float = 0.0
    # Fatigue globale
    avg_rom: float = 0.0
    rom_degradation: float = 0.0  # % perte ROM entre première et dernière rep
    velocity_degradation: float = 0.0  # % perte vitesse concentrique
    fatigue_onset_rep: int = 0  # rep où la fatigue commence (ROM < 90% de rep 1)
    # Triche globale
    cheat_reps: list[int] = field(default_factory=list)
    cheat_percentage: float = 0.0  # % de reps avec triche détectée

    def to_dict(self) -> dict[str, Any]:
        d = {
            "reps": [r.to_dict() for r in self.reps],
            "total_reps": self.total_reps,
            "avg_tempo": self.avg_tempo,
            "tempo_consistency": round(self.tempo_consistency, 3),
            "avg_rom": round(self.avg_rom, 1),
            "rom_degradation": round(self.rom_degradation, 1),
            "velocity_degradation": round(self.velocity_degradation, 1),
            "fatigue_onset_rep": self.fatigue_onset_rep,
        }
        if self.cheat_reps:
            d["cheat_reps"] = self.cheat_reps
            d["cheat_percentage"] = round(self.cheat_percentage, 1)
        return d


def _get_signal(
    angle_frames: list[FrameAngles],
    attr: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrait le signal d'un angle et les indices de frames correspondants."""
    values = []
    indices = []
    for f in angle_frames:
        val = getattr(f, attr, None)
        if val is not None:
            values.append(val)
            indices.append(f.frame_index)
    return np.array(values), np.array(indices)


def _smooth_signal(signal: np.ndarray, window: int = 5) -> np.ndarray:
    """Lissage simple par moyenne mobile."""
    if len(signal) < window:
        return signal
    kernel = np.ones(window) / window
    padded = np.pad(signal, (window // 2, window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")[:len(signal)]


def _adaptive_params(exercise: str, signal: np.ndarray, fps: float) -> dict[str, float]:
    """Paramètres adaptatifs selon le type d'exercice et la durée du signal.

    Les exercices lents (RDL, hip thrust, lateral raise...) ont des pics
    moins prononcés et des mouvements plus longs — on adapte le lissage,
    la prominence minimale et la distance minimale entre pics.
    """
    rom_total = float(np.max(signal) - np.min(signal))
    duration_s = len(signal) / max(fps, 1.0)

    if exercise in SLOW_EXERCISES:
        # Fenêtre de lissage plus large pour les mouvements lents
        smooth_window = min(11, max(7, int(fps * 0.4)))
        # Prominence réduite — les pics sont moins marqués
        min_prominence = max(rom_total * 0.12, 3.0)
        # Distance plus grande entre pics — reps plus longues
        min_distance = max(8, int(fps * 0.6))
    else:
        smooth_window = min(7, max(5, int(fps * 0.2)))
        min_prominence = max(rom_total * 0.20, 5.0)
        min_distance = max(5, int(fps * 0.3))

    # Si peu de signal (vidéo courte), réduire la distance
    if len(signal) < 40:
        min_distance = max(3, min_distance // 2)

    return {
        "smooth_window": smooth_window,
        "min_prominence": min_prominence,
        "min_distance": min_distance,
    }


def _find_peaks_valleys(
    signal: np.ndarray,
    min_prominence: float = 10.0,
    min_distance: int = 5,
):
    """Trouve les pics et vallées du signal."""
    try:
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(signal, prominence=min_prominence, distance=min_distance)
        valleys, _ = find_peaks(-signal, prominence=min_prominence, distance=min_distance)
        return peaks, valleys
    except ImportError:
        logger.warning("scipy non disponible, détection manuelle des pics.")
        return _manual_find_peaks(signal, min_prominence, min_distance)


def _manual_find_peaks(
    signal: np.ndarray,
    min_prominence: float,
    min_distance: int = 5,
):
    """Détection manuelle des pics/vallées sans scipy."""
    peaks = []
    valleys = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1]:
            # Vérifier distance avec le dernier pic
            if not peaks or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
        elif signal[i] < signal[i - 1] and signal[i] < signal[i + 1]:
            if not valleys or (i - valleys[-1]) >= min_distance:
                valleys.append(i)
    return np.array(peaks), np.array(valleys)


def _compute_fatigue(reps: list[Rep]) -> None:
    """Calcule les métriques de fatigue pour chaque rep (in-place).

    La fatigue se manifeste par :
    - Diminution du ROM (amplitude réduite)
    - Diminution de la vitesse concentrique (perte de puissance)
    - Augmentation du tempo concentrique (plus lent à remonter)
    """
    if len(reps) < 2:
        return

    first_rom = reps[0].rom if reps[0].rom > 0 else 1.0
    first_vel = reps[0].peak_velocity if reps[0].peak_velocity > 0 else 1.0
    first_conc = reps[0].concentric_duration_ms if reps[0].concentric_duration_ms > 0 else 1.0

    for rep in reps:
        # Ratios vs première rep
        rep.rom_vs_first = rep.rom / first_rom if first_rom > 0 else 1.0
        rep.velocity_vs_first = rep.peak_velocity / first_vel if first_vel > 0 else 1.0

        # Index de fatigue composite (0 = frais, 1 = épuisé)
        rom_loss = max(0.0, 1.0 - rep.rom_vs_first)
        vel_loss = max(0.0, 1.0 - rep.velocity_vs_first)
        conc_increase = max(0.0, (rep.concentric_duration_ms / first_conc) - 1.0) if first_conc > 0 else 0.0
        conc_increase = min(conc_increase, 1.0)  # Cap à 1.0

        # Pondération : ROM 40%, vitesse 35%, ralentissement concentrique 25%
        rep.fatigue_index = min(1.0, rom_loss * 0.40 + vel_loss * 0.35 + conc_increase * 0.25)


def _detect_cheat(
    reps: list[Rep],
    angle_frames: list[FrameAngles],
    frame_indices: np.ndarray,
    exercise: str,
) -> None:
    """Détecte la triche/momentum sur chaque rep (in-place).

    Analyse le mouvement parasite du tronc pendant la phase concentrique :
    - Curl : swing du torse pour aider à monter la barre
    - Row : extension excessive du tronc
    - Squat/deadlift : inclinaison excessive du buste
    """
    cheat_attr = CHEAT_ANGLE_MAP.get(exercise)
    if not cheat_attr:
        return

    threshold = CHEAT_THRESHOLD.get(exercise, 15.0)

    # Extraire le signal du tronc
    trunk_signal, trunk_indices = _get_signal(angle_frames, cheat_attr)
    if len(trunk_signal) < 5:
        return

    for rep in reps:
        # Trouver les frames du tronc correspondant à la phase concentrique
        conc_start, conc_end = rep.concentric_frames
        mask = (trunk_indices >= conc_start) & (trunk_indices <= conc_end)
        conc_trunk = trunk_signal[mask]

        if len(conc_trunk) < 2:
            continue

        # Variation du tronc pendant la concentrique
        trunk_range = float(np.max(conc_trunk) - np.min(conc_trunk))
        # Vitesse max de changement du tronc (° par frame)
        trunk_velocity = np.max(np.abs(np.diff(conc_trunk))) if len(conc_trunk) > 1 else 0.0

        # Score de triche : combien le tronc bouge vs le seuil
        cheat_score = min(1.0, trunk_range / threshold) if threshold > 0 else 0.0

        # Bonus si la vitesse du tronc est élevée (mouvement explosif = momentum)
        if trunk_velocity > threshold * 0.3:
            cheat_score = min(1.0, cheat_score + 0.2)

        rep.cheat_score = cheat_score
        if cheat_score >= 0.5:
            rep.cheat_detected = True
            if cheat_score >= 0.8:
                rep.cheat_details = f"Mouvement du tronc excessif ({trunk_range:.0f}°) — momentum flagrant"
            elif cheat_score >= 0.6:
                rep.cheat_details = f"Compensation du tronc ({trunk_range:.0f}°) — charge probablement trop lourde"
            else:
                rep.cheat_details = f"Légère compensation du tronc ({trunk_range:.0f}°)"


def segment_reps(
    angles: AngleResult,
    exercise: str,
    fps: float = 30.0,
) -> RepSegmentation:
    """Segmente les répétitions à partir du signal angulaire.

    Args:
        angles: Résultat du calcul d'angles.
        exercise: Nom de l'exercice (valeur de l'enum Exercise).
        fps: FPS de la vidéo pour calculer les durées.

    Returns:
        RepSegmentation avec les reps détectées, fatigue et triche.
    """
    result = RepSegmentation()

    # Déterminer l'angle principal
    attr = PRIMARY_ANGLE_MAP.get(exercise)
    if not attr:
        logger.warning("Exercice '%s' non mappé, essai avec left_knee_flexion.", exercise)
        attr = "left_knee_flexion"

    signal, frame_indices = _get_signal(angles.frames, attr)
    if len(signal) < 10:
        logger.warning("Signal trop court (%d points) pour détecter des reps.", len(signal))
        return result

    # Paramètres adaptatifs selon l'exercice
    params = _adaptive_params(exercise, signal, fps)

    # Lisser le signal
    smoothed = _smooth_signal(signal, window=int(params["smooth_window"]))

    # Détecter pics et vallées
    peaks, valleys = _find_peaks_valleys(
        smoothed,
        min_prominence=params["min_prominence"],
        min_distance=int(params["min_distance"]),
    )

    if len(valleys) < 2:
        # Pas assez de vallées pour segmenter
        # Essayer avec les pics comme délimiteurs
        if len(peaks) >= 2:
            valleys, peaks = peaks, valleys
        else:
            # Dernier recours : réduire la prominence de 50% et réessayer
            logger.info("Pas assez de points, réduction prominence de 50%%.")
            reduced_prom = params["min_prominence"] * 0.5
            peaks, valleys = _find_peaks_valleys(
                smoothed,
                min_prominence=reduced_prom,
                min_distance=max(3, int(params["min_distance"] * 0.7)),
            )
            if len(valleys) < 2 and len(peaks) >= 2:
                valleys, peaks = peaks, valleys
            elif len(valleys) < 2:
                logger.warning("Pas assez de points caractéristiques pour segmenter.")
                return result

    # Construire les reps : valley[i] → bottom (peak entre) → valley[i+1]
    reps: list[Rep] = []

    for i in range(len(valleys) - 1):
        v_start = valleys[i]
        v_end = valleys[i + 1]

        # Trouver le pic (bottom) entre les deux vallées
        between_peaks = peaks[(peaks > v_start) & (peaks < v_end)]
        if len(between_peaks) == 0:
            segment = smoothed[v_start:v_end + 1]
            bottom_local = (
                int(np.argmin(segment))
                if np.mean(smoothed[peaks]) < np.mean(smoothed[valleys])
                else int(np.argmax(segment))
            )
            bottom_idx = v_start + bottom_local
        else:
            bottom_idx = between_peaks[0]

        # Frames réelles
        sf = int(frame_indices[v_start])
        ef = int(frame_indices[v_end])
        bf = int(frame_indices[bottom_idx])

        # Durées
        ecc_ms = (bf - sf) / fps * 1000 if fps > 0 else 0
        conc_ms = (ef - bf) / fps * 1000 if fps > 0 else 0

        # Filtrer les reps aberrantes (trop courtes ou trop longues)
        total_ms = ecc_ms + conc_ms
        if total_ms < 200:  # Rep < 200ms = bruit
            continue
        if total_ms > 15000:  # Rep > 15s = probablement deux reps fusionnées
            continue

        # ROM de cette rep
        rep_signal = smoothed[v_start:v_end + 1]
        rep_rom = float(np.max(rep_signal) - np.min(rep_signal))

        # Vitesse angulaire max en concentrique
        conc_signal = smoothed[bottom_idx:v_end + 1]
        if len(conc_signal) > 1:
            velocities = np.abs(np.diff(conc_signal)) * fps
            peak_vel = float(np.max(velocities))
        else:
            peak_vel = 0.0

        # Tempo ratio
        tempo_ratio = ecc_ms / conc_ms if conc_ms > 0 else 0.0

        rep = Rep(
            rep_number=len(reps) + 1,
            start_frame=sf,
            end_frame=ef,
            bottom_frame=bf,
            eccentric_frames=(sf, bf),
            concentric_frames=(bf, ef),
            eccentric_duration_ms=ecc_ms,
            concentric_duration_ms=conc_ms,
            tempo_ratio=tempo_ratio,
            rom=rep_rom,
            peak_velocity=peak_vel,
        )
        reps.append(rep)

    # ── Analyse de fatigue ──────────────────────────────────────────────
    _compute_fatigue(reps)

    # ── Détection de triche ─────────────────────────────────────────────
    _detect_cheat(reps, angles.frames, frame_indices, exercise)

    result.reps = reps
    result.total_reps = len(reps)

    # ── Métriques globales ──────────────────────────────────────────────
    if reps:
        # Tempo moyen
        avg_ecc = np.mean([r.eccentric_duration_ms for r in reps]) / 1000
        avg_conc = np.mean([r.concentric_duration_ms for r in reps]) / 1000
        result.avg_tempo = f"{avg_ecc:.0f}:0:{avg_conc:.0f}"

        # Consistance du tempo
        if len(reps) > 1:
            ratios = [r.tempo_ratio for r in reps if r.tempo_ratio > 0]
            if ratios:
                std = float(np.std(ratios))
                mean = float(np.mean(ratios))
                cv = std / mean if mean > 0 else 1.0
                result.tempo_consistency = max(0.0, min(1.0, 1.0 - cv))

        # ROM moyen et dégradation
        roms = [r.rom for r in reps if r.rom > 0]
        if roms:
            result.avg_rom = float(np.mean(roms))
            if len(roms) >= 2:
                first_rom = roms[0]
                last_rom = roms[-1]
                if first_rom > 0:
                    result.rom_degradation = max(0.0, (1.0 - last_rom / first_rom) * 100)

        # Dégradation de vitesse
        vels = [r.peak_velocity for r in reps if r.peak_velocity > 0]
        if len(vels) >= 2:
            first_vel = vels[0]
            last_vel = vels[-1]
            if first_vel > 0:
                result.velocity_degradation = max(0.0, (1.0 - last_vel / first_vel) * 100)

        # Rep d'apparition de la fatigue (ROM < 90% de la première)
        if len(reps) >= 3:
            for rep in reps[1:]:
                if rep.rom_vs_first < 0.90:
                    result.fatigue_onset_rep = rep.rep_number
                    break

        # Triche
        cheat_list = [r.rep_number for r in reps if r.cheat_detected]
        result.cheat_reps = cheat_list
        if reps:
            result.cheat_percentage = (len(cheat_list) / len(reps)) * 100

    logger.info(
        "Segmentation: %d reps, tempo=%s, ROM_deg=%.0f%%, fatigue_onset=rep%d, triche=%d%%",
        result.total_reps, result.avg_tempo,
        result.rom_degradation, result.fatigue_onset_rep,
        result.cheat_percentage,
    )
    return result
