let fromData = { name: "Singapore", latitude: 1.29, longitude: 103.85 };
let toData = null;
let holidaysData = [];
let currentHolidayIdx = 0;
let currentStrategy = 'lobang'; // 'lobang' (Quick) or 'shiok' (Max)

function triggerUpdate() {
    if (toData) generatePlan();
}

function setStrategy(mode) {
    currentStrategy = mode;
    // Update buttons
    document.getElementById('btnLobang').className = mode === 'lobang' ? 'active' : '';
    document.getElementById('btnShiok').className = mode === 'shiok' ? 'active' : '';
    // Refresh view
    renderHolidayStats();
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
                        generatePlan();
                    }
                };
                list.appendChild(item);
            });
        } catch(e) {}
    });
    
    document.addEventListener('click', (e) => { if (e.target !== input) list.innerHTML = ''; });
}

async function generatePlan() {
    if (!fromData || !toData) return;
    
    const dash = document.getElementById('dashboard');
    dash.classList.remove('hidden');
    dash.style.opacity = '0.5';

    try {
        const res = await fetch('/api/plan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                from: fromData, to: toData, 
                year: document.getElementById('year').value, 
                leavesLeft: document.getElementById('leaves').value 
            })
        });
        
        const data = await res.json();
        holidaysData = data.holidays;

        // Static Info
        document.getElementById('routeTitle').innerText = `${fromData.name} ➝ ${toData.name}`;
        document.getElementById('weatherVal').innerText = data.weather;
        document.getElementById('budgetVal').innerText = data.budget;
        document.getElementById('distVal').innerText = data.dist;

        // Guide
        const fill = (id, items) => {
            const el = document.getElementById(id);
            el.innerHTML = items.length ? '' : '<div style="opacity:0.6;font-size:13px">No specific info found.</div>';
            items.forEach(i => {
                el.innerHTML += `<div class="guide-item"><b style="color:#38BDF8">${i.title}</b><div style="font-size:13px; color:#CBD5E1">${i.desc}</div></div>`;
            });
        };
        fill('seeList', data.guide.see);
        fill('eatList', data.guide.eat);

        // Nav
        const nav = document.getElementById('holidayNav');
        nav.innerHTML = '';
        data.holidays.forEach((h, idx) => {
            const btn = document.createElement('button');
            btn.innerText = `${h.name} (${h.date})`;
            btn.onclick = () => { currentHolidayIdx = idx; renderHolidayStats(); };
            nav.appendChild(btn);
        });

        // Default to first holiday
        currentHolidayIdx = 0;
        renderHolidayStats();

    } catch(e) { console.error(e); }
    finally { dash.style.opacity = '1'; }
}

function renderHolidayStats() {
    if (!holidaysData[currentHolidayIdx]) return;
    
    // Get plan based on current strategy selection
    const h = holidaysData[currentHolidayIdx];
    const plan = h.strategies[currentStrategy];
    
    document.getElementById('dateRange').innerText = plan.range;
    document.getElementById('daysOffVal').innerText = `${plan.off} Days Off`;
    document.getElementById('leavesVal').innerText = plan.leaves;
    
    // Highlight nav
    const btns = document.querySelectorAll('#holidayNav button');
    btns.forEach((b, i) => b.className = i === currentHolidayIdx ? 'active' : '');
}

setupAutocomplete('fromInput', 'fromList', true);
setupAutocomplete('toInput', 'toList', false);
