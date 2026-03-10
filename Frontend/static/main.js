/**
 * World of Shadows – public frontend base
 * Provides backend API URL via window.FrontendConfig.getApiBaseUrl() (from __FRONTEND_CONFIG__.backendApiUrl).
 * No server-side DB; pages consume backend API via JS where needed.
 */
(function() {
    function getApiBaseUrl() {
        var c = window.__FRONTEND_CONFIG__;
        return (c && c.backendApiUrl) ? c.backendApiUrl : '';
    }
    window.FrontendConfig = {
        getApiBaseUrl: getApiBaseUrl
    };
})();
