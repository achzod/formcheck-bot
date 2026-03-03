"""Construit une base de regles biomecaniques a partir du scrape brut.

Ce module lit `exrx_exercises` (SQLite), infere une "famille de mouvement",
applique un template biomecanique deterministe, puis sauvegarde les regles
dans `exercise_rules` (SQLite) + export JSON optionnel.
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("scraper.rules_builder")

DEFAULT_DB_PATH = "database/rules_db.sqlite"


@dataclass
class RuleBuildConfig:
    db_path: str = DEFAULT_DB_PATH
    min_confidence: float = 0.35
    limit: int = 0
    export_json: str = ""
    include_low_confidence: bool = False


BASE_RULE_TEMPLATES: dict[str, dict[str, Any]] = {
    "squat": {
        "category": "lower_body",
        "phase_direction": "max_y",
        "ideal_angles": {"knee_flexion_deg": [85, 105], "hip_flexion_deg": [95, 125]},
        "rom_targets_deg": {"knee": [70, 130], "hip": [70, 130], "trunk": [10, 45]},
        "tempo_target": "3-1-2-1",
        "risk_thresholds": {"knee_valgus_deg_red": 18, "lumbar_flexion_deg_red": 22},
        "compensations": ["knee_valgus", "heel_lift", "lumbar_rounding", "asymmetric_shift"],
        "recruitment_reference": {"quads": 0.48, "glutes": 0.34, "adductors": 0.08, "erectors": 0.10},
    },
    "lunge": {
        "category": "lower_body_unilateral",
        "phase_direction": "max_y",
        "ideal_angles": {"front_knee_flexion_deg": [80, 105], "rear_knee_flexion_deg": [70, 100]},
        "rom_targets_deg": {"knee": [65, 120], "hip": [55, 115], "trunk": [8, 35]},
        "tempo_target": "2-1-2-1",
        "risk_thresholds": {"knee_valgus_deg_red": 15, "pelvic_drop_deg_red": 8},
        "compensations": ["front_knee_collapse", "rear_leg_push_dominance", "pelvis_rotation"],
        "recruitment_reference": {"quads": 0.42, "glutes": 0.36, "adductors": 0.12, "calves": 0.10},
    },
    "hinge": {
        "category": "lower_body_posterior_chain",
        "phase_direction": "max_y",
        "ideal_angles": {"hip_flexion_deg": [65, 115], "knee_flexion_deg": [12, 35]},
        "rom_targets_deg": {"hip": [55, 120], "trunk": [20, 65], "knee": [8, 45]},
        "tempo_target": "3-1-1-1",
        "risk_thresholds": {"lumbar_flexion_deg_red": 20, "bar_path_deviation_cm_red": 8},
        "compensations": ["lumbar_rounding", "early_knee_extension", "asymmetric_hip_shift"],
        "recruitment_reference": {"glutes": 0.34, "hamstrings": 0.32, "erectors": 0.22, "quads": 0.12},
    },
    "horizontal_press": {
        "category": "upper_body_push",
        "phase_direction": "max_y",
        "ideal_angles": {"elbow_flexion_deg": [75, 120], "shoulder_abduction_deg": [35, 75]},
        "rom_targets_deg": {"elbow": [35, 125], "shoulder_flexion": [10, 70]},
        "tempo_target": "3-1-1-1",
        "risk_thresholds": {"elbow_flare_deg_red": 78, "wrist_extension_deg_red": 45},
        "compensations": ["elbow_flare", "shoulder_protraction", "bar_path_drift"],
        "recruitment_reference": {"chest": 0.50, "triceps": 0.28, "front_delts": 0.22},
    },
    "vertical_press": {
        "category": "upper_body_push",
        "phase_direction": "min_y",
        "ideal_angles": {"elbow_flexion_deg": [70, 165], "shoulder_flexion_deg": [65, 170]},
        "rom_targets_deg": {"elbow": [40, 170], "shoulder_flexion": [40, 175], "trunk": [0, 20]},
        "tempo_target": "2-0-1-1",
        "risk_thresholds": {"lumbar_extension_deg_red": 18, "shoulder_shrug_red": 0.65},
        "compensations": ["lumbar_hyperextension", "bar_path_forward", "elbow_lag"],
        "recruitment_reference": {"front_delts": 0.42, "triceps": 0.36, "upper_chest": 0.12, "upper_traps": 0.10},
    },
    "row": {
        "category": "upper_body_pull",
        "phase_direction": "min_y",
        "ideal_angles": {"elbow_flexion_deg": [55, 130], "shoulder_extension_deg": [20, 70]},
        "rom_targets_deg": {"elbow": [35, 130], "shoulder_extension": [15, 80], "trunk": [0, 40]},
        "tempo_target": "2-1-2-1",
        "risk_thresholds": {"lumbar_flexion_deg_red": 20, "scapular_wing_red": 0.6},
        "compensations": ["upper_trap_dominance", "lumbar_swing", "elbow_flare_excessive"],
        "recruitment_reference": {"lats": 0.38, "mid_back": 0.30, "rear_delts": 0.16, "biceps": 0.16},
    },
    "vertical_pull": {
        "category": "upper_body_pull",
        "phase_direction": "max_y",
        "ideal_angles": {"elbow_flexion_deg": [55, 130], "shoulder_adduction_deg": [20, 95]},
        "rom_targets_deg": {"elbow": [35, 135], "shoulder_adduction": [20, 105], "trunk": [0, 30]},
        "tempo_target": "2-1-2-1",
        "risk_thresholds": {"neck_protrusion_red": 0.65, "lumbar_extension_deg_red": 18},
        "compensations": ["neck_jut", "swinging_torso", "elbow_path_asymmetry"],
        "recruitment_reference": {"lats": 0.46, "teres_major": 0.14, "biceps": 0.22, "mid_back": 0.18},
    },
    "arm_isolation": {
        "category": "upper_body_isolation",
        "phase_direction": "min_y",
        "ideal_angles": {"elbow_flexion_deg": [40, 145]},
        "rom_targets_deg": {"elbow": [35, 150], "trunk": [0, 15]},
        "tempo_target": "2-1-2-1",
        "risk_thresholds": {"trunk_swing_deg_red": 12, "wrist_extension_deg_red": 42},
        "compensations": ["trunk_swing", "elbow_drift", "wrist_collapse"],
        "recruitment_reference": {"prime_mover": 0.68, "secondary": 0.22, "stabilizers": 0.10},
    },
    "raise": {
        "category": "upper_body_isolation",
        "phase_direction": "min_y",
        "ideal_angles": {"shoulder_abduction_deg": [20, 95], "elbow_flexion_deg": [150, 175]},
        "rom_targets_deg": {"shoulder_abduction": [15, 100], "trunk": [0, 18]},
        "tempo_target": "2-1-2-1",
        "risk_thresholds": {"upper_trap_compensation_red": 0.72, "trunk_lean_deg_red": 14},
        "compensations": ["upper_trap_shrug", "arm_internal_rotation", "momentum_swing"],
        "recruitment_reference": {"middle_delts": 0.52, "front_delts": 0.18, "upper_traps": 0.20, "supraspinatus": 0.10},
    },
    "generic": {
        "category": "generic",
        "phase_direction": "max_y",
        "ideal_angles": {},
        "rom_targets_deg": {},
        "tempo_target": "2-1-2-1",
        "risk_thresholds": {"lumbar_flexion_deg_red": 22},
        "compensations": ["asymmetry", "momentum", "range_of_motion_loss"],
        "recruitment_reference": {},
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads_list(raw: Any) -> list[str]:
    if raw in (None, ""):
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw]
    try:
        value = json.loads(str(raw))
    except Exception:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def infer_movement_pattern(name: str, body_part: str, raw_text: str) -> tuple[str, float]:
    low = " ".join([name or "", body_part or "", raw_text or ""]).lower()
    score = 0.25

    def has(*tokens: str) -> bool:
        return any(tok in low for tok in tokens)

    if has("bulgarian", "split squat", "lunge", "fente"):
        return "lunge", 0.88
    if has("squat", "hack squat", "leg press"):
        return "squat", 0.82
    if has("deadlift", "rdl", "good morning", "hip hinge", "hip thrust", "glute bridge"):
        return "hinge", 0.84
    if has("bench press", "chest press", "push-up", "push up", "dip"):
        return "horizontal_press", 0.78
    if has("overhead press", "shoulder press", "military press", "ohp"):
        return "vertical_press", 0.82
    if has("pulldown", "pull-up", "pull up", "chin-up", "chin up"):
        return "vertical_pull", 0.80
    if has("row", "tirage horizontal"):
        return "row", 0.78
    if has("curl", "tricep extension", "triceps extension", "skull crusher"):
        return "arm_isolation", 0.76
    if has("raise", "lateral raise", "front raise", "rear delt fly", "face pull"):
        return "raise", 0.76

    # fallback faible mais explicite
    if body_part in {"quadriceps", "hamstrings", "glutes", "calves"}:
        return "squat", 0.45
    if body_part in {"back", "lats", "biceps"}:
        return "vertical_pull", 0.42
    if body_part in {"chest", "shoulders", "triceps"}:
        return "horizontal_press", 0.40
    return "generic", score


def _infer_phase_direction(pattern: str, name: str) -> str:
    low = name.lower()
    if pattern in {"vertical_press", "raise"}:
        return "min_y"
    if pattern in {"vertical_pull"}:
        if "pullover" in low:
            return "max_y"
        return "max_y"
    if pattern in {"row", "arm_isolation"}:
        return "min_y"
    return "max_y"


def _merge_muscle_distribution(
    primary_muscles: list[str],
    secondary_muscles: list[str],
    template: dict[str, Any],
) -> dict[str, float]:
    base = dict(template.get("recruitment_reference", {}))
    if not primary_muscles and not secondary_muscles:
        return base

    distribution: dict[str, float] = {}
    if primary_muscles:
        weight = 0.7 / len(primary_muscles)
        for muscle in primary_muscles:
            distribution[muscle] = distribution.get(muscle, 0.0) + weight
    if secondary_muscles:
        weight = 0.25 / len(secondary_muscles)
        for muscle in secondary_muscles:
            distribution[muscle] = distribution.get(muscle, 0.0) + weight
    if distribution:
        distribution["stabilizers"] = max(0.0, 1.0 - sum(distribution.values()))
        return distribution
    return base


def build_rule_payload(exercise_row: dict[str, Any]) -> tuple[dict[str, Any], float]:
    name = str(exercise_row.get("name", "Unknown Exercise"))
    body_part = str(exercise_row.get("body_part", "unknown"))
    raw_text = str(exercise_row.get("raw_text", ""))
    primary = _loads_list(exercise_row.get("primary_muscles"))
    secondary = _loads_list(exercise_row.get("secondary_muscles"))
    instructions = _loads_list(exercise_row.get("instructions"))
    risk_notes = _loads_list(exercise_row.get("risk_notes"))
    variations = _loads_list(exercise_row.get("variations"))

    pattern, confidence = infer_movement_pattern(name, body_part, raw_text)
    template = copy.deepcopy(BASE_RULE_TEMPLATES.get(pattern, BASE_RULE_TEMPLATES["generic"]))
    template["phase_direction"] = _infer_phase_direction(pattern, name)
    template["recruitment_reference"] = _merge_muscle_distribution(primary, secondary, template)

    payload = {
        "name": name,
        "exercise_key": exercise_row.get("exercise_key", ""),
        "source": exercise_row.get("source", "exrx"),
        "source_url": exercise_row.get("url", ""),
        "body_part": body_part,
        "pattern": pattern,
        "confidence": round(float(confidence), 3),
        "primary_muscles": primary,
        "secondary_muscles": secondary,
        "instructions": instructions,
        "risk_notes": risk_notes,
        "variations": variations,
        "biomechanics": template,
        "generated_at": _now_iso(),
    }
    return payload, float(confidence)


def _init_rules_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS exercise_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exrx_id INTEGER,
            exercise_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            pattern TEXT NOT NULL,
            confidence REAL NOT NULL,
            rules_json TEXT NOT NULL,
            source TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def build_rules_from_db(config: RuleBuildConfig) -> dict[str, Any]:
    db_path = Path(config.db_path)
    if not db_path.exists():
        raise FileNotFoundError("Database not found: {}".format(db_path))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _init_rules_table(conn)

    query = "SELECT * FROM exrx_exercises ORDER BY id ASC"
    params: tuple[Any, ...] = ()
    if config.limit > 0:
        query += " LIMIT ?"
        params = (config.limit,)

    rows = conn.execute(query, params).fetchall()
    inserted = 0
    skipped = 0
    exported_payloads: list[dict[str, Any]] = []

    for row in rows:
        payload, conf = build_rule_payload(dict(row))
        if conf < config.min_confidence and not config.include_low_confidence:
            skipped += 1
            continue

        conn.execute(
            """
            INSERT INTO exercise_rules (
                exrx_id, exercise_key, name, pattern, confidence, rules_json, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(exercise_key) DO UPDATE SET
                exrx_id=excluded.exrx_id,
                name=excluded.name,
                pattern=excluded.pattern,
                confidence=excluded.confidence,
                rules_json=excluded.rules_json,
                source=excluded.source,
                updated_at=excluded.updated_at
            """,
            (
                int(row["id"]),
                str(row["exercise_key"]),
                str(row["name"]),
                str(payload["pattern"]),
                float(conf),
                json.dumps(payload, ensure_ascii=False),
                str(row["source"]),
                _now_iso(),
            ),
        )
        inserted += 1
        exported_payloads.append(payload)

    conn.commit()
    conn.close()

    if config.export_json:
        out = Path(config.export_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(exported_payloads, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "completed",
        "db_path": str(db_path),
        "inserted_or_updated": inserted,
        "skipped_low_confidence": skipped,
        "total_input_rows": len(rows),
        "min_confidence": config.min_confidence,
        "export_json": config.export_json,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build biomechanical rules from scraped exercise data.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)
    parser.add_argument("--min-confidence", type=float, default=0.35)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--export-json", default="")
    parser.add_argument("--include-low-confidence", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = RuleBuildConfig(
        db_path=str(args.db_path),
        min_confidence=float(args.min_confidence),
        limit=int(args.limit),
        export_json=str(args.export_json),
        include_low_confidence=bool(args.include_low_confidence),
    )
    summary = build_rules_from_db(config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

