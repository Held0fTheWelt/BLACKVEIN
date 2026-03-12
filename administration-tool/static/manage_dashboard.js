/**
 * Management dashboard: ensure auth, then show user and role-based links.
 */
(function() {
    document.addEventListener("DOMContentLoaded", function() {
        if (!window.ManageAuth) return;
        window.ManageAuth.ensureAuth().then(function(user) {
            window.ManageAuth.updateUI(user);
        }).catch(function() {});
    });
})();
