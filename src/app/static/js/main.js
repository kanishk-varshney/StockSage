/** Main JavaScript for StockSage UI. */

let eventSource = null;
let reconnectTimeoutId = null;
let reconnectStartedAt = null;

const RECONNECT_BUDGET_MS = 30000;
const RUNTIME = window.STOCKSAGE_RUNTIME || {};
const STREAM_MODE = RUNTIME.streamMode === 'mock' ? 'mock' : 'live';
const TOTAL_PIPELINE_STEPS = RUNTIME.totalPipelineSteps || 1;
const STAGE_LABELS = RUNTIME.stageLabels || {};
const SUBSTAGE_LABELS = RUNTIME.substageLabels || {};

function detectStageLabel(html) {
    const sub = html.match(/data-substage="([^"]+)"/);
    if (sub && SUBSTAGE_LABELS[sub[1]]) return SUBSTAGE_LABELS[sub[1]] + '...';
    const stg = html.match(/data-stage="([^"]+)"/);
    if (stg && STAGE_LABELS[stg[1]]) return STAGE_LABELS[stg[1]] + '...';
    return null;
}

const SECTION_ORDER = {
    'company-header': 0,
    'quick-answers': 1,
    'valuation': 2,
    'performance': 3,
    'health': 4,
    'sentiment': 5,
    'review': 6,
    'final-guidance': 7,
};

function updateProgress(step) {
    const fill = document.getElementById('progress-bar-fill');
    if (!fill) return;
    fill.style.width = `${Math.min(Math.round((step / TOTAL_PIPELINE_STEPS) * 100), 95)}%`;
}

function cardOrderPriority(card) {
    const section = card.getAttribute('data-section');
    if (section && section in SECTION_ORDER) return SECTION_ORDER[section];
    const text = (card.textContent || '').toLowerCase();
    if (text.includes('valuation')) return 2;
    if (text.includes('performance')) return 3;
    if (text.includes('financial health') || text.includes('business health')) return 4;
    if (text.includes('market sentiment')) return 5;
    if (text.includes('quality review')) return 6;
    if (text.includes('final')) return 7;
    return 99;
}

function reorderAnalysisCards() {
    const logsDiv = document.getElementById('logs');
    const cards = Array.from(logsDiv.querySelectorAll('.log-analysis'));
    if (cards.length < 2) return;
    const sorted = cards
        .map((card, index) => ({ card, index, priority: cardOrderPriority(card) }))
        .sort((a, b) => (a.priority - b.priority) || (a.index - b.index));
    const alreadyOrdered = sorted.every((item, i) => item.index === i);
    if (alreadyOrdered) return;
    sorted.forEach(item => logsDiv.appendChild(item.card));
}

function updateGlobalVerdictBadge() {
    const badge = document.getElementById('global-verdict-badge');
    let verdict = '';
    document.querySelectorAll('[data-section="company-header"], [data-section="final-guidance"]').forEach(card => {
        const el = card.querySelector('.bg-amber-500, .bg-green-500, .bg-red-500');
        if (el && el.textContent.trim()) verdict = el.textContent.trim();
    });
    if (!verdict) {
        badge.classList.add('hidden');
        return;
    }
    const upper = verdict.toUpperCase();
    badge.className = 'inline-flex items-center px-5 py-2 rounded-lg text-sm font-semibold';
    if (upper.includes('BUY')) {
        badge.classList.add('bg-green-500', 'text-white');
    } else if (upper.includes('SELL')) {
        badge.classList.add('bg-red-500', 'text-white');
    } else {
        badge.classList.add('bg-amber-500', 'text-white');
    }
    badge.textContent = `Recommendation: ${verdict.replace(/[^\w\s]/g, '').trim()}`;
    badge.classList.remove('hidden');
}

function updateLiveStatus(html) {
    const label = detectStageLabel(html);
    if (!label) return;
    const progressText = document.getElementById('progress-stage-text');
    if (progressText) progressText.textContent = label;
}

function setConnectionStatus(logsDiv, message) {
    let status = document.getElementById('connection-status');
    if (!status) {
        status = document.createElement('div');
        status.id = 'connection-status';
        status.className = 'text-gray-400 italic text-center py-4 text-sm';
        logsDiv.prepend(status);
    }
    status.textContent = message;
}

function clearConnectionStatus() {
    const el = document.getElementById('connection-status');
    if (el) el.remove();
}

function clearReconnectTimer() {
    if (reconnectTimeoutId) {
        clearTimeout(reconnectTimeoutId);
        reconnectTimeoutId = null;
    }
    reconnectStartedAt = null;
}

function closeActiveStreamIfAny() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}

function setProcessingUI(formEl, isProcessing) {
    const submitButton = formEl.querySelector('button[type="submit"]');
    submitButton.disabled = isProcessing;
    submitButton.textContent = isProcessing ? 'Analyzing...' : 'Analyze Stock';
    formEl.setAttribute('aria-busy', isProcessing ? 'true' : 'false');
}

function resetRunSurface(logsDiv) {
    logsDiv.innerHTML = '';
    const wsLogs = document.getElementById('workspace-logs');
    if (wsLogs) wsLogs.innerHTML = '';
    const progressFill = document.getElementById('progress-bar-fill');
    const progressText = document.getElementById('progress-stage-text');
    if (progressFill) progressFill.style.width = '0%';
    if (progressText) progressText.textContent = (STAGE_LABELS['starting'] || 'Starting') + '...';
    showProcessingSection();
    updateGlobalVerdictBadge();
}

function finalizeActiveWsEntry(status) {
    const prev = document.querySelector('#workspace-logs .ws-active');
    if (!prev) return;
    prev.classList.remove('ws-active');
    const icon = prev.querySelector('.ws-icon');
    if (status === 'failed') {
        prev.setAttribute('data-status', 'failed');
        if (icon) icon.textContent = '\u2717';
    } else {
        prev.classList.add('ws-done');
        if (icon) icon.textContent = '\u2713';
    }
}

function showProcessingSection() {
    const section = document.getElementById('processing-section');
    if (section) section.classList.remove('hidden');
}

function hideProcessingSection() {
    const section = document.getElementById('processing-section');
    if (section) section.classList.add('hidden');
}

function appendIncomingHtml(logsDiv, html, analysisStep) {
    clearReconnectTimer();
    clearConnectionStatus();
    const emptyState = logsDiv.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;

    const wsEntry = wrapper.querySelector('.workspace-entry');
    if (wsEntry) {
        const substage = wsEntry.getAttribute('data-substage') || '';
        const stage = wsEntry.getAttribute('data-stage') || '';
        const key = substage || ('stage:' + stage);
        const wsLogs = document.getElementById('workspace-logs');

        if (substage && wsLogs) {
            const existing = wsLogs.querySelector(`.workspace-entry[data-substage="${substage}"]`);
            if (existing) {
                const raw = wsEntry.querySelector('.ws-text')?.textContent?.replace(/^→\s*/, '').trim() || '';
                let summaryText = '';
                if (stage === 'analyzing') {
                    const pfx = 'Structured Summary:';
                    const idx = raw.indexOf(pfx);
                    if (idx !== -1) summaryText = raw.substring(idx + pfx.length).split('\n')[0].trim();
                } else if (raw.length <= 120) {
                    summaryText = raw;
                }
                if (summaryText) {
                    const detail = document.createElement('span');
                    detail.className = 'ws-detail';
                    detail.textContent = ' \u2014 ' + summaryText;
                    existing.querySelector('.ws-text').appendChild(detail);
                }
                const incomingStatus = wsEntry.getAttribute('data-status') || '';
                finalizeActiveWsEntry(incomingStatus);
                return;
            }
        }

        if (!analysisStep.seen.has(key)) {
            analysisStep.seen.add(key);
            analysisStep.value++;
        }
        updateProgress(analysisStep.value);
        updateLiveStatus(html);
        if (wsLogs) {
            finalizeActiveWsEntry();
            wsEntry.classList.add('ws-active');
            wsEntry.querySelector('.ws-icon').innerHTML = '<i class="fas fa-circle-notch fa-spin ws-spinner"></i>';
            wsLogs.appendChild(wsEntry);
        }
        return;
    }

    const analysisCards = wrapper.querySelectorAll('.log-analysis');
    if (analysisCards.length) {
        finalizeActiveWsEntry();
        const wsLogs = document.getElementById('workspace-logs');
        analysisCards.forEach(card => {
            if (wsLogs) {
                const sub = card.getAttribute('data-substage');
                const summary = card.getAttribute('data-ws-summary');
                if (sub && summary) {
                    const wsRow = wsLogs.querySelector(`.workspace-entry[data-substage="${sub}"]`);
                    if (wsRow) {
                        const detail = document.createElement('span');
                        detail.className = 'ws-detail';
                        detail.textContent = ' \u2014 ' + summary;
                        wsRow.querySelector('.ws-text').appendChild(detail);
                    }
                }
            }
            card.style.display = 'none';
            logsDiv.appendChild(card);
        });
        return;
    }

    if (wrapper.innerHTML.trim()) {
        logsDiv.insertAdjacentHTML('beforeend', wrapper.innerHTML);
        reorderAnalysisCards();
        updateGlobalVerdictBadge();
    }
    logsDiv.scrollTop = logsDiv.scrollHeight;
}

function getStreamUrl(symbol) {
    const encoded = encodeURIComponent(symbol);
    return STREAM_MODE === 'mock' ? `/stream/mock?symbol=${encoded}` : `/stream?symbol=${encoded}`;
}

function startProcessing(event) {
    event.preventDefault();
    const symbol = document.getElementById('symbol').value;
    const logsDiv = document.getElementById('logs');
    const formEl = event.target;
    const analysisStep = { value: 0, seen: new Set() };

    setProcessingUI(formEl, true);
    resetRunSurface(logsDiv);
    clearReconnectTimer();
    closeActiveStreamIfAny();

    eventSource = new EventSource(getStreamUrl(symbol));

    eventSource.onmessage = function(e) {
        appendIncomingHtml(logsDiv, e.data, analysisStep);
    };

    eventSource.onerror = function(e) {
        console.error('SSE error:', e);
        if (!reconnectStartedAt) {
            reconnectStartedAt = Date.now();
            setConnectionStatus(logsDiv, 'Connection interrupted. Reconnecting...');
            reconnectTimeoutId = setTimeout(() => {
                closeActiveStreamIfAny();
                setProcessingUI(formEl, false);
                setConnectionStatus(logsDiv, 'Connection could not be restored. Please retry your analysis.');
            }, RECONNECT_BUDGET_MS);
            return;
        }
        if (Date.now() - reconnectStartedAt >= RECONNECT_BUDGET_MS) {
            closeActiveStreamIfAny();
            setProcessingUI(formEl, false);
            setConnectionStatus(logsDiv, 'Connection could not be restored. Please retry your analysis.');
        }
    };

    eventSource.addEventListener('stream_error', function(e) {
        closeActiveStreamIfAny();
        clearReconnectTimer();
        setProcessingUI(formEl, false);
        finalizeActiveWsEntry();
        hideProcessingSection();
        logsDiv.querySelectorAll('.log-analysis').forEach(c => c.style.display = '');
        reorderAnalysisCards();
        updateGlobalVerdictBadge();
        setConnectionStatus(logsDiv, e.data || 'Analysis failed due to a server error.');
    });

    eventSource.addEventListener('complete', function() {
        closeActiveStreamIfAny();
        clearReconnectTimer();
        clearConnectionStatus();
        setProcessingUI(formEl, false);
        finalizeActiveWsEntry();
        hideProcessingSection();
        reorderAnalysisCards();
        logsDiv.querySelectorAll('.log-analysis').forEach(c => c.style.display = '');
        updateGlobalVerdictBadge();
    });
}
