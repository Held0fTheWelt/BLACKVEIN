(function () {
  "use strict";

  function selectedSessionId() {
    var input = document.getElementById("ui-session-id");
    return input ? String(input.value || "").trim() : "";
  }

  function setSelectedSessionId(sessionId) {
    var input = document.getElementById("ui-session-id");
    if (input) input.value = sessionId || "";
    try {
      if (sessionId) sessionStorage.setItem("we_ui_session_id", sessionId);
      else sessionStorage.removeItem("we_ui_session_id");
    } catch (e) {}
  }

  function restoreSessionId() {
    try {
      var saved = sessionStorage.getItem("we_ui_session_id");
      if (saved) setSelectedSessionId(saved);
    } catch (e) {}
  }

  function bindSessionPicker(onApply) {
    restoreSessionId();
    var applyBtn = document.getElementById("ui-session-apply");
    var refreshBtn = document.getElementById("ui-session-refresh");
    var select = document.getElementById("ui-session-select");
    if (applyBtn) {
      applyBtn.addEventListener("click", function () {
        setSelectedSessionId(selectedSessionId());
        if (typeof onApply === "function") onApply(selectedSessionId());
      });
    }
    if (select) {
      select.addEventListener("change", function () {
        setSelectedSessionId(select.value);
        if (typeof onApply === "function") onApply(select.value);
      });
    }
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        loadSessionOptions();
      });
    }
  }

  function loadSessionOptions() {
    if (!window.WorldEngineUI) return Promise.resolve();
    return window.WorldEngineUI.apiFetch("admin/world-engine/story/sessions")
      .then(function (data) {
        var select = document.getElementById("ui-session-select");
        if (!select) return;
        select.innerHTML = "";
        var items = data && data.items ? data.items : [];
        items.forEach(function (row) {
          var sid = row.session_id;
          if (!sid) return;
          var opt = document.createElement("option");
          opt.value = sid;
          opt.textContent = sid + " | " + (row.module_id || "") + " | turn " + String(row.turn_counter || 0);
          select.appendChild(opt);
        });
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message || String(err), true);
      });
  }

  window.WorldEngineSession = {
    selectedSessionId: selectedSessionId,
    setSelectedSessionId: setSelectedSessionId,
    bindSessionPicker: bindSessionPicker,
    loadSessionOptions: loadSessionOptions,
  };
})();
