/**
 * World of Shadows – news list and detail
 * Uses FrontendConfig.getApiBaseUrl() and FrontendConfig.apiFetch() (main.js) for backend API.
 * List: GET /api/v1/news?q=&sort=&direction=&page=&limit=&category= → { items, total, page, per_page }.
 * Detail: GET /api/v1/news/<id> → single article object.
 */
(function() {
    function getApiBase() {
        var fc = window.FrontendConfig;
        return (fc && fc.getApiBaseUrl) ? fc.getApiBaseUrl() : '';
    }

    function formatDate(iso) {
        if (!iso) return '';
        try {
            var d = new Date(iso);
            return isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { dateStyle: 'medium' });
        } catch (e) {
            return '';
        }
    }

        function getCurrentLang() {
        var c = window.__FRONTEND_CONFIG__;
        return (c && c.currentLanguage) ? c.currentLanguage : 'de';
    }

    function buildListUrl(base, opts) {
        var params = new URLSearchParams();
        params.set('lang', getCurrentLang());
        if (opts.q) params.set('q', opts.q);
        if (opts.sort) params.set('sort', opts.sort);
        if (opts.direction) params.set('direction', opts.direction);
        params.set('page', String(opts.page || 1));
        params.set('limit', String(opts.limit || 20));
        if (opts.category) params.set('category', opts.category);
        var query = params.toString();
        return base + '/api/v1/news' + (query ? '?' + query : '');
    }

    function initList() {
        var container = document.getElementById('news-list');
        if (!container) return;
        var apiBase = getApiBase();

        var loading = document.getElementById('news-loading');
        var content = document.getElementById('news-list-content');
        var empty = document.getElementById('news-empty');
        var errEl = document.getElementById('news-error');
        var pagination = document.getElementById('news-pagination');
        var paginationInfo = document.getElementById('news-pagination-info');
        var prevBtn = document.getElementById('news-prev');
        var nextBtn = document.getElementById('news-next');
        var searchInput = document.getElementById('news-search');
        var categoryInput = document.getElementById('news-category');
        var sortSelect = document.getElementById('news-sort');
        var directionSelect = document.getElementById('news-direction');
        var applyBtn = document.getElementById('news-apply');

        var state = { page: 1, total: 0, perPage: 20, totalPages: 0 };

        function getParams() {
            return {
                q: searchInput ? searchInput.value.trim() : '',
                category: categoryInput ? categoryInput.value.trim() : '',
                sort: sortSelect ? sortSelect.value : 'published_at',
                direction: directionSelect ? directionSelect.value : 'desc',
                page: state.page,
                limit: state.perPage
            };
        }

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
            if (errEl) {
                errEl.textContent = msg || 'Failed to load news.';
                errEl.hidden = false;
            }
            if (pagination) pagination.hidden = true;
        }

        function showEmpty() {
            if (loading) loading.hidden = true;
            if (content) content.hidden = true;
            if (empty) empty.hidden = false;
            if (errEl) errEl.hidden = true;
            if (pagination) pagination.hidden = true;
        }

        function renderItem(item) {
            var link = document.createElement('a');
            link.href = '/news/' + item.id;
            link.className = 'news-item-link';
            var title = document.createElement('h3');
            title.className = 'news-item-title';
            title.textContent = item.title || 'Untitled';
            link.appendChild(title);
            if (item.summary) {
                var summary = document.createElement('p');
                summary.className = 'news-item-summary';
                summary.textContent = item.summary;
                link.appendChild(summary);
            }
            var meta = document.createElement('p');
            meta.className = 'news-item-meta';
            var parts = [];
            var pub = formatDate(item.published_at || item.created_at);
            if (pub) parts.push(pub);
            if (item.category) parts.push(item.category);
            if (item.author_name) parts.push(item.author_name);
            meta.textContent = parts.join(' · ');
            link.appendChild(meta);
            var wrap = document.createElement('div');
            wrap.className = 'news-item';
            wrap.appendChild(link);
            return wrap;
        }

        function showItems(items, page, total, perPage) {
            if (loading) loading.hidden = true;
            if (empty) empty.hidden = true;
            if (errEl) errEl.hidden = true;
            if (!content) return;
            content.innerHTML = '';
            items.forEach(function(item) {
                content.appendChild(renderItem(item));
            });
            content.hidden = false;

            state.total = total;
            state.totalPages = perPage > 0 ? Math.ceil(total / perPage) : 0;
            if (pagination) {
                pagination.hidden = state.totalPages <= 1;
                if (paginationInfo) {
                    paginationInfo.textContent = 'Page ' + page + ' of ' + (state.totalPages || 1) + ' (' + total + ' total)';
                }
                if (prevBtn) prevBtn.disabled = page <= 1;
                if (nextBtn) nextBtn.disabled = page >= state.totalPages;
            }
        }

        function fetchList() {
            var params = getParams();
            showLoading(true);
            var pathWithQuery = buildListUrl('', params);
            var apiFetchFn = window.FrontendConfig && window.FrontendConfig.apiFetch;
            var req = apiFetchFn
                ? apiFetchFn(pathWithQuery)
                : fetch((apiBase || '') + pathWithQuery, { method: 'GET', headers: { 'Accept': 'application/json' } })
                    .then(function(res) {
                        if (!res.ok) throw new Error('Could not load news.');
                        return res.json();
                    });
            req.then(function(data) {
                if (data === null || data === undefined) return;
                var items = data.items || [];
                var total = typeof data.total === 'number' ? data.total : items.length;
                var page = typeof data.page === 'number' ? data.page : 1;
                var perPage = typeof data.per_page === 'number' ? data.per_page : 20;
                if (items.length === 0) showEmpty();
                else showItems(items, page, total, perPage);
            }).catch(function(err) {
                showError(typeof err === 'string' ? err : 'Could not load news.');
            });
        }

        function onApply() {
            state.page = 1;
            fetchList();
        }

        function onPrev() {
            if (state.page <= 1) return;
            state.page -= 1;
            fetchList();
        }

        function onNext() {
            if (state.page >= state.totalPages) return;
            state.page += 1;
            fetchList();
        }

        if (applyBtn) applyBtn.addEventListener('click', onApply);
        if (prevBtn) prevBtn.addEventListener('click', onPrev);
        if (nextBtn) nextBtn.addEventListener('click', onNext);
        if (sortSelect) sortSelect.addEventListener('change', function() { state.page = 1; fetchList(); });
        if (directionSelect) directionSelect.addEventListener('change', function() { state.page = 1; fetchList(); });

        if (searchInput) {
            searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); onApply(); }
            });
        }
        if (categoryInput) {
            categoryInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); onApply(); }
            });
        }

        fetchList();
    }

    function loadDetail(id) {
        var container = document.getElementById('news-detail');
        var loading = document.getElementById('news-detail-loading');
        var content = document.getElementById('news-detail-content');
        var errEl = document.getElementById('news-detail-error');
        var apiBase = getApiBase();

        function showLoading(show) {
            if (loading) loading.hidden = !show;
            if (content) content.hidden = true;
            if (errEl) errEl.hidden = true;
        }
        function showError(msg) {
            if (loading) loading.hidden = true;
            if (content) content.hidden = true;
            if (errEl) {
                errEl.textContent = msg || 'Failed to load article.';
                errEl.hidden = false;
            }
        }
        function showArticle(article) {
            if (loading) loading.hidden = true;
            if (errEl) errEl.hidden = true;
            if (!content) return;
            document.title = (article.title || 'News') + ' – World of Shadows';
            var title = document.createElement('h1');
            title.textContent = article.title || 'Untitled';
            var meta = document.createElement('p');
            meta.className = 'meta';
            var parts = [];
            var pub = formatDate(article.published_at || article.created_at);
            if (pub) parts.push(pub);
            if (article.category) parts.push(article.category);
            if (article.author_name) parts.push(article.author_name);
            meta.textContent = parts.join(' · ');
            var body = document.createElement('div');
            body.className = 'body';
            body.textContent = article.content || article.body || '';
            content.innerHTML = '';
            content.appendChild(title);
            content.appendChild(meta);
            if (article.summary) {
                var summary = document.createElement('p');
                summary.className = 'summary';
                summary.textContent = article.summary;
                content.appendChild(summary);
            }

            // Discussion entry point
            if (article.discussion_thread_slug) {
                var discuss = document.createElement('p');
                discuss.className = 'news-discussion-entry';
                var discussLink = document.createElement('a');
                discussLink.href = '/forum/threads/' + encodeURIComponent(article.discussion_thread_slug);
                discussLink.textContent = 'Discuss this article in the forum';
                discuss.appendChild(discussLink);
                content.appendChild(discuss);
            }

            // Related threads block (safe, public subset)
            if (article.related_threads && article.related_threads.length) {
                var relatedWrap = document.createElement('section');
                relatedWrap.className = 'news-related-threads';
                var heading = document.createElement('h2');
                heading.textContent = 'Related discussions';
                relatedWrap.appendChild(heading);
                var list = document.createElement('ul');
                list.className = 'news-related-threads-list';
                article.related_threads.forEach(function(t) {
                    if (!t || !t.slug) return;
                    var li = document.createElement('li');
                    var a = document.createElement('a');
                    a.href = '/forum/threads/' + encodeURIComponent(t.slug);
                    a.textContent = t.title || 'Forum thread';
                    li.appendChild(a);
                    if (t.category && t.category.slug) {
                        var catSpan = document.createElement('span');
                        catSpan.className = 'news-related-thread-category';
                        catSpan.textContent = ' (' + t.category.slug + ')';
                        li.appendChild(catSpan);
                    }
                    list.appendChild(li);
                });
                relatedWrap.appendChild(list);
                content.appendChild(relatedWrap);
            }

            // Suggested threads block (auto-generated, contextual)
            if (article.suggested_threads && article.suggested_threads.length) {
                var suggestedWrap = document.createElement('section');
                suggestedWrap.className = 'news-suggested-threads';
                var suggestedHeading = document.createElement('h3');
                suggestedHeading.textContent = 'Suggested discussions';
                suggestedWrap.appendChild(suggestedHeading);
                var suggestedList = document.createElement('ul');
                suggestedList.className = 'news-suggested-threads-list';
                article.suggested_threads.forEach(function(t) {
                    if (!t || !t.slug) return;
                    var li = document.createElement('li');
                    var a = document.createElement('a');
                    a.href = '/forum/threads/' + encodeURIComponent(t.slug);
                    a.textContent = t.title || 'Forum thread';
                    li.appendChild(a);
                    if (t.category && t.category.slug) {
                        var catSpan = document.createElement('span');
                        catSpan.className = 'news-suggested-thread-category';
                        catSpan.textContent = ' (' + t.category.slug + ')';
                        li.appendChild(catSpan);
                    }
                    suggestedList.appendChild(li);
                });
                suggestedWrap.appendChild(suggestedList);
                content.appendChild(suggestedWrap);
            }

            content.appendChild(body);
            if (article.discussion_thread_slug) {
                var discussWrap = document.createElement('p');
                discussWrap.className = 'news-detail-discussion';
                var discussLink = document.createElement('a');
                discussLink.href = '/forum/threads/' + encodeURIComponent(article.discussion_thread_slug);
                discussLink.textContent = 'Discuss this article';
                discussWrap.appendChild(discussLink);
                content.appendChild(discussWrap);
            }
            content.hidden = false;
        }

        showLoading(true);
        var path = '/api/v1/news/' + id + '?lang=' + encodeURIComponent(getCurrentLang());
        var apiFetchFn = window.FrontendConfig && window.FrontendConfig.apiFetch;
        var req = apiFetchFn
            ? apiFetchFn(path)
            : fetch((apiBase || '') + path, { method: 'GET', headers: { 'Accept': 'application/json' } })
                .then(function(res) {
                    if (res.status === 404) throw new Error('Article not found.');
                    if (!res.ok) throw new Error('Could not load article.');
                    return res.json();
                });
        req.then(function(data) {
            if (data) showArticle(data);
        }).catch(function(err) {
            showError(typeof err === 'string' ? err : (err && err.message) || 'Could not load article.');
        });
    }

    window.NewsApp = { initList: initList, loadDetail: loadDetail };
})();
