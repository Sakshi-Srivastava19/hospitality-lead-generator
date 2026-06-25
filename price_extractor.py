import json
import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


CITY_CODES = {
    "delhi": "CTDEL",
    "mumbai": "CTBOM",
    "goa": "CTGOI",
    "bangalore": "CTBLR",
    "hyderabad": "CTHYD",
    "chennai": "CTMAA",
    "kolkata": "CTCCU",
    "pune": "CTPNQ",
    "lonavala": "CTXLK",
}

PROPERTY_KEYWORDS = {
    "villa", "resort", "farm", "farmhouse",
    "estate", "cottage", "bungalow", "homestay",
}

# JS injected before page load — hides webdriver flag
_HIDE_WEBDRIVER_JS = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
)

# JS to call search-hotels API from within the browser (bypasses Akamai)
# Returns list of hotel names only (prices come from JSON-LD separately).
_SEARCH_HOTELS_JS = """
var callback = arguments[arguments.length - 1];
var cityCode = arguments[0];
var checkin   = arguments[1];
var checkout  = arguments[2];
var lastHotelId     = arguments[3];
var totalHotelsShown = arguments[4];

var vid       = crypto.randomUUID();
var deviceId  = crypto.randomUUID();
var sessionId = crypto.randomUUID();
var reqId     = crypto.randomUUID();

var usrMcid = '';
try {
    document.cookie.split(';').forEach(function(c) {
        if (c.trim().startsWith('AMCV_')) {
            var parts = c.split('|');
            for (var i = 0; i < parts.length; i++) {
                if (parts[i] === 'MCMID') { usrMcid = parts[i + 1]; }
            }
        }
    });
} catch (e) {}

var url = (
    'https://mapi.makemytrip.com/clientbackend/cg/search-hotels/DESKTOP/2'
    + '?cityCode=' + cityCode
    + '&requestId=' + reqId
    + '&language=eng&region=in&currency=INR&idContext=B2C&countryCode=IN'
);

var body = {
    deviceDetails: {
        appVersion: '149.0.0.0', deviceId: deviceId,
        bookingDevice: 'DESKTOP', networkType: 'WiFi',
        deviceType: 'DESKTOP', deviceName: null
    },
    filterRemovedCriteria: null,
    searchCriteria: {
        checkIn: checkin, checkOut: checkout, limit: 100,
        roomStayCandidates: [{adultCount: 2, rooms: 1, childAges: []}],
        countryCode: 'IN', cityCode: cityCode, locationId: cityCode,
        locationType: 'city', currency: 'INR', preAppliedFilter: false,
        userSearchType: 'city', lastHotelId: lastHotelId,
        lastHotelCategory: '', personalizedSearch: true, nearBySearch: false,
        totalHotelsShown: totalHotelsShown, personalCorpBooking: false,
        rmDHS: false, lastFetchedWindowInfo: '000000000000000#0#15#false'
    },
    requestDetails: {
        visitorId: vid, visitNumber: 1,
        trafficSource: {flowType: 'funnel'}, funnelSource: 'HOTELS',
        idContext: 'B2C', pageContext: 'LISTING', channel: 'B2Cweb',
        journeyId: reqId, requestId: reqId, sessionId: sessionId,
        subPageContext: '', couponCount: 2, seoCorp: false,
        loggedIn: false, forwardBookingFlow: false
    },
    featureFlags: {
        soldOut: true, staticData: true, extraAltAccoRequired: false,
        freeCancellation: true, coupon: true, walletRequired: true,
        mmtPrime: false, checkAvailability: true, reviewSummaryRequired: false
    },
    imageDetails: {types: ['professional'], categories: [{type: 'H', count: 1, height: 162, width: 243, imageFormat: 'webp'}]},
    filterCriteria: [], matchMakerDetails: {}, sortCriteria: null
};

fetch(url, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'Referer': 'https://www.makemytrip.com/',
        'currency': 'INR', 'entity-name': 'india', 'language': 'eng',
        'os': 'desktop', 'region': 'IN', 'server': 'b2c', 'tid': 'avc',
        'user-country': 'IN', 'user-currency': 'INR',
        'usr-mcid': usrMcid, 'vid': vid, 'visitor-id': vid
    },
    body: JSON.stringify(body)
})
.then(function(r) { return r.json(); })
.then(function(data) {
    var resp     = data.response || {};
    var sections = resp.personalizedSections || [];
    var main     = sections.find(function(s) { return s.name === 'RECOMMENDED_HOTELS'; })
                   || sections[0] || {};
    var hotels   = main.hotels || [];
    callback({
        success: true,
        hotelNames: hotels.map(function(h) { return h.name || ''; }),
        lastHotelId: resp.lastHotelId || '',
        noMoreHotels: resp.noMoreHotels || false,
        count: hotels.length
    });
})
.catch(function(err) {
    callback({success: false, error: err.toString()});
});
"""

# JS to read schema.org JSON-LD from the DOM (must run client-side;
# BeautifulSoup can't read dynamically-inserted script elements reliably).
_READ_LD_JS = """
var results = [];
var scripts = document.querySelectorAll('script[type="application/ld+json"]');
for (var i = 0; i < scripts.length; i++) {
    try { results.push(JSON.parse(scripts[i].textContent)); } catch (e) {}
}
return results;
"""


def _build_url(city_code):
    checkin  = (datetime.now() + timedelta(days=1)).strftime("%m%d%Y")
    checkout = (datetime.now() + timedelta(days=2)).strftime("%m%d%Y")
    return (
        f"https://www.makemytrip.com/hotels/hotel-listing/"
        f"?city={city_code}"
        f"&country=IN"
        f"&locusId={city_code}"
        f"&locusType=city"
        f"&checkin={checkin}"
        f"&checkout={checkout}"
        f"&roomCount=1"
        f"&adultsCount=2"
        f"&childCount=0"
    )


def _make_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                           {"source": _HIDE_WEBDRIVER_JS})
    return driver


def _extract_from_json_ld(driver):
    """
    Read schema.org JSON-LD via JavaScript and return {name_lower: '₹price'}.
    JSON-LD is injected by MMT's React app and contains the initial top-5
    hotels with priceRange.  BeautifulSoup .string fails on dynamic scripts.
    """
    prices = {}
    try:
        ld_list = driver.execute_script(_READ_LD_JS) or []
        for data in ld_list:
            for block in data.get("@graph", []):
                if block.get("@type") != "ItemList":
                    continue
                for el in block.get("itemListElement", []):
                    hotel = el.get("item", {})
                    name      = hotel.get("name", "")
                    price_raw = hotel.get("priceRange", "")
                    if not name or not price_raw:
                        continue
                    digits = re.sub(r"[^\d]", "", str(price_raw))
                    if digits:
                        val = int(digits)
                        if val > 0:
                            prices[name.lower().strip()] = f"₹{val:,}"
    except Exception:
        pass
    return prices


def _extract_from_html_cards(page_source):
    """
    Fallback: parse rendered hotel cards for names + inline price text.
    Only keeps hospitality-type properties (resort, villa, etc.).
    """
    soup   = BeautifulSoup(page_source, "lxml")
    prices = {}
    seen   = set()

    cards = (
        soup.select("[class*='listingRow']")
        or soup.select("[class*='hotelRow']")
        or soup.select("[class*='hotel-card']")
        or soup.select("[class*='hotelCard']")
        or soup.select("li[class*='hotel']")
    )

    for card in cards:
        name_node = (
            card.select_one("p[itemprop='name']")
            or card.select_one("[class*='hotelName']")
            or card.select_one("[class*='hotel-name']")
            or card.select_one("[class*='propertyName']")
            or card.select_one("h3")
            or card.select_one("h2")
        )
        if not name_node:
            continue

        hotel_name = name_node.get_text(strip=True)
        if not hotel_name or hotel_name in seen:
            continue
        seen.add(hotel_name)

        card_text = card.get_text(" ", strip=True)
        if not any(kw in hotel_name.lower() or kw in card_text.lower()
                   for kw in PROPERTY_KEYWORDS):
            continue

        price_matches = re.findall(r"₹\s?[\d,]+", card_text)
        vals = []
        for m in price_matches:
            try:
                v = int(re.sub(r"[₹,\s]", "", m))
                if v > 500:
                    vals.append(v)
            except ValueError:
                pass

        if vals:
            best = min(v for v in vals if v > 1000) if any(v > 1000 for v in vals) else vals[0]
            prices[hotel_name.lower().strip()] = f"₹{best:,}"

    return prices


def _get_all_hotel_names(driver, city_code, checkin_fmt, checkout_fmt):
    """
    Call MMT's search-hotels API from inside the browser with pagination
    to collect ALL hotel names for this city (no prices — used for matching).
    """
    all_names  = []
    last_id    = ""
    total_seen = 0

    driver.set_script_timeout(30)

    for page in range(10):
        result = driver.execute_async_script(
            _SEARCH_HOTELS_JS,
            city_code, checkin_fmt, checkout_fmt,
            last_id, total_seen
        )

        if not result or not result.get("success"):
            print(f"  API page {page+1}: error — {result.get('error','')}")
            break

        names = result.get("hotelNames", [])
        if not names:
            break

        all_names.extend(n for n in names if n)
        total_seen += len(names)
        last_id     = result.get("lastHotelId", "")
        no_more     = result.get("noMoreHotels", True)

        print(f"  API page {page+1}: {len(names)} hotels "
              f"(total {total_seen}, noMore={no_more})")

        if no_more or not last_id:
            break

        time.sleep(1)

    return list(dict.fromkeys(all_names))   # deduplicate, preserve order


def get_mmt_prices(city):
    city_code = CITY_CODES.get(city.lower())
    if not city_code:
        print(f"City not supported: {city}")
        return {}

    listing_url  = _build_url(city_code)
    checkin_fmt  = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    checkout_fmt = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    driver = _make_driver()
    prices = {}

    try:
        print(f"\nLoading MMT: {listing_url}")
        driver.get(listing_url)
        time.sleep(10)

        print(f"Page title: {driver.title}")

        # Close login / promo popup
        for xpath in [
            "//span[@data-cy='closeModal']",
            "//button[contains(@class,'close')]",
            "//*[@id='login_modal_close']",
        ]:
            try:
                driver.find_element(By.XPATH, xpath).click()
                print("Popup closed")
                time.sleep(2)
                break
            except Exception:
                pass

        time.sleep(3)

        # ── Source 1: schema.org JSON-LD (most reliable, has prices) ─────────
        print("\nExtracting prices from JSON-LD schema...")
        json_ld_prices = _extract_from_json_ld(driver)
        print(f"  JSON-LD: {len(json_ld_prices)} hotels with prices")
        for name, price in json_ld_prices.items():
            print(f"    {name}: {price}")
        prices.update(json_ld_prices)

        # ── Source 2: scroll and get more from rendered hotel cards ──────────
        print("\nScrolling to load more hotel cards...")
        body       = driver.find_element(By.TAG_NAME, "body")
        prev_count = len(prices)
        stale      = 0

        for i in range(20):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(1.5)
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(1.5)

            # Try clicking "Load More" / "Show More"
            for label in ["Load More", "Show More", "LOAD MORE"]:
                try:
                    btn = driver.find_element(
                        By.XPATH,
                        f"//*[normalize-space(text())='{label}']"
                    )
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    break
                except Exception:
                    pass

            # Re-extract JSON-LD (React may have added more hotels)
            new_ld = _extract_from_json_ld(driver)
            for n, p in new_ld.items():
                if n not in prices:
                    prices[n] = p

            # Also parse HTML cards
            html_prices = _extract_from_html_cards(driver.page_source)
            for n, p in html_prices.items():
                if n not in prices:
                    prices[n] = p

            if len(prices) == prev_count:
                stale += 1
                if stale >= 4:
                    print(f"  No new hotels after scroll {i+1} — stopping")
                    break
            else:
                stale = 0

            print(f"  Scroll {i+1}: {len(prices)} hotels with prices")
            prev_count = len(prices)

        # ── Source 3: search-hotels API → hotel names without prices ─────────
        # These give us names for fuzzy matching even without a price yet.
        print("\nFetching all hotel names from search-hotels API...")
        api_names = _get_all_hotel_names(driver, city_code, checkin_fmt, checkout_fmt)
        print(f"  API returned {len(api_names)} hotel names")

        # Hotels from API that we don't have prices for yet get placeholder
        # so the caller knows they exist on MMT (useful for name matching).
        # We do NOT add a price — the matcher must find a priced entry.
        # (kept as comment; enable if you want name-only entries)
        # for name in api_names:
        #     key = name.lower().strip()
        #     if key not in prices:
        #         prices[key] = ""

    except Exception as e:
        print(f"MMT Error: {e}")

    finally:
        driver.quit()

    print(f"\nTotal MMT hotels with prices: {len(prices)}")
    return prices


if __name__ == "__main__":
    result = get_mmt_prices("Lonavala")
    print(f"\nTOTAL: {len(result)}")
    for hotel, price in result.items():
        print(f"  {hotel} => {price}")
