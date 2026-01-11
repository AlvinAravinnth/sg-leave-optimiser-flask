let selectedCity = null;

// Handle Destination Search Dropdown
document.getElementById('toInput').addEventListener('input', async (e) => {
    const val = e.target.value;
    const list = document.getElementById('toList');
    if (val.length < 3) { list.classList.add('hidden'); return; }

    try {
        const res = await fetch(`/api/search?q=${val}`);
        const cities = await res.json();
        list.innerHTML = '';
        if (cities && cities.length > 0) {
            list.classList.remove('hidden');
            cities.forEach(city => {
                const div = document.createElement('div');
                div.className = 'suggestion-item';
                div.innerText = `${city.name}, ${city.country}`;
                div.onclick = () => {
                    selectedCity = city;
                    document.getElementById('toInput').value = city.name;
                    list.innerHTML = '';
                    list.classList.add('hidden');
                    generatePlan();
                };
                list.appendChild(div);
            });
        }
    } catch (err) { console.error("Search error:", err); }
});

async function fetchWeather(lat, lon) {
    try {
        const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
        const data = await res.json();
        return `${data.current_weather.temperature}°C`;
    } catch (err) { return "N/A"; }
}

async function generatePlan() {
    if (!selectedCity) return;
    
    document.querySelector('.input-panel').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('destName').innerText = selectedCity.name;
    
    // Fetch live weather
    const weather = await fetchWeather(selectedCity.latitude, selectedCity.longitude);
    document.getElementById('weatherVal').innerText = weather;

    const res = await fetch('/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            leavesLeft: document.getElementById('leaves').value,
            to: selectedCity
        })
    });

    const data = await res.json();
    if (data.plan) {
        document.getElementById('dateRange').innerText = data.plan.duration;
        document.getElementById('leavesVal').innerText = data.plan.leave_plan;
        document.getElementById('budgetVal').innerText = data.plan.budget;
        document.getElementById('distVal').innerText = data.dist;
        renderGuide(data.plan.itinerary);
    }
}

function renderGuide(itin) {
    const see = document.getElementById('seeList');
    const eat = document.getElementById('eatList');
    see.innerHTML = ''; eat.innerHTML = '';
    itin.see.forEach(i => see.innerHTML += `<div class="guide-item"><span class="guide-title">${i.title}</span><span class="guide-desc">${i.desc}</span></div>`);
    itin.eat.forEach(i => eat.innerHTML += `<div class="guide-item"><span class="guide-title">${i.title}</span><span class="guide-desc">${i.desc}</span></div>`);
}

// Reset Button Logic
function resetSearch() {
    document.getElementById('dashboard').classList.add('hidden');
    document.querySelector('.input-panel').classList.remove('hidden');
    document.getElementById('toInput').value = '';
    selectedCity = null;
}
