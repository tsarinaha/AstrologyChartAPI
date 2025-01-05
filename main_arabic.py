
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
OPENCAGE_API_KEY = "604e0439ff254a749ac2b4da5d87f078"

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
    response = requests.get(
        f"https://api.opencagedata.com/geocode/v1/json?q={location}&language=ar&key={OPENCAGE_API_KEY}"
    )
    data = response.json()
    if data['results']:
        lat = data['results'][0]['geometry']['lat']
        lng = data['results'][0]['geometry']['lng']
        return lat, lng
    else:
        raise ValueError("Location not found")

# API endpoint to calculate chart
@app.post("/calculate_chart/")
def calculate_chart(details: BirthDetails):
    # Get coordinates from location
    try:
        latitude, longitude = get_coordinates(details.location)
    except ValueError as e:
        return {"error": str(e)}

    # Convert birth date and time to Julian Day
    year, month, day = map(int, details.birth_date.split('-'))
    hour, minute = map(int, details.birth_time.split(':'))
    julian_day = swe.julday(year, month, day, hour + minute / 60.0)

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
