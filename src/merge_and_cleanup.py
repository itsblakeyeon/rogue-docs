"""Merge HIRA + Naver data and run cleanup."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from cleanup import BLOCKED_EMAIL_DOMAINS, BLOCKED_URL_DOMAINS, PORTAL_EMAILS, is_blocked_email, is_blocked_url
from config import OUTPUT_DIR


def main():
    hira_clean = os.path.join(OUTPUT_DIR, "step3_hospitals_final_clean.csv")
    naver_email = os.path.join(OUTPUT_DIR, "naver_hospitals_with_email.csv")

    dfs = []

    if os.path.exists(hira_clean):
        hdf = pd.read_csv(hira_clean, dtype=str).fillna("")
        hdf["source"] = "hira"
        print(f"HIRA: {len(hdf)} rows, {len(hdf[hdf['email'].str.strip() != ''])} with email")
        dfs.append(hdf)

    if os.path.exists(naver_email):
        ndf = pd.read_csv(naver_email, dtype=str).fillna("")
        if "source" not in ndf.columns:
            ndf["source"] = "naver"
        print(f"Naver: {len(ndf)} rows, {len(ndf[ndf['email'].str.strip() != ''])} with email")
        dfs.append(ndf)

    if not dfs:
        print("No data files found.")
        sys.exit(1)

    # Merge
    combined = pd.concat(dfs, ignore_index=True)

    # Deduplicate by hospital_name + address (keep first = HIRA priority)
    combined["_dedup_key"] = combined["hospital_name"].str.strip() + "|" + combined["address"].str.strip()
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=["_dedup_key"], keep="first")
    combined = combined.drop(columns=["_dedup_key"])
    print(f"\nDeduplication: {before_dedup} -> {len(combined)} ({before_dedup - len(combined)} removed)")

    # Cleanup: blocked emails
    blocked_email_count = 0
    for idx, row in combined.iterrows():
        emails = str(row.get("email", "")).strip()
        if not emails:
            continue
        email_list = [e.strip() for e in emails.split(",")]
        clean_emails = [e for e in email_list if e and not is_blocked_email(e)]
        if len(clean_emails) < len(email_list):
            blocked_email_count += len(email_list) - len(clean_emails)
        combined.at[idx, "email"] = ", ".join(clean_emails)

    # Cleanup: blocked URLs
    blocked_url_count = 0
    for idx, row in combined.iterrows():
        url = str(row.get("website", "")).strip()
        if url and is_blocked_url(url):
            combined.at[idx, "website"] = ""
            combined.at[idx, "email"] = ""
            blocked_url_count += 1

    # Save all
    all_output = os.path.join(OUTPUT_DIR, "all_hospitals_merged.csv")
    combined.to_csv(all_output, index=False, encoding="utf-8-sig")

    # Save email-only
    email_df = combined[combined["email"].str.strip() != ""]
    email_output = os.path.join(OUTPUT_DIR, "all_hospitals_with_email.csv")
    email_df.to_csv(email_output, index=False, encoding="utf-8-sig")

    print(f"\n=== Final Results ===")
    print(f"Total hospitals: {len(combined)}")
    print(f"Blocked portal emails removed: {blocked_email_count}")
    print(f"Blocked portal URLs cleared: {blocked_url_count}")
    print(f"With email: {len(email_df)}")
    print(f"  - from HIRA: {len(email_df[email_df['source'] == 'hira'])}")
    print(f"  - from Naver: {len(email_df[email_df['source'] == 'naver'])}")
    print(f"\nBy department:")
    if "specialty" in email_df.columns:
        print(email_df["specialty"].value_counts().to_string())
    print(f"\nBy region:")
    if "sido" in email_df.columns:
        print(email_df["sido"].value_counts().to_string())
    print(f"\nSaved: {all_output}")
    print(f"Saved: {email_output}")


if __name__ == "__main__":
    main()
