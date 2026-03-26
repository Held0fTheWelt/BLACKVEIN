(function () {
  const cfg = window.__FRONTEND_CONFIG__ || {};
  const apiBase = (cfg.apiProxyBase || '') + '/api/v1';
  const listEl = document.getElementById('game-content-list');
  const payloadEl = document.getElementById('experience-payload');
  const formEl = document.getElementById('game-content-form');
  const statusEl = document.getElementById('game-content-status');
  const publishBtn = document.getElementById('game-content-publish');
  const refreshBtn = document.getElementById('game-content-refresh');
  const createBtn = document.getElementById('game-content-create-default');
  const idEl = document.getElementById('experience-id');

  if (!listEl || !payloadEl || !formEl) return;

  function token() {
    return localStorage.getItem('access_token') || '';
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({ 'Accept': 'application/json' }, opts.headers || {});
    if (opts.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
    if (token()) headers['Authorization'] = 'Bearer ' + token();
    const res = await fetch(apiBase + path, Object.assign({}, opts, { headers }));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.detail || ('Request failed: ' + res.status));
    return data;
  }

  function canonicalDefaultPayload() {
    return {
      id: 'god_of_carnage_solo',
      slug: 'god-of-carnage',
      title: 'God of Carnage — Single Adventure',
      kind: 'solo_story',
      join_policy: 'owner_only',
      summary: 'Authored single-adventure slice for a social confrontation inside a Paris apartment.',
      max_humans: 1,
      min_humans_to_start: 1,
      persistent: false,
      initial_beat_id: 'courtesy',
      roles: [],
      rooms: [],
      props: [],
      actions: [],
      beats: [],
      tags: ['authored', 'single-adventure', 'social-drama'],
      style_profile: 'retro_pulp'
    };
  }

  function renderList(items) {
    listEl.innerHTML = '';
    if (!items.length) {
      listEl.innerHTML = '<p class="panel-note">No authored experiences found yet.</p>';
      return;
    }
    items.forEach((item) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'list-card';
      card.innerHTML = '<strong>' + item.title + '</strong><span>' + item.template_id + '</span><span>' + (item.is_published ? 'Published' : 'Draft') + ' · v' + item.version + '</span>';
      card.addEventListener('click', () => loadIntoEditor(item));
      listEl.appendChild(card);
    });
  }

  function loadIntoEditor(item) {
    idEl.value = item.id || '';
    payloadEl.value = JSON.stringify(item.payload || canonicalDefaultPayload(), null, 2);
    statusEl.textContent = 'Loaded ' + item.title + ' (' + (item.is_published ? 'published' : 'draft') + ')';
  }

  async function refresh() {
    const data = await api('/game/content/experiences');
    renderList(data.experiences || []);
    if (!idEl.value && data.experiences && data.experiences[0]) {
      loadIntoEditor(data.experiences[0]);
    }
  }

  formEl.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const payload = JSON.parse(payloadEl.value || '{}');
      const body = JSON.stringify({ payload });
      let data;
      if (idEl.value) {
        data = await api('/game/content/experiences/' + idEl.value, { method: 'PATCH', body });
      } else {
        data = await api('/game/content/experiences', { method: 'POST', body });
      }
      statusEl.textContent = 'Saved draft for ' + data.experience.title;
      idEl.value = data.experience.id;
      await refresh();
    } catch (err) {
      statusEl.textContent = err.message;
    }
  });

  publishBtn.addEventListener('click', async () => {
    if (!idEl.value) {
      statusEl.textContent = 'Save the draft first.';
      return;
    }
    try {
      const data = await api('/game/content/experiences/' + idEl.value + '/publish', { method: 'POST' });
      statusEl.textContent = 'Published ' + data.experience.title;
      await refresh();
    } catch (err) {
      statusEl.textContent = err.message;
    }
  });

  createBtn.addEventListener('click', () => {
    idEl.value = '';
    payloadEl.value = JSON.stringify(canonicalDefaultPayload(), null, 2);
    statusEl.textContent = 'Loaded editor template. Fill roles, rooms, props, actions, and beats before saving.';
  });

  refreshBtn.addEventListener('click', () => refresh().catch((err) => { statusEl.textContent = err.message; }));
  refresh().catch((err) => { statusEl.textContent = err.message; });
})();
