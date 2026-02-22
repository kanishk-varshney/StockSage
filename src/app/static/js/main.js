/** Main JavaScript for StockSage UI. */

let eventSource = null;

const ANALYSIS_STEPS = [
    'Valuation &amp; Profitability',
    'Price Performance &amp; Risk',
    'Financial Health',
    'Market Sentiment',
    'Quality Review',
    'Investment Report',
];
const TOTAL_STEPS = ANALYSIS_STEPS.length;
const STEP_LABELS = {
    'Valuation &amp; Profitability': 'Valuation',
    'Price Performance &amp; Risk': 'Performance & Risk',
    'Financial Health': 'Financial Summary',
    'Market Sentiment': 'Sentiment & News',
    'Quality Review': 'Quality Review',
    'Investment Report': 'Company Profile & Recommendation',
};

function stageLabel(step) {
    if (step <= 0) {
        return 'Preparing analysis...';
    }
    const raw = ANALYSIS_STEPS[step - 1] || 'Finalizing';
    const friendly = STEP_LABELS[raw] || raw;
    return `${friendly} (${step} of ${TOTAL_STEPS})`;
}

function updateProgress(step, label) {
    const wrapper = document.getElementById('progress-wrapper');
    const fill = document.getElementById('progress-fill');
    const labelEl = document.getElementById('progress-label');

    wrapper.style.display = '';
    const pct = Math.min(Math.round((step / TOTAL_STEPS) * 100), 100);
    fill.style.width = pct + '%';
    labelEl.textContent = label;

    if (step >= TOTAL_STEPS) {
        setTimeout(() => { wrapper.style.display = 'none'; }, 1200);
    }
}

function cardOrderPriority(card) {
    const header = card.querySelector('.log-analysis-header');
    const title = (header ? header.textContent : '').toLowerCase();
    if (title.includes('valuation')) return 0;
    if (title.includes('price performance')) return 1;
    if (title.includes('financial health')) return 2;
    if (title.includes('market sentiment')) return 3;
    if (title.includes('quality review')) return 4;
    if (title.includes('final analysis') || title.includes('investment report')) return 5;
    return 99;
}

function reorderAnalysisCards() {
    const logsDiv = document.getElementById('logs');
    const cards = Array.from(logsDiv.querySelectorAll('.log-analysis'));
    if (cards.length < 2) return;

    const sorted = cards
        .map((card, index) => ({ card, index, priority: cardOrderPriority(card) }))
        .sort((a, b) => (a.priority - b.priority) || (a.index - b.index))
        .map(item => item.card);

    sorted.forEach(card => logsDiv.appendChild(card));
}

function updateGlobalVerdictBadge() {
    const badge = document.getElementById('global-verdict-badge');
    const verdictNodes = Array.from(document.querySelectorAll('.gauge-verdict'));
    if (!verdictNodes.length) {
        badge.style.display = 'none';
        return;
    }

    const verdict = verdictNodes[verdictNodes.length - 1].textContent.trim();
    if (!verdict) {
        badge.style.display = 'none';
        return;
    }

    badge.classList.remove('verdict-buy', 'verdict-hold', 'verdict-sell');
    const upper = verdict.toUpperCase();
    if (upper.includes('BUY')) {
        badge.classList.add('verdict-buy');
    } else if (upper.includes('SELL')) {
        badge.classList.add('verdict-sell');
    } else {
        badge.classList.add('verdict-hold');
    }

    badge.textContent = `Recommendation: ${verdict}`;
    badge.style.display = 'inline-flex';
}

async function startProcessing(event) {
    event.preventDefault();
    const symbol = document.getElementById('symbol').value;
    const logsDiv = document.getElementById('logs');
    const spinner = document.getElementById('spinner');
    const submitButton = event.target.querySelector('button[type="submit"]');
    const progressWrapper = document.getElementById('progress-wrapper');
    const progressFill = document.getElementById('progress-fill');

    spinner.style.display = 'inline';
    submitButton.disabled = true;
    event.target.setAttribute('aria-busy', 'true');

    logsDiv.innerHTML = '<div class="empty-state">Preparing your analysis...</div>';
    progressWrapper.style.display = 'none';
    progressFill.style.width = '0%';
    updateGlobalVerdictBadge();

    let analysisStep = 0;

    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(`/stream?symbol=${encodeURIComponent(symbol)}`);

    eventSource.onmessage = function(e) {
        const emptyState = logsDiv.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const wrapper = document.createElement('div');
        wrapper.innerHTML = e.data;

        for (let i = 0; i < ANALYSIS_STEPS.length; i++) {
            if (e.data.includes(ANALYSIS_STEPS[i] + '...')) {
                analysisStep = i + 1;
                updateProgress(analysisStep, stageLabel(analysisStep));
                break;
            }
        }

        const completedCard = wrapper.querySelector('.log-analysis');
        if (completedCard) {
            updateProgress(analysisStep, stageLabel(analysisStep));
        }

        if (wrapper.innerHTML.trim()) {
            logsDiv.insertAdjacentHTML('beforeend', wrapper.innerHTML);
            reorderAnalysisCards();
            updateGlobalVerdictBadge();
        }

        logsDiv.scrollTop = logsDiv.scrollHeight;
    };

    eventSource.onerror = function(e) {
        console.error('SSE error:', e);
        eventSource.close();
        spinner.style.display = 'none';
        submitButton.disabled = false;
        event.target.setAttribute('aria-busy', 'false');
        document.getElementById('progress-wrapper').style.display = 'none';

        const emptyState = logsDiv.querySelector('.empty-state');
        if (emptyState) {
            emptyState.textContent = 'Analysis finished or connection was interrupted. Try again if needed.';
        }
    };

    eventSource.addEventListener('complete', function() {
        eventSource.close();
        spinner.style.display = 'none';
        submitButton.disabled = false;
        event.target.setAttribute('aria-busy', 'false');
        reorderAnalysisCards();
        updateGlobalVerdictBadge();
        updateProgress(TOTAL_STEPS, 'Complete');
    });
}
