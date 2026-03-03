from __future__ import annotations

import sys
import types
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Keep pipeline imports testable without OpenCV in local env.
if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.ModuleType("cv2")

from analysis.pipeline import _map_model_exercise_name
from analysis.rules_db import resolve_to_supported_exercise
from scraper.kaggle_downloader import DownloadConfig, download_targets


def _init_rules_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE exercise_rules (
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
    conn.execute(
        """
        INSERT INTO exercise_rules
        (exrx_id, exercise_key, name, pattern, confidence, rules_json, source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "strengthlog__arnold_press",
            "Arnold Press",
            "vertical_press",
            0.86,
            '{"variations": ["Dumbbell Arnold Press"]}',
            "strengthlog",
            "2026-03-03T00:00:00+00:00",
        ),
    )
    conn.commit()
    conn.close()


class RulesDbResolutionTests(unittest.TestCase):
    def test_resolve_to_supported_exercise_from_custom_db(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "rules.sqlite"
            _init_rules_db(db_path)
            mapped, meta = resolve_to_supported_exercise(
                "Dumbbell Arnold Press",
                path_override=str(db_path),
            )
            self.assertEqual(mapped, "arnold_press")
            self.assertEqual(meta["reason"], "resolved_from_rules_db")
            self.assertGreaterEqual(float(meta["score"]), 0.60)

    def test_pipeline_mapping_uses_rules_db_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "rules.sqlite"
            _init_rules_db(db_path)
            old_path = os.environ.get("RULES_DB_PATH", "")
            try:
                os.environ["RULES_DB_PATH"] = str(db_path)
                mapped = _map_model_exercise_name("Dumbbell Arnold Press")
                self.assertEqual(mapped, "arnold_press")
            finally:
                if old_path:
                    os.environ["RULES_DB_PATH"] = old_path
                else:
                    os.environ.pop("RULES_DB_PATH", None)


class KaggleDownloaderTests(unittest.TestCase):
    @patch("scraper.kaggle_downloader._has_kaggle_cli", return_value=True)
    @patch("scraper.kaggle_downloader._has_kaggle_auth", return_value=True)
    @patch("scraper.kaggle_downloader._run_kaggle_download")
    def test_download_targets_tries_variants_and_logs(self, run_mock, _auth_mock, _cli_mock) -> None:
        def _fake_run(slug: str, _out, unzip=True):
            if slug.endswith("gym-exercise-data"):
                return False, "not found"
            return True, "ok"

        run_mock.side_effect = _fake_run

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "rules.sqlite"
            out_dir = Path(td) / "kaggle_data"
            summary = download_targets(
                DownloadConfig(
                    db_path=str(db_path),
                    output_dir=str(out_dir),
                    only_targets=("gym",),
                )
            )

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(len(summary["results"]), 1)
            row = summary["results"][0]
            self.assertEqual(row["target"], "Gym Exercises Dataset")
            self.assertEqual(row["status"], "completed")
            self.assertNotEqual(row["chosen_slug"], "")

            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM kaggle_download_runs").fetchone()[0]
            status = conn.execute("SELECT status FROM kaggle_download_runs").fetchone()[0]
            conn.close()
            self.assertEqual(count, 1)
            self.assertEqual(status, "completed")

    @patch("scraper.kaggle_downloader._has_kaggle_cli", return_value=False)
    def test_download_targets_fails_when_cli_missing(self, _cli_mock) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "rules.sqlite"
            with self.assertRaises(RuntimeError):
                download_targets(DownloadConfig(db_path=str(db_path), output_dir=str(Path(td) / "out")))


if __name__ == "__main__":
    unittest.main()
