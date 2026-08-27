from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .adapter import execute_trials
from .bias import analyze_pairwise_bias
from .calibration import calibrate
from .engine import evaluate_project
from .faults import apply_faults
from .io import EvidenceError, load_json, load_jsonl, write_json, write_jsonl
from .reporting import render_inspection, render_markdown


def _decision_exit(decision: str) -> int:
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}.get(decision, 2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pm-verifier",
        description=(
            "AI Evals for PMs: grade outcomes, trajectories, systems, and "
            "promised memory across repeated trials, then gate release."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "validate", "run"):
        child = subparsers.add_parser(command)
        child.add_argument("--project", type=Path, default=Path("."))
        child.add_argument("--trials", type=Path)
        child.add_argument("--judgments", type=Path)
        child.add_argument(
            "--out",
            type=Path,
            default=Path(
                "prepared.json"
                if command == "prepare"
                else "validation.json"
                if command == "validate"
                else "results.json"
            ),
        )
    execute = subparsers.add_parser("execute")
    execute.add_argument("--project", type=Path, default=Path("."))
    execute.add_argument("--trials-out", type=Path, default=Path("trials.executed.jsonl"))
    execute.add_argument("--results-out", type=Path, default=Path("results.json"))
    execute.add_argument("--judgments", type=Path)
    execute.add_argument("--timeout-seconds", type=float, default=60)
    execute.add_argument("adapter_command", nargs=argparse.REMAINDER)
    report = subparsers.add_parser("report")
    report.add_argument("--results", type=Path, default=Path("results.json"))
    report.add_argument("--out", type=Path, default=Path("report.md"))
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--results", type=Path, default=Path("results.json"))
    inspect.add_argument("--trials", type=Path, default=Path("trials.jsonl"))
    inspect.add_argument("--case")
    inspect.add_argument("--trial")
    inspect.add_argument("--out", type=Path)
    fault = subparsers.add_parser("fault")
    fault.add_argument("--project", type=Path, default=Path("."))
    fault.add_argument("--trials", type=Path, default=Path("trials.jsonl"))
    fault.add_argument("--specs", type=Path, default=Path("faults/specs.json"))
    fault.add_argument("--name", required=True)
    fault.add_argument("--out", type=Path, default=Path("trials.faulted.jsonl"))
    calibration = subparsers.add_parser("calibrate")
    calibration.add_argument("--suite", type=Path, default=Path("suite.json"))
    calibration.add_argument("--goldens", type=Path, required=True)
    calibration.add_argument("--judgments", type=Path, required=True)
    calibration.add_argument("--out", type=Path, default=Path("calibration.json"))
    bias = subparsers.add_parser("bias")
    bias.add_argument("--pairs", type=Path, required=True)
    bias.add_argument("--out", type=Path, default=Path("bias-report.json"))
    return parser


def _project_path(project: Path, selected: Path) -> Path:
    return selected if selected.is_absolute() else project / selected


def _contract_lineage_input_paths(
    project_root: Path, run: dict[str, object]
) -> set[Path]:
    lineage = run.get("contract_lineage")
    if lineage is None:
        return set()
    if not isinstance(lineage, list):
        raise EvidenceError("run.contract_lineage must be a list")

    protected: set[Path] = set()
    for index, artifact in enumerate(lineage):
        label = f"run.contract_lineage[{index}]"
        if not isinstance(artifact, dict):
            raise EvidenceError(f"{label} must be an object")
        declared_path = artifact.get("path")
        if not isinstance(declared_path, str) or not declared_path.strip():
            raise EvidenceError(
                f"{label}.path must be a non-empty project-relative path"
            )
        try:
            relative = Path(declared_path)
            if relative.is_absolute() or ".." in relative.parts:
                raise EvidenceError(
                    f"{label}.path must stay within the evaluation project"
                )
            resolved = (project_root / relative).resolve()
        except EvidenceError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise EvidenceError(
                f"{label}.path cannot be resolved safely: {exc}"
            ) from exc
        if project_root not in resolved.parents:
            raise EvidenceError(
                f"{label}.path must stay within the evaluation project"
            )
        protected.add(resolved)
    return protected


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"prepare", "validate", "run"}:
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
    if args.command == "execute":
        adapter_command = list(args.adapter_command)
        if adapter_command and adapter_command[0] == "--":
            adapter_command = adapter_command[1:]
        if not adapter_command:
            print("ERROR: execute requires an adapter command after --", file=sys.stderr)
            return 2
        trials_out = _project_path(args.project, args.trials_out)
        results_out = _project_path(args.project, args.results_out)
        try:
            adapter_errors = execute_trials(
                args.project,
                adapter_command,
                trials_out,
                timeout_seconds=args.timeout_seconds,
            )
        except EvidenceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        result = evaluate_project(
            args.project,
            trials_path=trials_out,
            judgments_path=args.judgments,
        )
        write_json(results_out, result)
        for error in adapter_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"execute: {result['decision']} -> {results_out}")
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
    if args.command == "inspect":
        try:
            result = load_json(args.results)
            trials = load_jsonl(args.trials) if args.trials.is_file() else []
        except EvidenceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        known = result.get("trials", [])
        if args.case and not any(row.get("case_id") == args.case for row in known):
            print(f"ERROR: unknown case {args.case!r}", file=sys.stderr)
            return 2
        if args.trial and not any(row.get("trial_id") == args.trial for row in known):
            print(f"ERROR: unknown trial {args.trial!r}", file=sys.stderr)
            return 2
        rendered = render_inspection(
            result,
            trials,
            case_id=args.case,
            trial_id=args.trial,
        )
        if args.out:
            args.out.write_text(rendered, encoding="utf-8")
            print(f"inspect: {args.out}")
        else:
            print(rendered)
        return 0
    if args.command == "fault":
        trials_path = _project_path(args.project, args.trials)
        specs_path = _project_path(args.project, args.specs)
        output_path = _project_path(args.project, args.out)
        try:
            try:
                project_root = args.project.resolve()
                if output_path.is_symlink():
                    raise EvidenceError("fault output must not be a symbolic link")
                resolved_output = output_path.resolve()
                if project_root not in resolved_output.parents:
                    raise EvidenceError(
                        "fault output must stay within the evaluation project"
                    )
                if output_path.exists():
                    if not output_path.is_file():
                        raise EvidenceError(
                            "existing fault output must be a regular file"
                        )
                    if output_path.stat().st_nlink > 1:
                        raise EvidenceError(
                            "fault output must not be a multiply linked file"
                        )
                protected_inputs = {
                    trials_path.resolve(),
                    specs_path.resolve(),
                    *(
                        (args.project / name).resolve()
                        for name in (
                            "suite.json",
                            "run.json",
                            "dataset.json",
                            "cases.jsonl",
                            "judgments.jsonl",
                            "goldens.jsonl",
                        )
                    ),
                }
                run_path = args.project / "run.json"
                run = load_json(run_path) if run_path.is_file() else {}
                protected_inputs.update(
                    _contract_lineage_input_paths(project_root, run)
                )
            except EvidenceError:
                raise
            except (OSError, RuntimeError, ValueError) as exc:
                raise EvidenceError(f"fault paths cannot be resolved safely: {exc}") from exc
            if resolved_output in protected_inputs:
                raise EvidenceError("fault output must not overwrite evaluation inputs")
            if output_path.suffix != ".jsonl" or not output_path.name.startswith(
                "trials"
            ):
                raise EvidenceError(
                    "fault output must use a trials*.jsonl filename"
                )
            trials = load_jsonl(trials_path)
            named_specs = load_json(specs_path)
            selected = named_specs.get(args.name)
            if not isinstance(selected, list):
                raise EvidenceError(f"unknown or invalid fault name: {args.name!r}")
            mutated = apply_faults(trials, selected)
            write_jsonl(output_path, mutated)
        except EvidenceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(f"fault: {args.name} -> {output_path}")
        return 0
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
