let map;
let geojsonLayer;
let forecastData = {};
let districtPolygons = {};

function keyFor(name) {
  return (name || "").toString().trim().toLowerCase();
}

function applyColors(selectedDate = null) {
  if (!geojsonLayer || !forecastData) return;

  geojsonLayer.eachLayer((layer) => {
    const districtRaw =
      layer.feature?.properties?.district ||
      layer.feature?.properties?.name ||
      layer.feature?.properties?.DISTRICT ||
      "";
    const districtKey = keyFor(districtRaw);
    const data = forecastData[districtKey];

    if (data && data.length > 0) {
      let entry = data[data.length - 1];
      if (selectedDate) {
        const found = data.find((d) => d.date === selectedDate);
        if (found) entry = found;
      }

      if (entry) {
        layer.setStyle({
          fillColor: entry.risk_color || "#60a5fa",
          fillOpacity: 0.85,
          color: "#333",
          weight: 1.2,
        });

        const tt = `
          <b>${districtRaw}</b><br/>
          <b>Risk:</b> <span style="color:${
            entry.risk_color
          };font-weight:bold;">${entry.risk_level}</span><br/>
          <b>Probability:</b> ${Number(entry.probability).toFixed(1)}%<br/>
          🌡 ${Number(entry.temperature).toFixed(1)}°C &nbsp; 💧 ${Number(
          entry.humidity
        ).toFixed(0)}%<br/>
          ☔ ${Number(entry.rainfall).toFixed(1)} mm &nbsp; ⚙️ ${Number(
          entry.pressure
        ).toFixed(0)} hPa
        `;
        layer.bindTooltip(tt, {
          sticky: true,
          direction: "auto",
          className: "district-tooltip",
        });

        districtPolygons[districtRaw] = layer;
      }
    } else {
      layer.setStyle({
        fillColor: "#BDBDBD",
        fillOpacity: 0.6,
        color: "#999",
        weight: 0.9,
      });
      layer.bindTooltip(`<b>${districtRaw}</b><br/><i>No data</i>`, {
        direction: "center",
        className: "district-tooltip",
      });
    }
  });
}

async function initMap() {
  const loader = document.getElementById("loading-overlay");
  loader.classList.remove("hidden");

  const uttarakhandBounds = L.latLngBounds([28.5, 77.0], [31.5, 81.0]);

  map = L.map("map", {
    zoomControl: true,
    minZoom: 7,
    maxZoom: 11,
    attributionControl: false,
    maxBounds: uttarakhandBounds,
    maxBoundsViscosity: 1.0,
  }).setView([30.0668, 79.0193], 8);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
  }).addTo(map);

  const geoRes = await fetch("/static/data/uttarakhand_districts.geojson");
  const geoData = await geoRes.json();

  const forecastRes = await fetch("/forecast");
  const forecastJson = await forecastRes.json();

  forecastData = {};
  forecastJson.forEach((entry) => {
    const k = keyFor(entry.district);
    if (!forecastData[k]) forecastData[k] = [];
    forecastData[k].push(entry);
  });

  const styleFeature = (feature) => ({
    fillColor: "#BDBDBD",
    weight: 1.2,
    opacity: 1,
    color: "#555",
    fillOpacity: 75,
  });

  function highlightFeature(e) {
    const layer = e.target;
    layer.setStyle({
      weight: 2,
      color: "#000",
      fillOpacity: 0.9,
    });
    layer.bringToFront();
  }

  function resetHighlight(e) {
    e.target.setStyle({
      weight: 1.2,
      color: "#555",
      fillOpacity: 0.85,
    });
  }

  function onEachFeature(feature, layer) {
    const district = feature.properties.district;
    layer.on({
      mouseover: highlightFeature,
      mouseout: resetHighlight,
      click: () => {
        const date = document.getElementById("searchDate")?.value;
        if (date) {
          window.location.href = `/district/${encodeURIComponent(
            district
          )}?date=${date}`;
        } else {
          window.location.href = `/district/${encodeURIComponent(district)}`;
        }
      },
    });
  }

  geojsonLayer = L.geoJson(geoData, {
    style: styleFeature,
    onEachFeature,
  }).addTo(map);

  applyColors();

  const legend = L.control({ position: "bottomright" });
  legend.onAdd = function () {
    const div = L.DomUtil.create("div", "info legend");
    const grades = [
      { label: "Low", color: "#2ECC71" },
      { label: "Moderate", color: "#F1C40F" },
      { label: "High", color: "#E67E22" },
      { label: "Extreme", color: "#E74C3C" },
    ];

    div.innerHTML = `<strong>Cloudburst Risk</strong><br>`;
    grades.forEach((g) => {
      div.innerHTML += `<i style="background:${g.color};"></i> ${g.label}<br>`;
    });
    return div;
  };
  legend.addTo(map);

  setTimeout(() => loader.classList.add("hidden"), 800);
}

window.onload = initMap;

document.addEventListener("DOMContentLoaded", () => {
  const searchBtn = document.getElementById("searchBtn");
  const searchDate = document.getElementById("searchDate");
  const warning = document.getElementById("searchWarning");

  const today = new Date();
  const maxDate = new Date(today);
  maxDate.setDate(maxDate.getDate() + 5);
  const minDate = new Date("2000-01-01");

  const toYMD = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
      d.getDate()
    ).padStart(2, "0")}`;

  searchDate.min = toYMD(minDate);
  searchDate.max = toYMD(maxDate);

  searchBtn.addEventListener("click", async () => {
    const selectedDate = new Date(searchDate.value);

    if (!searchDate.value) {
      warning.textContent = "⚠️ Please select a date first.";
      warning.classList.remove("hidden");
      return;
    }

    if (selectedDate < minDate || selectedDate > maxDate) {
      warning.textContent =
        "⚠️ Date must be between year 2000 and next 5 days.";
      warning.classList.remove("hidden");
      return;
    }

    warning.classList.add("hidden");

    const loader = document.getElementById("loading-overlay");
    loader.classList.remove("hidden");

    try {
      const res = await fetch(`/forecast?date=${searchDate.value}`);
      const forecastJson = await res.json();

      forecastData = {};
      forecastJson.forEach((entry) => {
        const k = keyFor(entry.district);
        if (!forecastData[k]) forecastData[k] = [];
        forecastData[k].push(entry);
      });

      applyColors(searchDate.value);
    } catch (err) {
      console.error("❌ Error fetching forecast:", err);
    }

    setTimeout(() => loader.classList.add("hidden"), 800);
  });
});
