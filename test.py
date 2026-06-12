from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

url = "https://www.makemytrip.com/hotels/hotel-listing/?city=CTBOM&homestay=true&locusId=CTBOM&country=IN&locusType=city&checkin=date_7&checkout=date_9"

driver.get(url)

time.sleep(15)

cards = driver.find_elements(By.XPATH, "//div[contains(@class,'listingRow')]")

print("Hotels found:", len(cards))

for card in cards:
    try:
        print(card.text)
        print("-" * 50)
    except:
        pass

input("Press Enter...")
driver.quit()