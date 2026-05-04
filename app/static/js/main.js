/**
 * MCM Engine — Main JS
 * Funzioni globali condivise da tutte le pagine
 */

// ─── Sidebar toggle ────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  sidebar.classList.toggle('collapsed');
  // Reinizializza icone Lucide dopo transizione (per icone dinamiche)
  setTimeout(() => { if (window.lucide) lucide.createIcons(); }, 300);
}

// ─── Tab system ────────────────────────────────────────────
function initTabs(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const buttons = container.querySelectorAll('.tab-btn');
  const panels  = container.querySelectorAll('.tab-panel');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;

      buttons.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.add('hidden'));

      btn.classList.add('active');
      const panel = document.getElementById('tab-' + target);
      if (panel) panel.classList.remove('hidden');
    });
  });

  // Attiva primo tab di default
  if (buttons.length > 0) buttons[0].click();
}

// ─── Loading state ─────────────────────────────────────────
function showLoading(elementId) {
  const el = document.getElementById(elementId);
  if (el) el.innerHTML = '<div class="flex justify-center py-12"><div class="spinner"></div></div>';
}

function hideLoading(elementId) {
  const el = document.getElementById(elementId);
  if (el) el.innerHTML = '';
}

// ─── Fetch API con gestione errori ─────────────────────────
async function fetchJSON(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('[MCM] Fetch error:', url, err);
    return null;
  }
}

// ─── Render Plotly da JSON ──────────────────────────────────
function renderPlotly(divId, plotlyJson) {
  if (!plotlyJson || !window.Plotly) return;
  const { data, layout } = plotlyJson;
  Plotly.newPlot(divId, data, {
    ...layout,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter, sans-serif', size: 12 },
    margin: { t: 30, r: 20, b: 60, l: 60 },
  }, { responsive: true, displayModeBar: false });
}
