# =============================================================================
# config.py  —  All inputs and parameters for the lead-gen pipeline
# Change values here; no need to touch any other file.
# =============================================================================

# ── TARGET CITY ───────────────────────────────────────────────────────────────

CITY = "Jaipur"

# ── GOOGLE PLACES SEARCH ─────────────────────────────────────────────────────

# Search queries sent to Google Places (one API call per term).
# Add or remove terms to widen/narrow the property types collected.
SEARCH_QUERIES = [
    #f"Hotels in {CITY}",
    #f"Resorts in {CITY}",
    f"Villas in {CITY}",
    f"Farmhouses in {CITY}",
    f"Bungalows in {CITY}",
    #f"Homestays in {CITY}",
    #f"Lodges in {CITY}",
]

# Maximum hotels to process per pipeline run.
MAX_HOTELS = 2000

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
# Each page shows ~25 hotels. Since we're sorting price_from_high_to_low
# and filtering server-side (see PRICE_FILTER_MIN/MAX below), matching
# hotels should surface immediately -- 20 batches is a reasonable start.
BOOKING_MAX_PAGES = 20

# Seconds to wait after page load / after clicking "Next page".
BOOKING_PAGE_LOAD_WAIT = 4

# Page-Down keystrokes per page to trigger lazy-loaded hotel cards.
BOOKING_MAX_SCROLLS = 6

# Seconds between each Page-Down keystroke.
BOOKING_SCROLL_WAIT = 0.5

# ── BOOKING.COM PRICE FILTER (server-side) ───────────────────────────────────

# Restricts Booking.com's OWN search results to this ₹ range before scraping
# even begins, using the same price-range filter Booking's sidebar slider
# uses, applied via the search URL (see price_extractor.py's _build_url).
# Combined with descending price sort, this surfaces matching hotels
# immediately instead of scraping through every cheaper hotel first.
#
# Set both to None to disable and scrape the full unfiltered result set.
PRICE_FILTER_MIN = 15_000   # ₹ per night
PRICE_FILTER_MAX = 60_000   # ₹ per night

# ── PRICE BANDS ───────────────────────────────────────────────────────────────

# Bands are computed dynamically at runtime (see main.py). Two modes:
#
#   FIXED_PRICE_BAND_EDGES set (not None) -> fixed-width bands using these
#   exact ₹ cut points, e.g. [15000, 30000, 45000, 60000] produces three
#   bands: 15000-30000, 30000-45000, 45000-60000. Use this when you need
#   specific, predictable ranges regardless of how the scraped data is
#   distributed.
#
#   FIXED_PRICE_BAND_EDGES = None -> falls back to NUM_PRICE_BANDS
#   equal-frequency (quantile) bands computed from the actual data, same
#   as before. Set NUM_PRICE_BANDS to 1 for a single combined CSV.
FIXED_PRICE_BAND_EDGES = [15_000, 30_000, 45_000, 60_000]
NUM_PRICE_BANDS = 3

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
CONTACT_REQUEST_TIMEOUT = 5

# User-Agent sent with contact-page requests.
CONTACT_USER_AGENT = "Mozilla/5.0"

# ── OUTPUT ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = "output"

# All leads (no price filter) — new rows are appended on each run.
OUTPUT_ALL_FILE    = f"{OUTPUT_DIR}/{CITY.lower()}_hospitality_leads_all.csv"

# Price-band leads — one CSV per band, rebuilt on each run.
# Fill in with .format(band=label), e.g. OUTPUT_BAND_TEMPLATE.format(band="15000-30000")
OUTPUT_BAND_TEMPLATE = f"{OUTPUT_DIR}/{CITY.lower()}_hospitality_leads_{{band}}.csv"