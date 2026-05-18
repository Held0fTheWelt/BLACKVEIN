/**
 * PlayRuntimeBootstrap - shell-owned startup diagnostics.
 *
 * This module builds the DOS-like boot block that runs before the first
 * Director-owned narrative block. It is intentionally not a story beat.
 */
(function () {
  const BOOT_BLOCK_ID = 'runtime-dos-boot';
  const BOOT_BLOCK_TYPE = 'system_boot';

  function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : null;
  }

  function getPath(root, path) {
    let current = root;
    for (const key of path) {
      if (!asObject(current) && !Array.isArray(current)) {
        return undefined;
      }
      current = current[key];
      if (current === undefined || current === null) {
        return current;
      }
    }
    return current;
  }

  function firstValue(root, paths) {
    for (const path of paths) {
      const value = getPath(root, path);
      if (value !== undefined && value !== null && value !== '') {
        return value;
      }
    }
    return undefined;
  }

  function firstObject(root, paths) {
    const value = firstValue(root, paths);
    return asObject(value) || {};
  }

  function visibleSceneOutput(payload) {
    const root = asObject(payload) || {};
    const direct = asObject(root.visible_scene_output);
    if (direct) return direct;
    const nested = asObject(getPath(root, ['data', 'visible_scene_output']));
    return nested || null;
  }

  function visibleBlocks(payload) {
    const vso = visibleSceneOutput(payload);
    return vso && Array.isArray(vso.blocks) ? vso.blocks : [];
  }

  function hasDosBootBlock(blocks) {
    return Array.isArray(blocks) && blocks.some((block) => (
      asObject(block)
      && (block.id === BOOT_BLOCK_ID || String(block.block_type || '').toLowerCase() === BOOT_BLOCK_TYPE)
    ));
  }

  function isPlayerVisibleNarrativeBlock(block) {
    const item = asObject(block);
    if (!item) return false;
    const kind = String(item.block_type || '').trim().toLowerCase();
    if (!kind || kind === BOOT_BLOCK_TYPE || kind === 'system_meta') return false;
    if (kind.startsWith('diagnostic') || kind.startsWith('debug')) return false;
    if (item.id === 'typewriter-ui-liveness-probe') return false;
    const text = String(item.player_display_text != null ? item.player_display_text : item.text || '').trim();
    return text.length > 0;
  }

  function visibleNarrativeBlocks(payload) {
    return visibleBlocks(payload).filter(isPlayerVisibleNarrativeBlock);
  }

  function numberValue(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function statusFromBool(value, ready, falseStatus, unknown) {
    if (value === true) return ready;
    if (value === false) return falseStatus;
    return unknown;
  }

  function statusFromCount(value, positive, zero, unknown) {
    const n = numberValue(value);
    if (n === null) return unknown;
    return n > 0 ? positive : zero;
  }

  function shortId(value) {
    const text = String(value || '').trim();
    if (!text) return 'UNBOUND';
    if (text.length <= 18) return text.toUpperCase();
    return `${text.slice(0, 8)}··${text.slice(-6)}`.toUpperCase();
  }

  function bootLine(label, status) {
    const cleanLabel = String(label || '').trim().toUpperCase();
    const cleanStatus = String(status || 'STANDBY').trim().toUpperCase();
    return `${cleanLabel.padEnd(34, '·')}${cleanStatus}`;
  }

  function selectedCapabilityCount(plan) {
    const capabilityPlan = asObject(plan) || {};
    const candidates = [
      capabilityPlan.selected_capabilities,
      capabilityPlan.run_only,
      capabilityPlan.capabilities,
      capabilityPlan.dispatch_list,
    ];
    for (const candidate of candidates) {
      if (Array.isArray(candidate)) return candidate.length;
    }
    return 0;
  }

  function buildContext(payload) {
    const root = asObject(payload) || {};
    const shellState = firstObject(root, [['shell_state_view'], ['data', 'shell_state_view']]);
    const sessionLoop = firstObject(root, [['session_loop'], ['data', 'session_loop']]);
    const runtimeWorld = firstObject(root, [
      ['shell_state_view', 'runtime_world'],
      ['data', 'shell_state_view', 'runtime_world'],
      ['session_loop', 'runtime_world'],
      ['data', 'session_loop', 'runtime_world'],
      ['authoritative_state', 'runtime_world'],
      ['data', 'authoritative_state', 'runtime_world'],
    ]);
    const scenePlan = firstObject(root, [
      ['scene_plan_record'],
      ['data', 'scene_plan_record'],
      ['turn', 'scene_plan_record'],
      ['turn', 'scene_plan'],
      ['data', 'turn', 'scene_plan_record'],
      ['data', 'turn', 'scene_plan'],
    ]);
    const capabilityPlan = firstObject(root, [
      ['capability_manager_plan'],
      ['data', 'capability_manager_plan'],
      ['turn', 'capability_manager_plan'],
      ['data', 'turn', 'capability_manager_plan'],
      ['scene_plan_record', 'capability_manager_plan'],
      ['turn', 'scene_plan_record', 'capability_manager_plan'],
      ['turn', 'scene_plan', 'capability_manager_plan'],
    ]);
    const blocks = visibleNarrativeBlocks(root);
    const storyEntries = Array.isArray(root.story_entries) ? root.story_entries : [];
    return {
      moduleId: firstValue(root, [['module_id'], ['data', 'module_id'], ['shell_state_view', 'module_id']]),
      sessionId: firstValue(root, [['runtime_session_id'], ['world_engine_story_session_id'], ['backend_session_id']]),
      sceneId: firstValue(root, [['current_scene_id'], ['shell_state_view', 'current_scene_id'], ['data', 'shell_state_view', 'current_scene_id']]),
      runtimeSessionReady: firstValue(root, [['runtime_session_ready'], ['data', 'runtime_session_ready']]),
      canExecute: firstValue(root, [['can_execute'], ['data', 'can_execute']]),
      openingStatus: firstValue(root, [['opening_generation_status'], ['data', 'opening_generation_status']]),
      sessionLoop,
      shellState,
      runtimeWorld,
      scenePlan,
      capabilityPlan,
      selectedCapabilityCount: selectedCapabilityCount(capabilityPlan),
      blockCount: blocks.length,
      storyEntryCount: storyEntries.length,
    };
  }

  function buildDosBootLines(payload) {
    const ctx = buildContext(payload);
    const roomCount = ctx.runtimeWorld.room_count;
    const propCount = ctx.runtimeWorld.prop_count;
    const actorCount = ctx.runtimeWorld.actor_count;
    const actorNumber = numberValue(actorCount);
    const npcPresence = actorNumber === null
      ? 'PENDING'
      : actorNumber > 1
        ? 'PRESENT'
        : actorNumber === 1
          ? 'LOW'
          : 'EMPTY';
    const runtimeWorldStatus = String(ctx.runtimeWorld.status || ctx.shellState.status || '').toLowerCase();
    const managerReady = runtimeWorldStatus === 'initialized'
      || ctx.shellState.status === 'runtime_engine_initialized'
      || ctx.runtimeSessionReady === true;
    const capabilityPlanReady = Object.keys(ctx.capabilityPlan).length > 0;
    const directorFrameReady = Object.keys(ctx.scenePlan).length > 0 || Object.keys(ctx.shellState).length > 0;
    const openingStatus = String(ctx.openingStatus || '').toLowerCase();
    const narrativeReady = ctx.blockCount > 0 || ctx.storyEntryCount > 0;
    const openingReady = openingStatus === 'committed'
      || openingStatus === 'ready'
      || openingStatus === 'ready_with_opening'
      || narrativeReady;

    return [
      'WORLD OF SHADOWS RUNTIME BIOS',
      `MODULE ${ctx.moduleId || 'UNBOUND'}`,
      `SESSION ${shortId(ctx.sessionId)}`,
      '',
      'C:\\WOS> START DIRECTOR_TICK',
      '',
      'WARMING SYSTEMS',
      bootLine('Runtime session', statusFromBool(ctx.runtimeSessionReady, 'READY', 'DEGRADED', 'STANDBY')),
      bootLine('Session loop', Object.keys(ctx.sessionLoop).length > 0 ? 'READY' : 'STANDBY'),
      bootLine('System manager', managerReady ? 'ONLINE' : 'STANDBY'),
      bootLine('Content authority', ctx.moduleId ? 'BOUND' : 'STANDBY'),
      bootLine('Canonical path', ctx.moduleId ? 'BOUND' : 'PENDING'),
      bootLine('Scene graph', ctx.sceneId ? 'READY' : 'PENDING'),
      bootLine('Location model', statusFromCount(roomCount, 'READY', 'EMPTY', 'PENDING')),
      bootLine('Object model', statusFromCount(propCount, 'READY', 'EMPTY', 'PENDING')),
      bootLine('NPC presence', npcPresence),
      bootLine('Capability manager', capabilityPlanReady ? 'ONLINE' : 'STANDBY'),
      bootLine('Capability dispatcher', ctx.selectedCapabilityCount > 0 ? 'ARMED' : 'STANDBY'),
      bootLine('Validation manager', statusFromBool(ctx.canExecute, 'READY', 'HOLD', 'STANDBY')),
      bootLine('Commit seam', narrativeReady ? 'READY' : 'STANDBY'),
      '',
      'DIRECTOR HANDOFF',
      bootLine('Director context frame', directorFrameReady ? 'BUILT' : 'PENDING'),
      bootLine('Opening readiness', openingReady ? 'READY' : 'WAITING'),
      bootLine('Capability plan', ctx.selectedCapabilityCount > 0 ? 'SELECTED' : 'PENDING'),
      bootLine('Narrative channel', narrativeReady ? 'OPEN' : 'WAITING'),
      '',
      'C:\\WOS> RUN',
    ];
  }

  function buildDosBootBlock(payload, options) {
    const opts = asObject(options) || {};
    const text = buildDosBootLines(payload).join('\n');
    return {
      id: opts.id || BOOT_BLOCK_ID,
      block_type: BOOT_BLOCK_TYPE,
      card_style: 'runtime_boot',
      narration_beat: 'boot',
      runtime_boot: true,
      text,
      player_display_text: text,
      delivery: {
        mode: 'typewriter',
        characters_per_second: numberValue(opts.characters_per_second) || 220,
        max_duration_ms: 10000,
      },
    };
  }

  function shouldUseDosBoot(payload) {
    const root = asObject(payload) || {};
    const mode = String(
      root.play_shell_bootstrap_mode
      || root.bootstrap_mode
      || root.dos_boot_mode
      || ''
    ).trim().toLowerCase();
    return mode !== 'off' && mode !== 'plain' && mode !== 'disabled';
  }

  function withDosBootPayload(payload, options) {
    const root = asObject(payload) || {};
    const blocks = visibleBlocks(root);
    if (hasDosBootBlock(blocks)) {
      return root;
    }

    const sourceVso = visibleSceneOutput(root) || {};
    const bootBlock = buildDosBootBlock(root, options);
    const nextVso = Object.assign({}, sourceVso, {
      blocks: [bootBlock].concat(blocks),
      typewriter_slice_start_index: 0,
    });
    const next = Object.assign({}, root, {
      visible_scene_output: nextVso,
      play_shell_bootstrap: Object.assign({}, asObject(root.play_shell_bootstrap) || {}, {
        dos_boot: true,
      }),
    });
    if (asObject(root.data)) {
      next.data = Object.assign({}, root.data, {
        visible_scene_output: nextVso,
      });
    }
    return next;
  }

  const api = {
    BOOT_BLOCK_ID,
    BOOT_BLOCK_TYPE,
    buildDosBootBlock,
    buildDosBootLines,
    shouldUseDosBoot,
    withDosBootPayload,
  };

  if (typeof window !== 'undefined') {
    window.PlayRuntimeBootstrap = api;
  }
})();
