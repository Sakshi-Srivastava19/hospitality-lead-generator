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
    "pune": "CTPNQ"
}


def get_mmt_prices(city):

    city_code = CITY_CODES.get(
        city.lower()
    )

    if not city_code:

        print(
            f"City not supported: {city}"
        )

        return {}

    url = (
        f"https://www.makemytrip.com/hotels/hotel-listing/"
        f"?city={city_code}"
        f"&country=IN"
        f"&locusId={city_code}"
        f"&locusType=city"
    )

    options = Options()

    options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )

    options.add_argument(
        "--start-maximized"
    )

    driver = webdriver.Chrome(
        options=options
    )

    prices = {}

    try:

        driver.get(url)

        time.sleep(8)

        print(
            "\nCurrent URL:",
            driver.current_url
        )

        print(
            "Page Title:",
            driver.title
        )

        try:

            close_btn = driver.find_element(
                By.XPATH,
                "//span[@data-cy='closeModal']"
            )

            close_btn.click()

            print(
                "Popup Closed"
            )

            time.sleep(2)

        except:

            print(
                "No Popup Found"
            )

        for _ in range(10):

            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            time.sleep(2)

        soup = BeautifulSoup(
            driver.page_source,
            "lxml"
        )

        cards = soup.select(
            "[class*='listingRow']"
        )

        print(
            "\nCards Found:",
            len(cards)
        )

        for card in cards:

            try:

                name_node = card.select_one(
                    "p[itemprop='name']"
                )

                if not name_node:
                    continue

                hotel_name = name_node.get_text(
                    strip=True
                )

                if not hotel_name:
                    continue

                text = card.get_text(
                    " ",
                    strip=True
                )

                matches = re.findall(
                    r'₹\s?[\d,]+',
                    text
                )

                valid_prices = []

                for price in matches:

                    try:

                        value = int(
                            price
                            .replace("₹", "")
                            .replace(",", "")
                            .strip()
                        )

                        if value > 500:

                            valid_prices.append(
                                value
                            )

                    except:
                        pass

                if hotel_name and valid_prices:

                    best_price = max(
                        valid_prices
                    )

                    hotel_key = (
                        hotel_name
                        .lower()
                        .strip()
                    )

                    if hotel_key not in prices:

                        prices[
                            hotel_key
                        ] = (
                            f"₹{best_price:,}"
                        )

                        print(
                            hotel_name,
                            "=>",
                            f"₹{best_price:,}"
                        )

            except Exception as e:

                print(
                    "Card Error:",
                    e
                )

    except Exception as e:

        print(
            "MMT Error:",
            e
        )

    finally:

        driver.quit()

    return prices


if __name__ == "__main__":

    prices = get_mmt_prices(
        "Chennai"
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