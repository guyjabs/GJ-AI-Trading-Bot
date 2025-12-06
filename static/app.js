// WebSocket connection
const socket = io();

// State
let botRunning = false;
let currentMode = 'demo';
let currentView = 'trading';
let portfolioChart = null;
let researchInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');

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
    document.querySelectorAll('.nav-tab').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchView(e.target.dataset.view);
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
function switchView(view) {
    currentView = view;

    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-view="${view}"]`).classList.add('active');

    // Show/hide view sections
    document.getElementById('trading-view').style.display = view === 'trading' ? 'block' : 'none';
    document.getElementById('day-trading-view').style.display = view === 'day-trading' ? 'block' : 'none';
    document.getElementById('research-view').style.display = view === 'research' ? 'block' : 'none';

    // Load research data if switching to research view
    if (view === 'research') {
        loadResearchData();
        // Auto-refresh every 30 seconds
        if (researchInterval) clearInterval(researchInterval);
        researchInterval = setInterval(loadResearchData, 30000);
    } else if (view === 'day-trading') {
        loadDayTradingData();
        // Auto-refresh every 5 seconds for day trading
        if (researchInterval) clearInterval(researchInterval);
        researchInterval = setInterval(loadDayTradingData, 5000);
    } else {
        if (researchInterval) {
            clearInterval(researchInterval);
            researchInterval = null;
        }
    }
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

// Force research with selected sources
async function forceResearch() {
    const btn = document.getElementById('forceResearchBtn');
    const originalText = btn.textContent;

    try {
        // Disable button
        btn.disabled = true;
        btn.textContent = '⏳ Researching...';

        // Get selected sources
        const sources = {
            newsapi: document.getElementById('sourceNewsAPI').checked,
            alphavantage: document.getElementById('sourceAlphaVantage').checked,
            finnhub: document.getElementById('sourceFinnhub').checked
        };

        // Check if at least one source is selected
        if (!sources.newsapi && !sources.alphavantage && !sources.finnhub) {
            alert('Please select at least one research source!');
            btn.disabled = false;
            btn.textContent = originalText;
            return;
        }

        // Trigger research
        const response = await fetch('/api/research/force', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ sources })
        });

        const result = await response.json();

        if (result.success) {
            // Show success message
            btn.textContent = `✅ Done! ${result.articles_count} articles`;
            setTimeout(() => {
                btn.textContent = originalText;
            }, 3000);

            // Reload research data
            setTimeout(() => {
                loadResearchData();
            }, 1000);
        } else {
            throw new Error(result.error || 'Research failed');
        }

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
    addLog(data.message, data.level);
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
function addLog(message, level = 'info') {
    const logContainer = document.getElementById('logContainer');
    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;

    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span>${message}</span>
        `;

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
