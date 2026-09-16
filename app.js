const DATA_URL = new URL('data/pota.json', window.location.href).href;
const POTA_API = 'https://api.pota.app';

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? '—';
}

function normalizeStats(raw) {
  const s = raw?.stats || raw || {};
  const find = (keys) => {
    for (const k of keys) {
      if (s[k] !== undefined && s[k] !== null) return s[k];
      const lower = Object.keys(s).find(x => x.toLowerCase() === k.toLowerCase());
      if (lower) return s[lower];
    }
    return null;
  };
  return {
    activations: find(['activations','activationCount','totalActivations']),
    parks: find(['parks','parkCount','totalParks']),
    qsos: find(['qsos','qsoCount','totalQSOs','contacts']),
    states: find(['states','stateCount','totalStates'])
  };
}

function renderRecentActivations(list) {
  const el = document.getElementById('activation-list');
  if (!el) return;
  if (!Array.isArray(list) || !list.length) {
    el.innerHTML = '<div class="notice">Detailed activation history is available on my <a href="https://pota.app/#/profile/K5KAZ" target="_blank" rel="noopener noreferrer">POTA profile</a>.</div>';
    return;
  }
  const rows = list.slice(0, 8).map(a => {
    const date = a.date || a.qso_date || a.activationDate || '';
    const ref = a.reference || a.parkReference || a.park || '';
    const name = a.name || a.parkName || '';
    const qsos = a.qsos ?? a.qsoCount ?? a.contacts ?? '';
    return `<div class="activation-row"><div><strong>${ref}</strong><span>${name}</span></div><div>${date}</div><div>${qsos ? qsos + ' QSOs' : ''}</div></div>`;
  }).join('');
  el.innerHTML = rows;
}

function initParkMap() {
  const mapEl = document.getElementById('parks-map');
  const rows = Array.from(document.querySelectorAll('#parks-table-body tr'));
  if (!mapEl || !window.L || !rows.length) return;

  const map = L.map(mapEl, { scrollWheelZoom: false }).setView([37.8, -96], 4);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const layer = L.layerGroup().addTo(map);
  const bounds = [];
  const status = document.getElementById('map-status');

  const refs = rows.map(row => ({
    ref: row.querySelector('.park-ref')?.textContent.trim(),
    name: row.querySelector('.park-link')?.textContent.trim(),
    url: row.querySelector('.park-link')?.href
  })).filter(x => x.ref);

  async function loadPark(p) {
    try {
      const response = await fetch(`${POTA_API}/park/${encodeURIComponent(p.ref)}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const lat = Number(data.latitude);
      const lon = Number(data.longitude ?? data.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
      const marker = L.marker([lat, lon]).addTo(layer);
      marker.bindPopup(`<strong>${p.ref}</strong><br>${p.name}<br><a href="${p.url}" target="_blank" rel="noopener noreferrer">Open POTA park page →</a>`);
      bounds.push([lat, lon]);
      return true;
    } catch (e) {
      return false;
    }
  }

  Promise.all(refs.map(loadPark)).then(results => {
    const loaded = results.filter(Boolean).length;
    if (loaded) {
      map.fitBounds(bounds, { padding: [25, 25] });
      if (status) status.textContent = `${loaded} of ${refs.length} park locations loaded from POTA.`;
    } else if (status) {
      status.textContent = 'Park locations could not be loaded right now. Use the POTA links above to view locations.';
    }
  });
}

async function loadPotaData() {
  try {
    const response = await fetch(DATA_URL, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const stats = normalizeStats(data);
    setText('activations-stat', stats.activations);
    setText('parks-stat', stats.parks);
    setText('qsos-stat', stats.qsos);
    setText('states-stat', stats.states);
    renderRecentActivations(data.activationsList || data.activations || []);
  } catch (error) {
    console.error('POTA data load failed:', error);
    renderRecentActivations([]);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadPotaData();
  initParkMap();
});
