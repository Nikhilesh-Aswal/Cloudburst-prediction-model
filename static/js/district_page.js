let miniMap;
let districtGeo;
let districtForecast = [];

// --- NEW: read ?date= from URL ---
function getQueryParam(key) {
  const params = new URLSearchParams(window.location.search);
  return params.get(key);
}

let selectedDate = getQueryParam("date");
if (!selectedDate) {
  selectedDate = new Date().toISOString().split("T")[0];
}

// Pre-fill the date box
document.getElementById("searchDate").value = selectedDate;

// Initialize mini map
async function initMiniMap() {
  miniMap = L.map("miniMap", {
    zoomControl: false,
    dragging: false,
    scrollWheelZoom: false,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(miniMap);

  const geoRes = await fetch("/static/data/uttarakhand_districts.geojson");
  const geoData = await geoRes.json();
  const feature = geoData.features.find(
    (f) =>
      f.properties.district.toLowerCase() === districtName.toLowerCase()
  );

  if (feature) {
    districtGeo = L.geoJSON(feature, {
      style: {
        color: "#1e40af",
        weight: 2,
        fillColor: "#60a5fa",
        fillOpacity: 0.5,
      },
    }).addTo(miniMap);
    miniMap.fitBounds(districtGeo.getBounds());
  }
}

// Fetch 5-day forecast for this district
async function loadDistrictForecast() {
  const res = await fetch(`/forecast?date=${selectedDate}`);
  const data = await res.json();
  districtForecast = data.filter(
    (d) => d.district.toLowerCase() === districtName.toLowerCase()
  );
  renderForecastCards();
  renderCharts();
}

// Render 5-day summary cards
function renderForecastCards() {
  const container = document.getElementById("forecastCards");
  container.innerHTML = "";

  districtForecast.forEach((d) => {
    const card = document.createElement("div");
    card.className =
      "bg-blue-50 rounded-lg p-4 shadow hover:shadow-lg transition";
    card.innerHTML = `
      <h3 class="font-bold text-blue-800">${d.date}</h3>
      <p>🌧️ Cloudburst: <b>${d.probability.toFixed(1)}%</b></p>
      <p>🌡️ Temp: ${d.temperature.toFixed(1)} °C</p>
      <p>💧 Humidity: ${d.humidity.toFixed(1)}%</p>
      <p>🌬️ Pressure: ${d.pressure ? d.pressure + " hPa" : "N/A"}</p>
      <p>☔ Rainfall: ${d.rainfall.toFixed(1)} mm</p>
    `;
    container.appendChild(card);
  });
}

// Render parameter charts
function renderCharts() {
  const labels = districtForecast.map((d) => d.date);

  const createChart = (id, label, data, color) => {
    new Chart(document.getElementById(id), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label,
            data,
            borderColor: color,
            backgroundColor: color + "33",
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: {
        scales: {
          y: { beginAtZero: true },
        },
      },
    });
  };

  createChart(
    "probChart",
    "Cloudburst Probability (%)",
    districtForecast.map((d) => d.probability),
    "#2563eb"
  );
  createChart(
    "tempChart",
    "Temperature (°C)",
    districtForecast.map((d) => d.temperature),
    "#f97316"
  );
  createChart(
    "humidityChart",
    "Humidity (%)",
    districtForecast.map((d) => d.humidity),
    "#22c55e"
  );
  createChart(
    "pressureChart",
    "Pressure (hPa)",
    districtForecast.map((d) => d.pressure || 0),
    "#0ea5e9"
  );
  createChart(
    "rainChart",
    "Rainfall (mm)",
    districtForecast.map((d) => d.rainfall),
    "#3b82f6"
  );
}

// Date search logic
document.addEventListener("DOMContentLoaded", () => {
  initMiniMap();
  loadDistrictForecast();

  const searchInput = document.getElementById("searchDate");
  const searchBtn = document.getElementById("searchBtn");
  const today = new Date();
  const maxDate = new Date(today);
  maxDate.setDate(today.getDate() + 5);
  const minDate = "2000-01-01";

  searchInput.min = minDate;
  searchInput.max = maxDate.toISOString().split("T")[0];

  searchBtn.addEventListener("click", () => {
  const val = searchInput.value;
  if (!val) return alert("Please select a date.");

  // 👉 Reload the page with the chosen date
  window.location.href = `/district/${districtName}?date=${val}`;
});
});
