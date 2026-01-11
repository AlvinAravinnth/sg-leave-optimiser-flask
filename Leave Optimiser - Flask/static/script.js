let selectedCity = null;

// Handle Destination Search Dropdown
document.getElementById('toInput').addEventListener('input', async (e) => {
    const val = e.target.value;
    const list = document.getElementById('toList');

    // Requirement: Min 3 characters to search
    if (val.length < 3) {
        list.classList.add('hidden');
        return;
    }

    try {
        const res = await fetch(`/api/search?q=${val}`);
        const cities = await res.json();

        list.innerHTML = '';
        
        if (cities && cities.length > 0) {
            list.classList.remove('hidden'); // Show the list
            cities.forEach(city => {
                const div = document.createElement('div');
                div.className = 'suggestion-item';
                div.innerText = `${city.name}, ${city.country}`;
                div.onclick = () => {
                    selectedCity = city;
                    document.getElementById('toInput').value = city.name;
                    list.innerHTML = '';
                    list.classList.add('hidden');
                    generatePlan(); // Trigger plan generation
                };
                list.appendChild(div);
            });
        } else {
            list.classList.add('hidden');
        }
    } catch (err) {
        console.error("Search error:", err);
    }
});

// Close dropdown if user clicks outside
document.addEventListener('click', (e) => {
    const list = document.getElementById('toList');
    if (e.target.id !== 'toInput') {
        list.classList.add('hidden');
    }
});

async function generatePlan() {
    if (!selectedCity) return;
    
    const dashboard = document.getElementById('dashboard');
    const inputPanel = document.querySelector('.input-panel');
    
    // Hide input panel and show dashboard with animation
    inputPanel.classList.add('hidden');
    dashboard.classList.remove('hidden');
    dashboard.classList.add('fade-in');
    
    // Set initial loading state
    document.getElementById('destName').innerText = selectedCity.name;
    document.getElementById('seeList').innerHTML = '<p class="loading-text">Gemini 3 is thinking...</p>';
    document.getElementById('eatList').innerHTML = '';

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
            // Update Stats Boxes
            document.getElementById('dateRange').innerText = data.plan.duration;
            document.getElementById('leavesVal').innerText = data.plan.leave_plan;
            document.getElementById('budgetVal').innerText = data.plan.budget;
            document.getElementById('distVal').innerText = data.dist;
            
            // Render the AI Itinerary
            renderGuide(data.plan.itinerary);
        }
    } catch (err) {
        console.error("Planning error:", err);
        document.getElementById('seeList').innerHTML = '<p>Error generating plan. Please try again.</p>';
    }
}

function renderGuide(itin) {
    const see = document.getElementById('seeList');
    const eat = document.getElementById('eatList');
    see.innerHTML = ''; 
    eat.innerHTML = '';
    
    itin.see.forEach(i => {
        see.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${i.title}</span>
                <span class="guide-desc">${i.desc}</span>
            </div>`;
    });
    
    itin.eat.forEach(i => {
        eat.innerHTML += `
            <div class="guide-item">
                <span class="guide-title">${i.title}</span>
                <span class="guide-desc">${i.desc}</span>
            </div>`;
    });
}
