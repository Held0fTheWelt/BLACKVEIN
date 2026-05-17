(function () {
  "use strict";

  var state = {
    prompts: [],
    categories: [],
    promptTypes: [],
    domains: [],
    tags: [],
    status: {},
    selected: null,
    selectedKey: "",
    dirty: false
  };

  var PRESETS = {
    important: { tag: "important" },
    "runtime-prompts": { prompt_type: "runtime_prompt" },
    "runtime-fragments": { prompt_type: "runtime_fragment" },
    "game-ui": { prompt_type: "game_text" },
    localization: { tag: "localization" },
    readouts: { prompt_type: "readout_text" },
    edited: { drift: "edited" },
    all: {}
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var node = $(id);
    if (node) node.textContent = value == null || value === "" ? "-" : String(value);
  }

  function show(kind, msg) {
    var err = $("manage-ps-banner");
    var ok = $("manage-ps-success");
    if (err) {
      err.style.display = "none";
      err.textContent = "";
    }
    if (ok) {
      ok.style.display = "none";
      ok.textContent = "";
    }
    if (!msg) return;
    if (kind === "ok" && ok) {
      ok.style.display = "";
      ok.textContent = msg;
    } else if (err) {
      err.style.display = "";
      err.textContent = msg;
    }
  }

  function parseError(err) {
    if (!err) return "Request failed";
    if (typeof err.message === "string" && err.message) return err.message;
    if (err.body && window.ManageAuth && typeof window.ManageAuth.formatApiErrorMessage === "function") {
      return window.ManageAuth.formatApiErrorMessage(err.body, err.status);
    }
    return "Request failed";
  }

  function api(path, opts) {
    return window.ManageAuth.apiFetchWithAuth(path, opts).then(function (payload) {
      return payload && payload.data ? payload.data : {};
    });
  }

  function setJson(payload) {
    var box = $("manage-ps-json");
    if (!box) return;
    box.textContent = JSON.stringify(payload || {}, null, 2);
    if (window.ManageUI && typeof window.ManageUI.jsonViewer === "function") {
      window.ManageUI.jsonViewer(box, payload || {});
    }
  }

  function isEditedFromSeed(row) {
    return !!(row && row.seed_content_hash && row.current_content_hash && row.seed_content_hash !== row.current_content_hash);
  }

  function renderPills() {
    var status = state.status || {};
    var prompts = state.prompts || [];
    var active = status.active_prompts == null
      ? prompts.filter(function (row) { return row.is_active; }).length
      : status.active_prompts;
    var total = status.total_prompts == null ? prompts.length : status.total_prompts;
    var categories = status.categories || state.categories || [];
    var promptTypes = status.prompt_types || state.promptTypes || [];
    var domains = status.domains || state.domains || [];
    var edited = prompts.filter(isEditedFromSeed).length;
    setText("manage-ps-total-pill", total);
    setText("manage-ps-active-pill", active);
    setText("manage-ps-categories-pill", categories.length);
    setText("manage-ps-types-pill", promptTypes.length);
    setText("manage-ps-domains-pill", domains.length);
    setText("manage-ps-drift-count-pill", edited);
    var driftPill = $("manage-ps-drift-pill");
    if (driftPill) driftPill.hidden = edited <= 0;
  }

  function renderRuntimeLines() {
    var ul = $("manage-ps-runtime-lines");
    if (!ul) return;
    var status = state.status || {};
    var selected = state.selected || {};
    var lines = [
      "Active prompts in bundle: " + (status.active_prompts == null ? "-" : status.active_prompts),
      "Seeded prompts: " + (status.seeded_prompts == null ? "-" : status.seeded_prompts),
      "Live source: backend prompt_store_prompts table via resolved runtime config prompt_store bundle.",
      "Fallback source for tests and bootstrap: repo prompts JSON files.",
      selected.prompt_key
        ? "Selected prompt active: " + (selected.is_active ? "yes" : "no")
        : "Select a prompt to inspect runtime state."
    ];
    ul.innerHTML = "";
    lines.forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      ul.appendChild(li);
    });
  }

  function renderStatus(payload) {
    state.status = payload || {};
    setText("manage-ps-seed-root", state.status.seed_root || "-");
    setText(
      "manage-ps-seed-overwrite-default",
      state.status.seed_overwrite_default ? "overwrite existing rows" : "preserve existing rows"
    );
    renderPills();
    renderRuntimeLines();
    if (!state.selected) {
      setJson({ status: state.status, prompts: state.prompts });
    }
  }

  function renderSelectOptions(selectId, values, allLabel) {
    var select = $(selectId);
    if (!select) return;
    var previous = select.value || "";
    select.innerHTML = "";
    var all = document.createElement("option");
    all.value = "";
    all.textContent = allLabel;
    select.appendChild(all);
    (values || []).forEach(function (value) {
      var option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    select.value = previous;
  }

  function renderFacetFilters() {
    renderSelectOptions("manage-ps-category-filter", state.categories || [], "All categories");
    renderSelectOptions("manage-ps-type-filter", state.promptTypes || [], "All types");
    renderSelectOptions("manage-ps-domain-filter", state.domains || [], "All domains");
    renderSelectOptions("manage-ps-tag-filter", state.tags || [], "All tags");
    renderPresetButtons();
  }

  function filtersMatchPreset(filters, preset) {
    var keys = ["category", "prompt_type", "domain", "tag", "drift", "q"];
    return keys.every(function (key) {
      return (filters[key] || "") === (preset[key] || "");
    });
  }

  function renderPresetButtons() {
    var filters = currentFilters();
    document.querySelectorAll("[data-ps-preset]").forEach(function (btn) {
      var name = btn.getAttribute("data-ps-preset") || "all";
      var preset = PRESETS[name] || {};
      btn.classList.toggle("is-active", filtersMatchPreset(filters, preset));
    });
  }

  function promptSubtitle(row) {
    var parts = [];
    if (row.prompt_key) parts.push(row.prompt_key);
    if (row.prompt_type) parts.push(row.prompt_type);
    if (row.domain) parts.push(row.domain);
    if (row.template_length != null) parts.push(String(row.template_length) + " chars");
    if (!row.is_active) parts.push("inactive");
    if (isEditedFromSeed(row)) parts.push("edited");
    return parts.join(" | ");
  }

  function renderPromptList() {
    var list = $("manage-ps-prompt-list");
    var empty = $("manage-ps-empty");
    if (!list) return;
    list.innerHTML = "";
    var rows = state.prompts || [];
    if (empty) empty.hidden = rows.length > 0;
    rows.forEach(function (row) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "manage-ps-item";
      btn.dataset.promptKey = row.prompt_key || "";
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-selected", row.prompt_key === state.selectedKey ? "true" : "false");
      if (row.prompt_key === state.selectedKey) btn.classList.add("is-active");

      var top = document.createElement("span");
      top.className = "manage-ps-item-top";
      var name = document.createElement("span");
      name.className = "manage-ps-item-name";
      name.textContent = row.name || row.prompt_key || "(unnamed)";
      var cat = document.createElement("span");
      cat.className = "manage-ps-item-cat";
      cat.textContent = row.category || "uncategorized";
      top.appendChild(name);
      top.appendChild(cat);
      btn.appendChild(top);

      var desc = document.createElement("span");
      desc.className = "manage-ps-item-desc";
      desc.textContent = row.description || "";
      btn.appendChild(desc);

      var meta = document.createElement("span");
      meta.className = "manage-ps-item-meta";
      meta.textContent = promptSubtitle(row);
      btn.appendChild(meta);

      if (row.tags && row.tags.length) {
        var tagRow = document.createElement("span");
        tagRow.className = "manage-ps-tag-row";
        row.tags.slice(0, 5).forEach(function (tag) {
          var chip = document.createElement("span");
          chip.className = "manage-ps-tag-chip";
          chip.textContent = tag;
          tagRow.appendChild(chip);
        });
        btn.appendChild(tagRow);
      }

      btn.addEventListener("click", function () {
        selectPrompt(row.prompt_key);
      });
      list.appendChild(btn);
    });
  }

  function currentFilters() {
    return {
      category: ($("manage-ps-category-filter") || {}).value || "",
      prompt_type: ($("manage-ps-type-filter") || {}).value || "",
      domain: ($("manage-ps-domain-filter") || {}).value || "",
      tag: ($("manage-ps-tag-filter") || {}).value || "",
      drift: ($("manage-ps-drift-filter") || {}).value || "",
      q: ($("manage-ps-search") || {}).value || ""
    };
  }

  function applyFilters(filters) {
    var next = filters || {};
    setValue("manage-ps-category-filter", next.category || "");
    setValue("manage-ps-type-filter", next.prompt_type || "");
    setValue("manage-ps-domain-filter", next.domain || "");
    setValue("manage-ps-tag-filter", next.tag || "");
    setValue("manage-ps-drift-filter", next.drift || "");
    setValue("manage-ps-search", next.q || "");
    renderPresetButtons();
  }

  function listPath() {
    var filters = currentFilters();
    var params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.prompt_type) params.set("prompt_type", filters.prompt_type);
    if (filters.domain) params.set("domain", filters.domain);
    if (filters.tag) params.set("tag", filters.tag);
    if (filters.drift) params.set("drift", filters.drift);
    if (filters.q) params.set("q", filters.q);
    var qs = params.toString();
    return "/api/v1/admin/prompt-store/prompts" + (qs ? "?" + qs : "");
  }

  function loadList() {
    return api(listPath()).then(function (data) {
      state.prompts = data.prompts || [];
      state.categories = data.categories || [];
      state.promptTypes = data.prompt_types || [];
      state.domains = data.domains || [];
      state.tags = data.tags || [];
      renderFacetFilters();
      renderPromptList();
      renderPills();
      setJson({ status: state.status, prompts: state.prompts, selected: state.selected });
      if (!state.selectedKey && state.prompts.length) {
        return selectPrompt(state.prompts[0].prompt_key);
      }
      if (state.selectedKey) {
        renderPromptList();
      }
      return null;
    });
  }

  function loadStatus() {
    return api("/api/v1/admin/prompt-store/status").then(renderStatus);
  }

  function refreshAll() {
    return loadStatus().then(loadList);
  }

  function setEditorTemplate(template) {
    var editor = $("manage-ps-editor");
    var hidden = $("manage-ps-template");
    var value = template == null ? "" : String(template);
    if (editor) editor.textContent = value;
    if (hidden) hidden.value = value;
  }

  function readEditorTemplate() {
    var editor = $("manage-ps-editor");
    if (!editor) return "";
    var value = editor.innerText == null ? editor.textContent || "" : editor.innerText;
    value = value.replace(/\u00a0/g, " ").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    return value.replace(/\n\n$/, "\n");
  }

  function setValue(id, value) {
    var node = $(id);
    if (node) node.value = value == null ? "" : String(value);
  }

  function setChecked(id, value) {
    var node = $(id);
    if (node) node.checked = !!value;
  }

  function renderVariableButtons(variables) {
    var wrap = $("manage-ps-variable-buttons");
    if (!wrap) return;
    wrap.innerHTML = "";
    (variables || []).forEach(function (variable) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "manage-ps-variable-chip";
      btn.textContent = "{" + variable + "}";
      btn.addEventListener("click", function () {
        insertAtEditor("{" + variable + "}");
      });
      wrap.appendChild(btn);
    });
    if (!variables || !variables.length) {
      var empty = document.createElement("span");
      empty.className = "muted";
      empty.textContent = "No variables";
      wrap.appendChild(empty);
    }
  }

  function renderSelected(prompt) {
    state.selected = prompt || null;
    state.selectedKey = prompt ? prompt.prompt_key : "";
    state.dirty = false;

    var empty = $("manage-ps-editor-empty");
    var wrap = $("manage-ps-editor-wrap");
    if (empty) empty.hidden = !!prompt;
    if (wrap) wrap.hidden = !prompt;
    if (!prompt) {
      setText("manage-ps-editor-title", "Select a prompt");
      setJson({ status: state.status, prompts: state.prompts });
      return;
    }

    setText("manage-ps-editor-title", prompt.name || prompt.prompt_key);
    setText("manage-ps-editor-summary", prompt.description || "No description.");
    setValue("manage-ps-key", prompt.prompt_key);
    setValue("manage-ps-name", prompt.name || "");
    setValue("manage-ps-category", prompt.category || "");
    setValue("manage-ps-type", prompt.prompt_type || "");
    setValue("manage-ps-domain", prompt.domain || "");
    setValue("manage-ps-description", prompt.description || "");
    setValue("manage-ps-variables", (prompt.variables || []).join(", "));
    setValue("manage-ps-tags", (prompt.tags || []).join(", "));
    setChecked("manage-ps-active", prompt.is_active);
    setEditorTemplate(prompt.template || "");
    renderVariableButtons(prompt.variables || []);
    setText("manage-ps-key-display", prompt.prompt_key || "-");
    setText("manage-ps-source-display", [prompt.source_path, prompt.source_symbol].filter(Boolean).join(" :: ") || "-");
    setText("manage-ps-updated-display", prompt.updated_at || "-");
    setText("manage-ps-drift-display", isEditedFromSeed(prompt) ? "edited from seed" : "matches seed");
    setText("manage-ps-tags-display", (prompt.tags || []).join(", ") || "-");
    renderPromptList();
    renderRuntimeLines();
    setJson({ status: state.status, selected: prompt });
  }

  function selectPrompt(promptKey) {
    if (!promptKey) return Promise.resolve();
    return api("/api/v1/admin/prompt-store/prompts/" + encodeURIComponent(promptKey)).then(function (data) {
      renderSelected(data.prompt || null);
    }).catch(function (err) {
      show("err", parseError(err));
    });
  }

  function parseVariables(raw) {
    return String(raw || "")
      .split(/[,\n]/)
      .map(function (item) { return item.trim(); })
      .filter(Boolean);
  }

  function saveSelected() {
    if (!state.selectedKey) {
      show("err", "Select a prompt first.");
      return Promise.resolve();
    }
    var template = readEditorTemplate();
    setValue("manage-ps-template", template);
    var payload = {
      name: ($("manage-ps-name") || {}).value || "",
      category: ($("manage-ps-category") || {}).value || "",
      prompt_type: ($("manage-ps-type") || {}).value || "",
      domain: ($("manage-ps-domain") || {}).value || "",
      description: ($("manage-ps-description") || {}).value || "",
      variables: parseVariables(($("manage-ps-variables") || {}).value || ""),
      tags: parseVariables(($("manage-ps-tags") || {}).value || ""),
      template: template,
      is_active: !!(($("manage-ps-active") || {}).checked)
    };
    return api("/api/v1/admin/prompt-store/prompts/" + encodeURIComponent(state.selectedKey), {
      method: "PATCH",
      body: JSON.stringify(payload)
    }).then(function (data) {
      renderSelected(data.prompt || null);
      return loadStatus().then(loadList).then(function () {
        show("ok", "Prompt saved.");
      });
    }).catch(function (err) {
      show("err", parseError(err));
    });
  }

  function runSeed(overwrite) {
    return api("/api/v1/admin/prompt-store/seed", {
      method: "POST",
      body: JSON.stringify({ overwrite: !!overwrite })
    }).then(function (data) {
      show(
        "ok",
        "Seed complete: " + (data.inserted || 0) + " inserted, "
          + (data.updated || 0) + " updated, "
          + (data.skipped_existing || 0) + " preserved."
      );
      return refreshAll();
    }).catch(function (err) {
      show("err", parseError(err));
    });
  }

  function insertAtEditor(text) {
    var editor = $("manage-ps-editor");
    if (!editor) return;
    editor.focus();
    if (document.queryCommandSupported && document.queryCommandSupported("insertText")) {
      document.execCommand("insertText", false, text);
    } else {
      var selection = window.getSelection();
      if (!selection || !selection.rangeCount) {
        editor.textContent += text;
      } else {
        var range = selection.getRangeAt(0);
        range.deleteContents();
        range.insertNode(document.createTextNode(text));
        range.collapse(false);
      }
    }
    state.dirty = true;
    setValue("manage-ps-template", readEditorTemplate());
  }

  function bindActions() {
    var refresh = $("manage-ps-refresh");
    if (refresh) {
      refresh.addEventListener("click", function () {
        show(null, "");
        refreshAll().catch(function (err) { show("err", parseError(err)); });
      });
    }
    var seedDefault = $("manage-ps-seed-default");
    if (seedDefault) {
      seedDefault.addEventListener("click", function () {
        runSeed(false);
      });
    }
    var runSeedBtn = $("manage-ps-run-seed");
    if (runSeedBtn) {
      runSeedBtn.addEventListener("click", function () {
        runSeed(!!(($("manage-ps-overwrite") || {}).checked));
      });
    }
    var save = $("manage-ps-save");
    if (save) {
      save.addEventListener("click", function () {
        saveSelected();
      });
    }
    ["manage-ps-category-filter", "manage-ps-type-filter", "manage-ps-domain-filter", "manage-ps-tag-filter", "manage-ps-drift-filter"].forEach(function (id) {
      var filter = $(id);
      if (filter) {
        filter.addEventListener("change", function () {
          renderPresetButtons();
          loadList().catch(function (err) { show("err", parseError(err)); });
        });
      }
    });
    document.querySelectorAll("[data-ps-preset]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var name = btn.getAttribute("data-ps-preset") || "all";
        applyFilters(PRESETS[name] || {});
        loadList().catch(function (err) { show("err", parseError(err)); });
      });
    });
    var search = $("manage-ps-search");
    if (search) {
      var timer = null;
      search.addEventListener("input", function () {
        if (timer) window.clearTimeout(timer);
        timer = window.setTimeout(function () {
          renderPresetButtons();
          loadList().catch(function (err) { show("err", parseError(err)); });
        }, 180);
      });
    }
    var editor = $("manage-ps-editor");
    if (editor) {
      editor.addEventListener("input", function () {
        state.dirty = true;
        setValue("manage-ps-template", readEditorTemplate());
      });
    }
    document.querySelectorAll("[data-ps-command]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var command = btn.getAttribute("data-ps-command");
        var editorNode = $("manage-ps-editor");
        if (editorNode) editorNode.focus();
        if (command === "undo" || command === "redo") {
          document.execCommand(command, false, null);
          setValue("manage-ps-template", readEditorTemplate());
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;
    window.ManageAuth.ensureAuth().then(function () {
      bindActions();
      return refreshAll();
    }).catch(function (err) {
      show("err", parseError(err));
    });
  });
})();
