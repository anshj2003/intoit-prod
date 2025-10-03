#!/usr/bin/env python3


import requests
import time
import googlemaps  # pip install googlemaps
import codecs
import json

# ─── CONFIG ───────────────────────────────────────────────────────────────────

# NYC bounding box: (south, west, north, east)
BBOX = (40.4790, -74.2591, 40.9176, -73.7004)

# Overpass timeout & endpoint
OVERPASS_TIMEOUT = 60  # seconds
OSM_URL = "https://overpass-api.de/api/interpreter"

# Google API key (for details enrichment)
GMAPS_API_KEY = "AIzaSyC7MmFp48QUx4Jsmn_u69tjhznNSQJwArw"
gmaps = googlemaps.Client(key=GMAPS_API_KEY)

# Rate-limit pause between Google calls
GOOGLE_PAUSE = 0.1  # seconds

# ─── STEP 1: PULL RAW OSM DATA ─────────────────────────────────────────────────

def fetch_osm_bars(bbox):
    south, west, north, east = bbox
    query = f"""
    [out:json][timeout:{OVERPASS_TIMEOUT}];
    (
      node["amenity"="bar"]({south},{west},{north},{east});
      node["amenity"="nightclub"]({south},{west},{north},{east});
      node["amenity"="pub"]({south},{west},{north},{east});
      node["amenity"="music_venue"]["cocktails"="yes"]({south},{west},{north},{east});
      way ["amenity"="bar"]({south},{west},{north},{east});
      way ["amenity"="nightclub"]({south},{west},{north},{east});
      way ["amenity"="pub"]({south},{west},{north},{east});
      way ["amenity"="music_venue"]["cocktails"="yes"]({south},{west},{north},{east});
    );
    out center tags;
    """
    resp = requests.post(OSM_URL, data={"data": query})
    resp.raise_for_status()
    return resp.json().get("elements", [])

# ─── STEP 2: DEDUPE, DECODE & EXTRACT ───────────────────────────────────────────

def dedupe_and_extract(elements):
    seen = set()
    places = []
    for el in elements:
        # Node vs. way handling
        if el["type"] == "node":
            lat, lon = el["lat"], el["lon"]
        else:
            lat, lon = el["center"]["lat"], el["center"]["lon"]

        raw_name = el.get("tags", {}).get("name", "").strip()
        if not raw_name:
            continue

        # decode any literal "\uXXXX" sequences to real Unicode
        name = codecs.decode(raw_name, "unicode_escape")

        key = (round(lat, 6), round(lon, 6), name.lower())
        if key in seen:
            continue
        seen.add(key)

        place = {
            "name": name,
            "lat": lat,
            "lon": lon,
            **el.get("tags", {}),  # include any extra tags if desired
        }
        places.append(place)
    return places

# ─── STEP 3 (OPTIONAL): ENRICH WITH GOOGLE ─────────────────────────────────────

def enrich_with_google(place):
    """
    Given a place dict with 'name','lat','lon', use FindPlace + Place Details
    to fetch rating, total reviews, opening_hours.
    """
    query = f"{place['name']}, New York, NY"
    fp = gmaps.find_place(
        input=query,
        input_type="textquery",
        location_bias=f"point:{place['lat']},{place['lon']}",
        fields=["place_id"],
    )
    cand = fp.get("candidates", [])
    if not cand:
        return {}
    place_id = cand[0]["place_id"]
    details = gmaps.place(
        place_id=place_id,
        fields=["name", "rating", "user_ratings_total", "opening_hours","place_id", "price_level", "geometry", "type", "business_status", "plus_code", "vicinity"]
    ).get("result", {})
    time.sleep(GOOGLE_PAUSE)
    return details

# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching OSM data…")
    elements = fetch_osm_bars(BBOX)
    print(f"→ Retrieved {len(elements):,} raw elements from OSM")

    print("Deduping, decoding & extracting…")
    places = dedupe_and_extract(elements)
    print(f"→ {len(places):,} unique bars/pubs/nightclubs/music venues")

    # Save the raw list with real UTF-8 names (no \u escapes)
    out_raw = "nyc_bars_osm.json"
    with open(out_raw, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
    print(f"Saved clean data to {out_raw}")

    # Optional: enrich the first N places
    N = len(places)  # change to len(places) to enrich all
    enriched = []
    print(f"Enriching the first {N} places with Google Places Details…")
    for idx, p in enumerate(places[:N], 1):
        info = enrich_with_google(p)
        enriched.append({**p, **info})
        if idx % 10 == 0 or idx == N:
            print(f"  • {idx}/{N}")

    # Save enriched data with UTF-8 encoding
    out_enriched = "nyc_bars_enriched.json"
    with open(out_enriched, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"Saved enriched data to {out_enriched}")

if __name__ == "__main__":
    main()
