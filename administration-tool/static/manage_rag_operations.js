(function () {
  var state = { status: null, settings: null };

  function show(kind, msg) {
    var err = document.getElementById("manage-rag-banner");
    var ok = document.getElementById("manage-rag-success");
    if (err) {
      err.style.display = "none";
      err.textContent = "";
    }
    if (ok) {
      ok.style.display = "none";
      ok.textContent = "";
    }
    if (!msg) return;
    if (kind === "ok" && ok) {
      ok.style.display = "";
      ok.textContent = msg;
    } else if (err) {
      err.style.display = "";
      err.textContent = msg;
    }
  }

  function parseError(err) {
    if (!err) return "Request failed";
    if (typeof err.message === "string" && err.message) return err.message;
    if (err.body && window.ManageAuth && typeof window.ManageAuth.formatApiErrorMessage === "function") {
      return window.ManageAuth.formatApiErrorMessage(err.body, err.status);
    }
    return "Request failed";
  }

  function value(id, fallback) {
    var node = document.getElementById(id);
    if (!node) return fallback || "";
    return (node.value || fallback || "").trim();
  }

  function checked(id) {
    var node = document.getElementById(id);
    return !!(node && node.checked);
  }

  function setValue(id, val) {
    var node = document.getElementById(id);
    if (node) node.value = val == null ? "" : String(val);
  }

  function setChecked(id, val) {
    var node = document.getElementById(id);
    if (node) node.checked = !!val;
  }

  function setJson(id, payload) {
    var box = document.getElementById(id);
    if (!box) return;
    box.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function fillLines(id, lines, fallback) {
    var ul = document.getElementById(id);
    if (!ul) return;
    ul.innerHTML = "";
    (lines || []).forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      ul.appendChild(li);
    });
    if (!lines || !lines.length) {
      var empty = document.createElement("li");
      empty.textContent = fallback || "None";
      ul.appendChild(empty);
    }
  }

  function renderStatus(payload) {
    state.status = payload || {};
    var corpus = state.status.corpus || {};
    var retrieval = state.status.retrieval || {};
    var emb = state.status.embedding_backend || {};
    var dense = state.status.dense_index || {};
    fillLines("manage-rag-status-lines", [
      "Corpus chunks: " + (corpus.chunk_count || 0) + " | sources: " + (corpus.source_count || 0),
      "Retrieval mode (runtime/setting): " + (retrieval.mode_runtime || "?") + " / " + (retrieval.mode_setting || "?"),
      "Retrieval profile: " + (retrieval.retrieval_profile || "runtime_turn_support"),
      "Embedding backend: " + (emb.available ? "available" : "unavailable") + " (" + (emb.primary_reason_code || "n/a") + ")",
      "Dense index: " + (dense.present_on_retriever ? "attached" : "not attached") + " | validity: " + (dense.artifact_validity || "unknown"),
      "Corpus storage path: " + (corpus.storage_path || "n/a")
    ], "No RAG status data.");
    fillLines("manage-rag-degraded-lines", state.status.degraded_reasons || [], "No degraded reasons reported.");
    setJson("manage-rag-json", { status: state.status, settings: state.settings });
  }

  function renderSettings(payload) {
    state.settings = payload || {};
    setValue("manage-rag-setting-mode", state.settings.retrieval_execution_mode || "disabled");
    setValue("manage-rag-setting-profile", state.settings.retrieval_profile || "runtime_turn_support");
    setValue("manage-rag-setting-topk", state.settings.retrieval_top_k || 4);
    setValue("manage-rag-setting-min-score", state.settings.retrieval_min_score == null ? "" : state.settings.retrieval_min_score);
    setChecked("manage-rag-setting-embeddings", state.settings.embeddings_enabled);
    setJson("manage-rag-json", { status: state.status, settings: state.settings });
  }

  function renderProbe(payload) {
    var result = payload.result || {};
    fillLines("manage-rag-probe-summary", [
      "Status: " + (result.status || "?") + " | route: " + (result.retrieval_route || "?"),
      "Hit count: " + (result.hit_count || 0) + " | degradation: " + (result.degradation_mode || "none"),
      "Embedding model: " + (result.embedding_model_id || "n/a")
    ], "No probe summary.");
    var list = document.getElementById("manage-rag-probe-results");
    if (!list) return;
    list.innerHTML = "";
    (result.hits || []).forEach(function (hit) {
      var li = document.createElement("li");
      li.textContent = "[" + (hit.score != null ? hit.score.toFixed(3) : "?") + "] " + (hit.source_name || hit.source_path || "source")
        + " · class " + (hit.content_class || "?") + " · " + (hit.snippet || "");
      list.appendChild(li);
    });
    if (!(result.hits || []).length) {
      var empty = document.createElement("li");
      empty.textContent = "No hits returned.";
      list.appendChild(empty);
    }
    setJson("manage-rag-json", { status: state.status, settings: state.settings, probe: payload });
  }

  function loadStatus() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/rag/status").then(function (res) {
      renderStatus(res && res.data ? res.data : {});
    });
  }

  function loadSettings() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/rag/settings").then(function (res) {
      renderSettings(res && res.data ? res.data : {});
    });
  }

  function refreshAll() {
    return Promise.all([loadStatus(), loadSettings()]);
  }

  function bindActions() {
    var save = document.getElementById("manage-rag-save-settings");
    if (save) {
      save.addEventListener("click", function () {
        var body = {
          retrieval_execution_mode: value("manage-rag-setting-mode", "disabled"),
          retrieval_profile: value("manage-rag-setting-profile", "runtime_turn_support"),
          retrieval_top_k: parseInt(value("manage-rag-setting-topk", "4"), 10) || 4,
          embeddings_enabled: checked("manage-rag-setting-embeddings")
        };
        var minScoreRaw = value("manage-rag-setting-min-score", "");
        if (minScoreRaw !== "") {
          body.retrieval_min_score = parseFloat(minScoreRaw);
        }
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/rag/settings", {
          method: "PATCH",
          body: JSON.stringify(body)
        }).then(function () {
          return refreshAll().then(function () {
            show("ok", "RAG settings saved.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var runProbe = document.getElementById("manage-rag-run-probe");
    if (runProbe) {
      runProbe.addEventListener("click", function () {
        var query = value("manage-rag-probe-query", "");
        if (!query) {
          show("err", "Probe query is required.");
          return;
        }
        var body = {
          query: query,
          domain: value("manage-rag-probe-domain", "runtime"),
          max_chunks: parseInt(value("manage-rag-probe-max-chunks", "4"), 10) || 4,
          use_sparse_only: checked("manage-rag-probe-sparse-only")
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/rag/probe", {
          method: "POST",
          body: JSON.stringify(body)
        }).then(function (res) {
          renderProbe(res && res.data ? res.data : {});
          show("ok", "Probe completed.");
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    Array.prototype.forEach.call(document.querySelectorAll("[data-rag-action]"), function (btn) {
      btn.addEventListener("click", function () {
        var actionId = btn.getAttribute("data-rag-action") || "";
        if (!actionId) return;
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/rag/actions/" + actionId, {
          method: "POST",
          body: "{}"
        }).then(function (res) {
          var data = res && res.data ? res.data : {};
          renderStatus(data.status || {});
          show("ok", data.operator_message || "Action executed.");
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;
    window.ManageAuth.ensureAuth().then(function () {
      bindActions();
      return refreshAll();
    }).catch(function (err) {
      show("err", parseError(err));
    });
    var refresh = document.getElementById("manage-rag-refresh");
    if (refresh) {
      refresh.addEventListener("click", function () {
        show(null, "");
        refreshAll().catch(function (err) {
          show("err", parseError(err));
        });
      });
    }
  });
})();
