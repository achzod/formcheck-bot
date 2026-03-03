"""CLI entrypoint for offline deterministic evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.gates import GateThresholds, evaluate_gates
from evaluation.runner import evaluate_prediction_files


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate deterministic biomechanics outputs.")
    parser.add_argument("--reference", required=True, help="Path to reference labels (json/jsonl).")
    parser.add_argument("--predictions", required=True, help="Path to predicted outputs (json/jsonl).")
    parser.add_argument("--output", default="", help="Optional output path for JSON results.")
    parser.add_argument(
        "--fail-on-gates",
        action="store_true",
        help="Return exit code 1 when quality gates fail.",
    )
    parser.add_argument("--exercise-f1-min", type=float, default=GateThresholds.exercise_macro_f1_min)
    parser.add_argument("--rep-mae-max", type=float, default=GateThresholds.rep_count_mae_max)
    parser.add_argument("--tempo-mae-max", type=float, default=GateThresholds.tempo_mae_s_max)
    parser.add_argument("--angle-mae-max", type=float, default=GateThresholds.angle_mae_deg_max)
    parser.add_argument("--comp-f1-min", type=float, default=GateThresholds.compensation_f1_min)
    parser.add_argument("--min-samples", type=int, default=GateThresholds.min_paired_samples)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    thresholds = GateThresholds(
        exercise_macro_f1_min=args.exercise_f1_min,
        rep_count_mae_max=args.rep_mae_max,
        tempo_mae_s_max=args.tempo_mae_max,
        angle_mae_deg_max=args.angle_mae_max,
        compensation_f1_min=args.comp_f1_min,
        min_paired_samples=args.min_samples,
    )

    summary = evaluate_prediction_files(args.reference, args.predictions)
    gates = evaluate_gates(
        summary["metrics"],
        thresholds=thresholds,
        paired_samples=int(summary.get("paired_samples", 0)),
    )
    payload = {"summary": summary, "gates": gates}

    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    print(rendered)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")

    if args.fail_on_gates and not gates["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

