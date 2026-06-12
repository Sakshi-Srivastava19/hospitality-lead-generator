import re
import requests
from bs4 import BeautifulSoup


def extract_founder_info(base_url):

    pages = [
        "",
        "/about",
        "/about-us",
        "/leadership",
        "/management",
        "/team",
        "/our-team"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    roles = [
        "CEO",
        "Founder",
        "Owner",
        "Managing Director",
        "Director",
        "General Manager",
        "President",
        "Vice President",
        "Sales Head"
    ]

    found_people = []

    for page in pages:

        try:

            url = base_url.rstrip("/") + page

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
                separator="\n",
                strip=True
            )

            lines = text.split("\n")

            for i, line in enumerate(lines):

                for role in roles:

                    if role.lower() in line.lower():

                        person = ""

                        if i > 0:
                            person = lines[i - 1].strip()

                        elif i < len(lines) - 1:
                            person = lines[i + 1].strip()

                        if (
                            len(person.split()) >= 2
                            and len(person) < 50
                        ):

                            record = {
                                "name": person,
                                "role": role
                            }

                            if record not in found_people:
                                found_people.append(
                                    record
                                )

        except Exception:
            continue

    return found_people


if __name__ == "__main__":

    founders = extract_founder_info(
        "https://www.lemontreehotels.com"
    )

    print("\nPEOPLE FOUND:\n")

    for person in founders:

        print(
            person["name"],
            "-",
            person["role"]
        )