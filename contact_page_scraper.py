import requests
import re
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from config import CONTACT_PAGES, CONTACT_REQUEST_TIMEOUT, CONTACT_USER_AGENT


def _base_url(website):
    """Return scheme + netloc + path only — strip query params and fragments."""
    p = urlparse(website)
    return urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", "", ""))


def scrape_contact_pages(website):

    emails = set()
    phones = set()

    # Build pages from the clean base URL (no query string)
    base = _base_url(website)

    headers = {"User-Agent": CONTACT_USER_AGENT}

    for page in CONTACT_PAGES:

        try:

            url = base + page

            print(f"Checking: {url}")

            response = requests.get(
                url,
                headers=headers,
                timeout=CONTACT_REQUEST_TIMEOUT
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