"""Main pipeline orchestrator — runs step1, step2, step3 sequentially."""

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent

STEPS = {
    1: SRC_DIR / "step1_collect.py",
    2: SRC_DIR / "step2_enrich_urls.py",
    3: SRC_DIR / "step3_crawl_emails.py",
}


def build_step_args(step: int, args: argparse.Namespace) -> list[str]:
    """Build subprocess arguments for the given step."""
    cmd = [sys.executable, str(STEPS[step])]
    if args.limit:
        cmd += ["--limit", str(args.limit)]
    if step == 1 and args.skip_detail:
        cmd.append("--skip-detail")
    if step == 1 and args.priority:
        cmd += ["--priority", str(args.priority)]
    if step == 1 and args.dept:
        cmd += ["--dept", args.dept]
    if step == 3 and args.use_playwright:
        cmd.append("--use-playwright")
    return cmd


def run_step(step: int, args: argparse.Namespace) -> None:
    """Run a single pipeline step as a subprocess, logging timing."""
    script = STEPS[step]
    if not script.exists():
        print(f"[ERROR] Step {step} script not found: {script}")
        sys.exit(1)

    cmd = build_step_args(step, args)
    print(f"\n{'='*60}")
    print(f"[Step {step}] Starting: {script.name}")
    print(f"  Command: {' '.join(cmd)}")
    start = time.time()

    result = subprocess.run(cmd)

    elapsed = time.time() - start
    minutes, seconds = divmod(elapsed, 60)

    if result.returncode != 0:
        print(f"[Step {step}] FAILED (exit code {result.returncode}) after {int(minutes)}m {seconds:.1f}s")
        sys.exit(result.returncode)

    print(f"[Step {step}] Completed in {int(minutes)}m {seconds:.1f}s")


def print_summary() -> None:
    """Read the final CSV and print summary statistics."""
    # Import config here to resolve OUTPUT paths
    sys.path.insert(0, str(SRC_DIR))
    from config import STEP3_OUTPUT

    final_csv = Path(STEP3_OUTPUT)
    if not final_csv.exists():
        print("\n[Summary] Final CSV not found — skipping summary.")
        return

    total = 0
    with_url = 0
    with_email = 0

    with open(final_csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in (reader.fieldnames or [])]
        for row in reader:
            row = {k.strip(): v.strip() if v else "" for k, v in row.items()}
            total += 1
            # Check for website URL (try common column names)
            url_val = row.get("website") or row.get("url") or row.get("homepage") or ""
            if url_val:
                with_url += 1
            # Check for email
            email_val = row.get("email") or row.get("emails") or ""
            if email_val:
                with_email += 1

    rate = (with_email / total * 100) if total else 0.0

    print(f"\n{'='*60}")
    print("[Summary]")
    print(f"  Total hospitals collected : {total:,}")
    print(f"  With website URL          : {with_url:,}")
    print(f"  With email found          : {with_email:,}")
    print(f"  Email collection rate     : {rate:.1f}%")
    print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hospital crawling pipeline — run all steps or a single step.",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3],
        help="Run only step N (1, 2, or 3)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of items processed in each step (0 = no limit)",
    )
    parser.add_argument(
        "--skip-detail",
        action="store_true",
        help="Skip detail API calls in step 1",
    )
    parser.add_argument(
        "--use-playwright",
        action="store_true",
        help="Use Playwright browser for email crawling in step 3",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Filter by department priority group in step 1 (1=피부과/성형, 2=치과/안과, etc.)",
    )
    parser.add_argument(
        "--dept",
        type=str,
        default=None,
        help="Filter by department code in step 1 (e.g. 14,08)",
    )
    args = parser.parse_args()

    pipeline_start = time.time()
    steps_to_run = [args.step] if args.step else [1, 2, 3]

    print(f"Pipeline: running step(s) {steps_to_run}")

    for step in steps_to_run:
        run_step(step, args)

    elapsed = time.time() - pipeline_start
    minutes, seconds = divmod(elapsed, 60)
    print(f"\nAll steps completed in {int(minutes)}m {seconds:.1f}s")

    # Print summary if step 3 was included
    if 3 in steps_to_run:
        print_summary()


if __name__ == "__main__":
    main()
