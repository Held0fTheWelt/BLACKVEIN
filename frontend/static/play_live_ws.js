(function () {
  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function renderLiveSnapshot(root, snapshot) {
    if (!root || !snapshot) return;
    const room = snapshot.current_room || null;
    let html = `<div class="live-ws-meta runtime-meta">Run <code>${escapeHtml(snapshot.run_id)}</code> · ${escapeHtml(snapshot.template_title || "")} · beat ${escapeHtml(snapshot.beat_id)} · tension ${escapeHtml(String(snapshot.tension))}</div>`;
    if (room) {
      html += `<h4 class="live-ws-room-title">${escapeHtml(room.name)}</h4>`;
      html += `<p class="live-ws-room-desc">${escapeHtml(room.description || "")}</p>`;
    }
    const tail = snapshot.transcript_tail;
    if (Array.isArray(tail) && tail.length) {
      html += '<div class="live-ws-transcript">';
      tail.forEach(function (entry) {
        const at = entry && entry.at != null ? entry.at : "";
        const text = entry && entry.text != null ? entry.text : "";
        const actor = entry && entry.actor ? ` · ${entry.actor}` : "";
        html += `<div class="live-ws-entry"><div class="runtime-meta">${escapeHtml(String(at))}${escapeHtml(actor)}</div><div class="live-ws-entry-text">${escapeHtml(String(text))}</div></div>`;
      });
      html += "</div>";
    }
    root.innerHTML = html;
  }

  window.initPlayLiveWs = function initPlayLiveWs() {
    const connectBtn = document.getElementById("connect-btn");
    const status = document.getElementById("socket-status");
    const wsBaseEl = document.getElementById("ws-base");
    const ticketEl = document.getElementById("play-ticket");
    const snapshotRoot = document.getElementById("live-ws-snapshot-root");
    const autoEl = document.getElementById("ws-autoconnect");
    if (!connectBtn || !status || !wsBaseEl || !ticketEl) return;

    let socket = null;

    function connect() {
      const wsBase = (wsBaseEl.textContent || "").trim().replace(/\/$/, "");
      const ticket = (ticketEl.textContent || "").trim();
      if (!wsBase || !ticket) {
        status.textContent = "Missing WebSocket ticket data";
        return;
      }
      if (socket) {
        socket.close();
      }
      let url;
      try {
        const u = new URL(wsBase);
        const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
        url = `${wsProto}//${u.host}/ws?ticket=${encodeURIComponent(ticket)}`;
      } catch (_e) {
        const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
        url = `${wsProto}//${window.location.host}/ws?ticket=${encodeURIComponent(ticket)}`;
      }
      socket = new WebSocket(url);
      status.textContent = "Connecting…";
      socket.onopen = function () {
        status.textContent = "Connected (runtime manager)";
      };
      socket.onclose = function () {
        status.textContent = "Disconnected";
      };
      socket.onerror = function () {
        status.textContent = "Socket error";
      };
      socket.onmessage = function (event) {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "snapshot" && snapshotRoot) {
            renderLiveSnapshot(snapshotRoot, payload.data);
            status.textContent = "Connected — snapshot updated";
          } else if (payload.type === "command_rejected") {
            status.textContent = "Command rejected";
            window.alert(payload.reason || "Command rejected");
          } else {
            status.textContent = "Live message: " + payload.type;
          }
        } catch (_err) {
          status.textContent = "Non-JSON message (" + event.data.length + " bytes)";
        }
      };
    }

    connectBtn.addEventListener("click", connect);
    if (autoEl && autoEl.checked) {
      connect();
    }
    autoEl &&
      autoEl.addEventListener("change", function () {
        if (autoEl.checked) {
          connect();
        } else if (socket) {
          socket.close();
          socket = null;
        }
      });
  };
})();
