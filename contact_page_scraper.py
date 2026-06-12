import requests
import re
from bs4 import BeautifulSoup


def scrape_contact_pages(website):

    emails = set()
    phones = set()

    pages = [
        "",
        "/contact",
        "/contact-us",
        "/about",
        "/about-us"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for page in pages:

        try:

            url = website.rstrip("/") + page

            print(f"Checking: {url}")

            response = requests.get(
                url,
                headers=headers,
                timeout=10
            )

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            text = soup.get_text(
                separator=" ",
                strip=True
            )

            found_emails = re.findall(
                r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
                text
            )

            found_phones = re.findall(
                r'(?:\+91[\-\s]?)?[6-9]\d{9}',
                text
            )

            emails.update(found_emails)
            phones.update(found_phones)

        except:
            pass

    return {
        "emails": list(emails),
        "phones": list(phones)
    }


if __name__ == "__main__":

    data = scrape_contact_pages(
        "https://www.lemontreehotels.com"
    )

    print("\nEMAILS")
    print(data["emails"])

    print("\nPHONES")
    print(data["phones"])