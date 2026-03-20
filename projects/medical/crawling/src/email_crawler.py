from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import requests

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import REQUEST_TIMEOUT


class EmailCrawler:
    """Crawls hospital websites to extract email addresses and representative names."""

    # Regex for email addresses
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    # Extensions to filter out (image files mistaken as emails)
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}

    # Prefixes to filter out (non-human addresses)
    FILTERED_PREFIXES = {"noreply@", "no-reply@", "webmaster@", "mailer-daemon@"}

    # Contact page keywords (in href or link text)
    CONTACT_KEYWORDS = [
        "연락처", "문의", "contact", "오시는길", "about", "소개", "인사말", "greeting",
        "footer", "회사소개", "병원소개", "의료진", "원장", "찾아오시는", "상담",
        "고객센터", "customer", "inquiry", "staff", "doctor", "team",
    ]

    # Subpage path patterns to try when no contact page found
    SUBPAGE_PATHS = [
        "/contact", "/about", "/inquiry", "/greeting",
        "/sub/contact", "/sub/about", "/company", "/info",
        "/page/contact", "/page/about",
    ]

    # Representative name patterns
    NAME_PATTERNS = [
        re.compile(r"대표원장\s*[:\s]\s*([가-힣]{2,4})"),
        re.compile(r"원장\s+([가-힣]{2,4})"),
        re.compile(r"대표\s*[:\s]\s*([가-힣]{2,4})"),
    ]

    def __init__(self, use_playwright: bool = False):
        self.use_playwright = use_playwright
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch_page(self, url: str) -> str | None:
        """Fetch page HTML. Returns None on failure."""
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.exceptions.SSLError:
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding
                return resp.text
            except requests.RequestException:
                pass
        except requests.RequestException:
            pass

        if self.use_playwright:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, timeout=REQUEST_TIMEOUT * 1000)
                    html = page.content()
                    browser.close()
                    return html
            except Exception:
                pass

        return None

    def extract_emails(self, html: str) -> set[str]:
        """Extract unique, valid email addresses from HTML."""
        emails = set()

        # Extract from mailto: links
        soup = BeautifulSoup(html, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("mailto:"):
                # Strip mailto: and any query params
                email_part = href[7:].split("?")[0].strip()
                if email_part:
                    emails.add(email_part.lower())

        # Extract via regex from raw HTML
        for match in self.EMAIL_PATTERN.findall(html):
            emails.add(match.lower())

        # Filter invalid
        filtered = set()
        for email in emails:
            # Check image extensions
            if any(email.endswith(ext) for ext in self.IMAGE_EXTENSIONS):
                continue
            # Check filtered prefixes
            if any(email.startswith(prefix) for prefix in self.FILTERED_PREFIXES):
                continue
            filtered.add(email)

        return filtered

    def find_contact_pages(self, html: str, base_url: str) -> list[str]:
        """Find links to contact-related pages."""
        soup = BeautifulSoup(html, "html.parser")
        urls = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            text = a_tag.get_text(strip=True)
            href_lower = href.lower()
            text_lower = text.lower()

            is_contact = any(
                kw in href_lower or kw in text_lower
                for kw in self.CONTACT_KEYWORDS
            )

            if is_contact:
                absolute_url = urljoin(base_url, href)
                if absolute_url not in urls:
                    urls.append(absolute_url)

        return urls

    def extract_representative_name(self, html: str) -> str | None:
        """Extract representative/director name from HTML."""
        for pattern in self.NAME_PATTERNS:
            match = pattern.search(html)
            if match:
                return match.group(1)
        return None

    def crawl_hospital(self, url: str) -> dict:
        """Main crawl method for a hospital URL. Deep crawl: homepage → contact pages → subpage paths."""
        result = {"emails": [], "representative": None}

        html = self.fetch_page(url)
        if not html:
            return result

        emails = self.extract_emails(html)
        result["representative"] = self.extract_representative_name(html)

        if not emails:
            # Try contact pages found in links
            contact_pages = self.find_contact_pages(html, url)
            for contact_url in contact_pages[:5]:  # limit to 5
                contact_html = self.fetch_page(contact_url)
                if contact_html:
                    emails.update(self.extract_emails(contact_html))
                    if not result["representative"]:
                        result["representative"] = self.extract_representative_name(contact_html)
                if emails:
                    break

        if not emails:
            # Try common subpage paths
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            for path in self.SUBPAGE_PATHS:
                sub_url = base + path
                sub_html = self.fetch_page(sub_url)
                if sub_html and len(sub_html) > 500:  # skip error pages
                    emails.update(self.extract_emails(sub_html))
                    if not result["representative"]:
                        result["representative"] = self.extract_representative_name(sub_html)
                if emails:
                    break

        result["emails"] = sorted(emails)
        return result
