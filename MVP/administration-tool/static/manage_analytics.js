/**
 * Analytics Dashboard
 * Handles admin analytics dashboard interaction, API calls, and chart rendering
 */

const AnalyticsDashboard = {
    chart: null,
    currentRange: '30d',
    dateFrom: null,
    dateTo: null,

    /**
     * Initialize the dashboard
     */
    init() {
        this.setupEventListeners();
        this.setDefaultDates();
        this.loadAllAnalytics();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Preset date range buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.applyPresetRange(e.target.dataset.range);
            });
        });

        // Apply and reset buttons
        document.getElementById('apply_filters').addEventListener('click', () => {
            this.applyCustomRange();
        });

        document.getElementById('reset_filters').addEventListener('click', () => {
            this.resetFilters();
        });

        // Metric tabs
        document.querySelectorAll('.metric-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchMetric(e.target.dataset.metric);
            });
        });
    },

    /**
     * Set default dates (last 30 days)
     */
    setDefaultDates() {
        const today = new Date();
        const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

        document.getElementById('date_to').value = this.formatDate(today);
        document.getElementById('date_from').value = this.formatDate(thirtyDaysAgo);
    },

    /**
     * Format date as YYYY-MM-DD
     */
    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    },

    /**
     * Apply preset date range
     */
    applyPresetRange(range) {
        this.currentRange = range;
        const today = new Date();
        let daysAgo = 30;

        if (range === '7d') daysAgo = 7;
        else if (range === '30d') daysAgo = 30;
        else if (range === '90d') daysAgo = 90;

        const from = new Date(today.getTime() - daysAgo * 24 * 60 * 60 * 1000);

        document.getElementById('date_from').value = this.formatDate(from);
        document.getElementById('date_to').value = this.formatDate(today);

        this.loadAllAnalytics();
    },

    /**
     * Apply custom date range
     */
    applyCustomRange() {
        this.dateFrom = document.getElementById('date_from').value;
        this.dateTo = document.getElementById('date_to').value;

        if (!this.dateFrom || !this.dateTo) {
            this.showError('Please select both start and end dates');
            return;
        }

        if (this.dateFrom > this.dateTo) {
            this.showError('Start date must be before end date');
            return;
        }

        this.loadAllAnalytics();
    },

    /**
     * Reset filters to default
     */
    resetFilters() {
        this.currentRange = '30d';
        this.setDefaultDates();
        this.loadAllAnalytics();
    },

    /**
     * Get date range query parameters
     */
    getDateRangeParams() {
        const params = {};
        const from = document.getElementById('date_from').value;
        const to = document.getElementById('date_to').value;

        if (from) params.date_from = from;
        if (to) params.date_to = to;

        return params;
    },

    /**
     * Load all analytics data
     */
    loadAllAnalytics() {
        this.showLoading(true);
        this.clearError();

        Promise.all([
            this.loadSummary(),
            this.loadTimeline(),
            this.loadUsers(),
            this.loadContent(),
            this.loadModeration()
        ]).then(() => {
            this.showLoading(false);
        }).catch((error) => {
            this.showLoading(false);
            this.showError('Failed to load analytics: ' + error.message);
        });
    },

    /**
     * Load summary metrics
     */
    loadSummary() {
        const params = this.getDateRangeParams();
        return FrontendConfig.apiFetch('/api/v1/admin/analytics/summary', {
            params
        }).then(data => {
            const summary = data.summary || {};
            const users = summary.users || {};
            const content = summary.content || {};
            const reports = summary.reports || {};

            document.getElementById('active_now').textContent = users.active_now || 0;
            document.getElementById('total_users').textContent = users.total || 0;
            document.getElementById('threads_created').textContent = content.threads_created || 0;
            document.getElementById('posts_created').textContent = content.posts_created || 0;
            document.getElementById('open_reports').textContent = reports.open || 0;
        });
    },

    /**
     * Load timeline data and render chart
     */
    loadTimeline() {
        const params = this.getDateRangeParams();
        return FrontendConfig.apiFetch('/api/v1/admin/analytics/timeline', {
            params
        }).then(data => {
            this.renderTimelineChart(data.timeline);
        });
    },

    /**
     * Render timeline chart using Chart.js
     */
    renderTimelineChart(timeline) {
        const ctx = document.getElementById('timeline-chart');
        if (!ctx) return;

        const dates = timeline.dates || [];
        const threads = timeline.threads || [];
        const posts = timeline.posts || [];
        const reports = timeline.reports || [];
        const actions = timeline.actions || [];

        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Threads',
                        data: threads,
                        borderColor: '#0066cc',
                        backgroundColor: 'rgba(0, 102, 204, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Posts',
                        data: posts,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Reports',
                        data: reports,
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Moderation Actions',
                        data: actions,
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    },

    /**
     * Load user analytics
     */
    loadUsers() {
        const params = { limit: 10, ...this.getDateRangeParams() };
        return FrontendConfig.apiFetch('/api/v1/admin/analytics/users', {
            params
        }).then(data => {
            this.renderContributorsTable(data.top_contributors || []);
            this.renderRoleDistribution(data.role_distribution || {});
        });
    },

    /**
     * Render contributors table
     */
    renderContributorsTable(contributors) {
        const tbody = document.getElementById('contributors-table-body');
        tbody.innerHTML = '';

        if (contributors.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No contributors yet</td></tr>';
            return;
        }

        contributors.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.escapeHtml(user.username)}</td>
                <td>${this.escapeHtml(String(user.threads))}</td>
                <td>${this.escapeHtml(String(user.posts))}</td>
                <td><strong>${this.escapeHtml(String(user.total_contributions))}</strong></td>
            `;
            tbody.appendChild(row);
        });
    },

    /**
     * Render role distribution
     */
    renderRoleDistribution(distribution) {
        const container = document.getElementById('role-dist-container');
        container.innerHTML = '';

        Object.entries(distribution).forEach(([role, count]) => {
            const div = document.createElement('div');
            div.className = 'role-dist-item';
            div.innerHTML = `
                <div class="role-name">${this.escapeHtml(role)}</div>
                <div class="role-count">${this.escapeHtml(String(count))}</div>
            `;
            container.appendChild(div);
        });
    },

    /**
     * Load content analytics
     */
    loadContent() {
        const params = { limit: 10, ...this.getDateRangeParams() };
        return FrontendConfig.apiFetch('/api/v1/admin/analytics/content', {
            params
        }).then(data => {
            this.renderTagsTable(data.popular_tags || []);
            this.renderThreadsTable(data.trending_threads || []);
            this.renderFreshness(data.content_freshness || {});
        });
    },

    /**
     * Render tags table
     */
    renderTagsTable(tags) {
        const tbody = document.getElementById('tags-table-body');
        tbody.innerHTML = '';

        if (tags.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="no-data">No tags yet</td></tr>';
            return;
        }

        tags.forEach(tag => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${this.escapeHtml(tag.label)}</strong></td>
                <td>${this.escapeHtml(String(tag.thread_count))}</td>
            `;
            tbody.appendChild(row);
        });
    },

    /**
     * Render threads table
     */
    renderThreadsTable(threads) {
        const tbody = document.getElementById('threads-table-body');
        tbody.innerHTML = '';

        if (threads.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No trending threads</td></tr>';
            return;
        }

        threads.forEach(thread => {
            const lastActivity = thread.last_activity ? new Date(thread.last_activity).toLocaleDateString() : 'N/A';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${this.escapeHtml(thread.title)}</strong></td>
                <td>${this.escapeHtml(thread.author || 'Unknown')}</td>
                <td>${this.escapeHtml(String(thread.replies))}</td>
                <td>${this.escapeHtml(String(thread.views))}</td>
                <td>${this.escapeHtml(lastActivity)}</td>
            `;
            tbody.appendChild(row);
        });
    },

    /**
     * Render content freshness distribution
     */
    renderFreshness(freshness) {
        const newCount = freshness.new?.count || 0;
        const recentCount = freshness.recent?.count || 0;
        const oldCount = freshness.old?.count || 0;
        const total = newCount + recentCount + oldCount;

        document.getElementById('freshness-new-value').textContent = newCount;
        document.getElementById('freshness-recent-value').textContent = recentCount;
        document.getElementById('freshness-old-value').textContent = oldCount;

        if (total > 0) {
            const newPercent = (newCount / total) * 100;
            const recentPercent = (recentCount / total) * 100;
            const oldPercent = (oldCount / total) * 100;

            document.getElementById('freshness-new').style.width = newPercent + '%';
            document.getElementById('freshness-recent').style.width = recentPercent + '%';
            document.getElementById('freshness-old').style.width = oldPercent + '%';
        }
    },

    /**
     * Load moderation analytics
     */
    loadModeration() {
        const params = this.getDateRangeParams();
        return FrontendConfig.apiFetch('/api/v1/admin/analytics/moderation', {
            params
        }).then(data => {
            this.renderQueueStatus(data.queue_status || {});
            this.renderModActions(data.moderation_actions || {});

            const avgDays = data.average_resolution_days || 0;
            document.getElementById('avg_resolution').textContent = avgDays.toFixed(1);
        });
    },

    /**
     * Render queue status table
     */
    renderQueueStatus(queueStatus) {
        const tbody = document.getElementById('queue-status-body');
        tbody.innerHTML = '';

        Object.entries(queueStatus).forEach(([status, count]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${this.escapeHtml(status)}</strong></td>
                <td>${this.escapeHtml(String(count))}</td>
            `;
            tbody.appendChild(row);
        });

        if (Object.keys(queueStatus).length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="no-data">No reports</td></tr>';
        }
    },

    /**
     * Render moderation actions table
     */
    renderModActions(actions) {
        const tbody = document.getElementById('actions-body');
        tbody.innerHTML = '';

        Object.entries(actions).forEach(([action, count]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${this.escapeHtml(action)}</strong></td>
                <td>${this.escapeHtml(String(count))}</td>
            `;
            tbody.appendChild(row);
        });

        if (Object.keys(actions).length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="no-data">No moderation actions</td></tr>';
        }
    },

    /**
     * Switch metric view
     */
    switchMetric(metric) {
        // Update active tab
        document.querySelectorAll('.metric-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-metric="${metric}"]`).classList.add('active');

        // Update active view
        document.querySelectorAll('.metric-view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${metric}-view`).classList.add('active');
    },

    /**
     * Show loading indicator
     */
    showLoading(show) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.style.display = 'inline-flex';
        } else {
            loading.style.display = 'none';
        }
    },

    /**
     * Show error message
     */
    showError(message) {
        const errorDiv = document.getElementById('error_message');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    },

    /**
     * Clear error message
     */
    clearError() {
        const errorDiv = document.getElementById('error_message');
        errorDiv.style.display = 'none';
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }
};

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    AnalyticsDashboard.init();
});
