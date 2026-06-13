from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import time


CITY_CODES = {
    "delhi": "CTDEL",
    "mumbai": "CTBOM",
    "goa": "CTGOI",
    "bangalore": "CTBLR",
    "hyderabad": "CTHYD",
    "chennai": "CTMAA",
    "kolkata": "CTCCU",
    "pune": "CTPNQ",
    "lonavala":"CTXLK",
}


def get_mmt_prices(city):

    city_code = CITY_CODES.get(city.lower())

    if not city_code:
        print(f"City not supported: {city}")
        return {}

    url = (
        f"https://www.makemytrip.com/hotels/hotel-listing/"
        f"?city={city_code}"
        f"&country=IN"
        f"&locusId={city_code}"
        f"&locusType=city"
    )

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    prices = {}

    try:
        driver.get(url)
        time.sleep(8)

        print("\nCurrent URL:", driver.current_url)
        print("Page Title:", driver.title)

        try:
            close_btn = driver.find_element(
                By.XPATH,
                "//span[@data-cy='closeModal']"
            )
            close_btn.click()
            print("Popup Closed")
            time.sleep(2)
        except:
            print("No Popup Found")

        for i in range(30):

            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            time.sleep(2)

            cards_now = len(
                driver.find_elements(
                    By.CSS_SELECTOR,
                    "p[itemprop='name']"
                )
            )

            print(f"Scroll {i+1}: {cards_now} hotels")
            print("\nChecking pagination...")

            links = driver.find_elements(
                By.TAG_NAME,
                "a"
            )

            for link in links:

                try:

                    text = link.text.strip()

                    if text:

                        print(text)

                except:
                    pass
        soup = BeautifulSoup(driver.page_source, "lxml")

        cards = soup.select("[class*='listingRow']")

        print("\nCards Found:", len(cards))

        seen_hotels = set()   # ✅ FIXED POSITION

        for card in cards:

            try:
                name_node = card.select_one("p[itemprop='name']")
                if not name_node:
                    continue

                hotel_name = name_node.get_text(strip=True)
                if not hotel_name:
                    continue

                # ✅ REMOVE DUPLICATES PROPERLY
                if hotel_name in seen_hotels:
                    continue
                seen_hotels.add(hotel_name)

                text = card.get_text(" ", strip=True)
                PROPERTY_KEYWORDS = [
                    "villa",
                    "resort",
                    "farm",
                    "farmhouse",
                    "estate",
                    "cottage",
                    "bungalow",
                    "homestay"
                ]

                text_lower = text.lower()

                if not any(
                    keyword in text_lower
                    for keyword in PROPERTY_KEYWORDS
                ):
                    continue
                matches = re.findall(r'₹\s?[\d,]+', text)

                valid_prices = []

                for price in matches:
                    try:
                        value = int(
                            price.replace("₹", "")
                                 .replace(",", "")
                                 .strip()
                        )
                        if value > 500:
                            valid_prices.append(value)
                    except:
                        pass

                if not valid_prices:
                    continue

                print(f"\n{hotel_name}")
                print("ALL PRICES FOUND:", valid_prices)
                # Try to find any price directly in range
                best_price = None

                in_range_prices = [
                    p for p in valid_prices
                    if 15000 <= p <= 30000
                ]

                if in_range_prices:

                    best_price = max(in_range_prices)

                else:

                    # Example:
                    # [35000, 24858, 6804]
                    # pick 24858

                    room_prices = sorted(
                        [p for p in valid_prices if p > 3000],
                        reverse=True
                    )

                    if len(room_prices) >= 2:

                        candidate = room_prices[1]

                        if 15000 <= candidate <= 30000:
                            best_price = candidate

                    elif len(room_prices) == 1:

                        candidate = room_prices[0]

                        if 15000 <= candidate <= 30000:
                            best_price = candidate

                if best_price is None:
                    continue
                print("SELECTED PRICE:", best_price)
                hotel_key = hotel_name.lower().strip()

                prices[hotel_key] = f"₹{best_price:,}"

                print(hotel_name, "=>", f"₹{best_price:,}")

            except Exception as e:
                print("Card Error:", e)

    except Exception as e:
        print("MMT Error:", e)

    finally:
        driver.quit()

    return prices


if __name__ == "__main__":

    prices = get_mmt_prices(
        "Lonavala"
    )

    print(
        "\nTOTAL HOTELS FOUND:",
        len(prices)
    )

    print(
        "\nPRICE DICTIONARY:\n"
    )

    for hotel, price in prices.items():

        print(
            hotel,
            "=>",
            price
        )