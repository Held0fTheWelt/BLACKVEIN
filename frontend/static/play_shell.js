(function () {
  const shell = document.querySelector(".play-shell");
  if (!shell) return;

  const sessionId = shell.getAttribute("data-session-id") || "";
  const backendSessionId = (shell.getAttribute("data-backend-session-id") || "").trim();

  /* Tabs */
  const tabs = document.querySelectorAll(".play-tab");
  const panels = document.querySelectorAll(".play-panel");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      const targetId = tab.getAttribute("data-target");
      tabs.forEach(function (t) {
        const active = t === tab;
        t.classList.toggle("play-tab--active", active);
        t.setAttribute("aria-selected", active ? "true" : "false");
      });
      panels.forEach(function (p) {
        const show = p.id === targetId;
        p.classList.toggle("play-panel--active", show);
        if (show) {
          p.removeAttribute("hidden");
        } else {
          p.setAttribute("hidden", "hidden");
        }
      });
    });
  });

  let operatorJsonText = "{}";
  const bootEl = document.getElementById("play-shell-bootstrap");
  if (bootEl && bootEl.textContent) {
    try {
      const parsed = JSON.parse(bootEl.textContent);
      operatorJsonText = JSON.stringify(parsed.operator_bundle || {}, null, 2);
    } catch (_e) {
      operatorJsonText = "{}";
    }
  }
  const operatorPre = document.getElementById("operator-raw-pre");
  if (operatorPre) {
    operatorPre.textContent = operatorJsonText;
  }

  function setOperatorJson(obj) {
    operatorJsonText = JSON.stringify(obj || {}, null, 2);
    if (operatorPre) {
      operatorPre.textContent = operatorJsonText;
    }
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function buildTurnCardHtml(v) {
    const tn = v.turn_number != null ? "Zug " + escapeHtml(String(v.turn_number)) : "";
    const trace = v.trace_id ? " · <code>" + escapeHtml(v.trace_id) + "</code>" : "";
    const kind = v.interpreted_input_kind ? " · <strong>" + escapeHtml(v.interpreted_input_kind) + "</strong>" : "";
    let html = '<article class="play-turn-card play-turn-card--fresh">';
    html += '<header class="play-turn-card__meta runtime-meta">' + tn + trace + kind + "</header>";
    if (v.player_line) {
      html += '<p class="runtime-player-line"><strong>Du:</strong> ' + escapeHtml(v.player_line) + "</p>";
    }
    html += '<div class="runtime-scene-strip runtime-meta">';
    if (v.current_scene_id) {
      html += "Szene: <code>" + escapeHtml(v.current_scene_id) + "</code>";
    }
    if (v.committed_scene_id) {
      html += " · festgeschrieben: <code>" + escapeHtml(v.committed_scene_id) + "</code>";
    }
    if (v.validation_status) {
      html += " · Prüfung: <strong>" + escapeHtml(v.validation_status) + "</strong>";
    }
    if (v.graph_error_count) {
      html +=
        ' · Graph-Fehler: <strong class="runtime-warn">' + escapeHtml(String(v.graph_error_count)) + "</strong>";
    }
    html += "</div>";
    html += '<div class="play-story-output">';
    if (v.narration_text) {
      html += '<div class="play-story-text play-turn-card__narration">' + escapeHtml(v.narration_text) + "</div>";
    } else {
      html +=
        '<p class="play-story-missing">Für diesen Zug liefert die Engine keinen erzählenden Text (<code>gm_narration</code> leer). Der Lauf kann trotzdem weitergegangen sein — Details siehe Operator-Tab.</p>';
    }
    html += "</div>";
    if (v.spoken_lines && v.spoken_lines.length) {
      html += '<h3 class="play-dialogue-label">Gesprochen</h3><ul class="runtime-spoken play-dialogue-list">';
      v.spoken_lines.forEach(function (line) {
        html += "<li>" + escapeHtml(line) + "</li>";
      });
      html += "</ul>";
    }
    if (v.committed_consequences && v.committed_consequences.length) {
      html += '<h3 class="play-dialogue-label">Folgen</h3><ul class="runtime-consequences">';
      v.committed_consequences.forEach(function (c) {
        html += "<li>" + escapeHtml(String(c)) + "</li>";
      });
      html += "</ul>";
    }
    html += "</article>";
    return html;
  }

  const form = document.getElementById("play-execute-form");
  const executeStatus = document.getElementById("execute-status");
  const transcriptRoot = document.getElementById("turn-transcript");

  if (form && transcriptRoot) {
    form.addEventListener("submit", function (ev) {
      const ta = document.getElementById("player-input");
      if (!ta || !ta.value.trim()) return;
      ev.preventDefault();
      const btn = document.getElementById("execute-turn-btn");
      if (btn) btn.disabled = true;
      if (executeStatus) executeStatus.textContent = "Zug wird ausgeführt…";
      fetch(form.action, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({ player_input: ta.value.trim() }),
      })
        .then(function (r) {
          return r.json().then(function (data) {
            return { ok: r.ok, status: r.status, data: data };
          });
        })
        .then(function (res) {
          if (!res.ok || !res.data.ok) {
            const msg = (res.data && res.data.error) || "Zug fehlgeschlagen.";
            if (executeStatus) executeStatus.textContent = msg;
            return;
          }
          const empty = document.getElementById("transcript-empty");
          if (empty) empty.remove();
          transcriptRoot.insertAdjacentHTML("beforeend", buildTurnCardHtml(res.data.runtime_view));
          transcriptRoot.scrollTop = transcriptRoot.scrollHeight;
          const lastCard = transcriptRoot.querySelector(".play-turn-card:last-of-type");
          if (lastCard && typeof lastCard.scrollIntoView === "function") {
            lastCard.scrollIntoView({ block: "nearest", behavior: "smooth" });
          }
          window.setTimeout(function () {
            document.querySelectorAll(".play-turn-card--fresh").forEach(function (el) {
              el.classList.remove("play-turn-card--fresh");
            });
          }, 1200);
          if (res.data.operator_bundle) {
            setOperatorJson(res.data.operator_bundle);
          }
          ta.value = "";
          if (executeStatus) {
            executeStatus.textContent =
              "Antwort da — interpretiert als „" + (res.data.interpreted_input_kind || "unbekannt") + "“.";
          }
        })
        .catch(function () {
          if (executeStatus) {
            executeStatus.textContent =
              "Netzwerkfehler — erneut versuchen oder Formular ohne JavaScript absenden.";
          }
        })
        .finally(function () {
          if (btn) btn.disabled = false;
        });
    });
  }

  document.getElementById("copy-trace-btn") &&
    document.getElementById("copy-trace-btn").addEventListener("click", function () {
      let trace = "";
      try {
        const o = JSON.parse(operatorJsonText);
        trace = (o.trace_id || (o.turn && o.turn.trace_id) || "") + "";
      } catch (_e) {}
      if (trace) {
        navigator.clipboard.writeText(trace);
      }
    });

  document.getElementById("copy-operator-json-btn") &&
    document.getElementById("copy-operator-json-btn").addEventListener("click", function () {
      navigator.clipboard.writeText(operatorJsonText);
    });

  const refreshBtn = document.getElementById("refresh-operator-bundle-btn");
  const refreshStatus = document.getElementById("refresh-operator-status");
  if (refreshBtn && backendSessionId) {
    refreshBtn.addEventListener("click", function () {
      refreshStatus.textContent = "Loading…";
      fetch("/api/v1/sessions/" + encodeURIComponent(backendSessionId) + "/play-operator-bundle", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      })
        .then(function (r) {
          return r.json().then(function (data) {
            return { ok: r.ok, data: data };
          });
        })
        .then(function (res) {
          if (!res.ok) {
            const err = res.data.error || {};
            refreshStatus.textContent = (err.message || err.code || "Request failed") + "";
            return;
          }
          if (res.data.error) {
            refreshStatus.textContent = (res.data.error.message || res.data.error.code || "Error") + "";
            return;
          }
          setOperatorJson(res.data);
          refreshStatus.textContent = "Updated from API.";
        })
        .catch(function () {
          refreshStatus.textContent = "Refresh failed.";
        });
    });
  }

  if (typeof window.initPlayLiveWs === "function") {
    window.initPlayLiveWs();
  }
})();
