import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from config import (
    CHECKIN_DAYS_OFFSET,
    CHECKOUT_DAYS_OFFSET,
    ROOM_COUNT,
    ADULTS_COUNT,
    CHILD_COUNT,
    BOOKING_PAGE_LOAD_WAIT,
    BOOKING_SCROLL_WAIT,
    BOOKING_MAX_PAGES,
)

_HIDE_WEBDRIVER_JS = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
)

_BOOKING_BASE = "https://www.booking.com/searchresults.html"

# Selectors tried in order when looking for the Next-page button


def _build_url(city):
    checkin  = (datetime.now() + timedelta(days=CHECKIN_DAYS_OFFSET)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=CHECKOUT_DAYS_OFFSET)).strftime("%Y-%m-%d")
    return (
        f"{_BOOKING_BASE}"
        f"?ss={city}"
        f"&checkin={checkin}"
        f"&checkout={checkout}"
        f"&group_adults={ADULTS_COUNT}"
        f"&no_rooms={ROOM_COUNT}"
        f"&group_children={CHILD_COUNT}"
        f"&selected_currency=INR"
        f"&order=price"
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


def _extract_cards(driver):
    """
    Parse currently visible property cards.
    Returns {hotel_name_lower: price_int} — price is the nightly rate in INR.
    """
    results = {}
    cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card"]')
    for card in cards:
        # Hotel name
        try:
            name = card.find_element(
                By.CSS_SELECTOR, '[data-testid="title"]'
            ).text.strip()
        except Exception:
            continue
        if not name:
            continue

        # Price
        try:
            price_el = card.find_element(
                By.CSS_SELECTOR, '[data-testid="price-and-discounted-price"]'
            )
            price_text = price_el.text
        except Exception:
            price_text = card.text

        digits = re.sub(r"[^\d]", "", price_text.split("\n")[0])
        if digits:
            val = int(digits)
            if val > 100:
                results[name.lower().strip()] = val

    return results


def _click_load_more(driver):
    """
    Click 'Load more results' if visible. Returns True if clicked.
    The button has no data-testid or aria-label — matched by text only.
    """
    try:
        btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(.)='Load more results']"
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception:
        return False


def get_booking_prices(city):
    """
    Scrape Booking.com search results for *city* and return
    {hotel_name_lower: price_int}  where price is ₹/night.

    Booking.com loads hotels in two stages:
      1. Lazy-load: each scroll-to-bottom reveals ~25 more cards.
      2. 'Load more results' button: appears after lazy-load exhausts (~75
         cards); clicking it fetches the next batch, then lazy-load resumes.
    We alternate between scrolling and clicking the button until no new
    hotels appear for 2 consecutive attempts, or BOOKING_MAX_PAGES is hit.
    """
    base_url = _build_url(city)
    driver   = _make_driver()
    prices   = {}

    try:
        print(f"\nLoading Booking.com: {base_url}")
        driver.get(base_url)
        time.sleep(BOOKING_PAGE_LOAD_WAIT)
        _dismiss_popups(driver)
        time.sleep(1)

        stale = 0
        for batch in range(BOOKING_MAX_PAGES):
            # Scroll to the very bottom to trigger the next lazy-load batch
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(BOOKING_SCROLL_WAIT * 3)

            # If a 'Load more results' button is present, click it
            if _click_load_more(driver):
                print(f"  Batch {batch + 1}: clicked 'Load more results'")
                time.sleep(BOOKING_PAGE_LOAD_WAIT)

            page_prices = _extract_cards(driver)
            new_count   = sum(1 for n in page_prices if n not in prices)
            prices.update(page_prices)

            print(f"  Batch {batch + 1}: {len(page_prices)} cards visible, "
                  f"{new_count} new, total {len(prices)}")

            if new_count == 0:
                stale += 1
                if stale >= 2:
                    print("  No new hotels after 2 consecutive attempts — done.")
                    break
            else:
                stale = 0

    except Exception as e:
        print(f"Booking.com scrape error: {e}")

    finally:
        driver.quit()

    print(f"\nBooking.com total: {len(prices)} hotels with prices")
    return prices


if __name__ == "__main__":
    result = get_booking_prices("Lonavala")
    for name, price in sorted(result.items(), key=lambda x: x[1]):
        print(f"  ₹{price:,}  {name}")
