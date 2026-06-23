/* Memory Hunt — prototype game logic (text-label mock, no images yet) */

const els = {};
let game = null;          // loaded game.json
let stationIndex = {};    // stationId -> { pairId, label }
let state = null;         // persisted progress
let homeTimerInterval = null;
let scanStream = null;
let scanLoopHandle = null;

function $(id) { return document.getElementById(id); }

function cacheEls() {
  [
    'screen-home','screen-scan','screen-reveal','screen-end',
    'game-title','stat-pairs','stat-time','progress-fill','banner-area',
    'btn-scan','btn-reset','manual-station','btn-manual-go',
    'scanner-video','scan-status','btn-cancel-scan',
    'reveal-card','reveal-slot-label','hide-timer','reveal-photo',
    'reveal-label','reveal-result','btn-reveal-continue',
    'final-time','btn-play-again'
  ].forEach(id => els[id] = $(id));
}

function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  $('screen-' + name).classList.add('active');
}

/* ---------------- persistence ----------------
   Falls back to an in-memory store if localStorage is blocked (some
   private-browsing / restricted preview contexts throw on access). */

let memoryStore = {};
let storageOk = true;
try {
  localStorage.setItem('__mh_test__', '1');
  localStorage.removeItem('__mh_test__');
} catch (e) {
  storageOk = false;
}
function storageGet(k) {
  if (storageOk) { try { return localStorage.getItem(k); } catch (e) {} }
  return memoryStore[k] !== undefined ? memoryStore[k] : null;
}
function storageSet(k, v) {
  if (storageOk) { try { localStorage.setItem(k, v); return; } catch (e) {} }
  memoryStore[k] = v;
}

function stateKey() { return 'mh_state_' + game.gameId; }

function freshState() {
  return { startTime: null, endTime: null, matchedPairIds: [], pending: null };
}

function loadState() {
  const raw = storageGet(stateKey());
  if (raw) { try { return JSON.parse(raw); } catch (e) {} }
  return freshState();
}

function saveState() {
  storageSet(stateKey(), JSON.stringify(state));
}

/* ---------------- game load ----------------
   If an EMBEDDED_GAME object was defined before this script runs (used by
   the single-file standalone build), it's used directly with no network
   fetch needed. Otherwise the game config is fetched from game.json. */

async function loadGame() {
  if (typeof EMBEDDED_GAME !== 'undefined') {
    game = EMBEDDED_GAME;
  } else {
    const res = await fetch('game.json', { cache: 'no-store' });
    game = await res.json();
  }
  stationIndex = {};
  game.pairs.forEach(p => {
    p.stations.forEach(stId => {
      stationIndex[stId] = { pairId: p.pairId, label: p.label, photo: p.photo || null };
    });
  });
  state = loadState();
  els['game-title'].textContent = game.title || 'Memory Hunt';
  renderHome();
  maybeHandleUrlScan();
}

/* ---------------- home rendering ---------------- */

function totalPairs() { return game.pairs.length; }

function fmtTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = String(Math.floor(totalSec / 60)).padStart(2, '0');
  const s = String(totalSec % 60).padStart(2, '0');
  return m + ':' + s;
}

function currentElapsedMs() {
  if (!state.startTime) return 0;
  const end = state.endTime || Date.now();
  return end - state.startTime;
}

function renderHome() {
  const matched = state.matchedPairIds.length;
  const total = totalPairs();
  els['stat-pairs'].textContent = matched + '/' + total;
  els['stat-time'].textContent = fmtTime(currentElapsedMs());
  els['progress-fill'].style.width = (total ? (matched / total) * 100 : 0) + '%';

  els['banner-area'].innerHTML = '';
  if (state.pending) {
    const b = document.createElement('div');
    b.className = 'banner';
    b.textContent = 'Picture 1 captured: "' + state.pending.label + '" — find its match!';
    els['banner-area'].appendChild(b);
  }
  els['btn-reset'].classList.toggle('hidden', matched === 0 && !state.startTime);

  clearInterval(homeTimerInterval);
  if (state.startTime && !state.endTime) {
    homeTimerInterval = setInterval(() => {
      els['stat-time'].textContent = fmtTime(currentElapsedMs());
    }, 1000);
  }

  if (matched === total && total > 0) {
    showEnd();
  } else {
    showScreen('home');
  }
}

function showEnd() {
  clearInterval(homeTimerInterval);
  els['final-time'].textContent = fmtTime(currentElapsedMs());
  showScreen('end');
}

/* ---------------- scan handling (shared by camera + manual + URL) ---------------- */

function handleScanResult(raw) {
  const stationId = extractStationId(raw);
  if (!stationId || !stationIndex[stationId]) {
    alert('That code is not part of this game (or could not be read). Try again.');
    showScreen('home');
    return;
  }
  goToReveal(stationId);
}

function extractStationId(raw) {
  raw = (raw || '').trim();
  if (!raw) return null;
  // Try as a URL first (what a real printed QR code will encode)
  try {
    const url = new URL(raw, window.location.href);
    const st = url.searchParams.get('station');
    if (st) return st.toUpperCase();
  } catch (e) { /* not a URL, fall through */ }
  // Otherwise treat the raw text as a bare station id (manual entry / testing)
  return raw.toUpperCase();
}

function maybeHandleUrlScan() {
  const params = new URLSearchParams(window.location.search);
  const station = params.get('station');
  if (station) {
    // clean the URL so refresh/back doesn't replay the scan
    const clean = window.location.pathname;
    history.replaceState({}, '', clean);
    handleScanResult('?station=' + station);
  }
}

/* ---------------- reveal flow ----------------
   The picture/label shows IMMEDIATELY on scan, then stays on screen for
   `revealSeconds` (default 10s) before auto-hiding (returning home). The
   "Continue" button lets the player dismiss it early instead of waiting. */

let hideTimerInterval = null;

function goToReveal(stationId) {
  const outcome = processStation(stationId);

  showScreen('reveal');
  els['reveal-label'].textContent = outcome.label;

  if (outcome.photo) {
    els['reveal-photo'].src = outcome.photo;
    els['reveal-photo'].alt = outcome.label;
    els['reveal-photo'].classList.remove('hidden');
  } else {
    els['reveal-photo'].removeAttribute('src');
    els['reveal-photo'].classList.add('hidden');
  }

  const resultEl = els['reveal-result'];
  resultEl.className = 'reveal-result';

  if (outcome.type === 'already') {
    els['reveal-slot-label'].textContent = 'Already collected';
    resultEl.textContent = "You've already found this pair!";
    resultEl.classList.add('result-already');
  } else if (outcome.type === 'pending') {
    els['reveal-slot-label'].textContent = 'Picture 1';
    resultEl.textContent = 'Now go find its match…';
    resultEl.classList.add('result-pending');
  } else if (outcome.type === 'match') {
    els['reveal-slot-label'].textContent = 'Picture 2';
    resultEl.textContent = '🎉 Match found!';
    resultEl.classList.add('result-match');
  } else if (outcome.type === 'nomatch') {
    els['reveal-slot-label'].textContent = 'Picture 2';
    resultEl.textContent = 'No match (picture 1 was "' + outcome.prevLabel + '"). Try again!';
    resultEl.classList.add('result-nomatch');
  }

  let remaining = (game.revealSeconds || 10);
  els['hide-timer'].textContent = 'Hides in ' + remaining + 's';

  clearInterval(hideTimerInterval);
  hideTimerInterval = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(hideTimerInterval);
      renderHome();
    } else {
      els['hide-timer'].textContent = 'Hides in ' + remaining + 's';
    }
  }, 1000);
}

function processStation(stationId) {
  const station = stationIndex[stationId];

  if (!state.startTime) {
    state.startTime = Date.now();
  }

  if (state.matchedPairIds.includes(station.pairId)) {
    saveState();
    return { type: 'already', label: station.label, photo: station.photo };
  }

  if (!state.pending) {
    state.pending = { stationId, pairId: station.pairId, label: station.label };
    saveState();
    return { type: 'pending', label: station.label, photo: station.photo };
  }

  if (state.pending.stationId === stationId) {
    // same QR scanned twice in a row — just re-show, slot unchanged
    return { type: 'pending', label: station.label, photo: station.photo };
  }

  if (state.pending.pairId === station.pairId) {
    state.matchedPairIds.push(station.pairId);
    state.pending = null;
    if (state.matchedPairIds.length === totalPairs()) {
      state.endTime = Date.now();
    }
    saveState();
    return { type: 'match', label: station.label, photo: station.photo };
  }

  const prevLabel = state.pending.label;
  state.pending = null;
  saveState();
  return { type: 'nomatch', label: station.label, prevLabel, photo: station.photo };
}

/* ---------------- camera scanning ---------------- */

async function startScanner() {
  showScreen('scan');
  els['scan-status'].textContent = 'Looking for a code…';

  if (!('BarcodeDetector' in window)) {
    els['scan-status'].textContent =
      'Your browser camera scanner isn’t supported here. Use the "type a station code" box on the home screen instead.';
    return;
  }

  if (!window.isSecureContext) {
    els['scan-status'].textContent =
      'Camera access needs a secure (https) page or "localhost" — it won’t work from a plain local file. ' +
      'Use the manual code box, or deploy this as a real web page to test the camera.';
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    els['scan-status'].textContent =
      'This browser doesn’t expose camera access here. Use the manual code box instead.';
    return;
  }

  try {
    scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
  } catch (e) {
    els['scan-status'].textContent =
      'Could not access the camera (' + (e && e.message ? e.message : e) + '). Use the manual code box instead.';
    return;
  }

  els['scanner-video'].srcObject = scanStream;
  await els['scanner-video'].play();

  const detector = new BarcodeDetector({ formats: ['qr_code'] });
  let stopped = false;

  async function tick() {
    if (stopped) return;
    try {
      const codes = await detector.detect(els['scanner-video']);
      if (codes.length > 0) {
        stopped = true;
        stopScanner();
        handleScanResult(codes[0].rawValue);
        return;
      }
    } catch (e) { /* detection hiccup, just retry */ }
    scanLoopHandle = setTimeout(tick, 300); // throttle to save battery/CPU
  }
  tick();
}

function stopScanner() {
  clearTimeout(scanLoopHandle);
  if (scanStream) {
    scanStream.getTracks().forEach(t => t.stop());
    scanStream = null;
  }
}

/* ---------------- wiring ---------------- */

function init() {
  cacheEls();

  els['btn-scan'].addEventListener('click', startScanner);
  els['btn-cancel-scan'].addEventListener('click', () => {
    stopScanner();
    showScreen('home');
  });
  els['btn-manual-go'].addEventListener('click', () => {
    const v = els['manual-station'].value;
    els['manual-station'].value = '';
    if (v.trim()) handleScanResult(v);
  });
  els['manual-station'].addEventListener('keydown', (e) => {
    if (e.key === 'Enter') els['btn-manual-go'].click();
  });
  els['btn-reveal-continue'].addEventListener('click', () => {
    clearInterval(hideTimerInterval);
    renderHome();
  });
  els['btn-play-again'].addEventListener('click', () => {
    state = freshState();
    saveState();
    renderHome();
  });
  els['btn-reset'].addEventListener('click', () => {
    if (confirm('Reset progress and timer for this game?')) {
      state = freshState();
      saveState();
      renderHome();
    }
  });

  loadGame();

  if (typeof EMBEDDED_GAME === 'undefined' && 'serviceWorker' in navigator) {
    try {
      navigator.serviceWorker.register('sw.js').catch(() => {/* offline support best-effort */});
    } catch (e) { /* some restricted contexts throw synchronously instead of rejecting */ }
  }
}

document.addEventListener('DOMContentLoaded', init);
