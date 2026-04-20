/**
 * World of Shadows – public frontend base
 * Centralized backend API access: getApiBaseUrl() and apiFetch().
 * Config from window.__FRONTEND_CONFIG__.backendApiUrl (injected by Flask).
 */
(function() {
    function getApiBaseUrl() {
        var c = window.__FRONTEND_CONFIG__;
        // Prefer same-origin proxy to avoid CORS when backend is remote.
        if (c && c.apiProxyBase) return String(c.apiProxyBase).trim();
        return (c && c.backendApiUrl) ? String(c.backendApiUrl).trim() : '';
    }

    /**
     * Fetch JSON from backend. Returns Promise that resolves with parsed JSON
     * or rejects with an error message string (network, 4xx/5xx, or parse error).
     * @param {string} pathOrUrl - Path (e.g. "/api/v1/news") or full URL. Path is relative to getApiBaseUrl().
     * @param {{ method?: string, headers?: Object }} opts - Optional method and headers (Accept: application/json added by default).
     */
    function apiFetch(pathOrUrl, opts) {
        opts = opts || {};
        var base = getApiBaseUrl();
        var url = (pathOrUrl.indexOf('http') === 0)
            ? pathOrUrl
            : (base ? base.replace(/\/$/, '') + (pathOrUrl.indexOf('/') === 0 ? pathOrUrl : '/' + pathOrUrl) : pathOrUrl);
        var method = (opts.method || 'GET').toUpperCase();
        var headers = opts.headers || {};
        if (!headers['Accept']) headers['Accept'] = 'application/json';
        if (headers['Content-Type'] === undefined && (method === 'POST' || method === 'PUT')) {
            headers['Content-Type'] = 'application/json';
        }

        return new Promise(function(resolve, reject) {
            fetch(url, { method: method, headers: headers, body: opts.body })
                .then(function(res) {
                    var next = res.ok ? res.json().then(function(data) { resolve(data); }).catch(function() { reject('Invalid response'); })
                        : res.json().catch(function() { return {}; }).then(function(body) {
                            var msg = (body && body.error) ? body.error : ('Request failed: ' + res.status);
                            reject(msg);
                        });
                    return next;
                })
                .catch(function(err) {
                    if (err && typeof err.message === 'string') reject(err.message);
                    else reject('Network error');
                });
        });
    }

    window.FrontendConfig = {
        getApiBaseUrl: getApiBaseUrl,
        apiFetch: apiFetch
    };
})();
