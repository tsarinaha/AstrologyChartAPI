from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import swisseph as swe
import requests
import os
from datetime import datetime, timedelta
import pytz
import logging

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tsarinaha.github.io"],  # Explicitly allow your frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set the ephemeris path
swe.set_ephe_path("swisseph/ephe")
logger.info("Ephemeris path set to: swisseph/ephe")

# Zodiac signs in Arabic
ARABIC_ZODIAC_SIGNS = [
    "الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
    "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"
]

# Planets in Arabic
PLANETS_ARABIC = {
    swe.SUN: "الشمس",
    swe.MOON: "القمر",
    swe.MERCURY: "عطارد",
    swe.VENUS: "الزهرة",
    swe.MARS: "المريخ",
    swe.JUPITER: "المشتري",
    swe.SATURN: "زحل",
    swe.URANUS: "أورانوس",
    swe.NEPTUNE: "نبتون",
    swe.PLUTO: "بلوتو"
}

# OpenCage API for geocoding
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY")

# Define the request model
class BirthDetails(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    location: str

# Helper to determine zodiac sign
def get_arabic_zodiac_sign(degree):
    return ARABIC_ZODIAC_SIGNS[int(degree // 30)]

# Geocoding function with Arabic support
def get_coordinates(location):
    response = requests.get(
        "https://api.opencagedata.com/geocode/v1/json",
        params={
            "q": location,
            "language": "ar",  # Arabic language support
            "key": OPENCAGE_API_KEY
        }
    )
    response.raise_for_status()
    data = response.json()

    if data["results"]:
        lat = data["results"][0]["geometry"]["lat"]
        lon = data["results"][0]["geometry"]["lng"]
        timezone = data["results"][0].get("annotations", {}).get("timezone", {}).get("name")
        if not timezone:
            timezone = "UTC"  # Fallback to UTC
        return lat, lon, timezone
    else:
        raise ValueError("Location not found or invalid input")

# Function to adjust for DST
def adjust_for_dst(birth_datetime, timezone_name):
    try:
        tz = pytz.timezone(timezone_name)
        localized_time = tz.localize(birth_datetime, is_dst=None)
        utc_offset = localized_time.utcoffset().total_seconds() / 3600.0
        logger.info(f"Localized Time: {localized_time}, UTC Offset: {utc_offset}")
        return localized_time, utc_offset
    except Exception as e:
        logger.error(f"Failed to adjust for DST: {e}")
        raise ValueError("Invalid timezone or location for DST adjustment")

# Function to calculate houses and Ascendant
def calculate_houses_and_ascendant(julian_day, latitude, longitude):
    try:
        houses, ascendant = swe.houses(julian_day, latitude, longitude, b'P')
        if len(houses) != 12:
            raise ValueError("Invalid number of cusps returned by swe.houses")
    except Exception as e:
        logger.error(f"Error calculating houses and ascendant: {e}")
        raise

    # Debugging logs
    logger.info(f"Houses (Cusps): {houses}")
    logger.info(f"Ascendant: {ascendant}")

    houses_data = []
    for i in range(12):
        houses_data.append({
            "house": i + 1,
            "degree": round(houses[i], 2),
            "zodiac_sign": get_arabic_zodiac_sign(houses[i])
        })
    ascendant_sign = get_arabic_zodiac_sign(ascendant[0])
    return {
        "houses": houses_data,
        "ascendant": {
            "degree": round(ascendant[0], 2),
            "zodiac_sign": ascendant_sign
        },
        "cusps": houses  # Ensure the cusps array is passed back
    }

@app.post("/calculate_chart/")
async def calculate_chart(details: BirthDetails):
    try:
        logger.info(f"Received request: {details}")

        birth_datetime = datetime.strptime(
            f"{details.birth_date} {details.birth_time}", "%Y-%m-%d %H:%M"
        )
        latitude, longitude, timezone_name = get_coordinates(details.location)

        localized_time, utc_offset = adjust_for_dst(birth_datetime, timezone_name)

        julian_day = swe.julday(
            localized_time.year, localized_time.month, localized_time.day,
            localized_time.hour + localized_time.minute / 60.0
        )
        planets_chart = calculate_planetary_positions(julian_day)
        houses_and_ascendant = calculate_houses_and_ascendant(julian_day, latitude, longitude)

        return {
            "planets": planets_chart,
            "houses": houses_and_ascendant["houses"],
            "ascendant": houses_and_ascendant["ascendant"]
        }

    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}
