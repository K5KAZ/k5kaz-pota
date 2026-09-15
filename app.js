const CALLSIGN = "K5KAZ";

// Build the data URL from the GitHub Pages site path.
// This works both on the GitHub Pages project site and locally.
const DATA_URL = new URL("data/pota.json", window.location.href).href;

const $ = id => document.getElementById(id);

const fmt = v =>
  Number.isFinite(Number(v))
    ? Number(v).toLocaleString()
    : "—";

function first(o, keys) {
  for (const k of keys) {
    if (o && o[k] !== undefined && o[k] !== null) {
      return o[k];
    }
  }
  return null;
}

function normalize(data) {
  const s = data?.stats || {};

  return {
    activations: first(s, [
      "activations",
      "activationCount",
      "totalActivations",
      "activatorActivations"
    ]),

    parks: first(s, [
      "parks",
      "parkCount",
      "uniqueParks",
      "uniqueParksActivated",
      "activatorParks"
    ]),

    qsos: first(s, [
      "qsos",
      "qsoCount",
      "totalQsos",
      "totalQSOs",
      "activatorQsos"
    ]),

    states: first(s, [
      "states",
      "stateCount",
      "uniqueStates",
      "statesActivated"
    ]),

    activationsList: Array.isArray(data?.activationsList)
      ? data.activationsList
      : []
  };
}

function render(data) {
  console.log("K5KAZ POTA data loaded:", data);

  const n = normalize(data);

  const activations = $("activations-stat");
  const parks = $("parks-stat");
  const qsos = $("qsos-stat");
  const states = $("states-stat");

  if (activations) activations.textContent = fmt(n.activations);
  if (parks) parks.textContent = fmt(n.parks);
  if (qsos) qsos.textContent = fmt(n.qsos);
  if (states) states.textContent = fmt(n.states);

  const list = $("activation-list");

  if (list) {
    if (!n.activationsList.length) {
      list.innerHTML = `
        <div class="notice">
          POTA statistics are connected, but recent activation records
          are not available in the current cached response.
        </div>
      `;
    } else {
      list.innerHTML = n.activationsList
        .slice(0, 8)
        .map(a => {
          const ref =
            a.reference ||
            a.parkReference ||
            a.ref ||
            "POTA";

          const name =
            a.parkName ||
            a.name ||
            a.locationName ||
            "Park";

          const date =
            a.date ||
            a.activationDate ||
            a.qso_date ||
            "";

          const qsos = Number(
            a.qsos ??
            a.qsoCount ??
            a.total ??
            a.contacts ??
            0
          );

          return `
            <article class="activation">
              <div class="thumb">▲</div>
              <div>
                <h4>${esc(ref)} — ${esc(name)}</h4>
                <p>${esc(date)}</p>
                <p>POTA activation</p>
              </div>
              <div class="qso">
                ${qsos.toLocaleString()} QSOs
              </div>
            </article>
          `;
        })
        .join("");
    }
  }

  renderMap(data);
}

function renderMap(data) {
  const mapElement = $("map");

  if (!mapElement) {
    console.warn("Map element not found.");
    return;
  }

  const parks = Array.isArray(data?.parks)
    ? data.parks
    : [];

  const map = L.map("map").setView([37.8, -96], 4);

  L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: "&copy; OpenStreetMap contributors"
    }
  ).addTo(map);

  const icon = L.divIcon({
    className: "",
    html: '<div class="pin"></div>',
    iconSize: [15, 15],
    iconAnchor: [7, 15]
  });

  const valid = parks.filter(
    p =>
      Number.isFinite(Number(p.lat)) &&
      Number.isFinite(Number(p.lon))
  );

  if (valid.length) {
    const bounds = [];

    valid.forEach(p => {
      const lat = Number(p.lat);
      const lon = Number(p.lon);

      bounds.push([lat, lon]);

      const ref = esc(p.reference || "POTA");
      const name = esc(p.name || "Park");

      L.marker([lat, lon], { icon })
        .addTo(map)
        .bindPopup(`<strong>${ref}</strong><br>${name}`);
    });

    map.fitBounds(bounds, {
      padding: [20, 20],
      maxZoom: 8
    });

  } else {
    L.control.scale().addTo(map);

    const note = L.control({
      position: "topright"
    });

    note.onAdd = () => {
      const d = L.DomUtil.create("div");

      d.style.cssText =
        "background:#0d191d;color:#c8d2cf;padding:7px 9px;" +
        "border:1px solid #294045";

      d.textContent =
        "Park coordinates appear after the first data enrichment run.";

      return d;
    };

    note.addTo(map);
  }
}

function esc(s) {
  return String(s ?? "").replace(
    /[&<>"']/g,
    c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    }[c])
  );
}

function loadPOTA() {
  console.log("Loading K5KAZ POTA data from:", DATA_URL);

  fetch(DATA_URL, {
    cache: "no-store"
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(
          `POTA data request failed: HTTP ${response.status}`
        );
      }

      return response.json();
    })
    .then(data => {
      render(data);
    })
    .catch(error => {
      console.error("K5KAZ POTA data error:", error);

      const list = $("activation-list");

      if (list) {
        list.innerHTML = `
          <div class="notice">
            Unable to load the current POTA data.
            Please try refreshing the page.
          </div>
        `;
      }

      if ($("activations-stat"))
        $("activations-stat").textContent = "—";

      if ($("parks-stat"))
        $("parks-stat").textContent = "—";

      if ($("qsos-stat"))
        $("qsos-stat").textContent = "—";

      if ($("states-stat"))
        $("states-stat").textContent = "—";

      renderMap({});
    });
}

// Wait until the entire page is ready before running the app.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", loadPOTA);
} else {
  loadPOTA();
}
