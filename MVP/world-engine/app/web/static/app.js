const state = {
  templates: [],
  runs: [],
  currentRunId: null,
  participantId: null,
  socket: null,
  snapshot: null,
};

const el = {
  accountId: document.getElementById('accountId'),
  displayName: document.getElementById('displayName'),
  characterId: document.getElementById('characterId'),
  preferredRole: document.getElementById('preferredRole'),
  templateSelect: document.getElementById('templateSelect'),
  activeRunSelect: document.getElementById('activeRunSelect'),
  createRunButton: document.getElementById('createRunButton'),
  joinRunButton: document.getElementById('joinRunButton'),
  connectionStatus: document.getElementById('connectionStatus'),
  currentRunLabel: document.getElementById('currentRunLabel'),
  runtimeMeta: document.getElementById('runtimeMeta'),
  roomTitle: document.getElementById('roomTitle'),
  roomDescription: document.getElementById('roomDescription'),
  beatBadge: document.getElementById('beatBadge'),
  tensionBadge: document.getElementById('tensionBadge'),
  exitList: document.getElementById('exitList'),
  actionList: document.getElementById('actionList'),
  propList: document.getElementById('propList'),
  occupantList: document.getElementById('occupantList'),
  transcript: document.getElementById('transcript'),
  naturalInput: document.getElementById('naturalInput'),
  naturalSubmitButton: document.getElementById('naturalSubmitButton'),
  sayText: document.getElementById('sayText'),
  emoteText: document.getElementById('emoteText'),
  inspectTarget: document.getElementById('inspectTarget'),
  sayButton: document.getElementById('sayButton'),
  emoteButton: document.getElementById('emoteButton'),
  inspectButton: document.getElementById('inspectButton'),
  lobbyPanel: document.getElementById('lobbyPanel'),
  lobbyStatus: document.getElementById('lobbyStatus'),
  lobbySeatList: document.getElementById('lobbySeatList'),
  readyButton: document.getElementById('readyButton'),
  unreadyButton: document.getElementById('unreadyButton'),
  startRunButton: document.getElementById('startRunButton'),
};

async function getJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

function selectedAccountId() {
  return el.accountId.value.trim() || 'local:guest-hollywood';
}

function selectedDisplayName() {
  return el.displayName.value.trim() || 'Hollywood';
}

function selectedCharacterId() {
  return el.characterId.value.trim() || null;
}

function setStatus(text) {
  el.connectionStatus.textContent = text;
}

function renderSelectOptions() {
  el.templateSelect.innerHTML = state.templates
    .map(template => `<option value="${template.id}">${template.title} — ${template.kind}</option>`)
    .join('');

  el.activeRunSelect.innerHTML = state.runs
    .map(run => `<option value="${run.id}">${run.template_title} | ${run.id} | ${run.status} | ready=${run.ready_human_seats} | open=${run.open_human_seats}</option>`)
    .join('');
}

function currentRoom() {
  if (!state.snapshot) return null;
  return state.snapshot.current_room || null;
}

function renderLobby(snapshot) {
  const lobby = snapshot.lobby;
  if (!lobby) {
    el.lobbyPanel.hidden = true;
    return;
  }
  el.lobbyPanel.hidden = false;
  el.lobbyStatus.textContent = `Lobby: ${lobby.occupied_human_seats}/${lobby.seats.length} seats occupied • ${lobby.ready_human_seats} ready • min start ${lobby.min_humans_to_start}`;
  el.lobbySeatList.innerHTML = lobby.seats.map(seat => `
    <div class="token token--stacked">
      <strong>${seat.role_display_name}</strong>
      <span class="small muted">role_id=${seat.role_id}</span>
      <span>${seat.occupant_display_name || 'Open seat'}</span>
      <span class="small muted">${seat.connected ? 'connected' : 'offline'} • ${seat.ready ? 'ready' : 'not ready'}</span>
    </div>
  `).join('') || '<span class="muted small">No lobby seats defined.</span>';

  const mySeat = lobby.seats.find(seat => seat.participant_id === snapshot.viewer_participant_id);
  const amReady = Boolean(mySeat && mySeat.ready);
  el.readyButton.disabled = !mySeat || amReady;
  el.unreadyButton.disabled = !mySeat || !amReady;
  el.startRunButton.disabled = !(snapshot.viewer_account_id && lobby.can_start);
}

function renderSnapshot(snapshot) {
  state.snapshot = snapshot;
  const room = currentRoom();
  el.currentRunLabel.textContent = `Run: ${snapshot.run_id} | Template: ${snapshot.template_title} | Role: ${snapshot.viewer_role_id}`;
  el.beatBadge.textContent = `Beat: ${snapshot.beat_id}`;
  el.tensionBadge.textContent = `Tension: ${snapshot.tension}`;
  el.runtimeMeta.textContent = `store=${snapshot.metadata.store_backend} • policy=${snapshot.join_policy} • status=${snapshot.status}`;

  renderLobby(snapshot);

  if (room) {
    el.roomTitle.textContent = room.name;
    el.roomDescription.textContent = room.description;

    el.exitList.innerHTML = room.exits.map(exit => `
      <div class="token">
        <span>${exit.label}</span>
        <button data-room="${exit.target_room_id}" class="move-button">Go</button>
      </div>
    `).join('') || '<span class="muted small">No exits from here.</span>';

    const visibleProps = room.props || [];
    el.propList.innerHTML = visibleProps.map(prop => `
      <div class="token">
        <span>${prop.name} <span class="small muted">(${prop.state})</span></span>
        <button data-inspect="${prop.id}" class="inspect-button">Inspect</button>
      </div>
    `).join('') || '<span class="muted small">No props in this room.</span>';

    const occupants = snapshot.visible_occupants || [];
    el.occupantList.innerHTML = occupants.map(occupant => `
      <div class="token">
        <span>${occupant.display_name}${occupant.is_self ? ' (you)' : ''}</span>
        <span class="small muted">${occupant.mode}</span>
      </div>
    `).join('') || '<span class="muted small">Nobody else is here.</span>';
  }

  el.actionList.innerHTML = snapshot.available_actions.map(action => `
    <div class="token">
      <span>${action.label}</span>
      <button data-action="${action.id}" class="action-button">Use</button>
    </div>
  `).join('') || '<span class="muted small">No scripted actions available here.</span>';

  el.transcript.innerHTML = snapshot.transcript_tail.map(entry => `
    <div class="entry">
      <div class="meta">${new Date(entry.at).toLocaleTimeString()}${entry.actor ? ` • ${entry.actor}` : ''}${entry.room_id ? ` • ${entry.room_id}` : ''}</div>
      <div class="text">${entry.text}</div>
    </div>
  `).join('');
  el.transcript.scrollTop = el.transcript.scrollHeight;

  wireDynamicButtons();
}

function wireDynamicButtons() {
  document.querySelectorAll('.move-button').forEach(button => {
    button.onclick = () => sendCommand({ action: 'move', target_room_id: button.dataset.room });
  });
  document.querySelectorAll('.action-button').forEach(button => {
    button.onclick = () => sendCommand({ action: 'use_action', action_id: button.dataset.action });
  });
  document.querySelectorAll('.inspect-button').forEach(button => {
    button.onclick = () => sendCommand({ action: 'inspect', target_id: button.dataset.inspect });
  });
}

function connectSocket(ticket) {
  if (state.socket) {
    state.socket.close();
  }
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  state.socket = new WebSocket(`${protocol}//${location.host}/ws?ticket=${encodeURIComponent(ticket)}`);
  setStatus('Connecting...');

  state.socket.onopen = () => setStatus('Connected');
  state.socket.onclose = () => setStatus('Disconnected');
  state.socket.onerror = () => setStatus('Socket error');
  state.socket.onmessage = event => {
    const payload = JSON.parse(event.data);
    if (payload.type === 'snapshot') {
      renderSnapshot(payload.data);
    }
    if (payload.type === 'command_rejected') {
      alert(payload.reason);
    }
  };
}

async function createRun() {
  const payload = {
    template_id: el.templateSelect.value,
    account_id: selectedAccountId(),
    display_name: selectedDisplayName(),
    character_id: selectedCharacterId(),
  };
  const result = await getJson('/api/runs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  state.currentRunId = result.run.id;
  await refreshRuns();
  await joinRun(result.run.id);
}

async function joinRun(runId = el.activeRunSelect.value) {
  const payload = {
    run_id: runId,
    account_id: selectedAccountId(),
    display_name: selectedDisplayName(),
    character_id: selectedCharacterId(),
    preferred_role_id: el.preferredRole.value.trim() || null,
  };
  const result = await getJson('/api/tickets', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  state.currentRunId = result.run_id;
  state.participantId = result.participant_id;
  connectSocket(result.ticket);
}

function sendCommand(payload) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    alert('Not connected yet.');
    return;
  }
  state.socket.send(JSON.stringify(payload));
}

async function refreshTemplates() {
  state.templates = await getJson('/api/templates');
  renderSelectOptions();
}

async function refreshRuns() {
  state.runs = await getJson('/api/runs');
  renderSelectOptions();
}

el.createRunButton.onclick = () => createRun().catch(err => alert(err.message));
el.joinRunButton.onclick = () => joinRun().catch(err => alert(err.message));
el.readyButton.onclick = () => sendCommand({ action: 'set_ready', ready: true });
el.unreadyButton.onclick = () => sendCommand({ action: 'set_ready', ready: false });
el.startRunButton.onclick = () => sendCommand({ action: 'start_run' });
el.naturalSubmitButton.onclick = () => {
  const text = el.naturalInput.value.trim();
  if (text) {
    sendCommand({ player_input: text });
    el.naturalInput.value = '';
  }
};
el.sayButton.onclick = () => {
  const text = el.sayText.value.trim();
  if (text) {
    sendCommand({ action: 'say', text });
    el.sayText.value = '';
  }
};
el.emoteButton.onclick = () => {
  const text = el.emoteText.value.trim();
  if (text) {
    sendCommand({ action: 'emote', text });
    el.emoteText.value = '';
  }
};
el.inspectButton.onclick = () => {
  const text = el.inspectTarget.value.trim();
  if (text) {
    sendCommand({ action: 'inspect', target_id: text });
    el.inspectTarget.value = '';
  }
};

(async function bootstrap() {
  el.accountId.value = 'local:hollywood';
  el.displayName.value = 'Hollywood';
  el.characterId.value = 'char:hollywood:visitor';
  try {
    await refreshTemplates();
    await refreshRuns();
    setInterval(refreshRuns, 5000);
  } catch (err) {
    console.error(err);
    alert(err.message);
  }
})();
