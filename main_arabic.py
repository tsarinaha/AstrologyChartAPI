from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import swisseph as swe
import requests
import os
from datetime import datetime
import logging

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

# Function to calculate planetary positions
def calculate_planetary_positions(julian_day):
    planets = []
    for planet, arabic_name in PLANETS_ARABIC.items():
        pos, ret_code = swe.calc_ut(julian_day, planet)
        if ret_code < 0:
            logger.error(f"Error calculating position for {arabic_name}")
            planets.append({"name": arabic_name, "error": "Calculation error"})
            continue
        degree = pos[0]
        zodiac_sign = get_arabic_zodiac_sign(degree)
        planets.append({
            "name": arabic_name,
            "position": round(degree, 2),
            "zodiac_sign": zodiac_sign
        })
    return planets

# Geocoding function
def get_coordinates(location):
    response = requests.get(
        f"https://api.opencagedata.com/geocode/v1/json?q={location}&language=ar&key={OPENCAGE_API_KEY}"
    )
    response.raise_for_status()
    data = response.json()
    if data['results']:
        lat = data['results'][0]['geometry']['lat']
        lng = data['results'][0]['geometry']['lng']
        return lat, lng
    else:
        raise ValueError("Location not found")

# Function to calculate houses and Ascendant
def calculate_houses_and_ascendant(julian_day, latitude, longitude):
    houses, ascendant = swe.houses(julian_day, latitude, longitude, b'P')
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
        }
    }

# Function to assign planets to houses
def assign_planets_to_houses(planets, houses):
    planet_house_positions = {}
    house_degrees = [house["degree"] for house in houses]
    for planet in planets:
        planet_degree = planet["position"]
        for i in range(12):
            next_house_degree = house_degrees[(i + 1) % 12]
            if house_degrees[i] <= planet_degree < next_house_degree:
                planet_house_positions[planet["name"]] = {
                    "house": i + 1,
                    "degree": planet_degree,
                    "zodiac_sign": planet["zodiac_sign"]
                }
                break
    return planet_house_positions

# Function to calculate aspects between planets
def calculate_aspects(planets):
    aspect_types = {
        0: "Conjunction",
        60: "Sextile",
        90: "Square",
        120: "Trine",
        180: "Opposition"
    }
    aspects = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1 = planets[i]
            p2 = planets[j]
            angle = abs(p1["position"] - p2["position"]) % 360
            if angle > 180:
                angle = 360 - angle
            for aspect_angle, aspect_name in aspect_types.items():
                if abs(angle - aspect_angle) <= 5:
                    aspects.append({
                        "from": p1["name"],
                        "to": p2["name"],
                        "angle": angle,
                        "type": aspect_name
                    })
    return aspects

# FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tsarinaha.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint to calculate the natal chart
@app.post("/calculate_chart/")
async def calculate_chart(details: BirthDetails):
    try:
        logger.info(f"Received request: {details}")

        # Parse birth date and time
        birth_datetime = datetime.strptime(
            f"{details.birth_date} {details.birth_time}", "%Y-%m-%d %H:%M"
        )

        # Get location coordinates and timezone
        latitude, longitude, timezone_name = get_coordinates(details.location)
        logger.info(f"Location: {details.location}, Latitude: {latitude}, Longitude: {longitude}, Timezone: {timezone_name}")

        # Adjust for DST
        localized_time, utc_offset = adjust_for_dst(birth_datetime, timezone_name)
        logger.info(f"Localized Time: {localized_time}, UTC Offset: {utc_offset} hours")

        # Calculate Julian Day
        julian_day = swe.julday(
            localized_time.year, localized_time.month, localized_time.day,
            localized_time.hour + localized_time.minute / 60.0
        )

        # Calculate planetary positions
        planets_chart = calculate_planetary_positions(julian_day)

        # Calculate houses and Ascendant
        houses_and_ascendant = calculate_houses_and_ascendant(julian_day, latitude, longitude)

        # Generate table data
        table_data = []

        for planet in planets_chart:
            table_data.append({
                "type": "الكوكب",
                "name": planet["name"],
                "degree": f"{planet['position']:.2f}°",
                "zodiac_sign": planet["zodiac_sign"]
            })

        for house in houses_and_ascendant["houses"]:
            table_data.append({
                "type": "بيت",
                "name": f"بيت {house['house']}",
                "degree": f"{house['degree']:.2f}°",
                "zodiac_sign": house["zodiac_sign"]
            })

        ascendant = houses_and_ascendant["ascendant"]
        table_data.append({
            "type": "طالع",
            "name": "الطالع",
            "degree": f"{ascendant['degree']:.2f}°",
            "zodiac_sign": ascendant["zodiac_sign"]
        })

        return {
            "planets": [{"name": planet["name"], "longitude": planet["position"]} for planet in planets_chart],
            "cusps": [house["degree"] for house in houses_and_ascendant["houses"]],
            "ascendant": houses_and_ascendant["ascendant"],
            "table_data": table_data
        }

    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        return {"error": "Internal Server Error", "details": str(e)}

# Run the server if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
