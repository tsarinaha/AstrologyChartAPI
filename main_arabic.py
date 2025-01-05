from fastapi import FastAPI
from pydantic import BaseModel
import swisseph as swe
import requests
import os
from datetime import datetime

# Initialize FastAPI app
app = FastAPI()

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

# Base model for input validation
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
    planets = {}
    for planet, arabic_name in PLANETS_ARABIC.items():
        ret_code, pos = swe.calc_ut(julian_day, planet)
        if ret_code < 0:
            raise ValueError(f"Error calculating position for {arabic_name}")
        zodiac_sign = get_arabic_zodiac_sign(pos[0])
        planets[arabic_name] = {
            "position": round(pos[0], 2),
            "zodiac_sign": zodiac_sign
        }
    return planets

# Geocoding function
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

# API endpoint
@app.post("/calculate_chart/")
def calculate_chart(details: BirthDetails):
    try:
        latitude, longitude = get_coordinates(details.location)
    except ValueError as e:
        return {"error": str(e)}

    try:
        birth_datetime = datetime.strptime(
            f"{details.birth_date} {details.birth_time}", "%Y-%m-%d %H:%M"
        )
    except ValueError:
        return {"error": "Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time."}

    julian_day = swe.julday(
        birth_datetime.year, birth_datetime.month, birth_datetime.day,
        birth_datetime.hour + birth_datetime.minute / 60.0
    )

    # Calculate all planetary positions
    planets_chart = calculate_planetary_positions(julian_day)

    return {
        "name": details.name,
        "chart_in_arabic": planets_chart,
        "location": {"latitude": latitude, "longitude": longitude}
    }

# Run the server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main_arabic:app", host="0.0.0.0", port=port, reload=True)
