/**
 * ResQ Odisha — Core Frontend Application Logic
 * Integrates the preferred dashboard UI with live FastAPI endpoints:
 * - /api/stats
 * - /api/hazards
 * - /api/shelters
 * - /api/incidents
 * - /api/advisory
 * - /api/sos
 * - /api/weather/simulate-cyclone
 * - /api/weather/sync-live
 */

// Global State
let map = null;
let allMarkers = [];
let currentFilter = 'all';
let currentWeatherMode = 'SIMULATION';
let refreshTimer = null;
let lastSyncTimestamp = Date.now();

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }

  initNavigation();
  initMap();
  initDisasterNews();
  initReportModal();
  initWeatherModeToggle();
  initManualWeatherSync();
  initChatbot();

  // Initial Data Fetch
  refreshAllData();

  // Periodic Polling every 30 seconds
  refreshTimer = setInterval(() => {
    refreshAllData(true);
    updateLastSyncDisplay();
  }, 30000);

  // Automated 10-minute Live Weather Re-Sync
  setInterval(async () => {
    if (currentWeatherMode === 'LIVE') {
      try {
        console.log('Automated 10-minute frontend weather re-sync triggered...');
        await fetch('/api/weather/sync-live', { method: 'POST' });
        lastSyncTimestamp = Date.now();
        await refreshAllData(true);
      } catch (e) {
        console.warn('Auto weather sync error:', e);
      }
    }
  }, 600000);
});

/* ==========================================================================
   1. NAVIGATION
   ========================================================================== */
function initNavigation() {
  const navLinks = document.querySelectorAll('.nav a');
  navLinks.forEach((link) => {
    link.addEventListener('click', () => {
      navLinks.forEach((a) => a.classList.remove('active'));
      link.classList.add('active');

      if (link.getAttribute('href') === '#live-map' && map) {
        setTimeout(() => map.invalidateSize(), 300);
      }
    });
  });
}

/* ==========================================================================
   2. MAP INITIALIZATION & LAYERS (LEAFLET)
   ========================================================================== */
function initMap() {
  const mapElement = document.getElementById('map');
  if (!mapElement || typeof L === 'undefined') return;

  // Center on Coastal Odisha
  map = L.map('map', {
    scrollWheelZoom: true,
  }).setView([20.25, 85.85], 8);

  map.attributionControl.setPrefix(false);

  // High-contrast clean OpenStreetMap tiles
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors | ResQ Odisha GIS',
  }).addTo(map);

  // Setup filter buttons
  const filterButtons = document.querySelectorAll('[data-filter]');
  filterButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      filterButtons.forEach((b) => {
        b.classList.toggle('selected', b === btn);
        b.setAttribute('aria-pressed', String(b === btn));
      });
      currentFilter = btn.dataset.filter;
      applyMapFilter(currentFilter);
    });
  });
}

function applyMapFilter(filter) {
  let firstMatch = null;

  allMarkers.forEach(({ marker, type, severity, data }) => {
    let visible = false;

    if (filter === 'all') {
      visible = true;
    } else if (filter === 'critical') {
      visible = severity === 'critical';
    } else if (filter === 'high') {
      visible = severity === 'high';
    } else if (filter === 'moderate') {
      visible = severity === 'moderate';
    } else if (filter === 'shelter') {
      visible = type === 'shelter';
    }

    if (visible) {
      if (!map.hasLayer(marker)) {
        marker.addTo(map);
      }
      if (!firstMatch) {
        firstMatch = { type, data, severity };
      }
    } else {
      if (map.hasLayer(marker)) {
        map.removeLayer(marker);
      }
    }
  });

  if (firstMatch) {
    showDetail(firstMatch.type, firstMatch.data, firstMatch.severity);
  } else {
    const detailBox = document.getElementById('incident-detail');
    if (detailBox) {
      detailBox.innerHTML = `
        <div>
          <h3>No matching elements</h3>
          <p>No active incidents or shelters found under filter: "${filter}".</p>
        </div>
        <span class="badge moderate">FILTER EMPTY</span>
      `;
    }
  }
}

function syncChatbotDistrict(districtName) {
  if (!districtName) return;
  const select = document.getElementById('chat-district-select');
  if (!select) return;
  const search = districtName.toLowerCase().trim();
  for (let i = 0; i < select.options.length; i++) {
    const optVal = select.options[i].value.toLowerCase();
    const optText = select.options[i].text.toLowerCase();
    if (optVal === search || optText.includes(search) || search.includes(optVal)) {
      if (select.selectedIndex !== i) {
        select.selectedIndex = i;
        select.dispatchEvent(new Event('change'));
      }
      break;
    }
  }
}

function showDetail(type, data, severity = 'moderate') {
  const detailTitle = document.getElementById('detail-title');
  const detailDesc = document.getElementById('detail-desc');
  const detailBadge = document.getElementById('detail-badge');
  if (!detailTitle || !detailDesc || !detailBadge) return;

  if (type === 'incident') {
    detailTitle.textContent = `SOS #${data.id}: ${data.category ? data.category.toUpperCase() : 'EMERGENCY'}`;
    detailDesc.textContent = `${data.raw_text} · Assigned: ${data.dispatch_unit || 'ODRAF Team'} · Shelter: ${data.nearest_shelter_name || 'OSDMA Center'}`;
    detailBadge.className = `badge ${severity}`;
    detailBadge.textContent = `Urgency ${data.urgency_score || 5}/5`;
    if (data.district) syncChatbotDistrict(data.district);
  } else if (type === 'hazard') {
    detailTitle.textContent = `${data.district_name} Warning Zone`;
    detailDesc.textContent = `${data.summary || data.threat_type} · Wind: ${data.wind_kmh || 50} km/h · Rainfall: ${data.rainfall_mm || 0} mm`;
    detailBadge.className = `badge ${severity}`;
    detailBadge.textContent = `${data.alert_level || 'ALERT'}`;
    if (data.district_name) syncChatbotDistrict(data.district_name);
  } else if (type === 'shelter') {
    detailTitle.textContent = data.name;
    detailDesc.textContent = `${data.district} District · ${data.available_spots} beds free of ${data.capacity} total · Helpline: ${data.contact_phone || '1070'}`;
    detailBadge.className = 'badge open';
    detailBadge.textContent = 'Shelter Active';
    if (data.district) syncChatbotDistrict(data.district);
  }
}

/* ==========================================================================
   3. DATA FETCHING: STATS, HAZARDS, SHELTERS, INCIDENTS, ADVISORIES
   ========================================================================== */
async function refreshAllData(silent = false) {
  try {
    await Promise.all([
      loadStats(),
      loadHazardsAndMap(),
      loadSheltersTable(),
      loadAiInsights(),
    ]);
    if (window.lucide) {
      window.lucide.createIcons();
    }
  } catch (err) {
    console.error('Error refreshing ResQ Odisha data:', err);
  }
}

// 3.1 Load Stats & KPIs
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    currentWeatherMode = data.weather_mode || 'SIMULATION';
    updateWeatherModeUI(currentWeatherMode);

    // Update KPI numbers
    const redEl = document.getElementById('kpi-red-alerts');
    if (redEl) redEl.textContent = data.active_red_alerts ?? 0;

    const sosEl = document.getElementById('kpi-sos-calls');
    if (sosEl) sosEl.textContent = data.verified_sos_calls ?? 0;

    const spotsEl = document.getElementById('kpi-shelter-spots');
    if (spotsEl) spotsEl.textContent = (data.available_shelter_capacity ?? 0).toLocaleString();

    const spotsFoot = document.getElementById('kpi-shelter-foot');
    if (spotsFoot && data.total_shelter_capacity) {
      spotsFoot.textContent = `Of ${data.total_shelter_capacity.toLocaleString()} total beds capacity`;
    }

    // Engine & Status labels
    const metaEngine = document.getElementById('meta-engine-status');
    if (metaEngine && data.ai_engine_status) {
      metaEngine.textContent = data.ai_engine_status;
    }

    const liveBadge = document.getElementById('kpi-live-badge');
    if (liveBadge) {
      liveBadge.textContent = 'FASTAPI ONLINE';
      liveBadge.style.color = '#10b981';
    }

    if (data.last_sync) {
      lastSyncTimestamp = new Date(data.last_sync).getTime();
    }
    updateLastSyncDisplay();
  } catch (err) {
    console.warn('Could not load /api/stats, using fallback:', err);
    const liveBadge = document.getElementById('kpi-live-badge');
    if (liveBadge) {
      liveBadge.textContent = 'OFFLINE MODE';
      liveBadge.style.color = '#bf7713';
    }
  }
}

// 3.2 Load Hazards, Incidents & Plot on Map
async function loadHazardsAndMap() {
  try {
    const [hazardsRes, incidentsRes, sheltersRes] = await Promise.all([
      fetch('/api/hazards'),
      fetch('/api/incidents'),
      fetch('/api/shelters'),
    ]);

    const hazardsData = hazardsRes.ok ? await hazardsRes.json() : { districts: [] };
    const incidentsData = incidentsRes.ok ? await incidentsRes.json() : { incidents: [] };
    const sheltersData = sheltersRes.ok ? await sheltersRes.json() : { shelters: [] };

    // Update recent alerts list
    renderAlertsList(hazardsData.districts || []);

    // Plot on Leaflet map
    if (map) {
      // Clear old markers
      allMarkers.forEach(({ marker }) => {
        if (map.hasLayer(marker)) map.removeLayer(marker);
      });
      allMarkers = [];

      // 1. Plot District Hazard Circles & Center Markers
      (hazardsData.districts || []).forEach((d) => {
        if (!d.lat || !d.lon) return;

        const alertLvl = (d.alert_level || 'YELLOW').toUpperCase();
        let color = '#ef782d';
        let severity = 'high';
        if (alertLvl === 'RED') {
          color = '#c94242';
          severity = 'critical';
        } else if (alertLvl === 'GREEN') {
          color = '#16805b';
          severity = 'moderate';
        } else if (alertLvl === 'YELLOW') {
          color = '#bf7713';
          severity = 'moderate';
        }

        // Warning Radius Circle
        const circle = L.circle([d.lat, d.lon], {
          color: color,
          fillColor: color,
          fillOpacity: 0.15,
          radius: d.radius_meters || 25000,
          weight: 2,
        }).addTo(map);

        circle.bindPopup(`
          <strong>${d.district_name} Hazard Zone</strong><br>
          Alert: <strong style="color:${color}">${alertLvl}</strong><br>
          Wind: ${d.wind_kmh} km/h | Rain: ${d.rainfall_mm} mm<br>
          <em>${d.summary || d.threat_type}</em>
        `);

        circle.on('click', () => showDetail('hazard', d, severity));
        allMarkers.push({ marker: circle, type: 'hazard', severity, data: d });
      });

      // 2. Plot Real Incidents from SQLite
      (incidentsData.incidents || []).forEach((inc) => {
        if (!inc.latitude || !inc.longitude) return;

        const urgency = inc.urgency_score || 3;
        let severity = 'moderate';
        if (urgency >= 5 || inc.is_emergency) {
          severity = 'critical';
        } else if (urgency === 4) {
          severity = 'high';
        }

        const icon = L.divIcon({
          className: '',
          html: `<span class="incident-marker ${severity}"></span>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        });

        const marker = L.marker([inc.latitude, inc.longitude], {
          icon,
          title: `SOS #${inc.id}`,
        }).addTo(map);

        marker.bindPopup(`
          <strong>SOS #${inc.id} [${severity.toUpperCase()}]</strong><br>
          ${inc.raw_text}<br>
          <small>Dispatched: <strong>${inc.dispatch_unit || 'ODRAF Unit'}</strong></small><br>
          <small>Target: <strong>${inc.nearest_shelter_name || 'OSDMA Shelter'}</strong></small>
        `);

        marker.on('click', () => showDetail('incident', inc, severity));
        allMarkers.push({ marker, type: 'incident', severity, data: inc });
      });

      // 3. Plot Multipurpose Cyclone Shelters
      (sheltersData.shelters || []).forEach((s) => {
        if (!s.latitude || !s.longitude) return;

        const shelterIcon = L.divIcon({
          className: '',
          html: `<div class="shelter-marker" title="${s.name}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg></div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        });

        const marker = L.marker([s.latitude, s.longitude], {
          icon: shelterIcon,
          title: s.name,
        }).addTo(map);

        const freeBeds = s.available_spots ?? Math.max(0, s.capacity - s.occupied);
        marker.bindPopup(`
          <strong>${s.name}</strong><br>
          District: ${s.district}<br>
          Capacity: ${s.occupied} / ${s.capacity} (${freeBeds} free beds)<br>
          Helpline: <strong>${s.contact_phone || '1070'}</strong>
        `);

        marker.on('click', () => showDetail('shelter', s, 'open'));
        allMarkers.push({ marker, type: 'shelter', severity: 'open', data: s });
      });

      // Select first incident or hazard by default
      if (allMarkers.length > 0) {
        const first = allMarkers[0];
        showDetail(first.type, first.data, first.severity);
      }
    }
  } catch (err) {
    console.warn('Error loading hazards and map data:', err);
  }
}

// 3.3 Render Recent Alerts Timeline
function renderAlertsList(districts) {
  const container = document.getElementById('alerts-list-container');
  if (!container) return;

  if (!districts || districts.length === 0) {
    container.innerHTML = '<p style="color:#8a9aaa;padding:12px;">No active district alerts.</p>';
    return;
  }

  // Sort: RED first, then ORANGE, then YELLOW
  const severityOrder = { RED: 1, ORANGE: 2, YELLOW: 3, GREEN: 4 };
  const sorted = [...districts].sort((a, b) => {
    return (severityOrder[a.alert_level] || 5) - (severityOrder[b.alert_level] || 5);
  });

  container.innerHTML = sorted.map((d) => {
    const alertLvl = (d.alert_level || 'YELLOW').toUpperCase();
    let lineClass = 'alert-line';
    let badgeClass = 'badge';

    if (alertLvl === 'RED') {
      badgeClass += ' critical';
    } else if (alertLvl === 'ORANGE') {
      lineClass += ' high';
      badgeClass += ' high';
    } else if (alertLvl === 'YELLOW') {
      lineClass += ' moderate';
      badgeClass += ' moderate';
    } else {
      lineClass += ' green';
      badgeClass += ' open';
    }

    return `
      <article class="alert-item">
        <span class="${lineClass}"></span>
        <div class="alert-main">
          <div class="alert-top">
            <strong>${d.district_name}: ${d.threat_type || 'Hazard Watch'}</strong>
            <span class="${badgeClass}">${alertLvl} ALERT</span>
          </div>
          <p>${d.summary || 'Meteorological surveillance active.'} (Wind: ${d.wind_kmh} km/h, Rain: ${d.rainfall_mm} mm)</p>
          <time class="alert-time">Today · Coastal Watch Sector</time>
        </div>
      </article>
    `;
  }).join('');
}

// 3.4 Render Shelters & Resources Table
async function loadSheltersTable() {
  try {
    const res = await fetch('/api/shelters');
    if (!res.ok) return;
    const data = await res.json();
    const shelters = data.shelters || [];

    const tbody = document.getElementById('shelters-tbody');
    const countNote = document.getElementById('shelter-count-note');

    if (countNote) {
      countNote.textContent = `${shelters.length} CENTERS REGISTERED`;
    }

    if (tbody) {
      if (shelters.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;">No shelters registered.</td></tr>';
        return;
      }

      tbody.innerHTML = shelters.map((s) => {
        const occupied = s.occupied || 0;
        const capacity = s.capacity || 1000;
        const available = s.available_spots ?? Math.max(0, capacity - occupied);
        const pct = Math.round((occupied / capacity) * 100);

        let barClass = '';
        let badgeClass = 'badge open';
        let statusText = `Open (${available} free)`;

        if (pct >= 90) {
          barClass = 'critical';
          badgeClass = 'badge critical';
          statusText = `Near Full (${available} left)`;
        } else if (pct >= 65) {
          barClass = 'busy';
          badgeClass = 'badge limited';
          statusText = `Limited (${available} left)`;
        }

        return `
          <tr>
            <td>
              ${s.name}
              <small>${s.district} District · Helpline: ${s.contact_phone || '1070'}</small>
            </td>
            <td>Cyclone Shelter</td>
            <td>
              <div class="capacity">
                <span class="bar"><span class="${barClass}" style="width:${Math.min(100, pct)}%"></span></span>
                ${occupied.toLocaleString()} / ${capacity.toLocaleString()} (${pct}%)
              </div>
            </td>
            <td><span class="${badgeClass}">${statusText}</span></td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.warn('Error loading shelters table:', err);
  }
}

// 3.5 Load Grounded AI Insights
async function loadAiInsights() {
  try {
    const res = await fetch('/api/advisory?threat_type=CYCLONE&lang=en');
    if (res.ok) {
      const data = await res.json();
      const adv = data.advisory || {};

      const introEl = document.getElementById('ai-intro-text');
      if (introEl && adv.banner) {
        introEl.textContent = adv.banner;
      }

      const riskDesc = document.getElementById('ai-risk-desc');
      if (riskDesc && adv.immediate_actions && adv.immediate_actions.length > 0) {
        riskDesc.textContent = adv.immediate_actions[0];
      }

      const needsDesc = document.getElementById('ai-needs-desc');
      if (needsDesc && adv.checklist && adv.checklist.length > 0) {
        needsDesc.textContent = adv.checklist[0];
      }

      const actionDesc = document.getElementById('ai-action-desc');
      if (actionDesc && adv.immediate_actions && adv.immediate_actions.length > 1) {
        actionDesc.textContent = adv.immediate_actions[1];
      }
    }
  } catch (err) {
    console.warn('Error loading AI advisory:', err);
  }
}

/* ==========================================================================
   4. WEATHER MODE TOGGLE (SIMULATION VS LIVE WEATHER SYNC)
   ========================================================================== */
function initWeatherModeToggle() {
  const toggleBtn = document.getElementById('toggle-weather-mode');
  if (!toggleBtn) return;

  toggleBtn.addEventListener('click', async () => {
    const targetMode = currentWeatherMode === 'SIMULATION' ? 'LIVE' : 'SIMULATION';
    toggleBtn.disabled = true;

    try {
      if (targetMode === 'SIMULATION') {
        await fetch('/api/weather/simulate-cyclone', { method: 'POST' });
      } else {
        await fetch('/api/weather/sync-live', { method: 'POST' });
        lastSyncTimestamp = Date.now();
      }

      currentWeatherMode = targetMode;
      updateWeatherModeUI(currentWeatherMode);
      updateLastSyncDisplay();
      await refreshAllData();
    } catch (err) {
      console.error('Failed to toggle weather mode:', err);
    } finally {
      toggleBtn.disabled = false;
    }
  });
}

function updateWeatherModeUI(mode) {
  const toggleBtn = document.getElementById('toggle-weather-mode');
  const modeText = document.getElementById('mode-text');
  const mapModePill = document.getElementById('map-mode-pill');
  const metaStatus = document.getElementById('meta-scenario-status');

  const isSim = mode === 'SIMULATION';

  if (toggleBtn) {
    toggleBtn.className = `mode-pill ${isSim ? 'simulation' : 'live'}`;
  }
  if (modeText) {
    modeText.textContent = isSim ? '🔴 CYCLONE SIMULATION' : '🟢 LIVE WEATHER SYNCED';
  }
  if (mapModePill) {
    mapModePill.className = `mode-pill ${isSim ? 'simulation' : 'live'}`;
    mapModePill.textContent = isSim ? 'SIMULATED LANDFALL' : 'LIVE OPEN-METEO';
  }
  if (metaStatus) {
    metaStatus.textContent = isSim ? 'Simulated Cyclone Landfall Scenario' : 'Live Satellite Telemetry Synced';
  }
}

function initManualWeatherSync() {
  const syncBtn = document.getElementById('btn-sync-weather');
  const syncText = document.getElementById('sync-status-text');
  if (!syncBtn) return;

  syncBtn.addEventListener('click', async () => {
    syncBtn.disabled = true;
    syncBtn.classList.add('syncing');
    if (syncText) syncText.textContent = 'Syncing...';

    try {
      const res = await fetch('/api/weather/sync-live', { method: 'POST' });
      if (res.ok) {
        lastSyncTimestamp = Date.now();
        currentWeatherMode = 'LIVE';
        updateWeatherModeUI('LIVE');
        if (syncText) syncText.textContent = 'Synced!';
      }
      await refreshAllData();
      updateLastSyncDisplay();
    } catch (err) {
      console.error('Failed to sync live weather manually:', err);
      if (syncText) syncText.textContent = 'Sync Error';
    } finally {
      setTimeout(() => {
        syncBtn.classList.remove('syncing');
        syncBtn.disabled = false;
        if (syncText) syncText.textContent = 'Sync Live';
      }, 1200);
    }
  });
}

function updateLastSyncDisplay() {
  const label = document.getElementById('last-sync-label');
  if (!label) return;

  if (currentWeatherMode === 'SIMULATION') {
    label.textContent = 'Mode: Cyclone Landfall Simulation (Click "Sync Live" to fetch real-time)';
    return;
  }

  const diffSecs = Math.max(0, Math.floor((Date.now() - lastSyncTimestamp) / 1000));
  const diffMins = Math.floor(diffSecs / 60);

  if (diffMins < 1) {
    label.textContent = 'Auto-sync: every 10m · Updated just now';
  } else if (diffMins === 1) {
    label.textContent = 'Auto-sync: every 10m · Updated 1 min ago';
  } else {
    label.textContent = `Auto-sync: every 10m · Updated ${diffMins} mins ago`;
  }
}

/* ==========================================================================
   5. EMERGENCY INCIDENT REPORT MODAL (POST /api/sos)
   ========================================================================== */
function initReportModal() {
  const backdrop = document.getElementById('report-backdrop');
  const openBtn = document.getElementById('open-report');
  const closeBtn = document.getElementById('close-report');
  const cancelBtn = document.getElementById('cancel-report');
  const form = document.getElementById('incident-form');
  const submitBtn = document.getElementById('submit-report');
  const formMsg = document.getElementById('form-message');
  const resultCard = document.getElementById('dispatch-result-card');
  const districtSelect = document.getElementById('incident-district');
  const latInput = document.getElementById('incident-lat');
  const lonInput = document.getElementById('incident-lon');
  const gpsBtn = document.getElementById('btn-use-gps');

  if (!backdrop || !openBtn || !form) return;

  function openModal() {
    backdrop.classList.add('open');
    backdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (resultCard) resultCard.style.display = 'none';
    if (formMsg) formMsg.hidden = true;
    const firstField = document.getElementById('incident-type');
    if (firstField) firstField.focus();
  }

  function closeModal() {
    backdrop.classList.remove('open');
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  window.openReportModal = function(targetTeamName) {
    openModal();
    if (targetTeamName) {
      const descInput = document.getElementById('incident-desc');
      if (descInput) {
        descInput.value = `[EMERGENCY SOS TO ${targetTeamName.toUpperCase()}]: `;
        descInput.focus();
      }
    }
  };

  openBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (!backdrop.classList.contains('open')) return;
    if (e.key === 'Escape') closeModal();
  });

  // District dropdown updates coordinates
  if (districtSelect && latInput && lonInput) {
    districtSelect.addEventListener('change', () => {
      const selectedOption = districtSelect.options[districtSelect.selectedIndex];
      if (selectedOption) {
        latInput.value = selectedOption.dataset.lat || '19.8135';
        lonInput.value = selectedOption.dataset.lon || '85.8312';
        syncChatbotDistrict(districtSelect.value);
      }
    });
  }

  // Live GPS geolocation
  if (gpsBtn && latInput && lonInput) {
    gpsBtn.addEventListener('click', () => {
      if (navigator.geolocation) {
        gpsBtn.innerHTML = '<i data-lucide="loader" style="width:13px;height:13px;animation:spin 1s linear infinite;"></i> Locating...';
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            latInput.value = pos.coords.latitude.toFixed(4);
            lonInput.value = pos.coords.longitude.toFixed(4);
            gpsBtn.innerHTML = `✓ GPS: ${latInput.value}, ${lonInput.value}`;
            gpsBtn.style.color = '#10b981';
          },
          () => {
            latInput.value = '19.8135';
            lonInput.value = '85.8312';
            gpsBtn.textContent = 'Defaulted: Puri (GPS blocked)';
            gpsBtn.style.color = '#bf7713';
          }
        );
      }
    });
  }

  // Handle SOS Form Submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const phone = document.getElementById('incident-phone').value.trim();
    const type = document.getElementById('incident-type').value;
    const severity = document.getElementById('incident-severity').value;
    const description = document.getElementById('incident-description').value.trim();
    const lat = parseFloat(latInput.value) || 19.8135;
    const lon = parseFloat(lonInput.value) || 85.8312;

    if (!phone || !description) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Dispatching Units via AI Triage...';
    if (formMsg) formMsg.hidden = true;
    if (resultCard) resultCard.style.display = 'none';

    const fullMessage = `[${type} - Severity: ${severity}] ${description}`;

    try {
      const res = await fetch('/api/sos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contact_number: phone,
          latitude: lat,
          longitude: lon,
          message: fullMessage,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const inc = data.incident || {};
      const triage = data.triage || {};
      const shelter = data.assigned_shelter || {};

      if (resultCard) {
        resultCard.style.display = 'block';
        resultCard.innerHTML = `
          <strong>🚨 EMERGENCY RESCUE DISPATCH REGISTERED (#SOS-${inc.id || 'NEW'})</strong><br>
          • <strong>Assigned Team:</strong> ${inc.dispatch_unit || triage.dispatch_unit || 'ODRAF Multi-Hazard Rescue Unit'}<br>
          • <strong>Target Shelter:</strong> ${shelter.name || inc.nearest_shelter_name || 'Nearest Multipurpose Cyclone Shelter'}<br>
          • <strong>Estimated Arrival (ETA):</strong> ~${shelter.distance_km ? Math.max(3, Math.round(shelter.distance_km * 2.5)) : 7} mins (${shelter.distance_km || 1.2} km away)<br>
          • <strong>Status:</strong> ${inc.status || 'DISPATCHED'}<br>
          <small style="color:#047857;display:block;margin-top:6px;">OSDMA Emergency Operations Center has locked your coordinates. Live map has been updated.</small>
        `;
      }

      form.reset();
      latInput.value = '19.8135';
      lonInput.value = '85.8312';

      // Refresh dashboard stats & map immediately
      await refreshAllData();

      // Pan map to newly reported incident location
      if (map) {
        map.flyTo([lat, lon], 12);
      }
    } catch (err) {
      console.error('Failed to submit SOS:', err);
      if (formMsg) {
        formMsg.hidden = false;
        formMsg.className = 'form-message error';
        formMsg.textContent = 'Error connecting to emergency dispatch server. Please call toll-free helpline 1070 or 112 directly.';
      }
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Dispatch Rescue / ଉଦ୍ଧାର ପଠାନ୍ତୁ';
    }
  });
}

/* ==========================================================================
   7. RESQ AI ASSISTANT CHATBOT INTERFACE
   ========================================================================== */
function initChatbot() {
  const launcherBtn = document.getElementById('chatbot-launcher');
  const chatWindow = document.getElementById('chatbot-window');
  const closeBtn = document.getElementById('chatbot-close-btn');
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const userInput = document.getElementById('chat-user-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const langEnBtn = document.getElementById('chat-lang-en');
  const langOdBtn = document.getElementById('chat-lang-od');
  const contextText = document.getElementById('chat-context-text');
  const districtSelect = document.getElementById('chat-district-select');
  const gpsBtn = document.getElementById('chat-use-gps-btn');
  const quickChipsContainer = document.getElementById('chat-quick-chips');

  // Voice Search Elements
  const micBtn = document.getElementById('chat-mic-btn');
  const voiceStatus = document.getElementById('chat-voice-status');
  const voiceLabel = document.getElementById('chat-voice-label');
  const voiceStopBtn = document.getElementById('chat-voice-stop-btn');

  if (!launcherBtn || !chatWindow || !chatForm || !userInput) return;

  // Chatbot State
  let chatLang = 'en';
  let chatLat = 20.2961;
  let chatLon = 85.8245;
  let chatLocationName = 'Bhubaneswar';
  let isAwaitingResponse = false;
  let hasInitializedConversation = false;

  // District Selector in Chat Context Strip
  if (districtSelect) {
    const updateChatCoordsFromSelect = () => {
      const opt = districtSelect.options[districtSelect.selectedIndex];
      if (opt) {
        chatLat = parseFloat(opt.dataset.lat) || 20.2961;
        chatLon = parseFloat(opt.dataset.lon) || 85.8245;
        chatLocationName = opt.value;
      }
    };
    updateChatCoordsFromSelect();
    districtSelect.addEventListener('change', updateChatCoordsFromSelect);
  }

  // Voice State: Native Web Speech API for English + Bhashini ASR for Odia
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const isSpeechSupported = !!SpeechRecognition;
  let recognition = null;
  let isListening = false;
  let speechPreText = '';

  // Bhashini Microphone Recording State
  let bhashiniMediaStream = null;
  let bhashiniAudioContext = null;
  let bhashiniProcessor = null;
  let bhashiniSource = null;
  let bhashiniAudioSamples = [];

  function encodeWAV(samples, sampleRate = 16000) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    function writeString(view, offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, 1, true); // Mono channel
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return new Blob([view], { type: 'audio/wav' });
  }

  function getSpeechLocale(lang) {
    return lang === 'od' ? 'or-IN' : 'en-IN';
  }

  function getOrCreateEnglishRecognition() {
    if (!isSpeechSupported) return null;

    if (recognition) {
      try { recognition.abort(); } catch (e) {}
      recognition = null;
    }

    try {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      rec.lang = 'en-IN';

      rec.onstart = () => {
        isListening = true;
        if (micBtn) {
          micBtn.classList.add('listening');
          micBtn.disabled = false;
        }
        if (voiceStatus) {
          voiceStatus.style.display = 'flex';
          if (voiceLabel) {
            voiceLabel.textContent = 'Listening in English (en-IN)... Speak now';
          }
        }
        speechPreText = userInput.value ? (userInput.value.trim() + ' ') : '';
        updateMicTooltip();
      };

      rec.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const res = event.results[i];
          if (res.isFinal) {
            finalTranscript += res[0].transcript;
          } else {
            interimTranscript += res[0].transcript;
          }
        }

        const transcript = finalTranscript || interimTranscript;
        if (transcript) {
          userInput.value = speechPreText + transcript;
        }
      };

      rec.onerror = (event) => {
        console.warn('English Speech recognition error:', event.error);
        const err = event.error;
        if (err === 'not-allowed' || err === 'service-not-allowed') {
          showVoiceNotice('⚠️ Microphone access denied. Please click the camera/microphone icon in your browser address bar and allow permissions.');
        } else if (err === 'network') {
          showVoiceNotice('⚠️ Speech recognition network connection error. Check your internet connection.');
        } else if (err !== 'no-speech') {
          showVoiceNotice(`⚠️ Speech recognition notice: ${err}`);
        }
        cleanupVoiceState();
      };

      rec.onend = () => {
        cleanupVoiceState();
      };

      return rec;
    } catch (e) {
      console.warn('Failed to initialize SpeechRecognition instance:', e);
      return null;
    }
  }

  async function startBhashiniOdiaRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showVoiceNotice('⚠️ Your browser does not support microphone audio capture. Please use Google Chrome, Edge, or Firefox over HTTPS/localhost.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      bhashiniMediaStream = stream;
      bhashiniAudioSamples = [];

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      bhashiniAudioContext = new AudioCtx({ sampleRate: 16000 });
      if (bhashiniAudioContext.state === 'suspended') {
        await bhashiniAudioContext.resume();
      }
      bhashiniSource = bhashiniAudioContext.createMediaStreamSource(stream);
      bhashiniProcessor = bhashiniAudioContext.createScriptProcessor(4096, 1, 1);

      bhashiniProcessor.onaudioprocess = (e) => {
        if (!isListening) return;
        const input = e.inputBuffer.getChannelData(0);
        bhashiniAudioSamples.push(new Float32Array(input));
      };

      bhashiniSource.connect(bhashiniProcessor);
      bhashiniProcessor.connect(bhashiniAudioContext.destination);

      isListening = true;
      if (micBtn) {
        micBtn.classList.add('listening');
        micBtn.disabled = false;
      }
      if (voiceStatus) {
        voiceStatus.style.display = 'flex';
        if (voiceLabel) {
          voiceLabel.textContent = 'ଓଡ଼ିଆରେ ଶୁଣୁଅଛି (BHASHINI ASR)... କୁହନ୍ତୁ';
        }
      }
      speechPreText = userInput.value ? (userInput.value.trim() + ' ') : '';
      updateMicTooltip();

    } catch (err) {
      console.error('Bhashini microphone access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        showVoiceNotice('⚠️ ମାଇକ୍ରୋଫୋନ୍ ଅନୁମତି ମିଳିଲା ନାହିଁ। ବ୍ରାଉଜର୍ ଆଡ୍ରେସ୍ ବାର୍‌ରେ କ୍ଲିକ୍ କରି ମାଇକ୍ରୋଫୋନ୍ ଅନୁମତି ଦିଅନ୍ତୁ।');
      } else {
        showVoiceNotice(`⚠️ ମାଇକ୍ରୋଫୋନ୍ ସମସ୍ୟା: ${err.message || 'ଅଜ୍ଞାତ ତ୍ରୁଟି'}`);
      }
      cleanupVoiceState();
    }
  }

  async function stopBhashiniOdiaRecording() {
    if (!isListening) return;

    if (voiceLabel) {
      voiceLabel.textContent = 'Bhashini ASR ଦ୍ଵାରା ପ୍ରକ୍ରିୟାକରଣ ଚାଲିଛି...';
    }

    // Capture samples before stopping stream
    const samples = bhashiniAudioSamples;
    const stream = bhashiniMediaStream;
    const ctx = bhashiniAudioContext;
    const proc = bhashiniProcessor;
    const src = bhashiniSource;

    // Disconnect audio pipeline
    try {
      if (proc && src) src.disconnect();
      if (proc && ctx) proc.disconnect();
      if (stream) stream.getTracks().forEach(t => t.stop());
      if (ctx && ctx.state !== 'closed') ctx.close();
    } catch (e) {}

    bhashiniMediaStream = null;
    bhashiniAudioContext = null;
    bhashiniProcessor = null;
    bhashiniSource = null;
    bhashiniAudioSamples = [];
    isListening = false;

    if (micBtn) micBtn.classList.remove('listening');
    updateMicTooltip();

    // Flatten audio samples
    let totalLen = samples.reduce((acc, s) => acc + s.length, 0);
    if (totalLen < 1600) {
      // Less than 0.1s of audio recorded
      if (voiceStatus) voiceStatus.style.display = 'none';
      userInput.focus();
      return;
    }

    const merged = new Float32Array(totalLen);
    let offset = 0;
    for (const s of samples) {
      merged.set(s, offset);
      offset += s.length;
    }

    const wavBlob = encodeWAV(merged, 16000);

    // Convert to Base64 and send to FastAPI /api/ai/asr
    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64Data = reader.result;
      try {
        const resp = await fetch('/api/ai/asr', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            audio_base64: base64Data,
            language: 'or',
            audio_format: 'wav',
            sampling_rate: 16000
          })
        });

        if (voiceStatus) voiceStatus.style.display = 'none';

        if (!resp.ok) {
          throw new Error(`ASR API returned HTTP ${resp.status}`);
        }

        const data = await resp.json();

        if (data.status === 'success' && data.transcript) {
          userInput.value = speechPreText + data.transcript;
          userInput.focus();
        } else if (data.status === 'config_required') {
          showVoiceNotice('⚠️ Bhashini ASR ସେଟ୍‌ଅପ୍: ଓଡ଼ିଆ ଭଏସ୍ ରେକଗ୍ନିସନ୍ ପାଇଁ Bhashini API କ୍ରେଡେନ୍ସିଆଲ୍ ଆବଶ୍ୟକ। ଦୟାକରି backend .env ରେ BHASHINI_USER_ID ଏବଂ BHASHINI_API_KEY କନଫିଗର୍ କରନ୍ତୁ।');
          userInput.focus();
        } else if (data.status === 'no_speech') {
          showVoiceNotice('⚠️ କୌଣସି ଶବ୍ଦ ଶୁଣାଗଲା ନାହିଁ। ଦୟାକରି ପୁଣି ମାଇକ୍ ବଟନ୍ ଦବାଇ କୁହନ୍ତୁ।');
          userInput.focus();
        } else {
          showVoiceNotice(`⚠️ Bhashini ASR: ${data.message || 'ଭଏସ୍ ପ୍ରକ୍ରିୟାକରଣ ବିଫଳ ହେଲା'}`);
          userInput.focus();
        }
      } catch (err) {
        console.error('ASR transcription failed:', err);
        if (voiceStatus) voiceStatus.style.display = 'none';
        showVoiceNotice('⚠️ Bhashini ASR ସର୍ଭର ସହିତ ସଂଯୋଗ ବିଫଳ ହେଲା। ଦୟାକରି ଇଣ୍ଟରନେଟ୍ ଯାଞ୍ଚ କରନ୍ତୁ।');
        userInput.focus();
      }
    };
    reader.readAsDataURL(wavBlob);
  }

  function updateMicTooltip() {
    if (!micBtn) return;

    if (chatLang === 'od') {
      if (isListening) {
        micBtn.title = 'ରେକର୍ଡିଂ ବନ୍ଦ କରନ୍ତୁ (Stop Bhashini ASR)';
      } else {
        micBtn.title = 'ଭଏସ୍ ଇନପୁଟ୍: ଓଡ଼ିଆ (Bhashini ASR) - କହିବା ପାଇଁ କ୍ଲିକ୍ କରନ୍ତୁ';
      }
    } else {
      if (!isSpeechSupported) {
        micBtn.title = 'Voice recognition not supported in this browser';
        return;
      }
      if (isListening) {
        micBtn.title = 'Stop listening';
      } else {
        micBtn.title = 'Voice input: English (en-IN) - Click to speak';
      }
    }
  }

  function startVoiceRecognition() {
    if (isAwaitingResponse) return;

    if (chatLang === 'od') {
      // Odia -> Native AudioContext Recording -> Bhashini ASR Pipeline
      cleanupVoiceState();
      startBhashiniOdiaRecording();
    } else {
      // English -> Browser Web Speech API (en-IN)
      if (!isSpeechSupported) {
        showVoiceNotice('⚠️ Voice recognition is not supported in this browser. Please use Chrome or Edge.');
        return;
      }
      cleanupVoiceState();
      recognition = getOrCreateEnglishRecognition();
      if (!recognition) return;
      try {
        recognition.start();
      } catch (e) {
        console.warn('Failed to start English speech recognition:', e);
        cleanupVoiceState();
      }
    }
  }

  function stopVoiceRecognition() {
    if (chatLang === 'od') {
      stopBhashiniOdiaRecording();
    } else {
      if (recognition) {
        try { recognition.stop(); } catch (e) {
          try { recognition.abort(); } catch (err) {}
        }
      }
      cleanupVoiceState();
    }
  }

  function cleanupVoiceState() {
    isListening = false;
    if (micBtn) {
      micBtn.classList.remove('listening');
      micBtn.disabled = false;
    }
    if (voiceStatus) voiceStatus.style.display = 'none';
    updateMicTooltip();

    // Clean English recognition
    try {
      if (recognition) recognition.abort();
    } catch (e) {}
    recognition = null;

    // Clean Bhashini recorder if active
    try {
      if (bhashiniProcessor && bhashiniSource) bhashiniSource.disconnect();
      if (bhashiniProcessor && bhashiniAudioContext) bhashiniProcessor.disconnect();
      if (bhashiniMediaStream) bhashiniMediaStream.getTracks().forEach(t => t.stop());
      if (bhashiniAudioContext && bhashiniAudioContext.state !== 'closed') bhashiniAudioContext.close();
    } catch (e) {}
    bhashiniMediaStream = null;
    bhashiniAudioContext = null;
    bhashiniProcessor = null;
    bhashiniSource = null;
    bhashiniAudioSamples = [];

    userInput.focus();
  }

  function showVoiceNotice(msg) {
    const noticeDiv = document.createElement('div');
    noticeDiv.className = 'chat-msg chat-msg-bot';
    noticeDiv.innerHTML = `
      <div class="chat-bubble-bot" style="border-left: 3px solid #ef782d; background: #fff7ed;">
        <p style="margin:0; color:#9a3412; font-size:12.5px;">${escapeHtml(msg)}</p>
      </div>
      <span class="chat-msg-time">${getCurrentTime()}</span>
    `;
    chatMessages.appendChild(noticeDiv);
    scrollChatToBottom();
  }

  // Bind Mic Buttons
  if (micBtn) {
    micBtn.addEventListener('click', () => {
      if (isListening) {
        stopVoiceRecognition();
      } else {
        startVoiceRecognition();
      }
    });
    updateMicTooltip();
  }

  if (voiceStopBtn) {
    voiceStopBtn.addEventListener('click', stopVoiceRecognition);
  }

  // Toggle Chatbot Open/Close
  function openChat() {
    chatWindow.hidden = false;
    launcherBtn.setAttribute('aria-expanded', 'true');
    launcherBtn.style.display = 'none';

    if (!hasInitializedConversation) {
      renderWelcomeMessage();
      hasInitializedConversation = true;
    }

    setTimeout(() => {
      userInput.focus();
      scrollChatToBottom();
    }, 100);

    if (window.lucide) window.lucide.createIcons();
  }

  function closeChat() {
    chatWindow.hidden = true;
    launcherBtn.setAttribute('aria-expanded', 'false');
    launcherBtn.style.display = 'flex';
    if (isListening) {
      stopVoiceRecognition();
    }
  }

  launcherBtn.addEventListener('click', openChat);
  closeBtn.addEventListener('click', closeChat);

  // Global trigger to ask ResQ Chatbot directly
  window.askResQChatbot = function(promptText) {
    openChat();
    if (userInput && promptText) {
      userInput.value = promptText;
      userInput.focus();
    }
  };

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !chatWindow.hidden) {
      closeChat();
    }
  });

  // Language Switcher Handlers
  langEnBtn.addEventListener('click', () => switchLanguage('en'));
  langOdBtn.addEventListener('click', () => switchLanguage('od'));

  function switchLanguage(lang) {
    if (chatLang === lang) return;
    chatLang = lang;

    if (isListening) {
      stopVoiceRecognition();
    }
    if (recognition) {
      recognition.lang = getSpeechLocale(chatLang);
    }
    updateMicTooltip();

    langEnBtn.classList.toggle('active', lang === 'en');
    langOdBtn.classList.toggle('active', lang === 'od');

    if (lang === 'en') {
      userInput.placeholder = 'Ask ResQ AI about shelters, cyclone wind, flood safety...';
      updateQuickChips([
        { query: 'Where is the nearest shelter in Puri?', label: 'Nearest Shelter', icon: 'home' },
        { query: 'What is the current cyclone alert status in Puri?', label: 'Cyclone Status', icon: 'cloud-lightning' },
        { query: 'What are the essential flood safety steps when water enters house?', label: 'Flood Safety', icon: 'waves' },
        { query: 'Someone got bitten by a snake in flood water, what first aid should I give?', label: 'Snakebite First Aid', icon: 'shield-alert' },
        { query: 'What are the official OSDMA emergency helpline numbers?', label: 'Emergency Helplines', icon: 'phone' }
      ]);
    } else {
      userInput.placeholder = 'ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀ, ପବନର ବେଗ, ବନ୍ୟା ସୁରକ୍ଷା ବିଷୟରେ ପଚାରନ୍ତୁ...';
      updateQuickChips([
        { query: 'ପୁରୀରେ ସବୁଠାରୁ ନିକଟତମ ଆଶ୍ରୟସ୍ଥଳୀ କେଉଁଠାରେ ଅଛି?', label: 'ନିକଟତମ ଆଶ୍ରୟ', icon: 'home' },
        { query: 'ପୁରୀରେ ବର୍ତ୍ତମାନ ବାତ୍ୟା ଓ ପବନର ସ୍ଥିତି କଣ?', label: 'ବାତ୍ୟା ସତର୍କତା', icon: 'cloud-lightning' },
        { query: 'ଘରେ ବନ୍ୟା ପାଣି ପଶିଗଲେ କି ସୁରକ୍ଷା ପଦକ୍ଷେପ ନେବା ଉଚିତ?', label: 'ବନ୍ୟା ସୁରକ୍ଷା', icon: 'waves' },
        { query: 'ବନ୍ୟା ପାଣିରେ ସାପ କାମୁଡ଼ିଲେ କି ପ୍ରାଥମିକ ଚିକିତ୍ସା କରିବା?', label: 'ସର୍ପାଘାତ ଚିକିତ୍ସା', icon: 'shield-alert' },
        { query: 'ଜରୁରୀକାଳୀନ ସହାୟତା ପାଇଁ OSDMA ହେଲ୍ପଲାଇନ ନମ୍ବର କଣ?', label: 'ହେଲ୍ପଲାଇନ', icon: 'phone' }
      ]);
    }

    if (window.lucide) window.lucide.createIcons();
  }

  function updateQuickChips(chips) {
    if (!quickChipsContainer) return;
    quickChipsContainer.innerHTML = chips.map(chip => `
      <button type="button" class="quick-chip" data-query="${chip.query}">
        <i data-lucide="${chip.icon}"></i> ${chip.label}
      </button>
    `).join('');
    bindQuickChips();
  }

  function bindQuickChips() {
    const chips = quickChipsContainer.querySelectorAll('.quick-chip');
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const query = chip.dataset.query;
        if (query && !isAwaitingResponse) {
          userInput.value = query;
          handleUserSend(query);
        }
      });
    });
  }
  bindQuickChips();

  // GPS Context Handler
  if (gpsBtn) {
    gpsBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
      }

      gpsBtn.disabled = true;
      const originalText = gpsBtn.innerHTML;
      gpsBtn.innerHTML = '<span>Locating...</span>';

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          chatLat = Number(pos.coords.latitude.toFixed(4));
          chatLon = Number(pos.coords.longitude.toFixed(4));
          chatLocationName = `User GPS (${chatLat}° N, ${chatLon}° E)`;

          if (contextText) {
            contextText.textContent = `${chatLocationName}`;
          }

          gpsBtn.disabled = false;
          gpsBtn.innerHTML = originalText;
          if (window.lucide) window.lucide.createIcons();
        },
        (err) => {
          console.warn('Chat GPS request error:', err);
          gpsBtn.disabled = false;
          gpsBtn.innerHTML = originalText;
          if (window.lucide) window.lucide.createIcons();
          alert('Could not acquire GPS position. Continuing with default coastal Odisha coordinates.');
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }

  // Render Welcome Message
  function renderWelcomeMessage() {
    const isOd = chatLang === 'od';
    const welcomeHtml = isOd
      ? `
        <div class="chat-msg chat-msg-bot">
          <div class="chat-bubble-bot">
            <p>ନମସ୍କାର! ମୁଁ <strong>ResQ AI Assistant</strong>, ଓଡ଼ିଶା ରାଜ୍ୟ ବିପର୍ଯ୍ୟୟ ପରିଚାଳନା କର୍ତ୍ତୃପକ୍ଷ (OSDMA) ଏବଂ ରିଅଲ-ଟାଇମ୍ ପାଣିପାଗ ତଥ୍ୟ ସହିତ ସଂଯୁକ୍ତ ଆପଣଙ୍କ ୨୪/୭ ଏଆଇ ସହାୟକ।</p>
            <p>ମୁଁ ଆପଣଙ୍କୁ ନିମ୍ନ ବିଷୟରେ ସାହାଯ୍ୟ କରିପାରିବି:</p>
            <ul>
              <li><strong>ନିକଟତମ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀ:</strong> ଖାଲି ଥିବା ସିଟ୍ ଓ ଯୋଗାଯୋଗ ନମ୍ବର</li>
              <li><strong>ବାତ୍ୟା ସତର୍କତା:</strong> ପବନର ବେଗ, ସମୁଦ୍ର ତରଙ୍ଗ ଓ ବାତ୍ୟା ଗତିପଥ</li>
              <li><strong>ବନ୍ୟା ସୁରକ୍ଷା ଓ ଉଦ୍ଧାର:</strong> ଘରେ ପାଣି ପଶିଲେ କାର୍ଯ୍ୟାନୁଷ୍ଠାନ</li>
              <li><strong>ଜରୁରୀକାଳୀନ ପ୍ରାଥମିକ ଚିକିତ୍ସା:</strong> ସର୍ପାଘାତ, ଡଙ୍ଗା ଉଦ୍ଧାର, SOS ପରାମର୍ଶ</li>
            </ul>
            <p>ତଳେ ଥିବା ପ୍ରଶ୍ନ ବଟନ୍ କ୍ଲିକ୍ କରନ୍ତୁ କିମ୍ବା ଆପଣଙ୍କ ପ୍ରଶ୍ନ ଲେଖନ୍ତୁ।</p>
          </div>
          <span class="chat-msg-time">${getCurrentTime()}</span>
        </div>
      `
      : `
        <div class="chat-msg chat-msg-bot">
          <div class="chat-bubble-bot">
            <p>Hello! I am <strong>ResQ AI Assistant</strong>, your real-time multi-hazard guidance copilot powered by OSDMA intelligence and live coastal telemetry.</p>
            <p>I am equipped to provide instant guidance for:</p>
            <ul>
              <li><strong>Nearest Cyclone Shelters:</strong> Real-time bed availability &amp; direct navigation</li>
              <li><strong>Cyclone Alerts &amp; Wind Telemetry:</strong> Coastal surge, gust speeds &amp; landfall tracking</li>
              <li><strong>Flood Safety &amp; Evacuation:</strong> Critical SOPs when water rises inside homes</li>
              <li><strong>Emergency First Aid:</strong> Snakebite protocol, trauma handling &amp; rescue SOS</li>
            </ul>
            <p>Click a suggested query below or type your emergency question.</p>
          </div>
          <span class="chat-msg-time">${getCurrentTime()}</span>
        </div>
      `;

    chatMessages.innerHTML = welcomeHtml;
    if (window.lucide) window.lucide.createIcons();
    scrollChatToBottom();
  }

  // Handle Form Submission
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (isListening) {
      stopVoiceRecognition();
    }
    const query = userInput.value.trim();
    if (query && !isAwaitingResponse) {
      handleUserSend(query);
    }
  });

  async function handleUserSend(text) {
    if (!text || isAwaitingResponse) return;

    // Append User Message
    appendUserMessage(text);
    userInput.value = '';
    isAwaitingResponse = true;
    sendBtn.disabled = true;

    // Show Typing Indicator
    const typingElement = appendTypingIndicator();
    scrollChatToBottom();

    // Setup Timeout Controller (25 seconds for LLM external call)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    try {
      const response = await fetch('/api/ai/copilot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_message: text,
          latitude: chatLat,
          longitude: chatLon,
          language: chatLang
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      removeTypingIndicator(typingElement);
      renderBotResponse(data);
    } catch (err) {
      clearTimeout(timeoutId);
      console.error('Chatbot API request failed:', err);
      removeTypingIndicator(typingElement);
      renderErrorMessage(err);
    } finally {
      isAwaitingResponse = false;
      sendBtn.disabled = false;
      scrollChatToBottom();
      setTimeout(() => userInput.focus(), 100);
    }
  }

  function appendUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-msg chat-msg-user';
    msgDiv.innerHTML = `
      <div class="chat-bubble-user">${escapeHtml(text)}</div>
      <span class="chat-msg-time">${getCurrentTime()}</span>
    `;
    chatMessages.appendChild(msgDiv);
    scrollChatToBottom();
  }

  function appendTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-msg chat-msg-bot';
    typingDiv.id = 'chat-typing-indicator';
    typingDiv.innerHTML = `
      <div class="chat-typing-bubble">
        <div class="typing-dots">
          <span></span><span></span><span></span>
        </div>
        <span class="typing-text">ResQ AI is analyzing telemetry &amp; OSDMA SOPs...</span>
      </div>
    `;
    chatMessages.appendChild(typingDiv);
    return typingDiv;
  }

  function removeTypingIndicator(typingElem) {
    if (typingElem && typingElem.parentNode) {
      typingElem.parentNode.removeChild(typingElem);
    }
    const elem = document.getElementById('chat-typing-indicator');
    if (elem) elem.remove();
  }

  function renderBotResponse(data) {
    const copilot = data.copilot || {};
    const shelter = data.assigned_shelter;
    const isOd = chatLang === 'od';

    // Text selection: Odia if requested, else English
    let replyText = '';
    if (isOd && copilot.reply_od) {
      replyText = copilot.reply_od;
    } else if (copilot.reply_en) {
      replyText = copilot.reply_en;
    } else {
      replyText = data.ai_response || 'Assessment completed successfully based on active telemetry.';
    }

    // Format Markdown / Newlines in text
    let formattedText = formatReplyText(replyText);

    // Emergency Banner
    let alertBannerHtml = '';
    if (copilot.is_emergency) {
      const urgency = copilot.urgency_score || 4;
      alertBannerHtml = `
        <div class="chat-alert-banner">
          <i data-lucide="triangle-alert"></i>
          <span>EMERGENCY ADVISORY · URGENCY LEVEL ${urgency}/5 (${copilot.intent || 'CRITICAL'})</span>
        </div>
      `;
    }

    // Checklist rendering
    let checklistHtml = '';
    if (Array.isArray(copilot.safety_checklist) && copilot.safety_checklist.length > 0) {
      const checklistItems = copilot.safety_checklist
        .map(item => `
          <div class="chat-checklist-item">
            <i data-lucide="check-circle-2"></i>
            <span>${escapeHtml(item)}</span>
          </div>
        `).join('');
      
      checklistHtml = `
        <div style="margin-top:10px;">
          <strong style="font-size:12px;color:#10263d;">${isOd ? 'ସୁରକ୍ଷା ନିର୍ଦ୍ଦେଶାବଳୀ (Action Checklist):' : 'Safety SOP Action Checklist:'}</strong>
          <div class="chat-checklist">
            ${checklistItems}
          </div>
        </div>
      `;
    }

    // Assigned Shelter Card
    let shelterCardHtml = '';
    if (shelter && shelter.name) {
      const dist = shelter.distance_km != null ? `${Number(shelter.distance_km).toFixed(1)} km away` : 'Nearby';
      const available = shelter.available_spots ?? (shelter.capacity - (shelter.occupied || 0));
      shelterCardHtml = `
        <div class="chat-shelter-card">
          <div class="chat-shelter-card-title">
            <i data-lucide="home"></i>
            <span>${escapeHtml(shelter.name)}</span>
          </div>
          <div class="chat-shelter-meta">
            <div>📍 <strong>District:</strong> ${escapeHtml(shelter.district || 'Coastal Zone')} (${dist})</div>
            <div>🛏️ <strong>Beds Available:</strong> ${available} / ${shelter.capacity || 'N/A'} capacity</div>
            ${shelter.contact_phone ? `<div>📞 <strong>Helpline:</strong> <a href="tel:${shelter.contact_phone}" style="color:#ef782d;font-weight:700;">${shelter.contact_phone}</a></div>` : ''}
          </div>
          <div class="chat-shelter-actions">
            <button type="button" class="chat-card-btn primary chat-fly-map-btn" 
              data-lat="${shelter.latitude}" 
              data-lon="${shelter.longitude}" 
              data-name="${escapeHtml(shelter.name)}"
              title="Fly to this shelter on map">
              <i data-lucide="map-pin"></i> View on Map
            </button>
            ${shelter.contact_phone ? `
              <a href="tel:${shelter.contact_phone}" class="chat-card-btn secondary">
                <i data-lucide="phone"></i> Call Shelter
              </a>
            ` : ''}
          </div>
        </div>
      `;
    }

    // Assemble message
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-msg chat-msg-bot';
    msgDiv.innerHTML = `
      <div class="chat-bubble-bot">
        ${alertBannerHtml}
        <div>${formattedText}</div>
        ${checklistHtml}
        ${shelterCardHtml}
      </div>
      <span class="chat-msg-time">${getCurrentTime()}</span>
    `;

    chatMessages.appendChild(msgDiv);

    // Bind "View on Map" buttons
    const mapBtns = msgDiv.querySelectorAll('.chat-fly-map-btn');
    mapBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const lat = parseFloat(btn.dataset.lat);
        const lon = parseFloat(btn.dataset.lon);
        const name = btn.dataset.name;
        if (map && !isNaN(lat) && !isNaN(lon)) {
          // Pan map
          map.flyTo([lat, lon], 13);
          
          // Open popup if marker exists, or add a highlight circle
          L.circleMarker([lat, lon], {
            radius: 12,
            color: '#ef782d',
            fillColor: '#ef782d',
            fillOpacity: 0.4,
            weight: 3
          }).addTo(map).bindPopup(`<strong>${name}</strong><br>Focused via ResQ AI Assistant`).openPopup();

          // On mobile, minimize chat window to reveal map
          if (window.innerWidth <= 768) {
            closeChat();
            const mapSection = document.getElementById('live-map');
            if (mapSection) mapSection.scrollIntoView({ behavior: 'smooth' });
          }
        }
      });
    });

    if (window.lucide) window.lucide.createIcons();
    scrollChatToBottom();
  }

  function renderErrorMessage(err) {
    const isOd = chatLang === 'od';
    const isTimeout = err && (err.name === 'AbortError' || err.message?.includes('abort'));

    const errorHtml = isOd
      ? `
        <div class="chat-msg chat-msg-bot">
          <div class="chat-bubble-bot">
            <div class="chat-alert-banner">
              <i data-lucide="alert-triangle"></i>
              <span>ସଂଯୋଗ ବିଳମ୍ବ (Network Delay)</span>
            </div>
            <p>${isTimeout ? 'ଲାଇଭ୍ ରାଡାର୍ ଡାଟା ପ୍ରକ୍ରିୟାକରଣରେ ଅଧିକ ସମୟ ଲାଗୁଛି।' : 'ସର୍ଭର ସହିତ ସଂଯୋଗ ହୋଇପାରିଲା ନାହିଁ।'}</p>
            <p><strong>ଜରୁରୀକାଳୀନ ପରିସ୍ଥିତିରେ ତୁରନ୍ତ ଏଠାରେ ଯୋଗାଯୋଗ କରନ୍ତୁ:</strong></p>
            <ul>
              <li><strong>ରାଜ୍ୟ ଜରୁରୀକାଳୀନ କେନ୍ଦ୍ର (OSDMA SEOC):</strong> <a href="tel:1079" style="color:#c94242;font-weight:700;">1079</a></li>
              <li><strong>ସମସ୍ତ ଜରୁରୀକାଳୀନ ସେବା (ପୋଲିସ/ଅଗ୍ନିଶମ/ଆମ୍ବୁଲାନ୍ସ):</strong> <a href="tel:112" style="color:#c94242;font-weight:700;">112</a></li>
              <li><strong>ପୁରୀ ଜିଲ୍ଲା କଣ୍ଟ୍ରୋଲ ରୁମ:</strong> <a href="tel:06752222044" style="color:#10263d;font-weight:700;">06752-222044</a></li>
            </ul>
          </div>
          <span class="chat-msg-time">${getCurrentTime()}</span>
        </div>
      `
      : `
        <div class="chat-msg chat-msg-bot">
          <div class="chat-bubble-bot">
            <div class="chat-alert-banner">
              <i data-lucide="alert-triangle"></i>
              <span>CONNECTION DELAY / TIMEOUT</span>
            </div>
            <p>${isTimeout ? 'The AI copilot took longer than expected to synthesize live atmospheric telemetry.' : 'Unable to complete request to the disaster telemetry backend.'}</p>
            <p><strong>For immediate life-saving emergency rescue, contact:</strong></p>
            <ul>
              <li><strong>OSDMA State Emergency Center:</strong> <a href="tel:1079" style="color:#c94242;font-weight:700;">1079</a> (Toll-Free)</li>
              <li><strong>Emergency Response Support:</strong> <a href="tel:112" style="color:#c94242;font-weight:700;">112</a></li>
              <li><strong>Puri Disaster Control Room:</strong> <a href="tel:06752222044" style="color:#10263d;font-weight:700;">06752-222044</a></li>
            </ul>
          </div>
          <span class="chat-msg-time">${getCurrentTime()}</span>
        </div>
      `;

    const msgDiv = document.createElement('div');
    msgDiv.innerHTML = errorHtml;
    chatMessages.appendChild(msgDiv.firstElementChild);
    if (window.lucide) window.lucide.createIcons();
    scrollChatToBottom();
  }

  function formatReplyText(text) {
    if (!text) return '';
    // Escape HTML first
    let escaped = escapeHtml(text);

    // Convert bold **text** to <strong>text</strong>
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Split paragraphs by double newline
    const paragraphs = escaped.split(/\n\n+/);
    return paragraphs.map(p => {
      // Convert single newlines within paragraph to <br>
      const withBr = p.replace(/\n/g, '<br>');
      return `<p>${withBr}</p>`;
    }).join('');
  }

  function scrollChatToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

/* ==========================================================================
   8. DISASTER NEWS BULLETIN CONTROLLER
   ========================================================================== */
function initDisasterNews() {
  const newsSection = document.getElementById('disaster-news-section');
  if (!newsSection) return;

  const headlineEl = document.getElementById('news-item-headline');
  const summaryEl = document.getElementById('news-item-summary');
  const severityEl = document.getElementById('news-item-severity');
  const locationEl = document.getElementById('news-item-location');
  const timeEl = document.getElementById('news-item-time');
  const actionEl = document.getElementById('news-item-action');
  const sourceEl = document.getElementById('news-item-source');
  const counterEl = document.getElementById('news-counter');
  const prevBtn = document.getElementById('news-prev-btn');
  const nextBtn = document.getElementById('news-next-btn');
  const askCopilotBtn = document.getElementById('btn-news-ask-copilot');
  const filterBtns = document.querySelectorAll('.news-filter-btn');

  let newsList = [];
  let filteredList = [];
  let activeIndex = 0;
  let activeCategory = 'ALL';
  let rotateInterval = null;

  async function fetchNews() {
    try {
      const res = await fetch('/api/disaster-news');
      if (!res.ok) throw new Error('Failed to fetch disaster news');
      const data = await res.json();
      if (data && data.news && data.news.length > 0) {
        newsList = data.news;
        applyCategoryFilter();
      }
    } catch (err) {
      console.warn('Disaster news fetch error:', err);
    }
  }

  function applyCategoryFilter() {
    if (activeCategory === 'ALL') {
      filteredList = [...newsList];
    } else {
      filteredList = newsList.filter(item => item.category === activeCategory);
    }
    if (filteredList.length === 0) {
      filteredList = [...newsList];
    }
    activeIndex = 0;
    renderCurrentNews();
  }

  function renderCurrentNews() {
    if (!filteredList || filteredList.length === 0) return;
    const item = filteredList[activeIndex];
    if (!item) return;

    if (headlineEl) headlineEl.textContent = item.headline;
    if (summaryEl) summaryEl.textContent = item.summary;
    if (severityEl) {
      severityEl.textContent = item.badge || item.severity;
      severityEl.className = `news-severity-tag severity-${(item.severity || 'warning').toLowerCase()}`;
    }
    if (locationEl) locationEl.innerHTML = `<i data-lucide="map-pin"></i> ${item.location}`;
    if (timeEl) timeEl.innerHTML = `<i data-lucide="clock"></i> ${item.timestamp || 'Updated just now'}`;
    if (actionEl) actionEl.textContent = item.action_advice || '';
    if (sourceEl) sourceEl.textContent = `Source: ${item.source}`;
    if (counterEl) counterEl.textContent = `${activeIndex + 1} / ${filteredList.length}`;

    if (window.lucide) window.lucide.createIcons();
  }

  function nextNews() {
    if (filteredList.length <= 1) return;
    activeIndex = (activeIndex + 1) % filteredList.length;
    renderCurrentNews();
  }

  function prevNews() {
    if (filteredList.length <= 1) return;
    activeIndex = (activeIndex - 1 + filteredList.length) % filteredList.length;
    renderCurrentNews();
  }

  function startRotation() {
    stopRotation();
    rotateInterval = setInterval(nextNews, 8000);
  }

  function stopRotation() {
    if (rotateInterval) {
      clearInterval(rotateInterval);
      rotateInterval = null;
    }
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      stopRotation();
      prevNews();
      startRotation();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      stopRotation();
      nextNews();
      startRotation();
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.category || 'ALL';
      applyCategoryFilter();
      startRotation();
    });
  });

  if (askCopilotBtn) {
    askCopilotBtn.addEventListener('click', () => {
      const currentItem = filteredList[activeIndex];
      const prompt = currentItem ? (currentItem.copilot_prompt || `Tell me about: ${currentItem.headline}`) : 'What is the current disaster situation near Odisha?';
      if (typeof window.askResQChatbot === 'function') {
        window.askResQChatbot(prompt);
      }
    });
  }

  newsSection.addEventListener('mouseenter', stopRotation);
  newsSection.addEventListener('mouseleave', startRotation);

  fetchNews();
  startRotation();
}
