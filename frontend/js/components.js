/**
 * UI Components — Reusable constructors for dashboard elements.
 */

const Components = {
    /**
     * Agent activity icons by type and agent
     */
    agentIcons: {
        analyzer: '🔍',
        planner: '📋',
        fixer: '🔧',
        verifier: '✅'
    },

    eventIcons: {
        started: '▶️',
        thinking: '💭',
        tool_use: '⚙️',
        result: '✨',
        error: '❌'
    },

    /**
     * Create an activity feed item
     */
    createActivityItem(event) {
        const item = document.createElement('div');
        item.className = 'activity-item';

        const agentIcon = this.agentIcons[event.agent] || '🤖';
        const eventIcon = this.eventIcons[event.event_type] || '📌';
        const time = new Date(event.timestamp).toLocaleTimeString();

        item.innerHTML = `
            <div class="activity-icon ${event.agent}">
                ${agentIcon}
            </div>
            <div class="activity-body">
                <div class="activity-title">${eventIcon} ${this._escapeHtml(event.title)}</div>
                ${event.detail ? `<div class="activity-detail">${this._escapeHtml(event.detail)}</div>` : ''}
            </div>
            <div class="activity-time">${time}</div>
        `;

        return item;
    },

    /**
     * Create an issue card
     */
    createIssueCard(issue) {
        const card = document.createElement('div');
        card.className = `issue-card ${issue.severity}`;

        const fileName = issue.file_path.split('/').pop();
        card.innerHTML = `
            <div class="issue-header">
                <div class="issue-title">${this._escapeHtml(issue.title)}</div>
                <div class="issue-meta">
                    <span class="severity-badge ${issue.severity}">${issue.severity}</span>
                    <span class="category-badge">${issue.category}</span>
                </div>
            </div>
            <div class="issue-location">${fileName}:${issue.line_number}</div>
            <div class="issue-description">${this._escapeHtml(issue.description)}</div>
            ${issue.suggested_fix ? `<div class="issue-fix">${this._escapeHtml(issue.suggested_fix)}</div>` : ''}
        `;

        return card;
    },

    /**
     * Create a diff block
     */
    createDiffBlock(change) {
        const block = document.createElement('div');
        block.className = 'diff-block';

        const fileName = change.file_path.split('/').pop();
        const lines = change.diff ? change.diff.split('\n') : [];
        let additions = 0, deletions = 0;

        const diffHtml = lines.map(line => {
            if (line.startsWith('+') && !line.startsWith('+++')) {
                additions++;
                return `<span class="diff-line addition">${this._escapeHtml(line)}</span>`;
            } else if (line.startsWith('-') && !line.startsWith('---')) {
                deletions++;
                return `<span class="diff-line deletion">${this._escapeHtml(line)}</span>`;
            } else if (line.startsWith('@@')) {
                return `<span class="diff-line header">${this._escapeHtml(line)}</span>`;
            }
            return `<span class="diff-line">${this._escapeHtml(line)}</span>`;
        }).join('\n');

        block.innerHTML = `
            <div class="diff-header">
                <span class="diff-filename">📄 ${fileName}</span>
                <div class="diff-stats">
                    <span class="additions">+${additions}</span>
                    <span class="deletions">-${deletions}</span>
                </div>
            </div>
            <div class="diff-body">
                <pre>${diffHtml}</pre>
            </div>
        `;

        return block;
    },

    /**
     * Create a fix plan item
     */
    createPlanItem(action, index) {
        const item = document.createElement('div');
        item.className = 'plan-item';

        const fileName = action.file_path ? action.file_path.split('/').pop() : 'unknown';

        item.innerHTML = `
            <div class="plan-priority">${index + 1}</div>
            <div class="plan-body">
                <div class="plan-approach">${this._escapeHtml(action.approach)}</div>
                <div class="plan-file">${fileName} • Risk: ${action.risk_level || 'low'}</div>
                ${action.estimated_impact ? `<div class="plan-impact">→ ${this._escapeHtml(action.estimated_impact)}</div>` : ''}
            </div>
        `;

        return item;
    },

    /**
     * Create the full report view
     */
    createReport(result) {
        const container = document.createElement('div');

        // Stats cards
        const statsHtml = `
            <div class="report-stats">
                <div class="stat-card">
                    <div class="stat-value">${result.issues?.length || 0}</div>
                    <div class="stat-label">Issues Found</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${result.fix_result?.total_succeeded || 0}</div>
                    <div class="stat-label">Fixes Applied</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${result.verification?.tests_passed || 0}/${result.verification?.tests_total || 0}</div>
                    <div class="stat-label">Tests Passed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${result.retry_count || 0}</div>
                    <div class="stat-label">Retries</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${(result.total_duration || 0).toFixed(1)}s</div>
                    <div class="stat-label">Duration</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${result.verification?.passed ? '✅' : '⚠️'}</div>
                    <div class="stat-label">Verification</div>
                </div>
            </div>
        `;

        // Summary
        const summaryHtml = result.summary ? `
            <div class="report-section">
                <h3>📊 Pipeline Summary</h3>
                <pre style="font-family: var(--font-sans); font-size: 0.85rem; color: var(--text-secondary); white-space: pre-wrap; line-height: 1.8;">${this._escapeHtml(result.summary)}</pre>
            </div>
        ` : '';

        // Verification details
        const verifyHtml = result.verification ? `
            <div class="report-section">
                <h3>${result.verification.passed ? '✅' : '❌'} Verification Result</h3>
                <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.7;">
                    ${this._escapeHtml(result.verification.feedback || result.verification.details || 'No additional details.')}
                </p>
            </div>
        ` : '';

        container.innerHTML = statsHtml + summaryHtml + verifyHtml;
        return container;
    },

    /**
     * Escape HTML entities
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
