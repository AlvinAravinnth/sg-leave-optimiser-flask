from flask import Flask, jsonify, request, render_template
import requests
import pandas as pd
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- HELPER FUNCTIONS ---
def get_weather(lat, lng):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
        data = requests.get(url, timeout=2).json()
        return f"{data['current_weather']['temperature']}°C"
    except: return "N/A"

def get_wikivoyage(city):
    try:
        # Search
        r = requests.get("https://en.wikivoyage.org/w/api.php", params={"action": "query", "list": "search", "srsearch": city, "format": "json"}).json()
        if not r['query']['search']: return None
        title = r['query']['search'][0]['title']
        
        # Content
        r2 = requests.get("https://en.wikivoyage.org/w/api.php", params={"action": "query", "prop": "extracts", "titles": title, "explaintext": 1, "format": "json"}).json()
        page = next(iter(r2['query']['pages'].values()))
        text = page.get('extract', '')

        def extract(section):
            start = text.find(f"== {section} ==")
            if start == -1: return []
            items = []
            for line in text[start:].split('\n')[1:]:
                if line.startswith("=="): break
                if "*" in line and len(line) > 20:
                    clean = line.replace("*", "").strip()
                    parts = clean.split(" - ", 1) if " - " in clean else [clean, "Explore this highlight."]
                    items.append({"title": parts[0][:50], "desc": parts[1][:150]+"..."})
                    if len(items) >= 3: break
            return items

        return {"see": extract("See") + extract("Do"), "eat": extract("Eat")}
    except: return None

def calc_budget(lat1, lon1, lat2, lon2):
    try:
        R = 6371
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        dist = int(R * c)
        if dist < 1500: return f"{dist}km", "Low ($)"
        if dist < 5000: return f"{dist}km", "Med ($$)"
        return f"{dist}km", "High ($$$)"
    except: return "-", "-"

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
    f_lat, f_lng = data['from']['latitude'], data['from']['longitude']
    t_lat, t_lng = data['to']['latitude'], data['to']['longitude']
    city_name = data['to']['name']

    # 1. Weather & Budget
    weather = get_weather(t_lat, t_lng)
    dist, budget = calc_budget(f_lat, f_lng, t_lat, t_lng)
    
    # 2. Guide
    guide = get_wikivoyage(city_name)
    if not guide: guide = {"see": [], "eat": []}

    # 3. Holiday Logic (Simplified for JSON response)
    # Fetch holidays
    h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
    h_data = requests.get(h_url).json()
    holidays = []
    
    # Process into logic
    # (We return just the first valid long weekend for simplicity in this demo, 
    # but you can expand this to return all)
    for h in h_data:
        dt = datetime.strptime(h['date'], "%Y-%m-%d")
        # Logic: Find the Mon-Fri block
        mon = dt - timedelta(days=dt.weekday())
        start = (mon - timedelta(days=2)).strftime("%d %b")
        end = (mon + timedelta(days=6)).strftime("%d %b")
        holidays.append({
            "name": h['localName'],
            "date": dt.strftime("%d %b"),
            "range": f"{start} - {end}",
            "leaves": 4 # Hardcoded logic for demo, can be dynamic
        })

    return jsonify({
        "weather": weather,
        "dist": dist,
        "budget": budget,
        "guide": guide,
        "holidays": holidays
    })

# For local testing
if __name__ == '__main__':
    app.run(debug=True)