let fromData = { name: "Singapore", latitude: 1.29, longitude: 103.85 };
let toData = null;
let holidaysData = [];

// AUTOCOMPLETE LOGIC
async function setupSearch(inputId, listId, isFrom) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);

    input.addEventListener('input', async () => {
        const q = input.value;
        if (q.length < 2) { list.innerHTML = ''; return; }
        
        const res = await fetch(`/api/search?q=${q}`);
        const data = await res.json();
        
        list.innerHTML = '';
        data.forEach(city => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.innerText = `📍 ${city.name}, ${city.country || ''}`;
            div.onclick = () => {
                input.value = city.name;
                list.innerHTML = '';
                if (isFrom) fromData = city;
                else {
                    toData = city;
                    generatePlan(); // Trigger plan immediately on selection
                }
            };
            list.appendChild(div);
        });
    });
}

// MAIN LOGIC
async function generatePlan() {
    if (!fromData || !toData) return;
    
    const year = document.getElementById('year').value;
    document.getElementById('dashboard').classList.add('loading');

    const res = await fetch('/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from: fromData, to: toData, year: year })
    });
    
    const data = await res.json();
    holidaysData = data.holidays;
    
    // Render Dashboard
    document.getElementById('routeTitle').innerText = `${fromData.name} ➝ ${toData.name}`;
    document.getElementById('weatherVal').innerText = data.weather;
    document.getElementById('budgetVal').innerText = data.budget;
    document.getElementById('distVal').innerText = data.dist;
    
    // Render Guide
    const renderList = (id, items) => {
        const el = document.getElementById(id);
        el.innerHTML = items.length ? '' : '<div class="item">No data available</div>';
        items.forEach(i => {
            el.innerHTML += `<div class="item"><b>${i.title}</b><br>${i.desc}</div>`;
        });
    };
    renderList('seeList', data.guide.see);
    renderList('eatList', data.guide.eat);

    // Render Pills
    const nav = document.getElementById('holidayNav');
    nav.innerHTML = '';
    data.holidays.forEach((h, index) => {
        const btn = document.createElement('button');
        btn.className = index === 0 ? 'active' : '';
        btn.innerText = `${h.name} (${h.date})`;
        btn.onclick = () => updateHolidayStats(index);
        nav.appendChild(btn);
    });

    updateHolidayStats(0); // Select first by default
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('dashboard').classList.remove('loading');
}

function updateHolidayStats(index) {
    if (!holidaysData[index]) return;
    const h = holidaysData[index];
    document.getElementById('dateRange').innerText = h.range;
    document.getElementById('leavesVal').innerText = h.leaves;
    
    // Toggle active pill styling
    const btns = document.querySelectorAll('.holiday-nav button');
    btns.forEach((b, i) => b.className = i === index ? 'active' : '');
}

// INIT
setupSearch('fromInput', 'fromList', true);
setupSearch('toInput', 'toList', false);