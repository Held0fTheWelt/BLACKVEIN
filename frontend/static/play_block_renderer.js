/**
 * BlockRenderer — Pure DOM rendering for scene blocks
 *
 * Responsibility: Create one DOM element per scene block with appropriate data attributes.
 * No state management, no orchestration—just rendering.
 */

class BlockRenderer {
  constructor(domRoot) {
    this.dom_root = domRoot;
  }

  _isDiagnosticsBlock(blockType) {
    const kind = String(blockType || '').toLowerCase();
    return kind.startsWith('diagnostic') || kind.startsWith('debug') || kind === 'system_meta';
  }

  /**
   * Render a single block to DOM
   *
   * @param {Object} block - Scene block with id, block_type, text, actor_id, etc.
   * @returns {HTMLElement} The created div element
   */
  render(block) {
    if (!block || !block.id) {
      throw new Error('BlockRenderer.render: block must have id');
    }

    const div = document.createElement('div');
    div.setAttribute('data-block-id', block.id);
    div.setAttribute('data-block-type', block.block_type || 'unknown');

    if (block.actor_id) {
      div.setAttribute('data-actor-id', block.actor_id);
    }
    if (block.target_actor_id) {
      div.setAttribute('data-target-actor-id', block.target_actor_id);
    }
    if (block.speaker_label) {
      div.setAttribute('data-speaker-label', block.speaker_label);
    }
    const beat = String(block.narration_beat || '').trim().toLowerCase();
    if (beat) {
      div.setAttribute('data-narration-beat', beat);
    }

    const blockType = block.block_type || 'unknown';
    const cardStyle = String(block.card_style || '').trim().toLowerCase();
    const visibleLane = String(block.visible_lane || '').trim().toLowerCase();
    div.className = `scene-block scene-block--${blockType}`;
    if (visibleLane) {
      div.setAttribute('data-visible-lane', visibleLane);
    }
    if (cardStyle) {
      div.setAttribute('data-card-style', cardStyle);
    }
    if (cardStyle === 'npc_story' || cardStyle === 'narrative_story') {
      div.classList.add('scene-block--player-shell-story');
    } else if (cardStyle === 'player_lane') {
      div.classList.add('scene-block--player-shell-player');
    } else if (cardStyle === 'director_notice') {
      div.classList.add('scene-block--player-shell-director-notice');
    }
    if (beat === 'role_anchor' && blockType === 'narrator') {
      div.classList.add('scene-block--narrator-role-anchor');
    }
    const diagnosticsBlock = this._isDiagnosticsBlock(blockType);
    div.setAttribute('data-player-visible', diagnosticsBlock ? 'false' : 'true');
    if (diagnosticsBlock) {
      div.classList.add('scene-block--diagnostic');
      div.textContent = '';
    } else {
      const display =
        typeof blockDisplayTextForShell === 'function'
          ? String(blockDisplayTextForShell(block) ?? '')
          : block.player_display_text != null
            ? String(block.player_display_text)
            : String(block.text ?? '');
      div.textContent = display;
    }

    this.dom_root.appendChild(div);
    return div;
  }

  /**
   * Get DOM element for a block ID
   *
   * @param {string} blockId - The block ID to locate
   * @returns {HTMLElement|null}
   */
  getBlockElement(blockId) {
    return this.dom_root.querySelector(`[data-block-id="${blockId}"]`);
  }

  /**
   * Clear all rendered blocks from DOM
   */
  clear() {
    this.dom_root.innerHTML = '';
  }
}

// Export for use
if (typeof window !== 'undefined') {
  window.BlockRenderer = BlockRenderer;
}
