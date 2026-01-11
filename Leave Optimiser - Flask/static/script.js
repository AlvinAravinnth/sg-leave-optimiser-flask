let currentHolidays = [];
let currentStrategy = 'lobang';
let selectedCity = null;

// --- 1. INITIALIZATION (Connect Search Box) ---
document.addEventListener('DOMContentLoaded', () => {
    // Connect the input box to the search function
    const input = document.getElementById('toInput');
    if (input) {
        input.addEventListener('input', (e) => {
            const val = e.target.value;
            if (val.length > 2) {
                searchCity(val);
            } else {
                document.getElementById('toList').style.display = 'none';
            }
        });
    }
});

// --- 2. SEARCH LOGIC ---
async function searchCity(query) {
    try {
        const res = await fetch(`/api/search?q=${query}`);
        const data = await res.json();
        
        const list = document.getElementById('toList');
        list.innerHTML = '';
        
        if (data.length > 0) {
            data.forEach(city => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.innerText = `${city.name}, ${city.country || ''}`;
                item.onclick = () => {
                    document.getElementById('toInput').value = city.name;
                    selectedCity = city;
                    list.style.display = 'none'; // Hide list after selection
                    generatePlan(city); // Start Planning
                };
                list.appendChild(item);
            });
            list.style.display = 'block';
        } else {
            list.style.display = 'none';
        }
    } catch (e) {
        console.error("Search failed:", e);
    }
}

// --- 3. GENERATE PLAN ---
async function generatePlan(cityData) {
    // Show loading state
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('eatList').innerHTML = '<div style="color:#94A3B8; padding:10px;">🦁 Loading Lobang...</div>';
    document.getElementById('seeList').innerHTML = '<div style="color:#94A3B8; padding:10px;">✈️ Kiasu-ing best spots...</div>';

    const payload = {
        year: document.getElementById('year').value,
        leavesLeft: document.getElementById('leaves').value,
        from: { latitude: 1.3521, longitude: 103.8198 }, // Singapore
        to: cityData
    };

    try {
        const res = await fetch('/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        currentHolidays = data.holidays;
        
        // Update Stats
        document.getElementById('weatherVal').innerText = data.weather;
        document.getElementById('budgetVal').innerText = data.budget[1]; // "Med ($$)"
        document.getElementById('distVal').innerText = data.budget[0]; // "1500km"

        // Render Guide
        renderGuide(data.guide);

        // Render Holiday Pills
        renderHolidayNav();

        // Select first holiday by default
        if (currentHolidays.length > 0) {
            selectHoliday(0);
        }
    } catch (e) {
        console.error("Planning failed:", e);
    }
}

// --- 4. RENDER UI ---
function renderHolidayNav() {
    const container = document.getElementById('holidayNav');
    container.innerHTML = '';
    
    currentHolidays.forEach((h, index) => {
        const btn = document.createElement('button');
        btn.innerText = `${h.date} - ${h.name}`;
        btn.onclick = () => {
            document.querySelectorAll('#holidayNav button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectHoliday(index);
        };
        container.appendChild(btn);
    });

    if (container.firstChild) container.firstChild.click();
}

function selectHoliday(index) {
    const h = currentHolidays[index];
    const strategy = h.strategies[currentStrategy]; // 'lobang' or 'shiok'

    document.getElementById('dateRange').innerText = strategy.range;
    document.getElementById('daysOffVal').innerText = `${strategy.off} Days Off`;
    document.getElementById('leavesVal').innerText = strategy.leaves;
    
    // UPDATE "Cost" Text to show Recommendation
    const recText = document.querySelector('.stat-box.leaves .sub');
    if (recText) {
        // If API provided a recommendation (rec), show it. Otherwise default to "Leaves Used"
        if (strategy.rec) {
            recText.innerText = `Apply: ${strategy.rec}`;
            recText.style.color = '#F87171'; // Red highlight
            recText.style.fontSize = '0.9rem';
        } else {
            recText.innerText = 'Leaves Used';
            recText.style.color = '#64748B';
        }
    }
}

function setStrategy(type) {
    currentStrategy = type;
    document.getElementById('btnLobang').classList.toggle('active', type === 'lobang');
    document.getElementById('btnShiok').classList.toggle('active', type === 'shiok');
    
    // Refresh current view
    const activeBtn = document.querySelector('#holidayNav button.active');
    if (activeBtn) activeBtn.click();
}

function renderGuide(guide) {
    const seeList = document.getElementById('seeList');
    const eatList = document.getElementById('eatList');
    
    seeList.innerHTML = '';
    eatList.innerHTML = '';

    // Handle Fallback/Error display
    const seeItems = guide.see || [];
    const eatItems = guide.eat || [];

    seeItems.forEach(item => {
        seeList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });

    eatItems.forEach(item => {
        eatList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });
}
