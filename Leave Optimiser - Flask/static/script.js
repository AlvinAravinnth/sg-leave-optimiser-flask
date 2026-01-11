let currentHolidays = [];
let currentStrategy = 'lobang';
let selectedCity = null;

// 1. Initialize Search Listener
document.addEventListener('DOMContentLoaded', () => {
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

// 2. Search Logic
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
                    list.style.display = 'none';
                    generatePlan(city);
                };
                list.appendChild(item);
            });
            list.style.display = 'block';
        } else {
            list.style.display = 'none';
        }
    } catch (e) { console.error(e); }
}

// 3. Generate Plan
async function generatePlan(cityData) {
    document.getElementById('dashboard').classList.remove('hidden');
    // Loading State
    document.getElementById('eatList').innerHTML = '<div style="color:#94A3B8; padding:10px;">🦁 Loading...</div>';
    document.getElementById('seeList').innerHTML = '<div style="color:#94A3B8; padding:10px;">✈️ Planning...</div>';

    const payload = {
        year: document.getElementById('year').value,
        leavesLeft: document.getElementById('leaves').value,
        from: { latitude: 1.3521, longitude: 103.8198 },
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
        
        // --- FIX: Budget Display ---
        document.getElementById('weatherVal').innerText = data.weather;
        // Using direct values now, no array indexing [1]
        document.getElementById('budgetVal').innerText = data.budget; 
        document.getElementById('distVal').innerText = data.dist;

        renderGuide(data.guide);
        renderHolidayNav();

        if (currentHolidays.length > 0) selectHoliday(0);

    } catch (e) { console.error(e); }
}

// 4. Render UI
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
    const strategy = h.strategies[currentStrategy]; 

    document.getElementById('dateRange').innerText = strategy.range;
    document.getElementById('daysOffVal').innerText = `${strategy.off} Days Off`;
    document.getElementById('leavesVal').innerText = strategy.leaves;
    
    // --- FIX: Update Recommendation Text ---
    const recText = document.querySelector('.stat-box.leaves .sub');
    if (recText) {
        if (strategy.rec) {
            recText.innerText = strategy.rec; // Shows "Take leave on..."
            recText.style.color = strategy.leaves > 0 ? '#F87171' : '#64748B';
            recText.style.fontSize = '0.85rem';
        } else {
            recText.innerText = 'Leaves Used';
        }
    }
}

function setStrategy(type) {
    currentStrategy = type;
    document.getElementById('btnLobang').classList.toggle('active', type === 'lobang');
    document.getElementById('btnShiok').classList.toggle('active', type === 'shiok');
    const activeBtn = document.querySelector('#holidayNav button.active');
    if (activeBtn) activeBtn.click();
}

function renderGuide(guide) {
    const seeList = document.getElementById('seeList');
    const eatList = document.getElementById('eatList');
    seeList.innerHTML = '';
    eatList.innerHTML = '';

    (guide.see || []).forEach(item => {
        seeList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });

    (guide.eat || []).forEach(item => {
        eatList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });
}
