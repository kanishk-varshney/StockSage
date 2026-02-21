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

    logsDiv.innerHTML = '<div class="empty-state">Starting processing...</div>';
    progressWrapper.style.display = 'none';
    progressFill.style.width = '0%';

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
                updateProgress(analysisStep, 'Step ' + analysisStep + '/' + TOTAL_STEPS);
                break;
            }
        }

        const completedCard = wrapper.querySelector('.log-analysis');
        if (completedCard) {
            updateProgress(analysisStep, 'Step ' + analysisStep + '/' + TOTAL_STEPS);
        }

        if (wrapper.innerHTML.trim()) {
            logsDiv.insertAdjacentHTML('beforeend', wrapper.innerHTML);
        }

        logsDiv.scrollTop = logsDiv.scrollHeight;
    };

    eventSource.onerror = function(e) {
        console.error('SSE error:', e);
        eventSource.close();
        spinner.style.display = 'none';
        submitButton.disabled = false;
        document.getElementById('progress-wrapper').style.display = 'none';

        const emptyState = logsDiv.querySelector('.empty-state');
        if (emptyState) {
            emptyState.textContent = 'Connection closed. Processing may have completed.';
        }
    };

    eventSource.addEventListener('complete', function() {
        eventSource.close();
        spinner.style.display = 'none';
        submitButton.disabled = false;
        updateProgress(TOTAL_STEPS, 'Complete');
    });
}
