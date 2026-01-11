from flask import Flask, jsonify, request, render_template
import requests
from google import genai
from google.genai import types
import json
import os
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize the modern Client
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def get_ai_reasoning(city, leaves, budget_type, dist):
    if not client: return None
    
    # SYSTEM PROMPT: Giving the AI its PhD in Travel Planning
    prompt = f"""
    You are a PhD-level Travel Strategist. Use deep reasoning to solve this:
    User has {leaves} days of leave. Destination: {city} ({dist}km from Singapore).
    Budget Preference: {budget_type}.

    CONSTRAINTS:
    1. Duration: Decide the optimal stay. Long-haul (>4000km) requires 7-10 days. 
    2. Leave Strategy: Calculate which specific 2026 dates to bridge with public holidays.
    3. Categorized Budget: Estimate SGD costs for Flights, Hotels (based on {budget_type}), and Meals.
    
    Return ONLY a raw JSON object with these keys:
    "duration", "leave_plan", "cost_breakdown" (with 'total', 'flights', 'hotel', 'daily'), "itinerary" (with 'see', 'eat').
    """
    
    try:
        # GEMINI 3 REASONING CALL
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                # 'HIGH' enables multi-step planning and verification
                thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Gemini 3 Error: {e}")
        return None

# --- DISTANCE CALCULATOR ---
def calc_dist(lat2, lon2):
    lat1, lon1 = 1.3521, 103.8198 # Singapore
    R = 6371
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return int(R * 2 * asin(sqrt(a)))

@app.route('/api/plan', methods=['POST'])
def plan_trip():
    data = request.json
    city = data['to']['name']
    leaves = data.get('leavesLeft', 14)
    budget_type = data.get('budget_type', 'Mid-Range')
    
    dist = calc_dist(data['to']['latitude'], data['to']['longitude'])
    
    # The AI Agent takes over the "Heavy Work"
    full_plan = get_ai_reasoning(city, leaves, budget_type, dist)
    
    return jsonify({"plan": full_plan, "dist": f"{dist}km"})

@app.route('/')
def home(): return render_template('index.html')

@app.route('/api/search')
def search_city():
    q = request.args.get('q')
    res = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5")
    return jsonify(res.json().get('results', []))

if __name__ == '__main__': app.run(debug=True)
