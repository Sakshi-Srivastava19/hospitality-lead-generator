import os
import re
import pandas as pd
from rapidfuzz import fuzz
from places_api import search_places, get_place_details
from contact_page_scraper import scrape_contact_pages
from social_extractor import extract_social_links
from property_type import get_property_type
from price_extractor import get_mmt_prices
from config import (
    CITY,
    SEARCH_QUERIES,
    MAX_HOTELS,
    FUZZY_MATCH_THRESHOLD,
    FUZZY_STOP_WORDS,
    OUTPUT_ALL_FILE,
    OUTPUT_PRICED_FILE,
)

GENERIC_WORDS = FUZZY_STOP_WORDS | {CITY.lower()}


def normalize_hotel_name(name, extra_stop_words=None):
    """Return a cleaned token string suitable for fuzzy name matching."""
    stop = GENERIC_WORDS | (extra_stop_words or set())

    name = name.lower()
    name = re.sub(r"\(.*?\)", " ", name)        # drop parentheticals
    name = re.sub(r"[^a-z0-9\s]", " ", name)   # drop punctuation

    tokens = [t for t in name.split() if t and t not in stop]
    return " ".join(tokens)


print("Loading MMT prices...")

mmt_prices = get_mmt_prices(CITY)

print("MMT hotels found:", len(mmt_prices))

# Show exactly what MMT returned so name-matching issues are visible
for _mmt_name, _mmt_price in mmt_prices.items():
    print("  MMT:", _mmt_name, "=>", _mmt_price)
# ==================================
# LOAD EXISTING RESULTS (dedup support)
# ==================================

all_file = OUTPUT_ALL_FILE
os.makedirs(os.path.dirname(all_file), exist_ok=True)

existing_df   = pd.DataFrame()
existing_keys = set()          # set of (name_lower, website_lower) already saved
sr_start      = 1             # next SR NO to use

if os.path.exists(all_file):
    try:
        existing_df = pd.read_csv(all_file, encoding="utf-8-sig")
        for _, row in existing_df.iterrows():
            name    = str(row.get("NAME",    "")).strip().lower()
            website = str(row.get("WEBSITE", "")).strip().lower()
            existing_keys.add((name, website))
        sr_start = len(existing_df) + 1
        print(f"\nExisting CSV found: {len(existing_df)} leads already saved.")
        print(f"Will skip duplicates and continue from SR NO {sr_start}.")
    except Exception as e:
        print(f"Could not load existing CSV: {e} — starting fresh.")
else:
    print("\nNo existing CSV found — starting fresh.")

# ==================================
# SEARCH HOTELS
# ==================================

results = search_places(SEARCH_QUERIES)

hotels = results.get("results", [])

print("\nHOTELS RETURNED BY GOOGLE:\n")

for i, hotel in enumerate(hotels, start=1):
    print(f"{i}. {hotel.get('name')}")

# Filter out hotels already in the existing CSV
new_hotels = []
for place in hotels:
    name    = place.get("name", "").strip().lower()
    # website not known yet at this stage — use place_id as a proxy key too
    place_id = place.get("place_id", "")
    # Check by name only at this stage; website checked after details fetch
    if not any(name == k[0] for k in existing_keys):
        new_hotels.append(place)

print(f"\nNew hotels to process: {len(new_hotels)} "
      f"(skipped {len(hotels) - len(new_hotels)} already in CSV)")

rows = []

to_process = new_hotels[:MAX_HOTELS]
print(f"Processing {len(to_process)} hotels...\n")

# ==================================
# LOOP HOTELS
# ==================================

for count, place in enumerate(
    to_process,
    start=sr_start
):

    print(f"\nHotel {count - sr_start + 1}/{len(to_process)}")

    try:

        place_id = place["place_id"]

        details = get_place_details(
            place_id
        )

        result = details.get(
            "result",
            {}
        )

        name = result.get(
            "name",
            ""
        )

        address = result.get(
            "formatted_address",
            ""
        )

        website = result.get(
            "website",
            ""
        )

        rating = result.get(
            "rating",
            0
        )

        reviews = result.get(
            "user_ratings_total",
            0
        )

        location_type = ", ".join(
            result.get(
                "types",
                []
            )
        )

        city = ""

        try:

            parts = address.split(",")

            if len(parts) >= 3:
                city = parts[-3].strip()

        except:
            pass

        emails = []
        phones = []

        socials = {
            "Instagram": "",
            "Facebook": "",
            "LinkedIn": "",
            "YouTube": "",
            "Twitter": ""
        }

        property_type = ""
        price_per_day = ""

        # ==========================
        # WEBSITE SCRAPING
        # ==========================

        if website:

            print(
                f"Scraping Website: {website}"
            )

            try:

                contact_data = (
                    scrape_contact_pages(
                        website
                    )
                )

                emails = contact_data.get(
                    "emails",
                    []
                )

                phones = contact_data.get(
                    "phones",
                    []
                )

                print(
                    f"Emails Found: {len(emails)}"
                )

                print(
                    f"Phones Found: {len(phones)}"
                )

            except Exception as e:

                print(
                    "Contact Page Error:",
                    e
                )

            try:

                socials = (
                    extract_social_links(
                        website
                    )
                )

            except Exception as e:

                print(
                    "Social Error:",
                    e
                )

            try:

                property_type = get_property_type(
                    website,
                    ", ".join(result.get("types", [])),
                    result.get("name", "")
                )

            except Exception as e:

                print(
                    "Property Type Error:",
                    e
                )

            try:

                best_score = 0
                best_price = ""

                city_stop = {CITY.lower()}
                google_norm = normalize_hotel_name(name, city_stop)

                for mmt_name, mmt_price in mmt_prices.items():

                    mmt_norm = normalize_hotel_name(mmt_name, city_stop)

                    # skip if either name is all generic words - an empty
                    # string would otherwise score 100 against another empty
                    if not google_norm or not mmt_norm:
                        continue

                    # token_sort_ratio penalises extra distinctive words
                    # (e.g. "hydel park" vs "park"), which token_set_ratio
                    # wrongly rewarded - that caused every "park" hotel to
                    # grab The Park's price.
                    score = fuzz.token_sort_ratio(
                        google_norm,
                        mmt_norm
                    )

                    if score > best_score:

                        best_score = score
                        best_price = mmt_price

                if best_score >= FUZZY_MATCH_THRESHOLD:

                    price_per_day = best_price

                    print(
                        f"PRICE MATCHED: {name} -> {best_price} (Score: {best_score})"
                    )

                else:

                    price_per_day = ""

                    print(
                        f"NO PRICE MATCH: {name} (Best Score: {best_score})"
                    )

            except Exception as e:

                print(
                    "Price Error:",
                    e
                )

        # ==========================
        # SAVE ROW
        # ==========================

        rows.append({

            "SR NO": count,

            "NAME": name,

            "PROPERTY TYPE":
            property_type,

            "LOCATION":
            address,

            "CITY":
            city,

            "CONTACT NO 1":
            result.get(
                "formatted_phone_number",
                ""
            ),

            "CONTACT NO 2":
            phones[0]
            if len(phones) > 0
            else "",

            "CONTACT NO 3":
            phones[1]
            if len(phones) > 1
            else "",

            "EMAIL 1":
            emails[0]
            if len(emails) > 0
            else "",

            "EMAIL 2":
            emails[1]
            if len(emails) > 1
            else "",

            "EMAIL 3":
            emails[2]
            if len(emails) > 2
            else "",

            "RATING OUT OF 5":
            rating,

            "REVIEW COUNT":
            reviews,

        

            "PRICE PER DAY":
            price_per_day,

            "LOCATION TYPE":
            location_type,

            "WEBSITE":
            website,

            "INSTAGRAM":
            socials.get(
                "Instagram",
                ""
            ),

            "FACEBOOK":
            socials.get(
                "Facebook",
                ""
            ),

            "LINKEDIN":
            socials.get(
                "LinkedIn",
                ""
            ),

            "YOUTUBE":
            socials.get(
                "YouTube",
                ""
            ),

            "TWITTER":
            socials.get(
                "Twitter",
                ""
            )

        })

    except Exception as e:

        print(
            f"Hotel Failed: {e}"
        )

        continue

# ==================================
# DATAFRAME
# ==================================

new_df = pd.DataFrame(rows)

if new_df.empty:
    print("\nNo new leads to add.")
else:
    print(f"\nNew leads this run: {len(new_df)}")
    print(new_df[["SR NO", "NAME", "WEBSITE"]].head())

    # ── EXPORT 1: ALL LEADS — append to existing CSV ──────────────────────
    priced_file = OUTPUT_PRICED_FILE

    if existing_df.empty:
        # First run — write header
        new_df.to_csv(all_file, index=False, encoding="utf-8-sig")
    else:
        # Subsequent run — append without repeating the header
        new_df.to_csv(all_file, mode="a", index=False,
                      encoding="utf-8-sig", header=False)

    total_all = len(existing_df) + len(new_df)
    print(f"\nAll Leads CSV ({total_all} total rows):\n{all_file}")

    # ── EXPORT 2: PRICE-MATCHED LEADS — rebuild from full CSV ─────────────
    # Re-read the full file so priced CSV always reflects cumulative data.
    full_df = pd.read_csv(all_file, encoding="utf-8-sig")
    full_df["PRICE_NUM"] = (
        full_df["PRICE PER DAY"]
        .astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    full_df["PRICE_NUM"] = pd.to_numeric(full_df["PRICE_NUM"], errors="coerce")
    priced_df = full_df[full_df["PRICE_NUM"].notna()].drop(columns=["PRICE_NUM"])
    priced_df.to_csv(priced_file, index=False, encoding="utf-8-sig")
    print(f"Priced Leads CSV ({len(priced_df)} rows):\n{priced_file}")