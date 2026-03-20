"""Step 2: Enrich hospital data with website URLs via search."""

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from config import STEP1_OUTPUT, STEP2_OUTPUT, OUTPUT_DIR
from url_enricher import UrlEnricher

MAX_WORKERS = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 2: Enrich hospitals with website URLs"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of hospitals to process (for testing)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=STEP1_OUTPUT,
        help=f"Input CSV path (default: {STEP1_OUTPUT})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=STEP2_OUTPUT,
        help=f"Output CSV path (default: {STEP2_OUTPUT})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    os.makedirs(os.path.dirname(args.output) or OUTPUT_DIR, exist_ok=True)

    # Load input
    if not os.path.exists(args.input):
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    df = pd.read_csv(args.input)
    logger.info("Loaded %d hospitals from %s", len(df), args.input)

    # Ensure website column exists
    if "website" not in df.columns:
        df["website"] = ""

    # Resume support: if output file exists, merge already-enriched URLs
    if os.path.exists(args.output):
        existing = pd.read_csv(args.output)
        logger.info("Resuming: loaded %d rows from existing output", len(existing))
        # Update df with URLs already found in previous run
        if "website" in existing.columns:
            existing_urls = existing.set_index("ykiho")["website"].dropna()
            existing_urls = existing_urls[existing_urls.str.strip() != ""]
            for ykiho, url in existing_urls.items():
                mask = df["ykiho"] == ykiho
                df.loc[mask, "website"] = url

    # Identify rows that still need URL enrichment
    needs_url = df["website"].isna() | (df["website"].astype(str).str.strip() == "")
    candidates = df[needs_url]

    if args.limit is not None:
        candidates = candidates.head(args.limit)

    total = len(candidates)
    if total == 0:
        logger.info("No hospitals need URL enrichment. Done.")
        df.to_csv(args.output, index=False)
        return

    logger.info("Enriching URLs for %d hospitals (workers=%d)", total, MAX_WORKERS)
    enricher = UrlEnricher()

    def _enrich_one(item):
        idx, row = item
        name = row["hospital_name"]
        addr = row.get("address", "")
        found_url = enricher.search_hospital_url(name, addr)
        if found_url and enricher.validate_url(found_url):
            return idx, found_url
        return idx, None

    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_enrich_one, (idx, row)): idx for idx, row in candidates.iterrows()}
        for future in as_completed(futures):
            completed += 1
            idx, url = future.result()
            name = df.at[idx, "hospital_name"]
            if url:
                df.at[idx, "website"] = url
                logger.info("[%d/%d] %s → %s", completed, total, name, url)
            else:
                logger.info("[%d/%d] %s → No URL", completed, total, name)

            if completed % 50 == 0:
                df.to_csv(args.output, index=False)
                logger.info("Progress saved (%d/%d)", completed, total)

    # Final save
    df.to_csv(args.output, index=False)
    enriched_count = df["website"].notna() & (df["website"].astype(str).str.strip() != "")
    logger.info(
        "Done. %d/%d hospitals have URLs. Saved to %s",
        enriched_count.sum(),
        len(df),
        args.output,
    )


if __name__ == "__main__":
    main()
