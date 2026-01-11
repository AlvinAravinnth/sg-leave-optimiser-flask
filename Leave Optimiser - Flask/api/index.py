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
        # Using the new SDK client
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ SDK Init Error: {e}")
else:
    print("⚠️ Warning: GEMINI_API_KEY not found.")

# --- 1. CACHING SYSTEM ---
CITY_CACHE = {}

# --- 2. SMART GUIDE (Gemini AI) ---
def get_travel_guide(city):
    cache_key = city.lower().strip()
    if cache_key in CITY_CACHE:
        return CITY_CACHE[cache_key]

    # Error-Reporting Fallback (Helps us debug)
    def error_guide(msg):
        return {
            "see": [{"title": "⚠️ Guide Unavailable", "desc": msg}], 
            "eat": [{"title": "Connection Error", "desc": "Please check API Key or Model."}]
        }

    if not client:
        return error_guide("API Key missing in Vercel.")

    try:
        prompt = f"""
        I am a Singaporean tourist visiting {city}. 
        Return a valid JSON object with exactly two keys: "see" and "eat".
        "see": List of 3 top tourist attractions (dictionaries with "title" and "desc").
        "eat": List of 3 famous local foods (dictionaries with "title" and "desc").
        Keep descriptions short (under 15 words).
        IMPORTANT: Return ONLY the raw JSON string. No markdown formatting.
        """
        
        # Using gemini-2.0-flash-exp (Confirmed working for you)
        response = client.models.generate_content(
             model="gemini-3-flash-preview",
            contents=prompt
        )
        
        text = response.text.strip()
        # Clean Markdown
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        
        data = json.loads(text.strip())
        CITY_CACHE[cache_key] = data
        return data

    except Exception as e:
        print(f"❌ AI Error: {e}")
        # Return the actual error to the UI so we can see it
        return error_guide(str(e)[:100])

# --- 3. HELPER FUNCTIONS ---
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
        
        if dist < 1000: return f"{dist}km", "Low ($)"
        elif dist < 4000: return f"{dist}km", "Med ($$)"
        else: return f"{dist}km", "High ($$$)"
    except: return "-", "-"

# --- 4. ROUTES ---
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

    weather = get_weather(t_lat, t_lng)
    
    # Unpack budget tuple (dist_str, cost_str)
    dist, budget = calc_budget(f_lat, f_lng, t_lat, t_lng)
    
    guide = get_travel_guide(city)

    holidays = []
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        for h in h_data:
            dt = datetime.strptime(h['date'], "%Y-%m-%d")
            weekday = dt.weekday() # Mon=0
            
            # --- LOBANG STRATEGY ---
            l_leaves, l_off = 0, 3
            l_start, l_end = dt, dt
            l_rec = "No leave needed!" # Default

            if weekday == 0: # Mon -> Sat-Mon
                l_start = dt - timedelta(days=2)
                l_end = dt
            elif weekday == 4: # Fri -> Fri-Sun
                l_start = dt
                l_end = dt + timedelta(days=2)
            elif weekday == 1: # Tue -> Take Mon
                l_start = dt - timedelta(days=3)
                l_end = dt
                l_leaves, l_off = 1, 4
                l_rec = f"Take leave on {(dt - timedelta(days=1)).strftime('%a %d %b')}"
            elif weekday == 3: # Thu -> Take Fri
                l_start = dt
                l_end = dt + timedelta(days=3)
                l_leaves, l_off = 1, 4
                l_rec = f"Take leave on {(dt + timedelta(days=1)).strftime('%a %d %b')}"
            elif weekday == 2: # Wed -> Take Thu/Fri
                l_start = dt
                l_end = dt + timedelta(days=4)
                l_leaves, l_off = 2, 5
                d1 = (dt+timedelta(days=1)).strftime('%a %d %b')
                d2 = (dt+timedelta(days=2)).strftime('%a %d %b')
                l_rec = f"Take leave on {d1} & {d2}"

            l_range = f"{l_start.strftime('%d %b')} - {l_end.strftime('%d %b')}"

            # --- SHIOK STRATEGY ---
            mon_of_week = dt - timedelta(days=weekday)
            s_start = mon_of_week - timedelta(days=2)
            s_end = mon_of_week + timedelta(days=6)
            s_range = f"{s_start.strftime('%d %b')} - {s_end.strftime('%d %b')}"
            s_rec = "Clear the week"

            holidays.append({
                "name": h['localName'],
                "date": dt.strftime("%d %b"),
                "strategies": {
                    "lobang": {"range": l_range, "off": l_off, "leaves": l_leaves, "rec": l_rec},
                    "shiok": {"range": s_range, "off": 9, "leaves": 4, "rec": s_rec}
                }
            })
    except Exception as e: print(e)

    return jsonify({
        "weather": weather,
        "dist": dist,     # Send dist separately
        "budget": budget, # Send budget separately
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)

