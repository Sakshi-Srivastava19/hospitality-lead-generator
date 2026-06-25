import os
import time
import requests
from dotenv import load_dotenv
from config import PLACES_MAX_PAGES, PLACES_PAGE_DELAY, PLACES_REQUEST_TIMEOUT

load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

if not API_KEY:
    raise ValueError(
        "Google Places API Key not found in .env file"
    )

_SEARCH_URL  = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def _search_one(query):
    """
    Run a single text-search query with pagination.
    Returns a list of place result dicts (up to 60 per query — 3 pages of 20).
    """
    results = []
    params  = {"query": query, "key": API_KEY}

    for page in range(PLACES_MAX_PAGES):
        resp = requests.get(_SEARCH_URL, params=params, timeout=PLACES_REQUEST_TIMEOUT)
        data = resp.json()

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            print(f"  Places API error for '{query}': {status} — "
                  f"{data.get('error_message', '')}")
            break

        page_results = data.get("results", [])
        results.extend(page_results)

        token = data.get("next_page_token")
        if not token:
            break

        # Google requires a short delay before the next-page token is valid
        time.sleep(PLACES_PAGE_DELAY)
        params = {"pagetoken": token, "key": API_KEY}

    return results


def search_places(query):
    """
    Accept either a single query string or a list of query strings.
    Runs each query (with pagination) and returns deduplicated results
    in the same format as the original single-query response.
    """
    queries = [query] if isinstance(query, str) else list(query)

    seen_ids  = set()
    all_results = []

    for q in queries:
        print(f"\n===== SEARCH: {q} =====")
        page_results = _search_one(q)
        added = 0
        for place in page_results:
            pid = place.get("place_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_results.append(place)
                added += 1
        print(f"Results: {len(page_results)} fetched, {added} new unique")

    print(f"\nTotal unique places found: {len(all_results)}")
    return {"results": all_results, "status": "OK"}


def get_place_details(place_id):

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

    response = requests.get(_DETAILS_URL, params=params, timeout=PLACES_REQUEST_TIMEOUT)
    return response.json()
