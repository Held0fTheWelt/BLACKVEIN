(function () {
  const shell = document.querySelector(".play-shell");
  if (!shell) return;

  function escapeHtml(value) {
    const d = document.createElement("div");
    d.textContent = value == null ? "" : String(value);
    return d.innerHTML;
  }

  function entryHtml(entry) {
    const speaker = entry.speaker || "World of Shadows";
    const turn = entry.turn_number != null ? "Turn " + escapeHtml(entry.turn_number) + " · " : "";
    let html = '<article class="play-turn-card play-turn-card--fresh">';
    html += '<header class="play-turn-card__meta">' + turn + escapeHtml(speaker) + "</header>";
    if (entry.role === "player") {
      html += '<p class="runtime-player-line"><strong>You:</strong> ' + escapeHtml(entry.text || "") + "</p>";
    } else if (entry.text) {
      html += '<div class="play-story-output">';
      html +=
        '<div class="play-story-text play-turn-card__narration play-narration--reveal">' +
        escapeHtml(entry.text) +
        "</div>";
      html += "</div>";
    }
    if (entry.spoken_lines && entry.spoken_lines.length) {
      html += '<h3 class="play-dialogue-label">Spoken</h3><ul class="runtime-spoken play-dialogue-list">';
      entry.spoken_lines.forEach(function (line) {
        html += "<li>" + escapeHtml(line) + "</li>";
      });
      html += "</ul>";
    }
    if (entry.committed_consequences && entry.committed_consequences.length) {
      html += '<h3 class="play-dialogue-label">Consequences</h3><ul class="runtime-consequences">';
      entry.committed_consequences.forEach(function (line) {
        html += "<li>" + escapeHtml(line) + "</li>";
      });
      html += "</ul>";
    }
    html += "</article>";
    return html;
  }

  function renderEntries(entries) {
    const transcriptRoot = document.getElementById("turn-transcript");
    if (!transcriptRoot) return;
    if (!entries || !entries.length) {
      transcriptRoot.innerHTML =
        '<p id="transcript-empty" class="play-story-placeholder">No authored opening was returned by the story runtime. The player session is not ready for meaningful play.</p>';
      return;
    }
    transcriptRoot.innerHTML = entries.map(entryHtml).join("");
    transcriptRoot.scrollTop = transcriptRoot.scrollHeight;
    const lastCard = transcriptRoot.querySelector(".play-turn-card:last-of-type");
    if (lastCard && typeof lastCard.scrollIntoView === "function") {
      lastCard.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    window.setTimeout(function () {
      document.querySelectorAll(".play-turn-card--fresh").forEach(function (el) {
        el.classList.remove("play-turn-card--fresh");
      });
    }, 1000);
  }

  const form = document.getElementById("play-execute-form");
  const executeStatus = document.getElementById("execute-status");
  if (!form) return;

  form.addEventListener("submit", function (ev) {
    const ta = document.getElementById("player-input");
    if (!ta || !ta.value.trim()) return;
    ev.preventDefault();
    const btn = document.getElementById("execute-turn-btn");
    if (btn) btn.disabled = true;
    if (executeStatus) executeStatus.textContent = "Submitting turn...";
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
          return { ok: r.ok, data: data };
        });
      })
      .then(function (res) {
        if (!res.ok || !res.data.ok) {
          if (executeStatus) executeStatus.textContent = (res.data && res.data.error) || "Turn failed.";
          return;
        }
        renderEntries(res.data.story_entries || []);
        ta.value = "";
        if (executeStatus) {
          executeStatus.textContent = "Story updated.";
        }
      })
      .catch(function () {
        if (executeStatus) executeStatus.textContent = "Network error. Try again.";
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  });
})();
