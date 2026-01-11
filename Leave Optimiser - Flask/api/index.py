from flask import Flask, jsonify, request, render_template
import requests
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
        # 1. Search for Page
        r = requests.get("https://en.wikivoyage.org/w/api.php", params={"action": "query", "list": "search", "srsearch": city, "format": "json"}).json()
        if not r.get('query', {}).get('search'): return None
        title = r['query']['search'][0]['title']
        
        # 2. Get Content
        r2 = requests.get("https://en.wikivoyage.org/w/api.php", params={"action": "query", "prop": "extracts", "titles": title, "explaintext": 1, "format": "json"}).json()
        page = next(iter(r2['query']['pages'].values()))
        text = page.get('extract', '')

        # 3. Smart Extraction
        def extract(section_names):
            items = []
            for name in section_names:
                start = text.find(f"== {name} ==")
                if start != -1:
                    lines = text[start:].split('\n')[1:]
                    for line in lines:
                        if line.startswith("=="): break
                        # Look for list items or long sentences
                        if "*" in line and len(line) > 20:
                            clean = line.replace("*", "").strip()
                            parts = clean.split(" - ", 1) if " - " in clean else [clean, ""]
                            desc = parts[1] if parts[1] else "Explore this highlight."
                            items.append({"title": parts[0][:40], "desc": desc[:120]+"..."})
                            if len(items) >= 3: return items
            return items

        # Try multiple section names (e.g., "See", "Do", "Sights")
        see = extract(["See", "Do", "Sights", "Attractions"])
        eat = extract(["Eat", "Drink", "Food"])
        
        # Fallback if empty (e.g. for Countries like "Japan")
        if not see:
            see = [{"title": "Explore Region", "desc": text[:150] + "..."}]
        if not eat:
            eat = [{"title": "Local Cuisine", "desc": "Try the local national dishes and street food."}]

        return {"see": see, "eat": eat}
    except: 
        return {"see": [{"title":"Explore", "desc":"Discover local sights."}], "eat": [{"title":"Local Food", "desc":"Try local delicacies."}]}

def calc_budget(lat1, lon1, lat2, lon2):
    try:
        R = 6371
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        dist = int(R * c)
        if dist < 1000: return f"{dist}km", "Low ($)"
        if dist < 4000: return f"{dist}km", "Med ($$)"
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

    # Weather & Budget
    weather = get_weather(t_lat, t_lng)
    dist, budget = calc_budget(f_lat, f_lng, t_lat, t_lng)
    guide = get_wikivoyage(city_name)

    # Holiday Logic
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        holidays = []
        for h in h_data:
            dt = datetime.strptime(h['date'], "%Y-%m-%d")
            # Logic: 9 Day Trip (Sat -> Sun next week)
            # Find the Monday of that week
            mon = dt - timedelta(days=dt.weekday())
            start = (mon - timedelta(days=2)) # Previous Sat
            end = (mon + timedelta(days=6))   # Next Sun
            
            holidays.append({
                "name": h['localName'],
                "date": dt.strftime("%d %b"),
                "range": f"{start.strftime('%d %b')} - {end.strftime('%d %b')}",
                "leaves": 4 # Simplified logic
            })
    except: holidays = []

    return jsonify({
        "weather": weather,
        "dist": dist,
        "budget": budget,
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)
