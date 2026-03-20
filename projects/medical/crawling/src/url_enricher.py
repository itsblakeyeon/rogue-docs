import time
import re
from typing import Optional
from urllib.parse import quote, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


class UrlEnricher:
    PORTAL_PATTERNS = [
        "naver.com",
        "kakao.com",
        "daum.net",
        "tistory.com",
        "modoo.at",
        # 의료정보 포털 (병원 자체 사이트가 아님)
        "medinavi.co.kr",
        "pervsi.com",
        "cashdoc.me",
        "goodoc.co.kr",
        "hidoc.co.kr",
        "ayo.pe.kr",
        "march14th.net",
        "hira.or.kr",
        "healthmap.or.kr",
        # 일반 포털
        "google.com",
        "google.co.kr",
        "youtube.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
    ]
    PORTAL_PREFIX_PATTERNS = [
        "blog.",
        "cafe.",
    ]

    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    def build_search_query(self, hospital_name: str, address: str) -> str:
        # Extract district (구/시) from full address
        parts = address.split()
        district = ""
        for part in parts:
            if part.endswith(("구", "시", "군")):
                district = part
        return f"{hospital_name} {district} 홈페이지"

    def is_portal_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
        except Exception:
            return True

        for pattern in self.PORTAL_PATTERNS:
            if hostname.endswith(pattern) or hostname == pattern:
                return True

        for prefix in self.PORTAL_PREFIX_PATTERNS:
            if hostname.startswith(prefix):
                return True

        return False

    def search_hospital_url(self, hospital_name: str, address: str) -> Optional[str]:
        query = self.build_search_query(hospital_name, address)
        encoded_query = quote(query)
        search_url = f"https://search.naver.com/search.naver?query={encoded_query}"

        try:
            response = requests.get(
                search_url,
                headers={"User-Agent": self.user_agent},
                timeout=10,
            )
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if not href.startswith(("http://", "https://")):
                    continue
                if not self.is_portal_url(href):
                    return href

        except Exception:
            return None

        return None

    def validate_url(self, url: str) -> bool:
        try:
            response = requests.head(
                url,
                timeout=5,
                headers={"User-Agent": self.user_agent},
            )
            return response.status_code < 400
        except Exception:
            return False

    def enrich_urls(self, hospitals_df: pd.DataFrame) -> pd.DataFrame:
        df = hospitals_df.copy()

        for idx, row in df.iterrows():
            website = row.get("website")
            if pd.isna(website) or str(website).strip() == "":
                found_url = self.search_hospital_url(
                    row["yadmNm"], row["addr"]
                )
                if found_url and self.validate_url(found_url):
                    df.at[idx, "website"] = found_url

                if self.delay > 0:
                    time.sleep(self.delay)

        return df
