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
  const templateSelect = document.getElementById('game-content-published-template');

  if (!listEl || !payloadEl || !formEl) return;

  function operatorDefaultRuntimeTemplateId() {
    let v = String(cfg.defaultRuntimeTemplateId || '').trim();
    if (v) return v;
    if (typeof document !== 'undefined' && document.body && document.body.dataset) {
      v = String(document.body.dataset.defaultTemplateId || '').trim();
    }
    return v;
  }

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

  function clonePayload(obj) {
    return JSON.parse(JSON.stringify(obj || {}));
  }

  function populatePublishedSelect(items) {
    if (!templateSelect) return;
    templateSelect.innerHTML = '';
    const opt0 = document.createElement('option');
    opt0.value = '';
    opt0.textContent = items.length
      ? '— choose published template —'
      : 'No published experiences (publish on backend first)';
    templateSelect.appendChild(opt0);
    items.forEach((ex) => {
      const tid = String(ex.template_id || '').trim();
      if (!tid) return;
      const o = document.createElement('option');
      o.value = tid;
      o.textContent = (ex.title || '') + ' (' + tid + ')';
      templateSelect.appendChild(o);
    });
    const want = operatorDefaultRuntimeTemplateId();
    if (want) {
      for (let i = 0; i < templateSelect.options.length; i++) {
        if (templateSelect.options[i].value === want) {
          templateSelect.selectedIndex = i;
          break;
        }
      }
    }
  }

  function pickPublishedExperience(items) {
    const sel = templateSelect && templateSelect.value ? String(templateSelect.value).trim() : '';
    if (sel) {
      const hit = items.find((x) => String(x.template_id || '').trim() === sel);
      if (hit) return hit;
    }
    const want = operatorDefaultRuntimeTemplateId();
    if (want) {
      const byDefault = items.find((x) => String(x.template_id || '').trim() === want);
      if (byDefault) return byDefault;
    }
    return items[0] || null;
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
    const base = item.payload ? clonePayload(item.payload) : {};
    payloadEl.value = JSON.stringify(base, null, 2);
    const lc = item.content_lifecycle || 'draft';
    const allow = item.publish_allowed ? 'publish_allowed' : 'publish_gated';
    statusEl.textContent =
      'Loaded ' + item.title + ' — lifecycle:' + lc + ' · ' + allow + ' · ' + originLabel(item);
  }

  async function refresh() {
    const data = await api('/game/content/experiences');
    let pubItems = [];
    try {
      const pubData = await api('/game/content/experiences?status=published');
      pubItems = pubData.experiences || [];
    } catch (_e) {
      pubItems = [];
    }
    populatePublishedSelect(pubItems);
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

  async function applyPublishedStarter() {
    const pubData = await api('/game/content/experiences?status=published');
    const items = pubData.experiences || [];
    populatePublishedSelect(items);
    const picked = pickPublishedExperience(items);
    if (!picked || !picked.payload) {
      statusEl.textContent =
        'No published experience to use as a starter. Publish one on the backend, then refresh.';
      return;
    }
    idEl.value = '';
    payloadEl.value = JSON.stringify(clonePayload(picked.payload), null, 2);
    statusEl.textContent =
      'Loaded new draft from published template "' + (picked.template_id || '') + '". Edit JSON, then save.';
  }

  createBtn.addEventListener('click', () => {
    applyPublishedStarter().catch((err) => { statusEl.textContent = err.message; });
  });

  if (templateSelect) {
    templateSelect.addEventListener('change', () => {
      const v = String(templateSelect.value || '').trim();
      if (!v) return;
      api('/game/content/experiences?status=published')
        .then((pubData) => {
          const items = pubData.experiences || [];
          const picked = items.find((x) => String(x.template_id || '').trim() === v);
          if (!picked || !picked.payload) {
            statusEl.textContent = 'Selected template not found in published list; refresh.';
            return;
          }
          idEl.value = '';
          payloadEl.value = JSON.stringify(clonePayload(picked.payload), null, 2);
          statusEl.textContent = 'Starter from published "' + v + '" (not saved until you submit Save draft).';
        })
        .catch((err) => { statusEl.textContent = err.message; });
    });
  }

  refreshBtn.addEventListener('click', () => refresh().catch((err) => { statusEl.textContent = err.message; }));
  refresh().catch((err) => { statusEl.textContent = err.message; });
})();
