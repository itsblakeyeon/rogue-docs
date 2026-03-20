"""Naver Local Search API client for hospital discovery."""

import re
import time
from typing import List, Optional

import requests


class NaverClient:
    """Client for Naver Local Search API."""

    BASE_URL = "https://openapi.naver.com/v1/search/local.json"
    MAX_DISPLAY = 5  # API hard limit

    def __init__(self, client_id: str, client_secret: str, delay: float = 0.2):
        self.client_id = client_id
        self.client_secret = client_secret
        self.delay = delay

    def search(self, query: str) -> List[dict]:
        """Search for local businesses. Returns up to 5 results."""
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {
            "query": query,
            "display": self.MAX_DISPLAY,
            "start": 1,
            "sort": "comment",
        }
        try:
            resp = requests.get(
                self.BASE_URL, headers=headers, params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
        except Exception as e:
            print(f"  Naver search error for '{query}': {e}")
            return []

    @staticmethod
    def clean_title(title: str) -> str:
        """Remove HTML tags from title."""
        return re.sub(r"<[^>]+>", "", title).strip()

    @staticmethod
    def is_hospital(item: dict) -> bool:
        """Check if search result is a medical institution."""
        category = item.get("category", "")
        medical_keywords = [
            "의원", "병원", "치과", "안과", "피부과", "성형", "내과",
            "정형외과", "재활", "한의원", "한방", "의료", "클리닉",
            "가정의학", "외과",
        ]
        return any(kw in category for kw in medical_keywords)

    def item_to_row(self, item: dict, department: str) -> dict:
        """Convert a Naver search result to a CSV row dict."""
        return {
            "hospital_name": self.clean_title(item.get("title", "")),
            "institution_type": item.get("category", ""),
            "specialty": department,
            "departments": department,
            "address": item.get("roadAddress", "") or item.get("address", ""),
            "sido": "",
            "sigungu": "",
            "dong": "",
            "phone": item.get("telephone", ""),
            "website": item.get("link", ""),
            "email": "",
            "representative": "",
            "bed_count": "",
            "doctor_count": "",
            "established_date": "",
            "ykiho": "",
            "source": "naver",
        }

    def search_hospitals(
        self, region: str, dong: str, department: str
    ) -> List[dict]:
        """Search for hospitals in a specific dong + department."""
        query = f"{region} {dong} {department}"
        items = self.search(query)
        if self.delay > 0:
            time.sleep(self.delay)

        results = []
        for item in items:
            if self.is_hospital(item):
                row = self.item_to_row(item, department)
                # Parse sido/sigungu from address
                addr = row["address"]
                parts = addr.split()
                if len(parts) >= 1:
                    row["sido"] = parts[0]
                if len(parts) >= 2:
                    row["sigungu"] = parts[1]
                if len(parts) >= 3:
                    row["dong"] = parts[2]
                results.append(row)
        return results
