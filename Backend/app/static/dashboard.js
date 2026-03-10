/**
 * Dashboard: metrics, charts, threshold alerts, activity table, CSV export.
 */
(function () {
  'use strict';

  var DEMO_METRICS = { revenue: 52340, users: 1847, sessions: 4210, conversion: 4.2 };

  var DEMO_ROWS = [
    { date: '2025-02-01', user: 'alice', category: 'auth', action: 'Login', status: 'success', tags: ['web'] },
    { date: '2025-02-02', user: 'bob', category: 'api', action: 'API Call', status: 'success', tags: ['v1'] },
    { date: '2025-02-03', user: 'carol', category: 'admin', action: 'Admin Action', status: 'warning', tags: ['audit'] },
    { date: '2025-02-04', user: 'alice', category: 'auth', action: 'Password Reset', status: 'success', tags: ['email'] },
    { date: '2025-02-05', user: 'bob', category: 'api', action: 'Token Refresh', status: 'success', tags: ['jwt'] },
    { date: '2025-02-06', user: 'dave', category: 'auth', action: 'Register', status: 'success', tags: ['web'] },
    { date: '2025-02-07', user: 'alice', category: 'api', action: 'API Call', status: 'error', tags: ['v1', 'timeout'] },
    { date: '2025-02-08', user: 'bob', category: 'auth', action: '2FA Check', status: 'success', tags: ['mfa'] },
    { date: '2025-02-09', user: 'carol', category: 'admin', action: 'Export', status: 'success', tags: ['csv'] },
    { date: '2025-02-10', user: 'eve', category: 'api', action: 'Rate Limited', status: 'warning', tags: ['429'] },
    { date: '2025-02-11', user: 'alice', category: 'auth', action: 'Logout', status: 'success', tags: ['web'] },
    { date: '2025-02-12', user: 'bob', category: 'api', action: 'API Call', status: 'success', tags: ['v1'] },
    { date: '2025-02-13', user: 'dave', category: 'auth', action: 'Login', status: 'success', tags: ['web'] },
    { date: '2025-02-14', user: 'carol', category: 'admin', action: 'Admin Action', status: 'success', tags: ['audit'] },
    { date: '2025-02-15', user: 'alice', category: 'auth', action: 'Token Refresh', status: 'success', tags: ['session'] },
    { date: '2025-02-16', user: 'eve', category: 'api', action: 'API Call', status: 'error', tags: ['v1'] },
    { date: '2025-02-17', user: 'bob', category: 'auth', action: 'Password Reset', status: 'success', tags: ['email'] },
    { date: '2025-02-18', user: 'alice', category: 'api', action: 'API Call', status: 'success', tags: ['v1'] },
    { date: '2025-02-19', user: 'dave', category: 'admin', action: 'Export', status: 'warning', tags: ['csv'] },
    { date: '2025-02-20', user: 'carol', category: 'auth', action: '2FA Check', status: 'success', tags: ['mfa'] },
    { date: '2025-03-01', user: 'alice', category: 'api', action: 'API Call', status: 'success', tags: ['v1'] },
    { date: '2025-03-02', user: 'bob', category: 'auth', action: 'Login', status: 'success', tags: ['web'] },
    { date: '2025-03-03', user: 'eve', category: 'api', action: 'Rate Limited', status: 'error', tags: ['429'] },
    { date: '2025-03-04', user: 'carol', category: 'admin', action: 'Admin Action', status: 'success', tags: ['audit'] },
    { date: '2025-03-05', user: 'alice', category: 'auth', action: 'Logout', status: 'success', tags: ['web'] },
    { date: '2025-03-06', user: 'dave', category: 'api', action: 'Token Refresh', status: 'success', tags: ['jwt'] },
    { date: '2025-03-07', user: 'bob', category: 'auth', action: 'Register', status: 'success', tags: ['web'] },
    { date: '2025-03-08', user: 'alice', category: 'api', action: 'API Call', status: 'success', tags: ['v1'] },
    { date: '2025-03-09', user: 'carol', category: 'admin', action: 'Export', status: 'success', tags: ['csv'] },
    { date: '2025-03-10', user: 'eve', category: 'auth', action: 'Login', status: 'warning', tags: ['web'] }
  ];

  var STORAGE_KEY = 'wos-dashboard-thresholds';
  var chartRevenue = null;
  var chartUsers = null;

  function loadThresholds() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var o = JSON.parse(raw);
        setEl('#thresh-revenue', o.revenue);
        setEl('#thresh-users', o.users);
        setEl('#thresh-sessions', o.sessions);
        setEl('#thresh-conversion', o.conversion);
      }
    } catch (e) {}
  }

  function saveThresholds() {
    try {
      var o = {
        revenue: numEl('#thresh-revenue', 40000),
        users: numEl('#thresh-users', 1200),
        sessions: numEl('#thresh-sessions', 3000),
        conversion: numEl('#thresh-conversion', 3)
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(o));
    } catch (e) {}
  }

  function numEl(sel, def) {
    var el = document.querySelector(sel);
    if (!el) return def;
    var n = parseFloat(el.value, 10);
    return isNaN(n) ? def : n;
  }

  function setEl(sel, val) {
    var el = document.querySelector(sel);
    if (el) el.value = String(val);
  }

  function displayMetrics() {
    setText('#metric-revenue', '$' + String(DEMO_METRICS.revenue));
    setText('#metric-users', String(DEMO_METRICS.users));
    setText('#metric-sessions', String(DEMO_METRICS.sessions));
    setText('#metric-conversion', DEMO_METRICS.conversion + '%');
  }

  function setText(sel, text) {
    var el = document.querySelector(sel);
    if (el) el.textContent = text;
  }

  function initCharts() {
    if (typeof Chart === 'undefined') return;

    var revenueCanvas = document.getElementById('chart-revenue');
    if (revenueCanvas) {
      var ctx = revenueCanvas.getContext('2d');
      var months = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
      var values = [32, 38, 41, 44, 46, 48, 50, 49, 51, 50, 52, 52];
      chartRevenue = new Chart(ctx, {
        type: 'line',
        data: {
          labels: months,
          datasets: [{
            label: 'Revenue',
            data: values,
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
              ticks: { color: '#9a9692' }
            },
            y: {
              grid: { color: 'rgba(42,42,50,0.8)' },
              ticks: { color: '#9a9692' }
            }
          }
        }
      });
    }

    var usersCanvas = document.getElementById('chart-users');
    if (usersCanvas) {
      var ctx2 = usersCanvas.getContext('2d');
      var months2 = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
      var values2 = [1200, 1280, 1350, 1420, 1520, 1580, 1650, 1720, 1780, 1820, 1840, 1847];
      chartUsers = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: months2,
          datasets: [{
            label: 'Users',
            data: values2,
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
              ticks: { color: '#9a9692' }
            },
            y: {
              grid: { color: 'rgba(42,42,50,0.8)' },
              ticks: { color: '#9a9692' }
            }
          }
        }
      });
    }
  }

  function checkThresholds() {
    var rev = numEl('#thresh-revenue', 40000);
    var users = numEl('#thresh-users', 1200);
    var sess = numEl('#thresh-sessions', 3000);
    var conv = numEl('#thresh-conversion', 3);

    var breach = 0;
    setCardBreach('[data-metric="revenue"]', DEMO_METRICS.revenue < rev);
    if (DEMO_METRICS.revenue < rev) breach++;
    setCardBreach('[data-metric="users"]', DEMO_METRICS.users < users);
    if (DEMO_METRICS.users < users) breach++;
    setCardBreach('[data-metric="sessions"]', DEMO_METRICS.sessions < sess);
    if (DEMO_METRICS.sessions < sess) breach++;
    setCardBreach('[data-metric="conversion"]', DEMO_METRICS.conversion < conv);
    if (DEMO_METRICS.conversion < conv) breach++;

    var badge = document.getElementById('notif-badge');
    if (badge) {
      badge.textContent = String(breach);
      if (breach > 0) badge.classList.remove('hidden');
      else badge.classList.add('hidden');
    }
  }

  function setCardBreach(sel, on) {
    var card = document.querySelector('.metric-card' + sel);
    if (card) {
      if (on) card.classList.add('alert-breach');
      else card.classList.remove('alert-breach');
    }
  }

  function getFilters() {
    var search = (document.getElementById('filter-search') && document.getElementById('filter-search').value) || '';
    var category = (document.getElementById('filter-category') && document.getElementById('filter-category').value) || '';
    var status = (document.getElementById('filter-status') && document.getElementById('filter-status').value) || '';
    var from = (document.getElementById('filter-date-from') && document.getElementById('filter-date-from').value) || '';
    var to = (document.getElementById('filter-date-to') && document.getElementById('filter-date-to').value) || '';
    return { search: search.toLowerCase(), category, status, from, to };
  }

  function filterRows() {
    var f = getFilters();
    return DEMO_ROWS.filter(function (r) {
      if (f.category && r.category !== f.category) return false;
      if (f.status && r.status !== f.status) return false;
      if (f.from && r.date < f.from) return false;
      if (f.to && r.date > f.to) return false;
      if (f.search) {
        var text = (r.user + ' ' + r.action + ' ' + (r.tags || []).join(' ')).toLowerCase();
        if (text.indexOf(f.search) === -1) return false;
      }
      return true;
    });
  }

  function tagClass(s) {
    if (s === 'success') return 'tag-success';
    if (s === 'error') return 'tag-error';
    if (s === 'warning') return 'tag-warning';
    return 'tag-info';
  }

  function filterAndRender() {
    var rows = filterRows();
    var tbody = document.getElementById('table-body');
    var countEl = document.getElementById('table-count');
    if (!tbody) return;

    tbody.innerHTML = '';
    rows.forEach(function (r) {
      var tr = document.createElement('tr');
      var tags = (r.tags || []).map(function (t) {
        return '<span class="tag tag-info">' + escapeHtml(t) + '</span>';
      }).join('');
      tr.innerHTML =
        '<td>' + escapeHtml(r.date) + '</td>' +
        '<td>' + escapeHtml(r.user) + '</td>' +
        '<td>' + escapeHtml(r.category) + '</td>' +
        '<td>' + escapeHtml(r.action) + '</td>' +
        '<td><span class="tag ' + tagClass(r.status) + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td>' + tags + '</td>';
      tbody.appendChild(tr);
    });
    if (countEl) countEl.textContent = rows.length + ' entries';
  }

  function escapeHtml(s) {
    if (s == null) return '';
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function exportCsv() {
    var rows = filterRows();
    var header = 'Date,User,Category,Action,Status,Tags\n';
    var body = rows.map(function (r) {
      return [r.date, r.user, r.category, r.action, r.status, (r.tags || []).join(';')].map(csvEscape).join(',');
    }).join('\n');
    var csv = header + body;
    var blob = new Blob([csv], { type: 'text/csv' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'wos-activity-' + new Date().toISOString().slice(0, 10) + '.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  function csvEscape(s) {
    if (s == null) return '';
    s = String(s);
    if (/[,"\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
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

  function bindEvents() {
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

    var configToggle = document.getElementById('config-panel-toggle');
    var configPanel = document.getElementById('config-panel');
    if (configToggle && configPanel) {
      configToggle.addEventListener('click', function () {
        configPanel.classList.toggle('hidden');
      });
    }

    var configSave = document.getElementById('config-save');
    if (configSave) {
      configSave.addEventListener('click', function () {
        saveThresholds();
        checkThresholds();
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

    var bell = document.getElementById('notif-bell');
    if (bell) {
      bell.addEventListener('click', function () {
        var badge = document.getElementById('notif-badge');
        var n = badge && !badge.classList.contains('hidden') ? badge.textContent : '0';
        var msg = n === '0' ? 'No threshold alerts.' : n + ' metric(s) below threshold.';
        bell.setAttribute('title', msg);
        if (bell.getAttribute('aria-label')) bell.setAttribute('aria-label', 'Threshold alerts: ' + msg);
        var live = document.getElementById('notif-live');
        if (live) live.textContent = msg;
        else if (typeof document.createElement('div').setAttribute === 'function') {
          var el = document.createElement('div');
          el.id = 'notif-live';
          el.setAttribute('aria-live', 'polite');
          el.className = 'sr-only';
          el.textContent = msg;
          bell.appendChild(el);
          setTimeout(function () { el.remove(); }, 2000);
        }
      });
    }
  }

  function init() {
    setupDashboardNav();
    loadThresholds();
    displayMetrics();
    initCharts();
    checkThresholds();
    filterAndRender();
    bindEvents();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
