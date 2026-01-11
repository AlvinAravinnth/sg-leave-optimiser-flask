let fromData = { name: "Singapore", latitude: 1.29, longitude: 103.85 };
let toData = null;
let holidaysData = [];

// AUTOCOMPLETE SETUP
function setupSearch(inputId, listId, isFrom) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);

    input.addEventListener('input', async () => {
        const q = input.value;
        if (q.length < 2) { list.innerHTML = ''; return; }
        
        try {
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
                    if (isFrom) {
                        fromData = city;
                    } else {
                        toData = city;
                    }
                    // TRIGGER UPDATE IMMEDIATELY ON SELECTION
                    if (fromData && toData) generatePlan();
                };
                list.appendChild(div);
            });
        } catch (e) { console.error(e); }
    });
    
    // Hide list on click outside
    document.addEventListener('click', (e) => {
        if (e.target !== input) list.innerHTML = '';
    });
}

// MAIN LOGIC
async function generatePlan() {
    if (!fromData || !toData) return;
    
    const year = document.getElementById('year').value;
    const leavesBalance = document.getElementById('leaves').value;
    
    // Show loading state opacity
    const dash = document.getElementById('dashboard');
    dash.classList.remove('hidden');
    dash.style.opacity = '0.5';

    try {
        const res = await fetch('/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from: fromData, to: toData, year: year, leavesLeft: leavesBalance })
        });
        
        const data = await res.json();
        holidaysData = data.holidays;
        
        // Render Logistics
        document.getElementById('routeTitle').innerText = `${fromData.name} ➝ ${toData.name}`;
        document.getElementById('weatherVal').innerText = data.weather;
        document.getElementById('budgetVal').innerText = data.budget;
        document.getElementById('distVal').innerText = data.dist;
        
        // Render Guide
        const renderList = (id, items) => {
            const el = document.getElementById(id);
            if (!items || items.length === 0) {
                el.innerHTML = '<div class="item" style="opacity:0.6">No specific data found for this region.</div>';
                return;
            }
            el.innerHTML = '';
            items.forEach(i => {
                el.innerHTML += `<div class="item"><b style="color:#38BDF8">${i.title}</b><br>${i.desc}</div>`;
            });
        };
        renderList('seeList', data.guide.see);
        renderList('eatList', data.guide.eat);

        // Render Navigation Pills
        const nav = document.getElementById('holidayNav');
        nav.innerHTML = '';
        if (data.holidays.length > 0) {
            data.holidays.forEach((h, index) => {
                const btn = document.createElement('button');
                btn.className = index === 0 ? 'active' : '';
                btn.innerText = `${h.name} (${h.date})`;
                btn.onclick = () => updateHolidayStats(index);
                nav.appendChild(btn);
            });
            updateHolidayStats(0); // Select first by default
        } else {
            nav.innerHTML = '<div style="color:#94A3B8">No suitable holidays found.</div>';
        }

    } catch (error) {
        console.error("Plan failed:", error);
    } finally {
        dash.style.opacity = '1';
    }
}

function updateHolidayStats(index) {
    if (!holidaysData[index]) return;
    const h = holidaysData[index];
    
    document.getElementById('dateRange').innerText = h.range;
    document.getElementById('leavesVal').innerText = h.leaves;
    document.getElementById('stratLeaves').innerText = h.leaves;
    
    // Highlight active button
    const btns = document.querySelectorAll('.holiday-nav button');
    btns.forEach((b, i) => b.className = i === index ? 'active' : '');
}

// INIT
setupSearch('fromInput', 'fromList', true);
setupSearch('toInput', 'toList', false);
