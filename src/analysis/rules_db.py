"""Resolution de noms d'exercices via la base SQLite des regles scrapees."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuleEntry:
    name: str
    exercise_key: str
    pattern: str
    confidence: float
    aliases: tuple[str, ...]


def normalize_exercise_name(name: str | None) -> str:
    value = (name or "").strip().lower()
    value = re.sub(r"[\-_]+", " ", value)
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _token_overlap(a: str, b: str) -> float:
    ta = set(a.split())
    tb = set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(max(len(ta), len(tb)))


def _loads_list(raw: Any) -> list[str]:
    if raw in (None, ""):
        return []
    try:
        value = json.loads(str(raw))
    except Exception:
        return []
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if str(v).strip()]


def _pattern_to_supported(pattern: str, candidate_name: str) -> str:
    low = normalize_exercise_name(candidate_name)
    pattern = (pattern or "").strip().lower()

    if pattern == "squat":
        if "goblet" in low:
            return "goblet_squat"
        if "front squat" in low:
            return "front_squat"
        if "hack squat" in low:
            return "hack_squat"
        return "squat"
    if pattern == "lunge":
        if "walking" in low:
            return "walking_lunge"
        if "bulgarian" in low or "split squat" in low:
            return "bulgarian_split_squat"
        if "step up" in low:
            return "step_up"
        return "lunge"
    if pattern == "hinge":
        if "hip thrust" in low:
            return "hip_thrust"
        if "good morning" in low:
            return "good_morning"
        if "romanian" in low or "rdl" in low:
            return "rdl"
        if "sumo" in low:
            return "sumo_deadlift"
        if "single leg" in low and "rdl" in low:
            return "single_leg_rdl"
        return "deadlift"
    if pattern == "horizontal_press":
        if "incline" in low:
            return "incline_bench"
        if "push up" in low or "push-up" in low:
            return "push_up"
        if "dip" in low:
            return "dip"
        return "bench_press"
    if pattern == "vertical_press":
        if "dumbbell" in low and "press" in low:
            return "dumbbell_ohp"
        if "arnold press" in low:
            return "arnold_press"
        return "ohp"
    if pattern == "row":
        if "cable" in low:
            return "cable_row"
        if "dumbbell" in low:
            return "dumbbell_row"
        if "t bar" in low or "t-bar" in low:
            return "tbar_row"
        return "barbell_row"
    if pattern == "vertical_pull":
        if "pull up" in low or "pull-up" in low or "chin up" in low or "chin-up" in low:
            return "pullup"
        if "pullover" in low:
            return "cable_pullover"
        return "lat_pulldown"
    if pattern == "arm_isolation":
        if "tricep" in low or "triceps" in low or "skull crusher" in low:
            return "tricep_extension"
        if "cable curl" in low:
            return "cable_curl"
        if "hammer curl" in low:
            return "hammer_curl"
        return "curl"
    if pattern == "raise":
        if "front raise" in low:
            return "front_raise"
        if "face pull" in low:
            return "face_pull"
        return "lateral_raise"
    return ""


def _rules_db_path(path_override: str | None = None) -> Path:
    if path_override:
        return Path(path_override)
    env_path = os.getenv("RULES_DB_PATH", "").strip()
    if env_path:
        return Path(env_path)
    try:
        from app.config import settings  # Lazy import: optional in local test env.

        configured = str(getattr(settings, "rules_db_path", "") or "").strip()
        if configured:
            return Path(configured)
    except Exception:
        pass
    return Path("database/rules_db.sqlite")


@lru_cache(maxsize=4)
def _load_entries_cached(db_path: str, mtime_ns: int) -> tuple[RuleEntry, ...]:
    path = Path(db_path)
    if not path.exists():
        return tuple()

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        has_rules = (
            conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='exercise_rules'"
            ).fetchone()
            is not None
        )
        if not has_rules:
            return tuple()

        rows = conn.execute(
            """
            SELECT exercise_key, name, pattern, confidence, rules_json
            FROM exercise_rules
            """
        ).fetchall()
    finally:
        conn.close()

    entries: list[RuleEntry] = []
    for row in rows:
        rules_json = row["rules_json"]
        variations: list[str] = []
        try:
            payload = json.loads(str(rules_json))
            variations = _loads_list(payload.get("variations"))
        except Exception:
            variations = []
        aliases = [str(row["name"]), str(row["exercise_key"]).replace("__", " ")]
        aliases.extend(variations[:8])
        norm_aliases = tuple(
            sorted(
                {
                    normalize_exercise_name(alias)
                    for alias in aliases
                    if normalize_exercise_name(alias)
                }
            )
        )
        entries.append(
            RuleEntry(
                name=str(row["name"]),
                exercise_key=str(row["exercise_key"]),
                pattern=str(row["pattern"] or ""),
                confidence=float(row["confidence"] or 0.0),
                aliases=norm_aliases,
            )
        )
    return tuple(entries)


def _load_entries(path_override: str | None = None) -> tuple[RuleEntry, ...]:
    path = _rules_db_path(path_override)
    if not path.exists():
        return tuple()
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        return tuple()
    return _load_entries_cached(str(path), int(mtime_ns))


def resolve_to_supported_exercise(
    raw_name: str | None,
    *,
    min_score: float = 0.62,
    path_override: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Mappe un nom d'exercice libre vers un exercice supporte du moteur.

    Retourne `(exercise_name, meta)` avec `exercise_name=""` si non resolu.
    """
    query = normalize_exercise_name(raw_name)
    if not query:
        return "", {"reason": "empty_query"}

    entries = _load_entries(path_override)
    if not entries:
        return "", {"reason": "no_rules_db"}

    best_entry: RuleEntry | None = None
    best_alias = ""
    best_score = 0.0

    for entry in entries:
        for alias in entry.aliases:
            if not alias:
                continue
            if alias == query:
                best_entry = entry
                best_alias = alias
                best_score = 1.0
                break
            ratio = SequenceMatcher(None, query, alias).ratio()
            overlap = _token_overlap(query, alias)
            score = (ratio * 0.72) + (overlap * 0.28)
            if score > best_score:
                best_entry = entry
                best_alias = alias
                best_score = score
        if best_score >= 1.0:
            break

    if best_entry is None or best_score < min_score:
        return "", {
            "reason": "low_similarity",
            "score": round(best_score, 3),
            "query": query,
        }

    mapped = _pattern_to_supported(best_entry.pattern, best_entry.name)
    if not mapped:
        return "", {
            "reason": "no_pattern_mapping",
            "score": round(best_score, 3),
            "pattern": best_entry.pattern,
            "matched": best_entry.name,
        }

    return mapped, {
        "reason": "resolved_from_rules_db",
        "score": round(best_score, 3),
        "matched": best_entry.name,
        "matched_alias": best_alias,
        "pattern": best_entry.pattern,
        "rule_confidence": round(best_entry.confidence, 3),
    }
