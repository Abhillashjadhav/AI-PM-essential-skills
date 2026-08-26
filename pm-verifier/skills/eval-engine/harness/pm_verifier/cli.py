from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .bias import analyze_pairwise_bias
from .calibration import calibrate
from .engine import evaluate_project
from .io import EvidenceError, load_json, write_json
from .reporting import render_markdown


def _decision_exit(decision: str) -> int:
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}.get(decision, 2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pm-verifier",
        description="Validate evidence, grade repeated trials, inspect failures, and gate release.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "run"):
        child = subparsers.add_parser(command)
        child.add_argument("--project", type=Path, default=Path("."))
        child.add_argument("--trials", type=Path)
        child.add_argument("--judgments", type=Path)
        child.add_argument(
            "--out",
            type=Path,
            default=Path("prepared.json" if command == "prepare" else "results.json"),
        )
    report = subparsers.add_parser("report")
    report.add_argument("--results", type=Path, default=Path("results.json"))
    report.add_argument("--out", type=Path, default=Path("report.md"))
    calibration = subparsers.add_parser("calibrate")
    calibration.add_argument("--suite", type=Path, default=Path("suite.json"))
    calibration.add_argument("--goldens", type=Path, required=True)
    calibration.add_argument("--judgments", type=Path, required=True)
    calibration.add_argument("--out", type=Path, default=Path("calibration.json"))
    bias = subparsers.add_parser("bias")
    bias.add_argument("--pairs", type=Path, required=True)
    bias.add_argument("--out", type=Path, default=Path("bias-report.json"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"prepare", "run"}:
        result = evaluate_project(
            args.project,
            trials_path=args.trials,
            judgments_path=args.judgments,
        )
        write_json(args.out, result)
        print(f"{args.command}: {result['decision']} -> {args.out}")
        for error in result["evidence_errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return _decision_exit(result["decision"])
    if args.command == "report":
        try:
            result = load_json(args.results)
        except EvidenceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        args.out.write_text(render_markdown(result), encoding="utf-8")
        print(f"report: {result.get('decision', 'BLOCKED')} -> {args.out}")
        return _decision_exit(result.get("decision", "BLOCKED"))
    if args.command == "calibrate":
        try:
            suite = load_json(args.suite)
        except EvidenceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        result = calibrate(suite, args.goldens, args.judgments)
        write_json(args.out, result)
        print(f"calibrate: {result['status']} -> {args.out}")
        return _decision_exit(result["status"])
    result = analyze_pairwise_bias(args.pairs)
    write_json(args.out, result)
    print(f"bias: {result['status']} -> {args.out}")
    return _decision_exit(result["status"])


if __name__ == "__main__":
    raise SystemExit(main())
