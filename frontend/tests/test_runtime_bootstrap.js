/**
 * Unit tests for PlayRuntimeBootstrap.
 */

describe('PlayRuntimeBootstrap', () => {
  const bootstrap = () => window.PlayRuntimeBootstrap;

  test('builds a DOS boot block with the Director command', () => {
    const block = bootstrap().buildDosBootBlock({
      module_id: 'god_of_carnage',
      runtime_session_id: 'runtime-session-1234567890',
      runtime_session_ready: true,
      can_execute: true,
      shell_state_view: {
        status: 'runtime_engine_initialized',
        current_scene_id: 'scene_1_opening',
        runtime_world: {
          status: 'initialized',
          room_count: 3,
          prop_count: 9,
          actor_count: 4,
        },
      },
      visible_scene_output: {
        blocks: [{ id: 'story-1', block_type: 'narrator', text: 'Story.' }],
      },
    });

    expect(block.id).toBe('runtime-dos-boot');
    expect(block.block_type).toBe('system_boot');
    expect(block.narration_beat).toBe('boot');
    expect(block.text).toContain('C:\\WOS> START DIRECTOR_TICK');
    expect(block.text).toContain('CAPABILITY DISPATCHER');
    expect(block.text).toContain('C:\\WOS> RUN');
    expect(block.delivery.characters_per_second).toBe(220);
    expect(block.delivery.max_duration_ms).toBe(10000);
  });

  test('keeps the BIOS boot text but avoids slow ASCII punctuation leaders', () => {
    const block = bootstrap().buildDosBootBlock({
      module_id: 'god_of_carnage',
      runtime_session_id: 'runtime-session-1234567890',
      runtime_session_ready: true,
      can_execute: true,
      shell_state_view: {
        status: 'runtime_engine_initialized',
        current_scene_id: 'scene_1_opening',
        runtime_world: {
          status: 'initialized',
          room_count: 3,
          prop_count: 9,
          actor_count: 4,
        },
      },
      visible_scene_output: {
        blocks: [{ id: 'story-1', block_type: 'narrator', text: 'Story.' }],
      },
    });

    expect(block.text).not.toContain('................');
    expect(block.text).toContain('RUNTIME SESSION··');
    expect(block.text).toContain('DIRECTOR CONTEXT FRAME··');
    expect(block.text).toContain('CAPABILITY PLAN··');
    expect(window.TYPEWRITER_BEAT_PROFILES.default.cps).toBe(44);
    expect(window.TYPEWRITER_BEAT_PROFILES.boot.cps).toBe(76);
  });

  test('prepends the boot block and starts the typewriter slice at zero', () => {
    const original = {
      visible_scene_output: {
        typewriter_slice_start_index: 1,
        blocks: [{ id: 'story-1', block_type: 'narrator', text: 'Story.' }],
      },
    };

    const wrapped = bootstrap().withDosBootPayload(original);

    expect(wrapped).not.toBe(original);
    expect(original.visible_scene_output.blocks).toHaveLength(1);
    expect(wrapped.visible_scene_output.typewriter_slice_start_index).toBe(0);
    expect(wrapped.visible_scene_output.blocks).toHaveLength(2);
    expect(wrapped.visible_scene_output.blocks[0].block_type).toBe('system_boot');
    expect(wrapped.visible_scene_output.blocks[1].id).toBe('story-1');
  });

  test('does not duplicate an existing boot block', () => {
    const payload = {
      visible_scene_output: {
        blocks: [
          { id: 'runtime-dos-boot', block_type: 'system_boot', text: 'Boot.' },
          { id: 'story-1', block_type: 'narrator', text: 'Story.' },
        ],
      },
    };

    const wrapped = bootstrap().withDosBootPayload(payload);

    expect(wrapped.visible_scene_output.blocks).toHaveLength(2);
    expect(wrapped.visible_scene_output.blocks[0].id).toBe('runtime-dos-boot');
  });

  test('can be disabled by bootstrap mode', () => {
    expect(bootstrap().shouldUseDosBoot({ bootstrap_mode: 'plain' })).toBe(false);
    expect(bootstrap().shouldUseDosBoot({ play_shell_bootstrap_mode: 'off' })).toBe(false);
    expect(bootstrap().shouldUseDosBoot({})).toBe(true);
  });

  test('does not treat the UI liveness probe as an open narrative channel', () => {
    const block = bootstrap().buildDosBootBlock({
      module_id: 'god_of_carnage',
      runtime_session_ready: false,
      can_execute: false,
      visible_scene_output: {
        blocks: [
          {
            id: 'typewriter-ui-liveness-probe',
            block_type: 'narrator',
            text: 'Typewriter-Test: Die UI-Shell lebt.',
          },
        ],
      },
    });

    expect(block.text).toMatch(/OPENING READINESS·+WAITING/);
    expect(block.text).toMatch(/NARRATIVE CHANNEL·+WAITING/);
  });

  test('uses session-loop runtime world counts for boot readiness lines', () => {
    const block = bootstrap().buildDosBootBlock({
      module_id: 'god_of_carnage',
      runtime_session_ready: true,
      can_execute: true,
      session_loop: {
        status: 'runtime_engine_initialized',
        runtime_world: {
          status: 'initialized',
          room_count: 5,
          prop_count: 11,
          actor_count: 4,
        },
      },
      visible_scene_output: {
        blocks: [{ id: 'story-1', block_type: 'narrator', text: 'Story.' }],
      },
    });

    expect(block.text).toContain('LOCATION MODEL····················READY');
    expect(block.text).toContain('OBJECT MODEL······················READY');
    expect(block.text).toContain('NPC PRESENCE······················PRESENT');
  });
});
