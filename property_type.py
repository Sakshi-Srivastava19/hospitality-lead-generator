import requests


def get_property_type(
    website,
    place_types,
    hotel_name=""
):
    """
    Classify a hospitality property using:
    1. Hotel name
    2. Google Place types
    3. Website content

    Returns one of:
    - Hotel
    - Resort
    - Villa
    - Boutique Hotel
    - Luxury Hotel
    - Homestay
    - Guesthouse
    - Farm Stay
    - Vacation Home
    - Entire Home
    - Apartment
    - Lodge
    - Other
    """

    place_types = str(place_types).lower()
    hotel_name = str(hotel_name).lower()

    text = ""

    if website and website.startswith("http"):
        try:
            response = requests.get(
                website,
                timeout=10,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0 Safari/537.36"
                    )
                }
            )

            if response.ok:
                text = response.text.lower()

        except Exception:
            pass

    combined = f"{hotel_name} {place_types} {text}"

    # ============================================================
    # PRIVATE PROPERTY TYPES (Highest Priority)
    # ============================================================

    if any(word in combined for word in [
        "private villa",
        "pool villa",
        "luxury villa",
        "villa"
    ]):
        return "Villa"

    if any(word in combined for word in [
        "vacation home",
        "holiday home",
        "holiday house",
        "holiday villa"
    ]):
        return "Vacation Home"

    if any(word in combined for word in [
        "entire home",
        "entire apartment",
        "entire place",
        "private home"
    ]):
        return "Entire Home"

    if any(word in combined for word in [
        "homestay",
        "home stay",
        "home-stay"
    ]):
        return "Homestay"

    if any(word in combined for word in [
        "farm stay",
        "farmstay",
        "farm house",
        "farmhouse"
    ]):
        return "Farm Stay"

    if any(word in combined for word in [
        "guest house",
        "guesthouse"
    ]):
        return "Guesthouse"

    if any(word in combined for word in [
        "serviced apartment",
        "service apartment",
        "apartment"
    ]):
        return "Apartment"

    # ============================================================
    # HOTEL TYPES
    # ============================================================

    if any(word in combined for word in [
        "boutique hotel",
        "boutique"
    ]):
        return "Boutique Hotel"

    if any(word in combined for word in [
        "palace",
        "heritage hotel",
        "royal hotel"
    ]):
        return "Luxury Hotel"

    if "resort" in combined:
        return "Resort"

    if "hotel" in combined:
        return "Hotel"

    if "lodge" in combined:
        return "Lodge"

    # ============================================================
    # GOOGLE PLACE TYPES FALLBACK
    # ============================================================

    if "lodging" in place_types:
        return "Hotel"

    # ============================================================
    # FINAL FALLBACK USING NAME
    # ============================================================

    if "villa" in hotel_name:
        return "Villa"

    if "resort" in hotel_name:
        return "Resort"

    if "hotel" in hotel_name:
        return "Hotel"

    if "homestay" in hotel_name:
        return "Homestay"

    if "guesthouse" in hotel_name or "guest house" in hotel_name:
        return "Guesthouse"

    if "apartment" in hotel_name:
        return "Apartment"

    if "lodge" in hotel_name:
        return "Lodge"

    return "Other"