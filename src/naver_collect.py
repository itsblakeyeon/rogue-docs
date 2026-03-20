"""Collect hospitals via Naver Local Search API by region + department."""

import argparse
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET,
    NAVER_OUTPUT,
    NAVER_SEARCH_DEPARTMENTS,
    OUTPUT_DIR,
)
from naver_client import NaverClient

# 서울특별시 구 목록
SEOUL_GU = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구",
    "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구",
]

# 경기도 주요 시/군 목록
GYEONGGI_CITIES = [
    "수원시", "성남시", "고양시", "용인시", "부천시", "안산시", "안양시", "남양주시",
    "화성시", "평택시", "의정부시", "시흥시", "파주시", "김포시", "광명시", "광주시",
    "군포시", "하남시", "오산시", "이천시", "안성시", "의왕시", "양주시", "구리시",
    "포천시", "여주시", "동두천시", "과천시", "가평군", "양평군", "연천군",
]

CSV_COLUMNS = [
    "hospital_name", "institution_type", "specialty", "departments",
    "address", "sido", "sigungu", "dong", "phone", "website",
    "email", "representative", "bed_count", "doctor_count",
    "established_date", "ykiho", "source",
]


def load_existing_names(output_path: str) -> set:
    """Load already-collected hospital names for deduplication."""
    if not os.path.exists(output_path):
        return set()
    try:
        df = pd.read_csv(output_path, dtype=str)
        if "hospital_name" in df.columns:
            return set(df["hospital_name"].dropna().str.strip().tolist())
    except Exception:
        pass
    return set()


def parse_args():
    parser = argparse.ArgumentParser(description="Collect hospitals via Naver Local Search")
    parser.add_argument("--dept", type=str, default=None,
                        help="Specific department to search (e.g. 피부과, 치과)")
    parser.add_argument("--region", type=str, default=None,
                        choices=["서울", "경기", "all"],
                        help="Region to search (default: all)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit total queries (0=no limit)")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: 1 gu, 1 dept, limit=5")
    return parser.parse_args()


def main():
    args = parse_args()

    client_id = NAVER_CLIENT_ID or os.getenv("NAVER_CLIENT_ID", "")
    client_secret = NAVER_CLIENT_SECRET or os.getenv("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("ERROR: NAVER_CLIENT_ID/NAVER_CLIENT_SECRET not found in .env")
        sys.exit(1)

    client = NaverClient(client_id, client_secret, delay=0.2)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Resume support
    existing_names = load_existing_names(NAVER_OUTPUT)
    if existing_names:
        print(f"Resume: {len(existing_names)} hospitals already collected")

    # Determine search targets
    departments = [args.dept] if args.dept else NAVER_SEARCH_DEPARTMENTS
    regions = []
    if args.region in (None, "all", "서울"):
        regions.extend([("서울", gu) for gu in SEOUL_GU])
    if args.region in (None, "all", "경기"):
        regions.extend([("경기", city) for city in GYEONGGI_CITIES])

    if args.test:
        regions = regions[:1]
        departments = departments[:1]
        args.limit = 5

    total_queries = len(regions) * len(departments)
    print(f"Plan: {len(regions)} regions × {len(departments)} depts = {total_queries} queries")

    all_rows = []
    query_count = 0
    new_count = 0
    dup_count = 0

    for dept in departments:
        print(f"\n=== {dept} ===")
        for region_prefix, sub_region in regions:
            query_count += 1
            if args.limit > 0 and query_count > args.limit:
                break

            full_region = f"{region_prefix} {sub_region}"
            print(f"[{query_count}/{total_queries}] {full_region} {dept}...", end=" ")

            results = client.search_hospitals(region_prefix, sub_region, dept)

            added = 0
            for row in results:
                name = row["hospital_name"].strip()
                if name in existing_names:
                    dup_count += 1
                    continue
                existing_names.add(name)
                all_rows.append(row)
                added += 1
                new_count += 1

            print(f"{len(results)} found, {added} new")

            # Periodic save every 100 queries
            if query_count % 100 == 0 and all_rows:
                save_results(all_rows, NAVER_OUTPUT)
                print(f"  [Saved {new_count} new hospitals so far]")

        if args.limit > 0 and query_count > args.limit:
            print("Limit reached.")
            break

    # Final save
    if all_rows:
        save_results(all_rows, NAVER_OUTPUT)

    print(f"\n=== Results ===")
    print(f"Total queries: {query_count}")
    print(f"New hospitals: {new_count}")
    print(f"Duplicates skipped: {dup_count}")
    print(f"Saved: {NAVER_OUTPUT}")


def save_results(rows: list, output_path: str):
    """Append rows to existing CSV or create new."""
    new_df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    if os.path.exists(output_path):
        existing_df = pd.read_csv(output_path, dtype=str)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
