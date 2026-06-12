import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

if not API_KEY:
    raise ValueError(
        "Google Places API Key not found in .env file"
    )


def search_places(query):

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    params = {
        "query": query,
        "key": API_KEY
    }

    response = requests.get(url, params=params)

    data = response.json()

    print("\n===== SEARCH RESPONSE =====")
    print("Status:", data.get("status"))
    print("Results Found:", len(data.get("results", [])))

    return data


def get_place_details(place_id):

    url = "https://maps.googleapis.com/maps/api/place/details/json"

    params = {
        "place_id": place_id,
        "fields": (
            "name,"
            "formatted_address,"
            "formatted_phone_number,"
            "website,"
            "rating,"
            "user_ratings_total,"
            "types"
        ),
        "key": API_KEY
    }

    response = requests.get(url, params=params)

    return response.json()