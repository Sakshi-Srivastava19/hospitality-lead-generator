import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def extract_emails(url):

    try:

        service = Service(
            ChromeDriverManager().install()
        )

        chrome_options = webdriver.ChromeOptions()

        chrome_options.add_argument("--headless")

        chrome_options.add_argument("--disable-gpu")

        chrome_options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )

        driver.set_page_load_timeout(20)

        driver.get(url)

        time.sleep(5)

        page_text = driver.page_source

        emails = re.findall(
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
            page_text
        )

        driver.quit()

        return list(set(emails))

    except Exception as e:

        print("Email Extraction Error:", e)

        return []


if __name__ == "__main__":

    emails = extract_emails(
        "https://www.lemontreehotel.com"
    )

    print("\nEMAILS FOUND:\n")

    for email in emails:
        print(email)