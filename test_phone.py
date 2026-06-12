import requests

url = "https://www.lemontreehotels.com"

response = requests.get(
    url,
    headers={
        "User-Agent":"Mozilla/5.0"
    }
)

print(response.text[:5000])