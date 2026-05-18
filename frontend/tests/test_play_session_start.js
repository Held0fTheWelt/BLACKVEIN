const fs = require('fs');
const path = require('path');

function loadStaticScript(filename) {
  const full = path.join(__dirname, '..', 'static', filename);
  const code = fs.readFileSync(full, 'utf8');
  // eslint-disable-next-line no-eval
  eval(code);
}

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function renderLauncherDom() {
  document.body.innerHTML = `
    <form method="post" action="/play/start" id="play-launcher-form">
      <select name="template_id" id="template-select" required>
        <option value="god_of_carnage_solo" selected>God of Carnage</option>
      </select>
      <select name="selected_player_role" id="role-select">
        <option value="annette" selected>Annette</option>
      </select>
      <select name="session_output_language" id="session-output-language">
        <option value="de" selected>Deutsch</option>
      </select>
      <button type="submit">Create run</button>
      <span id="play-launcher-status" role="status"></span>
    </form>
  `;
  const form = document.getElementById('play-launcher-form');
  form.reportValidity = jest.fn(() => true);
  return form;
}

describe('PlaySessionStart', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    delete global.fetch;
    delete window.fetch;
    jest.restoreAllMocks();
  });

  test('fast-creates the session with skipped opening and redirects later', () => {
    const form = renderLauncherDom();
    global.fetch = jest.fn(() => new Promise(() => {}));
    window.fetch = global.fetch;

    loadStaticScript('play_session_start.js');
    const event = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(new URL(fetch.mock.calls[0][0], window.location.origin).pathname).toBe('/play/start');
    expect(fetch.mock.calls[0][1].headers.Accept).toBe('application/json');
    expect(fetch.mock.calls[0][1].body.get('template_id')).toBe('god_of_carnage_solo');
    expect(fetch.mock.calls[0][1].body.get('skip_graph_opening_on_create')).toBe('1');
    expect(document.getElementById('play-launcher-status').textContent).toBe('Starting session...');
    expect(form.elements.template_id.disabled).toBe(true);
  });
});

describe('Play shell delayed opening generation', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    delete window.TEST_MODE;
    delete global.fetch;
    delete window.fetch;
    jest.restoreAllMocks();
  });

  function renderShellDom() {
    document.body.innerHTML = `
      <div class="play-shell" data-session-id="run-1" data-runtime-session-id="story-1">
        <div id="turn-transcript"></div>
        <form id="play-execute-form" method="post" action="/play/run-1/execute">
          <textarea id="player-input" disabled></textarea>
          <button type="submit" id="execute-turn-btn" disabled>Submit turn</button>
          <span id="execute-status" role="status"></span>
        </form>
      </div>
      <script type="application/json" id="play-shell-bootstrap">
        {
          "run_id": "run-1",
          "module_id": "god_of_carnage",
          "runtime_session_id": "story-1",
          "runtime_session_ready": false,
          "can_execute": false,
          "opening_generation_status": "pending",
          "opening_present": false,
          "visible_scene_output": { "blocks": [], "typewriter_slice_start_index": 0 },
          "story_entries": []
        }
      </script>
    `;
  }

  test('requests the opening from inside the play shell while the boot block is displayed', () => {
    window.TEST_MODE = true;
    renderShellDom();
    global.fetch = jest.fn(() => new Promise(() => {}));
    window.fetch = global.fetch;

    loadStaticScript('play_shell.js');

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(new URL(fetch.mock.calls[0][0], window.location.origin).pathname).toBe('/play/run-1/opening');
    expect(document.querySelector('[data-block-type="system_boot"]')).not.toBeNull();
    expect(document.getElementById('execute-status').textContent).toBe('Generating opening...');
  });

  test('keeps the completed boot stable and types the opening once generation returns', async () => {
    window.TEST_MODE = true;
    renderShellDom();
    const openingPayload = {
      ok: true,
      run_id: 'run-1',
      module_id: 'god_of_carnage',
      runtime_session_id: 'story-1',
      runtime_session_ready: true,
      can_execute: true,
      opening_generation_status: 'ready_with_opening',
      opening_present: true,
      visible_scene_output: {
        typewriter_slice_start_index: 0,
        blocks: [
          { id: 'opening-1', block_type: 'narrator', text: 'The room waits.' },
        ],
      },
      story_entries: [],
    };
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve(openingPayload),
    }));
    window.fetch = global.fetch;
    const loadTurnSpy = jest.spyOn(window.BlocksOrchestrator.prototype, 'loadTurn');

    loadStaticScript('play_shell.js');
    await flushPromises();

    expect(loadTurnSpy).toHaveBeenCalledTimes(1);
    document.dispatchEvent(new CustomEvent('play-cinematic-idle', {}));
    await flushPromises();

    expect(loadTurnSpy).toHaveBeenCalledTimes(2);
    const finalPayload = loadTurnSpy.mock.calls[1][0];
    expect(finalPayload.visible_scene_output.typewriter_slice_start_index).toBe(1);
    expect(finalPayload.visible_scene_output.blocks[0].block_type).toBe('system_boot');
    expect(finalPayload.visible_scene_output.blocks[1].id).toBe('opening-1');
    expect(document.getElementById('player-input').disabled).toBe(false);
    expect(document.getElementById('execute-turn-btn').disabled).toBe(false);
  });
});
