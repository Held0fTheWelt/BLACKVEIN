/**
 * Single source for player-shell visible text (ADR-0034): renderer + typewriter + orchestrator.
 *
 * Must match: player_display_text if non-null, else text.
 */
function blockDisplayTextForShell(block) {
  if (!block) {
    return '';
  }
  return block.player_display_text != null ? block.player_display_text : block.text ?? '';
}

if (typeof window !== 'undefined') {
  window.blockDisplayTextForShell = blockDisplayTextForShell;
}
