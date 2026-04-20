/**
 * Wiki editor: list pages (wiki-admin), select page, edit translations (de/en) with markdown + preview,
 * save, submit-review, approve, publish translation, auto-translate. Uses real backend wiki-admin APIs.
 * Initializes on DOMContentLoaded; requires ManageAuth (loaded before this script in extra_scripts).
 */
(function() {
    var apiRef = null;
    function $(id) { return id ? document.getElementById(id) : null; }

    var LANGS = ["de", "en"];
    var state = {
        pages: [],
        selectedPageId: null,
        currentLang: "de",
        translations: null,
        translationData: { de: null, en: null },
        initialContent: "",
        dirty: false,
    };

    function setDirty() {
        state.dirty = true;
        var el = $("manage-wiki-dirty");
        if (el) el.hidden = false;
    }

    function clearDirty() {
        state.dirty = false;
        var el = $("manage-wiki-dirty");
        if (el) el.hidden = true;
    }

    /** Returns sanitized HTML when DOMPurify is available; otherwise null (caller must use textContent only). */
    function sanitizePreviewHtml(html) {
        if (typeof DOMPurify !== "undefined") {
            return DOMPurify.sanitize(html, {
                ALLOWED_TAGS: ["p", "br", "hr", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "strong", "b", "em", "i", "u", "s", "code", "pre", "blockquote", "a", "table", "thead", "tbody", "tr", "th", "td"],
                ALLOWED_ATTR: ["href", "title"]
            });
        }
        return null;
    }

    function updatePreview() {
        var textarea = $("manage-wiki-content");
        var preview = $("manage-wiki-preview");
        if (!textarea || !preview) return;
        var raw = textarea.value || "";
        if (typeof marked !== "undefined") {
            try {
                var parsed = marked.parse(raw);
                var sanitized = sanitizePreviewHtml(parsed);
                if (sanitized !== null) {
                    preview.innerHTML = sanitized;
                } else {
                    preview.textContent = raw || "(empty)";
                }
            } catch (e) {
                preview.textContent = raw || "(empty)";
            }
        } else {
            preview.textContent = raw || "(empty)";
        }
    }

    function statusBadge(status) {
        var c = "badge";
        if (status === "published") c += " badge-success";
        else if (status === "approved" || status === "review_required") c += " badge-warning";
        else if (status === "machine_draft" || status === "outdated") c += " badge-info";
        else c += " badge-secondary";
        return "<span class=\"" + c + "\">" + (status || "missing").replace(/</g, "&lt;") + "</span>";
    }

    function showLoading(show) {
        var loading = $("manage-wiki-loading");
        var list = $("manage-wiki-page-list");
        var empty = $("manage-wiki-empty");
        var err = $("manage-wiki-error");
        if (loading) loading.hidden = !show;
        if (list) list.hidden = show;
        if (empty) empty.hidden = true;
        if (err) err.hidden = true;
    }

    function showError(msg) {
        showLoading(false);
        var list = $("manage-wiki-page-list");
        var err = $("manage-wiki-error");
        if (list) list.hidden = false;
        if (err) { err.textContent = msg || "Failed."; err.hidden = false; }
    }

    function renderPageList(pages) {
        showLoading(false);
        state.pages = pages || [];
        var list = $("manage-wiki-page-list");
        var empty = $("manage-wiki-empty");
        var err = $("manage-wiki-error");
        if (err) err.hidden = true;
        if (!list) return;
        list.innerHTML = "";
        if (!pages || pages.length === 0) {
            if (empty) empty.hidden = false;
            list.hidden = true;
            return;
        }
        if (empty) empty.hidden = true;
        list.hidden = false;
        pages.forEach(function(p) {
            var li = document.createElement("li");
            li.dataset.pageId = p.id;
            var a = document.createElement("a");
            a.href = "#";
            a.className = "manage-wiki-page-link";
            a.textContent = p.key + (p.is_published ? "" : " (draft)");
            a.addEventListener("click", function(e) {
                e.preventDefault();
                selectPage(p.id);
            });
            li.appendChild(a);
            if (state.selectedPageId === p.id) li.classList.add("selected");
            list.appendChild(li);
        });
    }

    function fetchPages() {
        if (!apiRef) return Promise.reject();
        showLoading(true);
        return apiRef("/api/v1/wiki-admin/pages")
            .then(function(data) {
                renderPageList(data.items || []);
            })
            .catch(function(e) {
                showError(typeof e === "object" && e.message ? e.message : "Failed to load pages.");
                throw e;
            });
    }

    function setTab(lang) {
        state.currentLang = lang;
        var tabs = document.querySelectorAll("#manage-wiki-lang-tabs .manage-news-tab");
        tabs.forEach(function(t) {
            t.classList.toggle("active", t.getAttribute("data-lang") === lang);
        });
        var data = state.translationData[lang];
        var ta = $("manage-wiki-content");
        if (ta) {
            state.initialContent = data && data.content_markdown !== undefined ? data.content_markdown : "";
            ta.value = state.initialContent;
            clearDirty();
        }
        updatePreview();
        updateWikiTranslationActions(lang);
    }

    function updateTranslationStatusDisplay() {
        var el = $("manage-wiki-translation-status");
        if (!el) return;
        if (!state.translations || !state.translations.items) {
            el.innerHTML = "";
            return;
        }
        var html = [];
        (state.translations.items || []).forEach(function(t) {
            html.push("<span class=\"manage-news-status-item\"><strong>" + (t.language_code || "").toUpperCase() + "</strong>: " + statusBadge(t.translation_status) + "</span>");
        });
        el.innerHTML = html.length ? html.join(" ") : "";
    }

    function updateWikiTranslationActions(lang) {
        var data = state.translationData[lang];
        var status = data ? data.translation_status : "missing";
        var submitBtn = $("manage-wiki-submit-review");
        var approveBtn = $("manage-wiki-approve");
        var pubBtn = $("manage-wiki-publish-translation");
        if (submitBtn) submitBtn.hidden = !data || status === "review_required" || status === "approved" || status === "published";
        if (approveBtn) approveBtn.hidden = !data || status !== "review_required";
        if (pubBtn) pubBtn.hidden = !data || status === "published";
    }

    function updateWikiDiscussionDisplay() {
        var slugEl = $("manage-wiki-discussion-slug");
        var unlinkBtn = $("manage-wiki-discussion-unlink");
        var threadIdInput = $("manage-wiki-discussion-thread-id");
        var page = state.selectedPageId ? state.pages.find(function(p) { return p.id === state.selectedPageId; }) : null;
        if (slugEl) slugEl.textContent = (page && page.discussion_thread_slug) ? page.discussion_thread_slug : "—";
        if (unlinkBtn) unlinkBtn.hidden = !(page && page.discussion_thread_id);
        if (threadIdInput) threadIdInput.value = "";
    }

    function onWikiDiscussionLink() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        var threadIdInput = $("manage-wiki-discussion-thread-id");
        var raw = threadIdInput && threadIdInput.value ? threadIdInput.value.trim() : "";
        var tid = parseInt(raw, 10);
        if (!raw || isNaN(tid) || tid < 1) {
            var err = $("manage-wiki-error");
            if (err) { err.textContent = "Enter a valid thread ID (integer ≥ 1)."; err.hidden = false; }
            return;
        }
        apiRef("/api/v1/wiki/" + pageId + "/discussion-thread", { method: "POST", body: JSON.stringify({ discussion_thread_id: tid }) })
            .then(function() {
                return fetchPages();
            })
            .then(function() {
                updateWikiDiscussionDisplay();
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Link failed."); err.hidden = false; }
            });
    }

    function onWikiDiscussionUnlink() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        apiRef("/api/v1/wiki/" + pageId + "/discussion-thread", { method: "DELETE" })
            .then(function() {
                return fetchPages();
            })
            .then(function() {
                updateWikiDiscussionDisplay();
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Unlink failed."); err.hidden = false; }
            });
    }

    function renderWikiRelatedThreadsList(items) {
        var listEl = $("manage-wiki-related-threads-list");
        if (!listEl) return;
        while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
        if (!items || items.length === 0) {
            listEl.appendChild(document.createTextNode("No related threads."));
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
                    onWikiRelatedThreadRemove(tid);
                });
            }(t.id));
            li.appendChild(removeBtn);
            ul.appendChild(li);
        });
        listEl.appendChild(ul);
    }

    function fetchWikiRelatedThreads() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        apiRef("/api/v1/wiki/" + pageId + "/related-threads")
            .then(function(data) {
                renderWikiRelatedThreadsList(data.items || []);
            })
            .catch(function() {
                var listEl = $("manage-wiki-related-threads-list");
                if (listEl) listEl.textContent = "Failed to load related threads.";
            });
    }

    function onWikiRelatedThreadAdd(threadIdFromSuggested) {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        var tid;
        if (threadIdFromSuggested) {
            tid = threadIdFromSuggested;
        } else {
            var input = $("manage-wiki-related-thread-id");
            var raw = input && input.value ? input.value.trim() : "";
            tid = parseInt(raw, 10);
            if (!raw || isNaN(tid) || tid < 1) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = "Enter a valid thread ID (integer \u2265 1)."; err.hidden = false; }
                return;
            }
        }
        apiRef("/api/v1/wiki/" + pageId + "/related-threads", { method: "POST", body: JSON.stringify({ thread_id: tid }) })
            .then(function(data) {
                var input = $("manage-wiki-related-thread-id");
                if (input && !threadIdFromSuggested) input.value = "";
                renderWikiRelatedThreadsList(data.items || []);
                fetchWikiSuggestedThreads();
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Add related thread failed."); err.hidden = false; }
            });
    }

    function onWikiRelatedThreadRemove(threadId) {
        var pageId = state.selectedPageId;
        if (!pageId || !threadId) return;
        if (!confirm("Remove this related thread?")) return;
        apiRef("/api/v1/wiki/" + pageId + "/related-threads/" + threadId, { method: "DELETE" })
            .then(function(data) {
                renderWikiRelatedThreadsList(data.items || []);
                fetchWikiSuggestedThreads();
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Remove related thread failed."); err.hidden = false; }
            });
    }

    function renderWikiSuggestedThreadsList(items) {
        var listEl = $("manage-wiki-suggested-threads-list");
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
                    onWikiRelatedThreadAdd(tid);
                });
            }(t.id));
            li.appendChild(addBtn);
            ul.appendChild(li);
        });
        listEl.appendChild(ul);
    }

    function fetchWikiSuggestedThreads() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        apiRef("/api/v1/wiki/" + pageId + "/suggested-threads")
            .then(function(data) {
                renderWikiSuggestedThreadsList(data.items || []);
            })
            .catch(function() {
                var listEl = $("manage-wiki-suggested-threads-list");
                if (listEl) listEl.textContent = "Failed to load suggested threads.";
            });
    }

    function selectPage(pageId) {
        state.selectedPageId = pageId;
        state.translations = null;
        state.translationData = { de: null, en: null };

        var list = $("manage-wiki-page-list");
        if (list) {
            [].forEach.call(list.querySelectorAll("li"), function(li) {
                li.classList.toggle("selected", parseInt(li.dataset.pageId, 10) === pageId);
            });
        }

        var empty = $("manage-wiki-editor-empty");
        var wrap = $("manage-wiki-editor-wrap");
        if (!pageId) {
            if (wrap) wrap.hidden = true;
            if (empty) empty.hidden = false;
            updateWikiDiscussionDisplay();
            renderWikiRelatedThreadsList([]);
            return;
        }

        if (empty) empty.hidden = true;
        if (wrap) wrap.hidden = false;
        var page = state.pages.find(function(p) { return p.id === pageId; });
        ($("manage-wiki-page-title") || {}).textContent = page ? "Page: " + page.key : "Page";
        updateWikiDiscussionDisplay();
        fetchWikiRelatedThreads();
        fetchWikiSuggestedThreads();

        apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations")
            .then(function(data) {
                state.translations = data;
                (data.items || []).forEach(function(t) {
                    state.translationData[t.language_code] = {
                        title: t.title,
                        slug: t.slug,
                        content_markdown: null,
                        translation_status: t.translation_status,
                    };
                });
                setTab(state.currentLang);
                updateTranslationStatusDisplay();
                return Promise.all(LANGS.map(function(lang) {
                    return apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations/" + lang)
                        .then(function(tr) {
                            state.translationData[lang] = {
                                title: tr.title,
                                slug: tr.slug,
                                content_markdown: tr.content_markdown,
                                translation_status: tr.translation_status,
                            };
                        })
                        .catch(function() {});
                }));
            })
            .then(function() {
                setTab(state.currentLang);
            })
            .catch(function(e) {
                showError(typeof e === "object" && e.message ? e.message : "Failed to load translations.");
            });
    }

    function onSave() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        var lang = state.currentLang;
        var ta = $("manage-wiki-content");
        if (!ta) return;
        var content = ta.value || "";
        var data = state.translationData[lang];
        var page = state.pages.find(function(p) { return p.id === pageId; });
        var defaultKey = page ? page.key : "wiki";
        var title = (data && data.title) ? data.title : defaultKey;
        var slug = (data && data.slug) ? data.slug : defaultKey;
        var saveBtn = $("manage-wiki-save");
        var savedEl = $("manage-wiki-saved");
        if (saveBtn) saveBtn.disabled = true;
        apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations/" + lang, {
            method: "PUT",
            body: JSON.stringify({
                title: title,
                slug: slug,
                content_markdown: content,
            }),
        })
            .then(function(tr) {
                state.translationData[lang] = {
                    title: tr.title,
                    slug: tr.slug,
                    content_markdown: tr.content_markdown,
                    translation_status: tr.translation_status,
                };
                state.initialContent = content;
                clearDirty();
                if (savedEl) { savedEl.hidden = false; setTimeout(function() { savedEl.hidden = true; }, 3000); }
                updateTranslationStatusDisplay();
                updateWikiTranslationActions(lang);
                return apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations");
            })
            .then(function(data) {
                state.translations = data;
                updateTranslationStatusDisplay();
            })
            .catch(function(e) {
                if (savedEl) savedEl.hidden = true;
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Save failed."); err.hidden = false; }
            })
            .then(function() {
                if (saveBtn) saveBtn.disabled = false;
            });
    }

    function onSubmitReview() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        var lang = state.currentLang;
        apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations/" + lang + "/submit-review", { method: "POST" })
            .then(function(tr) {
                state.translationData[lang] = state.translationData[lang] || {};
                state.translationData[lang].translation_status = tr.translation_status;
                updateTranslationStatusDisplay();
                updateWikiTranslationActions(lang);
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Failed."); err.hidden = false; }
            });
    }

    function onApprove() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        var lang = state.currentLang;
        apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations/" + lang + "/approve", { method: "POST" })
            .then(function(tr) {
                state.translationData[lang] = state.translationData[lang] || {};
                state.translationData[lang].translation_status = tr.translation_status;
                updateTranslationStatusDisplay();
                updateWikiTranslationActions(lang);
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Failed."); err.hidden = false; }
            });
    }

    function onPublishTranslation() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        var lang = state.currentLang;
        apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations/" + lang + "/publish", { method: "POST" })
            .then(function(tr) {
                state.translationData[lang] = state.translationData[lang] || {};
                state.translationData[lang].translation_status = tr.translation_status;
                updateTranslationStatusDisplay();
                updateWikiTranslationActions(lang);
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Failed."); err.hidden = false; }
            });
    }

    function onAutoTranslate() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        apiRef("/api/v1/wiki-admin/pages/" + pageId + "/translations/auto-translate", { method: "POST", body: JSON.stringify({}) })
            .then(function(data) {
                state.translations = data.translations ? { items: data.translations } : data;
                updateTranslationStatusDisplay();
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Auto-translate failed."); err.hidden = false; }
            });
    }

    function fetchWikiRelatedThreads() {
        var pageId = state.selectedPageId;
        if (!pageId || !apiRef) return;
        var listEl = $("manage-wiki-related-threads-list");
        if (!listEl) return;
        apiRef("/api/v1/wiki/" + pageId + "/related-threads")
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
                        return function() { onWikiRelatedThreadRemove(tid); };
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

    function onWikiRelatedThreadAdd() {
        var pageId = state.selectedPageId;
        if (!pageId) return;
        var input = $("manage-wiki-related-thread-id");
        var raw = input && input.value ? input.value.trim() : "";
        var tid = parseInt(raw, 10);
        if (!raw || isNaN(tid) || tid < 1) {
            var err = $("manage-wiki-error");
            if (err) { err.textContent = "Enter a valid thread ID (integer \u2265 1)."; err.hidden = false; }
            return;
        }
        apiRef("/api/v1/wiki/" + pageId + "/related-threads", { method: "POST", body: JSON.stringify({ thread_id: tid }) })
            .then(function() {
                if (input) input.value = "";
                return fetchWikiRelatedThreads();
            })
            .then(function() {
                var savedEl = $("manage-wiki-saved");
                if (savedEl) { savedEl.hidden = false; setTimeout(function() { savedEl.hidden = true; }, 3000); }
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Add failed."); err.hidden = false; }
            });
    }

    function onWikiRelatedThreadRemove(threadId) {
        var pageId = state.selectedPageId;
        if (!pageId || !threadId) return;
        apiRef("/api/v1/wiki/" + pageId + "/related-threads/" + threadId, { method: "DELETE" })
            .then(function() {
                return fetchWikiRelatedThreads();
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Remove failed."); err.hidden = false; }
            });
    }

    function onNewPage() {
        var key = window.prompt("Page key (e.g. index, faq):");
        if (!key || !key.trim()) return;
        key = key.trim().toLowerCase().replace(/\s+/g, "-");
        apiRef("/api/v1/wiki-admin/pages", {
            method: "POST",
            body: JSON.stringify({ key: key, is_published: true }),
        })
            .then(function() {
                fetchPages();
            })
            .catch(function(e) {
                var err = $("manage-wiki-error");
                if (err) { err.textContent = (typeof e === "object" && e.message ? e.message : "Create failed."); err.hidden = false; }
            });
    }

    function checkUnload(e) {
        if (state.dirty) {
            e.preventDefault();
            e.returnValue = "";
        }
    }

    function initWikiPage() {
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            console.error("[manage_wiki] ManageAuth.apiFetchWithAuth not available.");
            var errEl = $("manage-wiki-error");
            if (errEl) { errEl.textContent = "Auth not loaded. Refresh the page."; errEl.hidden = false; }
            return;
        }
        apiRef = api;

        var ta = $("manage-wiki-content");
        var saveBtn = $("manage-wiki-save");
        if (ta) {
            ta.addEventListener("input", function() {
                setDirty();
                updatePreview();
            });
        }
        if (saveBtn) saveBtn.addEventListener("click", onSave);
        if ($("manage-wiki-submit-review")) $("manage-wiki-submit-review").addEventListener("click", onSubmitReview);
        if ($("manage-wiki-approve")) $("manage-wiki-approve").addEventListener("click", onApprove);
        if ($("manage-wiki-publish-translation")) $("manage-wiki-publish-translation").addEventListener("click", onPublishTranslation);
        if ($("manage-wiki-auto-translate")) $("manage-wiki-auto-translate").addEventListener("click", onAutoTranslate);
        if ($("manage-wiki-new-page")) $("manage-wiki-new-page").addEventListener("click", onNewPage);
        if ($("manage-wiki-discussion-link")) $("manage-wiki-discussion-link").addEventListener("click", onWikiDiscussionLink);
        if ($("manage-wiki-discussion-unlink")) $("manage-wiki-discussion-unlink").addEventListener("click", onWikiDiscussionUnlink);
        if ($("manage-wiki-related-thread-add")) $("manage-wiki-related-thread-add").addEventListener("click", onWikiRelatedThreadAdd);

        document.querySelectorAll("#manage-wiki-lang-tabs .manage-news-tab").forEach(function(tab) {
            tab.addEventListener("click", function() {
                setTab(tab.getAttribute("data-lang"));
            });
        });

        window.addEventListener("beforeunload", checkUnload);
        fetchPages();
    }

    function run() {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initWikiPage);
        } else {
            initWikiPage();
        }
    }
    run();
})();
