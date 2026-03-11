/**
 * Dashboard: real user metrics (active now, registered, verified, banned),
 * Active Users Over Time and User Growth charts from API. Activity log and CSV export.
 */
(function () {
  'use strict';

  var METRICS_API = '/dashboard/api/metrics';
  var LOGS_API = '/dashboard/api/logs';
  var logsLoading = false;
  var logsError = null;
  var chartActiveOverTime = null;
  var chartUserGrowth = null;

  function setText(sel, text) {
    var el = document.querySelector(sel);
    if (el) el.textContent = text;
  }

  function getRange() {
    var el = document.getElementById('metrics-range');
    var v = el ? el.value : '24h';
    return (v === '7d' || v === '30d' || v === '12m') ? v : '24h';
  }

  function maxVal(arr) {
    if (!arr || arr.length === 0) return 0;
    var m = arr[0];
    for (var i = 1; i < arr.length; i++) if (arr[i] > m) m = arr[i];
    return m;
  }

  function fetchAndDisplayMetrics() {
    var range = getRange();
    var url = METRICS_API + '?range=' + encodeURIComponent(range);
    setText('#metric-active-now', '…');
    setText('#metric-registered', '…');
    setText('#metric-verified', '…');
    setText('#metric-banned', '…');

    fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (res) {
        if (!res.ok) return res.json().then(function (j) { throw new Error(j.error || 'Failed to load metrics'); });
        return res.json();
      })
      .then(function (data) {
        setText('#metric-active-now', String(data.active_now != null ? data.active_now : '—'));
        setText('#metric-registered', String(data.registered_total != null ? data.registered_total : '—'));
        setText('#metric-verified', String(data.verified_total != null ? data.verified_total : '—'));
        setText('#metric-banned', String(data.banned_total != null ? data.banned_total : '—'));

        var labels = data.bucket_labels || [];
        var activeSeries = data.active_users_over_time || [];
        var growthSeries = data.user_growth_over_time || [];

        var activeMax = maxVal(activeSeries);
        var growthMax = maxVal(growthSeries);
        if (growthMax === 0) growthMax = 1;

        if (typeof Chart !== 'undefined') {
          var activeCanvas = document.getElementById('chart-active-over-time');
          if (activeCanvas) {
            if (chartActiveOverTime) chartActiveOverTime.destroy();
            var ctx = activeCanvas.getContext('2d');
            chartActiveOverTime = new Chart(ctx, {
              type: 'line',
              data: {
                labels: labels,
                datasets: [{
                  label: 'Active users',
                  data: activeSeries,
                  borderColor: '#7a5c9e',
                  backgroundColor: 'rgba(122, 92, 158, 0.2)',
                  fill: true,
                  tension: 0.3
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                  x: {
                    grid: { color: 'rgba(42,42,50,0.8)' },
                    ticks: { color: '#9a9692', maxTicksLimit: 12 }
                  },
                  y: {
                    min: 0,
                    max: activeMax > 0 ? Math.ceil(activeMax * 1.1) : 1,
                    grid: { color: 'rgba(42,42,50,0.8)' },
                    ticks: { color: '#9a9692' }
                  }
                }
              }
            });
          }

          var growthCanvas = document.getElementById('chart-user-growth');
          if (growthCanvas) {
            if (chartUserGrowth) chartUserGrowth.destroy();
            var ctx2 = growthCanvas.getContext('2d');
            chartUserGrowth = new Chart(ctx2, {
              type: 'bar',
              data: {
                labels: labels,
                datasets: [{
                  label: 'Cumulative users',
                  data: growthSeries,
                  backgroundColor: '#a07dcc',
                  borderColor: '#7a5c9e',
                  borderWidth: 1
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                  x: {
                    grid: { display: false },
                    ticks: { color: '#9a9692', maxTicksLimit: 12 }
                  },
                  y: {
                    min: 0,
                    max: Math.ceil(growthMax * 1.05) || 1,
                    grid: { color: 'rgba(42,42,50,0.8)' },
                    ticks: { color: '#9a9692' }
                  }
                }
              }
            });
          }
        }
      })
      .catch(function (err) {
        setText('#metric-active-now', '—');
        setText('#metric-registered', '—');
        setText('#metric-verified', '—');
        setText('#metric-banned', '—');
        if (chartActiveOverTime) { chartActiveOverTime.destroy(); chartActiveOverTime = null; }
        if (chartUserGrowth) { chartUserGrowth.destroy(); chartUserGrowth = null; }
        console.error('Metrics load failed:', err);
      });
  }

  function getFilters() {
    var search = (document.getElementById('filter-search') && document.getElementById('filter-search').value) || '';
    var category = (document.getElementById('filter-category') && document.getElementById('filter-category').value) || '';
    var status = (document.getElementById('filter-status') && document.getElementById('filter-status').value) || '';
    var from = (document.getElementById('filter-date-from') && document.getElementById('filter-date-from').value) || '';
    var to = (document.getElementById('filter-date-to') && document.getElementById('filter-date-to').value) || '';
    return { search: search.trim(), category, status, from, to };
  }

  function formatLogDate(isoStr) {
    if (!isoStr) return '';
    try {
      var d = new Date(isoStr);
      return isNaN(d.getTime()) ? isoStr : d.toISOString().slice(0, 10);
    } catch (e) {
      return isoStr;
    }
  }

  function tagClass(s) {
    if (s === 'success') return 'tag-success';
    if (s === 'error') return 'tag-error';
    if (s === 'warning') return 'tag-warning';
    return 'tag-info';
  }

  function renderLogsLoading(tbody, countEl) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="logs-loading">Loading…</td></tr>';
    if (countEl) countEl.textContent = '0 entries';
  }

  function renderLogsError(tbody, countEl, message) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="logs-error">' + escapeHtml(message) + '</td></tr>';
    if (countEl) countEl.textContent = '0 entries';
  }

  function renderLogsEmpty(tbody, countEl) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="logs-empty">No log entries.</td></tr>';
    if (countEl) countEl.textContent = '0 entries';
  }

  function renderLogsRows(items, total, tbody, countEl) {
    if (!tbody) return;
    tbody.innerHTML = '';
    (items || []).forEach(function (r) {
      var tr = document.createElement('tr');
      var tags = (r.tags || []).map(function (t) {
        return '<span class="tag tag-info">' + escapeHtml(t) + '</span>';
      }).join('');
      var dateStr = formatLogDate(r.created_at);
      tr.innerHTML =
        '<td>' + escapeHtml(dateStr) + '</td>' +
        '<td>' + escapeHtml(r.actor_username_snapshot || '—') + '</td>' +
        '<td>' + escapeHtml(r.category) + '</td>' +
        '<td>' + escapeHtml(r.action) + '</td>' +
        '<td><span class="tag ' + tagClass(r.status) + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td>' + tags + '</td>';
      tbody.appendChild(tr);
    });
    if (countEl) countEl.textContent = (total != null ? total : (items || []).length) + ' entries';
  }

  function fetchAndRenderLogs() {
    var tbody = document.getElementById('table-body');
    var countEl = document.getElementById('table-count');
    var f = getFilters();
    var params = new URLSearchParams();
    if (f.search) params.set('q', f.search);
    if (f.category) params.set('category', f.category);
    if (f.status) params.set('status', f.status);
    if (f.from) params.set('date_from', f.from);
    if (f.to) params.set('date_to', f.to);
    params.set('page', '1');
    params.set('limit', '100');
    var url = LOGS_API + (params.toString() ? '?' + params.toString() : '');

    logsLoading = true;
    logsError = null;
    renderLogsLoading(tbody, countEl);

    fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (res) {
        if (!res.ok) {
          if (res.status === 403) return { _error: 'Access denied. Admin only.' };
          return res.json().then(function (j) { return { _error: j.error || 'Failed to load logs' }; }).catch(function () { return { _error: 'Failed to load logs' }; });
        }
        return res.json();
      })
      .then(function (data) {
        logsLoading = false;
        if (data && data._error) {
          logsError = data._error;
          renderLogsError(tbody, countEl, data._error);
          return;
        }
        var items = (data && data.items) || [];
        var total = (data && typeof data.total === 'number') ? data.total : items.length;
        if (items.length === 0 && total === 0) {
          renderLogsEmpty(tbody, countEl);
        } else {
          renderLogsRows(items, total, tbody, countEl);
        }
      })
      .catch(function () {
        logsLoading = false;
        logsError = 'Unable to load logs.';
        renderLogsError(tbody, countEl, logsError);
      });
  }

  function filterAndRender() {
    fetchAndRenderLogs();
  }

  function escapeHtml(s) {
    if (s == null) return '';
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function exportCsv() {
    var f = getFilters();
    var params = new URLSearchParams();
    if (f.search) params.set('q', f.search);
    if (f.category) params.set('category', f.category);
    if (f.status) params.set('status', f.status);
    if (f.from) params.set('date_from', f.from);
    if (f.to) params.set('date_to', f.to);
    params.set('limit', '5000');
    var url = '/dashboard/api/logs/export' + (params.toString() ? '?' + params.toString() : '');
    window.location.href = url;
  }

  function setupDashboardNav() {
    document.querySelectorAll('.dash-nav-trigger[data-nav-trigger]').forEach(function (trigger) {
      var group = trigger.closest('[data-nav-group]');
      if (!group) return;
      trigger.addEventListener('click', function () {
        var expanded = trigger.getAttribute('aria-expanded') !== 'true';
        trigger.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        if (expanded) group.classList.remove('is-closed'); else group.classList.add('is-closed');
      });
    });

    document.querySelectorAll('.dash-nav-item[data-dash-view]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var viewId = btn.getAttribute('data-dash-view');
        if (!viewId) return;
        var view = document.getElementById('view-' + viewId);
        if (!view) return;
        document.querySelectorAll('.dash-view').forEach(function (v) {
          v.classList.remove('is-visible');
          v.setAttribute('hidden', '');
        });
        view.classList.add('is-visible');
        view.removeAttribute('hidden');
        document.querySelectorAll('.dash-nav-item').forEach(function (b) {
          b.classList.remove('is-active');
        });
        btn.classList.add('is-active');
      });
    });
  }

  function loadSiteSettings() {
    fetch('/dashboard/api/site-settings', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function(r) { return r.ok ? r.json() : null; })
      .catch(function() { return null; })
      .then(function(data) {
        if (data) {
          var el = document.getElementById('site-setting-rotation-interval');
          var en = document.getElementById('site-setting-rotation-enabled');
          if (el) el.value = data.slogan_rotation_interval_seconds != null ? data.slogan_rotation_interval_seconds : 60;
          if (en) en.checked = data.slogan_rotation_enabled !== false;
        }
      });
  }

  function saveSiteSettings(e) {
    e.preventDefault();
    var interval = document.getElementById('site-setting-rotation-interval');
    var enabled = document.getElementById('site-setting-rotation-enabled');
    var status = document.getElementById('site-settings-status');
    var payload = {
      slogan_rotation_interval_seconds: parseInt(interval && interval.value, 10) || 60,
      slogan_rotation_enabled: enabled ? enabled.checked : true
    };
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    var csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';
    var headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    fetch('/dashboard/api/site-settings', {
      credentials: 'same-origin',
      method: 'PUT',
      headers: headers,
      body: JSON.stringify(payload)
    })
      .then(function(r) {
        if (status) {
          if (r.ok) { status.textContent = 'Saved.'; status.setAttribute('aria-live', 'polite'); setTimeout(function() { status.textContent = ''; }, 3000); }
          else status.textContent = 'Save failed.';
        }
      })
      .catch(function() { if (status) status.textContent = 'Save failed.'; });
  }

  function bindEvents() {
    var rangeEl = document.getElementById('metrics-range');
    if (rangeEl) rangeEl.addEventListener('change', fetchAndDisplayMetrics);
    var siteForm = document.getElementById('site-settings-form');
    if (siteForm) siteForm.addEventListener('submit', saveSiteSettings);

    var searchEl = document.getElementById('filter-search');
    if (searchEl) searchEl.addEventListener('input', filterAndRender);
    var catEl = document.getElementById('filter-category');
    if (catEl) catEl.addEventListener('change', filterAndRender);
    var statusEl = document.getElementById('filter-status');
    if (statusEl) statusEl.addEventListener('change', filterAndRender);
    var fromEl = document.getElementById('filter-date-from');
    if (fromEl) fromEl.addEventListener('change', filterAndRender);
    var toEl = document.getElementById('filter-date-to');
    if (toEl) toEl.addEventListener('change', filterAndRender);

    var clearEl = document.getElementById('filter-clear');
    if (clearEl) {
      clearEl.addEventListener('click', function () {
        if (document.getElementById('filter-search')) document.getElementById('filter-search').value = '';
        if (document.getElementById('filter-category')) document.getElementById('filter-category').value = '';
        if (document.getElementById('filter-status')) document.getElementById('filter-status').value = '';
        if (document.getElementById('filter-date-from')) document.getElementById('filter-date-from').value = '';
        if (document.getElementById('filter-date-to')) document.getElementById('filter-date-to').value = '';
        filterAndRender();
      });
    }

    var exportBtn = document.getElementById('export-csv');
    if (exportBtn) exportBtn.addEventListener('click', exportCsv);

    var userSettingsForm = document.getElementById('form-user-settings');
    if (userSettingsForm) {
      userSettingsForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var statusEl = document.getElementById('user-settings-status');
        if (statusEl) {
          statusEl.textContent = 'Changes saved.';
          statusEl.setAttribute('aria-live', 'polite');
          setTimeout(function () { statusEl.textContent = ''; }, 3000);
        }
      });
    }
  }

  function init() {
    setupDashboardNav();
    fetchAndDisplayMetrics();
    fetchAndRenderLogs();
    loadSiteSettings();
    bindEvents();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
