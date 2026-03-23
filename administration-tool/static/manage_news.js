/**
 * News management: list (with drafts), filters (status, language), pagination,
 * create/edit with language tabs (de/en), translation status, save/publish/unpublish/delete,
 * submit-review, approve, auto-translate. Uses real backend APIs.
 * Initializes on DOMContentLoaded; requires ManageAuth (loaded before this script in extra_scripts).
 */
(function() {
    var apiRef = null;
    var LANGS = ["de", "en"];
    var DEFAULT_LANG = "de";

    function $(id) { return id ? document.getElementById(id) : null; }
    function formatDate(iso) {
        if (!iso) return "";
        var d = new Date(iso);
        return isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { dateStyle: "short" });
    }

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    function statusBadge(status) {
        var c = "badge";
        if (status === "published") c += " badge-success";
        else if (status === "approved" || status === "review_required") c += " badge-warning";
        else if (status === "machine_draft" || status === "outdated") c += " badge-info";
        else c += " badge-secondary";
        return "<span class=\"" + c + "\">" + escapeHtml(status || "missing") + "</span>";
    }

    var state = {
        page: 1,
        total: 0,
        perPage: 20,
        totalPages: 0,
        selectedId: null,
        items: [],
        currentLang: DEFAULT_LANG,
        article: null,
        translations: null,
        translationData: { de: null, en: null },
    };

    function getListParams() {
        var status = ($("manage-news-status") || {}).value;
        var params = {
            page: state.page,
            limit: state.perPage,
            q: ($("manage-news-q") || {}).value.trim() || undefined,
            category: ($("manage-news-category") || {}).value.trim() || undefined,
            sort: ($("manage-news-sort") || {}).value || "published_at",
            direction: ($("manage-news-direction") || {}).value || "desc",
            include_drafts: "1",
        };
        var lang = ($("manage-news-lang") || {}).value;
        if (lang) params.lang = lang;
        if (status === "published") {
            params.published_only = "1";
            delete params.include_drafts;
        }
        return params;
    }

    function buildListUrl(params) {
        var parts = [];
        for (var k in params) if (params[k] !== undefined && params[k] !== "") parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(params[k]));
        return "/api/v1/news" + (parts.length ? "?" + parts.join("&") : "");
    }

    function showLoading(show) {
        var loading = $("manage-news-loading");
        var wrap = $("manage-news-table-wrap");
        var empty = $("manage-news-empty");
        var err = $("manage-news-error");
        var pag = $("manage-news-pagination");
        if (loading) loading.hidden = !show;
        if (wrap) wrap.hidden = true;
        if (empty) empty.hidden = true;
        if (err) err.hidden = true;
        if (pag) pag.hidden = true;
    }

    function showError(msg) {
        showLoading(false);
        var wrap = $("manage-news-table-wrap");
        var empty = $("manage-news-empty");
        var err = $("manage-news-error");
        var pag = $("manage-news-pagination");
        if (wrap) wrap.hidden = true;
        if (empty) empty.hidden = true;
        if (err) { err.textContent = msg || "Failed to load."; err.hidden = false; }
        if (pag) pag.hidden = true;
    }

    function renderList(items, page, total, perPage) {
        showLoading(false);
        state.items = items || [];
        state.total = total || 0;
        state.perPage = perPage || 20;
        state.totalPages = perPage ? Math.ceil(total / perPage) : 0;

        var err = $("manage-news-error");
        var empty = $("manage-news-empty");
        var wrap = $("manage-news-table-wrap");
        var tbody = $("manage-news-tbody");
        var pag = $("manage-news-pagination");
        var pagInfo = $("manage-news-pagination-info");
        var prevBtn = $("manage-news-prev");
        var nextBtn = $("manage-news-next");

        if (err) err.hidden = true;
        if (!items || items.length === 0) {
            if (empty) empty.hidden = false;
            if (wrap) wrap.hidden = true;
            if (pag) pag.hidden = true;
            return;
        }
        if (empty) empty.hidden = true;
        if (wrap) wrap.hidden = false;
        if (tbody) {
            tbody.innerHTML = "";
            items.forEach(function(item) {
                var tr = document.createElement("tr");
                tr.dataset.id = item.id;
                if (state.selectedId === item.id) tr.classList.add("selected");
                var statuses = item.translation_statuses || {};
                tr.innerHTML =
                    "<td>" + escapeHtml(item.title || "") + "</td>" +
                    "<td>" + (item.is_published ? "Published" : "Draft") + "</td>" +
                    "<td>" + statusBadge(statuses.de) + "</td>" +
                    "<td>" + statusBadge(statuses.en) + "</td>" +
                    "<td>" + escapeHtml(item.category || "") + "</td>" +
                    "<td>" + formatDate(item.updated_at || item.created_at) + "</td>";
                tr.addEventListener("click", function() { selectArticle(item.id); });
                tbody.appendChild(tr);
            });
        }
        if (pag) {
            pag.hidden = state.totalPages <= 1;
            if (pagInfo) pagInfo.textContent = "Page " + page + " of " + (state.totalPages || 1) + " (" + total + " total)";
            if (prevBtn) prevBtn.disabled = page <= 1;
            if (nextBtn) nextBtn.disabled = page >= state.totalPages;
        }
    }

    function fetchList() {
        if (!apiRef) return;
        var params = getListParams();
        showLoading(true);
        apiRef(buildListUrl(params))
            .then(function(data) {
                var items = data.items || [];
                var status = ($("manage-news-status") || {}).value;
                if (status === "draft") {
                    items = items.filter(function(i) { return !i.is_published; });
                }
                var total = (status === "draft") ? items.length : (typeof data.total === "number" ? data.total : items.length);
                var page = typeof data.page === "number" ? data.page : 1;
                var perPage = typeof data.per_page === "number" ? data.per_page : 20;
                renderList(items, page, total, perPage);
            })
            .catch(function(e) {
                showError(typeof e === "object" && e.message ? e.message : "Failed to load news.");
            });
    }

    function setTab(lang) {
        state.currentLang = lang;
        var tabs = document.querySelectorAll(".manage-news-tab");
        var panels = document.querySelectorAll(".manage-news-tab-panel");
        tabs.forEach(function(t) {
            t.classList.toggle("active", t.getAttribute("data-lang") === lang);
            t.setAttribute("aria-selected", t.getAttribute("data-lang") === lang ? "true" : "false");
        });
        panels.forEach(function(p) {
            var show = p.getAttribute("data-lang") === lang;
            p.classList.toggle("active", show);
            p.hidden = !show;
        });
        fillTranslationForm(lang);
        updateTranslationActions(lang);
    }

    function fillTranslationForm(lang) {
        var data = state.translationData[lang];
        var pre = "manage-news-" + lang + "-";
        ($(pre + "title") || {}).value = data ? (data.title || "") : "";
        ($(pre + "slug") || {}).value = data ? (data.slug || "") : "";
        ($(pre + "summary") || {}).value = data ? (data.summary || "") : "";
        ($(pre + "content") || {}).value = data ? (data.content || "") : "";
    }

    function collectTranslationForm(lang) {
        var pre = "manage-news-" + lang + "-";
        return {
            title: ($(pre + "title") || {}).value.trim(),
            slug: ($(pre + "slug") || {}).value.trim(),
            summary: ($(pre + "summary") || {}).value.trim() || null,
            content: ($(pre + "content") || {}).value.trim(),
        };
    }

    function updateTranslationStatusDisplay() {
        var el = $("manage-news-translation-status");
        if (!el) return;
        if (!state.translations || !state.article) {
            el.innerHTML = "";
            return;
        }
        var items = state.translations.items || [];
        var html = [];
        items.forEach(function(t) {
            html.push("<span class=\"manage-news-status-item\"><strong>" + escapeHtml((t.language_code || "").toUpperCase()) + "</strong>: " + statusBadge(t.translation_status) + "</span>");
        });
        el.innerHTML = html.length ? html.join(" ") : "";
    }

    function updateTranslationActions(lang) {
        var data = state.translationData[lang];
        var status = data ? data.translation_status : "missing";
        var pubBtn = $("manage-news-publish-btn");
        var unpubBtn = $("manage-news-unpublish-btn");
        var pubTransBtn = $("manage-news-publish-translation-btn");
        var submitReviewBtn = $("manage-news-submit-review-btn");
        var approveBtn = $("manage-news-approve-btn");
        var autoBtn = $("manage-news-auto-translate-btn");
        if (pubBtn) pubBtn.hidden = !state.article || !!state.article.is_published;
        if (unpubBtn) unpubBtn.hidden = !state.article || !state.article.is_published;
        if (pubTransBtn) pubTransBtn.hidden = !data || status === "published";
        if (submitReviewBtn) submitReviewBtn.hidden = !data || status === "review_required" || status === "approved" || status === "published";
        if (approveBtn) approveBtn.hidden = !data || status !== "review_required";
        if (autoBtn) autoBtn.hidden = !state.selectedId;
    }

    function selectArticle(id) {
        state.selectedId = id;
        state.article = null;
        state.translations = null;
        state.translationData = { de: null, en: null };

        var tbody = $("manage-news-tbody");
        if (tbody) {
            [].forEach.call(tbody.querySelectorAll("tr"), function(tr) {
                tr.classList.toggle("selected", parseInt(tr.dataset.id, 10) === id);
            });
        }
        var form = $("manage-news-form");
        var empty = $("manage-news-editor-empty");
        if (!id) {
            if (form) form.hidden = true;
            if (empty) empty.hidden = false;
            return;
        }
        if (empty) empty.hidden = true;
        if (form) form.hidden = false;

        apiRef("/api/v1/news/" + id)
            .then(function(article) {
                state.article = article;
                ($("manage-news-id") || {}).value = article.id;
                ($("manage-news-category-edit") || {}).value = article.category || "";
                ($("manage-news-cover") || {}).value = article.cover_image || "";
                state.translationData[article.language_code || DEFAULT_LANG] = {
                    title: article.title,
                    slug: article.slug,
                    summary: article.summary,
                    content: article.content,
                    translation_status: "published",
                };
                return apiRef("/api/v1/news/" + id + "/translations");
            })
            .then(function(res) {
                state.translations = res;
                (res.items || []).forEach(function(t) {
                    state.translationData[t.language_code] = state.translationData[t.language_code] || {
                        title: t.title,
                        slug: t.slug,
                        summary: t.summary,
                        translation_status: t.translation_status,
                    };
                });
                setTab(state.currentLang);
                updateTranslationStatusDisplay();
                updateDiscussionDisplay();
                fetchRelatedThreads();
                fetchSuggestedThreads();
                ($("manage-news-editor-title") || {}).textContent = "Edit article";
                var pubBtn = $("manage-news-publish-btn");
                var unpubBtn = $("manage-news-unpublish-btn");
                if (pubBtn) pubBtn.hidden = !!(state.article && state.article.is_published);
                if (unpubBtn) unpubBtn.hidden = !(state.article && state.article.is_published);
            })
            .catch(function(e) {
                showError(typeof e === "object" && e.message ? e.message : "Failed to load article.");
            });
    }

    function updateDiscussionDisplay() {
        var slugEl = $("manage-news-discussion-slug");
        var unlinkBtn = $("manage-news-discussion-unlink");
        var threadIdInput = $("manage-news-discussion-thread-id");
        if (slugEl) slugEl.textContent = (state.article && state.article.discussion_thread_slug) ? state.article.discussion_thread_slug : "—";
        if (unlinkBtn) unlinkBtn.hidden = !(state.article && state.article.discussion_thread_id);
        if (threadIdInput) threadIdInput.value = "";
    }

    function fetchRelatedThreads() {
        var id = ($("manage-news-id") || {}).value;
        if (!id || !apiRef) return;
        var listEl = $("manage-news-related-threads-list");
        if (!listEl) return;
        apiRef("/api/v1/news/" + id + "/related-threads")
            .then(function(data) {
                var items = data.items || [];
                listEl.textContent = "";
                if (!items.length) { listEl.textContent = "None."; return; }
                items.forEach(function(t) {
                    var li = document.createElement("li");
                    var label = document.createTextNode(t.slug || ("Thread #" + t.thread_id));
                    var btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "btn btn-ghost btn-xs";
                    btn.textContent = "Remove";
                    btn.addEventListener("click", (function(tid) {
                        return function() { onRelatedThreadRemove(tid); };
                    })(t.thread_id));
                    li.appendChild(label);
                    li.appendChild(document.createTextNode(" "));
                    li.appendChild(btn);
                    listEl.appendChild(li);
                });
            })
            .catch(function(e) {
                if (listEl) listEl.textContent = "Failed to load related threads.";
            });
    }

    function onRelatedThreadAdd() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        var input = $("manage-news-related-thread-id");
        var raw = input && input.value ? input.value.trim() : "";
        var tid = parseInt(raw, 10);
        if (!raw || isNaN(tid) || tid < 1) {
            showFormError("Enter a valid thread ID (integer \u2265 1).");
            return;
        }
        apiRef("/api/v1/news/" + id + "/related-threads", { method: "POST", body: JSON.stringify({ thread_id: tid }) })
            .then(function() {
                showFormSuccess("Related thread added.");
                if (input) input.value = "";
                fetchRelatedThreads();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Add failed.");
            });
    }

    function onRelatedThreadRemove(threadId) {
        var id = ($("manage-news-id") || {}).value;
        if (!id || !threadId) return;
        apiRef("/api/v1/news/" + id + "/related-threads/" + threadId, { method: "DELETE" })
            .then(function() {
                fetchRelatedThreads();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Remove failed.");
            });
    }

    function onDiscussionLink() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        var threadIdInput = $("manage-news-discussion-thread-id");
        var raw = threadIdInput && threadIdInput.value ? threadIdInput.value.trim() : "";
        var tid = parseInt(raw, 10);
        if (!raw || isNaN(tid) || tid < 1) {
            showFormError("Enter a valid thread ID (integer ≥ 1).");
            return;
        }
        apiRef("/api/v1/news/" + id + "/discussion-thread", { method: "POST", body: JSON.stringify({ discussion_thread_id: tid }) })
            .then(function() {
                showFormSuccess("Discussion thread linked.");
                return apiRef("/api/v1/news/" + id);
            })
            .then(function(article) {
                state.article = article;
                updateDiscussionDisplay();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Link failed.");
            });
    }

    function onDiscussionUnlink() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        apiRef("/api/v1/news/" + id + "/discussion-thread", { method: "DELETE" })
            .then(function() {
                showFormSuccess("Discussion thread unlinked.");
                return apiRef("/api/v1/news/" + id);
            })
            .then(function(article) {
                state.article = article;
                updateDiscussionDisplay();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Unlink failed.");
            });
    }

    function renderRelatedThreadsList(items) {
        var listEl = $("manage-news-related-threads-list");
        if (!listEl) return;
        while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
        if (!items || items.length === 0) {
            var empty = document.createTextNode("No related threads.");
            listEl.appendChild(empty);
            return;
        }
        var ul = document.createElement("ul");
        ul.className = "manage-related-threads-ul";
        items.forEach(function(t) {
            if (!t) return;
            var li = document.createElement("li");
            li.className = "manage-related-thread-item";
            var span = document.createElement("span");
            span.textContent = (t.title || ("Thread #" + t.id)) + (t.id ? " (#" + t.id + ")" : "");
            li.appendChild(span);
            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "btn btn-danger btn-sm";
            removeBtn.textContent = "Remove";
            removeBtn.setAttribute("aria-label", "Remove related thread");
            (function(tid) {
                removeBtn.addEventListener("click", function() {
                    onRelatedThreadRemove(tid);
                });
            }(t.id));
            li.appendChild(removeBtn);
            ul.appendChild(li);
        });
        listEl.appendChild(ul);
    }

    function fetchRelatedThreads() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        apiRef("/api/v1/news/" + id + "/related-threads")
            .then(function(data) {
                renderRelatedThreadsList(data.items || []);
            })
            .catch(function() {
                var listEl = $("manage-news-related-threads-list");
                if (listEl) listEl.textContent = "Failed to load related threads.";
            });
    }

    function renderSuggestedThreadsList(items) {
        var listEl = $("manage-news-suggested-threads-list");
        if (!listEl) return;
        while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
        if (!items || items.length === 0) {
            var empty = document.createTextNode("No suggestions.");
            listEl.appendChild(empty);
            return;
        }
        var ul = document.createElement("ul");
        ul.className = "manage-suggested-threads-ul";
        items.forEach(function(t) {
            if (!t) return;
            var li = document.createElement("li");
            li.className = "manage-suggested-thread-item";
            var span = document.createElement("span");
            span.textContent = (t.title || ("Thread #" + t.id)) + " (#" + t.id + ")";
            li.appendChild(span);
            var addBtn = document.createElement("button");
            addBtn.type = "button";
            addBtn.className = "btn btn-ghost btn-sm";
            addBtn.textContent = "Add as related";
            addBtn.setAttribute("aria-label", "Add this suggested thread as related");
            (function(tid) {
                addBtn.addEventListener("click", function() {
                    onRelatedThreadAdd(tid);
                });
            }(t.id));
            li.appendChild(addBtn);
            ul.appendChild(li);
        });
        listEl.appendChild(ul);
    }

    function fetchSuggestedThreads() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        apiRef("/api/v1/news/" + id + "/suggested-threads")
            .then(function(data) {
                renderSuggestedThreadsList(data.items || []);
            })
            .catch(function() {
                var listEl = $("manage-news-suggested-threads-list");
                if (listEl) listEl.textContent = "Failed to load suggested threads.";
            });
    }

    function onRelatedThreadAdd(threadIdFromSuggested) {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        var tid;
        if (threadIdFromSuggested) {
            tid = threadIdFromSuggested;
        } else {
            var input = $("manage-news-related-thread-id");
            var raw = input && input.value ? input.value.trim() : "";
            tid = parseInt(raw, 10);
            if (!raw || isNaN(tid) || tid < 1) {
                showFormError("Enter a valid thread ID (integer \u2265 1).");
                return;
            }
        }
        apiRef("/api/v1/news/" + id + "/related-threads", { method: "POST", body: JSON.stringify({ thread_id: tid }) })
            .then(function(data) {
                showFormSuccess("Related thread added.");
                var input = $("manage-news-related-thread-id");
                if (input && !threadIdFromSuggested) input.value = "";
                renderRelatedThreadsList(data.items || []);
                fetchSuggestedThreads();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Add related thread failed.");
            });
    }

    function onRelatedThreadRemove(threadId) {
        var id = ($("manage-news-id") || {}).value;
        if (!id || !threadId) return;
        if (!confirm("Remove this related thread?")) return;
        apiRef("/api/v1/news/" + id + "/related-threads/" + threadId, { method: "DELETE" })
            .then(function(data) {
                showFormSuccess("Related thread removed.");
                renderRelatedThreadsList(data.items || []);
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Remove related thread failed.");
            });
    }

    function showFormEmpty() {
        state.selectedId = null;
        state.article = null;
        state.translations = null;
        state.translationData = { de: null, en: null };
        ($("manage-news-id") || {}).value = "";
        ($("manage-news-category-edit") || {}).value = "";
        ($("manage-news-cover") || {}).value = "";
        LANGS.forEach(function(lang) {
            var pre = "manage-news-" + lang + "-";
            ($(pre + "title") || {}).value = "";
            ($(pre + "slug") || {}).value = "";
            ($(pre + "summary") || {}).value = "";
            ($(pre + "content") || {}).value = "";
        });
        var form = $("manage-news-form");
        var empty = $("manage-news-editor-empty");
        if (form) form.hidden = true;
        if (empty) empty.hidden = false;
        updateDiscussionDisplay();
        renderRelatedThreadsList([]);
        ($("manage-news-editor-title") || {}).textContent = "Create / Edit";
    }

    function showFormSuccess(msg) {
        var el = $("manage-news-form-success");
        var err = $("manage-news-form-error");
        if (err) { err.hidden = true; err.textContent = ""; }
        if (el) { el.textContent = msg || "Saved."; el.hidden = false; }
        setTimeout(function() { if (el) el.hidden = true; }, 3000);
    }

    function showFormError(msg) {
        var el = $("manage-news-form-error");
        var ok = $("manage-news-form-success");
        if (ok) ok.hidden = true;
        if (el) { el.textContent = msg || "Error."; el.hidden = false; }
    }

    function onSave(e) {
        e.preventDefault();
        var idEl = $("manage-news-id");
        var id = (idEl && idEl.value) ? idEl.value.trim() : "";

        if (!id) {
            var de = collectTranslationForm("de");
            if (!de.title || !de.slug || !de.content) {
                showFormError("Title, slug, and content (DE) are required for new article.");
                return;
            }
            var payload = {
                title: de.title,
                slug: de.slug,
                summary: de.summary,
                content: de.content,
                category: ($("manage-news-category-edit") || {}).value.trim() || null,
                cover_image: ($("manage-news-cover") || {}).value.trim() || null,
                is_published: false,
            };
            var saveBtn = $("manage-news-save");
            if (saveBtn) saveBtn.disabled = true;
            apiRef("/api/v1/news", { method: "POST", body: JSON.stringify(payload) })
                .then(function(article) {
                    showFormSuccess("Created.");
                    if (saveBtn) saveBtn.disabled = false;
                    state.selectedId = article.id;
                    if (idEl) idEl.value = article.id;
                    fetchList();
                    selectArticle(article.id);
                })
                .catch(function(e) {
                    showFormError(typeof e === "object" && e.message ? e.message : "Create failed.");
                    if (saveBtn) saveBtn.disabled = false;
                });
            return;
        }

        var lang = state.currentLang;
        var trans = collectTranslationForm(lang);
        var payloadBase = {
            category: ($("manage-news-category-edit") || {}).value.trim() || null,
            cover_image: ($("manage-news-cover") || {}).value.trim() || null,
        };
        var saveBtn = $("manage-news-save");
        if (saveBtn) saveBtn.disabled = true;

        Promise.all([
            apiRef("/api/v1/news/" + id, { method: "PUT", body: JSON.stringify(payloadBase) }),
            apiRef("/api/v1/news/" + id + "/translations/" + lang, {
                method: "PUT",
                body: JSON.stringify({
                    title: trans.title,
                    slug: trans.slug,
                    summary: trans.summary,
                    content: trans.content,
                }),
            }),
        ])
            .then(function() {
                showFormSuccess("Saved.");
                if (saveBtn) saveBtn.disabled = false;
                state.translationData[lang] = state.translationData[lang] || {};
                state.translationData[lang].title = trans.title;
                state.translationData[lang].slug = trans.slug;
                state.translationData[lang].summary = trans.summary;
                state.translationData[lang].content = trans.content;
                fetchList();
                return apiRef("/api/v1/news/" + id + "/translations");
            })
            .then(function(res) {
                state.translations = res;
                updateTranslationStatusDisplay();
                updateTranslationActions(lang);
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Save failed.");
                if (saveBtn) saveBtn.disabled = false;
            });
    }

    function onPublish() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        apiRef("/api/v1/news/" + id + "/publish", { method: "POST" })
            .then(function() {
                showFormSuccess("Published.");
                selectArticle(parseInt(id, 10));
                fetchList();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Publish failed.");
            });
    }

    function onUnpublish() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        apiRef("/api/v1/news/" + id + "/unpublish", { method: "POST" })
            .then(function() {
                showFormSuccess("Unpublished.");
                selectArticle(parseInt(id, 10));
                fetchList();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Unpublish failed.");
            });
    }

    function onSubmitReview() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        var lang = state.currentLang;
        apiRef("/api/v1/news/" + id + "/translations/" + lang + "/submit-review", { method: "POST" })
            .then(function(data) {
                state.translationData[lang] = state.translationData[lang] || {};
                state.translationData[lang].translation_status = data.translation_status;
                showFormSuccess("Submitted for review.");
                return apiRef("/api/v1/news/" + id + "/translations");
            })
            .then(function(res) {
                state.translations = res;
                updateTranslationStatusDisplay();
                updateTranslationActions(lang);
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Submit failed.");
            });
    }

    function onApprove() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        var lang = state.currentLang;
        apiRef("/api/v1/news/" + id + "/translations/" + lang + "/approve", { method: "POST" })
            .then(function(data) {
                state.translationData[lang] = state.translationData[lang] || {};
                state.translationData[lang].translation_status = data.translation_status;
                showFormSuccess("Approved.");
                return apiRef("/api/v1/news/" + id + "/translations");
            })
            .then(function(res) {
                state.translations = res;
                updateTranslationStatusDisplay();
                updateTranslationActions(lang);
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Approve failed.");
            });
    }

    function onPublishTranslation() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        var lang = state.currentLang;
        apiRef("/api/v1/news/" + id + "/translations/" + lang + "/publish", { method: "POST" })
            .then(function(data) {
                state.translationData[lang] = state.translationData[lang] || {};
                state.translationData[lang].translation_status = data.translation_status;
                showFormSuccess("Translation published.");
                return apiRef("/api/v1/news/" + id + "/translations");
            })
            .then(function(res) {
                state.translations = res;
                updateTranslationStatusDisplay();
                updateTranslationActions(lang);
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Publish failed.");
            });
    }

    function onAutoTranslate() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        apiRef("/api/v1/news/" + id + "/translations/auto-translate", { method: "POST", body: JSON.stringify({}) })
            .then(function(res) {
                showFormSuccess("Auto-translate requested. Refresh or reselect to see new translations.");
                state.translations = res.translations ? { items: res.translations } : res;
                updateTranslationStatusDisplay();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Auto-translate failed.");
            });
    }

    function onDelete() {
        var id = ($("manage-news-id") || {}).value;
        if (!id) return;
        if (!confirm("Delete this article? This cannot be undone.")) return;
        apiRef("/api/v1/news/" + id, { method: "DELETE" })
            .then(function() {
                showFormEmpty();
                fetchList();
            })
            .catch(function(e) {
                showFormError(typeof e === "object" && e.message ? e.message : "Delete failed.");
            });
    }

    function onNew() {
        showFormEmpty();
        var form = $("manage-news-form");
        var empty = $("manage-news-editor-empty");
        if (empty) empty.hidden = true;
        if (form) form.hidden = false;
        setTab("de");
        ($("manage-news-editor-title") || {}).textContent = "New article";
        [$("manage-news-publish-btn"), $("manage-news-unpublish-btn"), $("manage-news-submit-review-btn"), $("manage-news-approve-btn"), $("manage-news-auto-translate-btn")].forEach(function(btn) {
            if (btn) btn.hidden = true;
        });
    }

    function initNewsPage() {
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            console.error("[manage_news] ManageAuth.apiFetchWithAuth not available.");
            var errEl = $("manage-news-error");
            if (errEl) { errEl.textContent = "Auth not loaded. Refresh the page."; errEl.hidden = false; }
            return;
        }
        apiRef = api;

        var applyBtn = $("manage-news-apply");
        var newBtn = $("manage-news-new");
        var form = $("manage-news-form");
        var saveBtn = $("manage-news-save");
        var pubBtn = $("manage-news-publish-btn");
        var unpubBtn = $("manage-news-unpublish-btn");
        var submitReviewBtn = $("manage-news-submit-review-btn");
        var approveBtn = $("manage-news-approve-btn");
        var publishTransBtn = $("manage-news-publish-translation-btn");
        var autoBtn = $("manage-news-auto-translate-btn");
        var delBtn = $("manage-news-delete-btn");
        var prevBtn = $("manage-news-prev");
        var nextBtn = $("manage-news-next");

        if (applyBtn) applyBtn.addEventListener("click", function() { state.page = 1; fetchList(); });
        if (newBtn) newBtn.addEventListener("click", onNew);
        if (form) form.addEventListener("submit", onSave);
        if (pubBtn) pubBtn.addEventListener("click", onPublish);
        if (unpubBtn) unpubBtn.addEventListener("click", onUnpublish);
        if (submitReviewBtn) submitReviewBtn.addEventListener("click", onSubmitReview);
        if (approveBtn) approveBtn.addEventListener("click", onApprove);
        var pubTransBtn = $("manage-news-publish-translation-btn");
        if (pubTransBtn) pubTransBtn.addEventListener("click", onPublishTranslation);
        if (autoBtn) autoBtn.addEventListener("click", onAutoTranslate);
        if (delBtn) delBtn.addEventListener("click", onDelete);
        var discussionLinkBtn = $("manage-news-discussion-link");
        var discussionUnlinkBtn = $("manage-news-discussion-unlink");
        if (discussionLinkBtn) discussionLinkBtn.addEventListener("click", onDiscussionLink);
        if (discussionUnlinkBtn) discussionUnlinkBtn.addEventListener("click", onDiscussionUnlink);
        var relatedThreadAddBtn = $("manage-news-related-thread-add");
        if (relatedThreadAddBtn) relatedThreadAddBtn.addEventListener("click", onRelatedThreadAdd);
        if (prevBtn) prevBtn.addEventListener("click", function() {
            if (state.page > 1) { state.page--; fetchList(); }
        });
        if (nextBtn) nextBtn.addEventListener("click", function() {
            if (state.page < state.totalPages) { state.page++; fetchList(); }
        });

        document.querySelectorAll(".manage-news-tab").forEach(function(tab) {
            tab.addEventListener("click", function() {
                var lang = tab.getAttribute("data-lang");
                var hasContent = state.translationData[lang] && state.translationData[lang].content !== undefined;
                if (state.selectedId && !hasContent && (state.translations || {}).items && (state.translations.items || []).some(function(t) { return t.language_code === lang; })) {
                    apiRef("/api/v1/news/" + state.selectedId + "/translations/" + lang)
                        .then(function(data) {
                            state.translationData[lang] = {
                                title: data.title,
                                slug: data.slug,
                                summary: data.summary,
                                content: data.content,
                                translation_status: data.translation_status,
                            };
                            setTab(lang);
                        })
                        .catch(function() { setTab(lang); });
                } else {
                    setTab(lang);
                }
            });
        });

        fetchList();
    }

    function run() {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initNewsPage);
        } else {
            initNewsPage();
        }
    }
    run();
})();
