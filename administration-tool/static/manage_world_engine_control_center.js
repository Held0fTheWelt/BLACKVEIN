(function () {
  function showMessage(kind, message) {
    var err = document.getElementById("wecc-banner");
    var ok = document.getElementById("wecc-success");
    if (err) {
      err.style.display = "none";
      err.textContent = "";
    }
    if (ok) {
      ok.style.display = "none";
      ok.textContent = "";
    }
    if (!message) return;
    if (kind === "ok" && ok) {
      ok.style.display = "";
      ok.textContent = message;
      return;
    }
    if (err) {
      err.style.display = "";
      err.textContent = message;
    }
  }

  function setJson(id, payload) {
    var node = document.getElementById(id);
    if (!node) return;
    node.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function fillList(ul, lines) {
    if (!ul) return;
    ul.innerHTML = "";
    (lines || []).forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      ul.appendChild(li);
    });
  }

  function connectivityGlanceLines(conn) {
    var lines = [];
    if (!conn) return lines;
    if (conn.error && conn.error.message) {
      lines.push("Last backend error talking to play-service: " + conn.error.message);
    }
    var ready = conn.backend_to_play_service_ready;
    if (ready && typeof ready === "object") {
      if (ready.status) lines.push("Ready probe status: " + ready.status);
      else if (ready.readiness) lines.push("Ready payload readiness: " + ready.readiness);
      else lines.push("Ready probe returned a payload (see technical JSON for fields).");
    } else if (!conn.error) {
      lines.push("No ready-probe payload yet — check posture and play-service process.");
    }
    return lines;
  }

  function renderOverviewBadges(payload) {
    var el = document.getElementById("wecc-overview-badges");
    if (!el) return;
    var st = payload.status || {};
    var bc = st.blocker_count != null ? st.blocker_count : (payload.blockers || []).length;
    var wc = st.warning_count != null ? st.warning_count : (payload.warnings || []).length;
    var state = st.state || (st.control_plane_ok ? "healthy" : "blocked");
    var ok = state === "healthy";
    var parts = [];
    parts.push("Control plane state: " + state);
    parts.push("Blockers: " + bc);
    parts.push("Warnings: " + wc);
    el.textContent = parts.join(" · ");
    el.className = "wecc-overview-badges muted" + (ok ? " wecc-overview-badges--ok" : " wecc-overview-badges--blocked");
  }

  function appendBlockerItem(ul, item) {
    var li = document.createElement("li");
    li.className = "wecc-blocker-item";
    var msg = document.createElement("div");
    msg.className = "wecc-blocker-msg";
    msg.textContent = item.msg;
    li.appendChild(msg);
    if (item.next) {
      var nx = document.createElement("div");
      nx.className = "wecc-blocker-next";
      nx.textContent = item.next;
      li.appendChild(nx);
    }
    ul.appendChild(li);
  }

  function renderPostureAndDrillDown(payload) {
    var glance = payload.posture_at_a_glance || {};
    fillList(document.getElementById("wecc-desired-glance"), glance.desired_lines || []);
    fillList(document.getElementById("wecc-observed-glance"), glance.observed_lines || []);
    fillList(document.getElementById("wecc-connectivity-glance"), connectivityGlanceLines(payload.connectivity || {}));
    var drillUl = document.getElementById("wecc-drill-down");
    if (!drillUl) return;
    drillUl.innerHTML = "";
    (payload.drill_down || []).forEach(function (row) {
      var li = document.createElement("li");
      var path = row.path || "";
      var hint = row.hint ? " — " + row.hint : "";
      if (path.indexOf("/manage/") === 0) {
        var a = document.createElement("a");
        a.href = path;
        a.textContent = row.label || "Open page";
        li.appendChild(a);
        li.appendChild(document.createTextNode(hint));
      } else {
        li.textContent = (row.label || "Page") + (path ? " (" + path + ")" : "") + hint;
      }
      drillUl.appendChild(li);
    });
  }

  function renderNarrativeLists(payload) {
    renderOverviewBadges(payload);
    var headline = document.getElementById("wecc-headline");
    var sub = document.getElementById("wecc-sub-lines");
    var dive = document.getElementById("wecc-deep-dive");
    var ctrlUl = document.getElementById("wecc-operator-controls");
    var summary = payload.operator_summary || {};
    if (headline) {
      headline.textContent = summary.headline || (payload.status && payload.status.control_plane_ok
        ? "Control plane reports no blocking issues."
        : "Review blockers and connectivity below.");
    }
    if (sub) {
      sub.innerHTML = "";
      (summary.sub_lines || []).forEach(function (line) {
        var li = document.createElement("li");
        li.textContent = line;
        sub.appendChild(li);
      });
    }
    if (dive) {
      dive.textContent = (summary.deep_dive_hint || "").replace(/\*\*/g, "");
    }
    if (ctrlUl) {
      ctrlUl.innerHTML = "";
      (payload.operator_controls || []).forEach(function (c) {
        var li = document.createElement("li");
        var label = c.label || c.id || "control";
        var method = c.method || "?";
        var path = c.path || "";
        var bits = [label + " (" + method + " " + path + ")"];
        if (c.requires_path_parameter) {
          bits.push("Needs " + c.requires_path_parameter + " in the URL — use " + (c.ui_surface || "World Engine console") + ".");
        }
        if (c.note) {
          bits.push(String(c.note).replace(/\*\*/g, ""));
        }
        li.textContent = bits.join(" ");
        ctrlUl.appendChild(li);
      });
    }
    renderPostureAndDrillDown(payload);
  }

  function blockerPresentation(row, kind) {
    var code = row.code || "";
    var msg = (row.message || code || "").trim();
    if (code) msg = "[" + code + "] " + msg;
    var next = "";
    if (row.suggested_action) {
      next = "Suggested next step: " + String(row.suggested_action).replace(/\*\*/g, "");
    }
    return { msg: msg, next: next };
  }

  function renderBlockersWarnings(payload) {
    var blockers = payload.blockers || [];
    var warnings = payload.warnings || [];
    var bEl = document.getElementById("wecc-blockers");
    var wEl = document.getElementById("wecc-warnings");
    if (bEl) {
      bEl.innerHTML = "";
      if (!blockers.length) {
        appendBlockerItem(bEl, { msg: "No blocking issues reported for this snapshot.", next: "" });
      } else {
        blockers.forEach(function (b) {
          var p = blockerPresentation(b, "blocker");
          appendBlockerItem(bEl, p);
        });
      }
    }
    if (wEl) {
      wEl.innerHTML = "";
      if (!warnings.length) {
        appendBlockerItem(wEl, { msg: "No warnings for this snapshot.", next: "" });
      } else {
        warnings.forEach(function (w) {
          var p = blockerPresentation(w, "warning");
          appendBlockerItem(wEl, p);
        });
      }
    }
  }

  function loadControlCenter() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/world-engine/control-center")
      .then(function (payload) {
        renderNarrativeLists(payload);
        setJson("wecc-desired", payload.desired_play_service_state || {});
        setJson("wecc-observed", payload.observed_play_service_state || {});
        setJson("wecc-connectivity", payload.connectivity || {});
        setJson("wecc-summary", payload.active_runtime || {});
        renderBlockersWarnings(payload);
      });
  }

  function postAction(path, successMessage) {
    return window.ManageAuth.apiFetchWithAuth(path, { method: "POST", body: "{}" })
      .then(function () {
        showMessage("ok", successMessage);
        return loadControlCenter();
      })
      .catch(function (err) {
        showMessage("err", err && err.message ? err.message : "Request failed");
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;

    window.ManageAuth.ensureAuth()
      .then(function () {
        return loadControlCenter();
      })
      .catch(function (err) {
        showMessage("err", err && err.message ? err.message : "Failed to load control center");
      });

    var refreshBtn = document.getElementById("wecc-refresh");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        showMessage(null, "");
        loadControlCenter().catch(function (err) {
          showMessage("err", err && err.message ? err.message : "Reload failed");
        });
      });
    }

    var testBtn = document.getElementById("wecc-test");
    if (testBtn) {
      testBtn.addEventListener("click", function () {
        showMessage(null, "");
        postAction("/api/v1/admin/play-service-control/test", "Connectivity test finished — review posture and warnings above.");
      });
    }

    var applyBtn = document.getElementById("wecc-apply");
    if (applyBtn) {
      applyBtn.addEventListener("click", function () {
        showMessage(null, "");
        postAction("/api/v1/admin/play-service-control/apply", "Saved desired configuration applied — verify observed posture.");
      });
    }
  });
})();
