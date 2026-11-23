"""Minimal CLI that prevents accidental paid calls without explicit opt-in."""
from __future__ import annotations
import argparse
import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

from .config import load_settings
from .scenarios import BY_KEY, DEFAULT_KEYS


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="patientprobe", description="Authorized synthetic-patient call tester")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scenarios", help="List all available scenario keys")
    sub.add_parser("doctor", help="Validate credentials and ffmpeg, without making calls")
    research = sub.add_parser("research", help="Evaluate annotated trials OFFLINE (never makes calls)")
    research.add_argument("--input", type=Path, required=True, help="Path to JSONL trial annotations")
    research.add_argument("--output", type=Path, required=True, help="Where to save JSON report")
    research.add_argument("--include-synthetic", action="store_true", help="Only for clearly labeled demo fixtures")
    call = sub.add_parser("run", help="Run authorized live research calls (explicit opt-in required)")
    call.add_argument("scenario", nargs="?", choices=list(BY_KEY), help="Scenario key")
    call.add_argument("--all", action="store_true", help="Run the first ten distinct scenarios")
    call.add_argument("--confirm-live-calls", action="store_true", help="Mandatory paid-call confirmation")
    call.add_argument("--delay-between", type=float, default=12.0)
    call.add_argument("--stop-on-qc-failure", action="store_true", default=False)
    review = sub.add_parser("review", help="Review real recorded calls using offline LLM evaluation")
    review.add_argument("folder", type=Path)
    report = sub.add_parser("report", help="Compile manually approved bugs across calls")
    report.add_argument("--output", type=Path, default=Path("docs/BUG_REPORT.md"))
    return p


def run_doctor(settings) -> bool:
    ok = True
    if shutil.which("ffmpeg") is None:
        print("[FAIL] ffmpeg is not installed")
        ok = False
    else:
        print("[OK] ffmpeg is available")
    if settings.sip_trunk_id.startswith("ST_"):
        print("[OK] SIP trunk ID has expected prefix")
    else:
        print("[WARN] Confirm outbound trunk ID in LiveKit Cloud")
    print("[OK] Approved test destination is configured privately (not displayed)")
    print("[OK] Caller ID configured privately (not displayed)")
    print("[NOTE] Only a live call confirms provider keys, SIP routing and audio quality")
    return ok


async def run_many(keys, settings, delay: float, stop_on_qc_failure: bool):
    from .runner import run_call
    results = []
    for i, key in enumerate(keys, 1):
        print(f"[{i}/{len(keys)}] Starting {key}", flush=True)
        result = await run_call(key, settings)
        results.append(result)
        print(json.dumps({"scenario": key, "status": result["status"],
                          "qc": result["qc"]["meets_minimum_full_call"],
                          "recording": result["recording"], "error": result["error"]}, indent=2), flush=True)
        if result["status"] == "failed":
            print("Stopping after failed call to avoid avoidable costs", flush=True)
            break
        if stop_on_qc_failure and not result["qc"]["meets_minimum_full_call"]:
            print("Stopping after failed quality check", flush=True)
            break
        if i < len(keys):
            await asyncio.sleep(delay)
    return results


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.cmd == "scenarios":
        for key, s in BY_KEY.items():
            print(f"{key:16} {s.title}")
        return 0
    if args.cmd == "research":
        from .research import evaluate_file
        try:
            result = evaluate_file(args.input, args.output, include_synthetic=args.include_synthetic)
        except (ValueError, OSError) as exc:
            print(f"Research evaluation error: {exc}", file=sys.stderr)
            return 2
        print(f"{result['report_type']}: {result['trial_count']} annotated trial(s) -> {args.output}")
        return 0
    if args.cmd == "report":
        from .analysis import bug_report
        settings = load_settings(require_live=False)
        folders = sorted(f for f in settings.artifacts_dir.glob("*") if f.is_dir())
        count = bug_report(folders, args.output)
        print(f"Compiled {count} manually verified issue(s): {args.output}")
        return 0
    try:
        settings = load_settings(require_live=True)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "doctor":
        return 0 if run_doctor(settings) else 1
    if args.cmd == "review":
        from .analysis import review_call
        try:
            path = review_call(args.folder, settings.openai_key, settings.llm_model)
        except Exception as exc:
            print(f"Review error: {exc}", file=sys.stderr)
            return 1
        print(f"Generated UNVERIFIED proposals: {path}")
        return 0
    if args.cmd == "run":
        if not args.confirm_live_calls:
            print("Refusing to dial without --confirm-live-calls (calls incur fees)", file=sys.stderr)
            return 2
        if args.all == bool(args.scenario):
            print("Supply exactly one scenario OR --all", file=sys.stderr)
            return 2
        if args.delay_between < 0:
            print("--delay-between must be nonnegative", file=sys.stderr)
            return 2
        if not run_doctor(settings):
            return 1
        keys = DEFAULT_KEYS if args.all else (args.scenario,)
        results = asyncio.run(run_many(keys, settings, args.delay_between, args.stop_on_qc_failure))
        if any(r["status"] == "failed" for r in results):
            return 1
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
