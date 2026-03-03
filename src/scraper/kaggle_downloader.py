"""Téléchargement robuste de datasets Kaggle pour enrichir la base exercices.

Fonctionnement:
- essaie plusieurs slugs par dataset cible
- télécharge via CLI Kaggle (kaggle datasets download ...)
- unzip optionnel
- journalise les runs dans SQLite (table `kaggle_download_runs`)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("scraper.kaggle")

DEFAULT_DB_PATH = "database/rules_db.sqlite"
DEFAULT_OUTPUT_DIR = "data/kaggle"


@dataclass(frozen=True)
class DatasetTarget:
    name: str
    slug_variants: tuple[str, ...]
    notes: str = ""


DEFAULT_TARGETS: tuple[DatasetTarget, ...] = (
    DatasetTarget(
        name="Gym Exercises Dataset",
        slug_variants=(
            "niharika41298/gym-exercise-data",
            "philosopher0808/gym-exercises-dataset",
            "thedevastator/fitness-exercises-with-animated-gifs",
        ),
        notes="Base d'exercices pour nomenclature et variations.",
    ),
    DatasetTarget(
        name="Biomechanical Injury Prevention",
        slug_variants=(
            "mohamedhanyyy/chest-press-biomechanics",
            "ankit30496/human-motion-analysis-and-activity-recognition",
            "uciml/human-activity-recognition-with-smartphones",
        ),
        notes="Fallback pragmatique si dataset exact indisponible.",
    ),
    DatasetTarget(
        name="Workout/Exercise Video Dataset",
        slug_variants=(
            "hasyimabrar/workoutfitness-video",
            "edoardoba/fitness-exercises-dataset",
            "stefanoleone992/fitness-videos",
        ),
        notes="Clips pour tests détection/reps à large couverture.",
    ),
)


@dataclass
class DownloadConfig:
    db_path: str = DEFAULT_DB_PATH
    output_dir: str = DEFAULT_OUTPUT_DIR
    unzip: bool = True
    force: bool = False
    only_targets: tuple[str, ...] = ()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kaggle_download_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                dataset_name TEXT NOT NULL,
                chosen_slug TEXT,
                tried_slugs TEXT NOT NULL,
                status TEXT NOT NULL,
                output_path TEXT,
                notes TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _insert_run(db_path: Path, dataset_name: str, tried_slugs: list[str]) -> int:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO kaggle_download_runs
            (started_at, dataset_name, tried_slugs, status)
            VALUES (?, ?, ?, ?)
            """,
            (_now_iso(), dataset_name, json.dumps(tried_slugs, ensure_ascii=False), "running"),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def _finish_run(
    db_path: Path,
    run_id: int,
    status: str,
    chosen_slug: str,
    output_path: str,
    notes: str,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            UPDATE kaggle_download_runs
            SET ended_at=?, status=?, chosen_slug=?, output_path=?, notes=?
            WHERE id=?
            """,
            (_now_iso(), status, chosen_slug, output_path, notes[:3000], run_id),
        )
        conn.commit()
    finally:
        conn.close()


def _has_kaggle_cli() -> bool:
    return shutil.which("kaggle") is not None


def _has_kaggle_auth() -> bool:
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return True
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    return kaggle_json.exists()


def _run_kaggle_download(slug: str, output_dir: Path, unzip: bool) -> tuple[bool, str]:
    cmd = ["kaggle", "datasets", "download", "-d", slug, "-p", str(output_dir)]
    if unzip:
        cmd.append("--unzip")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def _target_selected(target: DatasetTarget, only_targets: tuple[str, ...]) -> bool:
    if not only_targets:
        return True
    key = target.name.lower()
    return any(token.lower() in key for token in only_targets)


def _dataset_dir_name(target: DatasetTarget) -> str:
    low = target.name.lower().strip()
    clean = "".join(ch if ch.isalnum() else "_" for ch in low)
    return "_".join(filter(None, clean.split("_")))


def download_targets(config: DownloadConfig) -> dict[str, Any]:
    db_path = Path(config.db_path)
    out_root = Path(config.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    _ensure_db(db_path)

    if not _has_kaggle_cli():
        raise RuntimeError("Kaggle CLI introuvable. Installez: pip install kaggle")
    if not _has_kaggle_auth():
        raise RuntimeError(
            "Authentification Kaggle absente. Configurez KAGGLE_USERNAME/KAGGLE_KEY ou ~/.kaggle/kaggle.json"
        )

    summary_rows: list[dict[str, Any]] = []
    for target in DEFAULT_TARGETS:
        if not _target_selected(target, config.only_targets):
            continue
        dataset_dir = out_root / _dataset_dir_name(target)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        attempted: list[str] = list(target.slug_variants)
        run_id = _insert_run(db_path, target.name, attempted)
        logger.info("Downloading target: %s", target.name)

        success = False
        chosen_slug = ""
        last_output = ""
        for slug in target.slug_variants:
            ok, out = _run_kaggle_download(slug, dataset_dir, unzip=config.unzip)
            last_output = out
            if ok:
                success = True
                chosen_slug = slug
                logger.info("Success: %s via %s", target.name, slug)
                break
            logger.warning("Failed slug %s for %s", slug, target.name)

        status = "completed" if success else "failed"
        _finish_run(
            db_path,
            run_id,
            status=status,
            chosen_slug=chosen_slug,
            output_path=str(dataset_dir),
            notes=last_output,
        )
        summary_rows.append(
            {
                "target": target.name,
                "status": status,
                "chosen_slug": chosen_slug,
                "output_dir": str(dataset_dir),
                "tried": list(target.slug_variants),
            }
        )

    return {
        "status": "completed",
        "db_path": str(db_path),
        "output_dir": str(out_root),
        "results": summary_rows,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download curated Kaggle datasets for FormCheck research mode.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-unzip", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Filtrer les targets par sous-chaîne de nom (ex: --only gym injury).",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = DownloadConfig(
        db_path=str(args.db_path),
        output_dir=str(args.output_dir),
        unzip=not bool(args.no_unzip),
        force=bool(args.force),
        only_targets=tuple(str(v) for v in args.only),
    )
    summary = download_targets(config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

