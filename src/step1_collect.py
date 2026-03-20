"""Step 1: Collect hospital basic + detail info from HIRA API."""

import argparse
import os
import sys
import time

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    DEPARTMENT_CODES,
    DEPT_TO_INSTITUTION_CODES,
    HIRA_API_KEY,
    OUTPUT_DIR,
    REGION_CODES,
    REQUEST_DELAY,
    STEP1_OUTPUT,
    TARGET_DEPARTMENTS,
    TARGET_INSTITUTION_CODES,
    INSTITUTION_TYPES,
)
from hira_client import HiraClient

# Reverse lookup: code -> name
CODE_TO_DEPT = {v: k for k, v in DEPARTMENT_CODES.items()}

# CSV column order
CSV_COLUMNS = [
    "hospital_name",
    "institution_type",
    "specialty",
    "departments",
    "address",
    "sido",
    "sigungu",
    "dong",
    "phone",
    "website",
    "email",
    "representative",
    "bed_count",
    "doctor_count",
    "established_date",
    "ykiho",
]

# Map clCd code -> institution type name
CODE_TO_TYPE = {v: k for k, v in INSTITUTION_TYPES.items()}

# Target regions (subset of REGION_CODES)
TARGET_REGIONS = {"서울": "110000", "경기": "410000"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Step 1: Collect hospitals from HIRA API")
    parser.add_argument("--test", action="store_true", help="Test mode (limit=5, skip-detail)")
    parser.add_argument("--limit", type=int, default=0, help="Limit total hospitals processed (0=no limit)")
    parser.add_argument("--skip-detail", action="store_true", help="Skip detail API calls (departments/beds)")
    parser.add_argument("--priority", type=int, default=0,
                        help="Filter by department priority group (1=피부과/성형, 2=치과/안과, 3=내과/가정, 4=정형/재활, 5=한방, 0=all)")
    parser.add_argument("--dept", type=str, default=None,
                        help="Filter by specific department code (e.g. 14 for 피부과, comma-separated for multiple)")
    return parser.parse_args(argv)


def load_existing_ykihos(output_path: str) -> set:
    """Load already-collected ykiho set from existing CSV for resume support."""
    if not os.path.exists(output_path):
        return set()
    try:
        df = pd.read_csv(output_path, dtype=str)
        if "ykiho" in df.columns:
            return set(df["ykiho"].dropna().tolist())
    except Exception:
        pass
    return set()


def hospital_to_row(hospital: dict, departments_str: str, specialty: str, bed_count: int) -> dict:
    """Convert a HIRA hospital dict + detail info into a CSV row dict."""
    return {
        "hospital_name": hospital.get("yadmNm", ""),
        "institution_type": hospital.get("clCdNm", ""),
        "specialty": specialty,
        "departments": departments_str,
        "address": hospital.get("addr", ""),
        "sido": hospital.get("sidoCdNm", ""),
        "sigungu": hospital.get("sgguCdNm", ""),
        "dong": hospital.get("emdongNm", ""),
        "phone": hospital.get("telno", ""),
        "website": hospital.get("hospUrl", ""),
        "email": "",
        "representative": "",
        "bed_count": bed_count,
        "doctor_count": hospital.get("drTotCnt", ""),
        "established_date": hospital.get("estbDd", ""),
        "ykiho": hospital.get("ykiho", ""),
    }


def main(argv=None):
    load_dotenv()

    args = parse_args(argv)

    # Test mode shortcuts
    if args.test:
        if args.limit == 0:
            args.limit = 5
        args.skip_detail = True

    api_key = HIRA_API_KEY or os.getenv("HIRA_API_KEY", "")
    if not api_key:
        print("ERROR: HIRA_API_KEY not found in .env", file=sys.stderr)
        sys.exit(1)

    client = HiraClient(api_key)

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Resume support
    existing_ykihos = load_existing_ykihos(STEP1_OUTPUT)
    if existing_ykihos:
        print(f"Resume mode: {len(existing_ykihos)} hospitals already collected, skipping them.")

    # Determine department filter
    dept_codes = []
    if args.dept:
        dept_codes = [c.strip() for c in args.dept.split(",")]
        dept_names = [CODE_TO_DEPT.get(c, c) for c in dept_codes]
        print(f"Department filter: {', '.join(dept_names)}")
    elif args.priority and args.priority in TARGET_DEPARTMENTS:
        dept_codes = TARGET_DEPARTMENTS[args.priority]
        dept_names = [CODE_TO_DEPT.get(c, c) for c in dept_codes]
        print(f"Priority {args.priority} filter: {', '.join(dept_names)}")

    # Phase 1: Collect all hospital lists
    print("=== Phase 1: Fetching hospital lists ===")
    all_hospitals = []

    # Split dept_codes into two groups:
    # 1) Departments with dedicated institution types (치과→치과의원, 한방→한의원)
    # 2) Regular departments that filter within 의원/병원
    dedicated_depts = []
    regular_depts = []
    for dc in dept_codes:
        if dc in DEPT_TO_INSTITUTION_CODES:
            dedicated_depts.append(dc)
        else:
            regular_depts.append(dc)

    for region_name, region_code in TARGET_REGIONS.items():
        # Dedicated institution types: fetch ALL of that type (no dept filter needed)
        for dept_cd in dedicated_depts:
            dept_name = CODE_TO_DEPT.get(dept_cd, dept_cd)
            for cl_cd in DEPT_TO_INSTITUTION_CODES[dept_cd]:
                type_name = CODE_TO_TYPE.get(cl_cd, cl_cd)
                print(f"Fetching {region_name} / {type_name} (전체) ...")
                try:
                    hospitals = client.fetch_all_hospitals(region_code, cl_cd)
                    print(f"  -> {len(hospitals)} hospitals found")
                    all_hospitals.extend(hospitals)
                except Exception as e:
                    print(f"  ERROR fetching {region_name}/{type_name}: {e}", file=sys.stderr)

        # Regular departments: filter within 의원/병원
        for cl_cd in TARGET_INSTITUTION_CODES:
            type_name = CODE_TO_TYPE.get(cl_cd, cl_cd)
            if regular_depts:
                for dept_cd in regular_depts:
                    dept_name = CODE_TO_DEPT.get(dept_cd, dept_cd)
                    print(f"Fetching {region_name} / {type_name} / {dept_name} ...")
                    try:
                        hospitals = client.fetch_all_hospitals(region_code, cl_cd, dgsbjt_cd=dept_cd)
                        print(f"  -> {len(hospitals)} hospitals found")
                        all_hospitals.extend(hospitals)
                    except Exception as e:
                        print(f"  ERROR fetching {region_name}/{type_name}/{dept_name}: {e}", file=sys.stderr)
            elif not dept_codes:
                print(f"Fetching {region_name} / {type_name} ...")
                try:
                    hospitals = client.fetch_all_hospitals(region_code, cl_cd)
                    print(f"  -> {len(hospitals)} hospitals found")
                    all_hospitals.extend(hospitals)
                except Exception as e:
                    print(f"  ERROR fetching {region_name}/{type_name}: {e}", file=sys.stderr)

    # Filter out already-collected
    hospitals_to_process = [h for h in all_hospitals if h.get("ykiho") not in existing_ykihos]
    print(f"\nTotal hospitals: {len(all_hospitals)}, new to process: {len(hospitals_to_process)}")

    # Apply limit
    if args.limit > 0:
        hospitals_to_process = hospitals_to_process[: args.limit]
        print(f"Limiting to {args.limit} hospitals")

    # Phase 2: Fetch details and build rows
    print("\n=== Phase 2: Processing hospitals ===")
    rows = []
    total = len(hospitals_to_process)
    for i, hospital in enumerate(hospitals_to_process, 1):
        name = hospital.get("yadmNm", "unknown")
        ykiho = hospital.get("ykiho", "")
        print(f"Processing [{i}/{total}]: {name}...")

        departments_str = ""
        specialty = ""
        bed_count = 0

        if not args.skip_detail and ykiho:
            try:
                depts = client.fetch_departments(ykiho)
                departments_str = HiraClient.aggregate_departments(depts)
                specialty = depts[0]["name"] if depts else ""
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"  WARN: departments fetch failed for {name}: {e}")

            try:
                bed_count = client.fetch_bed_count(ykiho)
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"  WARN: bed count fetch failed for {name}: {e}")

        row = hospital_to_row(hospital, departments_str, specialty, bed_count)
        rows.append(row)

    if not rows:
        print("No new hospitals to save.")
        return

    # Build DataFrame and append/create CSV
    new_df = pd.DataFrame(rows, columns=CSV_COLUMNS)

    if existing_ykihos and os.path.exists(STEP1_OUTPUT):
        existing_df = pd.read_csv(STEP1_OUTPUT, dtype=str)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_csv(STEP1_OUTPUT, index=False)
    print(f"\nSaved {len(combined_df)} total hospitals to {STEP1_OUTPUT}")
    print(f"  (newly added: {len(rows)})")


if __name__ == "__main__":
    main()
