"""Step 3: Crawl hospital websites for email addresses."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

# Add project root and src dir to path for consistent imports
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SRC_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd

from config import (
    OUTPUT_DIR,
    REQUEST_DELAY,
    STEP2_OUTPUT,
    STEP3_OUTPUT,
    EMAIL_OUTPUT,
)
from email_crawler import EmailCrawler

FAILED_URLS_LOG = os.path.join(OUTPUT_DIR, "failed_urls.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 3: Crawl hospital websites to extract email addresses."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of hospitals to process",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=STEP2_OUTPUT,
        help=f"Input CSV path (default: {STEP2_OUTPUT})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=STEP3_OUTPUT,
        help=f"Output CSV path (default: {STEP3_OUTPUT})",
    )
    parser.add_argument(
        "--use-playwright",
        action="store_true",
        default=False,
        help="Use Playwright for JS-heavy sites",
    )
    return parser.parse_args()


def load_existing_results(output_path: str) -> dict[str, dict]:
    """Load already-crawled rows from an existing output CSV for resume support."""
    if not os.path.exists(output_path):
        return {}

    df = pd.read_csv(output_path, dtype=str)
    existing = {}
    for _, row in df.iterrows():
        email_val = row.get("email", "")
        if pd.notna(email_val) and str(email_val).strip():
            key = str(row.get("hospital_name", "")) + "|" + str(row.get("website", ""))
            existing[key] = {
                "email": str(email_val).strip(),
                "representative": str(row.get("representative", "")).strip()
                if pd.notna(row.get("representative"))
                else "",
            }
    return existing


def main() -> None:
    args = parse_args()
    input_path = args.input
    output_path = args.output

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info("Loading input: %s", input_path)
    df = pd.read_csv(input_path, dtype=str)

    # Ensure columns exist
    if "email" not in df.columns:
        df["email"] = ""
    if "representative" not in df.columns:
        df["representative"] = ""

    # Fill NaN with empty string for easier handling
    df["email"] = df["email"].fillna("")
    df["representative"] = df["representative"].fillna("")
    df["website"] = df["website"].fillna("") if "website" in df.columns else ""

    # Resume: load existing results
    existing = load_existing_results(output_path)
    if existing:
        logger.info("Resuming: found %d already-crawled rows", len(existing))

    # Filter rows that have a website
    targets = df[df["website"].str.strip().astype(bool)].copy()
    if args.limit:
        targets = targets.head(args.limit)

    total = len(targets)
    logger.info("Hospitals with website to crawl: %d", total)

    crawler = EmailCrawler(use_playwright=args.use_playwright)
    failed_urls: list[str] = []
    crawled_count = 0
    email_found_count = 0

    for idx, (df_idx, row) in enumerate(targets.iterrows(), start=1):
        hospital_name = str(row.get("hospital_name", ""))
        url = str(row["website"]).strip()
        key = hospital_name + "|" + url

        # Skip if already crawled (resume)
        if key in existing:
            prev = existing[key]
            df.at[df_idx, "email"] = prev["email"]
            df.at[df_idx, "representative"] = prev["representative"]
            if prev["email"]:
                email_found_count += 1
            crawled_count += 1
            logger.info(
                "Skipping [%d/%d]: %s (already crawled)", idx, total, hospital_name
            )
            continue

        # Also skip if email is already populated in the input
        if str(row["email"]).strip():
            email_found_count += 1
            crawled_count += 1
            continue

        logger.info("Crawling [%d/%d]: %s (%s)...", idx, total, hospital_name, url)

        try:
            result = crawler.crawl_hospital(url)
            emails_str = ", ".join(result["emails"]) if result["emails"] else ""
            rep = result["representative"] or ""

            df.at[df_idx, "email"] = emails_str
            df.at[df_idx, "representative"] = rep

            if emails_str:
                email_found_count += 1

            crawled_count += 1
        except Exception as e:
            logger.warning("Failed to crawl %s: %s", url, e)
            failed_urls.append(f"{hospital_name}\t{url}\t{e}")

        # Save periodically (every 10 hospitals)
        if idx % 10 == 0:
            df.to_csv(output_path, index=False, encoding="utf-8-sig")

        time.sleep(REQUEST_DELAY)

    # Final save
    logger.info("Saving full results to %s", output_path)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    # Save filtered (email found only)
    email_df = df[df["email"].str.strip().astype(bool)]
    email_output = args.output.replace(
        os.path.basename(args.output), "hospitals_with_email.csv"
    ) if args.output != STEP3_OUTPUT else EMAIL_OUTPUT
    logger.info("Saving hospitals with email to %s", email_output)
    email_df.to_csv(email_output, index=False, encoding="utf-8-sig")

    # Log failed URLs
    if failed_urls:
        with open(FAILED_URLS_LOG, "w", encoding="utf-8") as f:
            for line in failed_urls:
                f.write(line + "\n")
        logger.info("Failed URLs logged to %s", FAILED_URLS_LOG)

    # Summary
    total_hospitals = len(df)
    with_email = len(email_df)
    pct = (with_email / total_hospitals * 100) if total_hospitals > 0 else 0
    logger.info("Total: %d, With email: %d (%.1f%%)", total_hospitals, with_email, pct)


if __name__ == "__main__":
    main()
