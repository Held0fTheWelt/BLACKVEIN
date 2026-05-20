/**
 * System diagnosis: GET /api/v1/admin/system-diagnosis via same-origin proxy.
 */
(function () {
  var REFRESH_MS = 15000;

  function diagnosisPayload(res) {
    if (res && res.data !== undefined && Object.prototype.hasOwnProperty.call(res, "ok")) {
      return res.data || {};
    }
    return res || {};
  }

  function statusBadgeClass(status) {
    if (status === "fail") return "manage-dx-badge manage-dx-badge--fail";
    if (status === "initialized") return "manage-dx-badge manage-dx-badge--init";
    return "manage-dx-badge manage-dx-badge--ok";
  }

  function railBadgeClass(status) {
    if (status === "fail") return "mui-rail-badge--fail";
    if (status === "initialized") return "mui-rail-badge--warn";
    return "mui-rail-badge--ok";
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function syncRailBadges(data) {
    var overall = data.overall_status || "initialized";
    var checksRail = document.querySelector('.mui-rail-btn[data-deck-target="checks"] .mui-rail-badge');
    if (checksRail) {
      checksRail.className = "mui-rail-badge " + railBadgeClass(overall);
    }
    var metaRail = document.querySelector('.mui-rail-btn[data-deck-target="meta"] .mui-rail-badge');
    var metaSub = document.getElementById("manage-dx-rail-meta-sub");
    if (metaRail) {
      metaRail.className = "mui-rail-badge " + (data.generated_at ? "mui-rail-badge--ok" : "");
    }
    if (metaSub) {
      metaSub.textContent = data.generated_at ? "snapshot ready" : "awaiting run";
    }
  }

  function renderDiagnosisAudit(data) {
    var pre = document.getElementById("manage-diagnosis-json");
    if (!pre || !window.ManageUI || typeof window.ManageUI.jsonViewer !== "function") return;
    window.ManageUI.jsonViewer(pre, data, { label: "Diagnosis snapshot" });
  }

  function renderMeta(data) {
    var el = document.getElementById("manage-diagnosis-meta-grid");
    if (!el) return;
    var rows = [];
    if (data.generated_at) {
      rows.push({ label: "Generated", value: data.generated_at });
    }
    if (data.cached) {
      rows.push({
        label: "Cache",
        value: data.cache && data.cache.hit ? "TTL cache hit" : "fresh run",
      });
      if (typeof data.stale_seconds === "number") {
        rows.push({ label: "Snapshot age", value: data.stale_seconds + " s" });
      }
    } else {
      rows.push({ label: "Cache", value: "fresh run (not served from cache)" });
    }
    if (data.cache && typeof data.cache.ttl_seconds === "number") {
      rows.push({ label: "Cache TTL", value: data.cache.ttl_seconds + " s" });
    }
    if (!rows.length) {
      el.innerHTML = "<p class=\"manage-dx-empty\">No metadata yet — run a refresh.</p>";
      return;
    }
    var html = "<dl class=\"manage-dx-meta-grid\">";
    rows.forEach(function (row) {
      html += "<dt>" + escapeHtml(row.label) + "</dt><dd>" + escapeHtml(row.value) + "</dd>";
    });
    html += "</dl>";
    el.innerHTML = html;
  }

  function renderOverall(data) {
    var el = document.getElementById("manage-diagnosis-overall");
    if (!el) return;
    var st = data.overall_status || "initialized";
    var sum = data.summary || {};
    var headline =
      st === "running"
        ? "All critical checks report running."
        : st === "fail"
          ? "At least one critical check failed."
          : "Some checks are initialized or degraded — review groups below.";
    el.innerHTML =
      "<p class=\"mui-card-meta\">Overall posture</p>" +
      "<div class=\"manage-dx-overall-inner\">" +
      "<span class=\"" +
      statusBadgeClass(st) +
      "\" title=\"Overall status\">" +
      escapeHtml(st) +
      "</span>" +
      "<span class=\"manage-dx-summary-counts\" aria-label=\"Summary counts\">" +
      "running: " +
      (sum.running || 0) +
      " · initialized: " +
      (sum.initialized || 0) +
      " · fail: " +
      (sum.fail || 0) +
      "</span></div>" +
      "<p class=\"manage-dx-overall-copy muted\">" +
      escapeHtml(headline) +
      "</p>";
  }

  function detailsHasContent(details) {
    if (!details || typeof details !== "object" || Array.isArray(details)) return false;
    return Object.keys(details).length > 0;
  }

  function renderCheckDetails(c) {
    if (!detailsHasContent(c.details)) {
      return "";
    }
    var label = escapeHtml(c.label || c.id || "Check");
    return (
      "<details class=\"manage-dx-check-details\">" +
      "<summary>Technical details</summary>" +
      "<pre class=\"manage-psc-json\" data-json-viewer data-json-label=\"" +
      label +
      " details\">" +
      escapeHtml(JSON.stringify(c.details, null, 2)) +
      "</pre>" +
      "</details>"
    );
  }

  function renderGateLink(c) {
    if (!c.gate_id) return "";
    var gateBadgeClass = "manage-dx-gate-badge";
    var gateStatus = c.gate_status || "unknown";
    if (gateStatus === "closed") gateBadgeClass += " manage-dx-gate-badge--closed";
    else if (gateStatus === "partial") gateBadgeClass += " manage-dx-gate-badge--partial";
    else if (gateStatus === "open") gateBadgeClass += " manage-dx-gate-badge--open";

    return (
      "<p class=\"manage-dx-gate-info\">" +
      "Readiness gate: <strong>" +
      escapeHtml(c.gate_id) +
      "</strong> " +
      "<span class=\"" +
      gateBadgeClass +
      "\">" +
      escapeHtml(gateStatus) +
      "</span> " +
      "<a href=\"/manage/ai-stack/release-readiness\" class=\"manage-dx-gate-link\">View all gates</a>" +
      "</p>"
    );
  }

  function renderGroups(data) {
    var root = document.getElementById("manage-diagnosis-groups");
    if (!root) return;
    var groups = data.groups || [];
    if (!groups.length) {
      root.innerHTML = "<p class=\"manage-dx-empty\">No check groups returned. Verify backend access and feature <code>manage.system_diagnosis</code>.</p>";
      return;
    }
    var html = "";

    if (typeof data.partial_gate_count === "number") {
      html += "<section class=\"mui-card manage-dx-gates-summary\">";
      html += "<p class=\"mui-card-meta\">Readiness gates</p>";
      html += "<p class=\"manage-dx-gates-summary-line\">Partial gates: <strong>" + data.partial_gate_count + "</strong>";
      if (data.partial_gate_count > 0) {
        html += " <a href=\"/manage/ai-stack/release-readiness?status=partial\" class=\"manage-dx-gate-link\">View partial gates</a>";
      }
      html += "</p></section>";
    }

    for (var g = 0; g < groups.length; g++) {
      var grp = groups[g];
      var checks = grp.checks || [];
      html += "<section class=\"mui-card manage-dx-group\">";
      html += "<p class=\"mui-card-meta\">" + escapeHtml(grp.label || grp.id) + "</p>";
      if (!checks.length) {
        html += "<p class=\"manage-dx-empty\">No checks in this group.</p>";
      } else {
        html += "<ul class=\"manage-dx-check-list\">";
        for (var i = 0; i < checks.length; i++) {
          var c = checks[i];
          var crit = c.critical ? "critical" : "non-critical";
          var msg = (c.message || "").trim() || "No message from upstream check.";
          html += "<li class=\"manage-dx-check\">";
          html += "<div class=\"manage-dx-check-head\">";
          html += "<span class=\"" + statusBadgeClass(c.status) + "\">" + escapeHtml(c.status) + "</span>";
          html += "<strong class=\"manage-dx-check-label\">" + escapeHtml(c.label || c.id) + "</strong>";
          html += "<span class=\"manage-dx-check-meta muted\">" + escapeHtml(crit) + "</span>";
          html += "</div>";
          html += "<p class=\"manage-dx-msg\">" + escapeHtml(msg) + "</p>";
          var facts = [];
          if (typeof c.latency_ms === "number") {
            facts.push("Latency: " + c.latency_ms + " ms" + (c.timed_out ? " (timed out)" : ""));
          }
          if (c.source) facts.push("Source: " + c.source);
          if (c.id) facts.push("ID: " + c.id);
          if (facts.length) {
            html += "<p class=\"manage-dx-detail muted\">" + escapeHtml(facts.join(" · ")) + "</p>";
          }
          html += renderGateLink(c);
          html += renderCheckDetails(c);
          html += "</li>";
        }
        html += "</ul>";
      }
      html += "</section>";
    }
    root.innerHTML = html;
    if (window.ManageUI && typeof window.ManageUI.scan === "function") {
      window.ManageUI.scan(root);
    }
  }

  function setLoading(loading) {
    var overall = document.getElementById("manage-diagnosis-overall");
    var groups = document.getElementById("manage-diagnosis-groups");
    if (loading) {
      if (overall) {
        overall.innerHTML = "<p class=\"manage-dx-empty\">Loading overall status…</p>";
      }
      if (groups) {
        groups.innerHTML = "<p class=\"manage-dx-empty\">Loading checks…</p>";
      }
    }
  }

  function loadDiagnosis(refresh) {
    var errEl = document.getElementById("manage-diagnosis-error");
    if (errEl) {
      errEl.hidden = true;
      errEl.style.display = "none";
      errEl.textContent = "";
    }
    setLoading(true);
    var path = "/api/v1/admin/system-diagnosis";
    if (refresh) path += "?refresh=1";
    return window.ManageAuth.apiFetchWithAuth(path)
      .then(function (res) {
        var data = diagnosisPayload(res);
        if (!data || !data.groups) {
          throw { status: 0, message: "Diagnosis response missing groups — check proxy and backend route." };
        }
        renderMeta(data);
        renderDiagnosisAudit(data);
        renderOverall(data);
        renderGroups(data);
        syncRailBadges(data);
        if (window.ManageUI && typeof window.ManageUI.scan === "function") {
          window.ManageUI.scan(document.querySelector("[data-page=\"diagnosis\"]") || document);
        }
        return data;
      })
      .catch(function (e) {
        setLoading(false);
        var groups = document.getElementById("manage-diagnosis-groups");
        if (groups) {
          groups.innerHTML = "";
        }
        throw e;
      });
  }

  function showError(msg) {
    var errEl = document.getElementById("manage-diagnosis-error");
    if (!errEl) return;
    errEl.hidden = false;
    errEl.style.display = "";
    errEl.classList.remove("mui-hidden");
    errEl.textContent = msg || "Request failed";
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) {
      showError("ManageAuth is not loaded — cannot fetch diagnosis.");
      return;
    }
    var timer = null;
    function schedule() {
      if (timer) clearInterval(timer);
      timer = setInterval(function () {
        loadDiagnosis(false).catch(function (e) {
          showError(e && e.message ? e.message : "Auto-refresh failed");
        });
      }, REFRESH_MS);
    }

    window.ManageAuth.ensureAuth()
      .then(function () {
        return loadDiagnosis(false);
      })
      .then(function () {
        schedule();
      })
      .catch(function (e) {
        showError(e && e.message ? e.message : "Could not load system diagnosis");
      });

    var btn = document.getElementById("manage-diagnosis-refresh");
    if (btn) {
      btn.addEventListener("click", function () {
        loadDiagnosis(true).catch(function (e) {
          showError(e && e.message ? e.message : "Refresh failed");
        });
      });
    }
  });
})();
