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
        const keyCell = document.createElement('td');
        keyCell.textContent = key;
        row.appendChild(keyCell);

        const valueCell = document.createElement('td');
        if (typeof value === 'object' && value !== null) {
            valueCell.appendChild(generateTable(value));
        } else {
            valueCell.textContent = value;
        }
        row.appendChild(valueCell);

        table.appendChild(row);
    }
    return table;
}
