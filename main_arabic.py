from fastapi import FastAPI
from pydantic import BaseModel
import swisseph as swe
import requests
import os
from datetime import datetime
import logging

# ✅ Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Set the path to the Swiss Ephemeris files
swe.set_ephe_path("ephe")

# ✅ Zodiac signs in Arabic
ARABIC_ZODIAC_SIGNS = [
    "الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
    "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"
]

# ✅ Planets in Arabic
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

# ✅ OpenCage API for geocoding
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY")

# ✅ Base model for input validation
class BirthDetails(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    location: str

# ✅ Helper to determine zodiac sign
def get_arabic_zodiac_sign(degree):
    return ARABIC_ZODIAC_SIGNS[int(degree // 30)]

# ✅ Function to calculate planetary positions
def calculate_planetary_positions(julian_day):
    planets = {}
    for planet, arabic_name in PLANETS_ARABIC.items():
        ret_code, pos = swe.calc_ut(julian_day, planet)

        # Check if the result is valid and access the first element of pos
        if ret_code < 0 or not isinstance(pos, (list, tuple)) or len(pos) == 0:
            planets[arabic_name] = {"error": "Calculation error"}
            continue

        zodiac_sign = get_arabic_zodiac_sign(pos[0])  # Use pos[0] for the degree
        planets[arabic_name] = {
            "position": round(pos[0], 2),
            "zodiac_sign": zodiac_sign
        }
    return planets


# ✅ Geocoding function
def get_coordinates(location):
    try:
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
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error fetching location data: {str(e)}")

# ✅ API endpoint
app = FastAPI()

@app.post("/calculate_chart/")
def calculate_chart(details: BirthDetails):
    try:
        # ✅ Log the incoming request
        logger.info(f"Received request: {details}")

        # ✅ Step 1: Validate date
        birth_datetime = datetime.strptime(
            f"{details.birth_date} {details.birth_time}", "%Y-%m-%d %H:%M"
        )
        if birth_datetime.year < 1800 or birth_datetime.year > 2400:
            return {"error": "Date out of range. Please provide a date between 1800 and 2400."}

        # ✅ Step 2: Get coordinates from location
        latitude, longitude = get_coordinates(details.location)

        # ✅ Step 3: Convert birth date and time to Julian Day
        julian_day = swe.julday(
            birth_datetime.year, birth_datetime.month, birth_datetime.day,
            birth_datetime.hour + birth_datetime.minute / 60.0
        )

        # ✅ Step 4: Calculate all planetary positions
        planets_chart = calculate_planetary_positions(julian_day)

        # ✅ Step 5: Return the chart data
        return {
            "name": details.name,
            "chart_in_arabic": planets_chart,
            "location": {"latitude": latitude, "longitude": longitude}
        }

    except ValueError as e:
        # ✅ Handle specific value errors
        logger.error(f"ValueError: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        # ✅ Catch any other unexpected errors
        logger.error(f"Unexpected Error: {str(e)}")
        return {"error": "Internal Server Error", "details": str(e)}

# ✅ Run the server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main_arabic:app", host="0.0.0.0", port=port, reload=True)
