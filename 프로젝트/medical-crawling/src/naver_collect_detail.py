"""Detailed Naver collection — search at 구/동 level for better coverage."""

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

# 경기도 주요 시 → 구 단위
GYEONGGI_GU = {
    "수원시": ["장안구", "권선구", "팔달구", "영통구"],
    "성남시": ["수정구", "중원구", "분당구"],
    "고양시": ["덕양구", "일산동구", "일산서구"],
    "용인시": ["처인구", "기흥구", "수지구"],
    "안산시": ["상록구", "단원구"],
    "안양시": ["만안구", "동안구"],
}

# 서울 구 → 주요 동 (커버리지 확대)
SEOUL_DONG = {
    "강남구": ["역삼동", "삼성동", "논현동", "신사동", "청담동", "대치동", "도곡동", "압구정동"],
    "서초구": ["서초동", "반포동", "잠원동", "방배동", "양재동"],
    "송파구": ["잠실동", "가락동", "문정동", "방이동", "석촌동", "송파동"],
    "마포구": ["합정동", "상암동", "망원동", "연남동", "서교동", "공덕동"],
    "영등포구": ["여의도동", "영등포동", "당산동", "문래동", "신길동"],
    "종로구": ["종로", "관철동", "인사동", "혜화동", "삼청동"],
    "중구": ["명동", "을지로", "충무로", "신당동", "황학동"],
    "강서구": ["화곡동", "등촌동", "발산동", "마곡동", "공항동"],
    "노원구": ["상계동", "중계동", "하계동", "월계동", "공릉동"],
    "관악구": ["신림동", "봉천동", "남현동"],
    "강동구": ["천호동", "길동", "둔촌동", "명일동", "암사동"],
    "구로구": ["구로동", "신도림동", "고척동", "개봉동"],
    "동작구": ["사당동", "노량진동", "흑석동", "상도동"],
    "성동구": ["성수동", "왕십리동", "금호동", "옥수동"],
    "광진구": ["건대입구", "구의동", "자양동", "화양동"],
    "용산구": ["이태원동", "한남동", "용산동", "청파동"],
    "서대문구": ["신촌동", "연희동", "홍제동", "충정로"],
    "동대문구": ["전농동", "답십리동", "장안동", "회기동"],
    "성북구": ["길음동", "정릉동", "돈암동", "성북동"],
    "강북구": ["미아동", "수유동", "번동", "우이동"],
    "도봉구": ["창동", "쌍문동", "방학동", "도봉동"],
    "은평구": ["응암동", "역촌동", "불광동", "녹번동"],
    "양천구": ["목동", "신월동", "신정동"],
    "금천구": ["가산동", "독산동", "시흥동"],
    "중랑구": ["면목동", "상봉동", "묵동", "신내동"],
}

CSV_COLUMNS = [
    "hospital_name", "institution_type", "specialty", "departments",
    "address", "sido", "sigungu", "dong", "phone", "website",
    "email", "representative", "bed_count", "doctor_count",
    "established_date", "ykiho", "source",
]


def load_existing_names(output_path: str) -> set:
    if not os.path.exists(output_path):
        return set()
    try:
        df = pd.read_csv(output_path, dtype=str)
        if "hospital_name" in df.columns:
            return set(df["hospital_name"].dropna().str.strip().tolist())
    except Exception:
        pass
    return set()


def save_results(rows: list, output_path: str):
    new_df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    if os.path.exists(output_path):
        existing_df = pd.read_csv(output_path, dtype=str)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["seoul", "gyeonggi", "all"], default="all")
    parser.add_argument("--dept", type=str, default=None)
    args = parser.parse_args()

    client_id = NAVER_CLIENT_ID or os.getenv("NAVER_CLIENT_ID", "")
    client_secret = NAVER_CLIENT_SECRET or os.getenv("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("ERROR: NAVER_CLIENT_ID/NAVER_CLIENT_SECRET not found")
        sys.exit(1)

    client = NaverClient(client_id, client_secret, delay=0.15)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    existing_names = load_existing_names(NAVER_OUTPUT)
    print(f"Existing: {len(existing_names)} hospitals")

    departments = [args.dept] if args.dept else NAVER_SEARCH_DEPARTMENTS

    # Build search targets: (region_prefix, sub_region) pairs
    targets = []
    if args.target in ("all", "seoul"):
        for gu, dongs in SEOUL_DONG.items():
            for dong in dongs:
                targets.append(("서울", f"{gu} {dong}"))
    if args.target in ("all", "gyeonggi"):
        for city, gus in GYEONGGI_GU.items():
            for gu in gus:
                targets.append(("경기", f"{city} {gu}"))

    total_queries = len(targets) * len(departments)
    print(f"Plan: {len(targets)} locations × {len(departments)} depts = {total_queries} queries")

    all_rows = []
    query_count = 0
    new_count = 0

    for dept in departments:
        print(f"\n=== {dept} ===")
        for region_prefix, sub_region in targets:
            query_count += 1
            results = client.search_hospitals(region_prefix, sub_region, dept)

            added = 0
            for row in results:
                name = row["hospital_name"].strip()
                if name in existing_names:
                    continue
                existing_names.add(name)
                all_rows.append(row)
                added += 1
                new_count += 1

            if added > 0:
                print(f"  [{query_count}/{total_queries}] {region_prefix} {sub_region} {dept}: +{added}")

            if query_count % 200 == 0 and all_rows:
                save_results(all_rows, NAVER_OUTPUT)
                all_rows = []
                print(f"  [Saved, total new: {new_count}]")

    if all_rows:
        save_results(all_rows, NAVER_OUTPUT)

    print(f"\n=== Done ===")
    print(f"Queries: {query_count}")
    print(f"New hospitals: {new_count}")


if __name__ == "__main__":
    main()
