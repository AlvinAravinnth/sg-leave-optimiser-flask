from flask import Flask, jsonify, request, render_template
import requests
from google import genai
from google.genai import types
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
        # Initializing the new Google Gen AI SDK
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ SDK Init Error: {e}")

# --- AGENTIC REASONING: Gemini 3 Flash ---
def get_ai_decision(city, leave_balance, dist_val):
    if not client: return None
    
    # Prompt optimized for Gemini 3's reasoning capabilities
    prompt = f"""
    Reason through the following constraints as an expert travel agent:
    - User Leave Balance: {leave_balance} days.
    - Destination: {city} ({dist_val}km from Singapore).
    
    HEAVY LIFTING TASKS:
    1. Duration: Decide the optimal number of days to stay. If distance > 4000km, aim for 7-10 days.
    2. Leave Strategy: Suggest exactly which days to take leave to maximize the trip.
    3. Detailed Budget: Estimate total cost in SGD, broken down by Flights, Hotel, and Daily Food/Transport.
    
    Return ONLY a valid JSON object:
    {{
      "suggested_duration": "X days",
      "leave_recommendation": "Take leave on...",
      "budget": {{"total": "SGD X", "breakdown": "..."}},
      "itinerary": {{"see": [...], "eat": [...]}}
    }}
    """
    try:
        # Calling the reasoning model with HIGH thinking level
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="high"),
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

# --- HELPER: Distance Logic ---
def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return int(R * 2 * asin(sqrt(a)))

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
    city = data['to']['name']
    leaves = data.get('leavesLeft', 14)
    
    # Calculate physical distance for AI context
    dist = calc_dist(1.3521, 103.8198, data['to']['latitude'], data['to']['longitude'])
    
    # Delegate "Heavy Work" to reasoning model
    ai_plan = get_ai_decision(city, leaves, dist)
    
    return jsonify({
        "dist": f"{dist}km",
        "ai": ai_plan
    })

if __name__ == '__main__':
    app.run(debug=True)
