"""Crawl emails from Naver-collected hospital websites."""

import logging
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from config import NAVER_OUTPUT, OUTPUT_DIR
from email_crawler import EmailCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

NAVER_EMAIL_OUTPUT = os.path.join(OUTPUT_DIR, "naver_hospitals_with_email.csv")
SAVE_INTERVAL = 20


def main():
    if not os.path.exists(NAVER_OUTPUT):
        print(f"ERROR: {NAVER_OUTPUT} not found. Run naver_collect.py first.")
        sys.exit(1)

    df = pd.read_csv(NAVER_OUTPUT, dtype=str).fillna("")

    # Resume support: load already-crawled names
    crawled_names = set()
    if os.path.exists(NAVER_EMAIL_OUTPUT):
        existing = pd.read_csv(NAVER_EMAIL_OUTPUT, dtype=str).fillna("")
        crawled_names = set(existing["hospital_name"].tolist())
        logger.info(f"Resume: {len(crawled_names)} already crawled")

    crawler = EmailCrawler()
    total = len(df)
    new_results = []

    for i, (idx, row) in enumerate(df.iterrows(), 1):
        name = row["hospital_name"].strip()
        website = row["website"].strip()

        if name in crawled_names:
            continue

        if not website or website in ("", "http://", "https://"):
            crawled_names.add(name)
            new_results.append(row.to_dict())
            continue

        logger.info(f"Crawling [{i}/{total}]: {name} ({website})...")

        try:
            result = crawler.crawl_hospital(website)
            emails = result.get("emails", [])
            representative = result.get("representative", "")

            row_dict = row.to_dict()
            row_dict["email"] = ", ".join(emails) if emails else ""
            row_dict["representative"] = representative
            new_results.append(row_dict)
            crawled_names.add(name)

            if emails:
                logger.info(f"  Found: {', '.join(emails)}")
        except Exception as e:
            logger.warning(f"  Error crawling {name}: {e}")
            new_results.append(row.to_dict())
            crawled_names.add(name)

        # Periodic save
        if len(new_results) % SAVE_INTERVAL == 0 and new_results:
            save_results(new_results, df.columns.tolist())
            logger.info(f"  [Saved progress: {len(new_results)} new]")

    # Final save
    if new_results:
        save_results(new_results, df.columns.tolist())

    # Summary
    final_df = pd.read_csv(NAVER_EMAIL_OUTPUT, dtype=str).fillna("")
    with_email = len(final_df[final_df["email"].str.strip() != ""])
    logger.info(f"Total: {len(final_df)}, With email: {with_email} ({with_email/len(final_df)*100:.1f}%)")


def save_results(new_rows: list, columns: list):
    new_df = pd.DataFrame(new_rows)
    if os.path.exists(NAVER_EMAIL_OUTPUT):
        existing = pd.read_csv(NAVER_EMAIL_OUTPUT, dtype=str)
        combined = pd.concat([existing, new_df], ignore_index=True)
        # Deduplicate by hospital_name
        combined = combined.drop_duplicates(subset=["hospital_name"], keep="last")
    else:
        combined = new_df
    combined.to_csv(NAVER_EMAIL_OUTPUT, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
