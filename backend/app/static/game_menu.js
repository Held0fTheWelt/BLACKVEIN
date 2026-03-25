const state = {
  profile: null,
  playService: null,
  templates: [],
  runs: [],
  characters: [],
  saveSlots: [],
  currentRunId: null,
  participantId: null,
  socket: null,
  snapshot: null,
};

const config = window.WOS_GAME_CONFIG || {};
const apiBase = (config.apiBase || '/api/v1/game').replace(/\/$/, '');

const el = {
  characterSelect: document.getElementById('gameCharacterSelect'),
  displayName: document.getElementById('gameDisplayName'),
  preferredRole: document.getElementById('gamePreferredRole'),
  characterMeta: document.getElementById('characterMeta'),
  newCharacterName: document.getElementById('newCharacterName'),
  newCharacterDisplayName: document.getElementById('newCharacterDisplayName'),
  newCharacterBio: document.getElementById('newCharacterBio'),
  createCharacterButton: document.getElementById('createCharacterButton'),
  setDefaultCharacterButton: document.getElementById('setDefaultCharacterButton'),
  archiveCharacterButton: document.getElementById('archiveCharacterButton'),
  templateSelect: document.getElementById('templateSelect'),
  activeRunSelect: document.getElementById('activeRunSelect'),
  saveSlotSelect: document.getElementById('saveSlotSelect'),
  createRunButton: document.getElementById('createRunButton'),
  joinRunButton: document.getElementById('joinRunButton'),
  saveCurrentRunButton: document.getElementById('saveCurrentRunButton'),
  loadSavedRunButton: document.getElementById('loadSavedRunButton'),
  deleteSaveSlotButton: document.getElementById('deleteSaveSlotButton'),
  connectionStatus: document.getElementById('connectionStatus'),
  currentRunLabel: document.getElementById('currentRunLabel'),
  roomTitle: document.getElementById('roomTitle'),
  roomDescription: document.getElementById('roomDescription'),
  beatBadge: document.getElementById('beatBadge'),
  tensionBadge: document.getElementById('tensionBadge'),
  exitList: document.getElementById('exitList'),
  actionList: document.getElementById('actionList'),
  propList: document.getElementById('propList'),
  occupantList: document.getElementById('occupantList'),
  transcript: document.getElementById('transcript'),
  sayText: document.getElementById('sayText'),
  emoteText: document.getElementById('emoteText'),
  inspectTarget: document.getElementById('inspectTarget'),
  sayButton: document.getElementById('sayButton'),
  emoteButton: document.getElementById('emoteButton'),
  inspectButton: document.getElementById('inspectButton'),
};

async function getJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.detail || `Request failed: ${response.status}`);
  }
  return data;
}

function escapeHtml(s) {
  if (s == null) return '';
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

function setStatus(text) {
  el.connectionStatus.textContent = text;
}

function selectedCharacter() {
  const raw = el.characterSelect.value;
  if (!raw) return null;
  return state.characters.find(character => String(character.id) === String(raw)) || null;
}

function selectedSaveSlot() {
  const raw = el.saveSlotSelect.value;
  if (!raw) return null;
  return state.saveSlots.find(slot => String(slot.id) === String(raw)) || null;
}

function getCharacterPayload() {
  const character = selectedCharacter();
  return {
    display_name: el.displayName.value.trim() || state.profile?.default_display_name || 'Player',
    character_id: character ? String(character.id) : null,
    character_name: character ? character.name : null,
    preferred_role_id: el.preferredRole.value.trim() || null,
  };
}

function currentRoom() {
  if (!state.snapshot) return null;
  return state.snapshot.rooms.find(room => room.id === state.snapshot.viewer_room_id) || null;
}

function renderTokenButtonList(container, items, emptyText) {
  container.innerHTML = items.length ? items.join('') : `<div class="muted">${emptyText}</div>`;
}

function renderCharacterMeta() {
  const character = selectedCharacter();
  if (!character) {
    el.characterMeta.textContent = 'No character selected. Fallback display name will be used.';
    return;
  }
  const pieces = [];
  if (character.display_name) pieces.push(`Display: ${character.display_name}`);
  if (character.is_default) pieces.push('Default');
  if (character.bio) pieces.push(character.bio);
  el.characterMeta.textContent = pieces.join(' • ') || 'Character ready.';
}

function renderSelectOptions() {
  el.characterSelect.innerHTML = [
    '<option value="">No stored character (use fallback display name)</option>',
    ...state.characters.map(character => `<option value="${character.id}">${escapeHtml(character.display_name)} — ${escapeHtml(character.name)}${character.is_default ? ' [default]' : ''}</option>`),
  ].join('');

  const defaultCharacter = state.characters.find(character => character.is_default) || state.characters[0] || null;
  if (defaultCharacter && !el.characterSelect.value) {
    el.characterSelect.value = String(defaultCharacter.id);
  }

  el.templateSelect.innerHTML = state.templates
    .map(template => `<option value="${template.id}">${template.title} — ${template.kind_label || template.kind}</option>`)
    .join('');

  el.activeRunSelect.innerHTML = state.runs.length
    ? state.runs.map(run => `<option value="${run.id}">${run.template_title} | ${run.id} | beat=${run.beat_id} | humans=${run.total_humans}</option>`).join('')
    : '<option value="">No active runs</option>';

  el.saveSlotSelect.innerHTML = state.saveSlots.length
    ? state.saveSlots.map(slot => `<option value="${slot.id}">${slot.title} | ${slot.template_title || slot.template_id} | ${slot.run_id || 'no run linked yet'}</option>`).join('')
    : '<option value="">No save slots yet</option>';

  renderCharacterMeta();
}

function renderSnapshot(snapshot) {
  state.snapshot = snapshot;
  const room = currentRoom();
  el.currentRunLabel.textContent = `Run: ${snapshot.run_id} | Template: ${snapshot.template_title} | Role: ${snapshot.viewer_role_id}`;
  el.beatBadge.textContent = `Beat: ${snapshot.beat_id}`;
  el.tensionBadge.textContent = `Tension: ${snapshot.tension}`;

  if (room) {
    el.roomTitle.textContent = room.name;
    el.roomDescription.textContent = room.description;

    renderTokenButtonList(
      el.exitList,
      room.exits.map(exit => `
        <div style="display:flex; justify-content:space-between; align-items:center; gap:0.75rem; margin-bottom:0.5rem;">
          <span>${escapeHtml(exit.label)}</span>
          <button data-room="${exit.target_room_id}" class="move-button btn">Go</button>
        </div>`),
      'No exits from here.'
    );

    const visibleProps = room.props || [];
    renderTokenButtonList(
      el.propList,
      visibleProps.map(prop => `
        <div style="display:flex; justify-content:space-between; align-items:center; gap:0.75rem; margin-bottom:0.5rem;">
          <span>${escapeHtml(prop.name)} <small>(${escapeHtml(prop.state)})</small></span>
          <button data-inspect="${prop.id}" class="inspect-button btn">Inspect</button>
        </div>`),
      'No props in this room.'
    );

    const occupants = snapshot.room_occupants[room.id] || [];
    renderTokenButtonList(
      el.occupantList,
      occupants.map(occupant => `
        <div style="display:flex; justify-content:space-between; align-items:center; gap:0.75rem; margin-bottom:0.5rem;">
          <span>${escapeHtml(occupant.display_name)}</span>
          <small>${occupant.mode}</small>
        </div>`),
      'Nobody else is here.'
    );
  }

  renderTokenButtonList(
    el.actionList,
    snapshot.available_actions.map(action => `
      <div style="display:flex; justify-content:space-between; align-items:center; gap:0.75rem; margin-bottom:0.5rem;">
        <span>${escapeHtml(action.label)}</span>
        <button data-action="${action.id}" class="action-button btn">Use</button>
      </div>`),
    'No scripted actions available here.'
  );

  el.transcript.innerHTML = snapshot.transcript_tail.map(entry => `
    <div>
      <div style="font-size:0.8rem; opacity:0.75;">${new Date(entry.at).toLocaleTimeString()}${entry.actor ? ` • ${escapeHtml(entry.actor)}` : ''}</div>
      <div>${escapeHtml(entry.text)}</div>
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

function connectSocket(ticketResponse) {
  if (state.socket) {
    state.socket.close();
  }
  const wsBaseUrl = (ticketResponse.ws_base_url || state.playService?.ws_base_url || '').replace(/\/$/, '');
  if (!wsBaseUrl) {
    throw new Error('Missing ws_base_url from backend ticket response.');
  }
  state.socket = new WebSocket(`${wsBaseUrl}/ws?ticket=${encodeURIComponent(ticketResponse.ticket)}`);
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

async function refreshBootstrap() {
  const payload = await getJson(`${apiBase}/bootstrap`);
  state.profile = payload.profile || null;
  state.playService = payload.play_service || null;
  state.templates = payload.templates || [];
  state.runs = payload.runs || [];
  state.characters = payload.characters || [];
  state.saveSlots = payload.save_slots || [];
  renderSelectOptions();
}

async function createCharacter() {
  const payload = {
    name: el.newCharacterName.value.trim(),
    display_name: el.newCharacterDisplayName.value.trim() || null,
    bio: el.newCharacterBio.value.trim() || null,
    is_default: state.characters.length === 0,
  };
  const result = await getJson(`${apiBase}/characters`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  el.newCharacterName.value = '';
  el.newCharacterDisplayName.value = '';
  el.newCharacterBio.value = '';
  await refreshBootstrap();
  el.characterSelect.value = String(result.character.id);
  renderCharacterMeta();
}

async function setDefaultCharacter() {
  const character = selectedCharacter();
  if (!character) {
    alert('Select a character first.');
    return;
  }
  await getJson(`${apiBase}/characters/${character.id}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_default: true }),
  });
  await refreshBootstrap();
  el.characterSelect.value = String(character.id);
}

async function archiveCharacter() {
  const character = selectedCharacter();
  if (!character) {
    alert('Select a character first.');
    return;
  }
  await getJson(`${apiBase}/characters/${character.id}`, { method: 'DELETE' });
  await refreshBootstrap();
}

async function createRun() {
  const result = await getJson(`${apiBase}/runs`, {
    method: 'POST',
    body: JSON.stringify({
      template_id: el.templateSelect.value,
      ...getCharacterPayload(),
    }),
  });
  state.currentRunId = result.run.id;
  await refreshBootstrap();
  await joinRun(result.run.id);
}

async function joinRun(runId = el.activeRunSelect.value) {
  if (!runId) {
    alert('Select a run first.');
    return;
  }
  const result = await getJson(`${apiBase}/tickets`, {
    method: 'POST',
    body: JSON.stringify({
      run_id: runId,
      ...getCharacterPayload(),
    }),
  });
  state.currentRunId = result.run_id;
  state.participantId = result.participant_id;
  connectSocket(result);
}

function makeSlotKeyFromRun(runId) {
  return `${runId || 'run'}-${Date.now()}`.toLowerCase();
}

async function saveCurrentRun() {
  if (!state.currentRunId) {
    alert('Join or create a run first.');
    return;
  }
  const currentTemplate = state.templates.find(template => template.id === (state.snapshot?.template_id || ''))
    || state.templates.find(template => template.id === el.templateSelect.value)
    || null;
  const slotTitle = window.prompt('Save slot title', currentTemplate ? `${currentTemplate.title} checkpoint` : 'Scene checkpoint');
  if (!slotTitle) {
    return;
  }
  const character = selectedCharacter();
  await getJson(`${apiBase}/save-slots`, {
    method: 'POST',
    body: JSON.stringify({
      slot_key: makeSlotKeyFromRun(state.currentRunId),
      title: slotTitle,
      template_id: currentTemplate?.id || state.snapshot?.template_id || el.templateSelect.value,
      template_title: currentTemplate?.title || state.snapshot?.template_title || null,
      run_id: state.currentRunId,
      kind: currentTemplate?.kind || null,
      character_id: character ? character.id : null,
      metadata: {
        beat_id: state.snapshot?.beat_id || null,
        tension: state.snapshot?.tension || null,
      },
    }),
  });
  await refreshBootstrap();
}

async function joinSavedRun() {
  const slot = selectedSaveSlot();
  if (!slot || !slot.run_id) {
    alert('Select a save slot with a linked run.');
    return;
  }
  await joinRun(slot.run_id);
}

async function deleteSaveSlot() {
  const slot = selectedSaveSlot();
  if (!slot) {
    alert('Select a save slot first.');
    return;
  }
  await getJson(`${apiBase}/save-slots/${slot.id}`, { method: 'DELETE' });
  await refreshBootstrap();
}

function sendCommand(payload) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    alert('Not connected yet.');
    return;
  }
  state.socket.send(JSON.stringify(payload));
}

el.characterSelect.onchange = () => renderCharacterMeta();
el.createCharacterButton.onclick = () => createCharacter().catch(err => alert(err.message));
el.setDefaultCharacterButton.onclick = () => setDefaultCharacter().catch(err => alert(err.message));
el.archiveCharacterButton.onclick = () => archiveCharacter().catch(err => alert(err.message));
el.createRunButton.onclick = () => createRun().catch(err => alert(err.message));
el.joinRunButton.onclick = () => joinRun().catch(err => alert(err.message));
el.saveCurrentRunButton.onclick = () => saveCurrentRun().catch(err => alert(err.message));
el.loadSavedRunButton.onclick = () => joinSavedRun().catch(err => alert(err.message));
el.deleteSaveSlotButton.onclick = () => deleteSaveSlot().catch(err => alert(err.message));
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
  if (!config.playServiceConfigured) {
    setStatus('Play service not configured');
  }
  try {
    await refreshBootstrap();
    setInterval(refreshBootstrap, 5000);
  } catch (err) {
    console.error(err);
    alert(err.message);
  }
})();
