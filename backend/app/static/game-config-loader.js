// Game configuration loader - reads JSON from data element
(function() {
    var configEl = document.getElementById('game-config');
    if (configEl) {
        try {
            window.WOS_GAME_CONFIG = JSON.parse(configEl.textContent);
        } catch (e) {
            console.error('Failed to parse game config:', e);
            window.WOS_GAME_CONFIG = {
                playServiceConfigured: false,
                apiBase: '/api/v1/game',
                playServicePublicUrl: null
            };
        }
    }
})();
