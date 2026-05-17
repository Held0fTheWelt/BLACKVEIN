(function () {
  const app = document.getElementById("api-explorer-app");
  if (!app) return;

  const catalogUrl = app.dataset.catalogUrl;
  const openapiUrl = app.dataset.openapiUrl || "/backend/openapi.yaml";
  const input = document.getElementById("api-explorer-search");
  const clearButton = app.querySelector("[data-api-clear]");
  const tagList = app.querySelector("[data-api-tags]");
  const resultsList = app.querySelector("[data-api-results]");
  const countEl = app.querySelector("[data-api-count]");
  const activeFilterEl = app.querySelector("[data-api-active-filter]");
  const detailEl = app.querySelector("[data-api-detail]");
  const detailEmptyEl = app.querySelector("[data-api-detail-empty]");

  const state = {
    catalog: null,
    query: "",
    tag: "",
    selectedId: "",
  };

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function cssMethod(method) {
    return "method-" + String(method || "").toLowerCase();
  }

  function parameterText(parameters) {
    if (!parameters || parameters.length === 0) return "Keine Parameter";
    return parameters.map((param) => {
      const required = param.required ? "required" : "optional";
      return `${param.name} (${param.in}, ${param.type}, ${required})`;
    }).join(", ");
  }

  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }

  function endpointMatchesToken(endpoint, rawToken) {
    const token = normalize(rawToken);
    if (!token) return true;
    const idx = token.indexOf(":");
    if (idx > 0) {
      const key = token.slice(0, idx);
      const value = token.slice(idx + 1);
      if (!value) return true;
      if (key === "tag") return normalize(endpoint.tag).includes(value);
      if (key === "method") return normalize(endpoint.method) === value;
      if (key === "auth") return normalize(endpoint.auth_kind).includes(value) || normalize(endpoint.auth).includes(value);
      if (key === "limit" || key === "rate") {
        const rateLimit = endpoint.rate_limit || {};
        return normalize(rateLimit.limit).includes(value) || normalize(rateLimit.source).includes(value);
      }
      if (key === "path") return normalize(endpoint.path).includes(value);
      if (key === "handler") return normalize(endpoint.handler).includes(value);
      if (key === "param") {
        return (endpoint.parameters || []).some((param) => normalize(param.name).includes(value));
      }
      if (key === "status" || key === "response") {
        return (endpoint.responses || []).some((code) => normalize(code).includes(value));
      }
    }
    return normalize(endpoint.search).includes(token);
  }

  function filteredEndpoints() {
    if (!state.catalog) return [];
    const tokens = state.query.split(/\s+/).filter(Boolean);
    return state.catalog.endpoints.filter((endpoint) => {
      if (state.tag && endpoint.tag !== state.tag) return false;
      return tokens.every((token) => endpointMatchesToken(endpoint, token));
    });
  }

  function renderTags() {
    if (!state.catalog || !tagList) return;
    const buttons = [
      `<button type="button" class="api-tag-filter${state.tag ? "" : " is-active"}" data-tag="">Alle <span>${state.catalog.stats.endpoints}</span></button>`,
    ];
    state.catalog.tags.forEach((tag) => {
      const active = state.tag === tag.name ? " is-active" : "";
      buttons.push(
        `<button type="button" class="api-tag-filter${active}" data-tag="${escapeHtml(tag.name)}">` +
          `${escapeHtml(tag.name)} <span>${tag.count}</span>` +
        "</button>"
      );
    });
    tagList.innerHTML = buttons.join("");
  }

  function endpointCard(endpoint) {
    const doc = endpoint.doc || endpoint.tag_description || endpoint.description || endpoint.method_label;
    const source = endpoint.source_path
      ? `${endpoint.source_path}${endpoint.source_line ? ":" + endpoint.source_line : ""}`
      : endpoint.handler || endpoint.operation_id || "No handler";
    const selected = endpoint.id === state.selectedId ? " is-selected" : "";
    const rateLimit = endpoint.rate_limit || {};
    return (
      `<button type="button" class="api-endpoint-card${selected}" data-endpoint-id="${escapeHtml(endpoint.id)}">` +
        '<span class="api-card-main">' +
          `<span class="api-card-title"><span class="api-method ${cssMethod(endpoint.method)}">${escapeHtml(endpoint.method)}</span>` +
          `<code>${escapeHtml(endpoint.path)}</code></span>` +
          `<span class="api-card-summary">${escapeHtml(doc)}</span>` +
          `<span class="api-card-meta"><span>${escapeHtml(endpoint.tag)}</span><span>${escapeHtml(endpoint.auth)}</span><span>${escapeHtml(rateLimit.limit || "limit n/a")}</span><span>${escapeHtml(source)}</span></span>` +
        "</span>" +
      "</button>"
    );
  }

  function renderResults() {
    const endpoints = filteredEndpoints();
    if (!resultsList || !countEl) return;
    countEl.textContent = `${endpoints.length} Endpoint${endpoints.length === 1 ? "" : "s"}`;
    activeFilterEl.textContent = state.tag ? `Tag: ${state.tag}` : "";
    if (endpoints.length === 0) {
      resultsList.innerHTML = '<div class="api-empty-state">Keine Endpoints fuer diese Suche.</div>';
      clearDetail();
      return;
    }
    resultsList.innerHTML = endpoints.map(endpointCard).join("");
    if (!state.selectedId || !endpoints.some((endpoint) => endpoint.id === state.selectedId)) {
      state.selectedId = endpoints[0].id;
    }
    renderDetail(state.selectedId);
    renderSelectedCard();
  }

  function renderSelectedCard() {
    app.querySelectorAll(".api-endpoint-card").forEach((card) => {
      card.classList.toggle("is-selected", card.dataset.endpointId === state.selectedId);
    });
  }

  function selectedEndpoint(id) {
    if (!state.catalog) return null;
    return state.catalog.endpoints.find((endpoint) => endpoint.id === id) || null;
  }

  function responsePills(endpoint) {
    return (endpoint.responses || []).map((code) => `<span>${escapeHtml(code)}</span>`).join("");
  }

  function rateLimitText(endpoint) {
    const rateLimit = endpoint.rate_limit || {};
    const label = rateLimit.limit || "nicht im Katalog";
    const source = rateLimit.source ? ` (${rateLimit.source})` : "";
    const key = rateLimit.key ? `; key: ${rateLimit.key}` : "";
    return `${label}${source}${key}`;
  }

  function parameterRows(endpoint) {
    if (!endpoint.parameters || endpoint.parameters.length === 0) {
      return '<tr><td colspan="4">Keine Parameter in der OpenAPI-Spec.</td></tr>';
    }
    return endpoint.parameters.map((param) => (
      "<tr>" +
        `<td><code>${escapeHtml(param.name)}</code></td>` +
        `<td>${escapeHtml(param.in)}</td>` +
        `<td>${escapeHtml(param.type)}</td>` +
        `<td>${param.required ? "ja" : "nein"}</td>` +
      "</tr>"
    )).join("");
  }

  function renderDetail(id) {
    const endpoint = selectedEndpoint(id);
    if (!detailEl || !detailEmptyEl || !endpoint) {
      clearDetail();
      return;
    }
    detailEmptyEl.hidden = true;
    detailEl.hidden = false;
    const source = endpoint.source_path
      ? `${endpoint.source_path}${endpoint.source_line ? ":" + endpoint.source_line : ""}`
      : "";
    detailEl.innerHTML = (
      '<div class="api-detail-head">' +
        `<span class="api-method ${cssMethod(endpoint.method)}">${escapeHtml(endpoint.method)}</span>` +
        `<span class="api-auth-badge ${endpoint.auth_kind === "public" ? "is-public" : ""}">${escapeHtml(endpoint.auth)}</span>` +
      "</div>" +
      `<h3><code>${escapeHtml(endpoint.path)}</code></h3>` +
      `<p>${escapeHtml(endpoint.doc || endpoint.description || endpoint.summary)}</p>` +
      '<dl class="api-detail-facts">' +
        `<div><dt>Tag</dt><dd>${escapeHtml(endpoint.tag)}</dd></div>` +
        `<div><dt>Operation</dt><dd><code>${escapeHtml(endpoint.operation_id)}</code></dd></div>` +
        `<div><dt>Handler</dt><dd><code>${escapeHtml(endpoint.handler || "unbekannt")}</code></dd></div>` +
        (source ? `<div><dt>Source</dt><dd><code>${escapeHtml(source)}</code></dd></div>` : "") +
        `<div><dt>Rate-Limit</dt><dd>${escapeHtml(rateLimitText(endpoint))}</dd></div>` +
        `<div><dt>Parameter</dt><dd>${escapeHtml(parameterText(endpoint.parameters))}</dd></div>` +
      "</dl>" +
      '<h4>Parameter</h4>' +
      '<table class="api-param-table"><thead><tr><th>Name</th><th>Ort</th><th>Typ</th><th>Pflicht</th></tr></thead>' +
        `<tbody>${parameterRows(endpoint)}</tbody></table>` +
      '<h4>Statuscodes</h4>' +
      `<div class="api-response-pills">${responsePills(endpoint)}</div>` +
      '<h4>cURL</h4>' +
      `<pre class="api-curl"><code>${escapeHtml(endpoint.curl)}</code></pre>` +
      '<div class="api-detail-actions">' +
        `<a href="${escapeHtml(openapiUrl)}">OpenAPI YAML</a>` +
        (
          endpoint.method === "GET" && (!endpoint.path_parameters || endpoint.path_parameters.length === 0)
            ? `<a href="${escapeHtml(endpoint.path)}">GET oeffnen</a>`
            : ""
        ) +
        '<button type="button" data-copy-curl>cURL kopieren</button>' +
      "</div>"
    );
  }

  function clearDetail() {
    if (!detailEl || !detailEmptyEl) return;
    detailEl.hidden = true;
    detailEl.innerHTML = "";
    detailEmptyEl.hidden = false;
  }

  function applyQuery(query) {
    state.query = query;
    if (input) input.value = query;
    renderResults();
  }

  function wireEvents() {
    if (input) {
      input.addEventListener("input", () => {
        state.query = input.value;
        renderResults();
      });
    }
    if (clearButton) {
      clearButton.addEventListener("click", () => {
        state.query = "";
        state.tag = "";
        if (input) input.value = "";
        renderTags();
        renderResults();
        input && input.focus();
      });
    }
    app.addEventListener("click", (event) => {
      const queryButton = event.target.closest("[data-api-query]");
      if (queryButton) {
        applyQuery(queryButton.dataset.apiQuery || "");
        return;
      }
      const tagButton = event.target.closest("[data-tag]");
      if (tagButton) {
        state.tag = tagButton.dataset.tag || "";
        renderTags();
        renderResults();
        return;
      }
      const endpointButton = event.target.closest("[data-endpoint-id]");
      if (endpointButton) {
        state.selectedId = endpointButton.dataset.endpointId || "";
        renderDetail(state.selectedId);
        renderSelectedCard();
        return;
      }
      const copyButton = event.target.closest("[data-copy-curl]");
      if (copyButton) {
        const endpoint = selectedEndpoint(state.selectedId);
        if (!endpoint || !navigator.clipboard) return;
        navigator.clipboard.writeText(endpoint.curl).then(() => {
          copyButton.textContent = "Kopiert";
          window.setTimeout(() => {
            copyButton.textContent = "cURL kopieren";
          }, 1200);
        });
      }
    });
  }

  function init(catalog) {
    state.catalog = catalog;
    renderTags();
    renderResults();
  }

  wireEvents();
  fetch(catalogUrl, { headers: { Accept: "application/json" } })
    .then((response) => {
      if (!response.ok) throw new Error("Catalog request failed");
      return response.json();
    })
    .then(init)
    .catch(() => {
      if (countEl) countEl.textContent = "Catalog konnte nicht geladen werden";
      if (resultsList) {
        resultsList.innerHTML = '<div class="api-empty-state">OpenAPI YAML ist erreichbar, aber der Suchkatalog konnte nicht geladen werden.</div>';
      }
    });
})();
