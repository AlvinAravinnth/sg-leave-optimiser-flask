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
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ SDK Init Error: {e}")
else:
    print("⚠️ Warning: GEMINI_API_KEY not found.")

CITY_CACHE = {}

# --- SMART GUIDE ---
def get_travel_guide(city):
    cache_key = city.lower().strip()
    if cache_key in CITY_CACHE: return CITY_CACHE[cache_key]

    def error_guide(msg):
        return {
            "see": [{"title": "⚠️ Guide Unavailable", "desc": msg}], 
            "eat": [{"title": "Connection Error", "desc": "Please check API Key or Model."}]
        }

    if not client: return error_guide("API Key missing.")

    try:
        # Prompt optimized for speed (concise)
        prompt = f"""
        Singaporean tourist visiting {city}. 
        Return JSON with keys "see" (3 sights) and "eat" (3 foods).
        Format: {{ "see": [{{"title": "...", "desc": "..."}}], "eat": [...] }}
        Descriptions max 12 words. Raw JSON only.
        """
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
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
        
        if dist < 1500: return dist, "Low ($)"       # KL, Penang, Phuket
        elif dist < 4500: return dist, "Med ($$)"    # Hong Kong, Taiwan, Perth
        else: return dist, "High ($$$)"              # Japan, Europe, USA
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
    
    # 1. Math Calculations (Fast)
    f_lat, f_lng = data['from']['latitude'], data['from']['longitude']
    t_lat, t_lng = data['to']['latitude'], data['to']['longitude']
    
    weather = get_weather(t_lat, t_lng)
    dist_val, budget = calc_budget(f_lat, f_lng, t_lat, t_lng)
    
    # 2. Smart Duration Logic (The "AI" Brain)
    # If far away (>4000km), "Quick" trip should be longer (e.g. 6 days)
    is_long_haul = dist_val > 4000 
    
    # 3. AI Guide (Slow - takes ~2-3s)
    guide = get_travel_guide(city)

    holidays = []
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        
        for h in h_data:
            dt = datetime.strptime(h['date'], "%Y-%m-%d")
            weekday = dt.weekday()
            
            # --- SMART STRATEGY ---
            l_leaves, l_off = 0, 3
            l_start, l_end = dt, dt
            l_rec = "No leave needed"

            # Base Logic: Standard Long Weekend (Sat-Mon or Fri-Sun)
            if weekday == 0: # Mon holiday -> Sat-Mon
                l_start, l_end = dt - timedelta(days=2), dt
            elif weekday == 4: # Fri holiday -> Fri-Sun
                l_start, l_end = dt, dt + timedelta(days=2)
            elif weekday == 1: # Tue -> Take Mon
                l_start, l_end = dt - timedelta(days=3), dt
                l_leaves, l_off = 1, 4
                l_rec = f"Take {(dt - timedelta(days=1)).strftime('%a %d')}"
            elif weekday == 3: # Thu -> Take Fri
                l_start, l_end = dt, dt + timedelta(days=3)
                l_leaves, l_off = 1, 4
                l_rec = f"Take {(dt + timedelta(days=1)).strftime('%a %d')}"
            else: # Wed or Weekend -> Standard
                l_start, l_end = dt, dt
            
            # AI UPGRADE: If Long Haul, extend the "Quick" trip
            if is_long_haul:
                # Add 2 more buffer days (e.g. Turn 4 days into 6 days)
                l_end = l_end + timedelta(days=2)
                l_leaves += 2
                l_off += 2
                l_rec += " + 2 Days"

            l_range = f"{l_start.strftime('%d %b')} - {l_end.strftime('%d %b')}"

            # Shiok Strategy (Always 9 days)
            mon_of_week = dt - timedelta(days=weekday)
            s_start = mon_of_week - timedelta(days=2)
            s_end = mon_of_week + timedelta(days=6)
            s_range = f"{s_start.strftime('%d %b')} - {s_end.strftime('%d %b')}"

            holidays.append({
                "name": h['localName'],
                "date": dt.strftime("%d %b"),
                "strategies": {
                    "lobang": {"range": l_range, "off": l_off, "leaves": l_leaves, "rec": l_rec},
                    "shiok": {"range": s_range, "off": 9, "leaves": 4, "rec": "Clear week"}
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
