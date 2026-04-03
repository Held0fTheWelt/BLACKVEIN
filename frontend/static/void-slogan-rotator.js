// Void footer slogan rotation functionality
(function(){
    var lang = "de";
    var api = "/api/v1";
    var placement = "landing.hero.primary";

    function start() {
        var wrap = document.getElementById("void-hero-slogan-wrap");
        var track = document.getElementById("void-hero-slogan-track");
        if (!wrap || !track) return;

        function run(items, intervalSec, enabled) {
            if (!items || !items.length) return;
            var minInterval = 5;
            var sec = (intervalSec != null && intervalSec > 0) ? Math.max(minInterval, intervalSec) : 60;
            track.innerHTML = "";
            var reversed = items.slice().reverse();
            reversed.forEach(function(item){
                var span = document.createElement("span");
                span.className = "void-slogan-item";
                var text = item.text || "";
                var lines = text.split("\n");
                lines.forEach(function(line, idx) {
                    if (idx > 0) span.appendChild(document.createElement("br"));
                    span.appendChild(document.createTextNode(line));
                });
                track.appendChild(span);
            });
            var n = items.length;
            if (n > 1) {
                var itemHeight = track.children[0].offsetHeight;
                track.style.transform = "translateY(-" + (n - 1) * itemHeight + "px)";
            }
            if (items.length === 1 || !enabled) return;
            var idx = 0;
            function roll() {
                idx = (idx + 1) % n;
                var itemHeight = track.children[0].offsetHeight;
                var y = -(n - 1 - idx) * itemHeight;
                track.style.transform = "translateY(" + y + "px)";
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
