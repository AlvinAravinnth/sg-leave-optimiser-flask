let currentHolidays = [];
let currentStrategy = 'lobang';
let selectedCity = null;

// Initialize Search Box Listener
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('toInput');
    if (input) {
        input.addEventListener('input', (e) => {
            const val = e.target.value;
            if (val.length > 2) searchCity(val);
            else document.getElementById('toList').style.display = 'none';
        });
    }
});

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
                list.style.display = 'none';
                generatePlan(city);
            };
            list.appendChild(item);
        });
        list.style.display = 'block';
    }
}

async function generatePlan(cityData) {
    document.getElementById('dashboard').classList.remove('hidden');
    
    // UPDATE HEADER INSTANTLY
    const tripHeader = document.querySelector('.trip-header p');
    if(tripHeader) tripHeader.innerText = `Singapore → ${cityData.name}`;

    // SHOW LOADING STATES
    document.getElementById('eatList').innerHTML = '<div style="padding:20px; opacity:0.6">🦁 Finding best food lobang...</div>';
    document.getElementById('seeList').innerHTML = '<div style="padding:20px; opacity:0.6">🌏 Scouting top sights...</div>';
    
    const payload = {
        year: document.getElementById('year').value,
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
        
        // Update Stats
        document.getElementById('weatherVal').innerText = data.weather;
        document.getElementById('budgetVal').innerText = data.budget;
        document.getElementById('distVal').innerText = data.dist;

        renderGuide(data.guide);
        renderHolidayNav();
        if (currentHolidays.length > 0) selectHoliday(0);

    } catch (e) { console.error(e); }
}

function selectHoliday(index) {
    const h = currentHolidays[index];
    const strategy = h.strategies[currentStrategy]; 

    document.getElementById('dateRange').innerText = strategy.range;
    document.getElementById('daysOffVal').innerText = `${strategy.off} Days Off`;
    document.getElementById('leavesVal').innerText = strategy.leaves;
    
    const recText = document.querySelector('.stat-box.leaves .sub');
    if (recText) {
        recText.innerText = strategy.rec; 
        recText.style.color = strategy.leaves > 0 ? '#F87171' : '#64748B';
        recText.style.fontSize = '0.8rem';
    }
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

// Nav and Strategy functions remain standard...
