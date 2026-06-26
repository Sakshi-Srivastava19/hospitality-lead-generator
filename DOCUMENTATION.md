# DH Lead Gen — Full Technical Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Structure](#2-project-structure)
3. [How the Pipeline Works — End to End](#3-how-the-pipeline-works--end-to-end)
4. [Phase 1 — Booking.com Scraping (price_extractor.py)](#4-phase-1--bookingcom-scraping-price_extractorpy)
5. [Phase 2 — Google Places Enrichment (places_api.py)](#5-phase-2--google-places-enrichment-places_apipy)
6. [Phase 3 — Property Type Classification (property_type.py)](#6-phase-3--property-type-classification-property_typepy)
7. [Phase 4 — Contact Page Scraping (contact_page_scraper.py & phone_extractor.py)](#7-phase-4--contact-page-scraping-contact_page_scraperpy--phone_extractorpy)
8. [Phase 5 — Email Extraction (mail_extractor.py)](#8-phase-5--email-extraction-mail_extractorpy)
9. [Phase 6 — Social Media Links (social_extractor.py)](#9-phase-6--social-media-links-social_extractorpy)
10. [Supporting Modules](#10-supporting-modules)
11. [Output Files](#11-output-files)
12. [Configuration Reference (config.py)](#12-configuration-reference-configpy)
13. [Running the Pipeline](#13-running-the-pipeline)
14. [Backfilling Existing Data (enrich.py)](#14-backfilling-existing-data-enrichpy)
15. [Column Reference](#15-column-reference)
16. [Anti-Bot & Scraping Considerations](#16-anti-bot--scraping-considerations)
17. [Common Issues & Fixes](#17-common-issues--fixes)

---

## 1. Project Overview

**DH Lead Gen** is an automated hospitality lead generation pipeline. It builds a rich database of hotels, resorts, villas, homestays, and other accommodation properties in a target city (currently Lonavala).

For each property it collects:

- **Name** — scraped from Booking.com
- **Nightly Price** — scraped from Booking.com
- **Location / Address** — from Google Places API
- **Property Type** — classified by name, Google tags, and website content
- **Contact Numbers** — from Google Places + hotel website scraping
- **Email Addresses** — from hotel website scraping
- **Rating & Review Count** — from Google Places API
- **Website URL** — from Google Places API
- **Social Media Links** — Instagram, Facebook, LinkedIn, YouTube, Twitter — from the hotel website

The pipeline outputs two CSV files: one with all leads and one filtered to a configured nightly price range.

---

## 2. Project Structure

```
dh-lead-gen/
│
├── main.py                  # Master pipeline — runs all phases for new hotels
├── enrich.py                # Backfill script — enriches existing CSV rows
├── config.py                # All settings and parameters in one place
│
├── price_extractor.py       # Phase 1 — Booking.com Selenium scraper
├── places_api.py            # Phase 2 — Google Places API search + details
├── property_type.py         # Phase 3 — Classify hotel property type
├── contact_page_scraper.py  # Phase 4 — Scrape phones & emails from hotel website
├── phone_extractor.py       # Phone number extraction helper
├── mail_extractor.py        # Email extraction helper (Selenium-based)
├── social_extractor.py      # Phase 6 — Extract social media links from website
├── website_scraper.py       # Utility — combines email, phone, social extraction
├── founder_extractor.py     # Utility — extract founder/owner names from about pages
│
├── .env                     # API keys (not committed to git)
├── requirements.txt         # Python dependencies
│
└── output/
    ├── lonavala_hospitality_leads_all.csv      # All scraped hotels
    └── lonavala_hospitality_leads_priced.csv   # Hotels within price filter
```

---

## 3. How the Pipeline Works — End to End

When you run `python main.py`, the pipeline executes in two major phases:

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 — Booking.com Scrape                                   │
│  Opens a real Chrome browser → navigates to Booking.com         │
│  → scrolls through search results → extracts hotel names        │
│  and nightly prices → returns {hotel_name: price} dictionary    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  DEDUPLICATION                                                  │
│  Loads existing CSV (if any) → compares hotel names →           │
│  skips hotels already saved → finds only NEW hotels             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼  (for each new hotel)
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2 — Enrichment                                           │
│                                                                 │
│  2a. Google Places text search → find place_id                  │
│  2b. Google Places details → address, phone, rating, website    │
│  2c. Property type classification                               │
│  2d. Contact page scraping → more phones & emails               │
│  2e. Social link extraction → Instagram, Facebook, etc.         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  EXPORT                                                         │
│  Append new rows to _all.csv → rebuild _priced.csv              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Phase 1 — Booking.com Scraping (`price_extractor.py`)

### What it does

This is the most technically complex part of the pipeline. It controls a real Google Chrome browser using **Selenium WebDriver** to navigate Booking.com just like a human user would, then reads the hotel cards visible on screen.

### Why Selenium (not requests)?

Booking.com is a JavaScript-heavy single-page application. Hotel cards are rendered dynamically — they don't exist in the raw HTML at page load time. A simple HTTP request would return an empty shell. Selenium launches a full browser that executes JavaScript, waits for content to render, and gives us the fully built DOM to parse.

### Step-by-step breakdown

**Step 1 — Build the search URL**

```
https://www.booking.com/searchresults.html
  ?ss=Lonavala
  &checkin=2026-06-27
  &checkout=2026-06-28
  &group_adults=2
  &no_rooms=1
  &group_children=0
  &selected_currency=INR
  &order=price
```

Parameters are built from `config.py`:
- `ss` = city name
- `checkin` / `checkout` = today + offset (default: tomorrow, 1-night stay)
- `group_adults`, `no_rooms`, `group_children` = room configuration
- `selected_currency=INR` = forces prices in Indian Rupees
- `order=price` = sorts results cheapest first so we get the full price range

**Step 2 — Launch a bot-resistant Chrome instance**

```python
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
    {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"})
```

These settings hide the fact that the browser is being controlled by automation software. Without them, Booking.com detects the bot and shows a CAPTCHA or blocks the request.

**Step 3 — Dismiss popups**

As soon as the page loads, Booking.com may show multiple overlays:
- Cookie consent banner
- Sign-in prompt
- Promotional modal

The scraper tries clicking the close/dismiss button for each of these using CSS selectors. Each try is wrapped in a silent exception handler so a missing popup never crashes the run.

**Step 4 — Scroll-and-load loop**

Booking.com uses **lazy loading** — hotel cards are not all present in the DOM at once. Cards appear only when you scroll down towards them. The scraper simulates this:

```
Repeat up to BOOKING_MAX_PAGES (10) times:
  1. Scroll to the very bottom of the page
     → triggers the next batch of ~25 hotel cards to render
  2. Wait BOOKING_SCROLL_WAIT × 3 seconds for cards to appear
  3. Check for a "Load more results" button
     → clicking it fetches an entirely new batch from the server
  4. Extract all currently visible hotel cards
  5. Count how many are NEW (not seen before)
  6. If 0 new hotels appear twice in a row → we've reached the end → stop
```

**Step 5 — Extract hotel cards**

Each hotel card on Booking.com has the HTML attribute `data-testid="property-card"`. Inside each card:

- **Name**: `[data-testid="title"]` → the hotel name text
- **Price**: `[data-testid="price-and-discounted-price"]` → the price text

The price text is messy (e.g., "₹ 1,350 per night", "INR 4,500"). The extractor strips all non-digit characters and takes the first number it finds. Numbers under 100 are rejected as likely noise (e.g., star ratings).

**Result**: A dictionary of `{hotel_name_lowercase: price_as_integer}` — e.g., `{"green fog guesthouse": 1350}`.

---

## 5. Phase 2 — Google Places Enrichment (`places_api.py`)

### What it does

Takes each hotel name and uses the **Google Places API** to find the real-world business listing for that hotel. This gives us the official address, phone number, website, Google rating, and review count.

### Two-step API process

**Step 1 — Text Search (find the place_id)**

```
GET https://maps.googleapis.com/maps/api/place/textsearch/json
  ?query=Green Fog Guesthouse Lonavala
  &key=YOUR_API_KEY
```

This is like typing the hotel name into Google Maps search. The API returns a list of matching places. We always take the first result (highest relevance). The most important piece of data from this response is the `place_id` — Google's unique identifier for that business.

**Step 2 — Place Details (get full information)**

```
GET https://maps.googleapis.com/maps/api/place/details/json
  ?place_id=ChIJ...
  &fields=name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,types
  &key=YOUR_API_KEY
```

Using the `place_id` from Step 1, we request the full business details. The `fields` parameter controls exactly what we get back (and what we're billed for). We request:

| Field | What it gives us |
|---|---|
| `name` | Official business name |
| `formatted_address` | Full street address, city, state, pin code |
| `formatted_phone_number` | Phone number in local format (e.g., +91 98765 43210) |
| `website` | Official website URL |
| `rating` | Average Google rating (0.0 – 5.0) |
| `user_ratings_total` | Total number of Google reviews |
| `types` | Category tags (e.g., `lodging`, `resort`, `point_of_interest`) |

### Pagination for bulk searches

The `search_places()` function in `places_api.py` (used for bulk city-wide searches) supports pagination. Google Places returns up to 20 results per page with a `next_page_token`. The function waits 4 seconds between page requests because Google activates tokens asynchronously — requesting too fast returns `INVALID_REQUEST`. It retries up to 3 times with increasing delays (3s, 4s, 5s).

---

## 6. Phase 3 — Property Type Classification (`property_type.py`)

### What it does

Classifies each property into a human-readable category: `Hotel`, `Resort`, `Boutique Hotel`, `Villa`, `Farmhouse`, or `Luxury Hotel`.

### Classification logic

The classifier checks multiple signals in priority order:

1. **Hotel name** — the most reliable signal. If "farmhouse", "villa", "resort", or "palace" is in the name, it's almost certainly that type.
2. **Website content** — downloads the hotel's homepage and searches the text. If "farmhouse" appears anywhere on the site, it's a Farmhouse.
3. **Google Places types** — if Google has tagged it as `lodging`, it defaults to `Hotel`.

```python
if "farmhouse" in combined:      → "Farmhouse"
if "villa" in hotel_name:        → "Villa"
if "resort" in hotel_name:       → "Resort"
if "palace" in hotel_name:       → "Luxury Hotel"
if "boutique" in combined:       → "Boutique Hotel"
if "lodging" in place_types:     → "Hotel"
default:                         → "Hotel"
```

The `combined` variable merges the hotel name with the full text content of the website homepage, giving a broad signal from both sources.

---

## 7. Phase 4 — Contact Page Scraping (`contact_page_scraper.py` & `phone_extractor.py`)

### What it does

Many hotels list their phone numbers and email addresses on their website's contact or about page, but not on Booking.com or Google Places. This module directly visits the hotel's website and multiple sub-pages to extract that information.

### Pages visited

For each hotel website, the scraper visits these URLs in sequence:

```
https://hotel-website.com/            (homepage)
https://hotel-website.com/contact
https://hotel-website.com/contact-us
https://hotel-website.com/about
https://hotel-website.com/about-us
```

These sub-paths cover the vast majority of where contact information appears. The base URL is always stripped of any query parameters or fragments before appending these paths.

### Phone number extraction

Two regex patterns are used:

**Indian mobile numbers:**
```regex
(?:\+91[\-\s]?)?[6-9]\d{9}
```
This matches:
- Optional `+91` country code with optional separator
- A digit from 6–9 (all current Indian mobile numbers start with 6, 7, 8, or 9)
- Followed by exactly 9 more digits

**Landline numbers:**
```regex
(?:0\d{2,4}[\-\s]?\d{6,8})
```
This matches:
- STD code starting with 0 (2 to 4 digits)
- Optional separator
- 6 to 8 digit local number

**Validation filter** — numbers are kept only if the digit count is between 10 and 13. This removes:
- Very short matches (noise)
- Very long strings (accidental merges)

**Prioritization** — mobile numbers are listed before landline numbers in the output since mobile contacts are more useful for lead generation.

### Email extraction (`contact_page_scraper.py`)

```regex
[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}
```

This standard email regex is applied to the plain text extracted from each page (HTML tags stripped with BeautifulSoup). All found emails across all pages are deduplicated.

### Data merging

When both Google Places and the website return a phone number, they are merged and deduplicated. The Google Places number (usually the primary business number) goes first as `CONTACT NO 1`, then website-scraped numbers follow as `CONTACT NO 2` and `CONTACT NO 3`.

---

## 8. Phase 5 — Email Extraction (`mail_extractor.py`)

### What it does

An alternative email extractor that uses a full Selenium browser (with JavaScript enabled and a 5-second page load wait) instead of a plain HTTP request. This is useful for websites that load their email addresses dynamically via JavaScript — a plain request would get an empty page, but Selenium waits for JS to finish and then reads the fully rendered content.

The same email regex is applied to the rendered `page_source`.

This module is available as a standalone tool (`extract_emails(url)`) and is also wrapped by `website_scraper.py`.

---

## 9. Phase 6 — Social Media Links (`social_extractor.py`)

### What it does

Visits the hotel's homepage, parses all `<a href="...">` anchor tags, and looks for links to known social media domains.

### Platform detection

| Platform | Detection rule |
|---|---|
| Instagram | `instagram.com` in href, and href is not just `https://instagram.com/` (generic) |
| Facebook | `facebook.com` in href, and href is not just `https://facebook.com/` |
| LinkedIn | `linkedin.com` in href |
| YouTube | `youtube.com` in href |
| Twitter / X | `twitter.com` or `x.com` in href |

Only the **first** link per platform is saved. Generic homepage links (e.g., `https://instagram.com/`) are excluded because they point to the platform itself, not the hotel's profile.

All matching is case-insensitive (`href.lower()`).

---

## 10. Supporting Modules

### `website_scraper.py`

A utility module that orchestrates `mail_extractor`, `phone_extractor`, and `social_extractor` together for a single URL. It opens the website in a browser, prints the page title, and returns a combined dict of emails, phones, and socials. Used for standalone testing.

### `founder_extractor.py`

Visits the hotel's homepage and several sub-pages (`/about`, `/leadership`, `/team`, etc.) and looks for names near known role keywords:

```
CEO, Founder, Owner, Managing Director, Director,
General Manager, President, Vice President, Sales Head
```

When a role keyword is found in a line of text, it reads the line immediately before or after it as the person's name. Names are validated: they must contain at least 2 words and be shorter than 50 characters (to avoid capturing section headings as names).

This module is not currently wired into the main pipeline but can be called directly on any hotel website.

---

## 11. Output Files

All output files are saved in the `output/` directory.

### `lonavala_hospitality_leads_all.csv`

Contains every hotel scraped from Booking.com, regardless of price. New rows are **appended** to this file on each run. Existing hotels are skipped based on name matching (lowercased, stripped).

### `lonavala_hospitality_leads_priced.csv`

Contains only hotels whose nightly price falls within the configured range (`PRICE_MIN` to `PRICE_MAX` in `config.py`). This file is **rebuilt from scratch** on every run using the full `_all.csv` as source data, so it always reflects the latest price filter settings.

### File encoding

Both CSVs use `utf-8-sig` encoding. The `-sig` (BOM) variant is specifically chosen so that when the file is opened in **Microsoft Excel**, the rupee symbol (₹) and any Hindi/special characters in hotel names display correctly. Without the BOM, Excel often misreads UTF-8 and shows garbled text.

---

## 12. Configuration Reference (`config.py`)

All pipeline settings are centralized in `config.py`. You should never need to touch any other file to change how the pipeline runs.

### Target City

| Setting | Default | Description |
|---|---|---|
| `CITY` | `"Lonavala"` | City name used in Booking.com search and Google Places queries |

### Booking.com Settings

| Setting | Default | Description |
|---|---|---|
| `CHECKIN_DAYS_OFFSET` | `1` | Days from today for check-in (1 = tomorrow) |
| `CHECKOUT_DAYS_OFFSET` | `2` | Days from today for checkout (1-night stay) |
| `ROOM_COUNT` | `1` | Number of rooms in the search |
| `ADULTS_COUNT` | `2` | Number of adults |
| `CHILD_COUNT` | `0` | Number of children |
| `BOOKING_MAX_PAGES` | `10` | Max scroll/load batches (each yields ~25 hotels) |
| `BOOKING_PAGE_LOAD_WAIT` | `6` | Seconds to wait after page or batch load |
| `BOOKING_MAX_SCROLLS` | `6` | Page-down keystrokes per scroll pass |
| `BOOKING_SCROLL_WAIT` | `0.8` | Seconds between each Page-Down keystroke |

### Google Places Settings

| Setting | Default | Description |
|---|---|---|
| `PLACES_MAX_PAGES` | `3` | Pages per bulk search query (20 results each, max 3) |
| `PLACES_PAGE_DELAY` | `4` | Seconds to wait before requesting next page token |
| `PLACES_REQUEST_TIMEOUT` | `15` | HTTP timeout for Places API calls |
| `SEARCH_QUERIES` | Hotels, Resorts, Villas, Homestays, Farmhouses, Lodges | Queries used in bulk city-wide search mode |

### Price Filter

| Setting | Default | Description |
|---|---|---|
| `PRICE_MIN` | `1,000` | Minimum ₹/night for the priced CSV |
| `PRICE_MAX` | `50,000` | Maximum ₹/night for the priced CSV |

Set `PRICE_MIN = 0` and `PRICE_MAX = 9_999_999` to include all hotels.

### Contact Page Scraping

| Setting | Default | Description |
|---|---|---|
| `CONTACT_PAGES` | `["", "/contact", "/contact-us", "/about", "/about-us"]` | Sub-paths to visit on each hotel website |
| `CONTACT_REQUEST_TIMEOUT` | `10` | Seconds before a contact page request times out |
| `CONTACT_USER_AGENT` | `"Mozilla/5.0"` | Browser identity sent with requests |

### Output Paths

| Setting | Default | Description |
|---|---|---|
| `OUTPUT_DIR` | `"output"` | Directory for all CSV output |
| `OUTPUT_ALL_FILE` | `output/lonavala_hospitality_leads_all.csv` | All leads CSV path |
| `OUTPUT_PRICED_FILE` | `output/lonavala_hospitality_leads_priced.csv` | Price-filtered CSV path |

### Other

| Setting | Default | Description |
|---|---|---|
| `MAX_HOTELS` | `500` | Maximum new hotels to process per run |
| `FUZZY_MATCH_THRESHOLD` | `80` | Minimum fuzzy name match score (0–100) |

---

## 13. Running the Pipeline

### First-time setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Set your API key

Create a `.env` file in the project root:

```
GOOGLE_PLACES_API_KEY=your_key_here
```

Get a key from Google Cloud Console — enable the **Places API** on it.

### Run the full pipeline (new hotels only)

```bash
source venv/bin/activate
python main.py
```

This will:
1. Open a Chrome window and scrape Booking.com
2. Look up each new hotel on Google Places
3. Scrape each hotel's website for contacts and social links
4. Append results to the `output/` CSVs

### Change the target city

Edit `config.py`:

```python
CITY = "Pune"   # or any other city
```

The output filenames update automatically to `pune_hospitality_leads_all.csv`, etc.

### Expand the price range

Edit `config.py`:

```python
PRICE_MIN =  500     # lower floor
PRICE_MAX = 100_000  # raise ceiling
```

---

## 14. Backfilling Existing Data (`enrich.py`)

If you have a CSV from an earlier run where the detail columns (LOCATION, WEBSITE, contacts, socials) are all blank, run `enrich.py` to fill them in:

```bash
python enrich.py
```

### How it decides which rows to process

A row is considered "needs enrichment" if all three of these columns are empty: `LOCATION`, `WEBSITE`, `RATING OUT OF 5`.

This means:
- If a hotel already has its address, the enricher skips it (safe to re-run)
- If only some columns are empty (e.g., website is there but no social links), the row is also skipped — it is considered already processed

### What it outputs

- Updates the `_all.csv` in place (overwrites the file with enriched data)
- Rebuilds the `_priced.csv` from the freshly enriched data

---

## 15. Column Reference

| Column | Source | Description |
|---|---|---|
| `SR NO` | Generated | Sequential row number |
| `NAME` | Booking.com | Hotel name as listed on Booking.com, title-cased |
| `PROPERTY TYPE` | Classified | Hotel / Resort / Villa / Farmhouse / Boutique Hotel / Luxury Hotel |
| `LOCATION` | Google Places | Full formatted address (street, city, state, PIN) |
| `CITY` | Config | City name from `config.py` |
| `CONTACT NO 1` | Google Places / Website | Primary phone number |
| `CONTACT NO 2` | Website | Secondary phone number |
| `CONTACT NO 3` | Website | Tertiary phone number |
| `EMAIL 1` | Website | Primary email address |
| `EMAIL 2` | Website | Secondary email address |
| `EMAIL 3` | Website | Tertiary email address |
| `RATING OUT OF 5` | Google Places | Average Google Maps rating |
| `REVIEW COUNT` | Google Places | Total number of Google reviews |
| `PRICE PER DAY` | Booking.com | Nightly rate in ₹ for 1 room, 2 adults, 1 night |
| `LOCATION TYPE` | Google Places types | Derived from Google's category tags |
| `WEBSITE` | Google Places | Official hotel website URL |
| `INSTAGRAM` | Website | Instagram profile URL |
| `FACEBOOK` | Website | Facebook page URL |
| `LINKEDIN` | Website | LinkedIn page URL |
| `YOUTUBE` | Website | YouTube channel URL |
| `TWITTER` | Website | Twitter / X profile URL |

---

## 16. Anti-Bot & Scraping Considerations

### Booking.com

Booking.com actively detects and blocks automated browsers. The pipeline uses several techniques to appear human:

- **`--disable-blink-features=AutomationControlled`** — removes the `navigator.webdriver` flag that sites check to detect Selenium
- **Exclude automation switches** — removes Chrome flags that expose automated operation
- **CDP script injection** — overrides `navigator.webdriver` at the JavaScript level so it returns `undefined` instead of `true`
- **`--start-maximized`** — opens the browser in full-screen, matching normal human usage
- **Randomized waits** — `BOOKING_PAGE_LOAD_WAIT` and `BOOKING_SCROLL_WAIT` add pauses between actions rather than acting at machine speed

Despite these precautions, Booking.com may still show a CAPTCHA on some runs, especially if your IP has made many recent requests. If this happens, solving the CAPTCHA manually in the open browser window will usually let the scrape continue.

### Hotel Websites

Website scraping uses a standard `Mozilla/5.0` User-Agent header to identify as a normal browser. Requests time out after `CONTACT_REQUEST_TIMEOUT` (10 seconds) to avoid hanging on slow or unresponsive sites. All exceptions are caught silently so a broken or blocked website never crashes the run for the next hotel.

### Google Places API

The API key is stored in `.env` and never hard-coded. The pipeline respects Google's rate limits by adding a `time.sleep(0.3)` between consecutive hotel enrichments. For the paginated bulk search, a 4-second delay is added between page token requests as required by Google's documentation.

---

## 17. Common Issues & Fixes

### `ModuleNotFoundError: No module named 'requests'`

You're using the system Python, not the virtual environment.

```bash
source venv/bin/activate
python main.py
```

Or use the full venv path: `/path/to/venv/bin/python main.py`

### Booking.com scrape returns 0 hotels

- The browser may have been blocked or hit a CAPTCHA
- Try increasing `BOOKING_PAGE_LOAD_WAIT` to 10 seconds in `config.py`
- Run the script and watch the browser window — if a CAPTCHA appears, solve it manually

### Google Places returns wrong hotel

The text search uses `"Hotel Name City"` as the query. Very generic names like "Hotel Sunshine" in a large city may match the wrong business. The pipeline always takes the first result — if accuracy is critical, the `place_id` can be verified manually and hardcoded.

### Prices look wrong (too low or too high)

The price extractor strips all non-digits and takes the first number. On some cards this may capture a discount badge or star rating instead of the actual price. Numbers under 100 are filtered out, but edge cases can still slip through. The price filter in `config.py` catches the worst outliers.

### `INVALID_REQUEST` from Google Places pagination

This is normal — Google's `next_page_token` takes a few seconds to activate on their server. The `_fetch_with_retry` function handles this automatically by retrying up to 3 times with 3–5 second delays.

### CSV shows garbled characters in Excel

The files use `utf-8-sig` (UTF-8 with BOM) which Excel on Windows requires to correctly render special characters. If you open the file in a text editor and see `ï»¿` at the start, that is the BOM — it is correct and will be invisible in Excel.
