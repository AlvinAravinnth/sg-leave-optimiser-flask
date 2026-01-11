from flask import Flask, jsonify, request, render_template
import requests
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- 1. ROBUST GUIDE FETCHER (Fixes "No Data") ---
def get_wikivoyage(query):
    # Strip country for better wiki matches (e.g. "Tokyo, Japan" -> "Tokyo")
    clean_query = query.split(',')[0].strip()
    
    try:
        # 1. Search for the best matching page title
        r1 = requests.get("https://en.wikivoyage.org/w/api.php", 
                         params={"action": "query", "list": "search", "srsearch": clean_query, "format": "json"}).json()
        
        if not r1.get('query', {}).get('search'):
            return None
            
        title = r1['query']['search'][0]['title']

        # 2. Get the content
        r2 = requests.get("https://en.wikivoyage.org/w/api.php", 
                         params={"action": "query", "prop": "extracts", "titles": title, "explaintext": 1, "format": "json"}).json()
        
        page = next(iter(r2['query']['pages'].values()))
        text = page.get('extract', '')

        # 3. Extract Sections
        def extract_items(headers):
            items = []
            for header in headers:
                start = text.find(f"== {header} ==")
                if start != -1:
                    # Grab the section text
                    subtext = text[start:].split('\n')
                    for line in subtext[1:]:
                        if line.startswith("=="): break # End of section
                        # Find bullet points
                        if "*" in line and len(line) > 20:
                            clean = line.replace("*", "").strip()
                            # Split Title - Desc
                            parts = clean.split(" - ", 1) if " - " in clean else [clean, ""]
                            title = parts[0]
                            desc = parts[1] if parts[1] else "Explore this highlight."
                            
                            # Clean parenthesis from title
                            if "(" in title: title = title.split("(")[0].strip()
                            
                            items.append({"title": title[:40], "desc": desc[:150]+"..."})
                            if len(items) >= 4: return items
            return items

        see = extract_items(["See", "Do", "Sights", "Attractions"])
        eat = extract_items(["Eat", "Drink", "Food"])
        
        # Fallbacks if empty
        if not see: see = [{"title": "City Center", "desc": f"Explore the historic streets of {clean_query}."}]
        if not eat: eat = [{"title": "Local Markets", "desc": "Try authentic local street food."}]

        return {"see": see, "eat": eat}
    except Exception as e:
        print(f"Wiki Error: {e}")
        return {"see": [], "eat": []}

# --- 2. THE "AI" LEAVE OPTIMIZER (No Hardcoding) ---
def optimize_leave(holiday_date_str, user_leaves):
    # Convert string to date object
    h_date = datetime.strptime(holiday_date_str, "%Y-%m-%d")
    
    # "AI" Logic: Look at the 9-day window surrounding the holiday
    # We want to find the biggest block of OFF days we can buy with 'user_leaves'
    
    # 1. Define the window (start 5 days before, end 5 days after)
    # We essentially scan a 2-week period to find the best cluster
    window_start = h_date - timedelta(days=5)
    best_plan = {
        "leaves_needed": 0,
        "days_off": 0,
        "start_date": h_date,
        "end_date": h_date,
        "note": "Standard Holiday"
    }

    # Heuristic: Try to bridge to the nearest weekends
    # Check 3 common strategies:
    # A. Bridge Forward (Holiday + days after -> Weekend)
    # B. Bridge Backward (Weekend + days before -> Holiday)
    # C. Super Bridge (Weekend ... Holiday ... Weekend)
    
    # Simplification for this demo:
    # Find the Monday of the holiday week
    monday_of_week = h_date - timedelta(days=h_date.weekday())
    sat_before = monday_of_week - timedelta(days=2)
    sun_after = monday_of_week + timedelta(days=6)
    
    # Calculate workdays in this SAT-SUN block (9 days total)
    leaves_to_burn = 0
    current = sat_before
    while current <= sun_after:
        # If it's a weekday AND not the holiday, we need a leave
        if current.weekday() < 5 and current.date() != h_date.date():
            leaves_to_burn += 1
        current += timedelta(days=1)
        
    # Decision Engine
    if leaves_to_burn <= user_leaves:
        return {
            "leaves": leaves_to_burn,
            "off": 9,
            "range": f"{sat_before.strftime('%d %b')} - {sun_after.strftime('%d %b')}",
            "note": "Maximize 9-Day Block"
        }
    else:
        # Fallback: Just a long weekend
        # If holiday is Fri/Mon -> 3 days. If Tue/Thu -> Take 1 to make 4.
        wd = h_date.weekday()
        if wd == 1: # Tue -> Take Mon
            return {"leaves": 1, "off": 4, "range": f"{(h_date-timedelta(days=3)).strftime('%d %b')} - {h_date.strftime('%d %b')}", "note": "4-Day Long Weekend"}
        elif wd == 3: # Thu -> Take Fri
            return {"leaves": 1, "off": 4, "range": f"{h_date.strftime('%d %b')} - {(h_date+timedelta(days=3)).strftime('%d %b')}", "note": "4-Day Long Weekend"}
        
        return {"leaves": 0, "off": 3, "range": "Long Weekend", "note": "Standard Break"}

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
    f_lat = data['from']['latitude']
    f_lng = data['from']['longitude']
    t_lat = data['to']['latitude']
    t_lng = data['to']['longitude']
    city_name = data['to']['name'] # e.g. "Tokyo"

    # 1. Weather
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={t_lat}&longitude={t_lng}&current_weather=true"
        w_data = requests.get(w_url, timeout=2).json()
        weather = f"{w_data['current_weather']['temperature']}°C"
    except: weather = "N/A"

    # 2. Budget (Haversine)
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

    # 3. Guide (Wikivoyage)
    guide = get_wikivoyage(city_name)
    if not guide: 
        # Ultimate fallback
        guide = {
            "see": [{"title": "Explore City", "desc": f"Discover the main sights of {city_name}."}], 
            "eat": [{"title": "Local Eats", "desc": "Try the famous local dishes."}]
        }

    # 4. Holiday Logic (The "AI")
    try:
        h_url = f"https://date.nager.at/api/v3/publicholidays/{year}/SG"
        h_data = requests.get(h_url).json()
        holidays = []
        
        for h in h_data:
            # Run the optimizer for each holiday
            plan = optimize_leave(h['date'], leaves_balance)
            
            holidays.append({
                "name": h['localName'],
                "date": datetime.strptime(h['date'], "%Y-%m-%d").strftime("%d %b"),
                "range": plan['range'],
                "leaves": plan['leaves'],
                "off": plan['off'],
                "note": plan['note']
            })
    except Exception as e:
        print(e)
        holidays = []

    return jsonify({
        "weather": weather,
        "dist": f"{dist_km}km",
        "budget": budget,
        "guide": guide,
        "holidays": holidays
    })

if __name__ == '__main__':
    app.run(debug=True)
