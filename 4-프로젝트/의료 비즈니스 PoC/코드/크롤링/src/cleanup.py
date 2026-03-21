"""Clean up crawled email results — remove false positives."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from config import OUTPUT_DIR

# Emails from portal sites (not actual hospital emails)
PORTAL_EMAILS = {
    "cs@cashdoc.me",
    "answer@mcircle.biz",
    "example@email.com",
    "noreply@",
    "webmaster@",
    "admin@medinavi.co.kr",
}

# Email domain blocklist (portal/3rd party sites, hosting, platform)
BLOCKED_EMAIL_DOMAINS = [
    # 의료 포털
    "cashdoc.me",
    "mcircle.biz",
    "medinavi.co.kr",
    "pervsi.com",
    "goodoc.co.kr",
    "hidoc.co.kr",
    "ayo.pe.kr",
    "march14th.net",
    "yeoshin.co.kr",
    "doctornow.co.kr",
    # 호스팅/인프라
    "gabia.com",
    "sentry.io",
    "sentry.wixpress.com",
    "sentry-next.wixpress.com",
    "o37417.ingest.sentry.io",
    # 플랫폼/서비스
    "interactivy.com",
    "daangn.com",
    "daangnservice.com",
    "bbgnetworks.com",
    "domainagents.com",
    "director-holdings.com",
    "anybuild.co.kr",
    "fastlane.kr",
    "k-info.me",
    "madeinreal.com",
    "0000.co.kr",
    # 더미/테스트
    "email.com",
    "example.com",
    "test.com",
    "company.com",
]

# URL blocklist (portal sites that aren't hospital websites)
BLOCKED_URL_DOMAINS = [
    "cashdoc.me",
    "medinavi.co.kr",
    "pervsi.com",
    "goodoc.co.kr",
    "hidoc.co.kr",
    "ayo.pe.kr",
    "march14th.net",
]

# Institution types to exclude
EXCLUDED_TYPES = ["종합병원", "상급종합병원"]


def is_blocked_email(email: str) -> bool:
    """Check if email is from a blocked domain or is a known portal email."""
    email = email.strip().lower()
    if email in PORTAL_EMAILS:
        return True
    for domain in BLOCKED_EMAIL_DOMAINS:
        if email.endswith(f"@{domain}"):
            return True
    return False


def is_blocked_url(url: str) -> bool:
    """Check if URL is from a blocked portal domain."""
    url = str(url).strip().lower()
    for domain in BLOCKED_URL_DOMAINS:
        if domain in url:
            return True
    return False


def main():
    final_csv = os.path.join(OUTPUT_DIR, "step3_hospitals_final.csv")
    df = pd.read_csv(final_csv, dtype=str)
    df = df.fillna("")

    total_before = len(df)
    emails_before = len(df[df["email"].str.strip() != ""])

    # 1. Remove excluded institution types
    excluded_mask = df["institution_type"].isin(EXCLUDED_TYPES)
    excluded_count = excluded_mask.sum()
    df = df[~excluded_mask]

    # 2. Clear emails from blocked domains
    blocked_email_count = 0
    for idx, row in df.iterrows():
        emails = str(row["email"]).strip()
        if not emails:
            continue
        # Filter each email in comma-separated list
        email_list = [e.strip() for e in emails.split(",")]
        clean_emails = [e for e in email_list if e and not is_blocked_email(e)]
        if len(clean_emails) < len(email_list):
            blocked_email_count += len(email_list) - len(clean_emails)
        df.at[idx, "email"] = ", ".join(clean_emails)

    # 3. Clear URLs from blocked portal domains
    blocked_url_count = 0
    for idx, row in df.iterrows():
        url = str(row["website"]).strip()
        if url and is_blocked_url(url):
            df.at[idx, "website"] = ""
            df.at[idx, "email"] = ""  # email from portal URL is invalid too
            blocked_url_count += 1

    # Save cleaned results
    clean_final = os.path.join(OUTPUT_DIR, "step3_hospitals_final_clean.csv")
    df.to_csv(clean_final, index=False, encoding="utf-8-sig")

    # Save email-only filtered
    email_df = df[df["email"].str.strip() != ""]
    clean_email = os.path.join(OUTPUT_DIR, "hospitals_with_email_clean.csv")
    email_df.to_csv(clean_email, index=False, encoding="utf-8-sig")

    emails_after = len(email_df)

    print(f"=== Cleanup Results ===")
    print(f"Total before: {total_before}")
    print(f"Excluded institution types removed: {excluded_count}")
    print(f"Blocked portal URLs cleared: {blocked_url_count}")
    print(f"Blocked portal emails removed: {blocked_email_count}")
    print(f"Emails before cleanup: {emails_before}")
    print(f"Emails after cleanup: {emails_after}")
    print(f"Saved: {clean_final}")
    print(f"Saved: {clean_email}")


if __name__ == "__main__":
    main()
