/**
 * Load browser globals for play shell modules (eval in CommonJS scope).
 */
const fs = require('fs');
const path = require('path');

function loadStaticScript(filename) {
  const full = path.join(__dirname, '..', 'static', filename);
  const code = fs.readFileSync(full, 'utf8');
  // eslint-disable-next-line no-eval
  eval(code);
}

loadStaticScript('play_typewriter_engine.js');
loadStaticScript('play_block_renderer.js');
loadStaticScript('play_blocks_orchestrator.js');
loadStaticScript('play_controls.js');
