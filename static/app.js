// WebSocket connection
const socket = io();

// State
let botRunning = false;
let currentMode = 'demo';
let portfolioChart = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    setupEventListeners();
    requestInitialData();
});

// Setup event listeners
function setupEventListeners() {
    // Bot control buttons
    document.getElementById('startBtn').addEventListener('click', startBot);
    document.getElementById('stopBtn').addEventListener('click', stopBot);

    // Mode selector
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            setMode(e.target.dataset.mode);
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
        changeElement.textContent = `${data.total_pl >= 0 ? '+' : '-'}${Math.abs(data.total_pl).toFixed(2)}`;
        changeElement.className = `stat-change ${data.total_pl >= 0 ? 'positive' : 'negative'}`;
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
            <td class="${pl >= 0 ? 'stat-change positive' : 'stat-change negative'}">
                $${pl.toFixed(2)} (${plPercent.toFixed(2)}%)
            </td>
        `;
        tbody.appendChild(row);
    });
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
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#667eea',
                    '#764ba2',
                    '#f093fb',
                    '#4facfe',
                    '#00f2fe',
                    '#43e97b',
                    '#38f9d7',
                    '#fa709a',
                    '#fee140',
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#94a3b8',
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(20, 25, 55, 0.9)',
                    titleColor: '#ffffff',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(148, 163, 184, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function (context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            return `${label}: $${value.toFixed(2)}`;
                        }
                    }
                }
            }
        }
    });
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
