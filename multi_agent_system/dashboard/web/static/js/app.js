/**
 * PRAXIS-SENATE Dashboard JavaScript - Enhanced with Toast, Real-time Updates, and UI Polish
 */

// State
let ws = null;
let tasks = [];
let agents = [];
let events = [];
let critiques = [];
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Role editor state
let currentRoleFilename = null;
let originalRoleContent = null;

// Toast notifications
const toastContainer = document.getElementById('toastContainer');

// API Base URL
const API_BASE = window.location.origin;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    loadInitialData();
    setupEventListeners();
    setupTaskPolling(); // Fallback polling
});

// ==================== TOAST SYSTEM ====================
function showToast(type, title, message, duration = 4000) {
    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ',
        warning: '⚠'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || 'ℹ'}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="dismissToast(this.parentElement)">&times;</button>
    `;

    toastContainer.appendChild(toast);

    // Auto dismiss
    if (duration > 0) {
        setTimeout(() => {
            dismissToast(toast);
        }, duration);
    }

    return toast;
}

function dismissToast(toast) {
    if (!toast || !toast.parentElement) return;
    toast.classList.add('toast-out');
    setTimeout(() => {
        if (toast.parentElement) {
            toast.parentElement.removeChild(toast);
        }
    }, 300);
}

// ==================== SIDEBAR ====================
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const dashboard = document.querySelector('.dashboard');
    sidebar.classList.toggle('open');
    dashboard.classList.toggle('sidebar-open');
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const dashboard = document.querySelector('.dashboard');
    sidebar.classList.remove('open');
    dashboard.classList.remove('sidebar-open');
}

// ==================== COLLAPSIBLE PANELS ====================
function togglePanel(panelName) {
    const header = document.getElementById(`${panelName}Accordion`);
    const content = document.getElementById(`${panelName}Content`);

    if (header && content) {
        header.classList.toggle('collapsed');
        content.classList.toggle('collapsed');
    }
}

// ==================== WEBSOCKET ====================
function initWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/events/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            updateSystemStatus('connected');
            reconnectAttempts = 0;
            ws.send('subscribe:tasks');
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateSystemStatus('disconnected');
            handleReconnect();
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateSystemStatus('error');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleEvent(data);
                handleTaskEvent(data);
            } catch (e) {
                if (event.data === 'pong') return;
                console.error('Failed to parse event:', e);
            }
        };
    } catch (error) {
        console.error('WebSocket connection failed:', error);
        handleReconnect();
    }
}

function handleReconnect() {
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
        setTimeout(initWebSocket, delay);
    } else {
        console.log('Max reconnection attempts reached, using polling fallback');
        updateSystemStatus('disconnected');
    }
}

function updateSystemStatus(status) {
    const statusEl = document.getElementById('systemStatus');
    const dot = statusEl.querySelector('.dot');

    dot.className = 'dot';

    switch (status) {
        case 'connected':
            dot.classList.add('connected');
            statusEl.innerHTML = '<span class="dot connected"></span> Connected';
            break;
        case 'disconnected':
            dot.classList.add('error');
            statusEl.innerHTML = '<span class="dot error"></span> Disconnected (Polling)';
            break;
        case 'error':
            dot.classList.add('error');
            statusEl.innerHTML = '<span class="dot error"></span> Error';
            break;
    }
}

// Fallback polling
let pollingInterval = null;

function setupTaskPolling() {
    if (pollingInterval) return;

    pollingInterval = setInterval(async () => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            try {
                await loadTasks();
            } catch (error) {
                console.error('Polling error:', error);
            }
        }
    }, 5000);
}

// ==================== DATA LOADING ====================
async function loadInitialData() {
    try {
        const statsRes = await fetch(`${API_BASE}/api/stats`);
        if (statsRes.ok) {
            const stats = await statsRes.json();
            document.getElementById('llmProvider').textContent = stats.llm_provider || '-';
        }

        await Promise.all([loadAgents(), loadTasks()]);
        await loadTaskHistory();

    } catch (error) {
        console.error('Failed to load initial data:', error);
    }
}

async function loadAgents() {
    try {
        const agentsRes = await fetch(`${API_BASE}/api/agents`);
        if (agentsRes.ok) {
            agents = await agentsRes.json();
            renderAgents();
        }
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
}

async function loadTasks() {
    try {
        const tasksRes = await fetch(`${API_BASE}/api/tasks`);
        if (tasksRes.ok) {
            tasks = await tasksRes.json();
            renderTasks();
            updateStats();
            updateTaskHistory();
        }
    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
}

// ==================== TASK HISTORY ====================
async function loadTaskHistory() {
    updateTaskHistory();
}

function updateTaskHistory() {
    const historyList = document.getElementById('taskHistory');
    const completedTasks = tasks.filter(t => t.status === 'completed' || t.status === 'failed');

    if (completedTasks.length === 0) {
        historyList.innerHTML = '<p class="empty-state">No completed tasks yet</p>';
        return;
    }

    historyList.innerHTML = completedTasks.slice(0, 20).map(task => {
        const desc = task.description || 'Untitled Task';
        const time = task.completed_at ? formatTime(task.completed_at) : '-';
        return `
            <div class="history-item" onclick="showTaskInspector('${task.id}')">
                <span class="history-status ${task.status}"></span>
                <span class="history-desc" title="${desc}">${desc.substring(0, 30)}${desc.length > 30 ? '...' : ''}</span>
                <span class="history-time">${time}</span>
            </div>
        `;
    }).join('');
}

// ==================== EVENT HANDLING ====================
function handleEvent(event) {
    addActivityLogItem(event);

    // Handle LLM transparency events
    if (event.type === 'llm_prompt' || event.type === 'llm_response' || event.type === 'agent_thinking') {
        handleLlmEvent(event);
    }

    switch (event.type) {
        case 'task_created':
            showToast('info', 'New Task', event.data?.description?.substring(0, 50) || 'Task created');
            break;
        case 'task_completed':
            showToast('success', 'Task Completed', event.data?.task_id || 'Task finished');
            break;
        case 'task_failed':
            showToast('error', 'Task Failed', event.data?.error || 'Task failed', 6000);
            break;
        case 'task_halted':
            showToast('warning', 'Task Halted', event.data?.task_id || 'Task halted by human', 6000);
            break;
        case 'problem_detected':
            handleProblemDetected(event.data || event);
            break;
        case 'critique_received':
            handleCritiqueReceived(event.data);
            break;
    }
}

// ==================== LLM LOG RENDERING ====================
function handleLlmEvent(event) {
    const agent = event.source || event.data?.agent;
    const taskId = event.data?.task_id;

    if (agent === 'senior_agent' || agent === 'senior') {
        renderLlmEntry('seniorLlmLog', event);
    } else if (agent === 'critic_agent' || agent === 'critic') {
        renderLlmEntry('criticLlmLog', event);
    }
}

function renderLlmEntry(logId, event) {
    const log = document.getElementById(logId);
    if (!log) return;

    // Remove placeholder if present
    const placeholder = log.querySelector('.llm-log-placeholder');
    if (placeholder) placeholder.remove();

    const entry = document.createElement('div');
    entry.className = `llm-entry ${getLlmEntryClass(event.type)}`;

    const typeLabel = getLlmEntryTypeLabel(event.type);
    const content = getLlmEntryContent(event);

    entry.innerHTML = `
        <div class="llm-entry-header">
            <span class="llm-entry-type">${typeLabel}</span>
            <span class="llm-entry-time">${formatTime(event.timestamp)}</span>
        </div>
        <div class="llm-entry-content" id="llm-content-${Date.now()}">${escapeHtml(content)}</div>
    `;

    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;

    // Limit entries
    while (log.children.length > 50) {
        log.removeChild(log.firstChild);
    }
}

function getLlmEntryClass(type) {
    switch (type) {
        case 'llm_prompt': return 'system-prompt';
        case 'llm_response': return 'llm-response';
        case 'agent_thinking': return 'agent-thinking';
        default: return '';
    }
}

function getLlmEntryTypeLabel(type) {
    switch (type) {
        case 'llm_prompt': return '[SYSTEM PROMPT]';
        case 'llm_response': return '[LLM RESPONSE]';
        case 'agent_thinking': return '[THINKING]';
        default: return `[${type}]`;
    }
}

function getLlmEntryContent(event) {
    const data = event.data || {};

    switch (event.type) {
        case 'llm_prompt':
            return `[${data.action || 'action'}] Using model: ${data.model || 'unknown'}\n\nSystem: ${truncate(data.system_prompt || '', 300)}\n\nUser: ${truncate(data.user_prompt || '', 500)}`;

        case 'llm_response':
            return `Model: ${data.model || 'unknown'}\nTokens: ${data.tokens_used || 0}\n\n${truncate(data.response || '', 800)}`;

        case 'agent_thinking':
            return data.message || 'Thinking...';

        default:
            return JSON.stringify(data, null, 2);
    }
}

function truncate(str, maxLen) {
    if (!str) return '';
    if (str.length <= maxLen) return str;
    return str.substring(0, maxLen) + '...';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function handleTaskEvent(event) {
    const taskData = event.data || event;

    if (!taskData || !taskData.id) return;

    const existingIndex = tasks.findIndex(t => t.id === taskData.id);

    if (existingIndex >= 0) {
        tasks[existingIndex] = {
            ...tasks[existingIndex],
            ...taskData,
            _updated: true
        };

        setTimeout(() => {
            const t = tasks.find(t => t.id === taskData.id);
            if (t) t._updated = false;
        }, 1000);
    } else {
        tasks.push(taskData);
    }

    renderTasks();
    updateStats();
    updateTaskHistory();
}

function handleProblemDetected(data) {
    const list = document.getElementById('problemList');

    const emptyState = list.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const item = document.createElement('div');
    item.className = 'problem-item';

    item.innerHTML = `
        <span class="severity-badge ${data.severity || 'medium'}">${data.severity || 'medium'}</span>
        <span class="problem-desc">${data.description || JSON.stringify(data)}</span>
        <span class="problem-time">${formatTime(data.timestamp || new Date())}</span>
    `;

    list.insertBefore(item, list.firstChild);

    while (list.children.length > 20) {
        list.removeChild(list.lastChild);
    }
}

// ==================== RENDERING ====================
function renderTasks() {
    const columns = {
        pending: { el: document.getElementById('pendingTasks'), count: document.getElementById('pendingCount') },
        in_progress: { el: document.getElementById('inProgressTasks'), count: document.getElementById('inProgressCount') },
        completed: { el: document.getElementById('completedTasks'), count: document.getElementById('completedCount') },
        failed: { el: document.getElementById('failedTasks'), count: document.getElementById('failedCount') },
        halted: { el: document.getElementById('haltedTasks'), count: document.getElementById('haltedCount') }
    };

    Object.values(columns).forEach(col => {
        col.el.innerHTML = '';
        col.count.textContent = '0';
    });

    const filter = document.getElementById('taskFilter').value;
    let filteredTasks = tasks;
    if (filter) {
        filteredTasks = tasks.filter(t => t.status === filter);
    }

    const counts = { pending: 0, in_progress: 0, completed: 0, failed: 0, halted: 0 };

    filteredTasks.forEach(task => {
        const status = task.status;
        if (columns[status]) {
            counts[status]++;
            const card = createTaskCard(task);
            columns[status].el.appendChild(card);
        }
    });

    Object.keys(counts).forEach(status => {
        if (columns[status]) {
            columns[status].count.textContent = counts[status];
        }
    });
}

function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = 'task-card';
    if (task._updated) {
        card.classList.add('updated');
    }
    if (task.status === 'halted') {
        card.classList.add('halted');
    }
    card.onclick = () => showTaskInspector(task.id);

    const duration = task.completed_at && task.started_at
        ? getDuration(task.started_at, task.completed_at)
        : (task.started_at ? 'In progress...' : 'Waiting');

    const desc = task.description || task.desc || JSON.stringify(task.result || task);
    const id = task.id || 'unknown';
    const agentId = task.assigned_to || 'Unassigned';
    const agentInitial = agentId.charAt(0).toUpperCase();

    card.innerHTML = `
        <div class="task-header">
            <span class="task-id">${id.substring(0, 12)}...</span>
            <span class="task-agent">
                <span class="task-agent-badge">${agentInitial}</span>
                ${agentId}
            </span>
        </div>
        <div class="task-desc">${desc.substring(0, 60)}${desc.length > 60 ? '...' : ''}</div>
        <div class="task-meta">
            <span>${duration}</span>
            <span>${task.type || 'task'}</span>
        </div>
    `;

    return card;
}

function updateStats() {
    // Stats are computed but not logged - they update the UI directly
    // Log connection status only when debugging WebSocket issues
}

function renderAgents() {
    const grid = document.getElementById('agentGrid');
    grid.innerHTML = '';

    if (!agents || agents.length === 0) {
        grid.innerHTML = '<p class="empty-state">No agents connected</p>';
        return;
    }

    const agentAvatars = {
        senior: '👑',
        worker: '⚙️',
        critic: '🔍'
    };

    agents.forEach(agent => {
        const card = document.createElement('div');
        const statusClass = agent.status === 'idle' ? 'idle' : (agent.status === 'running' ? 'busy' : '');
        const avatar = agentAvatars[agent.type?.toLowerCase()] || '🤖';

        card.className = `agent-card ${statusClass}`;

        const statusDotClass = agent.status === 'running' ? 'active' : (agent.status === 'paused' ? 'paused' : 'offline');

        card.innerHTML = `
            <div class="agent-header">
                <div class="agent-avatar">${avatar}</div>
                <div class="agent-info">
                    <div class="agent-id">
                        <span class="status-dot ${statusDotClass}"></span>
                        ${agent.id}
                    </div>
                    <div class="agent-type">${agent.type}</div>
                </div>
            </div>
            <div class="agent-status ${agent.status}">
                <span class="status-dot ${statusDotClass}"></span>
                ${agent.status || 'idle'}
            </div>
            <div class="agent-stats">
                <span>📋 ${agent.tasks_completed || 0}</span>
                <span>📍 ${agent.current_task || '-'}</span>
            </div>
            <div class="agent-actions">
                <button class="btn-pause" onclick="pauseAgent('${agent.id}')">⏸ Pause</button>
                <button class="btn-resume" onclick="resumeAgent('${agent.id}')">▶ Resume</button>
            </div>
        `;

        grid.appendChild(card);
    });
}

function handleCritiqueReceived(data) {
    critiques.unshift(data);

    const list = document.getElementById('critiqueList');

    if (critiques.length === 1) {
        list.innerHTML = '';
    }

    const item = document.createElement('div');
    item.className = `critique-item ${data.approved ? 'approved' : 'rejected'}`;

    item.innerHTML = `
        <div class="critique-header">
            <span class="critique-task-id">Task: ${data.task_id}</span>
            <span class="critique-status ${data.approved ? 'approved' : 'rejected'}">
                ${data.approved ? '✓ APPROVED' : '✗ REJECTED'}
            </span>
        </div>
        <div class="critique-reasoning">${data.reasoning || 'No reasoning provided'}</div>
        ${data.confidence ? `
            <div class="critique-confidence">
                Confidence: ${(data.confidence * 100).toFixed(0)}%
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${data.confidence * 100}%"></div>
                </div>
            </div>
        ` : ''}
    `;

    list.insertBefore(item, list.firstChild);

    // Show toast for critique
    showToast(
        data.approved ? 'success' : 'warning',
        'Critique Received',
        `Task ${data.task_id}: ${data.approved ? 'Approved' : 'Needs revision'}`
    );
}

function addActivityLogItem(event) {
    const log = document.getElementById('eventLog');
    const filter = document.getElementById('eventFilter').value;

    if (filter && event.type !== filter) {
        return;
    }

    const item = document.createElement('div');

    // Determine event category for coloring
    let eventCategory = 'info';
    if (event.type === 'task_completed' || event.type === 'critique_received' && event.data?.approved) {
        eventCategory = 'success';
    } else if (event.type === 'task_failed' || event.type === 'problem_detected') {
        eventCategory = 'error';
    } else if (event.type === 'task_started') {
        eventCategory = 'warning';
    }

    // Check if this is a human feedback event
    if (event.type === 'agent_message' && event.data?.type === 'human_feedback' && event.data?.source === 'human') {
        eventCategory = 'human-feedback';
    }

    item.className = `event-item ${eventCategory}`;

    const iconClass = (event.type || 'unknown').replace(/_/g, '-').toLowerCase();

    const eventIcons = {
        task_created: '📝',
        task_assigned: '👤',
        task_started: '▶️',
        task_completed: '✅',
        task_failed: '❌',
        task_halted: '⏸',
        task_resumed: '▶️',
        critique_received: '🔍',
        problem_detected: '⚠️',
        agent_message: '💬',
        llm_prompt: '📤',
        llm_response: '📥',
        agent_thinking: '💭',
        task_decomposed: '📋',
        critique_request: '🔎',
        task_feedback: '💬'
    };

    item.innerHTML = `
        <span class="event-time">${formatTime(event.timestamp)}</span>
        <span class="event-icon ${iconClass}">${eventIcons[event.type] || '📌'}</span>
        <span class="event-type">${formatEventType(event.type)}</span>
        <span class="event-source">${event.source || '-'}</span>
    `;

    log.insertBefore(item, log.firstChild);

    while (log.children.length > 100) {
        log.removeChild(log.lastChild);
    }
}

// ==================== HELPERS ====================
function formatTime(timestamp) {
    if (!timestamp) return '--:--:--';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false }) || '--:--:--';
}

function formatEventType(type) {
    if (!type) return 'Unknown';
    return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function getDuration(start, end) {
    if (!start || !end) return '-';
    const ms = new Date(end) - new Date(start);
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
}

function showTaskModal(task) {
    const modal = document.getElementById('taskModal');
    const body = document.getElementById('taskModalBody');

    const result = task.result ? JSON.stringify(task.result, null, 2) : '';

    body.innerHTML = `
        <div class="info-row">
            <span class="label">Task ID:</span>
            <span class="value" style="font-family: monospace;">${task.id}</span>
        </div>
        <div class="info-row">
            <span class="label">Status:</span>
            <span class="value">${task.status}</span>
        </div>
        <div class="info-row">
            <span class="label">Assigned To:</span>
            <span class="value">${task.assigned_to || 'Unassigned'}</span>
        </div>
        <div class="info-row">
            <span class="label">Created:</span>
            <span class="value">${formatTime(task.created_at)}</span>
        </div>
        ${task.started_at ? `
            <div class="info-row">
                <span class="label">Started:</span>
                <span class="value">${formatTime(task.started_at)}</span>
            </div>
        ` : ''}
        ${task.completed_at ? `
            <div class="info-row">
                <span class="label">Completed:</span>
                <span class="value">${formatTime(task.completed_at)}</span>
            </div>
        ` : ''}
        ${task.type ? `
            <div class="info-row">
                <span class="label">Type:</span>
                <span class="value">${task.type}</span>
            </div>
        ` : ''}
        ${task.priority ? `
            <div class="info-row">
                <span class="label">Priority:</span>
                <span class="value">${task.priority}</span>
            </div>
        ` : ''}
        ${result ? `
            <div class="result-section" style="margin-top: 1rem;">
                <h3>Result</h3>
                <pre style="background: #0d1117; padding: 0.75rem; border-radius: 6px; overflow-x: auto; font-size: 0.8rem; max-height: 300px; border: 1px solid #30363d;">${result}</pre>
            </div>
        ` : ''}
        ${task.error ? `
            <div class="error-section" style="margin-top: 1rem; color: var(--error);">
                <h3>Error</h3>
                <p>${task.error}</p>
            </div>
        ` : ''}
        ${task.comments && task.comments.length > 0 ? `
            <div class="comments-section" style="margin-top: 1rem;">
                <h3>Comments (${task.comments.length})</h3>
                ${task.comments.map(c => `
                    <div style="background: var(--bg-primary); padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem;">
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">${c.agent_id} at ${formatTime(c.timestamp)}</div>
                        <div style="font-size: 0.85rem;">${c.content}</div>
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;

    modal.classList.add('active');
}

function closeTaskModal() {
    document.getElementById('taskModal').classList.remove('active');
}

// ==================== TASK INSPECTOR MODAL ====================
async function showTaskInspector(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) {
        // Try to fetch from API
        try {
            const res = await fetch(`${API_BASE}/api/tasks/${taskId}`);
            if (res.ok) {
                const fullTask = await res.json();
                renderTaskInspector(fullTask);
            }
        } catch (e) {
            console.error('Failed to load task:', e);
            showToast('error', 'Error', 'Failed to load task details');
        }
        return;
    }
    renderTaskInspector(task);
}

function renderTaskInspector(task) {
    const modal = document.getElementById('taskInspectorModal');
    const body = document.getElementById('taskInspectorBody');

    const statusClass = task.status || 'pending';
    const statusLabel = task.status ? task.status.replace('_', ' ') : 'pending';

    const subtasksHtml = (task.subtasks && task.subtasks.length > 0)
        ? task.subtasks.map((st, i) => `
            <div class="subtask-inspector-item">
                <span class="subtask-number">${i + 1}</span>
                <div class="subtask-inspector-content">
                    <div class="subtask-inspector-title">${st.description || st.title || JSON.stringify(st)}</div>
                    <div class="subtask-inspector-meta">${st.agent_id ? `Agent: ${st.agent_id}` : ''} ${st.status ? `• Status: ${st.status}` : ''}</div>
                </div>
            </div>
        `).join('')
        : '<p class="empty-state">No subtasks</p>';

    const commandsHtml = (task.commands && task.commands.length > 0)
        ? task.commands.map(cmd => `
            <div class="command-item">
                <div class="command-time">${formatTime(cmd.timestamp || cmd.time)}</div>
                <div style="margin-top: 0.25rem;">${cmd.command || cmd}</div>
                ${cmd.output ? `<div style="color: var(--text-secondary); margin-top: 0.25rem; font-size: 0.75rem;">Output: ${cmd.output.substring(0, 100)}...</div>` : ''}
            </div>
        `).join('')
        : '<p class="empty-state">No commands executed</p>';

    body.innerHTML = `
        <div class="inspector-header">
            <div>
                <span class="inspector-task-id">${task.id}</span>
                <h2 class="inspector-title">${task.description || 'Task Details'}</h2>
            </div>
            <span class="inspector-status ${statusClass}">${statusLabel.toUpperCase()}</span>
        </div>

        <div class="inspector-grid">
            <div class="inspector-field">
                <div class="inspector-field-label">Assigned To</div>
                <div class="inspector-field-value">${task.assigned_to || 'Unassigned'}</div>
            </div>
            <div class="inspector-field">
                <div class="inspector-field-label">Created</div>
                <div class="inspector-field-value">${formatTime(task.created_at)}</div>
            </div>
            <div class="inspector-field">
                <div class="inspector-field-label">Started</div>
                <div class="inspector-field-value">${task.started_at ? formatTime(task.started_at) : 'Not started'}</div>
            </div>
            <div class="inspector-field">
                <div class="inspector-field-label">Completed</div>
                <div class="inspector-field-value">${task.completed_at ? formatTime(task.completed_at) : 'In progress'}</div>
            </div>
        </div>

        <div class="inspector-section">
            <h3>📋 Subtasks (${task.subtasks ? task.subtasks.length : 0})</h3>
            <div class="inspector-subtasks">
                ${subtasksHtml}
            </div>
        </div>

        ${task.commands && task.commands.length > 0 ? `
            <div class="inspector-section">
                <h3>💻 Commands Executed</h3>
                <div class="inspector-commands">
                    ${commandsHtml}
                </div>
            </div>
        ` : ''}

        ${task.result ? `
            <div class="inspector-section">
                <h3>📊 Result</h3>
                <pre class="inspector-commands" style="max-height: 200px;">${JSON.stringify(task.result, null, 2)}</pre>
            </div>
        ` : ''}

        ${task.error ? `
            <div class="inspector-section" style="color: var(--error);">
                <h3>❌ Error</h3>
                <div class="inspector-description">${task.error}</div>
            </div>
        ` : ''}

        ${task.comments && task.comments.length > 0 ? `
            <div class="inspector-section">
                <h3>👤 Human Feedback (${task.comments.filter(c => c.agent_id === 'human').length})</h3>
                <div class="inspector-human-feedback" style="background: rgba(155, 89, 182, 0.1); border-color: rgba(155, 89, 182, 0.3);">
                    ${task.comments.filter(c => c.agent_id === 'human').map(c => `
                        <div style="background: var(--bg-secondary); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid #9b59b6;">
                            <div style="font-size: 0.75rem; color: #9b59b6; margin-bottom: 0.25rem;">👤 HUMAN at ${formatTime(c.timestamp)}</div>
                            <div style="font-size: 0.9rem;">${c.content}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : ''}

        <div class="inspector-section">
            <h3>💬 Human Intervention</h3>
            <div class="inspector-human-feedback">
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
                    Send feedback to guide the agent. The agent will receive this before its next LLM call.
                </p>
                <div class="feedback-form">
                    <textarea id="feedbackText" placeholder="E.g., 'Change the approach - use a dictionary instead of a list' or 'The output format is wrong, please fix it'"></textarea>
                    <div class="feedback-actions">
                        <button class="btn-halt" onclick="haltTaskFromInspector('${task.id}')">⏸ Halt</button>
                        <button class="btn-feedback" onclick="sendFeedbackAndResume('${task.id}')">💬 Send & Resume</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    modal.classList.add('active');
}

function closeTaskInspector() {
    document.getElementById('taskInspectorModal').classList.remove('active');
}

async function haltTaskFromInspector(taskId) {
    const reason = prompt('Reason for halting? (optional)');
    try {
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}/halt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: reason || 'Halted by human' })
        });
        if (res.ok) {
            showToast('warning', 'Task Halted', `Task ${taskId.substring(0, 12)}... has been halted`);
            await loadTasks();
            closeTaskInspector();
        } else {
            showToast('error', 'Error', 'Failed to halt task');
        }
    } catch (e) {
        console.error('Failed to halt task:', e);
        showToast('error', 'Error', 'Failed to halt task');
    }
}

async function addFeedbackFromInspector(taskId) {
    const feedback = document.getElementById('feedbackText').value;
    if (!feedback.trim()) {
        showToast('warning', 'Feedback Required', 'Please enter feedback before submitting');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback })
        });
        if (res.ok) {
            showToast('success', 'Feedback Added', 'Human feedback has been recorded');
            await loadTasks();
            closeTaskInspector();
        } else {
            showToast('error', 'Error', 'Failed to add feedback');
        }
    } catch (e) {
        console.error('Failed to add feedback:', e);
        showToast('error', 'Error', 'Failed to add feedback');
    }
}

async function sendFeedbackAndResume(taskId) {
    const feedback = document.getElementById('feedbackText').value;
    if (!feedback.trim()) {
        showToast('warning', 'Feedback Required', 'Please enter feedback before submitting');
        return;
    }

    try {
        // Send feedback
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback })
        });

        if (res.ok) {
            // Clear the textarea
            document.getElementById('feedbackText').value = '';

            // If task is halted, resume it using the dedicated resume endpoint
            const task = tasks.find(t => t.id === taskId);
            if (task && task.status === 'halted') {
                const resumeRes = await fetch(`${API_BASE}/api/tasks/${taskId}/resume`, {
                    method: 'POST'
                });
                if (resumeRes.ok) {
                    showToast('success', 'Feedback Sent & Task Resumed', 'Agent will process your feedback');
                } else {
                    showToast('success', 'Feedback Sent', 'Feedback sent (resume failed)');
                }
            } else {
                showToast('success', 'Feedback Sent', 'Agent will receive your feedback on next LLM call');
            }

            await loadTasks();
            closeTaskInspector();
        } else {
            showToast('error', 'Error', 'Failed to send feedback');
        }
    } catch (e) {
        console.error('Failed to send feedback:', e);
        showToast('error', 'Error', 'Failed to send feedback');
    }
}

// ==================== AGENT ACTIONS ====================
async function pauseAgent(agentId) {
    try {
        const res = await fetch(`${API_BASE}/api/agents/${agentId}/pause`, { method: 'POST' });
        if (res.ok) {
            await loadAgents();
            showToast('success', 'Agent Paused', `${agentId} has been paused`);
        }
    } catch (error) {
        console.error('Failed to pause agent:', error);
        showToast('error', 'Error', `Failed to pause ${agentId}`);
    }
}

async function resumeAgent(agentId) {
    try {
        const res = await fetch(`${API_BASE}/api/agents/${agentId}/resume`, { method: 'POST' });
        if (res.ok) {
            await loadAgents();
            showToast('success', 'Agent Resumed', `${agentId} is now running`);
        }
    } catch (error) {
        console.error('Failed to resume agent:', error);
        showToast('error', 'Error', `Failed to resume ${agentId}`);
    }
}

// ==================== ROLE EDITOR ====================
async function openRoleModal(filename) {
    currentRoleFilename = filename;
    const modal = document.getElementById('roleModal');
    const title = document.getElementById('roleModalTitle');
    const content = document.getElementById('roleContent');
    const info = document.getElementById('roleInfo');

    title.textContent = `Edit Role: ${filename}`;
    content.value = 'Loading...';
    info.textContent = '';

    try {
        const res = await fetch(`${API_BASE}/api/roles/${filename}`);
        if (res.ok) {
            const data = await res.json();
            content.value = data.content;
            originalRoleContent = data.content;
            info.textContent = `Size: ${data.content.length} characters`;
        } else {
            content.value = 'Error loading file';
            info.textContent = 'Failed to load role file';
            showToast('error', 'Error', 'Failed to load role file');
        }
    } catch (error) {
        content.value = 'Error loading file';
        info.textContent = `Error: ${error.message}`;
        showToast('error', 'Error', 'Failed to connect to server');
    }

    modal.classList.add('active');
    closeSidebar();
}

function closeRoleModal() {
    document.getElementById('roleModal').classList.remove('active');
    currentRoleFilename = null;
    originalRoleContent = null;
}

function resetRole() {
    if (originalRoleContent !== null) {
        document.getElementById('roleContent').value = originalRoleContent;
    }
}

async function saveRole() {
    if (!currentRoleFilename) return;

    const content = document.getElementById('roleContent').value;
    const info = document.getElementById('roleInfo');

    try {
        const res = await fetch(`${API_BASE}/api/roles/${currentRoleFilename}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (res.ok) {
            info.innerHTML = '<span class="role-success">✓ Changes saved successfully!</span>';
            originalRoleContent = content;
            showToast('success', 'Role Saved', `${currentRoleFilename} has been updated`);
            setTimeout(() => {
                info.textContent = `Size: ${content.length} characters`;
            }, 2000);
        } else {
            const err = await res.json();
            info.innerHTML = `<span class="role-error">✗ Error: ${err.detail || 'Failed to save'}</span>`;
            showToast('error', 'Error', 'Failed to save role file');
        }
    } catch (error) {
        info.innerHTML = `<span class="role-error">✗ Error: ${error.message}</span>`;
        showToast('error', 'Error', 'Failed to connect to server');
    }
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    document.getElementById('taskFilter').addEventListener('change', renderTasks);
    document.getElementById('eventFilter').addEventListener('change', () => {
        document.getElementById('eventLog').innerHTML = '';
    });

    document.getElementById('criticToggle').addEventListener('change', (e) => {
        showToast('info', 'Critic Agent', e.target.checked ? 'Enabled' : 'Disabled');
    });

    // Modal close handlers
    document.getElementById('taskModal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) closeTaskModal();
    });

    document.getElementById('taskInspectorModal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) closeTaskInspector();
    });

    document.getElementById('newTaskModal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) closeNewTaskModal();
    });

    document.getElementById('roleModal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) closeRoleModal();
    });

    // ESC key handler
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeTaskModal();
            closeTaskInspector();
            closeNewTaskModal();
            closeRoleModal();
            closeSidebar();
        }
    });

    // New task form
    document.getElementById('newTaskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const description = document.getElementById('taskDescription').value;
        if (description.trim()) {
            const taskId = await submitTask(description);
            if (taskId) {
                closeNewTaskModal();
                document.getElementById('taskDescription').value = '';
                showToast('success', 'Task Submitted', `Task ${taskId.substring(0, 12)}... created`);
            }
        }
    });

    // Close sidebar when clicking main content
    document.querySelector('.main-content')?.addEventListener('click', (e) => {
        if (e.target.closest('.sidebar')) return;
        closeSidebar();
    });
}

// ==================== NEW TASK MODAL ====================
function openNewTaskModal() {
    document.getElementById('newTaskModal').classList.add('active');
}

function closeNewTaskModal() {
    document.getElementById('newTaskModal').classList.remove('active');
}

async function submitTask(description) {
    try {
        const res = await fetch(`${API_BASE}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description })
        });
        if (res.ok) {
            const data = await res.json();
            await loadTasks();
            return data.task_id;
        } else {
            console.error('Failed to submit task:', await res.text());
            showToast('error', 'Error', 'Failed to submit task');
        }
    } catch (error) {
        console.error('Failed to submit task:', error);
        showToast('error', 'Error', 'Failed to connect to server');
    }
    return null;
}
