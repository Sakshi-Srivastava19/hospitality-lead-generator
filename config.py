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
# Google Places returns up to 60 per query × number of queries above.
MAX_HOTELS = 100

# Max result pages per Google Places query (1 page = 20 results, max 3 pages).
PLACES_MAX_PAGES = 3

# Seconds to wait between paginated Places API calls (required by Google).
PLACES_PAGE_DELAY = 2

# HTTP request timeout for Google Places API calls (seconds).
PLACES_REQUEST_TIMEOUT = 15

# ── MMT (MAKEMYTRIP) PRICE EXTRACTION ────────────────────────────────────────

# MMT city codes — add new cities here.
MMT_CITY_CODES = {
    "delhi":     "CTDEL",
    "mumbai":    "CTBOM",
    "goa":       "CTGOI",
    "bangalore": "CTBLR",
    "hyderabad": "CTHYD",
    "chennai":   "CTMAA",
    "kolkata":   "CTCCU",
    "pune":      "CTPNQ",
    "lonavala":  "CTXLK",
}

# Check-in offset from today (days). 1 = tomorrow.
MMT_CHECKIN_DAYS_OFFSET  = 1
# Check-out offset from today (days). 2 = day after tomorrow.
MMT_CHECKOUT_DAYS_OFFSET = 2

# Room configuration sent to MMT.
MMT_ROOM_COUNT   = 1
MMT_ADULTS_COUNT = 2
MMT_CHILD_COUNT  = 0

# Hotels requested per search-hotels API page (max observed: 100).
MMT_API_PAGE_LIMIT = 400

# Max pagination pages when fetching all hotel names from the search-hotels API.
MMT_API_MAX_PAGES = 10

# Selenium async-script timeout in seconds.
MMT_SCRIPT_TIMEOUT = 30

# Seconds between pagination requests to the search-hotels API.
MMT_API_PAGE_DELAY = 1

# Max scroll iterations on the MMT listing page.
MMT_MAX_SCROLLS = 20

# Stop scrolling after this many consecutive scrolls with no new hotels.
MMT_STALE_SCROLL_LIMIT = 4

# Seconds to wait after the MMT page first loads.
MMT_PAGE_LOAD_WAIT = 10

# Seconds between each Page-Down keystroke during scrolling.
MMT_SCROLL_WAIT = 1.5

# ── PROPERTY KEYWORD FILTER ───────────────────────────────────────────────────

# Hotel card text must contain at least one of these words to be included.
# Used in HTML-card fallback extraction (JSON-LD extraction ignores this).
PROPERTY_KEYWORDS = {
    "villa", "resort", "farm", "farmhouse",
    "estate", "cottage", "bungalow", "homestay",
}

# ── FUZZY NAME MATCHING ───────────────────────────────────────────────────────

# Minimum token_sort_ratio score (0–100) to accept an MMT↔Google name match.
# Lower = more lenient (more matches, higher false-positive risk).
# Higher = stricter (fewer matches, lower false-positive risk).
FUZZY_MATCH_THRESHOLD = 80

# Words stripped from hotel names before fuzzy comparison.
# Never add location/brand words — those distinguish one hotel from another.
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

# Price-matched leads only — rebuilt from the full CSV on each run.
OUTPUT_PRICED_FILE = f"{OUTPUT_DIR}/{CITY.lower()}_hospitality_leads_priced.csv"
