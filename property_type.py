import requests


def get_property_type(
    website,
    place_types,
    hotel_name=""
):

    place_types = place_types.lower()
    hotel_name = hotel_name.lower()

    try:

        response = requests.get(
            website,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        text = response.text.lower()

    except:
        text = ""

    combined = (
        hotel_name +
        " " +
        text
    )

    if "farmhouse" in combined:
        return "Farmhouse"

    if "villa" in hotel_name:
        return "Villa"

    if "resort" in hotel_name:
        return "Resort"

    if "palace" in hotel_name:
        return "Luxury Hotel"

    if "boutique" in combined:
        return "Boutique Hotel"

    if "lodging" in place_types:
        return "Hotel"

    return "Hotel"