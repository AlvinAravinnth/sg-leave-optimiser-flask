let selectedCity = null;

document.getElementById('toInput').addEventListener('input', async (e) => {
    const val = e.target.value;
    if (val.length < 3) return;
    const res = await fetch(`/api/search?q=${val}`);
    const cities = await res.json();
    const list = document.getElementById('toList');
    list.innerHTML = '';
    cities.forEach(city => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.innerText = `${city.name}, ${city.country}`;
        div.onclick = () => {
            selectedCity = city;
            document.getElementById('toInput').value = city.name;
            list.innerHTML = '';
            generatePlan(); // THIS UPDATES THE DASHBOARD
        };
        list.appendChild(div);
    });
});

async function generatePlan() {
    if (!selectedCity) return;
    
    // Show dashboard immediately
    const dashboard = document.getElementById('dashboard');
    dashboard.classList.remove('hidden');
    
    // Set loading state
    document.getElementById('destName').innerText = selectedCity.name;
    document.getElementById('seeList').innerHTML = '<p>Gemini 3 is thinking...</p>';

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
    itin.see.forEach(i => see.innerHTML += `<div class="guide-item"><b>${i.title}</b><p>${i.desc}</p></div>`);
    itin.eat.forEach(i => eat.innerHTML += `<div class="guide-item"><b>${i.title}</b><p>${i.desc}</p></div>`);
}

