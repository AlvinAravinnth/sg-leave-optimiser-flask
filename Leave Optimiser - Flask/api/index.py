from flask import Flask, jsonify, request, render_template
import requests
from google import genai
import json
import os
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

# Load environment variables from .env file (for local testing)
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- CONFIGURATION ---
# SECURE: Get key from Environment Variable (Vercel or .env)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Client only if key is present
client = None
if GEMINI_API_KEY:
    try:
        # NEW SDK SYNTAX: Create a client instance
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ SDK Init Error: {e}")
else:
    print("⚠️ Warning: GEMINI_API_KEY not found. AI features will be disabled.")

# --- 1. CACHING SYSTEM (Optimizes Free Tier) ---
CITY_CACHE = {}

# --- 2. SMART GUIDE (Gemini AI) ---
def get_travel_guide(city):
    # 1. Normalize City Name
    cache_key = city.lower().strip()

    # 2. Check Cache First
    if cache_key in CITY_CACHE:
        print(f"⚡ Cache Hit: Served {city} from memory.")
        return CITY_CACHE[cache_key]

    # Default Fallback
    default_guide = {
        "see": [{"title": "Explore City Center", "desc": f"Discover the main landmarks of {city}."}], 
        "eat": [{"title": "Local Delicacies", "desc": "Try the authentic local street food."}]
    }

    if not client:
        return default_guide

    try:
        # 3. Ask AI (Strict JSON Mode)
        prompt = f"""
        I am a Singaporean tourist visiting {city}. 
        Return a valid JSON object with exactly two keys: "see" and "eat".
        "see": List of 3 top tourist attractions (dictionaries with "title" and "desc").
        "eat": List of 3 famous local foods (dictionaries with "title" and "desc").
        Keep descriptions short (under 15 words).
        IMPORTANT: Return ONLY the raw JSON string. No markdown formatting.
        """
        
        # NEW SDK SYNTAX: Use client.models.generate_content
        # We switch to 'gemini-1.5-flash' which is the current standard fast model
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        text = response.text.strip()
        
        # Clean up Markdown (if AI adds ```json ... ```)
        if text.startswith("```"): 
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        
        data = json.loads(text.strip())

        # 4. Save to Cache
        CITY_CACHE[cache_key] = data
        return data

    except Exception as e:
        print(f"❌ AI Error: {e}")
        return default_guide

# --- 3. HELPER FUNCTIONS ---
def get_weather(lat, lng):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
        data = requests.get(url, timeout=1).json()
        return f"{data['current_weather']['temperature']}°C"
    except: return "N/A"

def calc_budget(lat1, lon1, lat2, lon2):
    try:
        R = 6371 # Earth radius in km
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        dist = int(R * c)
        
        if dist < 1000: return f"{dist}km", "Low ($)"       # Short haul (KL, JB)
        elif dist < 4000: return f"{dist}km", "Med ($$)"    # Medium (BKK, Bali, HK)
        else: return f"{dist}km", "High ($$$)"              # Long (Tokyo, Seoul, EU)
    except: return "-", "-"

# --- 4. FLASK ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/search')
def search_city():
    query = request.args.get('q')
    if not query: return jsonify([])
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=5&language=en&format=json"
        data = requests.get(url, timeout=2).json()
        return jsonify(data.get('results', []))
    except: return jsonify([])

@app.route('/api/plan', methods=['POST'])
def plan_trip():
    data = request.json
    year = int(data.get('year'))
    
    f_lat = data['from']['latitude']
    f_lng = data['from']['longitude']
    t_lat = data['to']['latitude']
    t_lng = data['to']['longitude']
    city = data['to']['name']

    # 1. Get Live Info
    weather = get_weather(t_lat, t_lng)
    dist, budget = calc_budget(f_lat, f_lng, t_lat, t_lng)
    
    # 2. Get AI Guide
    guide = get_travel_guide(city)

    # 3. Calculate Holidays & Strategy
    holidays = []
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        
        for h in h_data:
            dt = datetime.strptime(h['date'], "%Y-%m-%d")
            weekday = dt.weekday() # Mon=0, Tue=1, ... Sun=6
            
            l_leaves = 0
            l_off = 3
            l_start = dt
            l_end = dt

            if weekday == 0: # Mon -> Sat-Mon (3 days, 0 leaves)
                l_start = dt - timedelta(days=2) 
                l_end = dt
            elif weekday == 4: # Fri -> Fri-Sun (3 days, 0 leaves)
                l_start = dt
                l_end = dt + timedelta(days=2)
            elif weekday == 1: # Tue -> Sat-Tue (4 days, 1 leave [Mon])
                l_start = dt - timedelta(days=3)
                l_end = dt
                l_leaves = 1
                l_off = 4
            elif weekday == 3: # Thu -> Thu-Sun (4 days, 1 leave [Fri])
                l_start = dt
                l_end = dt + timedelta(days=3)
                l_leaves = 1
                l_off = 4
            elif weekday == 2: # Wed -> Take Thu/Fri for Wed-Sun block
                l_start = dt
                l_end = dt + timedelta(days=4)
                l_leaves = 2
                l_off = 5
            else: # Sat/Sun -> Standard Weekend
                l_start = dt
                l_end = dt
            
            l_range = f"{l_start.strftime('%d %b')} - {l_end.strftime('%d %b')}"

            # SHIOK Strategy
            mon_of_week = dt - timedelta(days=weekday)
            s_start = mon_of_week - timedelta(days=2) # Previous Sat
            s_end = mon_of_week + timedelta(days=6)   # Next Sun
            s_leaves = 4 
            s_range = f"{s_start.strftime('%d %b')} - {s_end.strftime('%d %b')}"

            holidays.append({
                "name": h['localName'],
                "date": dt.strftime("%d %b"),
                "strategies": {
                    "lobang": {
                        "range": l_range, 
                        "off": l_off, 
                        "leaves": l_leaves, 
                        "type": "Quick Getaway"
                    },
                    "shiok": {
                        "range": s_range, 
                        "off": 9, 
                        "leaves": s_leaves, 
                        "type": "Maximize Block"
                    }
                }
            })
    except Exception as e:
        print(f"Holiday Error: {e}")

    return jsonify({
        "weather": weather,
        "dist": dist,
        "budget": budget,
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)
