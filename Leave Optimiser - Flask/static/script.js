let fromData = { name: "Singapore", latitude: 1.29, longitude: 103.85 };
let toData = null;
let holidaysData = [];

// Trigger function for simple inputs
function triggerUpdate() {
    if (toData) generatePlan();
}

function setupAutocomplete(inputId, listId, isFrom) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);

    input.addEventListener('input', async () => {
        const val = input.value;
        if (val.length < 2) { list.innerHTML = ''; return; }
        
        try {
            const res = await fetch(`/api/search?q=${val}`);
            const data = await res.json();
            
            list.innerHTML = '';
            data.forEach(city => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.innerText = `📍 ${city.name}, ${city.country || ''}`;
                item.onclick = () => {
                    input.value = city.name;
                    list.innerHTML = '';
                    if (isFrom) fromData = city;
                    else {
                        toData = city;
                        generatePlan(); // AUTO TRIGGER
                    }
                };
                list.appendChild(item);
            });
        } catch(e) { console.error(e); }
    });
    
    // Close on click outside
    document.addEventListener('click', (e) => {
        if (e.target !== input) list.innerHTML = '';
    });
}

async function generatePlan() {
    if (!fromData || !toData) return;
    
    const year = document.getElementById('year').value;
    const leaves = document.getElementById('leaves').value;
    const dash = document.getElementById('dashboard');
    
    dash.classList.remove('hidden');
    dash.style.opacity = '0.6'; // Loading effect

    try {
        const res = await fetch('/api/plan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ from: fromData, to: toData, year: year, leavesLeft: leaves })
        });
        
        const data = await res.json();
        holidaysData = data.holidays;

        // Populate Logistics
        document.getElementById('routeTitle').innerText = `${fromData.name} ➝ ${toData.name}`;
        document.getElementById('weatherVal').innerText = data.weather;
        document.getElementById('budgetVal').innerText = data.budget;
        document.getElementById('distVal').innerText = data.dist;

        // Populate Guide
        const fillList = (id, items) => {
            const el = document.getElementById(id);
            el.innerHTML = '';
            if(!items || items.length === 0) {
                el.innerHTML = '<div style="color:#64748B; padding:10px;">No data found. Try general search.</div>';
                return;
            }
            items.forEach(i => {
                el.innerHTML += `
                    <div class="guide-item">
                        <span class="guide-title">${i.title}</span>
                        <span class="guide-desc">${i.desc}</span>
                    </div>`;
            });
        };
        fillList('seeList', data.guide.see);
        fillList('eatList', data.guide.eat);

        // Populate Pills
        const nav = document.getElementById('holidayNav');
        nav.innerHTML = '';
        data.holidays.forEach((h, idx) => {
            const btn = document.createElement('button');
            btn.innerText = `${h.name} (${h.date})`;
            btn.className = idx === 0 ? 'active' : '';
            btn.onclick = () => showHoliday(idx);
            nav.appendChild(btn);
        });
        
        showHoliday(0);

    } catch(e) { console.error(e); }
    finally { dash.style.opacity = '1'; }
}

function showHoliday(idx) {
    if (!holidaysData[idx]) return;
    const h = holidaysData[idx];
    
    document.getElementById('dateRange').innerText = h.range;
    document.getElementById('daysOffVal').innerText = `${h.off} Days Off`;
    document.getElementById('leavesVal').innerText = h.leaves;
    document.getElementById('aiNote').innerText = h.note; // The AI strategy text

    // Update active pill
    const btns = document.querySelectorAll('#holidayNav button');
    btns.forEach((b, i) => b.className = i === idx ? 'active' : '');
}

// Init
setupAutocomplete('fromInput', 'fromList', true);
setupAutocomplete('toInput', 'toList', false);
