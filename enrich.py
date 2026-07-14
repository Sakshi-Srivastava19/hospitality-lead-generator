"""
enrich.py  —  Backfill empty detail columns for hotels already in the CSV.

Run this once (or re-run safely — it skips hotels that already have a LOCATION
or WEBSITE filled in, so no work is duplicated).

After updating the master (all-leads) CSV, this also rebuilds every
price-band CSV for the city (e.g. jaipur_hospitality_leads_600-1000.csv),
since those are just filtered snapshots of the master file and go stale
the moment the master file changes.
"""

import os
import re
import glob
import time
import requests
import pandas as pd
from dotenv import load_dotenv

from places_api import get_place_details
from property_type import get_property_type
from contact_page_scraper import scrape_contact_pages
from social_extractor import extract_social_links
from config import (
    CITY,
    OUTPUT_DIR,
    OUTPUT_ALL_FILE,
    PLACES_REQUEST_TIMEOUT,
)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
_PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

DETAIL_COLS = [
    "PROPERTY TYPE", "LOCATION", "CONTACT NO 1", "CONTACT NO 2", "CONTACT NO 3",
    "EMAIL 1", "EMAIL 2", "EMAIL 3", "RATING OUT OF 5", "REVIEW COUNT",
    "LOCATION TYPE", "WEBSITE", "INSTAGRAM", "FACEBOOK", "LINKEDIN", "YOUTUBE", "TWITTER",
]

# Matches the two band-filename shapes main.py produces:
#   ..._leads_15000-30000.csv   (fixed/quantile band)
#   ..._leads_60000+.csv        (open-ended top band)
_BAND_FILE_RE = re.compile(r"_leads_(\d+)(?:-(\d+)|\+)\.csv$")


def _search_hotel_place(name, city):
    if not GOOGLE_API_KEY:
        return None
    try:
        resp = requests.get(
            _PLACES_SEARCH_URL,
            params={"query": f"{name} {city}", "key": GOOGLE_API_KEY},
            timeout=PLACES_REQUEST_TIMEOUT,
        )
        results = resp.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"    Places search error: {e}")
        return None


def enrich_row(name, city):
    """Return a dict of enrichment values for one hotel."""
    out = {c: "" for c in DETAIL_COLS}

    place = _search_hotel_place(name, city)
    place_id = place.get("place_id") if place else None
    website = ""
    place_types_raw = ""

    if place_id:
        details = get_place_details(place_id).get("result", {})
        out["LOCATION"]        = details.get("formatted_address", "")
        out["RATING OUT OF 5"] = details.get("rating", "")
        out["REVIEW COUNT"]    = details.get("user_ratings_total", "")
        website                = details.get("website", "")
        out["WEBSITE"]         = website
        phone                  = details.get("formatted_phone_number", "")
        if phone:
            out["CONTACT NO 1"] = phone
        place_types_raw = " ".join(details.get("types", []))

    out["PROPERTY TYPE"] = get_property_type(
        website or "http://example.com",
        place_types_raw,
        hotel_name=name,
    )
    if "lodging" in place_types_raw:
        out["LOCATION TYPE"] = "Hotel"
    elif place_types_raw:
        out["LOCATION TYPE"] = place_types_raw.split()[0].replace("_", " ").title()

    if website:
        try:
            contact = scrape_contact_pages(website)
            phones  = contact.get("phones", [])
            emails  = contact.get("emails", [])

            all_phones = []
            if out["CONTACT NO 1"]:
                all_phones.append(out["CONTACT NO 1"])
            for p in phones:
                if p not in all_phones:
                    all_phones.append(p)

            out["CONTACT NO 1"] = all_phones[0] if len(all_phones) > 0 else ""
            out["CONTACT NO 2"] = all_phones[1] if len(all_phones) > 1 else ""
            out["CONTACT NO 3"] = all_phones[2] if len(all_phones) > 2 else ""

            out["EMAIL 1"] = emails[0] if len(emails) > 0 else ""
            out["EMAIL 2"] = emails[1] if len(emails) > 1 else ""
            out["EMAIL 3"] = emails[2] if len(emails) > 2 else ""
        except Exception as e:
            print(f"    Contact scrape error: {e}")

        try:
            social = extract_social_links(website)
            out["INSTAGRAM"] = social.get("Instagram", "")
            out["FACEBOOK"]  = social.get("Facebook", "")
            out["LINKEDIN"]  = social.get("LinkedIn", "")
            out["YOUTUBE"]   = social.get("YouTube", "")
            out["TWITTER"]   = social.get("Twitter", "")
        except Exception as e:
            print(f"    Social extract error: {e}")

    return out


def _is_empty(row, cols):
    """True if all given columns are blank/NaN for this row."""
    for c in cols:
        val = str(row.get(c, "")).strip()
        if val and val.lower() not in ("nan", "none"):
            return False
    return True


def _rebuild_band_files(df, city):
    """Rebuild every existing price-band CSV for this city from the
    (now-enriched) master dataframe. Band files are just filtered
    snapshots of the master file, so they go stale whenever it changes —
    this keeps them in sync regardless of what config.py's current
    PRICE_BAND_EDGES happens to be set to right now."""
    df = df.copy()
    df["PRICE_NUM"] = pd.to_numeric(
        df["PRICE PER DAY"]
        .astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False),
        errors="coerce",
    )

    pattern = os.path.join(OUTPUT_DIR, f"{city.lower()}_hospitality_leads_*.csv")
    rebuilt = 0
    for path in glob.glob(pattern):
        if path.endswith("_all.csv"):
            continue
        m = _BAND_FILE_RE.search(path)
        if not m:
            continue
        low = int(m.group(1))
        high = int(m.group(2)) if m.group(2) else float("inf")

        mask = (df["PRICE_NUM"] >= low) & (df["PRICE_NUM"] < high)
        band_df = df[mask].drop(columns=["PRICE_NUM"])
        band_df.to_csv(path, index=False, encoding="utf-8-sig")
        rebuilt += 1
        print(f"  Rebuilt {os.path.basename(path)}: {len(band_df)} rows")

    if rebuilt == 0:
        print("  No existing price-band CSVs found for this city to rebuild.")
    else:
        print(f"\nRebuilt {rebuilt} price-band CSV(s) with the refreshed data.")


def run_enrich():
    if not os.path.exists(OUTPUT_ALL_FILE):
        print(f"No CSV found at {OUTPUT_ALL_FILE} — nothing to enrich.")
        return

    df = pd.read_csv(OUTPUT_ALL_FILE, encoding="utf-8-sig")
    df = df.fillna("")

    # Only enrich rows where key detail columns are all empty
    check_cols = ["LOCATION", "WEBSITE", "RATING OUT OF 5"]
    needs_enrich = df[df.apply(lambda r: _is_empty(r, check_cols), axis=1)]

    print(f"Total rows: {len(df)}  |  Need enrichment: {len(needs_enrich)}")
    if needs_enrich.empty:
        print("All rows already have details — nothing to do.")
        # Still rebuild band files in case they were generated before an
        # earlier enrichment run and never refreshed.
        _rebuild_band_files(df, CITY)
        return

    updated = 0
    for idx, row in needs_enrich.iterrows():
        name = str(row["NAME"]).strip()
        city = str(row.get("CITY", CITY)).strip() or CITY
        print(f"\n[{idx + 1}] Enriching: {name}")

        enriched = enrich_row(name, city)
        for col, val in enriched.items():
            df.at[idx, col] = val

        updated += 1
        time.sleep(0.3)

    df.to_csv(OUTPUT_ALL_FILE, index=False, encoding="utf-8-sig")
    print(f"\nEnriched {updated} hotels. Saved to {OUTPUT_ALL_FILE}")

    print("\nRebuilding price-band CSVs...")
    _rebuild_band_files(df, CITY)


if __name__ == "__main__":
    run_enrich()