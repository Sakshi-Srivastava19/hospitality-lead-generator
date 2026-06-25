import os
import pandas as pd
from rapidfuzz import fuzz
from places_api import (
    search_places,
    get_place_details
)

from contact_page_scraper import (
    scrape_contact_pages
)

from social_extractor import (
    extract_social_links
)

from property_type import (
    get_property_type
)


from price_extractor import get_mmt_prices

import re

# ==================================
# CONFIGURATION
# ==================================

CITY = "Lonavala"

QUERY = [
    f"Hotels in {CITY}",
    f"Resorts in {CITY}",
    f"Villas in {CITY}",
    f"Homestays in {CITY}",
    f"Farmhouses in {CITY}",
    f"Lodges in {CITY}",
]

MAX_HOTELS = 100

# Words that appear across most hotel names and add no matching signal.
# City name is excluded so it doesn't skew fuzzy scores.
GENERIC_WORDS = {
    "the", "a", "an", "in", "on", "by", "near", "and",
    "hotel", "hotels", "resort", "brand", "accor", "business",
    CITY.lower(),
}


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
# SEARCH HOTELS
# ==================================

results = search_places(QUERY)

hotels = results.get("results", [])

print("\nHOTELS RETURNED BY GOOGLE:\n")

for i, hotel in enumerate(hotels, start=1):
    print(f"{i}. {hotel.get('name')}")

rows = []

print(
    f"\nProcessing {min(MAX_HOTELS, len(hotels))} hotels...\n"
)

# ==================================
# LOOP HOTELS
# ==================================

for count, place in enumerate(
    hotels[:MAX_HOTELS],
    start=1
):

    print(f"\nHotel {count}/{MAX_HOTELS}")

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

                if best_score >= 80:

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

df = pd.DataFrame(rows)

print("\nPreview:\n")

print(df.head())

os.makedirs("output", exist_ok=True)

# ==================================
# EXPORT 1: ALL LEADS (no price filter)
# ==================================

all_file = f"output/{CITY.lower()}_hospitality_leads_all.csv"
df.to_csv(all_file, index=False, encoding="utf-8-sig")
print(f"\nAll Leads CSV ({len(df)} rows):\n{all_file}")

# ==================================
# EXPORT 2: PRICE-MATCHED LEADS ONLY
# Keeps only rows where a price was found on MMT.
# ==================================

df["PRICE_NUM"] = (
    df["PRICE PER DAY"]
    .astype(str)
    .str.replace("₹", "", regex=False)
    .str.replace(",", "", regex=False)
)
df["PRICE_NUM"] = pd.to_numeric(df["PRICE_NUM"], errors="coerce")

priced_df = df[df["PRICE_NUM"].notna()].drop(columns=["PRICE_NUM"])

priced_file = f"output/{CITY.lower()}_hospitality_leads_priced.csv"
priced_df.to_csv(priced_file, index=False, encoding="utf-8-sig")
print(f"Priced Leads CSV ({len(priced_df)} rows):\n{priced_file}")

# Clean up temp column from original df
df.drop(columns=["PRICE_NUM"], inplace=True, errors="ignore")