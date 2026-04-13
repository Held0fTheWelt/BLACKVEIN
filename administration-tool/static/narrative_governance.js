/* global ManageAuth */
(function () {
    "use strict";

    var DEFAULT_MODULE_ID = "god_of_carnage";

    function getModuleId() {
        var raw = window.prompt("Module ID", DEFAULT_MODULE_ID);
        if (raw === null) return null;
        var trimmed = String(raw || "").trim();
        return trimmed || DEFAULT_MODULE_ID;
    }

    function renderJson(targetId, title, data, actionsBuilder) {
        var el = document.getElementById(targetId);
        if (!el) return;
        el.innerHTML = "";
        var card = document.createElement("div");
        card.className = "narrative-card";
        var h = document.createElement("h2");
        h.textContent = title;
        var pre = document.createElement("pre");
        pre.textContent = JSON.stringify(data, null, 2);
        card.appendChild(h);
        if (typeof actionsBuilder === "function") {
            var actions = actionsBuilder();
            if (actions) card.appendChild(actions);
        }
        card.appendChild(pre);
        el.appendChild(card);
    }

    function buildActions(buttons) {
        var row = document.createElement("div");
        row.className = "narrative-actions";
        buttons.forEach(function (btnDef) {
            var btn = document.createElement("button");
            btn.className = "btn btn-outline btn-sm";
            btn.textContent = btnDef.label;
            btn.addEventListener("click", btnDef.onClick);
            row.appendChild(btn);
        });
        return row;
    }

    function postJson(path, payload) {
        return ManageAuth.apiFetchWithAuth(path, {
            method: "POST",
            body: JSON.stringify(payload || {})
        });
    }

    function extractError(err) {
        if (!err) return "Unknown error";
        if (typeof err.message === "string") return err.message;
        return JSON.stringify(err);
    }

    function loadOverview() {
        Promise.all([
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/packages"),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/health?module_id=" + encodeURIComponent(DEFAULT_MODULE_ID)),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/revision-conflicts"),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/notifications/feed")
        ]).then(function (results) {
            renderJson("narrative-overview-grid", "Overview", {
                packages: results[0].data,
                runtime_health: results[1].data,
                conflicts: results[2].data,
                notifications: results[3].data
            }, function () {
                return buildActions([
                    {
                        label: "Sync Runtime Health",
                        onClick: function () {
                            var moduleId = getModuleId();
                            if (!moduleId) return;
                            postJson("/api/v1/admin/narrative/runtime/health/sync", { module_id: moduleId })
                                .then(loadOverview)
                                .catch(function (err) { window.alert(extractError(err)); });
                        }
                    }
                ]);
            });
        }).catch(function (err) {
            renderJson("narrative-overview-grid", "Overview Error", err);
        });
    }

    function loadRuntime() {
        Promise.all([
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/config"),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/diagnostics?module_id=" + encodeURIComponent(DEFAULT_MODULE_ID))
        ]).then(function (results) {
            renderJson("narrative-runtime-panel", "Runtime Config & Diagnostics", {
                config: results[0].data,
                diagnostics: results[1].data
            }, function () {
                return buildActions([
                    {
                        label: "Reload Active Package",
                        onClick: function () {
                            var moduleId = getModuleId();
                            if (!moduleId) return;
                            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/packages/" + encodeURIComponent(moduleId) + "/active")
                                .then(function (activeRes) {
                                    var active = activeRes.data && activeRes.data.active_version;
                                    if (!active) {
                                        window.alert("No active version available.");
                                        return;
                                    }
                                    return postJson("/api/v1/admin/narrative/packages/" + encodeURIComponent(moduleId) + "/rollback-to/" + encodeURIComponent(active), {
                                        requested_by: "operator",
                                        reason: "Force runtime reload via rollback-to-active shortcut."
                                    }).then(loadRuntime);
                                })
                                .catch(function (err) { window.alert(extractError(err)); });
                        }
                    }
                ]);
            });
        })
            .catch(function (err) { renderJson("narrative-runtime-panel", "Runtime Config Error", err); });
    }

    function loadRuntimeHealth() {
        Promise.all([
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/health?module_id=" + encodeURIComponent(DEFAULT_MODULE_ID)),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/health/fallbacks?module_id=" + encodeURIComponent(DEFAULT_MODULE_ID))
        ]).then(function (results) {
            renderJson("narrative-runtime-health-panel", "Runtime Health", {
                summary: results[0].data,
                fallbacks: results[1].data
            }, function () {
                return buildActions([
                    {
                        label: "Sync From World-Engine",
                        onClick: function () {
                            var moduleId = getModuleId();
                            if (!moduleId) return;
                            postJson("/api/v1/admin/narrative/runtime/health/sync", { module_id: moduleId })
                                .then(loadRuntimeHealth)
                                .catch(function (err) { window.alert(extractError(err)); });
                        }
                    }
                ]);
            });
        }).catch(function (err) {
            renderJson("narrative-runtime-health-panel", "Runtime Health Error", err);
        });
    }

    function loadPackages() {
        Promise.all([
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/packages"),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/packages/" + encodeURIComponent(DEFAULT_MODULE_ID) + "/previews")
        ]).then(function (results) {
            renderJson("narrative-packages-panel", "Packages", {
                packages: results[0].data,
                previews: results[1].data
            }, function () {
                return buildActions([
                    {
                        label: "Build Preview",
                        onClick: function () {
                            var moduleId = getModuleId();
                            if (!moduleId) return;
                            var workspaceId = window.prompt("draft_workspace_id", "draft_goc_0003");
                            if (!workspaceId) return;
                            var sourceRevision = window.prompt("source_revision", "git:manual");
                            if (!sourceRevision) return;
                            postJson("/api/v1/admin/narrative/packages/" + encodeURIComponent(moduleId) + "/build-preview", {
                                draft_workspace_id: workspaceId,
                                source_revision: sourceRevision,
                                requested_by: "operator",
                                reason: "Operator initiated preview build."
                            }).then(loadPackages).catch(function (err) { window.alert(extractError(err)); });
                        }
                    },
                    {
                        label: "Promote Preview",
                        onClick: function () {
                            var moduleId = getModuleId();
                            if (!moduleId) return;
                            var previewId = window.prompt("preview_id");
                            if (!previewId) return;
                            postJson("/api/v1/admin/narrative/packages/" + encodeURIComponent(moduleId) + "/promote-preview", {
                                preview_id: previewId,
                                approved_by: "operator",
                                notes: "Operator promotion from admin surface."
                            }).then(loadPackages).catch(function (err) { window.alert(extractError(err)); });
                        }
                    },
                    {
                        label: "Emergency Rollback",
                        onClick: function () {
                            var moduleId = getModuleId();
                            if (!moduleId) return;
                            var version = window.prompt("target package_version");
                            if (!version) return;
                            postJson("/api/v1/admin/narrative/packages/" + encodeURIComponent(moduleId) + "/rollback-to/" + encodeURIComponent(version), {
                                requested_by: "operator",
                                reason: "Emergency rollback from admin package surface."
                            }).then(loadPackages).catch(function (err) { window.alert(extractError(err)); });
                        }
                    }
                ]);
            });
        })
            .catch(function (err) { renderJson("narrative-packages-panel", "Packages Error", err); });
    }

    function loadPolicies() {
        ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/config")
            .then(function (result) { renderJson("narrative-policies-panel", "Policy View", result.data); })
            .catch(function (err) { renderJson("narrative-policies-panel", "Policy Error", err); });
    }

    function loadFindings() {
        Promise.all([
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/health/events?module_id=" + encodeURIComponent(DEFAULT_MODULE_ID)),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/revisions")
        ]).then(function (results) {
            renderJson("narrative-findings-panel", "Findings and Linked Revisions", {
                runtime_events: results[0].data,
                revisions: results[1].data
            });
        }).catch(function (err) {
            renderJson("narrative-findings-panel", "Findings Error", err);
        });
    }

    function loadRevisions() {
        Promise.all([
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/revisions"),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/revision-conflicts")
        ]).then(function (results) {
            renderJson("narrative-revisions-panel", "Revisions with Inline Conflicts", {
                revisions: results[0].data,
                conflicts: results[1].data
            }, function () {
                return buildActions([
                    {
                        label: "Resolve Conflict",
                        onClick: function () {
                            var conflictId = window.prompt("conflict_id");
                            if (!conflictId) return;
                            var strategy = window.prompt(
                                "resolution_strategy",
                                "manual_select_winner"
                            );
                            if (!strategy) return;
                            var payload = {
                                resolution_strategy: strategy,
                                resolved_by: "operator",
                                notes: "Resolved from admin revisions surface."
                            };
                            if (strategy === "manual_select_winner" || strategy === "dismiss_loser") {
                                var winner = window.prompt("winner_revision_id");
                                if (!winner) return;
                                payload.winner_revision_id = winner;
                            }
                            postJson("/api/v1/admin/narrative/revision-conflicts/" + encodeURIComponent(conflictId) + "/resolve", payload)
                                .then(loadRevisions)
                                .catch(function (err) { window.alert(extractError(err)); });
                        }
                    }
                ]);
            });
        }).catch(function (err) {
            renderJson("narrative-revisions-panel", "Revisions Error", err);
        });
    }

    function loadEvaluations() {
        ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/evaluations?module_id=" + encodeURIComponent(DEFAULT_MODULE_ID))
            .then(function (result) {
                renderJson("narrative-evaluations-panel", "Evaluations", result.data, function () {
                    return buildActions([
                        {
                            label: "Run Preview Evaluation",
                            onClick: function () {
                                var moduleId = getModuleId();
                                if (!moduleId) return;
                                var previewId = window.prompt("preview_id");
                                if (!previewId) return;
                                postJson("/api/v1/admin/narrative/evaluations/run-preview", {
                                    module_id: moduleId,
                                    preview_id: previewId,
                                    run_types: ["preview_comparison"]
                                }).then(loadEvaluations).catch(function (err) { window.alert(extractError(err)); });
                            }
                        },
                        {
                            label: "Complete Evaluation",
                            onClick: function () {
                                var runId = window.prompt("run_id");
                                if (!runId) return;
                                var promotable = window.confirm("Set promotion_readiness.is_promotable = true?");
                                postJson("/api/v1/admin/narrative/evaluations/" + encodeURIComponent(runId) + "/complete", {
                                    status: "completed",
                                    scores: { policy_compliance: 0.95, regression_risk: 0.1 },
                                    promotion_readiness: {
                                        is_promotable: promotable,
                                        blocking_reasons: promotable ? [] : ["manual_gate_block"]
                                    }
                                }).then(loadEvaluations).catch(function (err) { window.alert(extractError(err)); });
                            }
                        }
                    ]);
                });
            })
            .catch(function (err) { renderJson("narrative-evaluations-panel", "Evaluations Error", err); });
    }

    function loadNotifications() {
        Promise.all([
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/notifications/rules"),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/notifications/feed")
        ]).then(function (results) {
            renderJson("narrative-notifications-panel", "Notifications", {
                rules: results[0].data,
                feed: results[1].data
            }, function () {
                return buildActions([
                    {
                        label: "Ack Notification",
                        onClick: function () {
                            var notificationId = window.prompt("notification_id");
                            if (!notificationId) return;
                            postJson("/api/v1/admin/narrative/notifications/feed/" + encodeURIComponent(notificationId) + "/ack", {
                                acknowledged_by: "operator"
                            }).then(loadNotifications).catch(function (err) { window.alert(extractError(err)); });
                        }
                    },
                    {
                        label: "Upsert Rule",
                        onClick: function () {
                            var ruleId = window.prompt("rule_id", "notif_rule_fallback_threshold");
                            if (!ruleId) return;
                            postJson("/api/v1/admin/narrative/notifications/rules", {
                                rule_id: ruleId,
                                event_type: "fallback_threshold_exceeded",
                                condition: {},
                                channels: ["admin_ui"],
                                recipients: ["ops"],
                                enabled: true
                            }).then(loadNotifications).catch(function (err) { window.alert(extractError(err)); });
                        }
                    }
                ]);
            });
        }).catch(function (err) {
            renderJson("narrative-notifications-panel", "Notifications Error", err);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var pageEl = document.querySelector(".narrative-governance-page");
        if (!pageEl) return;
        var page = pageEl.getAttribute("data-narrative-page");
        var loaders = {
            overview: loadOverview,
            runtime: loadRuntime,
            runtime_health: loadRuntimeHealth,
            packages: loadPackages,
            policies: loadPolicies,
            findings: loadFindings,
            revisions: loadRevisions,
            evaluations: loadEvaluations,
            notifications: loadNotifications
        };
        if (loaders[page]) loaders[page]();
    });
})();
