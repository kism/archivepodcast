document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            const healthDiv = document.getElementById('health');
            healthDiv.textContent = JSON.stringify(data, null, 2);
        })
        .catch(error => console.error('Error fetching health data:', error));
});
