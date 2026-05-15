/**
 * Release readiness deck — header pills + rail badges from gate summary.
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

    function metricCard(label, value, tone) {
        return (
            '<article class="mui-card manage-readiness-metric' +
            (tone ? " manage-readiness-metric--" + tone : "") +
            '">' +
            '<p class="manage-readiness-metric-value">' +
            value +
            "</p>" +
            '<p class="manage-readiness-metric-label">' +
            label +
            "</p>" +
            "</article>"
        );
    }

    window.ManageReadinessDeck = {
        syncSummary: function (summary) {
            summary = summary || {};
            var pills = $("readiness-pills");
            var metrics = $("readiness-metrics");
            var closed = summary.closed_gates || 0;
            var partial = summary.partial_gates || 0;
            var open = summary.open_gates || 0;
            var total = summary.total_gates || 0;
            var closure = summary.closure_percent != null ? summary.closure_percent : 0;

            if (metrics) {
                metrics.innerHTML =
                    metricCard("Closure", closure + "%", closure >= 100 ? "ok" : closure >= 50 ? "warn" : "fail") +
                    metricCard("Closed", String(closed), closed > 0 ? "ok" : "") +
                    metricCard("Partial", String(partial), partial > 0 ? "warn" : "") +
                    metricCard("Open", String(open), open > 0 ? "fail" : "ok") +
                    metricCard("Total", String(total), "");
            }

            if (pills) {
                pills.innerHTML = "";
                pills.appendChild(
                    makePill(
                        "Closure",
                        closure + "%",
                        closure >= 100 ? "ok" : closure >= 50 ? "warn" : "fail"
                    )
                );
                pills.appendChild(makePill("Open", String(open), open > 0 ? "fail" : "ok"));
                pills.appendChild(makePill("Partial", String(partial), partial > 0 ? "warn" : null));
            }

            var summaryBadge = $("readiness-rail-summary-badge");
            var summarySub = $("readiness-rail-summary-sub");
            var gatesBadge = $("readiness-rail-gates-badge");
            var gatesSub = $("readiness-rail-gates-sub");

            if (summaryBadge) {
                summaryBadge.className =
                    "mui-rail-badge " +
                    (closure >= 100
                        ? "mui-rail-badge--ok"
                        : open > 0
                          ? "mui-rail-badge--warn"
                          : "mui-rail-badge--ok");
            }
            if (summarySub) {
                summarySub.textContent = closure + "% closure · " + total + " gates";
            }
            if (gatesBadge) {
                gatesBadge.className =
                    "mui-rail-badge " + (open > 0 ? "mui-rail-badge--warn" : "mui-rail-badge--ok");
            }
            if (gatesSub) {
                gatesSub.textContent =
                    open > 0 ? open + " open · " + partial + " partial" : "all clear or partial";
            }
        },

        setClosureVisible: function (visible) {
            var section = $("readiness-closure-section");
            var rail = $("readiness-rail-closure");
            if (section) section.hidden = !visible;
            if (rail) rail.hidden = !visible;
        }
    };

    document.addEventListener("DOMContentLoaded", function () {
        if (window.ManageUI && typeof window.ManageUI.scan === "function") {
            window.ManageUI.scan(document.querySelector(".manage-readiness-page") || document);
        }
    });
})();
