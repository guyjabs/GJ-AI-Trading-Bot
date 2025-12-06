// Activity Log Management
let currentActivity = null;
let activitySteps = [];

// Add detailed activity with steps
function addDetailedActivity(title, icon = 'ℹ️', type = 'info') {
    const log = document.getElementById('activityLog');
    const time = new Date().toLocaleTimeString();

    const activity = document.createElement('div');
    activity.className = `activity-item ${type} in-progress`;
    activity.id = `activity-${Date.now()}`;

    activity.innerHTML = `
        <div class="activity-header">
            <span class="activity-icon">${icon}</span>
            <span class="activity-title">${title}</span>
            <span class="activity-time">${time}</span>
        </div>
        <div class="activity-body">
            <div class="progress-container">
                <div class="progress-bar" style="width: 0%"></div>
            </div>
            <div class="progress-text">0%</div>
            <div class="steps-container"></div>
        </div>
    `;

    log.insertBefore(activity, log.firstChild);

    // Keep max 20 activities
    while (log.children.length > 20) {
        log.removeChild(log.lastChild);
    }

    currentActivity = activity;
    activitySteps = [];

    return activity.id;
}

// Add step to current activity
function addActivityStep(stepText, status = 'in-progress') {
    if (!currentActivity) return;

    const stepsContainer = currentActivity.querySelector('.steps-container');
    const step = document.createElement('div');
    step.className = `step ${status}`;

    let icon = '⏳';
    if (status === 'done') icon = '✅';
    else if (status === 'error') icon = '❌';
    else if (status === 'pending') icon = '⏸️';
    else if (status === 'detail') icon = '🔎';

    step.innerHTML = `
        <span class="step-icon">${icon}</span>
        <span>${stepText}</span>
    `;

    stepsContainer.appendChild(step);
    activitySteps.push({ text: stepText, status, element: step });

    return step;
}

// Update step status
function updateActivityStep(stepIndex, status, newText = null) {
    if (!currentActivity || stepIndex >= activitySteps.length) return;

    const step = activitySteps[stepIndex];
    step.status = status;
    step.element.className = `step ${status}`;

    let icon = '⏳';
    if (status === 'done') icon = '✅';
    else if (status === 'error') icon = '❌';
    else if (status === 'pending') icon = '⏸️';
    else if (status === 'detail') icon = '🔎';

    const text = newText || step.text;
    step.element.innerHTML = `
        <span class="step-icon">${icon}</span>
        <span>${text}</span>
    `;

    if (newText) step.text = newText;
}

// Update progress bar
function updateActivityProgress(percent) {
    if (!currentActivity) return;

    const progressBar = currentActivity.querySelector('.progress-bar');
    const progressText = currentActivity.querySelector('.progress-text');

    progressBar.style.width = `${percent}%`;
    progressText.textContent = `${Math.round(percent)}%`;
}

// Complete current activity
function completeActivity(success = true) {
    if (!currentActivity) return;

    currentActivity.classList.remove('in-progress');
    currentActivity.classList.add(success ? 'success' : 'error');

    const progressBar = currentActivity.querySelector('.progress-bar');
    progressBar.classList.add(success ? 'success' : 'error');
    progressBar.style.width = '100%';

    const progressText = currentActivity.querySelector('.progress-text');
    progressText.textContent = success ? '✓ Complete' : '✗ Failed';

    currentActivity = null;
    activitySteps = [];
}

// Trading cycle with detailed logging
async function logTradingCycle() {
    // Start trading cycle
    addDetailedActivity('Trading Cycle Started', '🔄', 'info');

    // Step 1: Market Check
    addActivityStep('Checking if market is open...', 'in-progress');
    await sleep(500);
    updateActivityStep(0, 'done', 'Market status: Open ✓');
    updateActivityProgress(10);

    // Step 2: Account Info
    addActivityStep('Fetching account information...', 'in-progress');
    await sleep(800);
    updateActivityStep(1, 'done', 'Account info retrieved ✓');
    updateActivityProgress(20);

    // Step 3: Risk Check
    addActivityStep('Running risk management checks...', 'in-progress');
    await sleep(600);
    updateActivityStep(2, 'done', 'Portfolio health: Good ✓');
    updateActivityProgress(30);

    // Step 4: Get Portfolio
    addActivityStep('Loading current portfolio positions...', 'in-progress');
    await sleep(700);
    updateActivityStep(3, 'done', 'Portfolio loaded: 5 positions ✓');
    updateActivityProgress(40);

    // Step 5: Get Crypto
    addActivityStep('Fetching crypto positions...', 'in-progress');
    await sleep(500);
    updateActivityStep(4, 'done', 'Crypto positions: 2 assets ✓');
    updateActivityProgress(50);

    // Step 6: Run Screener
    addActivityStep('Running multi-strategy screener...', 'in-progress');
    await sleep(1200);
    updateActivityStep(5, 'done', 'Screener complete: 15 candidates ✓');
    updateActivityProgress(60);

    // Step 7: Gather Data
    addActivityStep('Gathering market data for candidates...', 'in-progress');
    await sleep(1500);
    updateActivityStep(6, 'done', 'Market data collected ✓');
    updateActivityProgress(70);

    // Step 8: AI Analysis
    addActivityStep('Running AI analysis on candidates...', 'in-progress');
    await sleep(2000);
    updateActivityStep(7, 'done', 'AI analysis complete: 3 decisions ✓');
    updateActivityProgress(85);

    // Step 9: Execute Trades
    addActivityStep('Executing trading decisions...', 'in-progress');
    await sleep(1000);
    updateActivityStep(8, 'done', 'Trades executed: 2 buy, 1 sell ✓');
    updateActivityProgress(95);

    // Step 10: Update ML
    addActivityStep('Updating ML engine...', 'in-progress');
    await sleep(500);
    updateActivityStep(9, 'done', 'ML engine updated ✓');
    updateActivityProgress(100);

    // Complete
    completeActivity(true);
}

// Helper sleep function
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Export functions for use in main app.js
window.activityLog = {
    addDetailedActivity,
    addActivityStep,
    updateActivityStep,
    updateActivityProgress,
    completeActivity,
    logTradingCycle,
    toggleFullScreen
};

// Toggle Full Screen Mode
function toggleFullScreen() {
    const sidebar = document.querySelector('.activity-sidebar');
    const btn = document.querySelector('.maximize-btn');

    sidebar.classList.toggle('fullscreen');

    if (sidebar.classList.contains('fullscreen')) {
        btn.innerHTML = '⤡'; // Shrink icon
        btn.title = "Exit Full Screen";
    } else {
        btn.innerHTML = '⤢'; // Expand icon
        btn.title = "Full Screen";
    }
}
