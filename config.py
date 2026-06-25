# =============================================================================
# config.py  —  All inputs and parameters for the lead-gen pipeline
# Change values here; no need to touch any other file.
# =============================================================================

# ── TARGET CITY ───────────────────────────────────────────────────────────────

CITY = "Lonavala"

# ── GOOGLE PLACES SEARCH ─────────────────────────────────────────────────────

# Search queries sent to Google Places (one API call per term).
# Add or remove terms to widen/narrow the property types collected.
SEARCH_QUERIES = [
    f"Hotels in {CITY}",
    f"Resorts in {CITY}",
    f"Villas in {CITY}",
    f"Homestays in {CITY}",
    f"Farmhouses in {CITY}",
    f"Lodges in {CITY}",
]

# Maximum hotels to process per pipeline run.
MAX_HOTELS = 500

# Max result pages per Google Places query (1 page = 20 results, max 3 pages).
PLACES_MAX_PAGES = 3

# Seconds to wait before requesting the next Places page token.
# Google activates tokens asynchronously — must be ≥3 s, 4 s is safer.
PLACES_PAGE_DELAY = 4

# HTTP request timeout for Google Places API calls (seconds).
PLACES_REQUEST_TIMEOUT = 15

# ── BOOKING.COM PRICE EXTRACTION ─────────────────────────────────────────────

# Check-in offset from today (days). 1 = tomorrow.
CHECKIN_DAYS_OFFSET  = 1
# Check-out offset from today (days). 2 = day after tomorrow.
CHECKOUT_DAYS_OFFSET = 2

# Room configuration sent to Booking.com.
ROOM_COUNT   = 1
ADULTS_COUNT = 2
CHILD_COUNT  = 0

# How many Booking.com result pages to paginate through.
# Each page shows ~25 hotels. 10 pages covers ~250 hotels.
BOOKING_MAX_PAGES = 10

# Seconds to wait after page load / after clicking "Next page".
BOOKING_PAGE_LOAD_WAIT = 6

# Page-Down keystrokes per page to trigger lazy-loaded hotel cards.
BOOKING_MAX_SCROLLS = 6

# Seconds between each Page-Down keystroke.
BOOKING_SCROLL_WAIT = 0.8

# ── PRICE FILTER ─────────────────────────────────────────────────────────────

# Hotels outside this nightly price range (₹) are excluded from the
# _priced CSV. They still appear in the _all CSV.
# Set PRICE_MIN = 0 and PRICE_MAX = 9_999_999 to disable filtering.
PRICE_MIN =     1_000   # ₹ per night
PRICE_MAX =    50_000   # ₹ per night

# ── FUZZY NAME MATCHING ───────────────────────────────────────────────────────

# Minimum token_sort_ratio score (0–100) to accept a Booking↔Google name match.
FUZZY_MATCH_THRESHOLD = 80

# Words stripped from hotel names before fuzzy comparison.
FUZZY_STOP_WORDS = {
    "the", "a", "an", "in", "on", "by", "near", "and",
    "hotel", "hotels", "resort", "brand", "accor", "business",
}

# ── CONTACT PAGE SCRAPING ─────────────────────────────────────────────────────

# Sub-pages appended to each hotel's base URL when hunting for contact info.
CONTACT_PAGES = [
    "",
    "/contact",
    "/contact-us",
    "/about",
    "/about-us",
]

# Seconds before a contact-page HTTP request times out.
CONTACT_REQUEST_TIMEOUT = 10

# User-Agent sent with contact-page requests.
CONTACT_USER_AGENT = "Mozilla/5.0"

# ── OUTPUT ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = "output"

# All leads (no price filter) — new rows are appended on each run.
OUTPUT_ALL_FILE    = f"{OUTPUT_DIR}/{CITY.lower()}_hospitality_leads_all.csv"

# Price-matched leads within PRICE_MIN–PRICE_MAX — rebuilt on each run.
OUTPUT_PRICED_FILE = f"{OUTPUT_DIR}/{CITY.lower()}_hospitality_leads_priced.csv"
