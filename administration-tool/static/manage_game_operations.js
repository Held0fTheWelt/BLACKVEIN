(function () {
  const cfg = window.__FRONTEND_CONFIG__ || {};
  const apiBase = (cfg.apiProxyBase || '') + '/api/v1';
  const runsEl = document.getElementById('game-ops-runs');
  const detailEl = document.getElementById('game-ops-detail');
  const transcriptEl = document.getElementById('game-ops-transcript');
  const refreshBtn = document.getElementById('game-ops-refresh');
  const terminateBtn = document.getElementById('game-ops-terminate');
  let selectedRunId = null;

  if (!runsEl || !detailEl || !transcriptEl) return;

  function token() { return localStorage.getItem('access_token') || ''; }
  async function api(path, opts = {}) {
    const headers = Object.assign({ 'Accept': 'application/json' }, opts.headers || {});
    if (token()) headers['Authorization'] = 'Bearer ' + token();
    const res = await fetch(apiBase + path, Object.assign({}, opts, { headers }));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.detail || ('Request failed: ' + res.status));
    return data;
  }

  async function loadRuns() {
    const data = await api('/game/ops/runs');
    const runs = data.runs || [];
    runsEl.innerHTML = '';
    if (!runs.length) {
      runsEl.innerHTML = '<p class="panel-note">No active runs reported.</p>';
      detailEl.textContent = '';
      transcriptEl.textContent = '';
      selectedRunId = null;
      return;
    }
    runs.forEach((run) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'list-card';
      btn.textContent = run.template_title + ' · ' + run.id + ' · ' + run.status;
      btn.addEventListener('click', () => inspectRun(run.id));
      runsEl.appendChild(btn);
    });
    if (!selectedRunId) await inspectRun(runs[0].id);
  }

  async function inspectRun(runId) {
    selectedRunId = runId;
    const detail = await api('/game/ops/runs/' + runId);
    const transcript = await api('/game/ops/runs/' + runId + '/transcript');
    detailEl.textContent = JSON.stringify(detail, null, 2);
    transcriptEl.textContent = JSON.stringify(transcript, null, 2);
  }

  terminateBtn.addEventListener('click', async () => {
    if (!selectedRunId) return;
    try {
      await api('/game/ops/runs/' + selectedRunId + '/terminate', { method: 'POST' });
      selectedRunId = null;
      await loadRuns();
    } catch (err) {
      detailEl.textContent = err.message;
    }
  });

  refreshBtn.addEventListener('click', () => loadRuns().catch((err) => { detailEl.textContent = err.message; }));
  loadRuns().catch((err) => { detailEl.textContent = err.message; });
})();
