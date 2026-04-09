(function () {
  const cfg = window.__FRONTEND_CONFIG__ || {};
  const apiBase = (cfg.apiProxyBase || '') + '/api/v1';

  const evidenceOut = document.getElementById('ai-stack-evidence-out');
  const packagesOut = document.getElementById('ai-stack-packages-out');
  const releaseOut = document.getElementById('ai-stack-release-readiness-out');
  const releaseSummary = document.getElementById('ai-stack-release-summary');

  const cockpitStamp = document.getElementById('ai-stack-cockpit-source-stamp');
  const cockpitWarning = document.getElementById('ai-stack-cockpit-warning');
  const aggregateSummaryEl = document.getElementById('ai-stack-aggregate-summary');
  const blockersPanelEl = document.getElementById('ai-stack-blockers-panel');
  const focusPanelEl = document.getElementById('ai-stack-g9-focus');
  const levelDistinctionEl = document.getElementById('ai-stack-level-distinction');
  const gateStackEl = document.getElementById('ai-stack-gate-stack');
  const sourceRefsEl = document.getElementById('ai-stack-source-refs');

  const sessionInput = document.getElementById('ai-stack-session-id');
  const loadEvidenceBtn = document.getElementById('ai-stack-load-evidence');
  const loadPackagesBtn = document.getElementById('ai-stack-load-packages');
  const loadReleaseBtn = document.getElementById('ai-stack-load-release-readiness');
  const loadCockpitBtn = document.getElementById('ai-stack-load-closure-cockpit');

  if (!evidenceOut || !packagesOut || !sessionInput || !loadEvidenceBtn || !loadPackagesBtn) return;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function statusBadge(value) {
    var safe = escapeHtml(value || 'unknown');
    return '<span class="badge badge-info">' + safe + '</span>';
  }

  function summarizeReleaseReadiness(data) {
    if (!data || typeof data !== 'object') return '';
    var lines = [];
    lines.push('Overall: ' + (data.overall_status || '(missing)'));
    if (data.decision_support && typeof data.decision_support === 'object') {
      var ds = data.decision_support;
      lines.push('Writers-Room retrieval tier (latest artifact): ' + String(ds.latest_writers_room_retrieval_tier));
      lines.push('Improvement retrieval class (latest package): ' + String(ds.latest_improvement_retrieval_context_class));
      lines.push('WR retrieval graded review-ready: ' + String(ds.writers_room_review_ready_for_retrieval_graded_review));
      lines.push('Improvement retrieval graded review-ready: ' + String(ds.improvement_review_ready_for_retrieval_graded_review));
    }
    if (Array.isArray(data.areas)) {
      lines.push('Areas:');
      data.areas.forEach(function (a) {
        var posture = a.evidence_posture ? ' [' + a.evidence_posture + ']' : '';
        lines.push('  - ' + a.area + ': ' + a.status + posture);
      });
    }
    if (Array.isArray(data.known_partiality) && data.known_partiality.length) {
      lines.push('Known partiality: ' + data.known_partiality.join('; '));
    }
    if (Array.isArray(data.known_environment_sensitivities) && data.known_environment_sensitivities.length) {
      lines.push('Environment sensitivities: ' + data.known_environment_sensitivities.join('; '));
    }
    return lines.join('\n');
  }

  function renderAggregateSummary(summary) {
    if (!aggregateSummaryEl) return;
    if (!summary || typeof summary !== 'object') {
      aggregateSummaryEl.innerHTML = '<p class="manage-empty">No aggregate summary available.</p>';
      return;
    }
    aggregateSummaryEl.innerHTML = [
      '<article class="ai-summary-card">',
      '<h4>Overall closure posture</h4>',
      '<p>' + escapeHtml(summary.overall_closure_posture || 'unknown') + '</p>',
      '</article>',
      '<article class="ai-summary-card">',
      '<h4>Level A status</h4>',
      '<p>' + statusBadge(summary.level_a_status) + '</p>',
      '</article>',
      '<article class="ai-summary-card">',
      '<h4>Level B status</h4>',
      '<p>' + statusBadge(summary.level_b_status) + '</p>',
      '</article>',
      '<article class="ai-summary-card">',
      '<h4>Key blocker summary</h4>',
      '<p>' + escapeHtml(summary.key_blocker_summary || 'No blocker summary provided.') + '</p>',
      '</article>'
    ].join('');

    if (cockpitStamp) {
      var ref = summary.authoritative_reference || {};
      cockpitStamp.textContent = 'Authoritative source: '
        + String(ref.audit_run_id || 'n/a')
        + ' @ '
        + String(ref.timestamp_utc || 'n/a')
        + ' (' + String(ref.source || 'unknown') + ')';
    }
  }

  function artifactListHtml(refs) {
    if (!Array.isArray(refs) || !refs.length) {
      return '<p class="manage-empty">No artifact pointers.</p>';
    }
    return '<ul class="ai-artifact-list">' + refs.map(function (ref) {
      return '<li><strong>' + escapeHtml(ref.label || 'Artifact') + ':</strong> '
        + '<code>' + escapeHtml(ref.path || '') + '</code></li>';
    }).join('') + '</ul>';
  }

  function renderBlockers(blockers) {
    if (!blockersPanelEl) return;
    if (!blockers || typeof blockers !== 'object') {
      blockersPanelEl.innerHTML = '<p class="manage-empty">No blocker data available.</p>';
      return;
    }
    var resolved = Array.isArray(blockers.repo_local_resolved) ? blockers.repo_local_resolved : [];
    var evidential = Array.isArray(blockers.evidential_or_external) ? blockers.evidential_or_external : [];
    blockersPanelEl.innerHTML = [
      '<div class="ai-blocker-grid">',
      '<article class="ai-summary-card">',
      '<h4>Repo-local resolved</h4>',
      (resolved.length
        ? '<ul>' + resolved.map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul>'
        : '<p class="manage-empty">No resolved entries reported.</p>'),
      '</article>',
      '<article class="ai-summary-card">',
      '<h4>Evidential / external blockers</h4>',
      (evidential.length
        ? evidential.map(function (b) {
          return '<div class="ai-blocker-card">'
            + '<p><strong>' + escapeHtml(b.title || b.id || 'Blocker') + '</strong> - '
            + escapeHtml(b.status || 'unknown') + '</p>'
            + '<p>' + escapeHtml(b.primary_classification || '') + '</p>'
            + artifactListHtml(b.artifact_refs)
            + '</div>';
        }).join('')
        : '<p class="manage-empty">No evidential/external blockers reported.</p>'),
      '</article>',
      '</div>'
    ].join('');
  }

  function renderFocus(focus) {
    if (!focusPanelEl || !levelDistinctionEl) return;
    if (!focus || typeof focus !== 'object') {
      focusPanelEl.innerHTML = '<p class="manage-empty">No G9/G9B/G10 focus data available.</p>';
      levelDistinctionEl.textContent = '';
      return;
    }
    var g9 = focus.g9_acceptance || {};
    var g9b = focus.g9b_independence || {};
    var g10 = focus.g10_integrative || {};
    focusPanelEl.innerHTML = [
      '<article class="ai-summary-card">',
      '<h4>G9 acceptance</h4>',
      '<p>Status: ' + statusBadge(g9.closure_level_status) + '</p>',
      '<p>Result: ' + escapeHtml(g9.result || 'unknown') + '</p>',
      '<p>' + escapeHtml(g9.rationale || '') + '</p>',
      artifactListHtml(g9.artifact_refs),
      '</article>',
      '<article class="ai-summary-card">',
      '<h4>G9B evaluator independence</h4>',
      '<p>Status: ' + statusBadge(g9b.closure_level_status) + '</p>',
      '<p>Attempt: ' + escapeHtml(g9b.level_b_attempt_status || 'unknown') + '</p>',
      '<p>Primary classification: ' + escapeHtml(g9b.independence_classification_primary || 'n/a') + '</p>',
      '<p>' + escapeHtml(g9b.rationale || '') + '</p>',
      artifactListHtml(g9b.artifact_refs),
      '</article>',
      '<article class="ai-summary-card">',
      '<h4>G10 integrative closure</h4>',
      '<p>Structural: ' + statusBadge(g10.structural_status) + '</p>',
      '<p>Closure-level: ' + statusBadge(g10.closure_level_status) + '</p>',
      '<p>' + escapeHtml(g10.rationale || '') + '</p>',
      artifactListHtml(g10.artifact_refs),
      '</article>'
    ].join('');
    levelDistinctionEl.textContent = String(
      focus.anti_misread_statement
      || 'G10 green does not equal Level B if G9B independence remains insufficient.'
    );
  }

  function renderGateStack(gateStack) {
    if (!gateStackEl) return;
    if (!Array.isArray(gateStack) || !gateStack.length) {
      gateStackEl.innerHTML = '<p class="manage-empty">No gate stack available.</p>';
      return;
    }
    gateStackEl.innerHTML = gateStack.map(function (gate) {
      return [
        '<article class="ai-gate-card">',
        '<h4>' + escapeHtml(gate.gate_label || gate.gate_id || 'Gate') + '</h4>',
        '<p><strong>Structural:</strong> ' + statusBadge(gate.structural_status) + '</p>',
        '<p><strong>Closure-level:</strong> ' + statusBadge(gate.closure_level_status) + '</p>',
        '<p><strong>Evidence quality:</strong> ' + statusBadge(gate.evidence_quality) + '</p>',
        '<p>' + escapeHtml(gate.rationale || '') + '</p>',
        '<details><summary>Artifact pointers</summary>',
        artifactListHtml(gate.artifact_refs),
        '</details>',
        '</article>'
      ].join('');
    }).join('');
  }

  function renderSourceRefs(data) {
    if (!sourceRefsEl) return;
    var refs = Array.isArray(data.source_refs) ? data.source_refs : [];
    var consistency = Array.isArray(data.consistency_notes) ? data.consistency_notes : [];
    var warnings = Array.isArray(data.warnings) ? data.warnings : [];
    sourceRefsEl.innerHTML = [
      '<details open><summary>Canonical source references</summary>',
      artifactListHtml(refs),
      '</details>',
      '<details><summary>Consistency notes</summary>',
      (consistency.length
        ? '<ul>' + consistency.map(function (note) { return '<li>' + escapeHtml(note) + '</li>'; }).join('') + '</ul>'
        : '<p class="manage-empty">No consistency notes.</p>'),
      '</details>',
      '<details><summary>Warnings</summary>',
      (warnings.length
        ? '<ul>' + warnings.map(function (note) { return '<li>' + escapeHtml(note) + '</li>'; }).join('') + '</ul>'
        : '<p class="manage-empty">No warnings.</p>'),
      '</details>'
    ].join('');
  }

  function clearCockpitError() {
    if (!cockpitWarning) return;
    cockpitWarning.style.display = 'none';
    cockpitWarning.textContent = '';
  }

  function showCockpitError(message) {
    if (!cockpitWarning) return;
    cockpitWarning.style.display = 'block';
    cockpitWarning.textContent = message;
  }

  function token() { return localStorage.getItem('access_token') || ''; }
  async function api(path, opts) {
    const headers = Object.assign({ 'Accept': 'application/json' }, (opts && opts.headers) || {});
    if (token()) headers['Authorization'] = 'Bearer ' + token();
    const res = await fetch(apiBase + path, Object.assign({}, opts, { headers }));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || data.message || ('Request failed: ' + res.status));
    return data;
  }

  loadEvidenceBtn.addEventListener('click', function () {
    const sid = (sessionInput.value || '').trim();
    if (!sid) {
      evidenceOut.textContent = 'Enter a backend session id.';
      return;
    }
    api('/admin/ai-stack/session-evidence/' + encodeURIComponent(sid), { method: 'GET' })
      .then(function (data) { evidenceOut.textContent = JSON.stringify(data, null, 2); })
      .catch(function (err) { evidenceOut.textContent = err.message; });
  });

  loadPackagesBtn.addEventListener('click', function () {
    api('/admin/ai-stack/improvement-packages', { method: 'GET' })
      .then(function (data) { packagesOut.textContent = JSON.stringify(data, null, 2); })
      .catch(function (err) { packagesOut.textContent = err.message; });
  });

  if (loadReleaseBtn && releaseOut) {
    loadReleaseBtn.addEventListener('click', function () {
      api('/admin/ai-stack/release-readiness', { method: 'GET' })
        .then(function (data) {
          if (releaseSummary) releaseSummary.textContent = summarizeReleaseReadiness(data);
          releaseOut.textContent = JSON.stringify(data, null, 2);
        })
        .catch(function (err) {
          if (releaseSummary) releaseSummary.textContent = '';
          releaseOut.textContent = err.message;
        });
    });
  }

  if (loadCockpitBtn) {
    loadCockpitBtn.addEventListener('click', function () {
      clearCockpitError();
      api('/admin/ai-stack/closure-cockpit', { method: 'GET' })
        .then(function (data) {
          renderAggregateSummary(data.aggregate_summary || {});
          renderBlockers(data.current_blockers || {});
          renderFocus(data.g9_g9b_g10_focus || {});
          renderGateStack(data.gate_stack || []);
          renderSourceRefs(data || {});
        })
        .catch(function (err) {
          showCockpitError(err.message || 'Failed to load closure cockpit.');
        });
    });
  }
})();
