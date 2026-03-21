"""Apply Naver enrichment to HIRA data and re-run email crawl on new URLs."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_DIR


def main():
    hira_path = os.path.join(OUTPUT_DIR, "step3_hospitals_final.csv")
    enriched_path = os.path.join(OUTPUT_DIR, "hira_naver_enriched.csv")
    output_path = os.path.join(OUTPUT_DIR, "step2_hospitals_enriched.csv")

    hira = pd.read_csv(hira_path, dtype=str).fillna("")
    enriched = pd.read_csv(enriched_path, dtype=str).fillna("")

    # Build lookup: hospital_name -> naver_website
    naver_urls = {}
    for _, row in enriched.iterrows():
        name = row["hospital_name"].strip()
        url = row.get("naver_website", "").strip()
        if url:
            naver_urls[name] = url

    print(f"HIRA hospitals: {len(hira)}")
    print(f"Naver URLs available: {len(naver_urls)}")

    # Apply: fill in website where missing
    filled = 0
    for idx, row in hira.iterrows():
        if row["website"].strip() == "":
            name = row["hospital_name"].strip()
            if name in naver_urls:
                hira.at[idx, "website"] = naver_urls[name]
                filled += 1

    with_url_before = len(hira[hira["website"].str.strip() != ""]) - filled
    with_url_after = len(hira[hira["website"].str.strip() != ""])

    print(f"\nURLs before enrichment: {with_url_before}")
    print(f"URLs added from Naver: {filled}")
    print(f"URLs after enrichment: {with_url_after}")
    print(f"Still without URL: {len(hira) - with_url_after}")

    hira.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
