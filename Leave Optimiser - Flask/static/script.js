document.getElementById('toInput').addEventListener('input', async (e) => {
    const val = e.target.value;
    const list = document.getElementById('toList'); // Move this up

    if (val.length < 3) {
        list.classList.add('hidden');
        return;
    }

    const res = await fetch(`/api/search?q=${val}`);
    const cities = await res.json();

    // CLEAR AND SHOW/HIDE LOGIC
    list.innerHTML = '';
    
    if (cities && cities.length > 0) {
        list.classList.remove('hidden'); // SHOW the dropdown
    } else {
        list.classList.add('hidden'); // HIDE if no results
        return;
    }

    cities.forEach(city => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.innerText = `${city.name}, ${city.country}`;
        div.onclick = () => {
            selectedCity = city;
            document.getElementById('toInput').value = city.name;
            list.innerHTML = '';
            list.classList.add('hidden'); // HIDE after selection
            generatePlan();
        };
        list.appendChild(div);
    });
});
