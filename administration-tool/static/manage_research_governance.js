/**
 * Strategic research-domain governance pages: load layered payloads from backend.
 */
(function () {
  function showBanner(id, text) {
    var el = document.getElementById(id);
    if (!el) return;
    if (!text) {
      el.style.display = "none";
      el.textContent = "";
      return;
    }
    el.style.display = "";
    el.textContent = text;
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text || "";
  }

  function setJson(id, obj) {
    var el = document.getElementById(id);
    if (!el) return;
    try {
      el.textContent = JSON.stringify(obj || {}, null, 2);
    } catch (e) {
      el.textContent = String(obj);
    }
  }

  function renderNavLinks(containerId, drillDown) {
    var ul = document.getElementById(containerId);
    if (!ul || !drillDown) return;
    ul.innerHTML = "";
    drillDown.forEach(function (item) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = item.path || "#";
      a.textContent = item.label || item.path;
      li.appendChild(a);
      ul.appendChild(li);
    });
  }

  function renderOverviewLayers(layers) {
    var host = document.getElementById("research-layer-cards");
    if (!host || !layers) return;
    host.innerHTML = "";
    var order = [
      "source_intake",
      "extraction_tuning",
      "findings_candidates",
      "canonical_truth",
      "mcp_workbench",
    ];
    order.forEach(function (key) {
      var L = layers[key];
      if (!L) return;
      var card = document.createElement("article");
      card.className = "panel research-layer-card";
      var title = document.createElement("header");
      title.className = "panel-header";
      var h = document.createElement("h2");
      h.textContent = key.replace(/_/g, " ");
      title.appendChild(h);
      card.appendChild(title);
      var body = document.createElement("div");
      body.className = "panel-body";
      var p = document.createElement("p");
      p.className = "muted";
      var sum = L.summary || {};
      p.textContent = JSON.stringify(sum);
      body.appendChild(p);
      var bw = (L.blockers || []).length + (L.warnings || []).length;
      if (bw) {
        var note = document.createElement("p");
        note.className = "manage-state manage-state--warn";
        note.textContent = "Signals: " + bw + " blocker/warning row(s) — open the layer page.";
        body.appendChild(note);
      }
      card.appendChild(body);
      host.appendChild(card);
    });
  }

  function loadOverview() {
    if (!window.ManageAuth || !window.ManageAuth.apiFetchWithAuth) return;
    window.ManageAuth.apiFetchWithAuth("/api/v1/admin/research-domain/overview")
      .then(function (body) {
        showBanner("research-error-banner", "");
        var data = body && body.data ? body.data : body;
        setText(
          "research-strip",
          "Operational state: " +
            (data.operational_state || "unknown") +
            " · governance version: " +
            (data.governance_version || "?")
        );
        var pr = data.governance_principles || {};
        setText(
          "research-principles",
          "Many findings allowed: " +
            !!pr.many_candidate_findings_allowed +
            " · one promoted canonical package per governed module: " +
            !!pr.single_promoted_canonical_truth_per_governed_module
        );
        renderNavLinks("research-drilldown", data.drill_down);
        renderOverviewLayers(data.layers);
        setJson("research-json-technical", data);
      })
      .catch(function (err) {
        var msg = (err && err.message) || "Failed to load overview";
        showBanner("research-error-banner", msg);
      });
  }

  function loadLayer(layerId) {
    if (!window.ManageAuth || !window.ManageAuth.apiFetchWithAuth) return;
    window.ManageAuth.apiFetchWithAuth("/api/v1/admin/research-domain/layer/" + encodeURIComponent(layerId))
      .then(function (body) {
        showBanner("research-error-banner", "");
        var data = body && body.data ? body.data : body;
        setText("research-strip", "Layer: " + layerId + " · state: " + (data.operational_state || "?"));
        var layer = data.layer || {};
        setText("research-layer-role", layer.layer_role || "");
        var canon = document.getElementById("research-canonical-note");
        if (canon) {
          if (layer.is_canonical_layer === true) {
            canon.style.display = "";
            canon.textContent = "This layer reflects governed canonical (promoted) operational truth — not raw research drafts.";
          } else if (layer.is_canonical_layer === false) {
            canon.style.display = "";
            canon.textContent = "This layer is explicitly non-canonical until promotion through narrative governance.";
          } else {
            canon.style.display = "none";
          }
        }
        renderNavLinks("research-drilldown", [
          { label: "Research overview", path: "/manage/research/overview" },
          { label: "Source intake", path: "/manage/research/source-intake" },
          { label: "Extraction / tuning", path: "/manage/research/extraction-tuning" },
          { label: "Findings (candidates)", path: "/manage/research/findings" },
          { label: "Canonical truth", path: "/manage/research/canonical-truth" },
          { label: "MCP / workbench posture", path: "/manage/research/mcp-workbench" },
        ]);
        setJson("research-json-technical", data);
      })
      .catch(function (err) {
        showBanner("research-error-banner", (err && err.message) || "Failed to load layer");
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector("[data-research-governance-page]");
    if (!root) return;
    if (window.ManageAuth && window.ManageAuth.ensureAuth) {
      window.ManageAuth.ensureAuth().catch(function () {});
    }
    var mode = root.getAttribute("data-research-governance-page");
    if (mode === "overview") loadOverview();
    else if (mode && mode.indexOf("layer:") === 0) loadLayer(mode.slice("layer:".length));
  });
})();
