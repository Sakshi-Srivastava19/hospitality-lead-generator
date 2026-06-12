import requests
from bs4 import BeautifulSoup


def extract_social_links(website):

    social = {
        "Instagram": "",
        "Facebook": "",
        "LinkedIn": "",
        "YouTube": "",
        "Twitter": ""
    }

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            website,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = soup.find_all("a", href=True)

        for link in links:

            href = link["href"]

            href_lower = href.lower()

            # Instagram
            if (
                "instagram.com" in href_lower
                and href_lower != "https://instagram.com/"
                and social["Instagram"] == ""
            ):
                social["Instagram"] = href

            # Facebook
            elif (
                "facebook.com" in href_lower
                and href_lower != "https://facebook.com/"
                and social["Facebook"] == ""
            ):
                social["Facebook"] = href

            # LinkedIn
            elif (
                "linkedin.com" in href_lower
                and social["LinkedIn"] == ""
            ):
                social["LinkedIn"] = href

            # YouTube
            elif (
                "youtube.com" in href_lower
                and social["YouTube"] == ""
            ):
                social["YouTube"] = href

            # Twitter / X
            elif (
                (
                    "twitter.com" in href_lower
                    or "x.com" in href_lower
                )
                and social["Twitter"] == ""
            ):
                social["Twitter"] = href

        return social

    except Exception as e:

        print(
            "Social Extraction Error:",
            e
        )

        return social


if __name__ == "__main__":

    result = extract_social_links(
        "https://www.lemontreehotels.com"
    )

    print("\nSOCIAL LINKS FOUND:\n")

    for platform, link in result.items():
        print(
            f"{platform}: {link}"
        )