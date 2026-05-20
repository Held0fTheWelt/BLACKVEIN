/* global ManageAuth */
(function () {
    "use strict";

    function getDefaultModuleId() {
        var cfg = (typeof window !== "undefined" && window.__FRONTEND_CONFIG__) || {};
        var v = String(cfg.contentModuleId || "").trim();
        if (v) return v;
        if (typeof document !== "undefined" && document.body && document.body.dataset) {
            v = String(document.body.dataset.contentModuleId || "").trim();
        }
        return v;
    }

    var OK_STATUSES = [
        "canonical_loaded",
        "evidenced_live_path",
        "profile_only",
        "runtime_logic_only",
        "ready_for_frontend",
        "normal",
        "not_invoked_live_graph_primary"
    ];

    function apiData(res) {
        if (res && res.data !== undefined && Object.prototype.hasOwnProperty.call(res, "ok")) {
            return res.data || {};
        }
        return res || {};
    }

    function escapeHtml(s) {
        if (s == null) return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function displayValue(value, emptyLabel) {
        if (value === true) return "yes";
        if (value === false) return "no";
        if (value === 0) return "0";
        if (value == null) return emptyLabel || "—";
        var text = String(value).trim();
        return text || (emptyLabel || "—");
    }

    function badgeClass(status) {
        if (!status) return "manage-dx-badge";
        if (OK_STATUSES.indexOf(status) >= 0) return "manage-dx-badge manage-dx-badge--ok";
        if (status === "failed" || status === "degraded") return "manage-dx-badge manage-dx-badge--fail";
        return "manage-dx-badge manage-dx-badge--init";
    }

    function metaRow(label, value, emptyLabel, opts) {
        opts = opts || {};
        var ddClass = opts.mono ? " ng-runtime-kv-mono" : "";
        if (opts.id) ddClass += " ng-runtime-kv-id";
        return (
            '<div class="ng-runtime-kv">' +
            '<span class="ng-runtime-kv-label">' +
            escapeHtml(label) +
            "</span>" +
            '<span class="ng-runtime-kv-value' +
            ddClass +
            '">' +
            escapeHtml(displayValue(value, emptyLabel)) +
            "</span></div>"
        );
    }

    function statusRow(label, status) {
        var text = displayValue(status, "unknown");
        return (
            '<div class="ng-runtime-kv ng-runtime-kv--status">' +
            '<span class="ng-runtime-kv-label">' +
            escapeHtml(label) +
            "</span>" +
            '<span class="ng-runtime-kv-value"><span class="' +
            badgeClass(status) +
            ' ng-runtime-status-badge">' +
            escapeHtml(text) +
            "</span></span></div>"
        );
    }

    function renderPanel(title, panelKey, rowsHtml) {
        return (
            '<article class="mui-card ng-runtime-panel" data-panel="' +
            escapeHtml(panelKey) +
            '">' +
            '<header class="ng-runtime-panel-head"><h4>' +
            escapeHtml(title) +
            "</h4></header>" +
            '<div class="ng-runtime-kv-list">' +
            rowsHtml +
            "</div></article>"
        );
    }

    function buildGovPanels(summary) {
        var d = summary || {};
        var html = "";

        var cm = d.content_module_health || {};
        html += renderPanel(
            "Content module",
            "content_module_health",
            statusRow("Status", cm.status) +
                metaRow("Module", cm.content_module_id || d.content_module_id, null, { mono: true }) +
                metaRow("Story truth present", cm.story_truth_present) +
                metaRow("Source", cm.source, null, { mono: true })
        );

        var rp = d.runtime_profile_health || {};
        html += renderPanel(
            "Runtime profile",
            "runtime_profile_health",
            statusRow("Status", rp.status) +
                metaRow("Profile", rp.runtime_profile_id || d.runtime_profile_id, null, { mono: true }) +
                metaRow("Story truth present", rp.story_truth_present) +
                metaRow("Source", rp.source, null, { mono: true })
        );

        var rm = d.runtime_module_health || {};
        html += renderPanel(
            "Runtime module",
            "runtime_module_health",
            statusRow("Status", rm.status) +
                metaRow("Module", rm.runtime_module_id || d.runtime_module_id, null, { mono: true }) +
                metaRow("Story truth present", rm.story_truth_present)
        );

        var ldss = d.ldss_health || {};
        html += renderPanel(
            "LDSS",
            "ldss_health",
            statusRow("Status", ldss.status) +
                metaRow("Last trace", ldss.last_trace_id || d.last_trace_id, "none", { mono: true, id: true }) +
                metaRow("Last session", ldss.last_session_id || d.last_story_session_id, "none", {
                    mono: true,
                    id: true
                }) +
                metaRow(
                    "Last turn",
                    ldss.last_turn_number != null ? ldss.last_turn_number : d.last_turn_number,
                    "0"
                ) +
                metaRow("Evidenced live path", ldss.evidenced)
        );

        var al = d.actor_lane_health || {};
        var npcs = al.npc_actor_ids || [];
        html += renderPanel(
            "Actor lanes",
            "actor_lane_health",
            metaRow("Human actor", al.human_actor_id, "not assigned") +
                metaRow("NPC actors", npcs.length ? npcs.join(", ") : null, "none") +
                metaRow("Visitor present", al.visitor_present) +
                metaRow("Enforcement active", al.enforcement_active)
        );

        var fc = d.frontend_render_contract_health || {};
        html += renderPanel(
            "Frontend render contract",
            "frontend_render_contract_health",
            statusRow("Status", fc.status) +
                metaRow("Scene blocks", fc.scene_block_count)
        );

        var dg = d.degradation_health || {};
        var sigs = dg.degradation_signals || [];
        html += renderPanel(
            "Degradation",
            "degradation_health",
            statusRow("Posture", dg.status || dg.quality_class) +
                metaRow("Quality class", dg.quality_class) +
                metaRow("Signals", sigs.length ? sigs.join(", ") : null, "none") +
                metaRow("Last reason", dg.last_degradation_reason, "none")
        );

        return html;
    }

    function renderSessionMeta(summary) {
        var el = document.getElementById("ng-runtime-session-meta");
        if (!el) return;
        var d = summary || {};
        var rows =
            metaRow("Contract", d.contract, null, { mono: true }) +
            metaRow("Content module", d.content_module_id, null, { mono: true }) +
            metaRow("Runtime profile", d.runtime_profile_id, null, { mono: true }) +
            metaRow("Runtime module", d.runtime_module_id, null, { mono: true }) +
            metaRow("Last session", d.last_story_session_id, "no live session yet", { mono: true, id: true }) +
            metaRow("Last turn", d.last_turn_number, "0") +
            metaRow("Last trace", d.last_trace_id, "none", { mono: true, id: true });
        el.innerHTML = '<div class="ng-runtime-kv-list ng-runtime-kv-list--session">' + rows + "</div>";
    }

    function renderTechnicalDetails(config, diagnostics) {
        var el = document.getElementById("ng-runtime-technical");
        if (!el) return;
        var payload = {
            config: config || {},
            diagnostics: diagnostics || {}
        };
        el.innerHTML =
            '<details class="manage-dx-check-details">' +
            "<summary>Technical payload (config &amp; diagnostics)</summary>" +
            '<pre class="manage-psc-json" data-json-viewer data-json-label="Technical payload"></pre>' +
            "</details>";
        var pre = el.querySelector("pre.manage-psc-json");
        if (!pre) return;
        if (window.ManageUI && typeof window.ManageUI.jsonViewer === "function") {
            window.ManageUI.jsonViewer(pre, payload, { label: "Technical payload" });
        } else {
            pre.textContent = JSON.stringify(payload, null, 2);
        }
    }

    function dimensionFacts(section) {
        var facts = (section && section.facts) || [];
        if (!facts.length) return "none";
        return facts
            .slice(0, 4)
            .map(function (fact) {
                return (
                    fact.key +
                    "=" +
                    displayValue(fact.value, "—") +
                    " [" +
                    displayValue(fact.truth_label || fact.truth_level, "truth") +
                    "]"
                );
            })
            .join("; ");
    }

    function renderProjectionDetails(title, payload) {
        var projection = (payload && payload.projection) || {};
        var who = projection.who_summary || {};
        var where = projection.where_summary || {};
        var what = projection.what_summary || {};
        var how = projection.how_summary || {};
        var why = projection.why_summary || {};
        return (
            '<details class="manage-dx-check-details" open><summary>' +
            escapeHtml(title) +
            "</summary>" +
            '<div class="ng-runtime-kv-list">' +
            metaRow("Consumer", projection.target_consumer, "none") +
            metaRow("Actor", projection.actor_id, "global") +
            metaRow("Who", who.actor_type || (who.actor_id ? who.actor_id : null), "none") +
            metaRow("Where", JSON.stringify(where.facts || where.derived_actor_locations || {}), "none", { mono: true }) +
            metaRow("What", JSON.stringify(what.facts || {}), "none", { mono: true }) +
            metaRow("How", JSON.stringify(how.facts || {}), "none", { mono: true }) +
            metaRow("Why", JSON.stringify(why.facts || {}), "none", { mono: true }) +
            metaRow("Attribution paths", Object.keys(projection.source_attribution || {}).length) +
            "</div></details>"
        );
    }

    function renderW5Diagnostics(snapshot, actor, conflicts, narratorProjection, npcProjection, validation) {
        var el = document.getElementById("ng-runtime-w5");
        if (!el) return;
        if (!snapshot || snapshot.status === "unavailable") {
            el.innerHTML = '<p class="manage-dx-empty">No W5 snapshot available for the latest session.</p>';
            return;
        }
        var stats = snapshot.stats || {};
        var actors = snapshot.actor_summaries || {};
        var actorIds = Object.keys(actors);
        var selectedActor = actor || {};
        var dims = selectedActor.dimensions || {};
        var flags = snapshot.flags || {};
        var validationData = (validation && validation.validation) || {};
        var conflictRows = ((conflicts && conflicts.conflicts) || [])
            .slice(0, 5)
            .map(function (conflict) {
                return (
                    conflict.conflict_id +
                    " · " +
                    conflict.actor_id +
                    " · " +
                    conflict.dimension +
                    " · " +
                    conflict.resolution_status
                );
            })
            .join("; ");

        var html = '<div class="mui-card-grid ng-runtime-gov-grid">';
        html += renderPanel(
            "W5 Actor Situation View",
            "w5_snapshot",
            metaRow("Snapshot", snapshot.snapshot_id, "none", { mono: true, id: true }) +
                metaRow("Actors", stats.actor_count, "0") +
                metaRow("Conflicts", stats.conflict_count, "0") +
                metaRow("How present", stats.has_how) +
                metaRow("Inferred Why", stats.has_inferred_why)
        );
        html += renderPanel(
            "Per-Actor W5 Drill-In",
            "w5_actor",
            metaRow("Actor", selectedActor.actor_id || actorIds[0], "none", { mono: true }) +
                metaRow("Who", JSON.stringify((dims.who || {})), "none", { mono: true }) +
                metaRow("Where", dimensionFacts(dims.where), "none") +
                metaRow("What", dimensionFacts(dims.what), "none") +
                metaRow("How", dimensionFacts(dims.how), "none") +
                metaRow("Why", dimensionFacts(dims.why), "none")
        );
        html += renderPanel(
            "Source & Truth-Level Inspector",
            "w5_truth",
            metaRow("Truth levels", ((selectedActor.source_truth_inspector || {}).truth_levels || []).join(", "), "none") +
                metaRow("Source count", (selectedActor.source_truth_inspector || {}).source_count, "0") +
                metaRow("Validation flags", JSON.stringify(flags), "{}", { mono: true })
        );
        html += renderPanel(
            "Visibility / Perception Matrix",
            "w5_visibility",
            metaRow("Private facts", (selectedActor.visibility_perception_matrix || {}).private_fact_count, "0") +
                metaRow(
                    "Scoped actors",
                    ((selectedActor.visibility_perception_matrix || {}).scoped_actor_ids || []).join(", "),
                    "none"
                )
        );
        html += renderPanel(
            "Stale / Contradicted Fact View",
            "w5_stale",
            metaRow("Stale facts", stats.stale_fact_count, "0") +
                metaRow("Contradicted facts", stats.contradicted_fact_count, "0") +
                metaRow("Unresolved conflicts", conflicts ? conflicts.unresolved_count : 0, "0") +
                metaRow("Conflict list", conflictRows, "none")
        );
        html += renderPanel(
            "W5 Validation Diagnostics",
            "w5_validation",
            metaRow("Enabled", validationData.w5_validation_enabled) +
                metaRow("Ran", validationData.w5_validation_ran) +
                metaRow("Failed", validationData.w5_validation_failed) +
                metaRow(
                    "Failure codes",
                    (validationData.w5_validation_failure_codes || []).join(", "),
                    "none",
                    { mono: true }
                )
        );
        html += "</div>";
        html += renderProjectionDetails("Narrator Projection Preview", narratorProjection || {});
        html += renderProjectionDetails("NPC Projection Preview", npcProjection || {});
        el.innerHTML = html;
    }

    function loadW5Diagnostics(summary) {
        var sessionId = String((summary || {}).last_story_session_id || "").trim();
        var el = document.getElementById("ng-runtime-w5");
        if (!el) return Promise.resolve();
        if (!sessionId) {
            el.innerHTML = '<p class="manage-dx-empty">No live session available for W5 diagnostics.</p>';
            return Promise.resolve();
        }
        el.innerHTML = '<p class="manage-dx-empty">Loading W5 diagnostics…</p>';
        return ManageAuth.apiFetchWithAuth("/api/v1/admin/w5/" + encodeURIComponent(sessionId) + "/snapshot")
            .then(function (snapshotRes) {
                var snapshot = apiData(snapshotRes);
                var actors = snapshot.actor_summaries || {};
                var actorIds = Object.keys(actors);
                var npcActorId = actorIds.find(function (actorId) {
                    return actors[actorId] && actors[actorId].actor_type === "npc";
                });
                var selectedActorId = npcActorId || actorIds[0] || "";
                var base = "/api/v1/admin/w5/" + encodeURIComponent(sessionId);
                var actorReq = selectedActorId
                    ? ManageAuth.apiFetchWithAuth(base + "/actor/" + encodeURIComponent(selectedActorId))
                    : Promise.resolve({});
                var npcReq = npcActorId
                    ? ManageAuth.apiFetchWithAuth(base + "/npc-projection/" + encodeURIComponent(npcActorId))
                    : Promise.resolve({});
                return Promise.all([
                    Promise.resolve(snapshot),
                    actorReq,
                    ManageAuth.apiFetchWithAuth(base + "/conflicts"),
                    ManageAuth.apiFetchWithAuth(base + "/narrator-projection"),
                    npcReq,
                    ManageAuth.apiFetchWithAuth(base + "/validation")
                ]);
            })
            .then(function (payloads) {
                renderW5Diagnostics(
                    apiData(payloads[0]),
                    apiData(payloads[1]),
                    apiData(payloads[2]),
                    apiData(payloads[3]),
                    apiData(payloads[4]),
                    apiData(payloads[5])
                );
            })
            .catch(function (err) {
                el.innerHTML =
                    '<p class="manage-dx-empty">W5 diagnostics unavailable: ' +
                    escapeHtml(err && err.message ? err.message : "request failed") +
                    "</p>";
            });
    }

    function setGovLoading(loading) {
        var root = document.getElementById("mvp4-narrative-gov-summary");
        if (!root) return;
        if (loading) {
            root.innerHTML = '<p class="manage-dx-empty">Loading runtime evidence…</p>';
        }
    }

    function showError(msg) {
        var errEl = document.getElementById("ng-runtime-error");
        if (!errEl) return;
        errEl.hidden = false;
        errEl.style.display = "";
        errEl.classList.remove("mui-hidden");
        errEl.textContent = msg || "Request failed";
    }

    function clearError() {
        var errEl = document.getElementById("ng-runtime-error");
        if (!errEl) return;
        errEl.hidden = true;
        errEl.style.display = "none";
        errEl.textContent = "";
    }

    function postJson(path, payload) {
        return ManageAuth.apiFetchWithAuth(path, {
            method: "POST",
            body: JSON.stringify(payload || {})
        });
    }

    function loadRuntime() {
        clearError();
        var mid = getDefaultModuleId();
        if (!mid) {
            setGovLoading(false);
            var root0 = document.getElementById("mvp4-narrative-gov-summary");
            if (root0) {
                root0.innerHTML =
                    '<p class="manage-dx-empty">Missing content module id. Configure site_settings (content_module_id) or ADMIN_DEFAULT_CONTENT_MODULE_ID.</p>';
            }
            showError("Missing content_module_id — cannot load narrative runtime evidence.");
            return Promise.resolve();
        }
        setGovLoading(true);
        return Promise.all([
            ManageAuth.apiFetchWithAuth(
                "/api/v1/admin/narrative/runtime/gov-summary?module_id=" + encodeURIComponent(mid)
            ),
            ManageAuth.apiFetchWithAuth("/api/v1/admin/narrative/runtime/config"),
            ManageAuth.apiFetchWithAuth(
                "/api/v1/admin/narrative/runtime/diagnostics?module_id=" +
                    encodeURIComponent(mid)
            )
        ])
            .then(function (results) {
                var govPayload = apiData(results[0]);
                var summary = govPayload.summary || govPayload;
                var config = apiData(results[1]);
                var diagnostics = apiData(results[2]);
                var root = document.getElementById("mvp4-narrative-gov-summary");
                if (root) {
                    root.innerHTML = buildGovPanels(summary);
                    root.className = "mui-card-grid ng-runtime-gov-grid";
                }
                renderSessionMeta(summary);
                renderTechnicalDetails(config, diagnostics);
                return loadW5Diagnostics(summary).then(function () {
                    if (window.ManageUI && typeof window.ManageUI.scan === "function") {
                        window.ManageUI.scan(document.querySelector('[data-page="narrative-runtime"]') || document);
                    }
                });
            })
            .catch(function (err) {
                var root = document.getElementById("mvp4-narrative-gov-summary");
                if (root) {
                    root.innerHTML =
                        '<p class="manage-dx-empty">Runtime evidence unavailable. Verify play-service connectivity and moderator access.</p>';
                }
                showError(err && err.message ? err.message : "Could not load narrative runtime evidence");
                throw err;
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var page = document.querySelector('[data-page="narrative-runtime"]');
        if (!page || !window.ManageAuth) {
            if (page && !window.ManageAuth) {
                showError("ManageAuth is not loaded — cannot fetch runtime evidence.");
            }
            return;
        }

        var refreshBtn = document.getElementById("ng-runtime-refresh");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", function () {
                loadRuntime().catch(function () {});
            });
        }

        var reloadBtn = document.getElementById("ng-runtime-reload-package");
        if (reloadBtn) {
            reloadBtn.addEventListener("click", function () {
                var mid = getDefaultModuleId();
                if (!mid) {
                    window.alert("Missing content_module_id — configure site settings or env first.");
                    return;
                }
                ManageAuth.apiFetchWithAuth(
                    "/api/v1/admin/narrative/packages/" + encodeURIComponent(mid) + "/active"
                )
                    .then(function (activeRes) {
                        var active = apiData(activeRes).active_version;
                        if (!active) {
                            window.alert("No active version available.");
                            return;
                        }
                        return postJson(
                            "/api/v1/admin/narrative/packages/" +
                                encodeURIComponent(mid) +
                                "/rollback-to/" +
                                encodeURIComponent(active),
                            {
                                requested_by: "operator",
                                reason: "Force runtime reload via rollback-to-active shortcut."
                            }
                        ).then(loadRuntime);
                    })
                    .catch(function (err) {
                        window.alert(err && err.message ? err.message : "Reload failed");
                    });
            });
        }

        ManageAuth.ensureAuth()
            .then(function () {
                return loadRuntime();
            })
            .catch(function (err) {
                showError(err && err.message ? err.message : "Could not load narrative runtime");
            });
    });
})();
