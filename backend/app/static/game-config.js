// Game configuration initialization for game menu
(function() {
    // This configuration is set inline to be passed from the server
    // No additional functionality needed here
    if (typeof window.WOS_GAME_CONFIG === 'undefined') {
        window.WOS_GAME_CONFIG = {
            playServiceConfigured: false,
            apiBase: '/api/v1/game',
            playServicePublicUrl: null
        };
    }
})();
