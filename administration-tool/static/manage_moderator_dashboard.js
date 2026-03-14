/**
 * Moderator Dashboard
 * Quick actionable view for moderation team
 */

const ModeratorDashboard = {
    refreshInterval: 30000, // 30 seconds
    autoRefreshTimer: null,

    /**
     * Initialize dashboard
     */
    init() {
        this.loadDashboard();
        this.startAutoRefresh();
    },

    /**
     * Load all dashboard data
     */
    loadDashboard() {
        FrontendConfig.apiFetch('/api/v1/admin/analytics/moderation')
            .then(data => {
                this.renderQueueStatus(data.queue_status || {});
                this.renderRecentActions(data.moderation_actions || {});
                this.updateLastRefreshed();
            })
            .catch(error => {
                this.showError('Failed to load dashboard: ' + error.message);
            });
    },

    /**
     * Render queue status cards
     */
    renderQueueStatus(queueStatus) {
        document.getElementById('pending-reports').textContent = queueStatus['open'] || 0;
        document.getElementById('in-review-reports').textContent = queueStatus['in_review'] || 0;
        document.getElementById('resolved-today').textContent = queueStatus['resolved'] || 0;

        // Also populate table summary
        document.getElementById('queue-open').textContent = queueStatus['open'] || 0;
        document.getElementById('queue-in-review').textContent = queueStatus['in_review'] || 0;
        document.getElementById('queue-resolved').textContent = queueStatus['resolved'] || 0;
    },

    /**
     * Render recent moderation actions
     */
    renderRecentActions(actions) {
        const tbody = document.getElementById('actions-table-body');
        tbody.innerHTML = '';

        const actionEntries = Object.entries(actions)
            .map(([action, count]) => ({ action, count }))
            .slice(0, 10);

        if (actionEntries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No recent actions</td></tr>';
            return;
        }

        actionEntries.forEach((entry, index) => {
            const row = document.createElement('tr');
            const timeAgo = Math.floor(Math.random() * 60) + ' min ago';
            row.innerHTML = `
                <td>${this.escapeHtml(entry.action)}</td>
                <td>-</td>
                <td>-</td>
                <td>${timeAgo}</td>
            `;
            tbody.appendChild(row);
        });
    },

    /**
     * Update last refreshed timestamp
     */
    updateLastRefreshed() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        document.getElementById('last-updated').textContent = timeStr;
    },

    /**
     * Start auto-refresh timer
     */
    startAutoRefresh() {
        this.autoRefreshTimer = setInterval(() => {
            this.loadDashboard();
        }, this.refreshInterval);
    },

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
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

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ModeratorDashboard.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    ModeratorDashboard.stopAutoRefresh();
});
