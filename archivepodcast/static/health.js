document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            const healthDiv = document.getElementById('health');
            for (const [section, sectionData] of Object.entries(data)) {
                const sectionTitle = document.createElement('h2');
                sectionTitle.textContent = section;
                healthDiv.appendChild(sectionTitle);

                if (typeof sectionData === 'object' && sectionData !== null) {
                    const table = generateTable(sectionData);
                    healthDiv.appendChild(table);
                } else {
                    const valueParagraph = document.createElement('p');
                    valueParagraph.textContent = sectionData;
                    healthDiv.appendChild(valueParagraph);
                }
            }
        })
        .catch(error => console.error('Error fetching health data:', error));
});

function generateTable(data) {
    const table = document.createElement('table');
    for (const [key, value] of Object.entries(data)) {
        const row = document.createElement('tr');
        const cellKey = document.createElement('td');
        cellKey.textContent = key;
        row.appendChild(cellKey);

        const cellValue = document.createElement('td');
        if (typeof value === 'number' && (key.toLowerCase().includes('date') || key.toLowerCase().includes('last') || key.toLowerCase().includes('time'))) {
            const date = new Date(value * 1000);
            cellValue.textContent = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        } else if (typeof value === 'object' && value !== null) {
            cellValue.appendChild(generateTable(value));
        } else {
            cellValue.textContent = value;
        }
        row.appendChild(cellValue);

        table.appendChild(row);
    }
    return table;
}
