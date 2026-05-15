/**
 * Forum manage deck — header pills from moderation metrics.
 */
(function () {
    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    function makePill(label, value, modifier) {
        var el = document.createElement("span");
        el.className = "mui-pill" + (modifier ? " mui-pill--" + modifier : "");
        var l = document.createElement("span");
        l.className = "mui-pill-label";
        l.textContent = label;
        var v = document.createElement("span");
        v.className = "mui-pill-value";
        v.textContent = value;
        el.appendChild(l);
        el.appendChild(v);
        return el;
    }

    function syncRail(openReports) {
        var badge = $("manage-forum-rail-dashboard-badge");
        var reportsBadge = $("manage-forum-rail-reports-badge");
        var dashSub = $("manage-forum-rail-dashboard-sub");
        var reportsSub = $("manage-forum-rail-reports-sub");
        var n = openReports || 0;
        if (badge) {
            badge.className =
                "mui-rail-badge " + (n > 0 ? "mui-rail-badge--warn" : "mui-rail-badge--ok");
        }
        if (reportsBadge) {
            reportsBadge.className =
                "mui-rail-badge " + (n > 0 ? "mui-rail-badge--warn" : "mui-rail-badge--ok");
        }
        if (dashSub) {
            dashSub.textContent = n > 0 ? n + " open in queue" : "queue clear";
        }
        if (reportsSub) {
            reportsSub.textContent = n > 0 ? n + " need attention" : "full queue";
        }
    }

    window.ManageForumDeck = {
        syncMetrics: function (metrics) {
            var m = metrics || {};
            var pills = $("manage-forum-pills");
            var open = m.open_reports || 0;
            syncRail(open);
            if (!pills) return;
            pills.innerHTML = "";
            pills.appendChild(
                makePill("Open reports", String(open), open > 0 ? "warn" : "ok")
            );
            pills.appendChild(makePill("Hidden posts", String(m.hidden_posts || 0), "warn"));
            pills.appendChild(makePill("Locked", String(m.locked_threads || 0), ""));
            pills.appendChild(makePill("Pinned", String(m.pinned_threads || 0), ""));
        }
    };

    document.addEventListener("DOMContentLoaded", function () {
        if (window.ManageUI && typeof window.ManageUI.scan === "function") {
            window.ManageUI.scan(document.querySelector(".manage-forum-page") || document);
        }
    });
})();
