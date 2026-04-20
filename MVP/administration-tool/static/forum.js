/**
 * World of Shadows – public forum frontend
 * Uses FrontendConfig.apiFetch (main.js) for GET; ManageAuth.apiFetchWithAuth for POST when logged in.
 * API: GET /api/v1/forum/categories, /forum/categories/<slug>, /forum/categories/<slug>/threads,
 *      GET /api/v1/forum/threads/<slug>, /forum/threads/<id>/posts;
 *      POST /api/v1/forum/categories/<slug>/threads, POST /api/v1/forum/threads/<id>/posts
 */
(function() {
    function getApiBase() {
        var fc = window.FrontendConfig;
        return (fc && fc.getApiBaseUrl) ? fc.getApiBaseUrl() : "";
    }

    function apiGet(path) {
        var url = (path.indexOf("/") === 0) ? path : "/api/v1/forum" + (path ? "/" + path : "");
        if (window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken()) {
            return window.ManageAuth.apiFetchWithAuth(url);
        }
        var fc = window.FrontendConfig;
        var fn = (fc && fc.apiFetch) ? fc.apiFetch : function(u) {
            return fetch((getApiBase() || "") + (u.indexOf("/") === 0 ? u : "/" + u), { headers: { Accept: "application/json" } })
                .then(function(r) { if (!r.ok) throw new Error(r.statusText); return r.json(); });
        };
        return fn(url);
    }

    function apiPost(path, body) {
        var url = "/api/v1/forum" + (path.indexOf("/") === 0 ? path : "/" + path);
        var opts = { method: "POST", body: typeof body === "string" ? body : JSON.stringify(body || {}) };
        if (window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken()) {
            return window.ManageAuth.apiFetchWithAuth(url, opts);
        }
        var fc = window.FrontendConfig;
        var base = getApiBase();
        var fullUrl = (base ? base.replace(/\/$/, "") : "") + url;
        return fetch(fullUrl, {
            method: "POST",
            headers: { "Accept": "application/json", "Content-Type": "application/json" },
            body: opts.body
        }).then(function(r) {
            if (r.status === 401) throw { status: 401, message: "Please log in to post." };
            if (!r.ok) return r.json().then(function(j) { throw { status: r.status, message: (j && j.error) || r.statusText }; });
            return r.json();
        });
    }

    function apiPut(path, body) {
        var url = "/api/v1/forum" + (path.indexOf("/") === 0 ? path : "/" + path);
        var opts = { method: "PUT", body: typeof body === "string" ? body : JSON.stringify(body || {}) };
        if (!(window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken())) {
            return Promise.reject({ status: 401, message: "Please log in." });
        }
        return window.ManageAuth.apiFetchWithAuth(url, opts);
    }

    function apiDelete(path) {
        var url = "/api/v1/forum" + (path.indexOf("/") === 0 ? path : "/" + path);
        var opts = { method: "DELETE" };
        if (!(window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken())) {
            return Promise.reject({ status: 401, message: "Please log in." });
        }
        return window.ManageAuth.apiFetchWithAuth(url, opts);
    }

    function formatDate(iso) {
        if (!iso) return "";
        try {
            var d = new Date(iso);
            return isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { dateStyle: "medium" });
        } catch (e) { return ""; }
    }

    function escapeHtml(s) {
        if (s == null) return "";
        var div = document.createElement("div");
        div.textContent = s;
        return div.innerHTML;
    }
    function formatPostContent(content) {
        var escaped = escapeHtml(content || "");
        return escaped.replace(/@([a-zA-Z0-9_]+)/g, "<span class=\"forum-mention\">@$1</span>");
    }

    // --- Index: categories list ---
    function initIndex() {
        var loading = document.getElementById("forum-loading");
        var content = document.getElementById("forum-categories");
        var empty = document.getElementById("forum-empty");
        var errEl = document.getElementById("forum-error");

        function showLoading(show) {
            if (loading) loading.hidden = !show;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
        }
        function showError(msg) {
            if (loading) loading.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) { errEl.textContent = msg || "Failed to load forum."; errEl.hidden = false; }
        }
        function showList(items) {
            if (loading) loading.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (!content) return;
            content.innerHTML = "";
            items.forEach(function(cat) {
                var card = document.createElement("a");
                card.href = "/forum/categories/" + encodeURIComponent(cat.slug || "");
                card.className = "forum-category-card card card-link";
                var title = document.createElement("h2");
                title.className = "forum-category-title";
                title.textContent = cat.title || "Unnamed";
                card.appendChild(title);
                if (cat.description) {
                    var desc = document.createElement("p");
                    desc.className = "forum-category-desc muted";
                    desc.textContent = cat.description;
                    card.appendChild(desc);
                }
                content.appendChild(card);
            });
            content.hidden = false;
        }

        showLoading(true);
        apiGet("categories")
            .then(function(data) {
                var items = (data && data.items) ? data.items : [];
                if (items.length === 0) {
                    if (loading) loading.hidden = true;
                    if (content) content.hidden = true;
                    if (empty) empty.hidden = false;
                } else showList(items);
            })
            .catch(function(e) { showError(typeof e === "string" ? e : (e && e.message) || "Failed to load."); });

        var searchForm = document.getElementById("forum-search-form");
        var searchInput = document.getElementById("forum-search-input");
        var searchResults = document.getElementById("forum-search-results");
        var searchTitle = document.getElementById("forum-search-results-title");
        var searchLoading = document.getElementById("forum-search-loading");
        var searchEmpty = document.getElementById("forum-search-empty");
        var searchThreads = document.getElementById("forum-search-threads");
        var searchPagination = document.getElementById("forum-search-pagination");
        var searchPaginationInfo = document.getElementById("forum-search-pagination-info");
        var searchPrev = document.getElementById("forum-search-prev");
        var searchNext = document.getElementById("forum-search-next");
        var searchState = { q: "", page: 1, total: 0, perPage: 20, totalPages: 0 };

        function showSearchLoading(show) {
            if (searchLoading) searchLoading.hidden = !show;
            if (searchEmpty) searchEmpty.hidden = true;
            if (searchThreads) searchThreads.hidden = true;
        }
        function renderSearchResults(items, page, total, perPage) {
            if (searchLoading) searchLoading.hidden = true;
            if (searchEmpty) searchEmpty.hidden = items.length > 0;
            if (!searchThreads) return;
            searchThreads.innerHTML = "";
            items.forEach(function(t) {
                var row = document.createElement("div");
                row.className = "forum-thread-row";
                var link = document.createElement("a");
                link.href = "/forum/threads/" + encodeURIComponent(t.slug || "");
                link.className = "forum-thread-link";
                var title = document.createElement("span");
                title.className = "forum-thread-title";
                title.textContent = t.title || "Untitled";
                if (t.is_pinned) {
                    var pin = document.createElement("span");
                    pin.className = "forum-badge forum-badge-pinned";
                    pin.textContent = "Pinned";
                    link.appendChild(pin);
                }
                link.appendChild(title);
                var meta = document.createElement("span");
                meta.className = "forum-thread-meta muted";
                var parts = [];
                if (t.reply_count != null) parts.push(t.reply_count + " replies");
                if (t.last_post_at) parts.push(formatDate(t.last_post_at));
                if (t.tags && t.tags.length) {
                    var tagNames = t.tags.map(function(tag) { return tag.label || tag.slug; }).join(", ");
                    if (tagNames) parts.push("Tags: " + tagNames);
                }
                meta.textContent = parts.join(" · ");
                row.appendChild(link);
                row.appendChild(meta);
                searchThreads.appendChild(row);
            });
            searchThreads.hidden = false;
            searchState.total = total;
            searchState.totalPages = perPage > 0 ? Math.ceil(total / perPage) : 0;
            if (searchPagination) {
                searchPagination.hidden = searchState.totalPages <= 1;
                if (searchPaginationInfo) searchPaginationInfo.textContent = "Page " + page + " of " + (searchState.totalPages || 1) + " (" + total + " total)";
                if (searchPrev) searchPrev.disabled = page <= 1;
                if (searchNext) searchNext.disabled = page >= searchState.totalPages;
            }
        }

        var searchCategoryInput = document.getElementById("forum-search-category");
        var searchTagInput = document.getElementById("forum-search-tag");

        function buildSearchQuery(q, page, perPage) {
            var params = [];
            if (q) params.push("q=" + encodeURIComponent(q));
            if (page) params.push("page=" + encodeURIComponent(String(page)));
            if (perPage) params.push("limit=" + encodeURIComponent(String(perPage)));
            if (searchCategoryInput && searchCategoryInput.value.trim()) {
                params.push("category=" + encodeURIComponent(searchCategoryInput.value.trim()));
            }
            if (searchTagInput && searchTagInput.value.trim()) {
                params.push("tag=" + encodeURIComponent(searchTagInput.value.trim().toLowerCase()));
            }
            return "search" + (params.length ? "?" + params.join("&") : "");
        }

        if (searchForm) searchForm.addEventListener("submit", function(e) {
            e.preventDefault();
            var q = (searchInput && searchInput.value) ? searchInput.value.trim() : "";
            searchState.q = q;
            searchState.page = 1;
            if (loading) loading.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (searchResults) {
                searchResults.hidden = false;
                if (searchTitle) searchTitle.textContent = q ? "Search: " + escapeHtml(q) : "Search";
            }
            showSearchLoading(true);
            apiGet(buildSearchQuery(q, 1, searchState.perPage))
                .then(function(data) {
                    var items = (data && data.items) ? data.items : [];
                    var total = (data && typeof data.total === "number") ? data.total : 0;
                    var page = (data && typeof data.page === "number") ? data.page : 1;
                    var perPage = (data && typeof data.per_page === "number") ? data.per_page : searchState.perPage;
                    searchState.page = page;
                    if (items.length === 0) {
                        if (searchLoading) searchLoading.hidden = true;
                        if (searchEmpty) searchEmpty.hidden = false;
                    } else renderSearchResults(items, page, total, perPage);
                })
                .catch(function(err) {
                    if (searchLoading) searchLoading.hidden = true;
                    if (searchEmpty) { searchEmpty.textContent = (err && err.message) || "Search failed."; searchEmpty.hidden = false; }
                });
        });

        if (searchPrev) searchPrev.addEventListener("click", function() {
            if (searchState.page <= 1 || !searchState.q) return;
            searchState.page--;
            showSearchLoading(true);
            apiGet(buildSearchQuery(searchState.q, searchState.page, searchState.perPage))
                .then(function(data) {
                    var items = (data && data.items) ? data.items : [];
                    var total = (data && typeof data.total === "number") ? data.total : 0;
                    var page = (data && typeof data.page === "number") ? data.page : searchState.page;
                    var perPage = (data && typeof data.per_page === "number") ? data.per_page : searchState.perPage;
                    renderSearchResults(items, page, total, perPage);
                }).catch(function() { if (searchLoading) searchLoading.hidden = true; });
        });
        if (searchNext) searchNext.addEventListener("click", function() {
            if (searchState.page >= searchState.totalPages || !searchState.q) return;
            searchState.page++;
            showSearchLoading(true);
            apiGet(buildSearchQuery(searchState.q, searchState.page, searchState.perPage))
                .then(function(data) {
                    var items = (data && data.items) ? data.items : [];
                    var total = (data && typeof data.total === "number") ? data.total : 0;
                    var page = (data && typeof data.page === "number") ? data.page : searchState.page;
                    var perPage = (data && typeof data.per_page === "number") ? data.per_page : searchState.perPage;
                    renderSearchResults(items, page, total, perPage);
                }).catch(function() { if (searchLoading) searchLoading.hidden = true; });
        });
    }

    // --- Category: threads list + new thread modal ---
    function initCategory(categorySlug) {
        var loading = document.getElementById("forum-category-loading");
        var header = document.getElementById("forum-category-header");
        var actions = document.getElementById("forum-category-actions");
        var content = document.getElementById("forum-threads-content");
        var empty = document.getElementById("forum-category-empty");
        var errEl = document.getElementById("forum-category-error");
        var pagination = document.getElementById("forum-category-pagination");
        var paginationInfo = document.getElementById("forum-category-pagination-info");
        var prevBtn = document.getElementById("forum-category-prev");
        var nextBtn = document.getElementById("forum-category-next");
        var state = { page: 1, total: 0, perPage: 20, totalPages: 0, category: null };

        function showLoading(show) {
            if (loading) loading.hidden = !show;
            if (header) header.hidden = true;
            if (actions) actions.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (pagination) pagination.hidden = true;
        }
        function showError(msg) {
            if (loading) loading.hidden = true;
            if (header) header.hidden = true;
            if (actions) actions.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) { errEl.textContent = msg || "Failed to load."; errEl.hidden = false; }
            if (pagination) pagination.hidden = true;
        }
        function toggleBookmark(threadId, btn) {
            var isBookmarked = btn.getAttribute("data-bookmarked") === "true";
            var method = isBookmarked ? "DELETE" : "POST";
            var url = "/threads/" + threadId + "/bookmark";
            if (window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken()) {
                window.ManageAuth.apiFetchWithAuth("/api/v1/forum" + url, { method: method })
                    .then(function() {
                        var newState = !isBookmarked;
                        btn.setAttribute("data-bookmarked", newState ? "true" : "false");
                        btn.textContent = newState ? "\u2605" : "\u2606";
                        btn.title = newState ? "Remove bookmark" : "Bookmark";
                        btn.classList.toggle("forum-bookmark-active", newState);
                    })
                    .catch(function() {});
            }
        }

        function renderThreads(items, page, total, perPage) {
            if (loading) loading.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (!content) return;
            while (content.firstChild) content.removeChild(content.firstChild);
            var isLoggedIn = !!(window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken());
            items.forEach(function(t) {
                var row = document.createElement("div");
                row.className = "forum-thread-row";
                var link = document.createElement("a");
                link.href = "/forum/threads/" + encodeURIComponent(t.slug || "");
                link.className = "forum-thread-link";
                var title = document.createElement("span");
                title.className = "forum-thread-title";
                title.textContent = t.title || "Untitled";
                if (t.is_pinned) {
                    var pin = document.createElement("span");
                    pin.className = "forum-badge forum-badge-pinned";
                    pin.textContent = "Pinned";
                    link.appendChild(pin);
                }
                link.appendChild(title);
                // Tags badges
                if (t.tags && t.tags.length) {
                    t.tags.forEach(function(tag) {
                        var badge = document.createElement("span");
                        badge.className = "forum-badge forum-badge-tag";
                        badge.textContent = tag.label || tag.slug;
                        link.appendChild(badge);
                    });
                }
                var meta = document.createElement("span");
                meta.className = "forum-thread-meta muted";
                var parts = [];
                if (t.reply_count != null) parts.push(t.reply_count + " replies");
                if (t.last_post_at) parts.push(formatDate(t.last_post_at));
                meta.textContent = parts.join(" \u00b7 ");
                row.appendChild(link);
                // Bookmark button (only for logged-in users)
                if (isLoggedIn) {
                    var bmBtn = document.createElement("button");
                    bmBtn.type = "button";
                    bmBtn.className = "forum-bookmark-btn" + (t.bookmarked_by_me ? " forum-bookmark-active" : "");
                    bmBtn.setAttribute("data-bookmarked", t.bookmarked_by_me ? "true" : "false");
                    bmBtn.textContent = t.bookmarked_by_me ? "\u2605" : "\u2606";
                    bmBtn.title = t.bookmarked_by_me ? "Remove bookmark" : "Bookmark";
                    (function(tid, btn) {
                        btn.addEventListener("click", function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            toggleBookmark(tid, btn);
                        });
                    })(t.id, bmBtn);
                    row.appendChild(bmBtn);
                }
                row.appendChild(meta);
                content.appendChild(row);
            });
            content.hidden = false;
            if (actions) actions.hidden = false;
            state.total = total;
            state.totalPages = perPage > 0 ? Math.ceil(total / perPage) : 0;
            if (pagination) {
                pagination.hidden = state.totalPages <= 1;
                if (paginationInfo) paginationInfo.textContent = "Page " + page + " of " + (state.totalPages || 1) + " (" + total + " total)";
                if (prevBtn) prevBtn.disabled = page <= 1;
                if (nextBtn) nextBtn.disabled = page >= state.totalPages;
            }
        }

        function fetchCategory() {
            return apiGet("categories/" + encodeURIComponent(categorySlug));
        }
        function fetchThreads(page) {
            return apiGet("categories/" + encodeURIComponent(categorySlug) + "/threads?page=" + page + "&limit=" + state.perPage);
        }

        showLoading(true);
        fetchCategory()
            .then(function(cat) {
                state.category = cat;
                if (header) {
                    header.innerHTML = "";
                    var h1 = document.createElement("h1");
                    h1.className = "page-header forum-category-name";
                    h1.textContent = cat.title || "Category";
                    header.appendChild(h1);
                    if (cat.description) {
                        var p = document.createElement("p");
                        p.className = "muted";
                        p.textContent = cat.description;
                        header.appendChild(p);
                    }
                    header.hidden = false;
                }
                return fetchThreads(1);
            })
            .then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : items.length;
                var page = (data && typeof data.page === "number") ? data.page : 1;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                state.page = page;
                if (items.length === 0) {
                    if (loading) loading.hidden = true;
                    if (content) content.hidden = true;
                    if (empty) empty.hidden = false;
                    if (actions) actions.hidden = false;
                } else renderThreads(items, page, total, perPage);
            })
            .catch(function(e) { showError(typeof e === "string" ? e : (e && e.message) || "Failed to load."); });

        if (prevBtn) prevBtn.addEventListener("click", function() {
            if (state.page <= 1) return;
            state.page--;
            showLoading(true);
            fetchThreads(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                renderThreads(items, page, total, perPage);
            }).catch(function(e) { showError(e && e.message); });
        });
        if (nextBtn) nextBtn.addEventListener("click", function() {
            if (state.page >= state.totalPages) return;
            state.page++;
            showLoading(true);
            fetchThreads(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                renderThreads(items, page, total, perPage);
            }).catch(function(e) { showError(e && e.message); });
        });

        // New thread modal
        var newThreadBtn = document.getElementById("forum-new-thread-btn");
        var modal = document.getElementById("forum-new-thread-modal");
        var loginHint = document.getElementById("forum-new-thread-login-hint");
        var form = document.getElementById("forum-new-thread-form");
        var formError = document.getElementById("forum-new-thread-error");
        var titleInput = document.getElementById("forum-new-thread-title-input");
        var contentInput = document.getElementById("forum-new-thread-content");
        var submitBtn = document.getElementById("forum-new-thread-submit");
        var cancelBtn = document.getElementById("forum-new-thread-cancel");

        if (newThreadBtn) newThreadBtn.addEventListener("click", function(e) {
            e.preventDefault();
            if (!modal) return;
            var hasToken = window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken();
            if (loginHint) loginHint.hidden = !!hasToken;
            if (form) form.hidden = !hasToken;
            if (formError) { formError.hidden = true; formError.textContent = ""; }
            if (titleInput) titleInput.value = "";
            if (contentInput) contentInput.value = "";
            modal.hidden = false;
        });
        if (cancelBtn) cancelBtn.addEventListener("click", function() { if (modal) modal.hidden = true; });
        if (form) form.addEventListener("submit", function(e) {
            e.preventDefault();
            var title = (titleInput && titleInput.value) ? titleInput.value.trim() : "";
            var content = (contentInput && contentInput.value) ? contentInput.value.trim() : "";
            if (!title || !content) {
                if (formError) { formError.textContent = "Title and content are required."; formError.hidden = false; }
                return;
            }
            if (submitBtn) submitBtn.disabled = true;
            apiPost("categories/" + encodeURIComponent(categorySlug) + "/threads", { title: title, content: content })
                .then(function(thread) {
                    if (modal) modal.hidden = true;
                    window.location.href = "/forum/threads/" + encodeURIComponent(thread.slug || thread.id);
                })
                .catch(function(err) {
                    if (formError) {
                        formError.textContent = (err && err.message) || "Failed to create thread.";
                        formError.hidden = false;
                    }
                    if (submitBtn) submitBtn.disabled = false;
                });
        });
    }

    // --- Thread: detail + posts + reply ---
    function initThread(threadSlug) {
        var loading = document.getElementById("forum-thread-loading");
        var header = document.getElementById("forum-thread-header");
        var content = document.getElementById("forum-posts-content");
        var empty = document.getElementById("forum-thread-empty");
        var errEl = document.getElementById("forum-thread-error");
        var pagination = document.getElementById("forum-thread-pagination");
        var paginationInfo = document.getElementById("forum-thread-pagination-info");
        var prevBtn = document.getElementById("forum-thread-prev");
        var nextBtn = document.getElementById("forum-thread-next");
        var replySection = document.getElementById("forum-reply-section");
        var replyLoginHint = document.getElementById("forum-reply-login-hint");
        var replyForm = document.getElementById("forum-reply-form");
        var replyError = document.getElementById("forum-reply-error");
        var replyContent = document.getElementById("forum-reply-content");
        var replySubmit = document.getElementById("forum-reply-submit");
        var hasToken = !!(window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken());
        var state = {
            thread: null,
            page: 1,
            total: 0,
            perPage: 20,
            totalPages: 0,
            hasToken: hasToken,
            currentUserId: (window.ManageAuth && window.ManageAuth.getStoredUser && window.ManageAuth.getStoredUser()) ? (window.ManageAuth.getStoredUser().id) : null,
            canModerate: false
        };
        function renderThreadModBarIfNeeded() {
            if (!state.canModerate || !state.thread) return;
            var modBar = document.getElementById("forum-thread-mod-actions");
            if (!modBar || modBar.children.length > 0) return;
            var thread = state.thread;
            var lockBtn = document.createElement("button");
            lockBtn.type = "button";
            lockBtn.className = "btn btn-outline btn-sm forum-mod-lock";
            lockBtn.textContent = thread.is_locked ? "Unlock thread" : "Lock thread";
            lockBtn.dataset.threadId = thread.id;
            var pinBtn = document.createElement("button");
            pinBtn.type = "button";
            pinBtn.className = "btn btn-outline btn-sm forum-mod-pin";
            pinBtn.textContent = thread.is_pinned ? "Unpin" : "Pin";
            pinBtn.dataset.threadId = thread.id;
            var archBtn = document.createElement("button");
            archBtn.type = "button";
            archBtn.className = "btn btn-outline btn-sm forum-mod-archive";
            archBtn.textContent = thread.status === "archived" ? "Unarchive" : "Archive";
            archBtn.dataset.threadId = thread.id;
            var moveBtn = document.createElement("button");
            moveBtn.type = "button";
            moveBtn.className = "btn btn-outline btn-sm forum-mod-move";
            moveBtn.textContent = "Move…";
            moveBtn.dataset.threadId = thread.id;
            var mergeBtn = document.createElement("button");
            mergeBtn.type = "button";
            mergeBtn.className = "btn btn-outline btn-sm forum-mod-merge";
            mergeBtn.textContent = "Merge…";
            mergeBtn.dataset.threadId = thread.id;
            modBar.appendChild(lockBtn);
            modBar.appendChild(pinBtn);
            modBar.appendChild(archBtn);
            modBar.appendChild(moveBtn);
            modBar.appendChild(mergeBtn);
            modBar.hidden = false;
            lockBtn.addEventListener("click", function() {
                var tid = lockBtn.dataset.threadId;
                if (!tid) return;
                lockBtn.disabled = true;
                apiPost("threads/" + tid + "/" + (thread.is_locked ? "unlock" : "lock"), {}).then(function() {
                    state.thread.is_locked = !thread.is_locked;
                    thread.is_locked = state.thread.is_locked;
                    lockBtn.textContent = state.thread.is_locked ? "Unlock thread" : "Lock thread";
                }).catch(function() {}).then(function() { lockBtn.disabled = false; });
            });
            pinBtn.addEventListener("click", function() {
                var tid = pinBtn.dataset.threadId;
                if (!tid) return;
                pinBtn.disabled = true;
                apiPost("threads/" + tid + "/" + (thread.is_pinned ? "unpin" : "pin"), {}).then(function() {
                    state.thread.is_pinned = !thread.is_pinned;
                    thread.is_pinned = state.thread.is_pinned;
                    pinBtn.textContent = state.thread.is_pinned ? "Unpin" : "Pin";
                }).catch(function() {}).then(function() { pinBtn.disabled = false; });
            });
            archBtn.addEventListener("click", function() {
                var tid = archBtn.dataset.threadId;
                if (!tid) return;
                archBtn.disabled = true;
                var isArchived = thread.status === "archived";
                apiPost("threads/" + tid + "/" + (isArchived ? "unarchive" : "archive"), {}).then(function() {
                    state.thread.status = isArchived ? "open" : "archived";
                    thread.status = state.thread.status;
                    archBtn.textContent = state.thread.status === "archived" ? "Unarchive" : "Archive";
                }).catch(function() {}).then(function() { archBtn.disabled = false; });
            });
            moveBtn.addEventListener("click", function() {
                var tid = moveBtn.dataset.threadId;
                if (!tid) return;
                var existing = document.getElementById("forum-move-wrap");
                if (existing) { existing.remove(); return; }
                var base = (window.FrontendConfig && window.FrontendConfig.getApiBaseUrl) ? window.FrontendConfig.getApiBaseUrl() : "";
                var apiAuth = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
                if (!apiAuth) return;
                apiAuth((base ? base.replace(/\/$/, "") : "") + "/api/v1/forum/categories").then(function(data) {
                    var cats = (data && data.items) || [];
                    var currentId = thread.category_id || (thread.category && thread.category.id);
                    var wrap = document.createElement("div");
                    wrap.id = "forum-move-wrap";
                    wrap.className = "forum-move-wrap";
                    var label = document.createElement("label");
                    label.htmlFor = "forum-move-select";
                    label.textContent = "Move to category: ";
                    var sel = document.createElement("select");
                    sel.id = "forum-move-select";
                    cats.forEach(function(c) {
                        var opt = document.createElement("option");
                        opt.value = c.id;
                        opt.textContent = (c.title || c.slug) + (c.id === currentId ? " (current)" : "");
                        if (c.id === currentId) opt.disabled = true;
                        sel.appendChild(opt);
                    });
                    var goBtn = document.createElement("button");
                    goBtn.type = "button";
                    goBtn.className = "btn btn-primary btn-sm";
                    goBtn.textContent = "Move";
                    var cancelBtn = document.createElement("button");
                    cancelBtn.type = "button";
                    cancelBtn.className = "btn btn-ghost btn-sm";
                    cancelBtn.textContent = "Cancel";
                    wrap.appendChild(label);
                    wrap.appendChild(sel);
                    wrap.appendChild(goBtn);
                    wrap.appendChild(cancelBtn);
                    modBar.parentNode && modBar.parentNode.insertBefore(wrap, modBar.nextSibling);
                    cancelBtn.addEventListener("click", function() { wrap.remove(); });
                    goBtn.addEventListener("click", function() {
                        var num = parseInt(sel.value, 10);
                        if (isNaN(num) || num === currentId) return;
                        goBtn.disabled = true;
                        apiPost("threads/" + tid + "/move", { category_id: num }).then(function(t) {
                            state.thread = t;
                            state.thread.category_id = t.category_id;
                            if (t.category) state.thread.category = t.category;
                            thread = state.thread;
                            var back = document.getElementById("forum-thread-back-category");
                            var backBottom = document.getElementById("forum-thread-back-category-bottom");
                            if (state.thread.category && state.thread.category.slug) {
                                var href = "/forum/categories/" + encodeURIComponent(state.thread.category.slug);
                                if (back) back.href = href;
                                if (backBottom) backBottom.href = href;
                            }
                            wrap.remove();
                        }).catch(function() {}).then(function() { goBtn.disabled = false; });
                    });
                });
            });
            mergeBtn.addEventListener("click", function() {
                var tid = mergeBtn.dataset.threadId;
                if (!tid) return;
                var input = window.prompt("Enter target thread slug or ID to merge into:", "");
                if (!input) return;
                var targetIdPromise;
                var num = parseInt(input, 10);
                if (!isNaN(num)) {
                    targetIdPromise = Promise.resolve(num);
                } else {
                    targetIdPromise = apiGet("threads/" + encodeURIComponent(input)).then(function(t) {
                        return t && t.id;
                    });
                }
                targetIdPromise.then(function(targetId) {
                    if (!targetId) {
                        alert("Target thread not found.");
                        return;
                    }
                    if (String(targetId) === String(tid)) {
                        alert("Cannot merge a thread into itself.");
                        return;
                    }
                    if (!window.confirm("Merge this thread into target thread " + targetId + "? This cannot be undone.")) {
                        return;
                    }
                    mergeBtn.disabled = true;
                    apiPost("threads/" + tid + "/merge", { target_thread_id: targetId })
                        .then(function(t) {
                            var slug = (t && t.slug) || null;
                            var url = slug ? ("/forum/threads/" + encodeURIComponent(slug)) : window.location.href;
                            window.location.href = url;
                        })
                        .catch(function(err) {
                            alert((err && err.message) || "Failed to merge threads.");
                        })
                        .then(function() { mergeBtn.disabled = false; });
                }).catch(function() {
                    alert("Failed to resolve target thread.");
                });
            });
        }
        if (hasToken && window.ManageAuth && window.ManageAuth.getMe) {
            window.ManageAuth.getMe().then(function(u) {
                if (u && u.id) state.currentUserId = u.id;
                state.canModerate = !!(u && (u.role === "moderator" || u.role === "admin"));
                renderThreadModBarIfNeeded();
            }).catch(function() {});
        }

        var backCategory = document.getElementById("forum-thread-back-category");
        var backCategoryBottom = document.getElementById("forum-thread-back-category-bottom");

        function setBackLink(href) {
            if (backCategory) backCategory.href = href || "#";
            if (backCategoryBottom) backCategoryBottom.href = href || "#";
        }

        function showLoading(show) {
            if (loading) loading.hidden = !show;
            if (header) header.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (pagination) pagination.hidden = true;
        }
        function showError(msg) {
            if (loading) loading.hidden = true;
            if (header) header.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) { errEl.textContent = msg || "Failed to load."; errEl.hidden = false; }
            if (pagination) pagination.hidden = true;
        }
        function renderPosts(items, page, total, perPage) {
            if (loading) loading.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (!content) return;
            content.innerHTML = "";
            var currentUserId = state.currentUserId;
            items.forEach(function(p) {
                var post = document.createElement("article");
                post.id = "post-" + p.id;
                post.className = "forum-post";
                post.dataset.postId = p.id;
                var meta = document.createElement("div");
                meta.className = "forum-post-meta";
                var metaParts = [];
                if (p.author_username) metaParts.push("<span class=\"forum-post-author\">" + escapeHtml(p.author_username) + "</span>");
                metaParts.push("<span class=\"forum-post-date\">" + escapeHtml(formatDate(p.created_at)) + "</span>");
                if (p.edited_at) metaParts.push("<span class=\"muted\">(edited " + escapeHtml(formatDate(p.edited_at)) + ")</span>");
                meta.innerHTML = metaParts.join(" · ");
                var body = document.createElement("div");
                body.className = "forum-post-body";
                body.innerHTML = formatPostContent(p.content || "");
                post.appendChild(meta);
                if (p.status === "hidden" && state.canModerate) {
                    var hiddenBadge = document.createElement("span");
                    hiddenBadge.className = "forum-badge forum-badge-hidden";
                    hiddenBadge.textContent = "Hidden";
                    post.insertBefore(hiddenBadge, body);
                }
                post.appendChild(body);
                var actions = document.createElement("div");
                actions.className = "forum-post-actions";
                var likeCount = document.createElement("span");
                likeCount.className = "forum-post-like-count";
                likeCount.textContent = (p.like_count || 0) + " like" + ((p.like_count || 0) === 1 ? "" : "s");
                actions.appendChild(likeCount);
                if (state.hasToken) {
                    var likeBtn = document.createElement("button");
                    likeBtn.type = "button";
                    likeBtn.className = "btn btn-ghost forum-btn-like";
                    likeBtn.textContent = p.liked_by_me ? "Unlike" : "Like";
                    likeBtn.dataset.postId = p.id;
                    likeBtn.dataset.liked = p.liked_by_me ? "1" : "0";
                    actions.appendChild(likeBtn);
                    var reportBtn = document.createElement("button");
                    reportBtn.type = "button";
                    reportBtn.className = "btn btn-ghost forum-btn-report";
                    reportBtn.textContent = "Report";
                    reportBtn.dataset.postId = p.id;
                    actions.appendChild(reportBtn);
                    if (currentUserId && p.author_id === currentUserId) {
                        var editBtn = document.createElement("button");
                        editBtn.type = "button";
                        editBtn.className = "btn btn-ghost forum-btn-edit";
                        editBtn.textContent = "Edit";
                        editBtn.dataset.postId = p.id;
                        actions.appendChild(editBtn);
                        var delBtn = document.createElement("button");
                        delBtn.type = "button";
                        delBtn.className = "btn btn-ghost forum-btn-delete";
                        delBtn.textContent = "Delete";
                        delBtn.dataset.postId = p.id;
                        actions.appendChild(delBtn);
                    }
                    if (state.canModerate) {
                        var hideBtn = document.createElement("button");
                        hideBtn.type = "button";
                        hideBtn.className = "btn btn-ghost forum-btn-hide";
                        hideBtn.textContent = p.status === "hidden" ? "Unhide" : "Hide";
                        hideBtn.dataset.postId = p.id;
                        hideBtn.dataset.hidden = p.status === "hidden" ? "1" : "0";
                        actions.appendChild(hideBtn);
                        if (p.parent_post_id == null) {
                            var splitBtn = document.createElement("button");
                            splitBtn.type = "button";
                            splitBtn.className = "btn btn-ghost forum-btn-split";
                            splitBtn.textContent = "Split to new thread";
                            splitBtn.dataset.postId = p.id;
                            actions.appendChild(splitBtn);
                        }
                    }
                }
                post.appendChild(actions);
                content.appendChild(post);
            });
            content.hidden = false;
            if (replySection) replySection.hidden = false;
            state.total = total;
            state.totalPages = perPage > 0 ? Math.ceil(total / perPage) : 0;
            if (pagination) {
                pagination.hidden = state.totalPages <= 1;
                if (paginationInfo) paginationInfo.textContent = "Page " + page + " of " + (state.totalPages || 1) + " (" + total + " total)";
                if (prevBtn) prevBtn.disabled = page <= 1;
                if (nextBtn) nextBtn.disabled = page >= state.totalPages;
            }
        }

        function renderTagsSection() {
            var tagsSection = document.getElementById("forum-thread-tags-section");
            if (!tagsSection || !state.thread) return;
            tagsSection.innerHTML = "";
            var thread = state.thread;
            var isAuthor = state.currentUserId && state.currentUserId === thread.author_id;
            var canEditTags = state.hasToken && (isAuthor || state.canModerate);
            var tags = thread.tags || [];

            // Create tags container
            var container = document.createElement("div");
            container.className = "forum-tags-container";

            // Display existing tags as pills
            if (tags.length > 0) {
                var tagList = document.createElement("div");
                tagList.className = "forum-tags-list";
                tagList.id = "forum-thread-tags-display";
                tags.forEach(function(tag) {
                    var pill = document.createElement("span");
                    pill.className = "forum-tag-pill";
                    pill.textContent = tag.label || tag.slug;
                    tagList.appendChild(pill);
                });
                container.appendChild(tagList);
            }

            // Add edit button if user is author or moderator
            if (canEditTags) {
                var editBtn = document.createElement("button");
                editBtn.type = "button";
                editBtn.className = "btn btn-outline btn-sm forum-btn-edit-tags";
                editBtn.textContent = tags.length > 0 ? "Edit tags" : "Add tags";
                editBtn.dataset.threadId = thread.id;
                container.appendChild(editBtn);

                editBtn.addEventListener("click", function() {
                    showTagEditor();
                });
            }

            tagsSection.appendChild(container);
            tagsSection.hidden = false;
        }

        function showTagEditor() {
            var tagsSection = document.getElementById("forum-thread-tags-section");
            if (!tagsSection || !state.thread) return;

            // Clear the section
            tagsSection.innerHTML = "";

            var thread = state.thread;
            var currentTags = (thread.tags || []).map(function(t) { return t.slug; });

            var editorContainer = document.createElement("div");
            editorContainer.className = "forum-tag-editor";

            // Existing tags with remove buttons
            if (currentTags.length > 0) {
                var tagsList = document.createElement("div");
                tagsList.className = "forum-tags-editor-list";
                tagsList.id = "forum-tags-editor-list";
                currentTags.forEach(function(slug) {
                    var tagItem = document.createElement("div");
                    tagItem.className = "forum-tag-item";
                    tagItem.dataset.slug = slug;
                    var label = document.createElement("span");
                    label.className = "forum-tag-label";
                    label.textContent = slug;
                    var removeBtn = document.createElement("button");
                    removeBtn.type = "button";
                    removeBtn.className = "forum-tag-remove";
                    removeBtn.textContent = "×";
                    removeBtn.title = "Remove tag";
                    removeBtn.addEventListener("click", function() {
                        tagItem.remove();
                    });
                    tagItem.appendChild(label);
                    tagItem.appendChild(removeBtn);
                    tagsList.appendChild(tagItem);
                });
                editorContainer.appendChild(tagsList);
            }

            // Input field for adding new tags
            var inputGroup = document.createElement("div");
            inputGroup.className = "forum-tag-input-group";
            var input = document.createElement("input");
            input.type = "text";
            input.className = "forum-tag-input";
            input.placeholder = "Add tag (press Enter or click Add)";
            input.id = "forum-tag-input";
            var addBtn = document.createElement("button");
            addBtn.type = "button";
            addBtn.className = "btn btn-outline btn-sm";
            addBtn.textContent = "Add";
            addBtn.id = "forum-add-tag-btn";
            inputGroup.appendChild(input);
            inputGroup.appendChild(addBtn);
            editorContainer.appendChild(inputGroup);

            // Error message
            var errorMsg = document.createElement("p");
            errorMsg.className = "forum-form-error";
            errorMsg.id = "forum-tag-editor-error";
            errorMsg.hidden = true;
            editorContainer.appendChild(errorMsg);

            // Action buttons
            var actions = document.createElement("div");
            actions.className = "forum-tag-editor-actions";
            var saveBtn = document.createElement("button");
            saveBtn.type = "button";
            saveBtn.className = "btn btn-primary btn-sm";
            saveBtn.textContent = "Save tags";
            saveBtn.id = "forum-save-tags-btn";
            var cancelBtn = document.createElement("button");
            cancelBtn.type = "button";
            cancelBtn.className = "btn btn-ghost btn-sm";
            cancelBtn.textContent = "Cancel";
            cancelBtn.id = "forum-cancel-tags-btn";
            actions.appendChild(saveBtn);
            actions.appendChild(cancelBtn);
            editorContainer.appendChild(actions);

            var tagsSection = document.getElementById("forum-thread-tags-section");
            tagsSection.innerHTML = "";
            tagsSection.appendChild(editorContainer);
            tagsSection.hidden = false;

            // Focus input
            input.focus();

            // Add tag button click handler
            addBtn.addEventListener("click", function() {
                var val = input.value.trim().toLowerCase();
                if (!val) return;
                if (!/^[a-z0-9\-]+$/.test(val)) {
                    var err = document.getElementById("forum-tag-editor-error");
                    if (err) {
                        err.textContent = "Tags must contain only lowercase letters, numbers, and hyphens";
                        err.hidden = false;
                    }
                    return;
                }
                var tagsList = document.getElementById("forum-tags-editor-list");
                if (!tagsList) {
                    tagsList = document.createElement("div");
                    tagsList.className = "forum-tags-editor-list";
                    tagsList.id = "forum-tags-editor-list";
                    editorContainer.insertBefore(tagsList, inputGroup);
                }
                // Check if tag already exists
                var existing = Array.from(tagsList.querySelectorAll("[data-slug]")).some(function(el) {
                    return el.dataset.slug === val;
                });
                if (existing) {
                    var err = document.getElementById("forum-tag-editor-error");
                    if (err) {
                        err.textContent = "This tag is already added";
                        err.hidden = false;
                    }
                    return;
                }
                var tagItem = document.createElement("div");
                tagItem.className = "forum-tag-item";
                tagItem.dataset.slug = val;
                var label = document.createElement("span");
                label.className = "forum-tag-label";
                label.textContent = val;
                var removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.className = "forum-tag-remove";
                removeBtn.textContent = "×";
                removeBtn.title = "Remove tag";
                removeBtn.addEventListener("click", function() {
                    tagItem.remove();
                });
                tagItem.appendChild(label);
                tagItem.appendChild(removeBtn);
                tagsList.appendChild(tagItem);
                input.value = "";
                var err = document.getElementById("forum-tag-editor-error");
                if (err) {
                    err.hidden = true;
                    err.textContent = "";
                }
                input.focus();
            });

            // Enter key handler
            input.addEventListener("keypress", function(e) {
                if (e.key === "Enter") {
                    e.preventDefault();
                    addBtn.click();
                }
            });

            // Save handler
            saveBtn.addEventListener("click", function() {
                saveBtn.disabled = true;
                var tagsList = document.getElementById("forum-tags-editor-list");
                var tags = Array.from((tagsList || []).querySelectorAll("[data-slug]")).map(function(el) {
                    return el.dataset.slug;
                });
                var errorEl = document.getElementById("forum-tag-editor-error");
                apiPut("threads/" + state.thread.id + "/tags", { tags: tags })
                    .then(function(res) {
                        state.thread.tags = res.tags || [];
                        renderTagsSection();
                    })
                    .catch(function(err) {
                        if (errorEl) {
                            errorEl.textContent = (err && err.message) || "Failed to save tags";
                            errorEl.hidden = false;
                        }
                        saveBtn.disabled = false;
                    });
            });

            // Cancel handler
            cancelBtn.addEventListener("click", function() {
                renderTagsSection();
            });
        }

        showLoading(true);
        apiGet("threads/" + encodeURIComponent(threadSlug))
            .then(function(thread) {
                state.thread = thread;
                if (header) {
                    header.innerHTML = "";
                    var h1 = document.createElement("h1");
                    h1.className = "forum-thread-title";
                    h1.textContent = thread.title || "Thread";
                    header.appendChild(h1);
                    var meta = document.createElement("p");
                    meta.className = "forum-thread-meta muted";
                    var parts = [];
                    if (thread.author_username) parts.push("by " + thread.author_username);
                    if (thread.reply_count != null) parts.push(thread.reply_count + " replies");
                    if (thread.view_count != null) parts.push(thread.view_count + " views");
                    if (thread.created_at) parts.push(formatDate(thread.created_at));
                    meta.textContent = parts.join(" · ");
                    header.appendChild(meta);
                    if (thread.status === "archived") {
                        var archivedHint = document.createElement("p");
                        archivedHint.className = "forum-thread-status-hint";
                        archivedHint.textContent = "This thread is archived and visible to staff only. It may be the result of a merge.";
                        header.appendChild(archivedHint);
                    }
                    if (thread.category && thread.category.slug) {
                        setBackLink("/forum/categories/" + encodeURIComponent(thread.category.slug));
                    }
                    if (state.hasToken) {
                        var subWrap = document.createElement("div");
                        subWrap.className = "forum-thread-subscribe-wrap";
                        var subBtn = document.createElement("button");
                        subBtn.type = "button";
                        subBtn.className = "btn btn-outline btn-sm forum-btn-subscribe";
                        subBtn.textContent = thread.subscribed_by_me ? "Unsubscribe" : "Subscribe";
                        subBtn.dataset.threadId = thread.id;
                        subWrap.appendChild(subBtn);
                        header.appendChild(subWrap);
                        subBtn.addEventListener("click", function() {
                            var tid = subBtn.dataset.threadId;
                            if (!tid) return;
                            subBtn.disabled = true;
                            var isSub = state.thread.subscribed_by_me;
                            var req = isSub
                                ? apiDelete("threads/" + tid + "/subscribe")
                                : apiPost("threads/" + tid + "/subscribe", {});
                            req.then(function() {
                                state.thread.subscribed_by_me = !isSub;
                                subBtn.textContent = state.thread.subscribed_by_me ? "Unsubscribe" : "Subscribe";
                            }).catch(function() {}).then(function() { subBtn.disabled = false; });
                        });
                    }
                    var modBar = document.createElement("div");
                    modBar.id = "forum-thread-mod-actions";
                    modBar.className = "forum-thread-mod-actions";
                    modBar.hidden = true;
                    header.appendChild(modBar);
                    renderThreadModBarIfNeeded();
                    header.hidden = false;
                }
                // Render tags section
                renderTagsSection();
                var threadId = thread.id;
                return apiGet("threads/" + threadId + "/posts?page=1&limit=" + state.perPage);
            })
            .then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : items.length;
                var page = (data && typeof data.page === "number") ? data.page : 1;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                state.page = page;
                if (items.length === 0) {
                    if (loading) loading.hidden = true;
                    if (content) content.hidden = true;
                    if (empty) empty.hidden = false;
                    if (replySection) replySection.hidden = false;
                } else renderPosts(items, page, total, perPage);
            })
            .catch(function(e) { showError(typeof e === "string" ? e : (e && e.message) || "Failed to load."); });

        function fetchPosts(page) {
            var url = "threads/" + state.thread.id + "/posts?page=" + page + "&limit=" + state.perPage;
            if (state.canModerate) url += "&include_hidden=true";
            return apiGet(url);
        }
        if (prevBtn) prevBtn.addEventListener("click", function() {
            if (state.page <= 1 || !state.thread) return;
            state.page--;
            fetchPosts(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                renderPosts(items, page, total, perPage);
            }).catch(function(e) { showError(e && e.message); });
        });
        if (nextBtn) nextBtn.addEventListener("click", function() {
            if (state.page >= state.totalPages || !state.thread) return;
            state.page++;
            fetchPosts(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                renderPosts(items, page, total, perPage);
            }).catch(function(e) { showError(e && e.message); });
        });

        if (replyLoginHint) replyLoginHint.hidden = !!state.hasToken;
        if (replyForm) replyForm.hidden = !state.hasToken;

        if (replyForm) replyForm.addEventListener("submit", function(e) {
            e.preventDefault();
            if (!state.thread) return;
            var contentText = (replyContent && replyContent.value) ? replyContent.value.trim() : "";
            if (!contentText) return;
            if (replySubmit) replySubmit.disabled = true;
            if (replyError) { replyError.hidden = true; replyError.textContent = ""; }
            apiPost("threads/" + state.thread.id + "/posts", { content: contentText })
                .then(function() {
                    if (replyContent) replyContent.value = "";
                    state.total++;
                    state.totalPages = Math.ceil(state.total / state.perPage);
                    state.page = state.totalPages;
                    return fetchPosts(state.page);
                })
                .then(function(data) {
                    var items = (data && data.items) ? data.items : [];
                    var total = (data && typeof data.total === "number") ? data.total : state.total;
                    var page = (data && typeof data.page === "number") ? data.page : state.page;
                    var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                    state.total = total;
                    renderPosts(items, page, total, perPage);
                    if (content) content.scrollIntoView({ behavior: "smooth" });
                    if (replySubmit) replySubmit.disabled = false;
                })
                .catch(function(err) {
                    if (replyError) {
                        replyError.textContent = (err && err.message) || "Failed to post.";
                        replyError.hidden = false;
                    }
                    if (replySubmit) replySubmit.disabled = false;
                });
        });

        content.addEventListener("click", function(e) {
            var likeBtn = e.target && e.target.closest && e.target.closest(".forum-btn-like");
            var reportBtn = e.target && e.target.closest && e.target.closest(".forum-btn-report");
            var editBtn = e.target && e.target.closest && e.target.closest(".forum-btn-edit");
            var delBtn = e.target && e.target.closest && e.target.closest(".forum-btn-delete");
            var hideBtn = e.target && e.target.closest && e.target.closest(".forum-btn-hide");
            var splitBtn = e.target && e.target.closest && e.target.closest(".forum-btn-split");

            if (likeBtn) {
                var postId = likeBtn.dataset.postId;
                if (!postId || !state.thread) return;
                likeBtn.disabled = true;
                var isLiked = likeBtn.dataset.liked === "1";
                var promise = isLiked ? apiDelete("posts/" + postId + "/like") : apiPost("posts/" + postId + "/like", {});
                promise.then(function(res) {
                    var cnt = res.like_count != null ? res.like_count : 0;
                    likeBtn.textContent = res.liked_by_me ? "Unlike" : "Like";
                    likeBtn.dataset.liked = res.liked_by_me ? "1" : "0";
                    var countEl = likeBtn.parentElement && likeBtn.parentElement.querySelector(".forum-post-like-count");
                    if (countEl) countEl.textContent = cnt + " like" + (cnt === 1 ? "" : "s");
                }).catch(function() {}).then(function() { likeBtn.disabled = false; });
            }

            if (reportBtn) {
                var reportPostId = reportBtn.dataset.postId;
                if (!reportPostId) return;
                var modal = document.getElementById("forum-report-modal");
                var targetInput = document.getElementById("forum-report-target-id");
                var typeInput = document.getElementById("forum-report-target-type");
                var reasonInput = document.getElementById("forum-report-reason");
                if (modal && typeInput && targetInput) {
                    typeInput.value = "post";
                    targetInput.value = reportPostId;
                    if (reasonInput) reasonInput.value = "";
                    modal.hidden = false;
                }
            }

            if (editBtn) {
                var editPostId = editBtn.dataset.postId;
                if (!editPostId) return;
                var article = editBtn.closest && editBtn.closest(".forum-post");
                if (!article) return;
                var bodyEl = article.querySelector(".forum-post-body");
                if (!bodyEl) return;
                var currentContent = bodyEl.textContent || "";
                var textarea = document.createElement("textarea");
                textarea.className = "forum-edit-textarea";
                textarea.rows = 4;
                textarea.value = currentContent;
                var wrap = document.createElement("div");
                wrap.className = "forum-edit-wrap";
                var saveBtn = document.createElement("button");
                saveBtn.type = "button";
                saveBtn.className = "btn btn-primary forum-edit-save";
                saveBtn.textContent = "Save";
                var cancelBtn = document.createElement("button");
                cancelBtn.type = "button";
                cancelBtn.className = "btn btn-ghost forum-edit-cancel";
                cancelBtn.textContent = "Cancel";
                bodyEl.replaceWith(wrap);
                wrap.appendChild(textarea);
                wrap.appendChild(saveBtn);
                wrap.appendChild(cancelBtn);
                function restore() {
                    var newBody = document.createElement("div");
                    newBody.className = "forum-post-body";
                    newBody.innerHTML = formatPostContent(textarea.value);
                    wrap.replaceWith(newBody);
                }
                cancelBtn.addEventListener("click", restore);
                saveBtn.addEventListener("click", function() {
                    var newContent = (textarea.value || "").trim();
                    if (!newContent) return;
                    saveBtn.disabled = true;
                    apiPut("posts/" + editPostId, { content: newContent })
                        .then(function() {
                            var newBody = document.createElement("div");
                            newBody.className = "forum-post-body";
                            newBody.innerHTML = formatPostContent(newContent);
                            wrap.replaceWith(newBody);
                        })
                        .catch(function(err) {
                            alert((err && err.message) || "Failed to update.");
                        })
                        .then(function() { saveBtn.disabled = false; });
                });
            }

            if (delBtn) {
                var delPostId = delBtn.dataset.postId;
                if (!delPostId || !state.thread) return;
                if (!confirm("Delete this post?")) return;
                delBtn.disabled = true;
                apiDelete("posts/" + delPostId)
                    .then(function() {
                        return fetchPosts(state.page);
                    })
                    .then(function(data) {
                        var items = (data && data.items) ? data.items : [];
                        var total = (data && typeof data.total === "number") ? data.total : Math.max(0, state.total - 1);
                        var page = (data && typeof data.page === "number") ? data.page : state.page;
                        var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                        state.total = total;
                        renderPosts(items, page, total, perPage);
                    })
                    .catch(function() { delBtn.disabled = false; });
            }

            if (splitBtn) {
                var splitPostId = splitBtn.dataset.postId;
                if (!splitPostId || !state.thread) return;
                if (!window.confirm("Split this post and its direct replies into a new thread?")) return;
                var suggestedTitle = state.thread && state.thread.title ? state.thread.title : "New thread";
                var title = window.prompt("New thread title:", suggestedTitle);
                if (!title) return;
                splitBtn.disabled = true;
                apiPost("threads/" + state.thread.id + "/split", {
                    root_post_id: parseInt(splitPostId, 10),
                    title: title
                }).then(function(t) {
                    var slug = (t && t.slug) || null;
                    if (slug) {
                        window.location.href = "/forum/threads/" + encodeURIComponent(slug);
                    }
                }).catch(function(err) {
                    alert((err && err.message) || "Failed to split thread.");
                }).then(function() {
                    splitBtn.disabled = false;
                });
            }

            if (hideBtn) {
                var hidePostId = hideBtn.dataset.postId;
                if (!hidePostId || !state.thread) return;
                var isHidden = hideBtn.dataset.hidden === "1";
                hideBtn.disabled = true;
                var path = "posts/" + hidePostId + "/" + (isHidden ? "unhide" : "hide");
                apiPost(path, {}).then(function() {
                    hideBtn.textContent = isHidden ? "Hide" : "Unhide";
                    hideBtn.dataset.hidden = isHidden ? "0" : "1";
                    var article = hideBtn.closest && hideBtn.closest(".forum-post");
                    if (article) {
                        var badge = article.querySelector(".forum-badge-hidden");
                        if (isHidden) {
                            if (badge) badge.remove();
                        } else {
                            if (!badge) {
                                var b = document.createElement("span");
                                b.className = "forum-badge forum-badge-hidden";
                                b.textContent = "Hidden";
                                var bodyEl = article.querySelector(".forum-post-body");
                                if (bodyEl) article.insertBefore(b, bodyEl);
                            }
                        }
                    }
                }).catch(function() {}).then(function() { hideBtn.disabled = false; });
            }
        });

        var reportModal = document.getElementById("forum-report-modal");
        var reportForm = document.getElementById("forum-report-form");
        var reportError = document.getElementById("forum-report-error");
        var reportSuccess = document.getElementById("forum-report-success");
        if (reportForm) reportForm.addEventListener("submit", function(e) {
            e.preventDefault();
            var typeInput = document.getElementById("forum-report-target-type");
            var targetInput = document.getElementById("forum-report-target-id");
            var reasonInput = document.getElementById("forum-report-reason");
            var reason = (reasonInput && reasonInput.value) ? reasonInput.value.trim() : "";
            if (!reason) {
                if (reportError) { reportError.textContent = "Please enter a reason."; reportError.hidden = false; }
                if (reportSuccess) reportSuccess.hidden = true;
                return;
            }
            if (!typeInput || !targetInput) return;
            var targetId = parseInt(targetInput.value, 10);
            if (isNaN(targetId)) return;
            if (reportError) reportError.hidden = true;
            if (reportSuccess) reportSuccess.hidden = true;
            apiPost("reports", { target_type: typeInput.value, target_id: targetId, reason: reason })
                .then(function() {
                    if (reportModal) reportModal.hidden = true;
                    if (reportSuccess) { reportSuccess.textContent = "Report submitted."; reportSuccess.hidden = false; }
                    setTimeout(function() { if (reportSuccess) reportSuccess.hidden = true; }, 3000);
                })
                .catch(function(err) {
                    if (reportError) { reportError.textContent = (err && err.message) || "Failed to submit report."; reportError.hidden = false; }
                });
        });
        var reportCancel = document.getElementById("forum-report-cancel");
        if (reportCancel) reportCancel.addEventListener("click", function() {
            if (reportModal) reportModal.hidden = true;
        });
    }

    function initNotifications() {
        var loading = document.getElementById("forum-notifications-loading");
        var errEl = document.getElementById("forum-notifications-error");
        var empty = document.getElementById("forum-notifications-empty");
        var loginHint = document.getElementById("forum-notifications-login-hint");
        var list = document.getElementById("forum-notifications-list");
        var pagination = document.getElementById("forum-notifications-pagination");
        var paginationInfo = document.getElementById("forum-notifications-pagination-info");
        var prevBtn = document.getElementById("forum-notifications-prev");
        var nextBtn = document.getElementById("forum-notifications-next");
        var toolbar = document.getElementById("forum-notifications-toolbar");
        var markAllReadBtn = document.getElementById("forum-notifications-mark-all-read");
        var hasToken = !!(window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken());
        var state = { page: 1, total: 0, perPage: 20, totalPages: 0 };

        function hideAll() {
            if (loading) loading.hidden = true;
            if (errEl) errEl.hidden = true;
            if (empty) empty.hidden = true;
            if (loginHint) loginHint.hidden = true;
            if (toolbar) toolbar.hidden = true;
            if (list) list.hidden = true;
            if (pagination) pagination.hidden = true;
        }
        if (!hasToken) {
            hideAll();
            if (loginHint) loginHint.hidden = false;
            return;
        }
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            hideAll();
            if (errEl) { errEl.textContent = "Auth not available."; errEl.hidden = false; }
            return;
        }
        var base = (window.FrontendConfig && window.FrontendConfig.getApiBaseUrl) ? window.FrontendConfig.getApiBaseUrl() : "";
        function fetchNotifications(page) {
            var url = (base ? base.replace(/\/$/, "") : "") + "/api/v1/notifications?page=" + page + "&limit=" + state.perPage;
            return api(url);
        }
        function markRead(id) {
            var url = (base ? base.replace(/\/$/, "") : "") + "/api/v1/notifications/" + id + "/read";
            return api(url, { method: "PATCH" });
        }
        function markAllRead() {
            var url = (base ? base.replace(/\/$/, "") : "") + "/api/v1/notifications/read-all";
            return api(url, { method: "PUT" });
        }
        function render(items, page, total, perPage) {
            hideAll();
            if (!list) return;
            state.total = total;
            state.totalPages = perPage > 0 ? Math.ceil(total / perPage) : 0;
            if (!items || items.length === 0) {
                if (empty) empty.hidden = false;
                return;
            }
            list.innerHTML = "";
            items.forEach(function(n) {
                var li = document.createElement("li");
                li.className = "forum-notification-item" + (n.is_read ? " forum-notification-read" : "");
                var link = document.createElement("a");
                var href = n.thread_slug ? "/forum/threads/" + encodeURIComponent(n.thread_slug) : "#";
                if (n.thread_slug && n.target_post_id) href += "#post-" + n.target_post_id;
                link.href = href;
                link.className = "forum-notification-link";
                link.textContent = n.message || "Notification";
                li.appendChild(link);
                var meta = document.createElement("span");
                meta.className = "forum-notification-meta muted";
                meta.textContent = formatDate(n.created_at) || "";
                li.appendChild(meta);
                if (!n.is_read) {
                    var readBtn = document.createElement("button");
                    readBtn.type = "button";
                    readBtn.className = "btn btn-ghost btn-sm forum-notification-mark-read";
                    readBtn.textContent = "Mark as read";
                    readBtn.dataset.id = n.id;
                    readBtn.addEventListener("click", function() {
                        var id = readBtn.dataset.id;
                        if (!id) return;
                        readBtn.disabled = true;
                        markRead(id).then(function() {
                            li.classList.add("forum-notification-read");
                            readBtn.remove();
                        }).catch(function() {}).then(function() { readBtn.disabled = false; });
                    });
                    li.appendChild(readBtn);
                }
                list.appendChild(li);
            });
            list.hidden = false;
            if (toolbar) toolbar.hidden = false;
            if (pagination) {
                pagination.hidden = state.totalPages <= 1;
                if (paginationInfo) paginationInfo.textContent = "Page " + page + " of " + (state.totalPages || 1) + " (" + total + " total)";
                if (prevBtn) prevBtn.disabled = page <= 1;
                if (nextBtn) nextBtn.disabled = page >= state.totalPages;
            }
        }
        if (loading) loading.hidden = false;
        fetchNotifications(1)
            .then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : 1;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                state.page = page;
                render(items, page, total, perPage);
            })
            .catch(function(e) {
                hideAll();
                if (errEl) { errEl.textContent = (e && e.message) || "Failed to load notifications."; errEl.hidden = false; }
            });
        if (prevBtn) prevBtn.addEventListener("click", function() {
            if (state.page <= 1) return;
            state.page--;
            if (loading) loading.hidden = false;
            fetchNotifications(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                render(items, page, total, perPage);
            }).catch(function() { if (loading) loading.hidden = true; });
        });
        if (nextBtn) nextBtn.addEventListener("click", function() {
            if (state.page >= state.totalPages) return;
            state.page++;
            if (loading) loading.hidden = false;
            fetchNotifications(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                render(items, page, total, perPage);
            }).catch(function() { if (loading) loading.hidden = true; });
        });
        if (markAllReadBtn) markAllReadBtn.addEventListener("click", function() {
            markAllReadBtn.disabled = true;
            markAllRead().then(function() {
                return fetchNotifications(1);
            }).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : 1;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                state.page = 1;
                render(items, page, total, perPage);
            }).catch(function() {}).then(function() { markAllReadBtn.disabled = false; });
        });
    }

    // --- Saved Threads: bookmarks list ---
    function initSavedThreads() {
        var loading = document.getElementById("forum-saved-loading");
        var content = document.getElementById("forum-saved-content");
        var empty = document.getElementById("forum-saved-empty");
        var errEl = document.getElementById("forum-saved-error");
        var pagination = document.getElementById("forum-saved-pagination");
        var paginationInfo = document.getElementById("forum-saved-pagination-info");
        var prevBtn = document.getElementById("forum-saved-prev");
        var nextBtn = document.getElementById("forum-saved-next");
        var state = { page: 1, total: 0, perPage: 20, totalPages: 0 };

        function showLoading(show) {
            if (loading) loading.hidden = !show;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (pagination) pagination.hidden = true;
        }

        function showError(msg) {
            if (loading) loading.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) { errEl.textContent = msg || "Failed to load."; errEl.hidden = false; }
            if (pagination) pagination.hidden = true;
        }

        function toggleBookmark(threadId, btn) {
            var isBookmarked = btn.getAttribute("data-bookmarked") === "true";
            var method = isBookmarked ? "DELETE" : "POST";
            var url = "/threads/" + threadId + "/bookmark";
            if (window.ManageAuth && window.ManageAuth.getToken && window.ManageAuth.getToken()) {
                window.ManageAuth.apiFetchWithAuth("/api/v1/forum" + url, { method: method })
                    .then(function() {
                        // Remove the thread from the list when unbookmarked
                        if (isBookmarked) {
                            var row = btn.closest(".forum-thread-row");
                            if (row) row.remove();
                            // Update pagination info
                            state.total--;
                            if (state.total === 0) {
                                if (content) content.hidden = true;
                                if (empty) empty.hidden = false;
                                if (pagination) pagination.hidden = true;
                            } else {
                                state.totalPages = state.perPage > 0 ? Math.ceil(state.total / state.perPage) : 0;
                                if (paginationInfo) paginationInfo.textContent = "Page " + state.page + " of " + (state.totalPages || 1) + " (" + state.total + " total)";
                                if (nextBtn) nextBtn.disabled = state.page >= state.totalPages;
                            }
                        }
                    })
                    .catch(function() {});
            }
        }

        function renderThreads(items, page, total, perPage) {
            if (loading) loading.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (!content) return;
            while (content.firstChild) content.removeChild(content.firstChild);
            items.forEach(function(t) {
                var row = document.createElement("div");
                row.className = "forum-thread-row";
                var link = document.createElement("a");
                link.href = "/forum/threads/" + encodeURIComponent(t.slug || "");
                link.className = "forum-thread-link";
                var title = document.createElement("span");
                title.className = "forum-thread-title";
                title.textContent = t.title || "Untitled";
                if (t.is_pinned) {
                    var pin = document.createElement("span");
                    pin.className = "forum-badge forum-badge-pinned";
                    pin.textContent = "Pinned";
                    link.appendChild(pin);
                }
                link.appendChild(title);
                // Tags badges
                if (t.tags && t.tags.length) {
                    t.tags.forEach(function(tag) {
                        var badge = document.createElement("span");
                        badge.className = "forum-badge forum-badge-tag";
                        badge.textContent = tag.label || tag.slug;
                        link.appendChild(badge);
                    });
                }
                var meta = document.createElement("span");
                meta.className = "forum-thread-meta muted";
                var parts = [];
                if (t.reply_count != null) parts.push(t.reply_count + " replies");
                if (t.last_post_at) parts.push(formatDate(t.last_post_at));
                meta.textContent = parts.join(" \u00b7 ");
                row.appendChild(link);
                // Bookmark button (should always be bookmarked, but keep button to unbookmark)
                var bmBtn = document.createElement("button");
                bmBtn.type = "button";
                bmBtn.className = "forum-bookmark-btn forum-bookmark-active";
                bmBtn.setAttribute("data-bookmarked", "true");
                bmBtn.textContent = "\u2605";
                bmBtn.title = "Remove bookmark";
                (function(tid, btn) {
                    btn.addEventListener("click", function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        toggleBookmark(tid, btn);
                    });
                })(t.id, bmBtn);
                row.appendChild(bmBtn);
                row.appendChild(meta);
                content.appendChild(row);
            });
            content.hidden = false;
            state.total = total;
            state.totalPages = perPage > 0 ? Math.ceil(total / perPage) : 0;
            if (pagination) {
                pagination.hidden = state.totalPages <= 1;
                if (paginationInfo) paginationInfo.textContent = "Page " + page + " of " + (state.totalPages || 1) + " (" + total + " total)";
                if (prevBtn) prevBtn.disabled = page <= 1;
                if (nextBtn) nextBtn.disabled = page >= state.totalPages;
            }
        }

        function fetchBookmarks(page) {
            return apiGet("bookmarks?page=" + page + "&limit=" + state.perPage);
        }

        showLoading(true);
        fetchBookmarks(1)
            .then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : items.length;
                var page = (data && typeof data.page === "number") ? data.page : 1;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                state.page = page;
                if (items.length === 0) {
                    if (loading) loading.hidden = true;
                    if (content) content.hidden = true;
                    if (empty) empty.hidden = false;
                } else renderThreads(items, page, total, perPage);
            })
            .catch(function(e) { showError(typeof e === "string" ? e : (e && e.message) || "Failed to load."); });

        if (prevBtn) prevBtn.addEventListener("click", function() {
            if (state.page <= 1) return;
            state.page--;
            showLoading(true);
            fetchBookmarks(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                renderThreads(items, page, total, perPage);
            }).catch(function(e) { showError(e && e.message); });
        });
        if (nextBtn) nextBtn.addEventListener("click", function() {
            if (state.page >= state.totalPages) return;
            state.page++;
            showLoading(true);
            fetchBookmarks(state.page).then(function(data) {
                var items = (data && data.items) ? data.items : [];
                var total = (data && typeof data.total === "number") ? data.total : 0;
                var page = (data && typeof data.page === "number") ? data.page : state.page;
                var perPage = (data && typeof data.per_page === "number") ? data.per_page : state.perPage;
                renderThreads(items, page, total, perPage);
            }).catch(function(e) { showError(e && e.message); });
        });
    }

    window.ForumApp = {
        initIndex: initIndex,
        initCategory: initCategory,
        initThread: initThread,
        initNotifications: initNotifications,
        initSavedThreads: initSavedThreads
    };
})();
