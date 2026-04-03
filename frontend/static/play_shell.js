(function () {
  const connectBtn = document.getElementById("connect-btn");
  const status = document.getElementById("socket-status");
  const wsBaseEl = document.getElementById("ws-base");
  const ticketEl = document.getElementById("play-ticket");
  if (!connectBtn || !status || !wsBaseEl || !ticketEl) return;

  let socket = null;
  connectBtn.addEventListener("click", function () {
    const wsBase = (wsBaseEl.textContent || "").trim().replace(/\/$/, "");
    const ticket = (ticketEl.textContent || "").trim();
    if (!wsBase || !ticket) {
      status.textContent = "Missing WebSocket ticket data";
      return;
    }
    if (socket) {
      socket.close();
    }
    const url = `${wsBase}/ws?ticket=${encodeURIComponent(ticket)}`;
    socket = new WebSocket(url);
    status.textContent = "Connecting...";
    socket.onopen = function () {
      status.textContent = "Connected";
    };
    socket.onclose = function () {
      status.textContent = "Disconnected";
    };
    socket.onerror = function () {
      status.textContent = "Socket error";
    };
    socket.onmessage = function (event) {
      status.textContent = `Live update received (${event.data.length} bytes)`;
    };
  });
})();
