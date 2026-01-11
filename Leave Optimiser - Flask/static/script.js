let selectedCity = null;

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('toInput');
    if (input) {
        input.addEventListener('input', (e) => {
            const val = e.target.value;
            if (val.length > 2) searchCity(val);
        });
    }
});

async function searchCity(query) {
    const res = await fetch(`/api/search?q=${query}`);
    const data = await res.json();
    const list = document.getElementById('toList');
    list.innerHTML = '';
    
    data.forEach(city => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.innerText = `${city.name}, ${city.country || ''}`;
        item.onclick = () => {
            document.getElementById('toInput').value = city.name;
            selectedCity = city;
            list.style.display = 'none';
            generatePlan(city); // Trigger heavy lifting
        };
        list.appendChild(item);
    });
    list.style.display = 'block';
}

async function generatePlan(cityData) {
    // 1. INSTANT HEADER UPDATE
    const headerTitle = document.querySelector('.trip-header p');
    if (headerTitle) headerTitle.innerText = `Singapore → ${cityData.name}`;

    // 2. SHOW SKELETON LOADERS
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('seeList').innerHTML = '<div class="shimmer">Gemini 3 is reasoning...</div>';

    const payload = {
        leavesLeft: document.getElementById('leaves').value,
        to: cityData,
        year: document.getElementById('year').value
    };

    try {
        const res = await fetch('/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        
        if (data.ai) {
            // Update UI with AI Decisions
            document.getElementById('dateRange').innerText = data.ai.suggested_duration;
            document.getElementById('leavesVal').innerText = data.ai.leave_recommendation;
            document.getElementById('budgetVal').innerText = data.ai.budget.total;
            document.getElementById('distVal').innerText = data.dist;
            
            // Render the AI's custom itinerary
            renderGuide(data.ai.itinerary);
        }
    } catch (e) { console.error("Plan failed:", e); }
}

function renderGuide(itinerary) {
    const seeList = document.getElementById('seeList');
    const eatList = document.getElementById('eatList');
    seeList.innerHTML = '';
    eatList.innerHTML = '';

    itinerary.see.forEach(item => {
        seeList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });

    itinerary.eat.forEach(item => {
        eatList.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${item.title}</span>
                <span class="guide-desc">${item.desc}</span>
            </div>`;
    });
}
