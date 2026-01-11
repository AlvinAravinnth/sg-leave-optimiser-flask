from flask import Flask, jsonify, request, render_template
import requests
from duckduckgo_search import DDGS
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- 1. THE "LIVE SCRAPER" (DuckDuckGo) ---
def search_internet_for_guide(city):
    guide = {"see": [], "eat": []}
    
    try:
        ddgs = DDGS()
        
        # A. SEARCH FOR SIGHTS
        # We search specifically for "Top things to do in [City]"
        # We take the top 4 search results
        sights_results = ddgs.text(f"top tourist attractions in {city} must visit", max_results=4)
        if sights_results:
            for r in sights_results:
                guide['see'].append({
                    "title": r['title'].split('-')[0].split('|')[0].strip(), # Clean up title
                    "desc": r['body'][:120] + "..."
                })

        # B. SEARCH FOR FOOD
        # We search for "Must eat food in [City]"
        food_results = ddgs.text(f"famous local food must eat in {city}", max_results=4)
        if food_results:
            for r in food_results:
                guide['eat'].append({
                    "title": r['title'].split('-')[0].split('|')[0].strip(),
                    "desc": r['body'][:120] + "..."
                })

    except Exception as e:
        print(f"Scrape Error: {e}")
        # Fallback if DuckDuckGo blocks the request (rare but possible)
        guide = {
            "see": [{"title": "City Center", "desc": f"Explore the highlights of {city}."}],
            "eat": [{"title": "Local Delicacies", "desc": f"Try the street food in {city}."}]
        }

    # Safety check: If search found nothing, fill with generic
    if not guide['see']: guide['see'].append({"title": "Explore Downtown", "desc": "Visit the city center."})
    if not guide['eat']: guide['eat'].append({"title": "Local Cuisine", "desc": "Try authentic local dishes."})
        
    return guide

# --- 2. EXISTING HELPER FUNCTIONS ---
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

# --- 3. ROUTES ---
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
    leaves_balance = int(data.get('leavesLeft', 14))
    
    f_lat = data['from']['latitude']
    f_lng = data['from']['longitude']
    t_lat = data['to']['latitude']
    t_lng = data['to']['longitude']
    city = data['to']['name']

    # 1. Fetch Live Data
    weather = get_weather(t_lat, t_lng)
    dist, budget = calc_budget(f_lat, f_lng, t_lat, t_lng)
    
    # 2. THE LIVE SCRAPE
    guide = search_internet_for_guide(city)

    # 3. Holiday Logic
    holidays = []
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        for h in h_data:
            dt = datetime.strptime(h['date'], "%Y-%m-%d")
            weekday = dt.weekday()
            
            # Lobang Strategy
            if weekday in [1, 2, 3]: # Tue-Thu
                l_off, l_cost, l_note = 4, 1, "Bridge 1 Day"
            else:
                l_off, l_cost, l_note = 3, 0, "Long Weekend"

            # Shiok Strategy (Sat -> Sun)
            mon = dt - timedelta(days=weekday)
            s_start = mon - timedelta(days=2)
            s_end = mon + timedelta(days=6)
            
            holidays.append({
                "name": h['localName'],
                "date": dt.strftime("%d %b"),
                "strategies": {
                    "lobang": {"range": "Long Weekend", "off": l_off, "leaves": l_cost, "note": l_note},
                    "shiok": {"range": f"{s_start.strftime('%d %b')} - {s_end.strftime('%d %b')}", "off": 9, "leaves": 4, "note": "Maximize Block"}
                }
            })
    except: pass

    return jsonify({
        "weather": weather,
        "dist": dist,
        "budget": budget,
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)
