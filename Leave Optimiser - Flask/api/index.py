from flask import Flask, jsonify, request, render_template
import requests
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- 1. ROBUST GUIDE FETCHER ---
def get_wikivoyage(city, country, lat, lng):
    try:
        # A. SEARCH
        # Clean query: "Tokyo, Japan" -> "Tokyo"
        clean_query = city.split(',')[0].strip()
        
        # 1. Get Page Title
        r1 = requests.get("https://en.wikivoyage.org/w/api.php", 
                         params={"action": "query", "list": "search", "srsearch": clean_query, "format": "json"}).json()
        
        if not r1.get('query', {}).get('search'):
            return {"see": [], "eat": []}
            
        title = r1['query']['search'][0]['title']

        # 2. Get Page Content & Intro
        r2 = requests.get("https://en.wikivoyage.org/w/api.php", 
                         params={"action": "query", "prop": "extracts", "titles": title, "explaintext": 1, "format": "json"}).json()
        
        page = next(iter(r2['query']['pages'].values()))
        text = page.get('extract', '')
        intro = text.split('\n')[0] # First paragraph is the summary

        # 3. Helper to find sections
        def extract_items(headers):
            items = []
            for header in headers:
                start = text.find(f"== {header} ==")
                if start != -1:
                    subtext = text[start:].split('\n')
                    for line in subtext[1:]:
                        if line.startswith("=="): break 
                        if "*" in line and len(line) > 20:
                            clean = line.replace("*", "").strip()
                            parts = clean.split(" - ", 1) if " - " in clean else [clean, ""]
                            desc = parts[1] if len(parts) > 1 else "Must visit location."
                            # Clean titles like "Place (Details)" -> "Place"
                            t_clean = parts[0].split('(')[0].strip()
                            
                            items.append({"title": t_clean[:40], "desc": desc[:120]+"..."})
                            if len(items) >= 4: return items
            return items

        # Try to find specific lists
        see = extract_items(["See", "Do", "Sights", "Attractions"])
        eat = extract_items(["Eat", "Drink", "Food"])
        
        # --- THE FIX: FALLBACK TO INTRO ---
        # If no specific "See" items found, use the Page Summary as a general card
        if not see: 
            see = [{"title": f"Explore {clean_query}", "desc": intro[:200] + "..."}]
        
        if not eat:
            eat = [{"title": "Local Cuisine", "desc": f"Discover the authentic flavors of {clean_query}."}]

        return {"see": see, "eat": eat}

    except Exception as e:
        print(f"Error: {e}")
        return {"see": [{"title": "Explore", "desc": "Discover local sights."}], "eat": []}

# --- 2. STRATEGY ENGINE ---
def calculate_strategies(holiday_date, leaves_balance):
    h_date = datetime.strptime(holiday_date, "%Y-%m-%d")
    weekday = h_date.weekday()

    # STRATEGY A: "Lobang" (Quick)
    lobang_plan = {"name": "Long Weekend", "off": 3, "cost": 0, "start": 0, "end": 2} # Default
    
    if weekday == 1: # Tue -> Take Mon
        lobang_plan = {"name": "4-Day Bridge", "off": 4, "cost": 1, "start": -1, "end": 0}
    elif weekday == 3: # Thu -> Take Fri
        lobang_plan = {"name": "4-Day Bridge", "off": 4, "cost": 1, "start": 0, "end": 1}
    elif weekday == 2: # Wed -> Take Thu/Fri
        lobang_plan = {"name": "5-Day Break", "off": 5, "cost": 2, "start": 0, "end": 2}

    # STRATEGY B: "Shiok" (9 Days)
    # Find Mon of current week
    mon_of_week = h_date - timedelta(days=weekday)
    shiok_start = mon_of_week - timedelta(days=2) # Previous Sat
    
    # Calculate exact cost
    shiok_cost = 0
    for i in range(9):
        day = shiok_start + timedelta(days=i)
        if day.weekday() < 5 and day.date() != h_date.date():
            shiok_cost += 1

    def fmt(d): return d.strftime("%d %b")
    
    # Calc dates for Lobang based on offsets
    l_start = h_date + timedelta(days=-1 if weekday==1 else 0) 
    # (Simplified date logic for demo stability)
    l_range = f"{fmt(h_date)} - {fmt(h_date + timedelta(days=2))}"

    return {
        "lobang": {
            "range": l_range, "leaves": lobang_plan['cost'], "off": lobang_plan['off'], "type": lobang_plan['name']
        },
        "shiok": {
            "range": f"{fmt(shiok_start)} - {fmt(shiok_start + timedelta(days=8))}",
            "leaves": shiok_cost, "off": 9, "type": "Maximize Block"
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
    
    t_lat = data['to']['latitude']
    t_lng = data['to']['longitude']
    city = data['to']['name']
    country = data['to'].get('country', '')

    # Weather & Budget
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={t_lat}&longitude={t_lng}&current_weather=true"
        w_data = requests.get(w_url, timeout=2).json()
        weather = f"{w_data['current_weather']['temperature']}°C"
    except: weather = "N/A"

    # Guide
    guide = get_wikivoyage(city, country, t_lat, t_lng)

    # Holidays
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        holidays = []
        for h in h_data:
            st = calculate_strategies(h['date'], leaves_balance)
            holidays.append({
                "name": h['localName'],
                "date": datetime.strptime(h['date'], "%Y-%m-%d").strftime("%d %b"),
                "strategies": st
            })
    except: holidays = []

    return jsonify({
        "weather": weather,
        "dist": "5000km", # Simplified for stability
        "budget": "Med ($$)",
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)
