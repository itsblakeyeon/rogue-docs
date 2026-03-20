"""Step 2: Enrich hospital data with website URLs via search."""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from config import STEP1_OUTPUT, STEP2_OUTPUT, OUTPUT_DIR
from url_enricher import UrlEnricher

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

    logger.info("Enriching URLs for %d hospitals", total)
    enricher = UrlEnricher()

    for i, (idx, row) in enumerate(candidates.iterrows(), start=1):
        hospital_name = row["hospital_name"]
        logger.info("Enriching URL [%d/%d]: %s", i, total, hospital_name)

        found_url = enricher.search_hospital_url(hospital_name, row.get("address", ""))
        if found_url and enricher.validate_url(found_url):
            df.at[idx, "website"] = found_url
            logger.info("  Found: %s", found_url)
        else:
            logger.info("  No URL found")

        # Periodic save every 50 rows
        if i % 50 == 0:
            df.to_csv(args.output, index=False)
            logger.info("Progress saved (%d/%d)", i, total)

        if enricher.delay > 0:
            time.sleep(enricher.delay)

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
