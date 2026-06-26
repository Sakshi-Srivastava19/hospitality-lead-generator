import os
import time
import requests
import pandas as pd

from price_extractor import get_booking_prices
from places_api import get_place_details
from property_type import get_property_type
from contact_page_scraper import scrape_contact_pages
from social_extractor import extract_social_links
from config import (
    CITY,
    MAX_HOTELS,
    PRICE_MIN,
    PRICE_MAX,
    OUTPUT_ALL_FILE,
    OUTPUT_PRICED_FILE,
    PLACES_REQUEST_TIMEOUT,
)

import os
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
_PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"


# ==================================
# HELPERS
# ==================================

def _search_hotel_place(name, city):
    """Search Google Places for a single hotel and return the first result dict."""
    if not GOOGLE_API_KEY:
        return None
    try:
        resp = requests.get(
            _PLACES_SEARCH_URL,
            params={"query": f"{name} {city}", "key": GOOGLE_API_KEY},
            timeout=PLACES_REQUEST_TIMEOUT,
        )
        data = resp.json()
        results = data.get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"    Places search error for '{name}': {e}")
        return None


def _enrich_hotel(name, city):
    """
    Look up a hotel by name+city in Google Places, then scrape its website.
    Returns a dict with all enrichment fields (all default to empty string).
    """
    enriched = {
        "PROPERTY TYPE": "",
        "LOCATION": "",
        "LOCATION TYPE": "",
        "CONTACT NO 1": "",
        "CONTACT NO 2": "",
        "CONTACT NO 3": "",
        "EMAIL 1": "",
        "EMAIL 2": "",
        "EMAIL 3": "",
        "RATING OUT OF 5": "",
        "REVIEW COUNT": "",
        "WEBSITE": "",
        "INSTAGRAM": "",
        "FACEBOOK": "",
        "LINKEDIN": "",
        "YOUTUBE": "",
        "TWITTER": "",
    }

    # ── Step 1: Google Places text search ─────────────────────────────────────
    place = _search_hotel_place(name, city)
    place_id = place.get("place_id") if place else None

    place_types_raw = ""
    website = ""

    if place_id:
        details_resp = get_place_details(place_id)
        details = details_resp.get("result", {})

        enriched["LOCATION"]      = details.get("formatted_address", "")
        enriched["RATING OUT OF 5"] = details.get("rating", "")
        enriched["REVIEW COUNT"]  = details.get("user_ratings_total", "")
        website                   = details.get("website", "")
        enriched["WEBSITE"]       = website

        # Phone from Places
        phone = details.get("formatted_phone_number", "")
        if phone:
            enriched["CONTACT NO 1"] = phone

        # Types for property classification
        place_types_raw = " ".join(details.get("types", []))

    # ── Step 2: Property type ──────────────────────────────────────────────────
    enriched["PROPERTY TYPE"] = get_property_type(
        website or "http://example.com",
        place_types_raw,
        hotel_name=name,
    )

    # Determine location type from Google types
    if "lodging" in place_types_raw:
        enriched["LOCATION TYPE"] = "Hotel"
    elif place_types_raw:
        enriched["LOCATION TYPE"] = place_types_raw.split()[0].replace("_", " ").title()

    # ── Step 3: Contact page scraping ─────────────────────────────────────────
    if website:
        try:
            contact_data = scrape_contact_pages(website)
            phones  = contact_data.get("phones", [])
            emails  = contact_data.get("emails", [])

            # Merge Places phone with scraped phones (dedup)
            all_phones = []
            if enriched["CONTACT NO 1"]:
                all_phones.append(enriched["CONTACT NO 1"])
            for p in phones:
                if p not in all_phones:
                    all_phones.append(p)

            enriched["CONTACT NO 1"] = all_phones[0] if len(all_phones) > 0 else ""
            enriched["CONTACT NO 2"] = all_phones[1] if len(all_phones) > 1 else ""
            enriched["CONTACT NO 3"] = all_phones[2] if len(all_phones) > 2 else ""

            enriched["EMAIL 1"] = emails[0] if len(emails) > 0 else ""
            enriched["EMAIL 2"] = emails[1] if len(emails) > 1 else ""
            enriched["EMAIL 3"] = emails[2] if len(emails) > 2 else ""
        except Exception as e:
            print(f"    Contact scrape error: {e}")

    # ── Step 4: Social links ───────────────────────────────────────────────────
    if website:
        try:
            social = extract_social_links(website)
            enriched["INSTAGRAM"] = social.get("Instagram", "")
            enriched["FACEBOOK"]  = social.get("Facebook", "")
            enriched["LINKEDIN"]  = social.get("LinkedIn", "")
            enriched["YOUTUBE"]   = social.get("YouTube", "")
            enriched["TWITTER"]   = social.get("Twitter", "")
        except Exception as e:
            print(f"    Social extract error: {e}")

    return enriched


# ==================================
# PHASE 1: SCRAPE BOOKING.COM
# ==================================

print("=" * 60)
print("PHASE 1 — Scraping Booking.com prices...")
print("=" * 60)
booking_prices = get_booking_prices(CITY)
print(f"Booking.com hotels found: {len(booking_prices)}\n")

# ==================================
# LOAD EXISTING RESULTS (dedup)
# ==================================

all_file = OUTPUT_ALL_FILE
os.makedirs(os.path.dirname(all_file), exist_ok=True)

existing_df    = pd.DataFrame()
existing_names = set()
sr_start       = 1

if os.path.exists(all_file):
    try:
        existing_df = pd.read_csv(all_file, encoding="utf-8-sig")
        existing_names = {
            str(row.get("NAME", "")).strip().lower()
            for _, row in existing_df.iterrows()
        }
        sr_start = len(existing_df) + 1
        print(f"Existing CSV: {len(existing_df)} leads already saved.")
        print(f"Will skip duplicates and continue from SR NO {sr_start}.")
    except Exception as e:
        print(f"Could not load existing CSV: {e} — starting fresh.")
else:
    print("No existing CSV found — starting fresh.")

new_hotels = {
    name: price
    for name, price in booking_prices.items()
    if name not in existing_names
}

print(f"\nNew hotels to process: {len(new_hotels)} "
      f"(skipped {len(booking_prices) - len(new_hotels)} already in CSV)\n")

# ==================================
# PHASE 2: ENRICH EACH NEW HOTEL
# ==================================

print("=" * 60)
print("PHASE 2 — Enriching new hotels (Places + website scraping)...")
print("=" * 60)

rows  = []
count = sr_start

for name, price_int in list(new_hotels.items())[:MAX_HOTELS]:

    display_name  = name.title()
    price_per_day = f"₹{price_int:,}"

    print(f"\n[{count}] {display_name}  →  {price_per_day}")

    enriched = _enrich_hotel(display_name, CITY)

    rows.append({
        "SR NO":           count,
        "NAME":            display_name,
        "PROPERTY TYPE":   enriched["PROPERTY TYPE"],
        "LOCATION":        enriched["LOCATION"],
        "CITY":            CITY,
        "CONTACT NO 1":    enriched["CONTACT NO 1"],
        "CONTACT NO 2":    enriched["CONTACT NO 2"],
        "CONTACT NO 3":    enriched["CONTACT NO 3"],
        "EMAIL 1":         enriched["EMAIL 1"],
        "EMAIL 2":         enriched["EMAIL 2"],
        "EMAIL 3":         enriched["EMAIL 3"],
        "RATING OUT OF 5": enriched["RATING OUT OF 5"],
        "REVIEW COUNT":    enriched["REVIEW COUNT"],
        "PRICE PER DAY":   price_per_day,
        "LOCATION TYPE":   enriched["LOCATION TYPE"],
        "WEBSITE":         enriched["WEBSITE"],
        "INSTAGRAM":       enriched["INSTAGRAM"],
        "FACEBOOK":        enriched["FACEBOOK"],
        "LINKEDIN":        enriched["LINKEDIN"],
        "YOUTUBE":         enriched["YOUTUBE"],
        "TWITTER":         enriched["TWITTER"],
    })

    count += 1
    time.sleep(0.3)   # small pause between Places API calls

# ==================================
# EXPORT
# ==================================

new_df = pd.DataFrame(rows)

if new_df.empty:
    print("\nNo new leads to add.")
else:
    print(f"\nNew leads this run: {len(new_df)}")

    if existing_df.empty:
        new_df.to_csv(all_file, index=False, encoding="utf-8-sig")
    else:
        new_df.to_csv(all_file, mode="a", index=False,
                      encoding="utf-8-sig", header=False)

    total_all = len(existing_df) + len(new_df)
    print(f"All Leads CSV ({total_all} total rows): {all_file}")

    # Price-filtered CSV — rebuilt from the full file each run
    full_df = pd.read_csv(all_file, encoding="utf-8-sig")
    full_df["PRICE_NUM"] = pd.to_numeric(
        full_df["PRICE PER DAY"]
        .astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False),
        errors="coerce",
    )
    priced_df = full_df[
        full_df["PRICE_NUM"].notna()
        & (full_df["PRICE_NUM"] >= PRICE_MIN)
        & (full_df["PRICE_NUM"] <= PRICE_MAX)
    ].drop(columns=["PRICE_NUM"])
    priced_df.to_csv(OUTPUT_PRICED_FILE, index=False, encoding="utf-8-sig")
    print(
        f"Priced Leads CSV ({len(priced_df)} rows, "
        f"₹{PRICE_MIN:,}–₹{PRICE_MAX:,}/night): {OUTPUT_PRICED_FILE}"
    )
