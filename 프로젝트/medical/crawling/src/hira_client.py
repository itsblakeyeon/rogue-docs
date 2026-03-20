import time
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    HIRA_BASE_URL,
    HIRA_DETAIL_BASE_URL,
    NUM_OF_ROWS,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
)

# Fields to extract from hospital list response
HOSPITAL_FIELDS = [
    "yadmNm", "addr", "telno", "hospUrl", "clCdNm",
    "sidoCdNm", "sgguCdNm", "emdongNm", "estbDd", "ykiho", "drTotCnt",
]

# Bed count fields to sum
BED_FIELDS = [
    "hghrSickbdCnt", "stdSickbdCnt", "aduChldSprmCnt",
    "chldSprmCnt", "nbySprmCnt",
]


class HiraClient:
    """Client for HIRA (Health Insurance Review & Assessment Service) API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def build_params(self, sido_cd: str, cl_cd: str, page: int = 1, num_of_rows: int = NUM_OF_ROWS, dgsbjt_cd: str = "") -> dict:
        """Build request parameters for hospital list API."""
        params = {
            "ServiceKey": self.api_key,
            "pageNo": page,
            "numOfRows": num_of_rows,
            "sidoCd": sido_cd,
            "clCd": cl_cd,
        }
        if dgsbjt_cd:
            params["dgsbjtCd"] = dgsbjt_cd
        return params

    def parse_response(self, xml_text: str) -> List[dict]:
        """Parse hospital list XML response into list of dicts."""
        soup = BeautifulSoup(xml_text, "xml")
        total_count = soup.find("totalCount")
        if total_count and int(total_count.text) == 0:
            return []

        items = soup.find_all("item")
        results = []
        for item in items:
            record = {}
            for field in HOSPITAL_FIELDS:
                tag = item.find(field)
                record[field] = tag.text if tag else ""
            results.append(record)
        return results

    def fetch_hospitals(self, sido_cd: str, cl_cd: str, page: int = 1, num_of_rows: int = NUM_OF_ROWS, dgsbjt_cd: str = "") -> Tuple[List[dict], int]:
        """Fetch one page of hospitals. Returns (items, totalCount)."""
        params = self.build_params(sido_cd, cl_cd, page, num_of_rows, dgsbjt_cd)
        url = f"{HIRA_BASE_URL}/getHospBasisList"
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "xml")
        total_count_tag = soup.find("totalCount")
        total_count = int(total_count_tag.text) if total_count_tag else 0

        items = self.parse_response(resp.text)
        return items, total_count

    def fetch_all_hospitals(self, sido_cd: str, cl_cd: str, dgsbjt_cd: str = "") -> List[dict]:
        """Paginate through all pages and return all hospital items."""
        all_items = []
        page = 1
        while True:
            items, total_count = self.fetch_hospitals(sido_cd, cl_cd, page, dgsbjt_cd=dgsbjt_cd)
            all_items.extend(items)
            if len(all_items) >= total_count:
                break
            page += 1
            time.sleep(REQUEST_DELAY)
        return all_items

    # --- Task 3: Detail APIs ---

    def parse_departments(self, xml_text: str) -> List[dict]:
        """Parse department info XML into list of {code, name, doctor_count}."""
        soup = BeautifulSoup(xml_text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items:
            code_tag = item.find("dgsbjtCd")
            name_tag = item.find("dgsbjtCdNm")
            count_tag = item.find("dgsbjtPrSdrCnt")
            results.append({
                "code": code_tag.text if code_tag else "",
                "name": name_tag.text if name_tag else "",
                "doctor_count": int(count_tag.text) if count_tag else 0,
            })
        return results

    def parse_bed_count(self, xml_text: str) -> int:
        """Parse bed info XML and return total bed count (sum of all bed fields)."""
        soup = BeautifulSoup(xml_text, "xml")
        item = soup.find("item")
        if not item:
            return 0
        total = 0
        for field in BED_FIELDS:
            tag = item.find(field)
            if tag and tag.text:
                total += int(tag.text)
        return total

    def fetch_departments(self, ykiho: str) -> List[dict]:
        """Fetch department info for a hospital by ykiho."""
        url = f"{HIRA_DETAIL_BASE_URL}/getDgsbjtInfo2.7"
        params = {
            "ServiceKey": self.api_key,
            "ykiho": ykiho,
        }
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return self.parse_departments(resp.text)

    def fetch_bed_count(self, ykiho: str) -> int:
        """Fetch bed count for a hospital by ykiho."""
        url = f"{HIRA_DETAIL_BASE_URL}/getEqpInfo2.7"
        params = {
            "ServiceKey": self.api_key,
            "ykiho": ykiho,
        }
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return self.parse_bed_count(resp.text)

    @staticmethod
    def aggregate_departments(departments: List[dict]) -> str:
        """Join department names as comma-separated string."""
        return ", ".join(d["name"] for d in departments)
