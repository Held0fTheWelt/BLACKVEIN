(function () {
  const cfg = window.__FRONTEND_CONFIG__ || {};
  const apiBase = (cfg.apiProxyBase || '') + '/api/v1';
  const listEl = document.getElementById('game-content-list');
  const payloadEl = document.getElementById('experience-payload');
  const formEl = document.getElementById('game-content-form');
  const statusEl = document.getElementById('game-content-status');
  const publishBtn = document.getElementById('game-content-publish');
  const unpublishBtn = document.getElementById('game-content-unpublish');
  const govSubmitBtn = document.getElementById('game-content-gov-submit');
  const govApproveBtn = document.getElementById('game-content-gov-approve');
  const govRejectBtn = document.getElementById('game-content-gov-reject');
  const govRevisionBtn = document.getElementById('game-content-gov-revision');
  const markPublishableBtn = document.getElementById('game-content-mark-publishable');
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
    if (!res.ok) {
      let msg = data.error || data.detail || ('Request failed: ' + res.status);
      if (data.code) {
        msg += ' [' + data.code + (data.content_lifecycle ? '|' + data.content_lifecycle : '') + ']';
      }
      throw new Error(msg);
    }
    return data;
  }

  function canonicalDefaultPayload() {
    return {
      id: 'god_of_carnage_solo',
      slug: 'god-of-carnage',
      title: 'God of Carnage',
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

  function originLabel(item) {
    const p = item.governance_provenance;
    if (!p || typeof p !== 'object') return 'origin:?';
    return 'origin:' + (p.origin_kind || '?');
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
      const lc = item.content_lifecycle || 'draft';
      const pub = item.is_published ? 'live' : 'offline';
      card.innerHTML =
        '<strong>' + item.title + '</strong><span>' + item.template_id + '</span><span>' +
        lc + ' · ' + pub + ' · ' + originLabel(item) + ' · v' + item.version + '</span>';
      card.addEventListener('click', () => loadIntoEditor(item));
      listEl.appendChild(card);
    });
  }

  function loadIntoEditor(item) {
    idEl.value = item.id || '';
    payloadEl.value = JSON.stringify(item.payload || canonicalDefaultPayload(), null, 2);
    const lc = item.content_lifecycle || 'draft';
    const allow = item.publish_allowed ? 'publish_allowed' : 'publish_gated';
    statusEl.textContent =
      'Loaded ' + item.title + ' — lifecycle:' + lc + ' · ' + allow + ' · ' + originLabel(item);
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
      statusEl.textContent = 'Saved draft for ' + data.experience.title + ' (lifecycle:' + (data.experience.content_lifecycle || '') + ')';
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

  function govPost(suffix) {
    if (!idEl.value) {
      statusEl.textContent = 'Save and select an experience first.';
      return Promise.resolve();
    }
    return api('/game/content/experiences/' + idEl.value + suffix, { method: 'POST', body: '{}' });
  }

  if (unpublishBtn) {
    unpublishBtn.addEventListener('click', () => {
      govPost('/unpublish')
        .then((data) => {
          statusEl.textContent = 'Unpublished ' + (data.experience && data.experience.title);
          return refresh();
        })
        .catch((err) => { statusEl.textContent = err.message; });
    });
  }

  if (govSubmitBtn) {
    govSubmitBtn.addEventListener('click', () => {
      govPost('/governance/submit-review')
        .then(() => refresh())
        .then(() => { statusEl.textContent = 'Submitted for review.'; })
        .catch((err) => { statusEl.textContent = err.message; });
    });
  }

  if (govApproveBtn) {
    govApproveBtn.addEventListener('click', () => {
      if (!idEl.value) {
        statusEl.textContent = 'Save and select an experience first.';
        return;
      }
      api('/game/content/experiences/' + idEl.value + '/governance/decision', {
        method: 'POST',
        body: JSON.stringify({ decision: 'approve' }),
      })
        .then(() => refresh())
        .then(() => { statusEl.textContent = 'Editorial: approved.'; })
        .catch((err) => { statusEl.textContent = err.message; });
    });
  }

  if (govRejectBtn) {
    govRejectBtn.addEventListener('click', () => {
      if (!idEl.value) {
        statusEl.textContent = 'Save and select an experience first.';
        return;
      }
      api('/game/content/experiences/' + idEl.value + '/governance/decision', {
        method: 'POST',
        body: JSON.stringify({ decision: 'reject' }),
      })
        .then(() => refresh())
        .then(() => { statusEl.textContent = 'Editorial: rejected.'; })
        .catch((err) => { statusEl.textContent = err.message; });
    });
  }

  if (govRevisionBtn) {
    govRevisionBtn.addEventListener('click', () => {
      if (!idEl.value) {
        statusEl.textContent = 'Save and select an experience first.';
        return;
      }
      api('/game/content/experiences/' + idEl.value + '/governance/decision', {
        method: 'POST',
        body: JSON.stringify({ decision: 'request_revision' }),
      })
        .then(() => refresh())
        .then(() => { statusEl.textContent = 'Editorial: revision requested.'; })
        .catch((err) => { statusEl.textContent = err.message; });
    });
  }

  if (markPublishableBtn) {
    markPublishableBtn.addEventListener('click', () => {
      govPost('/governance/mark-publishable')
        .then(() => refresh())
        .then(() => { statusEl.textContent = 'Marked publishable (moderator readiness step).'; })
        .catch((err) => { statusEl.textContent = err.message; });
    });
  }

  createBtn.addEventListener('click', () => {
    idEl.value = '';
    payloadEl.value = JSON.stringify(canonicalDefaultPayload(), null, 2);
    statusEl.textContent = 'Loaded editor template. Fill roles, rooms, props, actions, and beats before saving.';
  });

  refreshBtn.addEventListener('click', () => refresh().catch((err) => { statusEl.textContent = err.message; }));
  refresh().catch((err) => { statusEl.textContent = err.message; });
})();
