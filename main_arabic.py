
from fastapi import FastAPI
from pydantic import BaseModel
import swisseph as swe
import requests
import os

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

# OpenCage API for geocoding (replace with your own API key)
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY")

# Base model for input validation
class BirthDetails(BaseModel):
    name: str
    birth_date: str  # Format: YYYY-MM-DD
    birth_time: str  # Format: HH:MM
    location: str  # Location in Arabic or English

# Helper to determine zodiac sign
def get_arabic_zodiac_sign(degree):
    return ARABIC_ZODIAC_SIGNS[int(degree // 30)]

# Function to calculate planetary positions
def calculate_planetary_positions(julian_day):
    planets = {}
    for planet, arabic_name in PLANETS_ARABIC.items():
        _, pos = swe.calc_ut(julian_day, planet)
        zodiac_sign = get_arabic_zodiac_sign(pos[0])
        planets[arabic_name] = {
            "position": round(pos[0], 2),
            "zodiac_sign": zodiac_sign
        }
    return planets

# Geocoding function to get latitude and longitude from location
def get_coordinates(location):
    try:
        response = requests.get(
            f"https://api.opencagedata.com/geocode/v1/json?q={location}&language=ar&key={OPENCAGE_API_KEY}"
        )
        response.raise_for_status()  # Raise an error for bad HTTP status codes
        data = response.json()
        if data['results']:
            lat = data['results'][0]['geometry']['lat']
            lng = data['results'][0]['geometry']['lng']
            return lat, lng
        else:
            raise ValueError("Location not found")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error fetching location data: {str(e)}")


# API endpoint to calculate chart
@app.post("/calculate_chart/")
def calculate_chart(details: BirthDetails):
    # Get coordinates from location
    try:
        latitude, longitude = get_coordinates(details.location)
    except ValueError as e:
        return {"error": str(e)}

 from datetime import datetime

# Convert birth date and time to Julian Day
try:
    birth_datetime = datetime.strptime(f"{details.birth_date} {details.birth_time}", "%Y-%m-%d %H:%M")
except ValueError:
    return {"error": "Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time."}

julian_day = swe.julday(birth_datetime.year, birth_datetime.month, birth_datetime.day, birth_datetime.hour + birth_datetime.minute / 60.0)

    # Calculate all planetary positions
    planets_chart = calculate_planetary_positions(julian_day)

    return {
        "name": details.name,
        "chart_in_arabic": planets_chart,
        "location": {"latitude": latitude, "longitude": longitude}
    }

import uvicorn

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main_arabic:app", host="0.0.0.0", port=8000, reload=True)
