(function () {
  var api = null;

  function init() {
    if (!window.ManageAuth || !window.ManageAuth.apiFetchWithAuth) {
      console.error("ManageAuth not available for manage_data.");
      return;
    }
    api = window.ManageAuth.apiFetchWithAuth;
    bindExport();
    bindImport();
    loadTables();
  }

  function bindExport() {
    var form = document.getElementById("data-export-form");
    var scopeEl = document.getElementById("data-export-scope");
    var rowsField = document.getElementById("data-export-rows-field");
    var output = document.getElementById("data-export-output");

    if (!form || !scopeEl || !rowsField || !output) return;

    function updateScopeUI() {
      var scope = scopeEl.value;
      rowsField.style.display = scope === "rows" ? "" : "none";
    }
    scopeEl.addEventListener("change", updateScopeUI);
    updateScopeUI();

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!api) return;
      output.textContent = "Export running...";
      var scope = scopeEl.value;
      var table = document.getElementById("data-export-table").value || null;
      var pksRaw = document.getElementById("data-export-pks").value || "";
      var body = { scope: scope };
      if (scope === "table" || scope === "rows") {
        body.table = table;
      }
      if (scope === "rows") {
        var ids = pksRaw
          .split(",")
          .map(function (s) { return s.trim(); })
          .filter(function (s) { return s.length > 0; })
          .map(function (s) { var n = Number(s); return isNaN(n) ? s : n; });
        body.primary_keys = ids;
      }
      api("/data/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      }).then(function (res) {
        if (!res.ok) {
          return res.json().then(function (j) {
            throw new Error(j.error || ("HTTP " + res.status));
          });
        }
        return res.json();
      }).then(function (json) {
        output.textContent = JSON.stringify(json, null, 2);
      }).catch(function (err) {
        console.error(err);
        output.textContent = "Export failed: " + err.message;
      });
    });
  }

  function loadTables() {
    var selectEl = document.getElementById("data-export-table");
    if (!api || !selectEl) return;
    // Use list_exportable_tables via a lightweight export metadata-only call: scope=full, then read metadata.tables
    api("/data/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: "full" })
    }).then(function (res) {
      if (!res.ok) return res.json().then(function (j) { throw new Error(j.error || ("HTTP " + res.status)); });
      return res.json();
    }).then(function (json) {
      var tables = (json.metadata && json.metadata.tables) || [];
      tables.forEach(function (t) {
        var opt = document.createElement("option");
        opt.value = t.name;
        opt.textContent = t.name + " (" + t.row_count + ")";
        selectEl.appendChild(opt);
      });
    }).catch(function (err) {
      console.warn("Could not pre-load tables for export:", err);
    });
  }

  function bindImport() {
    var textarea = document.getElementById("data-import-json");
    var preflightBtn = document.getElementById("data-import-preflight");
    var executeBtn = document.getElementById("data-import-execute");
    var preflightOut = document.getElementById("data-import-preflight-output");
    var executeOut = document.getElementById("data-import-execute-output");
    if (!textarea || !preflightBtn || !executeBtn || !preflightOut || !executeOut) return;

    function parseJson() {
      var raw = textarea.value || "";
      if (!raw.trim()) {
        throw new Error("No JSON payload provided.");
      }
      try {
        return JSON.parse(raw);
      } catch (e) {
        throw new Error("Invalid JSON: " + e.message);
      }
    }

    preflightBtn.addEventListener("click", function () {
      if (!api) return;
      preflightOut.textContent = "Preflight running...";
      executeOut.textContent = "";
      var payload;
      try {
        payload = parseJson();
      } catch (e) {
        preflightOut.textContent = e.message;
        return;
      }
      api("/data/import/preflight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (res) {
        return res.json().then(function (j) { return { status: res.status, body: j }; });
      }).then(function (res) {
        preflightOut.textContent = JSON.stringify(res.body, null, 2);
      }).catch(function (err) {
        preflightOut.textContent = "Preflight failed: " + err.message;
      });
    });

    executeBtn.addEventListener("click", function () {
      if (!api) return;
      executeOut.textContent = "Import running...";
      var payload;
      try {
        payload = parseJson();
      } catch (e) {
        executeOut.textContent = e.message;
        return;
      }
      api("/data/import/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (res) {
        return res.json().then(function (j) { return { status: res.status, body: j }; });
      }).then(function (res) {
        executeOut.textContent = JSON.stringify(res.body, null, 2);
      }).catch(function (err) {
        executeOut.textContent = "Import failed: " + err.message;
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

