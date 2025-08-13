# Flask application for tracking and mapping
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify, request
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import re
import aiohttp
import ssl
import googlemaps
import threading
from unidecode import unidecode
import os
from os import environ
import math
import pickle
import hashlib
import json
import logging
from deep_translator import GoogleTranslator
from langdetect import detect
import csv
from io import StringIO
import pytz

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Constants for location extraction
MILITARY_TERMS = {
    "аеродром": "airport",
    "аэропорт": "airport",
    "летовище": "airport",
    "казарм": "military_base",
    "база": "base",
    "в/ч": "military_base",
    "депо": "depot",
    "склад": "warehouse",
    "завод": "factory",
    "електростанц": "power_plant",
    "енерго": "power_plant",
    "пво": "air_defense",
    "зрк": "air_defense"
}

class LocationExtractor:
    def __init__(self):
        self.patterns = [
            r'(?:у |в |біля |поблизу |районі |м\. |с\. |смт )?([А-ЯІЇЄҐ][а-яіїєґ\'-]+)(?:, ([А-ЯІЇЄҐ][а-яіїєґ\'-]+))?(?: області| районі)?',
            r'(північніше|південніше|східніше|західніше|північній|південній|східній|західній)\s+([\w\-\']+)',
            r'на\s+(?:північ|південь|схід|захід)\s+від\s+([\w\-\']+)',
            r'(біля|поблизу|околиці|район|поруч\s+з|під)\s*([\w\-\']+)',
            r'у\s+([\w\-\']+)\s+районі'
        ]
        self.skip_words = {
            "український", "ппошник", "канал", "підтримати", 
            "напрямок", "решта", "the", "new", "times", "cnn", 
            "оае", "сша"
        }
        self.keywords = {
            "київ": "Київ",
            "одес": "Одеса",
            "харків": "Харків",
            "львів": "Львів",
            "дніпр": "Дніпро",
            "запоріж": "Запоріжжя",
            "миколаїв": "Миколаїв",
            "херсон": "Херсон",
            "дп": "Дніпро",
            "зп": "Запоріжжя",
            "од": "Одеса"
        }

    def extract_locations(self, text):
        locations = {}
        
        # Pattern-based extraction
        for pattern in self.patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                place = match.group(2) if len(match.groups()) > 1 else match.group(1)
                if place and self._is_valid_location(place):
                    context = self._get_context(text, match)
                    loc_type = self._determine_location_type(context)
                    locations[place.strip()] = {
                        "type": loc_type,
                        "context": context,
                        "direction": match.group(1) if len(match.groups()) > 1 else None
                    }
        
        # Keyword-based extraction
        for pattern, place in self.keywords.items():
            if re.search(pattern, text, re.IGNORECASE):
                locations[place] = {
                    "type": "city",
                    "context": "keyword_match",
                    "direction": None
                }
        
        return locations

    def _is_valid_location(self, place):
        if not place or len(place) < 3:
            return False
        return place.lower() not in self.skip_words

    def _get_context(self, text, match):
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        return text[start:end]

    def _determine_location_type(self, context):
        for term, term_type in MILITARY_TERMS.items():
            if term in context.lower():
                return term_type
        return "generic"

# Initialize location extractor
location_extractor = LocationExtractor()

# Load configuration
api_id = environ.get('API_ID')
api_hash = environ.get('API_HASH')
GOOGLE_MAPS_API_KEY = environ.get('GOOGLE_MAPS_API_KEY')

# Initialize Google Maps client
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY) if GOOGLE_MAPS_API_KEY else None

# Initialize Telegram client
client = TelegramClient('anon', api_id, api_hash)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract_locations', methods=['POST'])
def extract_locations():
    try:
        text = request.json.get('text', '')
        locations = location_extractor.extract_locations(text)
        return jsonify(locations)
    except Exception as e:
        logger.error(f"Error extracting locations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/geocode', methods=['POST'])
async def geocode():
    try:
        location = request.json.get('location')
        if not location:
            return jsonify({"error": "Location is required"}), 400

        if not gmaps:
            return jsonify({"error": "Google Maps API not configured"}), 500

        result = gmaps.geocode(location)
        if result:
            location_data = result[0]
            lat = location_data['geometry']['location']['lat']
            lng = location_data['geometry']['location']['lng']
            formatted_address = location_data['formatted_address']
            return jsonify({
                "lat": lat,
                "lng": lng,
                "formatted_address": formatted_address
            })
        else:
            return jsonify({"error": f"Location '{location}' not found"}), 404
    except Exception as e:
        logger.error(f"Error geocoding location: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(environ.get('PORT', 5000)))
