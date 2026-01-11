let selectedCity = null;

// Destination Search Dropdown
document.getElementById('toInput').addEventListener('input', async (e) => {
    const val = e.target.value;
    const list = document.getElementById('toList');
    if (val.length < 3) { list.classList.add('hidden'); return; }

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
});

function showLoading() {
    const skeleton = '<div class="skeleton-loading"></div><div class="skeleton-loading"></div>';
    document.getElementById('seeList').innerHTML = skeleton;
    document.getElementById('eatList').innerHTML = skeleton;
    document.getElementById('dateRange').innerText = '...';
    document.getElementById('budgetVal').innerText = '...';
    document.getElementById('leavesVal').innerText = 'Analyzing dates...';
}

async function fetchWeather(lat, lon) {
    try {
        const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
        const data = await res.json();
        return `${Math.round(data.current_weather.temperature)}°C`;
    } catch (err) { return "N/A"; }
}

async function generatePlan() {
    if (!selectedCity) return;
    
    // Switch UI from Search to Dashboard
    document.querySelector('.input-panel').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('destName').innerText = selectedCity.name;
    
    showLoading(); 

    // Live Weather Fetch
    const weather = await fetchWeather(selectedCity.latitude, selectedCity.longitude);
    document.getElementById('weatherVal').innerText = weather;

    // AI Plan Fetch
    try {
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
            renderGuide(data.plan.itinerary);
        }
    } catch (err) { console.error("Error:", err); }
}

function renderGuide(itin) {
    const see = document.getElementById('seeList');
    const eat = document.getElementById('eatList');
    see.innerHTML = ''; eat.innerHTML = '';
    itin.see.forEach(i => see.innerHTML += `<div class="guide-item"><b>${i.title}</b><p>${i.desc}</p></div>`);
    itin.eat.forEach(i => eat.innerHTML += `<div class="guide-item"><b>${i.title}</b><p>${i.desc}</p></div>`);
}

function resetSearch() {
    document.getElementById('dashboard').classList.add('hidden');
    document.querySelector('.input-panel').classList.remove('hidden');
    document.getElementById('toInput').value = '';
    selectedCity = null;
}
