"""Validate and clean email addresses: junk removal + format check + MX record verification."""

import os
import re
import sys
from typing import Optional

import dns.resolver
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_DIR

# --- Junk patterns to remove ---
JUNK_EMAILS = {
    "yt-support-solutions-kr@google.com",
    "email@example.com",
    "test@example.com",
}

JUNK_DOMAINS = [
    "sentry.wixpress.com", "sentry-next.wixpress.com",  # error tracking
    "11.min.css", "11.min.js",  # CSS/JS filenames
    "domain.com", "example.com",  # placeholders
    "a.com",  # placeholder
    "web2002.co.kr",  # web agency template
]

JUNK_PATTERNS = [
    re.compile(r"^.{1,2}@"),  # 1-2 char local part (d@2.fnx)
    re.compile(r"@.+\.(css|js|png|jpg|svg)$", re.I),  # file extensions
    re.compile(r"^(noreply|no-reply|mailer-daemon|postmaster|abuse)@", re.I),
]

# Agency/web-agency/platform/media emails (not the hospital's own)
AGENCY_DOMAINS = [
    # 웹에이전시 / 개발사
    "beautyleader.co.kr",   # 병원 마케팅 대행사 (11건, 같은 master@ 반복)
    "boazent.co.kr",        # 웹에이전시 (6건, info@ 반복)
    "boazent.net",          # 웹에이전시 (2건)
    "web2002.co.kr",        # 웹에이전시 (13건, test@ 반복)
    "bbgnetworks.com",      # 웹개발사 (톡스앤필 계열 사이트 제작)
    "madeinreal.com",       # 웹개발사
    "anybuild.co.kr",       # 웹빌더
    "imweb.me",             # 웹빌더 플랫폼
    "vizensoft.com",        # IT 솔루션
    "eurekanet.co.kr",      # 웹개발사 (tech@ 반복)
    "strikingly.com",       # 웹빌더 플랫폼
    # 마케팅 대행사
    "cunetwork.co.kr",      # 마케팅 대행사 (5건, promotion@ 반복)
    "maylin.co.kr",         # 마케팅 대행사 (4건, mkt@ 반복)
    "vnco.kr",              # PR/마케팅 대행사
    "lingtea.co.kr",        # 마케팅 대행사
    "brancos.co.kr",        # 마케팅 대행사
    # 의료 플랫폼 / 미디어 (병원 자체 이메일 아님)
    "rapportian.com",       # 의료 IT 솔루션
    "okchart.com",          # 의료 차트 솔루션
    "techlist.com",         # 해시값 이메일 (3건, 트래킹용)
    "docfriends.com",       # 의료 플랫폼
    "mdtoday.co.kr",        # 의료 뉴스 미디어
    "medigate.net",         # 의료 뉴스 미디어
    "dable.io",             # 광고 플랫폼
    "seoultimes.news",      # 뉴스 미디어
    # 기타
    "e-dream.co.kr",        # 웹개발사 (3건, dream@ 반복)
    "dolwumul.com",         # 콘텐츠 대행
    "girinlife.com",        # test@ 포함, 관리용
]

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Cache MX results
_mx_cache = {}


def check_mx(domain: str) -> bool:
    """Check if domain has valid MX records."""
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        result = len(answers) > 0
    except Exception:
        # Fallback: check A record (some domains receive email without MX)
        try:
            dns.resolver.resolve(domain, "A", lifetime=5)
            result = True
        except Exception:
            result = False
    _mx_cache[domain] = result
    return result


def is_junk(email: str) -> Optional[str]:
    """Return reason if email is junk, None if valid."""
    email_lower = email.lower().strip()

    if email_lower in JUNK_EMAILS:
        return "known_junk"

    domain = email_lower.split("@")[-1] if "@" in email_lower else ""

    for jd in JUNK_DOMAINS:
        if domain == jd:
            return f"junk_domain:{jd}"

    for jd in AGENCY_DOMAINS:
        if domain == jd:
            return f"agency:{jd}"

    for pattern in JUNK_PATTERNS:
        if pattern.search(email_lower):
            return "junk_pattern"

    if not EMAIL_REGEX.match(email_lower):
        return "invalid_format"

    return None


def validate_email(email: str) -> dict:
    """Full validation: junk check + format + MX."""
    email = email.strip()
    result = {"email": email, "valid": False, "reason": ""}

    # Junk check
    junk_reason = is_junk(email)
    if junk_reason:
        result["reason"] = junk_reason
        return result

    # MX check
    domain = email.split("@")[-1]
    if not check_mx(domain):
        result["reason"] = "no_mx_record"
        return result

    result["valid"] = True
    result["reason"] = "ok"
    return result


def main():
    input_path = os.path.join(OUTPUT_DIR, "all_hospitals_with_email.csv")
    output_valid = os.path.join(OUTPUT_DIR, "all_hospitals_valid_email.csv")
    output_rejected = os.path.join(OUTPUT_DIR, "rejected_emails.csv")

    df = pd.read_csv(input_path, dtype=str).fillna("")
    print(f"Input: {len(df)} hospitals with email")

    # Collect all unique emails for batch validation
    all_emails = set()
    for _, row in df.iterrows():
        for e in row["email"].split(","):
            e = e.strip()
            if e:
                all_emails.add(e)

    print(f"Unique emails to validate: {len(all_emails)}")

    # Validate all emails (MX checks in parallel)
    email_results = {}

    # First pass: junk check (fast, no network)
    to_mx_check = []
    for email in all_emails:
        junk_reason = is_junk(email)
        if junk_reason:
            email_results[email] = {"valid": False, "reason": junk_reason}
        else:
            to_mx_check.append(email)

    junk_count = len(all_emails) - len(to_mx_check)
    print(f"Junk removed: {junk_count}")
    print(f"MX check needed: {len(to_mx_check)}")

    # Collect unique domains for MX check
    domains = set(e.split("@")[-1] for e in to_mx_check)
    print(f"Unique domains to check: {len(domains)}")

    # Parallel MX check
    domain_valid = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_mx, d): d for d in domains}
        done = 0
        for future in as_completed(futures):
            d = futures[future]
            domain_valid[d] = future.result()
            done += 1
            if done % 50 == 0:
                print(f"  MX checked: {done}/{len(domains)}")

    mx_invalid = sum(1 for v in domain_valid.values() if not v)
    print(f"Domains with no MX: {mx_invalid}")

    # Apply MX results
    for email in to_mx_check:
        domain = email.split("@")[-1]
        if domain_valid.get(domain, False):
            email_results[email] = {"valid": True, "reason": "ok"}
        else:
            email_results[email] = {"valid": False, "reason": "no_mx_record"}

    # Apply to dataframe: keep only valid emails per row
    rejected_rows = []
    valid_count = 0
    cleaned_count = 0

    for idx, row in df.iterrows():
        original_emails = [e.strip() for e in row["email"].split(",") if e.strip()]
        valid_emails = []
        for e in original_emails:
            result = email_results.get(e, {"valid": False, "reason": "unknown"})
            if result["valid"]:
                valid_emails.append(e)
            else:
                rejected_rows.append({
                    "hospital_name": row.get("hospital_name", ""),
                    "email": e,
                    "reason": result["reason"],
                })

        df.at[idx, "email"] = ", ".join(valid_emails)
        if valid_emails:
            valid_count += 1
        if len(valid_emails) < len(original_emails):
            cleaned_count += 1

    # Save valid
    valid_df = df[df["email"].str.strip() != ""]
    valid_df.to_csv(output_valid, index=False, encoding="utf-8-sig")

    # Save rejected
    rejected_df = pd.DataFrame(rejected_rows)
    rejected_df.to_csv(output_rejected, index=False, encoding="utf-8-sig")

    print(f"\n=== Results ===")
    print(f"Original hospitals with email: {len(df)}")
    print(f"Hospitals with valid email: {valid_count}")
    print(f"Hospitals cleaned (some emails removed): {cleaned_count}")
    print(f"Rejected emails: {len(rejected_rows)}")
    print(f"\nRejection breakdown:")
    if rejected_rows:
        reasons = pd.DataFrame(rejected_rows)["reason"].value_counts()
        for reason, count in reasons.items():
            print(f"  {reason}: {count}")
    print(f"\nSaved valid: {output_valid}")
    print(f"Saved rejected: {output_rejected}")


if __name__ == "__main__":
    main()
