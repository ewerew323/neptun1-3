from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta, timezone
import re
import json
import logging
import pytz
import os
from os import environ

# Configure logging
logging.basicConfig(
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

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "message": "Server is running"})

@app.route('/extract_locations', methods=['POST'])
def extract_locations():
    try:
        text = request.json.get('text', '')
        locations = location_extractor.extract_locations(text)
        return jsonify(locations)
    except Exception as e:
        logger.error(f"Error extracting locations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """
    Healthcheck endpoint
    """
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})
