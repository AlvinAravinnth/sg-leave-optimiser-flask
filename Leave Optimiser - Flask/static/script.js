let selectedCity = null;

// Listen for typing in the Search Box
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
            generatePlan(); // Start the heavy lifting
        };
        list.appendChild(div);
    });
});

async function generatePlan() {
    if (!selectedCity) return;

    // 1. INSTANT HEADER UPDATE (UX Fix)
    document.querySelector('.trip-header p').innerText = `Singapore → ${selectedCity.name}`;
    document.getElementById('dashboard').classList.remove('hidden');

    // 2. SHOW SKELETON LOADING
    document.getElementById('seeList').innerHTML = '<div class="shimmer">Gemini 3 is reasoning through your trip...</div>';
    document.getElementById('eatList').innerHTML = '';

    const payload = {
        leavesLeft: document.getElementById('leaves').value,
        budget_type: document.getElementById('budgetText').innerText,
        to: selectedCity
    };

    try {
        const res = await fetch('/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        const p = data.plan;

        if (p) {
            // Update UI Stats from AI Reasoning
            document.getElementById('dateRange').innerText = `${p.duration} Stay`;
            document.getElementById('leavesVal').innerText = p.leave_plan;
            document.getElementById('budgetVal').innerText = p.cost_breakdown.total;
            document.getElementById('distVal').innerText = data.dist;
            
            // Log full breakdown for debug
            console.log("AI Budget Logic:", p.cost_breakdown);
            
            renderItinerary(p.itinerary);
        }
    } catch (e) { console.error("Plan Error:", e); }
}

function renderItinerary(itin) {
    const see = document.getElementById('seeList');
    const eat = document.getElementById('eatList');
    see.innerHTML = ''; eat.innerHTML = '';

    itin.see.forEach(i => {
        see.innerHTML += `<div class="guide-item"><b>${i.title}</b><p>${i.desc}</p></div>`;
    });
    itin.eat.forEach(i => {
        eat.innerHTML += `<div class="guide-item"><b>${i.title}</b><p>${i.desc}</p></div>`;
    });
}
