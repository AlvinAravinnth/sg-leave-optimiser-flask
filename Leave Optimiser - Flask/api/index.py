from flask import Flask, jsonify, request, render_template
import requests
from google import genai
import json
import os
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = None
if GEMINI_API_KEY:
    try:
        # Initializing the new SDK client for reasoning-capable models
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ SDK Init Error: {e}")
else:
    print("⚠️ Warning: GEMINI_API_KEY not found.")

CITY_CACHE = {}

# --- SMART GUIDE (Reasoning-Capable Gemini 3 Flash) ---
def get_travel_guide(city):
    cache_key = city.lower().strip()
    if cache_key in CITY_CACHE: return CITY_CACHE[cache_key]

    def error_guide(msg):
        return {
            "see": [{"title": "⚠️ Guide Unavailable", "desc": msg}], 
            "eat": [{"title": "Connection Error", "desc": "Check API Key status."}]
        }

    if not client: return error_guide("API Key missing.")

    try:
        # Prompt optimized for Gemini 3's reasoning behavior
        prompt = f"""
        I am a Singaporean tourist visiting {city}. 
        Return a valid JSON object with:
        "see": List of 3 top tourist attractions (dictionaries with "title" and "desc").
        "eat": List of 3 famous local foods (dictionaries with "title" and "desc").
        Keep descriptions under 12 words. Return ONLY raw JSON.
        """
        
        # Using the advanced gemini-3-flash-preview model
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt
        )
        
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        
        data = json.loads(text.strip())
        CITY_CACHE[cache_key] = data
        return data

    except Exception as e:
        return error_guide(str(e)[:100])

# --- HELPER FUNCTIONS ---
def get_weather(lat, lng):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
        data = requests.get(url, timeout=1).json()
        return f"{data['current_weather']['temperature']}°C"
    except: return "N/A"

def calc_budget(lat1, lon1, lat2, lon2):
    try:
        R = 6371 
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        dist = int(R * c)
        
        if dist < 1500: return dist, "Low ($)"
        elif dist < 4500: return dist, "Med ($$)"
        else: return dist, "High ($$$)"
    except: return 0, "-"

# --- ROUTES ---
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
    city = data['to']['name']
    f_lat, f_lng = data['from']['latitude'], data['from']['longitude']
    t_lat, t_lng = data['to']['latitude'], data['to']['longitude']
    
    weather = get_weather(t_lat, t_lng)
    dist_val, budget = calc_budget(f_lat, f_lng, t_lat, t_lng)
    
    # SMART DURATION: If long haul (>4000km), automatically suggest a longer stay
    is_long_haul = dist_val > 4000 
    guide = get_travel_guide(city)

    holidays = []
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        for h in h_data:
            dt = datetime.strptime(h['date'], "%Y-%m-%d")
            weekday = dt.weekday()
            
            l_leaves, l_off = 0, 3
            l_start, l_end = dt, dt
            l_rec = "No leave needed"

            if weekday == 0: # Monday holiday
                l_start, l_end = dt - timedelta(days=2), dt
            elif weekday == 4: # Friday holiday
                l_start, l_end = dt, dt + timedelta(days=2)
            elif weekday == 1: # Tuesday
                l_start, l_end = dt - timedelta(days=3), dt
                l_leaves, l_off = 1, 4
                l_rec = f"Take leave on {(dt - timedelta(days=1)).strftime('%a %d %b')}"
            elif weekday == 3: # Thursday
                l_start, l_end = dt, dt + timedelta(days=3)
                l_leaves, l_off = 1, 4
                l_rec = f"Take leave on {(dt + timedelta(days=1)).strftime('%a %d %b')}"
            elif weekday == 2: # Wednesday
                l_start, l_end = dt, dt + timedelta(days=4)
                l_leaves, l_off = 2, 5
                d1 = (dt + timedelta(days=1)).strftime('%a %d %b')
                d2 = (dt + timedelta(days=2)).strftime('%a %d %b')
                l_rec = f"Take leave on {d1} and {d2}"

            if is_long_haul:
                l_end += timedelta(days=2)
                l_leaves += 2
                l_off += 2
                l_rec += " plus 2 extra days for travel"

            l_range = f"{l_start.strftime('%d %b')} - {l_end.strftime('%d %b')}"
            
            mon_of_week = dt - timedelta(days=weekday)
            s_range = f"{(mon_of_week - timedelta(days=2)).strftime('%d %b')} - {(mon_of_week + timedelta(days=6)).strftime('%d %b')}"

            holidays.append({
                "name": h['localName'],
                "date": dt.strftime("%d %b"),
                "strategies": {
                    "lobang": {"range": l_range, "off": l_off, "leaves": l_leaves, "rec": l_rec},
                    "shiok": {"range": s_range, "off": 9, "leaves": 4, "rec": "Clear the entire week"}
                }
            })
    except Exception as e: print(e)

    return jsonify({
        "weather": weather,
        "dist": f"{dist_val}km",
        "budget": budget,
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)
