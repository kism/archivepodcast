document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM fully loaded and parsed");
  fetch("/api/health")
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      console.log("Health data received");
      populateHealth(data);
    })
    .catch((error) => console.error("Error fetching health data:", error));
});

export function populateHealth(data) {
  const healthDiv = document.getElementById("health");
  for (const [section, sectionData] of Object.entries(data)) {
    const sectionContainer = document.createElement("p");
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
