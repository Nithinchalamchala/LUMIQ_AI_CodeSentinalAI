/**
 * Main application controller for CodeSentinel AI dashboard.
 */

// ── State ──────────────────────────────────────────────
let currentJobId = null;
let timerInterval = null;
let startTime = null;
let currentTab = 'demo';
let pipelineResult = null;

// ── Input Tab Switching ───────────────────────────────
document.querySelectorAll('.input-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        currentTab = tabName;

        // Update tab active state
        document.querySelectorAll('.input-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Update pane visibility
        document.querySelectorAll('.input-pane').forEach(p => p.classList.remove('active'));
        document.getElementById(`pane${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`).classList.add('active');
    });
});

// ── Start Review ──────────────────────────────────────
async function startReview() {
    const btn = document.getElementById('startBtn');
    if (btn.classList.contains('loading')) return;

    // Build request body
    let body = {};
    if (currentTab === 'demo') {
        body = { demo: true };
    } else if (currentTab === 'path') {
        const path = document.getElementById('pathInput').value.trim();
        if (!path) {
            alert('Please enter a project path');
            return;
        }
        body = { target_path: path };
    } else if (currentTab === 'url') {
        const url = document.getElementById('urlInput').value.trim();
        if (!url) {
            alert('Please enter a Git URL');
            return;
        }
        body = { repo_url: url };
    }

    // Show loading state
    btn.classList.add('loading');
    updateGlobalStatus('running', 'Running');

    // Show panels
    document.getElementById('pipelinePanel').style.display = '';
    document.getElementById('activityPanel').style.display = '';
    document.getElementById('resultsPanel').style.display = '';

    // Reset state
    resetPipeline();
    startTimer();

    try {
        const response = await fetch('/api/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        currentJobId = data.job_id;

        // Connect WebSocket
        setupWebSocket(currentJobId);

        // Poll for results as fallback
        pollForResults(currentJobId);

    } catch (error) {
        console.error('Failed to start review:', error);
        btn.classList.remove('loading');
        updateGlobalStatus('error', 'Error');
        addActivityItem({
            agent: 'analyzer',
            event_type: 'error',
            title: 'Failed to start review',
            detail: error.message,
            timestamp: new Date().toISOString()
        });
    }
}

// ── WebSocket Setup ───────────────────────────────────
function setupWebSocket(jobId) {
    agentWS.on('agent_event', (event) => {
        addActivityItem(event);
        updatePipelineStep(event);
    });

    agentWS.on('status_update', (data) => {
        handleStatusUpdate(data);
    });

    agentWS.connect(jobId);
}

// ── Pipeline Step Updates ─────────────────────────────
function updatePipelineStep(event) {
    const agent = event.agent;
    const step = document.getElementById(`step-${agent}`);
    if (!step) return;

    if (event.event_type === 'started') {
        // Mark all previous steps as completed
        const agents = ['analyzer', 'planner', 'fixer', 'verifier'];
        const currentIndex = agents.indexOf(agent);
        agents.forEach((a, i) => {
            const s = document.getElementById(`step-${a}`);
            if (i < currentIndex) {
                s.className = 'pipeline-step completed';
                s.querySelector('.step-badge').textContent = 'Done';
            } else if (i === currentIndex) {
                s.className = 'pipeline-step active';
                s.querySelector('.step-badge').textContent = 'Running';
            }
        });
    }

    // Update step description with latest event
    if (step.classList.contains('active')) {
        step.querySelector('.step-desc').textContent = event.title.substring(0, 40);
    }
}

function handleStatusUpdate(data) {
    const status = data.status;

    if (status === 'completed' || status === 'failed') {
        stopTimer();
        const btn = document.getElementById('startBtn');
        btn.classList.remove('loading');

        if (status === 'completed') {
            updateGlobalStatus('ready', 'Completed');
            // Mark all steps as completed
            document.querySelectorAll('.pipeline-step').forEach(s => {
                s.className = 'pipeline-step completed';
                s.querySelector('.step-badge').textContent = 'Done';
            });
        } else {
            updateGlobalStatus('error', 'Failed');
        }

        // Load full results
        if (data.result) {
            pipelineResult = data.result;
            renderResults(data.result);
        } else if (currentJobId) {
            fetchResults(currentJobId);
        }
    }
}

// ── Polling Fallback ──────────────────────────────────
function pollForResults(jobId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${jobId}`);
            const data = await response.json();

            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(interval);
                handleStatusUpdate({ status: data.status });
            }
        } catch (e) {
            console.warn('Poll error:', e);
        }
    }, 2000);

    // Stop polling after 5 minutes
    setTimeout(() => clearInterval(interval), 300000);
}

async function fetchResults(jobId) {
    try {
        const response = await fetch(`/api/report/${jobId}`);
        const result = await response.json();
        pipelineResult = result;
        renderResults(result);
    } catch (e) {
        console.error('Failed to fetch results:', e);
    }
}

// ── Render Results ────────────────────────────────────
function renderResults(result) {
    // Issues
    const issuesList = document.getElementById('issuesList');
    issuesList.innerHTML = '';
    const issues = result.issues || [];
    document.getElementById('issueCount').textContent = issues.length;

    if (issues.length === 0) {
        issuesList.innerHTML = '<div class="activity-empty">No issues found — code is clean! 🎉</div>';
    } else {
        issues.forEach(issue => {
            issuesList.appendChild(Components.createIssueCard(issue));
        });
    }

    // Fix Plan
    const planContent = document.getElementById('planContent');
    planContent.innerHTML = '';
    if (result.fix_plan && result.fix_plan.actions) {
        result.fix_plan.actions.forEach((action, i) => {
            planContent.appendChild(Components.createPlanItem(action, i));
        });
        if (result.fix_plan.summary) {
            const summary = document.createElement('p');
            summary.style.cssText = 'color: var(--text-secondary); font-size: 0.8rem; margin-top: 16px;';
            summary.textContent = result.fix_plan.summary;
            planContent.appendChild(summary);
        }
    } else {
        planContent.innerHTML = '<div class="activity-empty">No fix plan available.</div>';
    }

    // Diffs
    const diffsContent = document.getElementById('diffsContent');
    diffsContent.innerHTML = '';
    if (result.fix_result && result.fix_result.changes) {
        result.fix_result.changes.forEach(change => {
            if (change.diff) {
                diffsContent.appendChild(Components.createDiffBlock(change));
            }
        });
        if (diffsContent.children.length === 0) {
            diffsContent.innerHTML = '<div class="activity-empty">No diffs generated.</div>';
        }
    } else {
        diffsContent.innerHTML = '<div class="activity-empty">No code changes applied.</div>';
    }

    // Report
    const reportContent = document.getElementById('reportContent');
    reportContent.innerHTML = '';
    reportContent.appendChild(Components.createReport(result));
}

// ── Activity Feed ─────────────────────────────────────
function addActivityItem(event) {
    const feed = document.getElementById('activityFeed');

    // Remove empty state
    const empty = feed.querySelector('.activity-empty');
    if (empty) empty.remove();

    const item = Components.createActivityItem(event);
    feed.appendChild(item);

    // Auto-scroll to bottom
    feed.scrollTop = feed.scrollHeight;
}

function clearActivityFeed() {
    const feed = document.getElementById('activityFeed');
    feed.innerHTML = '<div class="activity-empty"><span>Feed cleared.</span></div>';
}

// ── Result Tab Switching ──────────────────────────────
function switchResultTab(tabName) {
    document.querySelectorAll('.result-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.result === tabName);
    });

    document.getElementById('resultIssues').classList.toggle('active', tabName === 'issues');
    document.getElementById('resultPlan').classList.toggle('active', tabName === 'plan');
    document.getElementById('resultDiffs').classList.toggle('active', tabName === 'diffs');
    document.getElementById('resultReport').classList.toggle('active', tabName === 'report');
}

// ── Timer ─────────────────────────────────────────────
function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(() => {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        document.getElementById('timer').textContent = `${elapsed}s`;
    }, 100);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// ── Status Badge ──────────────────────────────────────
function updateGlobalStatus(state, text) {
    const badge = document.getElementById('globalStatus');
    badge.className = `status-badge ${state}`;
    badge.querySelector('.status-text').textContent = text;
}

// ── Reset ─────────────────────────────────────────────
function resetPipeline() {
    // Reset pipeline steps
    document.querySelectorAll('.pipeline-step').forEach(s => {
        s.className = 'pipeline-step';
        s.querySelector('.step-badge').textContent = 'Pending';
        s.querySelector('.step-desc').textContent = s.querySelector('.step-desc').textContent;
    });

    // Reset activity feed
    document.getElementById('activityFeed').innerHTML =
        '<div class="activity-empty"><span>Waiting for agents to start...</span></div>';

    // Reset results
    document.getElementById('issuesList').innerHTML = '';
    document.getElementById('planContent').innerHTML = '';
    document.getElementById('diffsContent').innerHTML = '';
    document.getElementById('reportContent').innerHTML = '';
    document.getElementById('issueCount').textContent = '0';

    // Reset retry
    document.getElementById('retryBadge').style.display = 'none';

    // Disconnect previous WebSocket
    agentWS.disconnect();
    pipelineResult = null;
}

// ── Smooth Scroll on Load ─────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Animate header on scroll
    const header = document.getElementById('header');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.style.boxShadow = 'var(--shadow-md)';
        } else {
            header.style.boxShadow = 'none';
        }
    });
});
