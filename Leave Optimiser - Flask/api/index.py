from flask import Flask, jsonify, request, render_template
import requests
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- 1. SMART GUIDE FETCHER (GPS + Country Fallback) ---
def get_wikivoyage(city, country, lat, lng):
    try:
        sights = []
        food = []

        # A. FETCH SIGHTS via GPS (Geosearch) - Accurate for big cities
        # Finds wiki pages within 10km of the destination
        geo_url = "https://en.wikivoyage.org/w/api.php"
        geo_params = {
            "action": "query", "list": "geosearch", 
            "gscoord": f"{lat}|{lng}", "gsradius": 10000, "gslimit": 5, "format": "json"
        }
        r_geo = requests.get(geo_url, params=geo_params, timeout=2).json()
        if 'query' in r_geo and 'geosearch' in r_geo['query']:
            for item in r_geo['query']['geosearch']:
                # Get snippet for this place
                sights.append({"title": item['title'], "desc": "Popular local attraction."})

        # B. FETCH FOOD via Text Search (City first, then Country)
        def scrape_section(query, section_names):
            # 1. Search page
            r1 = requests.get("https://en.wikivoyage.org/w/api.php", 
                             params={"action": "query", "list": "search", "srsearch": query, "format": "json"}).json()
            if not r1.get('query', {}).get('search'): return []
            title = r1['query']['search'][0]['title']

            # 2. Get content
            r2 = requests.get("https://en.wikivoyage.org/w/api.php", 
                             params={"action": "query", "prop": "extracts", "titles": title, "explaintext": 1, "format": "json"}).json()
            page = next(iter(r2['query']['pages'].values()))
            text = page.get('extract', '')

            # 3. Extract items
            items = []
            for name in section_names:
                start = text.find(f"== {name} ==")
                if start != -1:
                    lines = text[start:].split('\n')[1:]
                    for line in lines:
                        if line.startswith("=="): break
                        if "*" in line and len(line) > 15:
                            clean = line.replace("*", "").strip()
                            parts = clean.split(" - ", 1) if " - " in clean else [clean, ""]
                            desc = parts[1] if parts[1] else "Authentic local dining experience."
                            items.append({"title": parts[0][:40], "desc": desc[:100]+"..."})
                            if len(items) >= 4: return items
            return items

        # Try City Food
        food = scrape_section(city, ["Eat", "Drink", "Food"])
        
        # Fallback to Country Food if empty (e.g. "Japan" instead of "Tokyo")
        if not food and country:
             food = scrape_section(country, ["Eat", "Drink", "Food"])

        # Fallback Sights if GPS failed
        if not sights:
            s_text = scrape_section(city, ["See", "Do", "Sights"])
            sights = s_text if s_text else [{"title": "City Center", "desc": "Explore the historic downtown."}]
            
        return {"see": sights[:4], "eat": food[:4]}

    except Exception as e:
        print(f"Guide Error: {e}")
        return {"see": [], "eat": []}

# --- 2. DUAL STRATEGY OPTIMIZER ---
def calculate_strategies(holiday_date, leaves_balance):
    h_date = datetime.strptime(holiday_date, "%Y-%m-%d")
    weekday = h_date.weekday() # Mon=0, Sun=6

    # STRATEGY A: "Lobang" (Quick/Conservative)
    # If Mon/Fri -> 3 Day weekend (0 leaves)
    # If Tue/Wed/Thu -> 4-5 Day block (1-2 leaves)
    lobang_plan = {}
    
    if weekday == 0: # Mon
        lobang_plan = {"name": "Long Weekend", "off": 3, "cost": 0, "start": -2, "end": 0}
    elif weekday == 4: # Fri
        lobang_plan = {"name": "Long Weekend", "off": 3, "cost": 0, "start": 0, "end": 2}
    elif weekday == 1: # Tue (Take Mon)
        lobang_plan = {"name": "4-Day Bridge", "off": 4, "cost": 1, "start": -3, "end": 0}
    elif weekday == 3: # Thu (Take Fri)
        lobang_plan = {"name": "4-Day Bridge", "off": 4, "cost": 1, "start": 0, "end": 3}
    elif weekday == 2: # Wed (Take Thu/Fri or Mon/Tue)
        lobang_plan = {"name": "5-Day Break", "off": 5, "cost": 2, "start": 0, "end": 4} # Wed-Sun
    else: # Sat/Sun
        lobang_plan = {"name": "Replacement Mon", "off": 3, "cost": 0, "start": 0, "end": 2}

    # STRATEGY B: "Shiok" (Maximize 9 Days)
    # Always bridging the full Sat-Sun-Mon...Sun week
    mon_of_week = h_date - timedelta(days=weekday)
    shiok_start_date = mon_of_week - timedelta(days=2) # Previous Sat
    
    # Calculate exact cost for 9 days (exclude Sat/Sun and the holiday itself)
    shiok_cost = 0
    for i in range(9):
        day = shiok_start_date + timedelta(days=i)
        if day.weekday() < 5 and day.date() != h_date.date():
            shiok_cost += 1
            
    shiok_plan = {"name": "9-Day Vacation", "off": 9, "cost": shiok_cost, "start_date": shiok_start_date}
    
    # Calculate exact dates for display
    def fmt(d): return d.strftime("%d %b")
    
    l_start = h_date + timedelta(days=lobang_plan['start'])
    l_end = h_date + timedelta(days=lobang_plan['end'])
    
    s_end = shiok_start_date + timedelta(days=8)

    return {
        "lobang": {
            "range": f"{fmt(l_start)} - {fmt(l_end)}",
            "leaves": lobang_plan['cost'],
            "off": lobang_plan['off'],
            "type": lobang_plan['name']
        },
        "shiok": {
            "range": f"{fmt(shiok_start_date)} - {fmt(s_end)}",
            "leaves": shiok_cost,
            "off": 9,
            "type": "Maximize Block"
        }
    }

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
    
    # Locations
    f_lat, f_lng = data['from']['latitude'], data['from']['longitude']
    t_lat, t_lng = data['to']['latitude'], data['to']['longitude']
    city = data['to']['name']
    country = data['to'].get('country', '')

    # 1. Weather
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={t_lat}&longitude={t_lng}&current_weather=true"
        w_data = requests.get(w_url, timeout=2).json()
        weather = f"{w_data['current_weather']['temperature']}°C"
    except: weather = "N/A"

    # 2. Budget
    try:
        R = 6371
        dlat, dlon = radians(t_lat - f_lat), radians(t_lng - f_lng)
        a = sin(dlat/2)**2 + cos(radians(f_lat)) * cos(radians(t_lat)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        dist_km = int(R * c)
        
        if dist_km < 1000: budget = "Low ($)"
        elif dist_km < 4000: budget = "Med ($$)"
        else: budget = "High ($$$)"
    except: dist_km, budget = 0, "-"

    # 3. Guide (New Logic)
    guide = get_wikivoyage(city, country, t_lat, t_lng)

    # 4. Holidays
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        holidays = []
        
        for h in h_data:
            strategies = calculate_strategies(h['date'], leaves_balance)
            holidays.append({
                "name": h['localName'],
                "date": datetime.strptime(h['date'], "%Y-%m-%d").strftime("%d %b"),
                "strategies": strategies
            })
    except: holidays = []

    return jsonify({
        "weather": weather,
        "dist": f"{dist_km}km",
        "budget": budget,
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)
