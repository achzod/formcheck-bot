"""Scraper ExRx robuste pour remplir la base d'exercices.

Objectif:
- crawler le directory ExRx
- parser les pages exo (nom, muscles, instructions, variantes, risques)
- sauvegarder en SQLite pour usage par le rules builder

Le scraper est "poli":
- User-Agent explicite
- delai configurable (2s par defaut)
- timeout/retry
- fallback Selenium si Cloudflare bloque les requetes HTTP classiques
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency at runtime
    BeautifulSoup = None  # type: ignore[assignment]

logger = logging.getLogger("scraper.exrx")

DEFAULT_EXRX_DIRECTORY = "https://exrx.net/Lists/Directory"
DEFAULT_STRENGTHLOG_DIRECTORY = "https://www.strengthlog.com/exercise-directory/"
DEFAULT_DB_PATH = "database/rules_db.sqlite"
DEFAULT_DELAY_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0

_DEFAULT_HEADERS = {
    "User-Agent": (
        "FormCheckBotResearch/2026.03 (+https://formcheck-bot.onrender.com; "
        "contact: support@formcheck-bot.onrender.com)"
    ),
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}

_CLOUDFLARE_MARKERS = (
    "Just a moment...",
    "cf-browser-verification",
    "Attention Required! | Cloudflare",
    "challenge-platform",
)

_MUSCLE_SPLIT_PATTERN = re.compile(
    r"(?:primary|target|secondary|synergist|stabilizer)\s*(?:muscles?)?\s*:?\s*(.+)",
    re.IGNORECASE,
)

_STRENGTHLOG_STOP_TOKENS = {
    "program",
    "programs",
    "strength standards",
    "standards",
    "how to",
    "vs",
    "alternatives",
    "variations",
    "articles",
    "about",
    "support",
    "podcast",
    "shop",
    "workout",
    "muscles",
}

_STRENGTHLOG_STOP_SLUG_TOKENS = (
    "how-to-",
    "-vs-",
    "-program",
    "-programs",
    "strength-standards",
    "accessory-exercises",
    "best-",
    "-workout",
    "-muscles-worked",
    "training-",
)

_EXERCISE_HINT_TOKENS = (
    "press",
    "squat",
    "deadlift",
    "row",
    "curl",
    "raise",
    "pulldown",
    "pull up",
    "chin up",
    "lunge",
    "dip",
    "extension",
    "fly",
    "thrust",
    "bridge",
    "push-up",
    "push up",
    "crunch",
    "shrug",
    "calf",
    "adductor",
    "abductor",
)


@dataclass
class ScrapeConfig:
    start_url: str = DEFAULT_EXRX_DIRECTORY
    db_path: str = DEFAULT_DB_PATH
    output_jsonl: str = ""
    delay_seconds: float = DEFAULT_DELAY_SECONDS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_exercises: int = 0
    use_selenium_fallback: bool = True
    selenium_wait_seconds: float = 8.0


@dataclass
class ExerciseRecord:
    source: str
    exercise_key: str
    url: str
    name: str
    body_part: str
    equipment: list[str]
    primary_muscles: list[str]
    secondary_muscles: list[str]
    instructions: list[str]
    variations: list[str]
    risk_notes: list[str]
    raw_sections: dict[str, list[str]]
    raw_text: str

    def to_row(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "exercise_key": self.exercise_key,
            "url": self.url,
            "name": self.name,
            "body_part": self.body_part,
            "equipment": json.dumps(self.equipment, ensure_ascii=False),
            "primary_muscles": json.dumps(self.primary_muscles, ensure_ascii=False),
            "secondary_muscles": json.dumps(self.secondary_muscles, ensure_ascii=False),
            "instructions": json.dumps(self.instructions, ensure_ascii=False),
            "variations": json.dumps(self.variations, ensure_ascii=False),
            "risk_notes": json.dumps(self.risk_notes, ensure_ascii=False),
            "raw_sections": json.dumps(self.raw_sections, ensure_ascii=False),
            "raw_text": self.raw_text,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_cloudflare_block(response: httpx.Response) -> bool:
    text = response.text[:8000]
    marker_hit = any(m in text for m in _CLOUDFLARE_MARKERS)
    if marker_hit:
        return True
    return response.status_code in {403, 429, 503}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return "unknown"
    slug = path.replace("/", "__")
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", slug)
    return slug.strip("_").lower()


def _body_part_from_url(url: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    if len(parts) >= 3 and parts[0].lower() == "weightexercises":
        return parts[1].lower()
    if len(parts) >= 2 and parts[0].lower() == "exercises":
        return parts[1].lower()
    return "unknown"


def _extract_sections(soup: BeautifulSoup) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    for heading in headings:
        title = _normalize_text(heading.get_text(" ", strip=True))
        if not title:
            continue
        bucket: list[str] = []
        node = heading.next_sibling
        while node is not None:
            name = getattr(node, "name", "")
            if name in {"h1", "h2", "h3", "h4"}:
                break
            if name in {"ol", "ul"}:
                for li in getattr(node, "find_all", lambda *a, **k: [])("li"):
                    li_text = _normalize_text(li.get_text(" ", strip=True))
                    if li_text:
                        bucket.append(li_text)
            else:
                text = _normalize_text(getattr(node, "get_text", lambda *a, **k: "")(" ", strip=True))
                if text:
                    bucket.append(text)
            node = node.next_sibling
        if bucket:
            sections[title] = bucket
    return sections


def _extract_muscles(raw_text: str) -> tuple[list[str], list[str]]:
    primary: list[str] = []
    secondary: list[str] = []
    lines = [_normalize_text(line) for line in raw_text.splitlines() if _normalize_text(line)]
    for line in lines:
        match = _MUSCLE_SPLIT_PATTERN.search(line)
        if not match:
            continue
        rhs = re.sub(r"[.;|]", ",", match.group(1))
        values = [v.strip(" -").lower() for v in rhs.split(",") if v.strip()]
        line_lower = line.lower()
        if "primary" in line_lower or "target" in line_lower:
            primary.extend(values)
        else:
            secondary.extend(values)
    return sorted(set(primary)), sorted(set(secondary))


def _extract_instructions(soup: BeautifulSoup, sections: dict[str, list[str]]) -> list[str]:
    instructions: list[str] = []
    for title, rows in sections.items():
        t = title.lower()
        if "instruction" in t or "execution" in t or "technique" in t:
            instructions.extend(rows[:12])

    if not instructions:
        for ol in soup.find_all(["ol", "ul"]):
            li_texts = [_normalize_text(li.get_text(" ", strip=True)) for li in ol.find_all("li")]
            li_texts = [t for t in li_texts if len(t) > 8]
            if len(li_texts) >= 2:
                instructions.extend(li_texts[:12])
                break

    return list(dict.fromkeys(instructions))[:20]


def _extract_risk_notes(raw_text: str) -> list[str]:
    keywords = (
        "risk",
        "injury",
        "contraindication",
        "danger",
        "warning",
        "avoid",
        "caution",
        "douleur",
        "blessure",
    )
    notes: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", raw_text)
    for sentence in sentences:
        normalized = _normalize_text(sentence)
        if not normalized:
            continue
        low = normalized.lower()
        if any(k in low for k in keywords):
            notes.append(normalized)
    return list(dict.fromkeys(notes))[:20]


def _extract_variations(soup: BeautifulSoup) -> list[str]:
    values: list[str] = []
    var_keywords = ("variation", "alternate", "alternative", "barbell", "dumbbell", "machine", "cable", "smith")
    for anchor in soup.find_all("a", href=True):
        text = _normalize_text(anchor.get_text(" ", strip=True))
        if not text or len(text) < 4:
            continue
        low = text.lower()
        if any(k in low for k in var_keywords):
            values.append(text)
    return list(dict.fromkeys(values))[:30]


def _guess_equipment(name: str, raw_text: str) -> list[str]:
    low = "{} {}".format(name.lower(), raw_text.lower())
    mapping = {
        "barbell": ("barbell", "bb "),
        "dumbbell": ("dumbbell", "db "),
        "cable": ("cable",),
        "machine": ("machine", "smith"),
        "bodyweight": ("bodyweight", "pull-up", "push-up", "dip"),
        "kettlebell": ("kettlebell", "kb "),
    }
    out: list[str] = []
    for equipment, markers in mapping.items():
        if any(marker in low for marker in markers):
            out.append(equipment)
    return out or ["unknown"]


def extract_exercise_links_from_html(html: str, base_url: str = "https://exrx.net") -> list[str]:
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required for HTML parsing")
    soup = BeautifulSoup(html, "lxml")
    links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != "exrx.net":
            continue
        path = parsed.path
        if "/WeightExercises/" not in path and "/Exercises/" not in path:
            continue
        if path.endswith("/") or path.count("/") < 3:
            continue
        links.add("https://exrx.net{}".format(path))
    return sorted(links)


def parse_exercise_html(url: str, html: str, *, source: str = "exrx") -> ExerciseRecord:
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required for HTML parsing")
    soup = BeautifulSoup(html, "lxml")
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = _normalize_text(h1.get_text(" ", strip=True))
    if not title and soup.title:
        title = _normalize_text(soup.title.get_text(" ", strip=True)).replace(" - ExRx.net", "")
    if not title:
        title = _slug_from_url(url).replace("__", " ")

    raw_text = _normalize_text(soup.get_text("\n", strip=True))
    sections = _extract_sections(soup)
    primary, secondary = _extract_muscles(raw_text)
    instructions = _extract_instructions(soup, sections)
    variations = _extract_variations(soup)
    risk_notes = _extract_risk_notes(raw_text)
    equipment = _guess_equipment(title, raw_text)

    return ExerciseRecord(
        source=source,
        exercise_key=_slug_from_url(url),
        url=url,
        name=title,
        body_part=_body_part_from_url(url),
        equipment=equipment,
        primary_muscles=primary,
        secondary_muscles=secondary,
        instructions=instructions,
        variations=variations,
        risk_notes=risk_notes,
        raw_sections=sections,
        raw_text=raw_text[:120000],
    )


class ExRxScraper:
    def __init__(self, config: ScrapeConfig):
        self.config = config
        self.client = httpx.Client(
            headers=_DEFAULT_HEADERS,
            timeout=config.timeout_seconds,
            follow_redirects=True,
        )
        self.db_path = Path(config.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def close(self) -> None:
        self.client.close()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS exrx_exercises (
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
                CREATE TABLE IF NOT EXISTS scrape_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    pages_discovered INTEGER NOT NULL DEFAULT 0,
                    pages_scraped INTEGER NOT NULL DEFAULT 0,
                    errors INTEGER NOT NULL DEFAULT 0,
                    notes TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _fetch_html(self, url: str) -> str:
        response = self.client.get(url)
        if response.status_code < 400 and not _is_cloudflare_block(response):
            return response.text

        if self.config.use_selenium_fallback:
            html = self._fetch_html_selenium(url)
            if html:
                return html

        response.raise_for_status()
        return response.text

    def _fetch_html_selenium(self, url: str) -> str:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
        except Exception as exc:
            logger.warning("Selenium indisponible (%s) — fallback impossible pour %s", exc, url)
            return ""

        driver = None
        try:
            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1400,1200")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
            driver.get(url)
            time.sleep(self.config.selenium_wait_seconds)
            return driver.page_source or ""
        except Exception as exc:
            logger.warning("Selenium fetch a echoue pour %s: %s", url, exc)
            return ""
        finally:
            if driver is not None:
                driver.quit()

    def _upsert_exercise(self, record: ExerciseRecord) -> None:
        row = record.to_row()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO exrx_exercises (
                    source, exercise_key, url, name, body_part, equipment,
                    primary_muscles, secondary_muscles, instructions, variations,
                    risk_notes, raw_sections, raw_text, fetched_at
                ) VALUES (
                    :source, :exercise_key, :url, :name, :body_part, :equipment,
                    :primary_muscles, :secondary_muscles, :instructions, :variations,
                    :risk_notes, :raw_sections, :raw_text, :fetched_at
                )
                ON CONFLICT(exercise_key) DO UPDATE SET
                    source=excluded.source,
                    url=excluded.url,
                    name=excluded.name,
                    body_part=excluded.body_part,
                    equipment=excluded.equipment,
                    primary_muscles=excluded.primary_muscles,
                    secondary_muscles=excluded.secondary_muscles,
                    instructions=excluded.instructions,
                    variations=excluded.variations,
                    risk_notes=excluded.risk_notes,
                    raw_sections=excluded.raw_sections,
                    raw_text=excluded.raw_text,
                    fetched_at=excluded.fetched_at
                """,
                {**row, "fetched_at": _now_iso()},
            )
            conn.commit()
        finally:
            conn.close()

    def run(self) -> dict[str, Any]:
        started_at = _now_iso()
        run_id = self._create_run("running", started_at)
        discovered = 0
        scraped = 0
        errors = 0

        try:
            links_with_source: list[tuple[str, str]] = []
            try:
                directory_html = self._fetch_html(self.config.start_url)
                exrx_links = extract_exercise_links_from_html(directory_html, base_url="https://exrx.net")
                if exrx_links:
                    links_with_source = [("exrx", link) for link in exrx_links]
                    logger.info("ExRx links discovered: %d", len(exrx_links))
                else:
                    logger.warning("ExRx discovery returned 0 exercise links. Trying StrengthLog fallback.")
                    strengthlog_links = self._discover_strengthlog_links()
                    links_with_source = [("strengthlog", link) for link in strengthlog_links]
            except Exception as exc:
                logger.warning("ExRx discovery failed (%s). Trying StrengthLog fallback.", exc)
                strengthlog_links = self._discover_strengthlog_links()
                links_with_source = [("strengthlog", link) for link in strengthlog_links]

            discovered = len(links_with_source)
            if self.config.max_exercises > 0:
                links_with_source = links_with_source[: self.config.max_exercises]

            jsonl_path = Path(self.config.output_jsonl) if self.config.output_jsonl else None
            if jsonl_path:
                jsonl_path.parent.mkdir(parents=True, exist_ok=True)

            for idx, (source_name, url) in enumerate(links_with_source, start=1):
                try:
                    html = self._fetch_html(url)
                    record = parse_exercise_html(url, html, source=source_name)
                    self._upsert_exercise(record)
                    scraped += 1
                    if jsonl_path:
                        with jsonl_path.open("a", encoding="utf-8") as fh:
                            fh.write(json.dumps(record.to_row(), ensure_ascii=False) + "\n")
                    logger.info("[%d/%d] scraped (%s): %s", idx, len(links_with_source), source_name, record.name)
                except Exception as exc:
                    errors += 1
                    logger.warning("[%d/%d] failed: %s (%s)", idx, len(links_with_source), url, exc)
                time.sleep(max(0.0, self.config.delay_seconds))

            self._finish_run(run_id, "completed", discovered, scraped, errors, notes="")
            return {
                "status": "completed",
                "run_id": run_id,
                "discovered": discovered,
                "scraped": scraped,
                "errors": errors,
                "db_path": str(self.db_path),
            }
        except Exception as exc:
            self._finish_run(run_id, "failed", discovered, scraped, errors + 1, notes=str(exc))
            raise
        finally:
            self.close()

    def _discover_strengthlog_links(self) -> list[str]:
        html = self._fetch_html(DEFAULT_STRENGTHLOG_DIRECTORY)
        soup = BeautifulSoup(html, "lxml")
        links: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            text = _normalize_text(anchor.get_text(" ", strip=True))
            if not href or not text:
                continue
            url = urljoin(DEFAULT_STRENGTHLOG_DIRECTORY, href)
            parsed = urlparse(url)
            if parsed.netloc != "www.strengthlog.com":
                continue
            path = parsed.path.strip("/")
            if not path or "/" in path:
                continue

            low_text = text.lower()
            low_slug = path.replace("-", " ").lower()
            if any(token in low_text for token in _STRENGTHLOG_STOP_TOKENS):
                continue
            if any(token in path.lower() for token in _STRENGTHLOG_STOP_SLUG_TOKENS):
                continue
            if len(low_text) > 60:
                continue

            has_exercise_hint = any(token in low_text for token in _EXERCISE_HINT_TOKENS) or any(
                token in low_slug for token in _EXERCISE_HINT_TOKENS
            )
            if not has_exercise_hint:
                continue
            links.add("https://www.strengthlog.com/{}/".format(path))
        out = sorted(links)
        logger.info("StrengthLog fallback links discovered: %d", len(out))
        return out

    def _create_run(self, status: str, started_at: str) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                """
                INSERT INTO scrape_runs (source, started_at, status)
                VALUES (?, ?, ?)
                """,
                ("exrx", started_at, status),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def _finish_run(
        self,
        run_id: int,
        status: str,
        discovered: int,
        scraped: int,
        errors: int,
        notes: str,
    ) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE scrape_runs
                SET ended_at=?, status=?, pages_discovered=?, pages_scraped=?, errors=?, notes=?
                WHERE id=?
                """,
                (_now_iso(), status, discovered, scraped, errors, notes[:2000], run_id),
            )
            conn.commit()
        finally:
            conn.close()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape ExRx directory into SQLite.")
    parser.add_argument("--start-url", default=DEFAULT_EXRX_DIRECTORY)
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)
    parser.add_argument("--output-jsonl", default="")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-exercises", type=int, default=0)
    parser.add_argument("--disable-selenium-fallback", action="store_true")
    parser.add_argument("--selenium-wait", type=float, default=8.0)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    cfg = ScrapeConfig(
        start_url=str(args.start_url),
        db_path=str(args.db_path),
        output_jsonl=str(args.output_jsonl),
        delay_seconds=float(args.delay),
        timeout_seconds=float(args.timeout),
        max_exercises=int(args.max_exercises),
        use_selenium_fallback=not bool(args.disable_selenium_fallback),
        selenium_wait_seconds=float(args.selenium_wait),
    )
    scraper = ExRxScraper(cfg)
    summary = scraper.run()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
