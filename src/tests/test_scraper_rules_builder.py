from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scraper.exrx_scraper import BeautifulSoup, extract_exercise_links_from_html, parse_exercise_html
from scraper.rules_builder import RuleBuildConfig, build_rules_from_db, infer_movement_pattern


class ExRxScraperParserTests(unittest.TestCase):
    @unittest.skipIf(BeautifulSoup is None, "beautifulsoup4 not installed")
    def test_extract_exercise_links_filters_expected_paths(self) -> None:
        html = """
        <html><body>
          <a href="/WeightExercises/Quadriceps/BBBackSquat">Back Squat</a>
          <a href="/WeightExercises/Back/BBBentOverRow">Barbell Row</a>
          <a href="/Lists/Directory">Directory</a>
          <a href="https://exrx.net/Exercises/Triceps/CablePushdown">Pushdown</a>
        </body></html>
        """
        links = extract_exercise_links_from_html(html)
        self.assertEqual(
            links,
            [
                "https://exrx.net/Exercises/Triceps/CablePushdown",
                "https://exrx.net/WeightExercises/Back/BBBentOverRow",
                "https://exrx.net/WeightExercises/Quadriceps/BBBackSquat",
            ],
        )

    @unittest.skipIf(BeautifulSoup is None, "beautifulsoup4 not installed")
    def test_parse_exercise_html_extracts_core_fields(self) -> None:
        html = """
        <html><head><title>Barbell Back Squat - ExRx.net</title></head>
        <body>
          <h1>Barbell Back Squat</h1>
          <h2>Instructions</h2>
          <ol>
            <li>Descend under control.</li>
            <li>Keep knees tracking over toes.</li>
          </ol>
          <p>Primary Muscles: Quadriceps, Gluteus Maximus</p>
          <p>Secondary Muscles: Adductors, Erector Spinae</p>
          <p>Warning: avoid lumbar flexion under heavy load.</p>
          <a href="/WeightExercises/Quadriceps/DBGobletSquat">Goblet Squat Variation</a>
        </body></html>
        """
        record = parse_exercise_html(
            "https://exrx.net/WeightExercises/Quadriceps/BBBackSquat",
            html,
        )
        self.assertEqual(record.name, "Barbell Back Squat")
        self.assertEqual(record.body_part, "quadriceps")
        self.assertIn("barbell", record.equipment)
        self.assertIn("quadriceps", record.primary_muscles)
        self.assertIn("descend under control.", [v.lower() for v in record.instructions])
        self.assertTrue(any("warning" in note.lower() for note in record.risk_notes))
        self.assertTrue(any("variation" in v.lower() for v in record.variations))


class RulesBuilderTests(unittest.TestCase):
    def test_infer_movement_pattern_classifies_common_names(self) -> None:
        pattern, conf = infer_movement_pattern("Bulgarian Split Squat", "quadriceps", "")
        self.assertEqual(pattern, "lunge")
        self.assertGreaterEqual(conf, 0.80)

        pattern, conf = infer_movement_pattern("Lat Pulldown", "back", "")
        self.assertEqual(pattern, "vertical_pull")
        self.assertGreaterEqual(conf, 0.75)

    def test_build_rules_from_db_generates_rules_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "rules.sqlite"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE exrx_exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    exercise_key TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    body_part TEXT,
                    equipment TEXT,
                    primary_muscles TEXT,
                    secondary_muscles TEXT,
                    instructions TEXT,
                    variations TEXT,
                    risk_notes TEXT,
                    raw_sections TEXT,
                    raw_text TEXT,
                    fetched_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO exrx_exercises (
                    source, exercise_key, url, name, body_part, equipment,
                    primary_muscles, secondary_muscles, instructions, variations,
                    risk_notes, raw_sections, raw_text, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "exrx",
                    "weightexercises__quadriceps__bbbacksquat",
                    "https://exrx.net/WeightExercises/Quadriceps/BBBackSquat",
                    "Barbell Back Squat",
                    "quadriceps",
                    json.dumps(["barbell"]),
                    json.dumps(["quadriceps", "gluteus maximus"]),
                    json.dumps(["adductors"]),
                    json.dumps(["descend controlled", "drive up"]),
                    json.dumps(["goblet squat"]),
                    json.dumps(["Warning: avoid lumbar flexion under heavy load."]),
                    json.dumps({"Instructions": ["descend controlled"]}),
                    "Primary Muscles: quadriceps",
                    "2026-03-03T00:00:00+00:00",
                ),
            )
            conn.commit()
            conn.close()

            summary = build_rules_from_db(
                RuleBuildConfig(
                    db_path=str(db_path),
                    min_confidence=0.20,
                    export_json=str(Path(td) / "rules.json"),
                )
            )

            self.assertEqual(summary["inserted_or_updated"], 1)
            self.assertEqual(summary["skipped_low_confidence"], 0)

            conn = sqlite3.connect(db_path)
            row = conn.execute("SELECT pattern, confidence, rules_json FROM exercise_rules").fetchone()
            conn.close()

            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row[0], "squat")
            self.assertGreaterEqual(float(row[1]), 0.70)
            payload = json.loads(row[2])
            self.assertEqual(payload["name"], "Barbell Back Squat")
            self.assertEqual(payload["pattern"], "squat")
            self.assertIn("knee_valgus_deg_red", payload["biomechanics"]["risk_thresholds"])


if __name__ == "__main__":
    unittest.main()
