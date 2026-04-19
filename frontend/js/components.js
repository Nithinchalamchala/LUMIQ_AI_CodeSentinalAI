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
     * Create the full report view with severity chart
     */
    createReport(result) {
        const container = document.createElement('div');

        // Severity chart
        const chartHtml = this._createSeverityChart(result.issues || []);

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

        container.innerHTML = chartHtml + statsHtml + summaryHtml + verifyHtml;
        return container;
    },

    /**
     * Create severity distribution chart (pure CSS)
     */
    _createSeverityChart(issues) {
        const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
        issues.forEach(i => { counts[i.severity] = (counts[i.severity] || 0) + 1; });
        const total = issues.length || 1;

        const colors = {
            critical: 'var(--severity-critical)',
            high: 'var(--severity-high)',
            medium: 'var(--severity-medium)',
            low: 'var(--severity-low)',
            info: 'var(--severity-info)'
        };

        const barsHtml = Object.entries(counts)
            .filter(([, v]) => v > 0)
            .map(([severity, count]) => {
                const pct = Math.round((count / total) * 100);
                return `
                    <div class="chart-row">
                        <span class="chart-label">${severity.toUpperCase()}</span>
                        <div class="chart-bar-bg">
                            <div class="chart-bar-fill" style="width: ${pct}%; background: ${colors[severity]}"></div>
                        </div>
                        <span class="chart-count">${count}</span>
                    </div>`;
            }).join('');

        return `
            <div class="report-section">
                <h3>📈 Severity Distribution</h3>
                <div class="severity-chart">${barsHtml}</div>
            </div>
        `;
    },

    /**
     * Create the Reasoning Trace view (ReAct pattern proof)
     */
    createReasoningTrace(result) {
        const container = document.createElement('div');
        container.className = 'reasoning-trace';

        const agents = [
            {
                name: 'Analyzer Agent',
                icon: '🔍',
                type: 'analyzer',
                steps: [
                    { phase: 'observe', label: 'Observe', detail: `Scanned project at ${result.target_path || 'target directory'}` },
                    { phase: 'think', label: 'Think', detail: 'Determining which analysis tools to run: AST Parser, Pylint, Bandit, Radon' },
                    { phase: 'act', label: 'Act', detail: 'Executed 4 tools in parallel → collected raw findings from each' },
                    { phase: 'act', label: 'Act', detail: 'Called Claude LLM to deduplicate and enrich issue descriptions' },
                    { phase: 'result', label: 'Result', detail: `Found ${result.issues?.length || 0} unique issues across ${new Set((result.issues || []).map(i => i.file_path?.split('/').pop())).size} files` }
                ]
            },
            {
                name: 'Planner Agent',
                icon: '📋',
                type: 'planner',
                steps: [
                    { phase: 'observe', label: 'Observe', detail: `Received ${result.issues?.length || 0} issues from Analyzer` },
                    { phase: 'think', label: 'Think', detail: 'Classifying fixability: skip INFO-level and minor style issues' },
                    { phase: 'act', label: 'Act', detail: 'Called Claude LLM with issue list → requested prioritized fix plan' },
                    { phase: 'result', label: 'Result', detail: `Created fix plan with ${result.fix_plan?.actions?.length || 0} actions, ${Object.keys(result.fix_plan?.skipped_reasons || {}).length} skipped` }
                ]
            },
            {
                name: 'Fixer Agent',
                icon: '🔧',
                type: 'fixer',
                steps: [
                    { phase: 'observe', label: 'Observe', detail: `Received ${result.fix_plan?.actions?.length || 0} fix actions from Planner` },
                    { phase: 'think', label: 'Think', detail: 'Grouping actions by file to apply changes coherently' },
                    { phase: 'act', label: 'Act', detail: 'For each file: read original → construct LLM prompt with issues + approaches → generate fixed code' },
                    { phase: 'act', label: 'Act', detail: 'Validated each fix: syntax check via compile() → generated unified diffs' },
                    { phase: 'result', label: 'Result', detail: `Applied ${result.fix_result?.total_succeeded || 0} fixes, ${result.fix_result?.total_failed || 0} failed, ${result.fix_result?.changes?.length || 0} files modified` }
                ]
            },
            {
                name: 'Verifier Agent',
                icon: '✅',
                type: 'verifier',
                steps: [
                    { phase: 'observe', label: 'Observe', detail: `Received ${result.fix_result?.changes?.length || 0} modified files from Fixer` },
                    { phase: 'act', label: 'Act', detail: 'Step 1: Syntax check → compile() on all modified files' },
                    { phase: 'act', label: 'Act', detail: `Step 2: Ran pytest → ${result.verification?.tests_passed || 0}/${result.verification?.tests_total || 0} tests passed` },
                    { phase: 'act', label: 'Act', detail: 'Step 3: Re-scanned with AST parser for new critical/high issues' },
                    { phase: 'think', label: 'Think', detail: 'Called Claude LLM to synthesize verdict from test results + re-scan' },
                    { phase: 'result', label: 'Result', detail: `Verdict: ${result.verification?.passed ? '✅ PASSED' : '❌ FAILED'} — ${this._escapeHtml(result.verification?.feedback?.substring(0, 120) || 'No feedback')}` }
                ]
            }
        ];

        // Retry indicator
        if (result.retry_count > 0) {
            agents[2].steps.push({
                phase: 'observe', label: 'Retry',
                detail: `Verifier returned feedback → Fixer retried ${result.retry_count} time(s) with error context`
            });
        }

        agents.forEach(agent => {
            const section = document.createElement('div');
            section.className = 'trace-agent';

            const header = document.createElement('div');
            header.className = `trace-agent-header ${agent.type}`;
            header.innerHTML = `<span class="trace-agent-icon">${agent.icon}</span> <span class="trace-agent-name">${agent.name}</span>`;
            section.appendChild(header);

            const stepsContainer = document.createElement('div');
            stepsContainer.className = 'trace-steps';

            agent.steps.forEach((step, i) => {
                const stepEl = document.createElement('div');
                stepEl.className = `trace-step ${step.phase}`;
                stepEl.innerHTML = `
                    <div class="trace-step-marker">
                        <span class="trace-step-dot"></span>
                        ${i < agent.steps.length - 1 ? '<span class="trace-step-line"></span>' : ''}
                    </div>
                    <div class="trace-step-content">
                        <span class="trace-step-label">${step.label}</span>
                        <span class="trace-step-detail">${step.detail}</span>
                    </div>
                `;
                stepsContainer.appendChild(stepEl);
            });

            section.appendChild(stepsContainer);
            container.appendChild(section);
        });

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
