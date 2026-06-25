import os
import pandas as pd
from price_extractor import get_booking_prices
from config import (
    CITY,
    MAX_HOTELS,
    PRICE_MIN,
    PRICE_MAX,
    OUTPUT_ALL_FILE,
    OUTPUT_PRICED_FILE,
)

# ==================================
# SCRAPE BOOKING.COM
# ==================================

print("Scraping Booking.com prices...")
booking_prices = get_booking_prices(CITY)
print(f"Booking.com hotels found: {len(booking_prices)}\n")

# ==================================
# LOAD EXISTING RESULTS (dedup)
# ==================================

all_file = OUTPUT_ALL_FILE
os.makedirs(os.path.dirname(all_file), exist_ok=True)

existing_df   = pd.DataFrame()
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
        print(f"Existing CSV found: {len(existing_df)} leads already saved.")
        print(f"Will skip duplicates and continue from SR NO {sr_start}.")
    except Exception as e:
        print(f"Could not load existing CSV: {e} — starting fresh.")
else:
    print("No existing CSV found — starting fresh.")

# ==================================
# BUILD ROWS
# ==================================

rows  = []
count = sr_start

new_hotels = {
    name: price
    for name, price in booking_prices.items()
    if name not in existing_names
}

print(f"\nNew hotels to add: {len(new_hotels)} "
      f"(skipped {len(booking_prices) - len(new_hotels)} already in CSV)\n")

for name, price_int in list(new_hotels.items())[:MAX_HOTELS]:

    display_name  = name.title()
    price_per_day = f"₹{price_int:,}"

    print(f"  [{count}] {display_name}  →  {price_per_day}")

    rows.append({
        "SR NO":          count,
        "NAME":           display_name,
        "PROPERTY TYPE":  "",
        "LOCATION":       "",
        "CITY":           CITY,
        "CONTACT NO 1":   "",
        "CONTACT NO 2":   "",
        "CONTACT NO 3":   "",
        "EMAIL 1":        "",
        "EMAIL 2":        "",
        "EMAIL 3":        "",
        "RATING OUT OF 5": "",
        "REVIEW COUNT":   "",
        "PRICE PER DAY":  price_per_day,
        "LOCATION TYPE":  "",
        "WEBSITE":        "",
        "INSTAGRAM":      "",
        "FACEBOOK":       "",
        "LINKEDIN":       "",
        "YOUTUBE":        "",
        "TWITTER":        "",
    })

    count += 1

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
