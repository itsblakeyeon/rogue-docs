"""Enrich HIRA hospitals that have no website by searching their name on Naver.

v2: Loose matching + retry with name-only query if area+name fails."""

import os
import re
import sys
import time
import argparse

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, OUTPUT_DIR
from naver_client import NaverClient


def normalize_name(name: str) -> str:
    """Normalize hospital name for fuzzy matching."""
    # Remove common suffixes/prefixes for matching
    name = re.sub(r"\s*(의원|병원|클리닉|센터)$", "", name.strip())
    # Remove spaces
    return name.replace(" ", "")


def fuzzy_match(hira_name: str, naver_name: str) -> bool:
    """Loose name matching between HIRA and Naver results."""
    h = normalize_name(hira_name)
    n = normalize_name(naver_name)
    # Exact normalized match
    if h == n:
        return True
    # One contains the other
    if h in n or n in h:
        return True
    # Original names contain each other
    if hira_name in naver_name or naver_name in hira_name:
        return True
    # Check if core part (2+ chars) overlaps
    if len(h) >= 3 and len(n) >= 3:
        # Longest common substring >= 3 chars
        for i in range(len(h)):
            for j in range(i + 3, min(i + len(h), len(h)) + 1):
                if h[i:j] in n:
                    return True
    return False


def is_valid_website(url: str) -> bool:
    """Filter out non-website URLs (blogs, social, portals)."""
    blocked = ["blog.naver.com", "cafe.naver.com", "youtube.com", "youtu.be",
               "instagram.com", "facebook.com", "kakao.com", "pf.kakao.com",
               "booking.naver.com", "map.naver.com", "place.naver.com"]
    url_lower = url.lower()
    return not any(b in url_lower for b in blocked)


def main():
    parser = argparse.ArgumentParser(description="Enrich HIRA hospitals via Naver name search")
    parser.add_argument("--limit", type=int, default=0, help="Max hospitals to process (0=all)")
    parser.add_argument("--resume", action="store_true", help="Resume from last progress")
    parser.add_argument("--retry-failed", action="store_true", help="Retry previously failed (no URL found)")
    args = parser.parse_args()

    client_id = NAVER_CLIENT_ID or os.getenv("NAVER_CLIENT_ID", "")
    client_secret = NAVER_CLIENT_SECRET or os.getenv("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("ERROR: NAVER_CLIENT_ID/NAVER_CLIENT_SECRET not found")
        sys.exit(1)

    client = NaverClient(client_id, client_secret, delay=0.15)

    # Load HIRA data
    hira_path = os.path.join(OUTPUT_DIR, "step3_hospitals_final.csv")
    df = pd.read_csv(hira_path, dtype=str).fillna("")

    # Load progress if resuming
    enriched_path = os.path.join(OUTPUT_DIR, "hira_naver_enriched.csv")
    processed_names = set()
    failed_names = set()
    if (args.resume or args.retry_failed) and os.path.exists(enriched_path):
        done_df = pd.read_csv(enriched_path, dtype=str).fillna("")
        processed_names = set(done_df["hospital_name"].str.strip().tolist())
        failed_names = set(
            done_df[done_df["naver_website"].str.strip() == ""]["hospital_name"].str.strip().tolist()
        )
        print(f"Resume: {len(processed_names)} already processed, {len(failed_names)} failed")

    # Filter targets
    no_url = df[df["website"].str.strip() == ""].copy()
    if args.retry_failed:
        # Only retry ones that previously failed
        no_url = no_url[no_url["hospital_name"].str.strip().isin(failed_names)]
        # Remove from processed so they get re-processed
        processed_names -= failed_names
        print(f"Retrying {len(no_url)} previously failed hospitals")
    else:
        no_url = no_url[~no_url["hospital_name"].str.strip().isin(processed_names)]

    print(f"HIRA hospitals to process: {len(no_url)}")

    if args.limit > 0:
        no_url = no_url.head(args.limit)
        print(f"Limited to: {args.limit}")

    results = []
    found_count = 0
    total = len(no_url)

    for i, (idx, row) in enumerate(no_url.iterrows()):
        name = row["hospital_name"].strip()
        address = row.get("address", "").strip()

        website = ""
        phone = ""

        # Strategy 1: area + name
        addr_parts = address.split()
        area = " ".join(addr_parts[:2]) if len(addr_parts) >= 2 else ""
        query = f"{area} {name}" if area else name
        items = client.search(query, max_pages=1)

        for item in items:
            clean_name = client.clean_title(item.get("title", ""))
            if fuzzy_match(name, clean_name):
                link = item.get("link", "")
                if link:
                    website = link
                    phone = item.get("telephone", "") or row.get("phone", "")
                    break

        # Strategy 2: name only (if area+name failed)
        if not website and area:
            items = client.search(name, max_pages=1)
            for item in items:
                clean_name = client.clean_title(item.get("title", ""))
                if fuzzy_match(name, clean_name):
                    link = item.get("link", "")
                    if link:
                        website = link
                        phone = item.get("telephone", "") or row.get("phone", "")
                        break

        # Strategy 3: take first medical result even without name match (address match)
        if not website:
            for item in items:
                item_addr = item.get("roadAddress", "") or item.get("address", "")
                # Check if addresses share sigungu
                if len(addr_parts) >= 2 and addr_parts[1] in item_addr:
                    link = item.get("link", "")
                    category = item.get("category", "")
                    if link and any(kw in category for kw in ["의원", "병원", "피부", "성형", "클리닉"]):
                        # Weak match - only use if it's a proper website
                        if is_valid_website(link):
                            website = link
                            phone = item.get("telephone", "") or row.get("phone", "")
                            break

        results.append({
            "hospital_name": name,
            "address": address,
            "naver_website": website,
            "naver_phone": phone,
        })

        if website:
            found_count += 1

        if (i + 1) % 100 == 0:
            print(f"[{i+1}/{total}] Processed, {found_count} websites found so far")
            save_progress(results, enriched_path, processed_names)

        if (i + 1) % 1000 == 0:
            print(f"  [Checkpoint saved]")

    # Final save
    save_progress(results, enriched_path, processed_names)

    print(f"\n=== Done ===")
    print(f"Processed: {len(results)}")
    print(f"Websites found: {found_count} ({found_count/max(len(results),1)*100:.1f}%)")
    print(f"Saved: {enriched_path}")


def save_progress(results, output_path, processed_names):
    new_df = pd.DataFrame(results)
    if os.path.exists(output_path) and processed_names:
        existing_df = pd.read_csv(output_path, dtype=str)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
