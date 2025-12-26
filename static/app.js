// WebSocket connection
let socket = null;

// State
let botRunning = false;
let currentMode = 'demo';
let currentView = 'strategy';
let portfolioChart = null;
let researchInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');
    fetch('/api/debug_log?msg=DOMContentLoaded');

    // Initialize Socket.IO safely
    if (typeof io !== 'undefined') {
        socket = io();
    } else {
        console.error('Socket.IO not loaded');
        // Mock socket to prevent errors
        socket = {
            on: () => { },
            emit: () => { }
        };
    }

    // Setup listeners FIRST so buttons work even if charts fail
    try {
        setupEventListeners();
        console.log('Event listeners setup');
    } catch (e) {
        console.error('Error setting up event listeners:', e);
    }

    // Initialize charts
    try {
        if (typeof Chart !== 'undefined') {
            initializeCharts();
        } else {
            console.error('Chart.js not loaded');
        }
    } catch (e) {
        console.error('Error initializing charts:', e);
    }

    // Request initial data
    try {
        requestInitialData();
    } catch (e) {
        console.error('Error requesting initial data:', e);
    }
});

// Setup event listeners
function setupEventListeners() {
    console.log('Setting up event listeners...');
    fetch('/api/debug_log?msg=setupEventListeners_Start');
    // Bot control buttons
    document.getElementById('startBtn').addEventListener('click', startBot);
    document.getElementById('stopBtn').addEventListener('click', stopBot);

    // Mode selector
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            setMode(e.target.dataset.mode);
        });
    });

    // View navigation
    document.querySelectorAll('.nav-link').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Check for disabled attribute or class if needed, or get dataset from currentTarget
            const view = e.currentTarget.dataset.view;
            if (view) switchView(view);
        });
    });

    // Force research button
    const forceResearchBtn = document.getElementById('forceResearchBtn');
    if (forceResearchBtn) {
        forceResearchBtn.addEventListener('click', forceResearch);
    }

    // Broker tabs
    document.querySelectorAll('.broker-tab').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchBroker(e.target.dataset.broker);
        });
    });

    // Watchlist & Alerts
    const addStockBtn = document.getElementById('addStockBtn');
    if (addStockBtn) addStockBtn.addEventListener('click', addToWatchlist);


    const createAlertBtn = document.getElementById('createAlertBtn');
    if (createAlertBtn) createAlertBtn.addEventListener('click', createAlert);

    // Save Config Button
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    if (saveConfigBtn) saveConfigBtn.addEventListener('click', saveMetricsConfig);

    // Socket events
    socket.on('connect', () => {
        console.log('Connected to server');
        addLog('Connected to server', 'info');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        addLog('Disconnected from server', 'warning');
    });

    socket.on('status_update', handleStatusUpdate);
    socket.on('log_message', handleLogMessage);
    socket.on('portfolio_update', handlePortfolioUpdate);
    socket.on('trade_executed', handleTradeExecuted);
    socket.on('research_log', function (data) {
        const logContainer = document.getElementById('researchLog');
        if (!logContainer) return;

        // Clear empty state if present
        const emptyState = logContainer.querySelector('.empty-state');
        if (emptyState) emptyState.remove();

        const entry = document.createElement('div');
        entry.style.marginBottom = '8px';
        entry.style.padding = '8px';
        entry.style.borderLeft = '3px solid #444';
        entry.style.background = 'rgba(255,255,255,0.05)';

        const timestamp = new Date().toLocaleTimeString();

        if (data.type === 'info') {
            entry.style.borderLeftColor = '#3498db';
            entry.innerHTML = `<span style="color:#aaa">[${timestamp}]</span> ℹ️ ${data.message}`;
        } else if (data.type === 'success') {
            entry.style.borderLeftColor = '#2ecc71';
            entry.innerHTML = `<span style="color:#aaa">[${timestamp}]</span> ✅ ${data.message}`;
        } else if (data.type === 'article') {
            entry.style.borderLeftColor = '#9b59b6';
            entry.innerHTML = `
                <div style="color:#aaa; font-size:0.8em">[${timestamp}] 📰 Article ${data.index}/${data.total}</div>
                <div style="color:#fff; font-weight:bold">${data.title}</div>
                <div style="color:#aaa; font-size:0.9em">Source: ${data.source}</div>
                <div style="color:#ccc; font-style:italic; margin-top:4px">${data.summary.substring(0, 100)}...</div>
            `;
        } else if (data.type === 'progress') {
            entry.style.borderLeftColor = '#3498db';
            entry.style.background = 'rgba(52, 152, 219, 0.1)';
            entry.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#fff; font-weight:bold;">${data.message}</span>
                    <span style="color:#3498db;">${data.percent}%</span>
                </div>
                <div style="width:100%; height:4px; background:#333; margin-top:5px; border-radius:2px;">
                    <div style="width:${data.percent}%; height:100%; background:#3498db; border-radius:2px; transition:width 0.3s ease;"></div>
                </div>
            `;
        } else if (data.type === 'detail') {
            entry.style.borderLeftColor = '#95a5a6';
            entry.style.padding = '4px 8px'; // Compact padding
            entry.innerHTML = `<span style="color:#888; font-family:monospace;">> ${data.message}</span>`;
        } else if (data.type === 'trend') {
            entry.style.borderLeftColor = '#e67e22';
            entry.innerHTML = `
                <div style="color:#aaa; font-size:0.8em">[${timestamp}] 📈 Trend Detected</div>
                <div style="color:#fff; font-weight:bold">${data.name}</div>
                <div style="color:#aaa">Type: ${data.trend_type} | Mentions: ${data.count}</div>
            `;
        } else if (data.type === 'insight') {
            entry.style.borderLeftColor = '#f1c40f';
            entry.innerHTML = `
                <div style="color:#aaa; font-size:0.8em">[${timestamp}] 💡 Insight</div>
                <div style="color:#fff">${data.text}</div>
                <div style="color:#aaa">Confidence: ${(data.confidence * 100).toFixed(0)}%</div>
            `;
        }

        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
    });

    socket.on('bot_status', handleBotStatus);
    socket.on('decision_update', handleDecisionUpdate);

    // Activity logging events
    socket.on('activity_start', (data) => {
        if (window.activityLog) {
            window.activityLog.addDetailedActivity(data.title, data.icon, data.type);
        }
    });

    socket.on('activity_step', (data) => {
        if (window.activityLog) {
            window.activityLog.addActivityStep(data.text, data.status);
        }
    });

    socket.on('activity_step_update', (data) => {
        if (window.activityLog) {
            window.activityLog.updateActivityStep(data.index, data.status, data.text);
        }
    });

    socket.on('activity_progress', (data) => {
        if (window.activityLog) {
            window.activityLog.updateActivityProgress(data.percent);
        }
    });

    socket.on('activity_complete', (data) => {
        if (window.activityLog) {
            window.activityLog.completeActivity(data.success);
        }
    });
}

// Switch between views
// Switch between views
function switchView(view) {
    try {
        console.log('Switching to view:', view);
        fetch(`/api/debug_log?msg=switchView_${view}`);

        currentView = view;

        // 1. Update tab buttons
        document.querySelectorAll('.nav-link').forEach(tab => {
            // Remove active class from all
            tab.classList.remove('active');
            // Add active class if it matches the current view
            if (tab.dataset.view === view) {
                tab.classList.add('active');
            }
        });

        // 2. Hide ALL views first
        const allViews = ['strategy', 'trading', 'day-trading', 'research', 'readme', 'metrics', 'scalping', 'learning'];
        allViews.forEach(v => {
            const el = document.getElementById(`${v}-view`);
            if (el) {
                el.style.display = 'none';
                el.classList.remove('active'); // Ensure class logic matches strictly
            }
        });

        // 3. Show the selected view
        const targetView = document.getElementById(`${view}-view`);
        if (targetView) {
            targetView.style.display = 'block';
            targetView.classList.add('active');
        } else {
            console.error(`View element #${view}-view not found!`);
        }

        // 4. Trigger specific view loaders
        if (view === 'research') {
            loadResearchData();
            if (researchInterval) clearInterval(researchInterval);
            researchInterval = setInterval(loadResearchData, 30000);
        } else if (view === 'day-trading') {
            loadDayTradingData();
            if (researchInterval) clearInterval(researchInterval);
            researchInterval = setInterval(loadDayTradingData, 5000);
        } else if (view === 'scalping') {
            loadScalpingData();
            if (researchInterval) clearInterval(researchInterval);
            researchInterval = setInterval(loadScalpingData, 1000); // Fast polling
        } else if (view === 'trading') {
            loadTradingDashboardStats();
            if (researchInterval) clearInterval(researchInterval);
            researchInterval = setInterval(loadTradingDashboardStats, 2000);
        } else if (view === 'strategy') {
            loadStrategyHistory();
        } else if (view === 'metrics') {
            loadMetricsConfig();
            if (researchInterval) {
                clearInterval(researchInterval);
                researchInterval = null;
            }
        }
    } catch (e) {
        console.error('Error switching view:', e);
        fetch(`/api/debug_log?msg=ERROR_switchView_${e.message}`);
    }
}


// Load Strategy History
function loadStrategyHistory() {
    fetch('/api/strategy/history')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('strategy-timeline');
            if (!data.history || data.history.length === 0) {
                container.innerHTML = '<div class="timeline-item">No strategy history yet.</div>';
                return;
            }

            container.innerHTML = data.history.map(item => {
                const date = new Date(item.date).toLocaleString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                });
                const weights = item.weights || {};
                const weightsStr = Object.entries(weights)
                    .map(([k, v]) => `<span style="margin-right: 15px;"><strong>${k.charAt(0).toUpperCase() + k.slice(1)}:</strong> ${(v * 100).toFixed(0)}%</span>`)
                    .join('');

                const color = item.action === 'updated' ? 'var(--success)' : 'var(--accent-primary)';

                return `
                    <div class="timeline-item" style="border-left: 2px solid ${color}; padding-left: 15px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                            <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary);">
                                <span style="color: ${color}; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 0.5px; margin-right: 8px;">${item.action}</span>
                                Strategy Adjustment
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${date}</div>
                        </div>
                        <div style="margin-bottom: 6px; color: var(--text-secondary); font-size: 0.85rem; line-height: 1.4;">${item.reason}</div>
                        <div style="background: var(--bg-tertiary); padding: 6px 10px; border-radius: 4px; font-size: 0.8rem; color: var(--text-primary); border: 1px solid var(--border-color); display: flex;">
                            ${weightsStr}
                        </div>
                    </div>
                `;
            }).join('');

            // Render Chart
            renderStrategyChart(data.history);
        })
        .catch(error => console.error('Error loading strategy history:', error));
}

let strategyChartInstance = null;

function renderStrategyChart(history) {
    const ctx = document.getElementById('strategyChart').getContext('2d');

    // Destroy existing chart if it exists
    if (strategyChartInstance) {
        strategyChartInstance.destroy();
    }

    // Process data for chart (reverse to show oldest to newest)
    const sortedHistory = [...history].reverse();
    const labels = sortedHistory.map(item => new Date(item.date).toLocaleDateString());

    const momentumData = sortedHistory.map(item => (item.weights?.momentum || 0) * 100);
    const growthData = sortedHistory.map(item => (item.weights?.growth || 0) * 100);
    const valueData = sortedHistory.map(item => (item.weights?.value || 0) * 100);

    strategyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Momentum',
                    data: momentumData,
                    borderColor: '#0066cc', // accent-primary
                    backgroundColor: 'rgba(0, 102, 204, 0.05)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Growth',
                    data: growthData,
                    borderColor: '#28a745', // success
                    backgroundColor: 'rgba(40, 167, 69, 0.05)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Value',
                    data: valueData,
                    borderColor: '#fd7e14', // warning
                    backgroundColor: 'rgba(253, 126, 20, 0.05)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#212529',
                    bodyColor: '#212529',
                    borderColor: '#dee2e6',
                    borderWidth: 1,
                    padding: 10,
                    boxPadding: 4,
                    callbacks: {
                        afterBody: function (context) {
                            const index = context[0].dataIndex;
                            const item = sortedHistory[index];
                            return `\nReason: ${item.reason}`;
                        }
                    }
                },
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        font: {
                            size: 11,
                            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif"
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: '#f1f3f5'
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    },
                    title: {
                        display: true,
                        text: 'Allocation (%)',
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    });
}

// Load Day Trading Data
async function loadDayTradingData() {
    try {
        const response = await fetch('/api/day-trading/dashboard');
        const data = await response.json();

        // Update Stats
        document.getElementById('dayPnL').textContent = data.pnl_formatted;
        document.getElementById('dayPnL').className = data.pnl >= 0 ? 'value positive' : 'value negative';
        document.getElementById('dayTradesCount').textContent = data.trades_count;
        document.getElementById('dayWinRate').textContent = data.win_rate;
        document.getElementById('spyTrend').textContent = data.market_context.spy_trend;

        // Update Active Trades
        const tbody = document.getElementById('dayTradesBody');
        if (data.active_trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No active day trades</td></tr>';
        } else {
            tbody.innerHTML = data.active_trades.map(trade => `
                <tr>
                    <td>${trade.symbol}</td>
                    <td>$${trade.entry_price.toFixed(2)}</td>
                    <td>$${trade.current_price.toFixed(2)}</td>
                    <td>$${trade.stop_loss.toFixed(2)}</td>
                    <td>$${trade.target.toFixed(2)}</td>
                    <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">$${trade.pnl.toFixed(2)}</td>
                    <td>${trade.r_multiple.toFixed(2)}R</td>
                </tr>
            `).join('');
        }

        // Update Scanner
        updateScannerList('gappersList', data.scanner.gappers);
        updateScannerList('momentumList', data.scanner.momentum);

    } catch (error) {
        console.error('Error loading day trading data:', error);
    }
}

function updateScannerList(elementId, items) {
    const list = document.getElementById(elementId);
    if (!items || items.length === 0) {
        list.innerHTML = '<li class="empty-state">No candidates found</li>';
        return;
    }

    list.innerHTML = items.map(item => `
        <li class="scanner-item">
            <span class="symbol">${item.symbol}</span>
            <span class="detail">${item.detail}</span>
            <button class="action-btn" onclick="analyzeSymbol('${item.symbol}')">Analyze</button>
        </li>
    `).join('');
}

// Load research data
async function loadResearchData() {
    try {
        // Fetch summary
        const summary = await fetch('/api/research/summary').then(r => r.json());
        updateResearchSummary(summary);

        // Fetch predictions
        const predictions = await fetch('/api/research/predictions').then(r => r.json());
        updatePredictions(predictions.predictions || []);

        // Fetch trends
        const trends = await fetch('/api/research/trends').then(r => r.json());
        updateTrends(trends.trends || []);

        // Fetch news
        const news = await fetch('/api/research/news').then(r => r.json());
        updateNews(news.articles || []);
    } catch (error) {
        console.error('Error loading research data:', error);
    }
}

// Update research summary
function updateResearchSummary(summary) {
    if (!summary) return;

    // Market sentiment
    const sentiment = summary.overall_sentiment || {};
    const avgSentiment = sentiment.average || 0;
    document.getElementById('marketSentiment').textContent = avgSentiment.toFixed(2);

    const breakdown = `${sentiment.positive || 0} pos / ${sentiment.negative || 0} neg`;
    document.getElementById('sentimentBreakdown').textContent = breakdown;

    // News volume
    document.getElementById('newsVolume').textContent = summary.news_count || 0;

    // Prediction accuracy
    const accuracy = summary.prediction_accuracy || {};
    document.getElementById('predictionAccuracy').textContent =
        accuracy.accuracy ? `${accuracy.accuracy.toFixed(1)}%` : '--%';
}

// Update predictions list
function updatePredictions(predictions) {
    const container = document.getElementById('predictionsList');

    if (!predictions || predictions.length === 0) {
        container.innerHTML = '<div class="empty-state">No active predictions</div>';
        return;
    }

    container.innerHTML = predictions.map(pred => {
        const confidence = pred.metadata?.confidence || 0;
        const highConf = confidence > 0.7 ? 'high-confidence' : '';
        const symbol = pred.metadata?.symbol || 'N/A';
        const direction = pred.metadata?.direction || 'unknown';

        return `
            <div class="prediction-item ${highConf}">
                <div class="prediction-header">
                    <span><strong>${symbol}</strong> - ${direction.toUpperCase()}</span>
                    <span>Confidence: ${(confidence * 100).toFixed(0)}%</span>
                </div>
                <div class="prediction-text">${pred.text}</div>
            </div>
        `;
    }).join('');
}

// Update trends list
function updateTrends(trends) {
    const container = document.getElementById('trendsList');

    if (!trends || trends.length === 0) {
        container.innerHTML = '<div class="empty-state">No trends detected</div>';
        return;
    }

    container.innerHTML = trends.slice(0, 10).map(trend => {
        const type = trend.metadata?.type || 'general';
        const strength = trend.metadata?.strength || 0;

        return `
            <div class="trend-item">
                <div class="trend-header">
                    <span>${type}</span>
                    <span>Strength: ${(strength * 100).toFixed(0)}%</span>
                </div>
                <div class="trend-text">${trend.text}</div>
            </div>
        `;
    }).join('');
}

// Update news feed
function updateNews(articles) {
    const container = document.getElementById('newsFeed');

    if (!articles || articles.length === 0) {
        container.innerHTML = '<div class="empty-state">No news available</div>';
        return;
    }

    container.innerHTML = articles.slice(0, 12).map(article => {
        const sentiment = article.sentiment || 0;
        const sentimentClass = sentiment > 0.1 ? 'positive' : sentiment < -0.1 ? 'negative' : 'neutral';
        const sentimentLabel = sentiment > 0.1 ? 'Positive' : sentiment < -0.1 ? 'Negative' : 'Neutral';

        const date = new Date(article.published_at || article.datetime);
        const timeAgo = getTimeAgo(date);

        return `
            <div class="news-item">
                <div class="news-meta">
                    <span>${article.source || 'Unknown'}</span>
                    <span class="sentiment-badge sentiment-${sentimentClass}">${sentimentLabel}</span>
                </div>
                <a href="${article.url}" target="_blank" class="news-title">${article.title}</a>
                <div class="news-summary">${article.summary || article.description || ''}</div>
                <div class="news-meta" style="margin-top: 6px;">
                    <span>${timeAgo}</span>
                    <span>${article.tickers?.join(', ') || ''}</span>
                </div>
            </div>
        `;
    }).join('');
}

// Helper: Get time ago string
function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}



// === Custom Bot Asset Management ===
let customBotAssets = [];

// ==========================================
// SIMULATOR LOGIC
// ==========================================

let simChartInstance = null;

function runSimulation() {
    const startDetails = {
        start_date: document.getElementById('simStartDate').value,
        end_date: document.getElementById('simEndDate').value,
        initial_cash: document.getElementById('simCapital').value,
        universe: document.getElementById('simUniverse').value
    };

    if (!startDetails.start_date || !startDetails.end_date) {
        showToast('Please select a date range', 'error');
        return;
    }

    const btn = document.getElementById('runSimulationBtn');
    btn.disabled = true;
    btn.innerHTML = '⏳ Running Simulation...';

    // Show loading state or hide results
    document.getElementById('simResults').style.display = 'none';

    fetch('/api/simulate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(startDetails)
    })
        .then(response => response.json())
        .then(data => {
            btn.disabled = false;
            btn.innerHTML = '▶ Run Simulation';

            if (data.error) {
                showToast('Simulation Failed: ' + data.error, 'error');
                return;
            }

            renderSimulationResults(data);
        })
        .catch(error => {
            console.error('Simulation error:', error);
            showToast('Error running simulation', 'error');
            btn.disabled = false;
            btn.innerHTML = '▶ Run Simulation';
        });
}

function renderSimulationResults(data) {
    const resultsDiv = document.getElementById('simResults');
    resultsDiv.style.display = 'block';

    // Update Stats
    const finalBal = data.final_balance || 0;
    const initial = parseFloat(document.getElementById('simCapital').value);
    const profit = finalBal - initial;
    const profitPct = (profit / initial) * 100;

    document.getElementById('simFinalBalance').textContent = '$' + finalBal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    const returnEl = document.getElementById('simReturn');
    returnEl.textContent = (profitPct >= 0 ? '+' : '') + profitPct.toFixed(2) + '%';
    returnEl.className = 'value ' + (profitPct >= 0 ? 'text-success' : 'text-danger'); // Assuming bootstrap-like classes or global styles

    document.getElementById('simTrades').textContent = data.trades || 0;

    // Render Chart
    const ctx = document.getElementById('simChart').getContext('2d');

    if (simChartInstance) {
        simChartInstance.destroy();
    }

    // Prepare Data
    const equityCurve = data.equity_curve || [];
    const labels = equityCurve.map(p => new Date(p.timestamp).toLocaleDateString());
    const values = equityCurve.map(p => p.equity);

    simChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Portfolio Equity',
                data: values,
                borderColor: profitPct >= 0 ? '#2ecc71' : '#e74c3c',
                backgroundColor: profitPct >= 0 ? 'rgba(46, 204, 113, 0.1)' : 'rgba(231, 76, 60, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 10 }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return '$' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            }
        }
    });

    // Scroll to results
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

// Add event listener manually if setupEventListeners didn't catch it yet (it runs on load)
// But we can add it safely here again or rely on the init.
document.addEventListener('DOMContentLoaded', () => {
    const simBtn = document.getElementById('runSimulationBtn');
    if (simBtn) {
        simBtn.addEventListener('click', runSimulation);
    }
});

function renderAssetTable() {
    const tbody = document.getElementById('asset-list-body');
    const emptyState = document.getElementById('empty-state');
    const badge = document.getElementById('asset-count');

    tbody.innerHTML = '';

    if (customBotAssets.length === 0) {
        emptyState.style.display = 'block';
    } else {
        emptyState.style.display = 'none';
        customBotAssets.forEach((symbol, index) => {
            const row = document.createElement('tr');
            row.className = 'asset-row';
            row.innerHTML = `
                <td><strong>${symbol}</strong></td>
                <td class="text-right">
                    <button class="btn-delete" onclick="deleteAsset(${index})" title="Remove">
                        🗑️
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    badge.innerText = `${customBotAssets.length} Asset${customBotAssets.length !== 1 ? 's' : ''}`;
}

function handleAssetInput(event) {
    if (event.key === 'Enter') {
        addAsset();
    }
}

function addAsset() {
    const input = document.getElementById('new-asset-symbol');
    let symbol = input.value.trim().toUpperCase();

    if (!symbol) return;

    // Auto-append /USD if missing
    if (!symbol.includes('/') && !symbol.includes('-')) {
        symbol += '/USD';
    }

    if (customBotAssets.includes(symbol)) {
        showToast('Asset already exists!', 'error');
        return;
    }

    customBotAssets.push(symbol);
    renderAssetTable();
    syncAssetsToBackend();
    input.value = '';
    showToast(`Added ${symbol}`, 'success');
}

function deleteAsset(index) {
    const removed = customBotAssets.splice(index, 1);
    renderAssetTable();
    syncAssetsToBackend();
    showToast(`Removed ${removed}`, 'success');
}

function syncAssetsToBackend() {
    fetch('/api/config/update_custom_bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: customBotAssets }),
    })
        .catch(error => {
            console.error('Error syncing assets:', error);
            showToast('Sync failed', 'error');
        });
}

// === Metrics Configuration ===

// Save Custom Bot Config (Deprecated by dynamic sync)
// function saveCustomBotConfig() {
//     const input = document.getElementById('custom-bot-symbols').value;
//     const symbols = input.split(',').map(s => s.trim()).filter(s => s.length > 0);

//     // Basic validation: Ensure /USD suffix if missing (optional helper)
//     const formattedSymbols = symbols.map(s => s.toUpperCase().includes('/') ? s.toUpperCase() : `${s.toUpperCase()}/USD`);

//     if (formattedSymbols.length === 0) {
//         showToast('Please enter at least one symbol', 'error');
//         return;
//     }

//     fetch('/api/config/update_custom_bot', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({ symbols: formattedSymbols }),
//     })
//         .then(response => response.json())
//         .then(data => {
//             if (data.status === 'success') {
//                 showToast('Custom Bot Updated! 🤖', 'success');
//             } else {
//                 showToast('Error: ' + data.message, 'error');
//             }
//         })
//         .catch(error => {
//             console.error('Error:', error);
//             showToast('Error updating custom bot', 'error');
//         });
// }

async function loadMetricsConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        const config = data.config;

        if (!config) return;

        // Metrics...
        if (config.metrics) {
            const metrics = config.metrics;
            // Momentum
            if (document.getElementById('cfg_mom_min_gain'))
                document.getElementById('cfg_mom_min_gain').value = metrics.momentum?.min_top_gainers_pct || 5.0;
            if (document.getElementById('cfg_mom_min_vol'))
                document.getElementById('cfg_mom_min_vol').value = metrics.momentum?.volume_ratio || 1.5;

            // Value
            if (document.getElementById('cfg_val_max_peg'))
                document.getElementById('cfg_val_max_peg').value = metrics.value?.max_peg_ratio || 2.0;
            if (document.getElementById('cfg_val_industry'))
                document.getElementById('cfg_val_industry').checked = metrics.value?.check_industry_pe || false;
            if (document.getElementById('cfg_val_pe_industry'))
                document.getElementById('cfg_val_pe_industry').checked = metrics.value?.industry_filter || false;

            // Populate Asset Table
            if (metrics.crypto_bots) {
                const customBot = metrics.crypto_bots.find(b => b.name === 'Custom');
                if (customBot && customBot.symbols) {
                    customBotAssets = customBot.symbols;
                    renderAssetTable();
                }
            }

            // Growth
            if (document.getElementById('cfg_growth_min_eps'))
                document.getElementById('cfg_growth_min_eps').value = metrics.growth?.min_earnings_growth || 15.0;
            if (document.getElementById('cfg_growth_industries'))
                document.getElementById('cfg_growth_industries').value = (metrics.growth?.trending_industries || []).join('\n');
        } else {
            // Fallback for older config structure if metrics object is not present
            // Momentum
            if (document.getElementById('cfg_mom_min_gain'))
                document.getElementById('cfg_mom_min_gain').value = config.momentum?.min_top_gainers_pct || 5.0;
            if (document.getElementById('cfg_mom_min_vol'))
                document.getElementById('cfg_mom_min_vol').value = config.momentum?.volume_ratio || 1.5;

            // Value
            if (document.getElementById('cfg_val_max_peg'))
                document.getElementById('cfg_val_max_peg').value = config.value?.max_peg_ratio || 2.0;
            if (document.getElementById('cfg_val_industry'))
                document.getElementById('cfg_val_industry').checked = config.value?.check_industry_pe || false;

            // Custom Bot
            if (config.crypto_bots) {
                const customBot = config.crypto_bots.find(b => b.name === 'Custom');
                if (customBot && customBot.symbols) {
                    customBotAssets = customBot.symbols;
                    renderAssetTable();
                }
            }

            // Growth
            if (document.getElementById('cfg_growth_min_eps'))
                document.getElementById('cfg_growth_min_eps').value = config.growth?.min_earnings_growth || 15.0;
            if (document.getElementById('cfg_growth_industries'))
                document.getElementById('cfg_growth_industries').value = (config.growth?.trending_industries || []).join('\n');
        }

    } catch (error) {
        console.error('Error loading config:', error);
        addLog('Failed to load strategy config', 'error');
    }
}

async function saveMetricsConfig() {
    const btn = document.getElementById('saveConfigBtn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Saving...';

    // Gather values
    const configUpdate = {
        momentum: {
            min_top_gainers_pct: parseFloat(document.getElementById('cfg_mom_min_gain').value),
            volume_ratio: parseFloat(document.getElementById('cfg_mom_min_vol').value)
        },
        value: {
            max_peg_ratio: parseFloat(document.getElementById('cfg_val_max_peg').value),
            check_industry_pe: document.getElementById('cfg_val_industry').checked
        },
        growth: {
            min_earnings_growth: parseFloat(document.getElementById('cfg_growth_min_eps').value),
            trending_industries: document.getElementById('cfg_growth_industries').value
                .split('\n')
                .map(s => s.trim())
                .filter(s => s.length > 0)
        }
    };

    try {
        const response = await fetch('/api/config/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configUpdate)
        });

        const result = await response.json();

        if (result.status === 'success') {
            addLog('Strategy configuration saved', 'success');
            btn.textContent = '✅ Saved';
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Error saving config:', error);
        addLog(`Error saving config: ${error.message}`, 'error');
        btn.textContent = '❌ Error';
    } finally {
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    }
}

// Force research with selected sources
async function forceResearch() {
    const btn = document.getElementById('forceResearchBtn');
    const originalText = btn.textContent;
    if (btn) btn.disabled = true;

    const sources = {
        newsapi: document.getElementById('sourceNewsAPI').checked,
        alphavantage: document.getElementById('sourceAlphaVantage').checked,
        finnhub: document.getElementById('sourceFinnhub').checked
    };

    try {
        const response = await fetch('/api/research/force', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sources })
        });

        if (!response.ok) {
            const result = await response.json();
            throw new Error(result.error || 'Research failed');
        }

        // Reload research data
        setTimeout(() => {
            loadResearchData();
        }, 1000);

        btn.textContent = '✅ Started';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);

    } catch (error) {
        console.error('Force research error:', error);
        btn.textContent = '❌ Error';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 3000);
    } finally {
        btn.disabled = false;
    }
}

// Request initial data
function requestInitialData() {
    socket.emit('get_status');
    socket.emit('get_portfolio');

    // HTTP Fallback to ensure data loads
    fetch('/api/status/data')
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                console.log("HTTP Status Data:", data);
                updateDashboard(data);
            }
        })
        .catch(err => console.error("HTTP Status Error:", err));
}

// Start bot
function startBot() {
    socket.emit('start_bot', { mode: currentMode });
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
}

// Stop bot
function stopBot() {
    socket.emit('stop_bot');
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
}

// Set mode
function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

    // Update mode badge
    document.getElementById('currentMode').textContent = mode.toUpperCase();
}

// Handle status update
function handleStatusUpdate(data) {
    updateDashboard(data);
}

// Handle log message
function handleLogMessage(data) {
    addLog(data.message, data.level, data.details);
}

// Handle portfolio update
function handlePortfolioUpdate(data) {
    updatePortfolio(data.portfolio);
    updatePortfolioChart(data.portfolio);
}

// Handle trade executed
function handleTradeExecuted(data) {
    addTradeToHistory(data);
    addLog(`${data.decision.toUpperCase()}: ${data.symbol} x${data.quantity}`,
        data.result === 'success' ? 'success' : 'error');
}

// Handle bot status
function handleBotStatus(data) {
    botRunning = data.running;
    updateBotStatus(data.running);

    if (data.mode) {
        setMode(data.mode);
    }
}

// Handle decision update
function handleDecisionUpdate(event) {
    const feed = document.getElementById('decisionFeed');
    const card = document.createElement('div');
    const time = new Date(event.timestamp).toLocaleTimeString();

    let icon = 'ℹ️';
    let title = 'Update';
    let body = '';
    let typeClass = 'info';

    if (event.type === 'screener') {
        icon = '🔍';
        title = 'Screener Results';
        typeClass = 'screener';
        const stocks = event.data.stocks.join(', ') || 'None';
        const crypto = event.data.crypto.join(', ') || 'None';
        body = `
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <div class="tag">Stocks: ${stocks}</div>
                <div class="tag">Crypto: ${crypto}</div>
            </div>
            <div style="margin-top: 5px; font-size: 0.9em; color: var(--text-muted);">
                Scanned ${event.data.count} assets
            </div>
        `;
    } else if (event.type === 'risk_check') {
        icon = '🛡️';
        title = 'Risk Check';
        typeClass = 'risk';
        body = `Checking portfolio health for ${event.data.portfolio_size} positions...`;
    } else if (event.type === 'ai_decision') {
        icon = '🤖';
        title = `AI Analysis: ${event.data.symbol}`;
        const decision = event.data.decision.toUpperCase();
        typeClass = decision === 'BUY' ? 'success' : (decision === 'SELL' ? 'warning' : 'neutral');
        body = `
            <div style="font-weight: bold; margin-bottom: 4px;">${decision} ${event.data.quantity} shares</div>
            <div style="font-style: italic; color: var(--text-muted);">"${event.data.reasoning}"</div>
        `;
    }

    card.className = `decision-card ${typeClass}`;
    card.innerHTML = `
        <div class="card-header">
            <span class="icon">${icon}</span>
            <span class="title">${title}</span>
            <span class="time">${time}</span>
        </div>
        <div class="card-body">${body}</div>
    `;

    feed.insertBefore(card, feed.firstChild);

    // Keep max 50 cards
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }
}

// Update dashboard
function updateDashboard(data) {
    if (data.portfolio_value !== undefined) {
        document.getElementById('portfolioValue').textContent =
            `$${data.portfolio_value.toFixed(2)}`;
    }

    if (data.buying_power !== undefined) {
        document.getElementById('buyingPower').textContent =
            `$${data.buying_power.toFixed(2)}`;
    }

    if (data.total_pl !== undefined) {
        const plElement = document.getElementById('totalPL');
        plElement.textContent = `$${Math.abs(data.total_pl).toFixed(2)}`;

        const changeElement = document.getElementById('plChange');
        if (changeElement) {
            changeElement.textContent = `${data.total_pl >= 0 ? '+' : '-'}${Math.abs(data.total_pl).toFixed(2)}`;
            changeElement.className = `stat-change ${data.total_pl >= 0 ? 'positive' : 'negative'}`;
        }
    }

    // Update header stats
    const balance = (data.portfolio_value || 0) + (data.buying_power || 0);
    document.getElementById('headerBalance').textContent = `$${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    if (data.total_pl !== undefined) {
        const plPercent = balance > 0 ? (data.total_pl / balance * 100) : 0;
        const headerPL = document.getElementById('headerPL');
        headerPL.textContent = `${data.total_pl >= 0 ? '+' : ''}$${data.total_pl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${data.total_pl >= 0 ? '+' : ''}${plPercent.toFixed(2)}%)`;
        headerPL.className = data.total_pl >= 0 ? 'positive' : 'negative';
    }
}

// Update portfolio table
function updatePortfolio(portfolio) {
    const tbody = document.getElementById('portfolioBody');
    tbody.innerHTML = '';

    if (!portfolio || portfolio.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No positions</td></tr>';
        return;
    }

    // Update ticker bar with portfolio stocks
    updateTickerBar(portfolio.slice(0, 5));

    portfolio.forEach(stock => {
        const row = document.createElement('tr');
        const pl = (stock.current_price - stock.average_buy_price) * stock.quantity;
        const plPercent = ((stock.current_price - stock.average_buy_price) / stock.average_buy_price * 100);

        const icon = stock.type === 'crypto' ? '🪙' : '📈';

        row.innerHTML = `
            <td><span class="symbol">${icon} ${stock.symbol}</span></td>
            <td>${stock.quantity.toFixed(4)}</td>
            <td>$${stock.current_price.toFixed(2)}</td>
            <td>$${stock.average_buy_price.toFixed(2)}</td>
            <td class="${pl >= 0 ? 'positive' : 'negative'}">
                $${pl.toFixed(2)} (${plPercent.toFixed(2)}%)
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Update ticker bar
function updateTickerBar(stocks) {
    const tickerBar = document.getElementById('tickerBar');
    if (!tickerBar || !stocks || stocks.length === 0) return;

    tickerBar.innerHTML = stocks.map(stock => {
        const pl = (stock.current_price - stock.average_buy_price) / stock.average_buy_price * 100;
        const changeClass = pl >= 0 ? 'positive' : 'negative';

        return `
            <div class="ticker-item">
                <span class="ticker-symbol">${stock.symbol}</span>
                <span class="ticker-price">$${stock.current_price.toFixed(2)}</span>
                <span class="ticker-change ${changeClass}">${pl >= 0 ? '+' : ''}${pl.toFixed(2)}%</span>
            </div>
        `;
    }).join('');
}

// Add log entry
function addLog(message, level = 'info', details = null) {
    const logContainer = document.getElementById('activityLog'); // Fixed ID
    if (!logContainer) return;

    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;

    // Add fullscreen class check to initialize visibility correctly if needed, 
    // though CSS handles it via parent class.

    const timestamp = new Date().toLocaleTimeString();

    let detailsHtml = '';
    if (details) {
        // Format details object/string
        const debugContent = typeof details === 'object' ? JSON.stringify(details, null, 2) : details;
        detailsHtml = `<div class="detail-view">${debugContent}</div>`;
    }

    entry.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span>${message}</span>
            ${detailsHtml}
        `;

    // Insert after the header? activityLog usually has activities or steps.
    // Wait, activityLog is the detailed view container BUT there's also a logContainer used by addLog?
    // Let's check index.html structure previously viewed or inferred. 
    // Actually, 'activityLog' ID was used in activity-log.js. 
    // The previous code targeted 'logContainer' which didn't exist.
    // We should treat 'activityLog' as the unified place or check if there's a specific 'logs' list inside it.
    // activity-log.js appends directly to 'activityLog'.

    logContainer.insertBefore(entry, logContainer.firstChild);

    // Keep only last 100 logs
    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.lastChild);
    }
}

// Add trade to history
function addTradeToHistory(trade) {
    const tbody = document.getElementById('tradeHistoryBody');
    const row = document.createElement('tr');

    const timestamp = new Date().toLocaleTimeString();
    row.innerHTML = `
            <td>${timestamp}</td>
        <td><span class="symbol">${trade.symbol}</span></td>
        <td>${trade.decision.toUpperCase()}</td>
        <td>${trade.quantity.toFixed(4)}</td>
        <td class="${trade.result === 'success' ? 'stat-change positive' : 'stat-change negative'}">
            ${trade.result}
        </td>
        `;

    tbody.insertBefore(row, tbody.firstChild);

    // Keep only last 50 trades
    while (tbody.children.length > 50) {
        tbody.removeChild(tbody.lastChild);
    }
}

// Update bot status indicator
function updateBotStatus(running) {
    const indicator = document.getElementById('statusIndicator');
    const text = document.getElementById('statusText');

    if (running) {
        indicator.className = 'status-indicator running';
        text.textContent = 'Running';
    } else {
        indicator.className = 'status-indicator stopped';
        text.textContent = 'Stopped';
    }
}

// Initialize charts
function initializeCharts() {
    const ctx = document.getElementById('portfolioChart');
    if (!ctx) return;

    portfolioChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Portfolio Value',
                data: [],
                fill: true,
                backgroundColor: function (context) {
                    const ctx = context.chart.ctx;
                    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
                    gradient.addColorStop(0, 'rgba(0, 255, 136, 0.3)');
                    gradient.addColorStop(1, 'rgba(0, 255, 136, 0)');
                    return gradient;
                },
                borderColor: '#00ff88',
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointBackgroundColor: '#00ff88',
                pointBorderColor: '#0a0e14',
                pointBorderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 19, 24, 0.95)',
                    titleColor: '#e4e6eb',
                    bodyColor: '#8b92a8',
                    borderColor: '#2a2e38',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function (context) {
                            return `$${context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#5a5f73',
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: '#1e2128',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#5a5f73',
                        font: {
                            size: 10
                        },
                        callback: function (value) {
                            return '$' + (value / 1000).toFixed(0) + 'k';
                        }
                    }
                }
            }
        }
    });

    // Initialize with sample data
    updatePortfolioChartWithHistory();
}

// Update timeline item styles to use theme variables


// Update portfolio chart with historical data
function updatePortfolioChartWithHistory() {
    if (!portfolioChart) return;

    // Generate sample historical data (in real app, fetch from backend)
    const now = new Date();
    const labels = [];
    const data = [];

    for (let i = 30; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));

        // Sample data - replace with real data
        const baseValue = 125000;
        const variance = Math.sin(i / 5) * 2000 + Math.random() * 1000;
        data.push(baseValue + variance + (i * 50));
    }

    portfolioChart.data.labels = labels;
    portfolioChart.data.datasets[0].data = data;
    portfolioChart.update('none');
}

// Update portfolio chart
function updatePortfolioChart(portfolio) {
    if (!portfolioChart || !portfolio || portfolio.length === 0) return;

    const labels = portfolio.map(s => s.symbol);
    const data = portfolio.map(s => s.current_price * s.quantity);

    portfolioChart.data.labels = labels;
    portfolioChart.data.datasets[0].data = data;
    portfolioChart.update('none'); // Update without animation for real-time feel
}

// ---------------------------------------------------------
// Watchlist & Alerts Functions (Missing in original file)
// ---------------------------------------------------------

async function loadWatchlist() {
    try {
        const response = await fetch('/api/watchlist');
        const data = await response.json();

        updateWatchlistTable(data.watchlist || []);
        updateAlertsList(data.alerts || []);
    } catch (error) {
        console.error('Error loading watchlist:', error);
    }
}

function updateWatchlistTable(watchlist) {
    const tbody = document.getElementById('watchlistBody');
    if (!tbody) return;

    if (!watchlist || watchlist.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No stocks in watchlist</td></tr>';
        return;
    }

    tbody.innerHTML = watchlist.map(item => {
        const changeClass = item.change >= 0 ? 'positive' : 'negative';
        const sign = item.change >= 0 ? '+' : '';
        return `
            <tr>
                <td><span class="symbol">${item.symbol}</span></td>
                <td>$${item.price.toFixed(2)}</td>
                <td class="${changeClass}">${sign}${item.change.toFixed(2)}%</td>
                <td>
                    <button class="action-btn danger" onclick="removeFromWatchlist('${item.symbol}')" title="Remove">×</button>
                </td>
            </tr>
        `;
    }).join('');
}

function updateAlertsList(alerts) {
    const list = document.getElementById('activeAlertsList');
    const symbolSelect = document.getElementById('alertSymbol');
    if (!list) return;

    // Update symbol select
    if (symbolSelect) {
        // Keep the first option
        const first = symbolSelect.options[0];
        symbolSelect.innerHTML = '';
        symbolSelect.appendChild(first);

        // Add watchlist symbols
        const watchlist = document.querySelectorAll('#watchlistBody .symbol');
        watchlist.forEach(el => {
            const sym = el.textContent;
            const opt = document.createElement('option');
            opt.value = sym;
            opt.textContent = sym;
            symbolSelect.appendChild(opt);
        });
    }

    if (!alerts || alerts.length === 0) {
        list.innerHTML = '<div class="empty-state">No active alerts</div>';
        return;
    }

    list.innerHTML = alerts.map(alert => `
        <div class="alert-item" style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid var(--border-color);">
            <div>
                <span style="font-weight: bold;">${alert.symbol}</span>
                <span style="color: var(--text-secondary); font-size: 0.9em;">
                    ${alert.condition === 'price_above' ? '>' : '<'} ${alert.value}
                </span>
            </div>
            <button class="action-btn danger" onclick="deleteAlert(${alert.id})" style="padding: 2px 6px;">×</button>
        </div>
    `).join('');
}

async function addToWatchlist() {
    const input = document.getElementById('newStockInput');
    const symbol = input.value.trim().toUpperCase();

    if (!symbol) return;

    try {
        const response = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        const data = await response.json();

        if (data.success) {
            input.value = '';
            loadWatchlist();
            addLog(`Added ${symbol} to watchlist`, 'success');
        } else {
            addLog(data.message || 'Error adding stock', 'warning');
        }
    } catch (error) {
        console.error('Error adding to watchlist:', error);
    }
}

async function removeFromWatchlist(symbol) {
    if (!confirm(`Remove ${symbol} from watchlist?`)) return;

    try {
        const response = await fetch('/api/watchlist/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        const data = await response.json();

        if (data.success) {
            loadWatchlist();
            addLog(`Removed ${symbol} from watchlist`, 'info');
        }
    } catch (error) {
        console.error('Error removing from watchlist:', error);
    }
}

async function createAlert() {
    const symbol = document.getElementById('alertSymbol').value;
    const condition = document.getElementById('alertCondition').value;
    const value = document.getElementById('alertValue').value;

    if (!symbol || !condition || !value) {
        alert('Please fill all fields');
        return;
    }

    try {
        const response = await fetch('/api/alerts/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, condition, value })
        });
        const data = await response.json();

        if (data.success) {
            document.getElementById('alertValue').value = '';
            loadWatchlist();
            addLog(`Created alert for ${symbol}`, 'success');
        } else {
            addLog(data.message || 'Error creating alert', 'warning');
        }
    } catch (error) {
        console.error('Error creating alert:', error);
    }
}

async function deleteAlert(alertId) {
    try {
        const response = await fetch('/api/alerts/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ alert_id: alertId })
        });
        const data = await response.json();

        if (data.success) {
            loadWatchlist();
            addLog(`Deleted alert`, 'info');
        }
    } catch (error) {
        console.error('Error deleting alert:', error);
    }
}


// CLICK LOGGER REMOVED FOR PRIVATE LOGGING

// --- Scalping Bot Functions ---
function loadScalpingData() {
    fetch('/api/scalping/status')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('scalper-status-badge');
            if (data.running) {
                badge.textContent = 'RUNNING';
                badge.className = 'badge long'; // success style
            } else {
                badge.textContent = 'OFFLINE';
                badge.className = 'badge short'; // error style
            }

            document.getElementById('scalper-pair-count').textContent = data.monitored_symbols.length;

            const log = document.getElementById('scalper-log');
            log.innerHTML = ''; // Clear and rebuild for now (simple)

            // Format active trades as signals
            if (Object.keys(data.active_trades).length > 0) {
                Object.entries(data.active_trades).forEach(([symbol, info]) => {
                    const div = document.createElement('div');
                    div.className = 'log-entry info';
                    div.innerHTML = `<span class="timestamp">${info.time}</span> <strong>${symbol}</strong>: ${info.signal} (${(info.change * 100).toFixed(4)}%) @ ${info.price.toFixed(2)}`;
                    log.appendChild(div);
                });
                // Update last signal box
                const lastKey = Object.keys(data.active_trades).pop();
                const lastInfo = data.active_trades[lastKey];
                document.getElementById('scalper-last-signal').textContent = `${lastKey} ${lastInfo.signal}`;
                document.getElementById('scalper-last-signal').className = lastInfo.signal === 'UP' ? 'value positive' : 'value negative';
                document.getElementById('scalper-last-time').textContent = lastInfo.time;
            } else {
                log.innerHTML = '<div class="empty-state">No signals yet. Waiting for volatility...</div>';
            }
        })
        .catch(err => console.error('Error loading scalping data:', err));
}

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-scalper-btn');
    const stopBtn = document.getElementById('stop-scalper-btn');

    if (startBtn) {
        startBtn.addEventListener('click', () => {
            fetch('/api/scalping/start', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    console.log(data.message);
                    loadScalpingData();
                });
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            fetch('/api/scalping/stop', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    console.log(data.message);
                    loadScalpingData();
                });
        });
    }
});
// Load Trading Dashboard Stats (Day P&L, Win Rate, etc.)
function loadTradingDashboardStats() {
    fetch('/api/day-trading/dashboard')
        .then(response => response.json())
        .then(data => {
            // Update Stats
            if (data.pnl_formatted) {
                const el = document.getElementById('tradingDayPnL');
                if (el) {
                    el.textContent = data.pnl_formatted;
                    el.className = `text-xl font-mono font-semibold ${data.pnl >= 0 ? 'text-success' : 'text-destructive'}`;
                }
            }
            if (data.win_rate) {
                const el = document.getElementById('tradingWinRate');
                if (el) el.textContent = data.win_rate;
            }
            if (data.trades_count !== undefined) {
                const el = document.getElementById('tradingTradeCount');
                if (el) el.textContent = data.trades_count;
            }

            // Update Open Positions Count (using active trades length or just a placeholder if not available)
            // Ideally this comes from portfolio length, but let's use what we have
            if (data.active_trades) {
                const el = document.getElementById('tradingOpenPos');
                if (el) el.textContent = data.active_trades.length;
            }
        })
        .catch(err => console.error('Error loading trading dashboard stats:', err));
}
