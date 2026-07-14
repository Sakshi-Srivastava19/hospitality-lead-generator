import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from config import (
    CHECKIN_DAYS_OFFSET,
    CHECKOUT_DAYS_OFFSET,
    ROOM_COUNT,
    ADULTS_COUNT,
    CHILD_COUNT,
    BOOKING_PAGE_LOAD_WAIT,
    BOOKING_SCROLL_WAIT,
    BOOKING_MAX_PAGES,
    PRICE_FILTER_MIN,
    PRICE_FILTER_MAX,
)

_HIDE_WEBDRIVER_JS = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
)

_BOOKING_BASE = "https://www.booking.com/searchresults.html"


def _build_url(search_term):
    checkin  = (datetime.now() + timedelta(days=CHECKIN_DAYS_OFFSET)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=CHECKOUT_DAYS_OFFSET)).strftime("%Y-%m-%d")
    ss = quote(search_term)
    url = (
        f"{_BOOKING_BASE}"
        f"?ss={ss}"
        f"&checkin={checkin}"
        f"&checkout={checkout}"
        f"&group_adults={ADULTS_COUNT}"
        f"&no_rooms={ROOM_COUNT}"
        f"&group_children={CHILD_COUNT}"
        f"&selected_currency=INR"
        # "price_from_high_to_low" surfaces the priciest matches within the
        # nflt-filtered ₹10k–35k band first, so higher-value leads are
        # captured early instead of risking BOOKING_MAX_PAGES running out
        # before reaching the top of the range.
        f"&order=price_from_high_to_low"
    )
    if PRICE_FILTER_MIN is not None:
        # Booking's own sidebar price-range filter, applied server-side.
        # Correct raw min/max slider format is price=<MIN>-<MAX>-<CURRENCY>
        # (value range first, currency code last). A malformed chip is
        # silently ignored by Booking rather than erroring, so getting this
        # exact order right matters.
        max_part = str(PRICE_FILTER_MAX) if PRICE_FILTER_MAX is not None else "999999"
        url += f"&nflt=price%3D{PRICE_FILTER_MIN}-{max_part}-INR"
    return url


def _make_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": _HIDE_WEBDRIVER_JS},
    )
    return driver


def _dismiss_popups(driver):
    """Silently close cookie consent, sign-in, and promo overlays."""
    for sel in [
        "#onetrust-accept-btn-handler",
        "[data-testid='accept-all-cookies-button']",
        "[aria-label='Dismiss sign in information.']",
        "[data-testid='dismiss-button']",
        "[aria-label='Close']",
        "button.modal-mask-closeBtn",
    ]:
        try:
            driver.find_element(By.CSS_SELECTOR, sel).click()
            time.sleep(0.4)
        except Exception:
            pass


def _extract_visible_cards(driver, prices, debug_state):
    """
    Parse whatever property cards are CURRENTLY rendered and merge any new
    ones straight into `prices` (mutated in place).

    Returns the number of genuinely new hotels added this call.

    Cards are read incrementally (small scroll steps) rather than all at
    once after a big jump-to-bottom, because Booking.com only fully paints
    title/price text for cards near the current viewport -- cards far from
    it are present in the DOM (so the selector still finds them) but their
    inner text is empty, which silently failed the old digit-parse check.
    """
    added = 0
    cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card"]')
    seen_failed_ids = debug_state.setdefault("seen_failed_ids", set())

    for card in cards:
        try:
            try:
                name = card.find_element(
                    By.CSS_SELECTOR, '[data-testid="title"]'
                ).text.strip()
            except StaleElementReferenceException:
                # This card's reference died mid-read (Booking re-rendered
                # the DOM under us). Skip it -- it'll be re-collected on
                # the next scroll step once it's stable again.
                continue
            except Exception:
                name = ""

            if not name:
                # Dedupe by the card's link href so the same broken/sponsored
                # card isn't recounted on every one of the ~6 scroll steps per
                # sweep -- without this, a handful of bad cards can inflate
                # name_fail into the hundreds and hide the real failure count.
                try:
                    card_id = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                except Exception:
                    card_id = None

                if card_id and card_id in seen_failed_ids:
                    continue
                if card_id:
                    seen_failed_ids.add(card_id)

                debug_state["name_fail"] += 1
                if debug_state["name_fail"] <= 3:
                    try:
                        snippet = card.get_attribute("outerHTML")[:200]
                    except StaleElementReferenceException:
                        snippet = "<stale, could not read>"
                    print(f"    [debug] name parse failed, card html snippet: "
                          f"{snippet!r}")
                continue

            key = name.lower().strip()
            if key in prices:
                continue  # already captured on an earlier scroll step

            try:
                price_el = card.find_element(
                    By.CSS_SELECTOR, '[data-testid="price-and-discounted-price"]'
                )
                price_text = price_el.text
            except StaleElementReferenceException:
                continue
            except Exception:
                try:
                    price_text = card.text
                except StaleElementReferenceException:
                    continue

            digits = re.sub(r"[^\d]", "", price_text.split("\n")[0])

            if digits and int(digits) > 100:
                prices[key] = int(digits)
                added += 1
            else:
                debug_state["price_fail"] += 1
                # Log one example so a real selector/format problem (as opposed
                # to a timing problem) shows up in the console instead of being
                # silently swallowed.
                if debug_state["price_fail"] <= 3:
                    print(f"    [debug] price parse failed for '{name}': "
                          f"raw text={price_text[:80]!r}")

        except StaleElementReferenceException:
            # Catch-all: any other stale reference within this card's
            # processing skips just this one card instead of blowing up
            # the entire scrape (which previously ended runs with 0 hotels).
            continue

    return added


def _scroll_and_collect(driver, prices, debug_state, step_wait, max_idle_steps=6):
    """
    Scroll down in small increments (~80% of viewport height) instead of
    jumping straight to the bottom, extracting cards at every step so each
    one is captured while it's actually rendered. Stops once we hit the
    bottom of the page or get several consecutive scroll steps with no new
    hotels.
    """
    idle_steps = 0

    while True:
        added = _extract_visible_cards(driver, prices, debug_state)
        idle_steps = 0 if added else idle_steps + 1

        at_bottom = driver.execute_script(
            "return (window.innerHeight + window.scrollY) "
            ">= document.body.scrollHeight - 5;"
        )

        if at_bottom or idle_steps >= max_idle_steps:
            break

        driver.execute_script(
            "window.scrollBy(0, Math.round(window.innerHeight * 0.8));"
        )
        time.sleep(step_wait)


def _click_load_more(driver):
    """
    Click 'Load more results' if visible. Returns True if clicked.
    The button has no data-testid or aria-label, and on later pages the
    exact text/markup can vary slightly -- try a few strategies before
    giving up, since one exact-text match ending the whole scrape early
    is expensive (each failed batch = one lost page of results).
    """
    candidates = [
        (By.XPATH, "//button[normalize-space(.)='Load more results']"),
        (By.XPATH, "//button[contains(normalize-space(.), 'Load more')]"),
        (By.CSS_SELECTOR, "[data-testid='load-more-button']"),
    ]
    for by, sel in candidates:
        try:
            btn = driver.find_element(by, sel)
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", btn)
            return True
        except Exception:
            continue
    return False


def get_booking_prices(search_term):
    """
    Scrape Booking.com search results for *search_term* (e.g. "Villas in
    Jaipur", or just "Jaipur") and return {hotel_name_lower: price_int}
    where price is ₹/night.

    Passing a property-type-qualified term ("Villas in Jaipur") instead of
    a bare city name leans on Booking's own destination-search relevance
    to surface that property type -- there is no confirmed, stable public
    URL parameter for filtering by accommodation type on the scraped HTML
    search page (Booking's official type-filter IDs, e.g. villa=213, only
    apply to their authenticated Demand API, not this page).

    Booking.com loads hotels in two stages:
      1. Lazy-load: scrolling reveals ~25 more cards at a time, but only
         paints title/price text for cards near the viewport.
      2. 'Load more results' button: appears after lazy-load exhausts
         (~75-100 cards); clicking it fetches the next batch.
    We sweep the page in small scroll steps (so every card gets painted and
    captured before it's virtualized away), then click 'Load more', then
    sweep again -- repeating until no new hotels appear for 2 consecutive
    full sweeps, or BOOKING_MAX_PAGES is hit.
    """
    base_url = _build_url(search_term)
    driver   = _make_driver()
    prices   = {}
    debug_state = {"name_fail": 0, "price_fail": 0}

    try:
        print(f"\nLoading Booking.com: {base_url}")
        driver.get(base_url)
        time.sleep(BOOKING_PAGE_LOAD_WAIT)
        _dismiss_popups(driver)
        time.sleep(1)

        stale = 0
        for batch in range(BOOKING_MAX_PAGES):
            before = len(prices)

            # Sweep everything currently loaded, scrolling incrementally
            # so nothing gets read before it's rendered.
            _scroll_and_collect(driver, prices, debug_state, BOOKING_SCROLL_WAIT)

            # Now try to load the next batch of results.
            clicked = _click_load_more(driver)
            if clicked:
                print(f"  Batch {batch + 1}: clicked 'Load more results'")
                time.sleep(BOOKING_PAGE_LOAD_WAIT)
                # Sweep again to capture what just got added.
                _scroll_and_collect(driver, prices, debug_state, BOOKING_SCROLL_WAIT)

            new_count = len(prices) - before
            print(f"  Batch {batch + 1}: total {len(prices)} "
                  f"({new_count} new this batch)")

            if new_count == 0:
                stale += 1
                if stale >= 2:
                    print("  No new hotels after 2 consecutive attempts — done.")
                    break
            else:
                stale = 0

            if not clicked and new_count == 0:
                # Nothing new from scrolling and no Load more button left.
                break

        if debug_state["name_fail"] or debug_state["price_fail"]:
            print(f"\n  [debug] cards skipped — no name: {debug_state['name_fail']}, "
                  f"unparseable price: {debug_state['price_fail']}")

    except Exception as e:
        print(f"Booking.com scrape error: {e}")

    finally:
        driver.quit()

    print(f"\nBooking.com total: {len(prices)} hotels with prices")
    return prices


if __name__ == "__main__":
    result = get_booking_prices("Villas in Jaipur")
    for name, price in sorted(result.items(), key=lambda x: x[1]):
        print(f"  ₹{price:,}  {name}")