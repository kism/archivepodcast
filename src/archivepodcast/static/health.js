/**
 * Health monitoring module for checking system status
 */

// Initialize health check on page load
document.addEventListener("DOMContentLoaded", () => {
  fetchHealth();
  fetchProfile();
});

/**
 * Fetches health status from API endpoint
 */
export function fetchHealth() {
  fetch("/api/health")
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      console.log("Health data received");
      populateHealth(data);
    })
    .catch((error) => console.error("Error fetching health data:", error));
}

export function fetchProfile() {
  fetch("/api/profile")
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      console.log("Profile data received");
      populateProfile(data);
    })
    .catch((error) => console.error("Error fetching profile data:", error));
}

export function populateProfile(data) {
  const profileDiv = document.getElementById("profile");
  profileDiv.innerHTML = "";

  const description = document.createElement("h3");
  description.textContent = `Timer stats per: /api/profile`;
  profileDiv.appendChild(description);

  // /api/profile is a flat {path: seconds} map, indent by path depth to make the tree
  const timerDisplay = document.createElement("div");
  timerDisplay.classList.add("health-table");
  timerDisplay.style.whiteSpace = "pre";
  timerDisplay.textContent = Object.entries(data.times ?? {})
    .map(([path, duration]) => {
      const parts = path.split("/");
      return `${"  ".repeat(parts.length - 1)}${parts.at(-1)}: ${duration.toFixed(2)}s`;
    })
    .join("\n");
  profileDiv.appendChild(timerDisplay);
}

/**
 * Renders health status data in the UI
 * @param {Object} data - Health status data
 */
export function populateHealth(data) {
  const healthDiv = document.getElementById("health");
  healthDiv.innerHTML = "";

  const currentTime = new Date().toLocaleTimeString();

  const description = document.createElement("p");
  description.textContent = `Health per: /api/health @ ${currentTime}`;
  healthDiv.appendChild(description);

  for (const [section, sectionData] of Object.entries(data)) {
    const sectionContainer = document.createElement("p");
    sectionContainer.classList.add("health-table");
    const sectionTitle = document.createElement("h3");
    sectionTitle.textContent = section;
    sectionContainer.appendChild(sectionTitle);

    if (typeof sectionData === "object" && sectionData !== null) {
      const table = generateTable(sectionData);
      sectionContainer.appendChild(table);
    } else {
      const table = document.createElement("table");
      const row = document.createElement("tr");
      const cell = document.createElement("td");

      cell.textContent = sectionData;
      row.appendChild(cell);
      table.appendChild(row);
      sectionContainer.appendChild(table);
    }
    healthDiv.appendChild(sectionContainer);
  }
}

/**
 * Generates an HTML table from health data
 * @param {Object} data - Health data to display
 * @returns {HTMLTableElement}
 */
function generateTable(data) {
  const table = document.createElement("table");
  for (const [key, value] of Object.entries(data)) {
    const row = document.createElement("tr");
    const cellKey = document.createElement("td");

    if (typeof value === "object" && value !== null) {
      cellKey.textContent = key;
    } else {
      cellKey.textContent = `${key}:`;
    }
    row.appendChild(cellKey);

    const cellValue = document.createElement("td");
    if (
      typeof value === "number" &&
      (key.toLowerCase().includes("date") || key.toLowerCase().includes("last") || key.toLowerCase().includes("time"))
    ) {
      const date = new Date(value * 1000);
      cellValue.textContent = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
    } else if (typeof value === "object" && value !== null) {
      cellValue.appendChild(generateTable(value));
    } else {
      cellValue.textContent = value;
      if (key.toLowerCase().includes("alive") || key.toLowerCase().includes("healthy")) {
        if (value === true) {
          cellValue.style.color = "green";
        } else if (value === false) {
          cellValue.style.color = "red";
        }
      }
    }
    row.appendChild(cellValue);

    table.appendChild(row);
  }
  return table;
}
