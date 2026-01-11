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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def get_ai_reasoning(city, leaves, dist):
    if not client: return None
    prompt = f"""Reason as a PhD Travel Strategist. User has {leaves} days leave. 
    Destination: {city} ({dist}km from SG). 
    Return ONLY JSON: {{
      "duration": "X days Stay",
      "leave_plan": "Specific 2026 dates",
      "budget": "Total SGD",
      "itinerary": {{"see": [{{"title":"", "desc":""}}], "eat": [{{"title":"", "desc":""}}]}}
    }}"""
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except: return None

@app.route('/api/plan', methods=['POST'])
def plan_trip():
    data = request.json
    lat2, lon2 = data['to']['latitude'], data['to']['longitude']
    dist = int(6371 * 2 * asin(sqrt(sin(radians(lat2-1.35)/2)**2 + cos(radians(1.35))*cos(radians(lat2))*sin(radians(lon2-103.8)/2)**2)))
    plan = get_ai_reasoning(data['to']['name'], data.get('leavesLeft', 14), dist)
    return jsonify({"plan": plan, "dist": f"{dist}km"})

@app.route('/')
def home(): return render_template('index.html')

@app.route('/api/search')
def search_city():
    q = request.args.get('q')
    res = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5")
    return jsonify(res.json().get('results', []))

if __name__ == '__main__': app.run(debug=True)
