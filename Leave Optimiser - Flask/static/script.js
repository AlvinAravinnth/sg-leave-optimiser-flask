let currentHolidays = [];
let currentStrategy = 'lobang';
let selectedCity = null;

async function triggerUpdate() {
    const city = document.getElementById('toInput').value;
    if (city.length > 2) searchCity(city);
}

// 1. Search for City (Coordinates)
async function searchCity(query) {
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
                list.innerHTML = '';
                generatePlan(city); // Start Planning
            };
            list.appendChild(item);
        });
        list.style.display = 'block';
    }
}

// 2. Generate Plan
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
}

// 3. Render Holiday Navigation (Pills)
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

    // Activate first one
    if (container.firstChild) container.firstChild.click();
}

// 4. Update Stats based on Selection
function selectHoliday(index) {
    const h = currentHolidays[index];
    const strategy = h.strategies[currentStrategy]; // 'lobang' or 'shiok'

    document.getElementById('dateRange').innerText = strategy.range;
    document.getElementById('daysOffVal').innerText = `${strategy.off} Days Off`;
    
    document.getElementById('leavesVal').innerText = strategy.leaves;
    
    // --- THIS IS THE UPDATE FOR THE TEXT ---
    // Target the "Leaves Used" text and replace it with "Apply on..."
    const recText = document.querySelector('.stat-box.leaves .sub');
    if (recText) {
        recText.innerText = strategy.rec ? `Apply: ${strategy.rec}` : 'Leaves Used';
        recText.style.color = strategy.leaves > 0 ? '#F87171' : '#64748B'; // Red if taking leave
    }
}

function setStrategy(type) {
    currentStrategy = type;
    document.getElementById('btnLobang').classList.toggle('active', type === 'lobang');
    document.getElementById('btnShiok').classList.toggle('active', type === 'shiok');
    
    // Re-render current selection
    const activeBtn = document.querySelector('#holidayNav button.active');
    if (activeBtn) activeBtn.click();
}

function renderGuide(guide) {
    const seeList = document.getElementById('seeList');
    const eatList = document.getElementById('eatList');
    
    seeList.innerHTML = '';
    eatList.innerHTML = '';

    guide.see.forEach(item => {
        seeList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });

    guide.eat.forEach(item => {
        eatList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });
}
