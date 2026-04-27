import httpx
import urllib.parse

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "TrailTrainingApp/1.0 (trail running training application)"
}

def query_trails_near_location(
    lat: float,
    lon: float,
    radius_miles: float = 60.0,
    min_distance_miles: float = None,
    max_distance_miles: float = None,
    min_elevation_gain_ft: float = None,
    max_elevation_gain_ft: float = None,
):
    """
    Query OpenStreetMap for hiking and trail running routes
    near a given location within a radius.
    """
    radius_meters = int(radius_miles * 1609.34)

    query = f"""[out:json][timeout:60];
(
  relation["route"="hiking"]["name"](around:{radius_meters},{lat},{lon});
  relation["route"="running"]["name"](around:{radius_meters},{lat},{lon});
  relation["route"="foot"]["name"](around:{radius_meters},{lat},{lon});
);
out tags;"""

    try:
        encoded = urllib.parse.urlencode({"data": query})
        response = httpx.post(
            OVERPASS_URL,
            content=encoded.encode("utf-8"),
            headers=HEADERS,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {"error": str(e), "trails": []}

    # Parse the results
    trails = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        # Extract distance if available
        distance_miles = None
        raw_distance = tags.get("distance")
        if raw_distance:
            try:
                dist_str = str(raw_distance).replace("km", "").replace("mi", "").strip()
                dist_num = float(dist_str)
                if "mi" in str(raw_distance):
                    distance_miles = round(dist_num, 1)
                else:
                    distance_miles = round(dist_num * 0.621371, 1)
            except:
                pass

        # Apply distance filters if provided
        if min_distance_miles and distance_miles and distance_miles < min_distance_miles:
            continue
        if max_distance_miles and distance_miles and distance_miles > max_distance_miles:
            continue

        trail = {
            "osm_id": str(element.get("id")),
            "name": name,
            "type": tags.get("route"),
            "distance_miles": distance_miles,
            "difficulty": tags.get("sac_scale") or tags.get("difficulty"),
            "surface": tags.get("surface"),
            "description": tags.get("description") or tags.get("note"),
            "website": tags.get("website") or tags.get("url"),
            "region": tags.get("region") or tags.get("area"),
            "network": tags.get("network"),
        }

        trails.append(trail)

    return {
        "total": len(trails),
        "trails": trails
    }