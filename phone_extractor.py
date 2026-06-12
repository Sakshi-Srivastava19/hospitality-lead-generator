import re
import requests


def extract_phones(website):

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

            text = response.text

            # Indian mobile numbers
            mobile_numbers = re.findall(
                r'(?:\+91[\s\-]?)?[6-9]\d{9}',
                text
            )

            # Landline numbers
            landline_numbers = re.findall(
                r'(?:0\d{2,4}[\-\s]?\d{6,8})',
                text
            )

            for number in mobile_numbers:
                phones.add(number.strip())

            for number in landline_numbers:
                phones.add(number.strip())

        except Exception:
            pass

    phones = list(phones)

    cleaned = []

    for phone in phones:

        digits = re.sub(r"\D", "", phone)

        # Keep only realistic phone numbers
        if len(digits) < 10:
            continue

        if len(digits) > 13:
            continue

        cleaned.append(phone)

    # Mobile numbers first
    mobiles = []
    landlines = []

    for phone in cleaned:

        digits = re.sub(r"\D", "", phone)

        if len(digits) >= 10 and digits[-10][0] in "6789":
            mobiles.append(phone)
        else:
            landlines.append(phone)

    final_numbers = mobiles + landlines

    return list(dict.fromkeys(final_numbers))


if __name__ == "__main__":

    phones = extract_phones(
        "https://www.lemontreehotels.com"
    )

    print("\nPHONES FOUND:\n")

    for phone in phones:
        print(phone)