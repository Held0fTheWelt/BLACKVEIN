// Slogan rotation functionality for landing page
(function(){
    var lang = "de";
    var api = "/api/v1";
    var placement = "landing.teaser.primary";

    function start() {
        var wrap = document.getElementById("hero-teaser-slogan-wrap");
        var track = document.getElementById("hero-teaser-track");
        var defaultEl = document.getElementById("hero-teaser-slogan");
        if (!wrap || !track || !defaultEl) return;

        function run(items, intervalSec, enabled) {
            if (!items || !items.length) return;
            var minInterval = 5;
            var sec = (intervalSec != null && intervalSec > 0) ? Math.max(minInterval, intervalSec) : 60;
            track.innerHTML = "";
            items.forEach(function(item){
                var p = document.createElement("p");
                p.className = "hero-teaser-item hero-sub";
                var text = item.text || "";
                var lines = text.split("\n");
                lines.forEach(function(line, idx) {
                    if (idx > 0) p.appendChild(document.createElement("br"));
                    p.appendChild(document.createTextNode(line));
                });
                track.appendChild(p);
            });
            if (items.length === 1 || !enabled) return;
            var idx = 0;
            function roll() {
                idx = (idx + 1) % items.length;
                var itemHeight = track.children[0].offsetHeight;
                track.style.transform = "translateY(-" + (idx * itemHeight) + "px)";
            }
            setInterval(roll, sec * 1000);
        }

        Promise.all([
            fetch(api + "/site/slogans?placement=" + encodeURIComponent(placement) + "&lang=" + encodeURIComponent(lang), { credentials: "same-origin" }).then(function(r){ return r.ok ? r.json() : { items: [] }; }).catch(function(){ return { items: [] }; }),
            fetch(api + "/site/settings", { credentials: "same-origin" }).then(function(r){ return r.ok ? r.json() : {}; }).catch(function(){ return {}; })
        ]).then(function(res){
            var items = (res[0].items || []);
            var settings = res[1] || {};
            var intervalSec = settings.slogan_rotation_interval_seconds;
            var enabled = settings.slogan_rotation_enabled !== false;
            if (items.length) {
                run(items, intervalSec, enabled);
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
