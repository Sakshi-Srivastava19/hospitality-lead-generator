from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from mail_extractor import extract_emails
from phone_extractor import extract_phones
from social_extractor import extract_social_links


def scrape_website(url):

    service = Service(
        ChromeDriverManager().install()
    )

    driver = webdriver.Chrome(
        service=service
    )

    driver.get(url)

    print("\nWebsite Title:")
    print(driver.title)

    driver.quit()

    emails = extract_emails(url)

    phones = extract_phones(url)

    socials = extract_social_links(url)

    return {
        "emails": emails,
        "phones": phones,
        "socials": socials
    }


if __name__ == "__main__":

    url = "https://www.lemontreehotels.com"

    result = scrape_website(url)

    print("\nEMAILS:")
    print(result["emails"])

    print("\nPHONES:")
    print(result["phones"])

    print("\nSOCIALS:")
    print(result["socials"])