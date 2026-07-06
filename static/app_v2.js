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
    console.log('DOM loaded, initializing GUI2...');
    if (window.lucide) lucide.createIcons();

    // Initialize Socket.IO safely
    if (typeof io !== 'undefined') {
        socket = io();
    } else {
        console.error('Socket.IO not loaded');
        socket = { on: () => { }, emit: () => { } };
    }

    // --- ACTIVITY LOG EVENTS ---


    socket.on('activity_progress', (data) => {
        // Optional: Update a progress bar if we had one. For now, just logging important steps.
        // addLog('PROGRESS', `${data.percent}% - ${data.message}`, 'debug'); 
    });

    socket.on('decision_update', (data) => {
        addLog('DECISION', `${data.symbol}: ${data.decision} (${data.confidence}%) - ${data.reason}`, 'warning');
    });

    socket.on('trade_executed', (data) => {
        addLog('TRADE', `${data.action} ${data.qty} ${data.symbol} @ $${data.price}`, data.status === 'filled' ? 'success' : 'warning');
        refreshTradingData(); // Refresh table
    });

    socket.on('activity_start', (data) => {
        addLog('SYSTEM', '--- TRADING CYCLE STARTED ---', 'info');
        updateActivityStatus('Running Cycle');
    });

    socket.on('activity_complete', (data) => {
        addLog('SYSTEM', '--- TRADING CYCLE COMPLETE ---', 'info');
        updateActivityStatus('Idle');
    });

    // --- RESEARCH LOG EVENTS ---
    socket.on('research_log', (data) => {
        // If we are in Research view, we might want to show this there. 
        // For now, let's pipe it to the main log too so it's visible.
        let level = 'info';
        if (data.type === 'trend') level = 'success';
        if (data.type === 'error') level = 'error';

        const msg = data.message || JSON.stringify(data);
        addLog('RESEARCH', msg, level);
    });

    // --- GLOBAL CLICK LISTENER FOR LOGGING ---
    document.body.addEventListener('click', (event) => {
        try {
            const target = event.target;
            const element = target.closest('button, a, input, select') || target;

            const logData = {
                type: 'click',
                timestamp: new Date().toISOString(),
                details: {
                    tagName: element.tagName,
                    id: element.id || 'no-id',
                    className: element.className || 'no-class',
                    text: (element.innerText || element.value || '').substring(0, 50), // Limit text
                    x: event.clientX,
                    y: event.clientY
                }
            };

            // Send to server
            fetch('/api/log_client_event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(logData)
            }).catch(err => console.error("Log error", err));

        } catch (e) {
            // Silently fail to not impact user
        }
    }, true); // Capture phase
    // -----------------------------------------

    // Setup listeners
    try {
        setupEventListeners();
        console.log('Event listeners setup');
    } catch (e) {
        console.error('Error setting up event listeners:', e);
    }

    // Initialize charts logic (if needed apart from Strategy chart)
    // ...

    // Request initial data
    try {
        requestInitialData();
    } catch (e) {
        console.error('Error requesting initial data:', e);
    }
});

function setupEventListeners() {
    // Mode selector (Header)
    const modeSelect = document.querySelector('header select');
    // Mode Buttons Logic (Demo/Manual/Auto)
    const modeBtns = document.querySelectorAll('.mode-btn');

    if (modeSelect) {
        modeSelect.addEventListener('change', (e) => {
            console.log('Mode changed to:', e.target.value);
            // In a real app we might want to sync this with the button selector below
        });
    }

    if (modeBtns.length > 0) {
        modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // visual update
                modeBtns.forEach(b => {
                    b.classList.remove('active', 'bg-background', 'shadow-sm', 'text-foreground');
                    b.classList.add('text-muted-foreground', 'hover:bg-background/50', 'hover:text-foreground');
                });
                btn.classList.remove('text-muted-foreground', 'hover:bg-background/50', 'hover:text-foreground');
                btn.classList.add('active', 'bg-background', 'shadow-sm', 'text-foreground');

                currentMode = btn.dataset.mode;
                console.log('Selected bot mode:', currentMode);
            });
        });

        // Set initial active
        const initial = document.querySelector(`.mode-btn[data-mode="${currentMode}"]`);
        if (initial) initial.click();
    }

    // AI Mode Selector
    const aiModeSelect = document.getElementById('aiModeSelect');
    if (aiModeSelect) {
        aiModeSelect.addEventListener('change', (e) => {
            const mode = e.target.value;
            console.log('AI Reasoning Mode changed to:', mode);
            socket.emit('set_reasoning_mode', { mode: mode });
        });
    }

    // Trading Bot Start/Stop Listeners
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');

    if (startBtn) {
        startBtn.addEventListener('click', () => {
            // Robust connection check
            const isConnected = socket && (socket.connected !== false);

            if (!isConnected) {
                alert('Cannot start bot: No server connection. \nCheck your internet (for libraries) and ensure backend is running.');
                return;
            }

            console.log(`Starting bot in ${currentMode} mode...`);
            // Disable immediately to prevent double clicks
            startBtn.disabled = true;
            startBtn.innerText = 'Starting...';

            socket.emit('start_bot', { mode: currentMode });
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            console.log('Stopping bot...');
            stopBtn.disabled = true;
            stopBtn.innerText = 'Stopping...';

            socket.emit('stop_bot');
        });
    }

    // View navigation (Sidebar)
    // Note: In index_v2.html, we need to add data-view attributes to sidebar buttons first
    // For now, I'll select by text content or icon if needed, but the plan is to add attributes.
    // Assuming attributes are added:
    document.querySelectorAll('aside nav button.nav-link').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Traverse up to button if icon clicked
            const button = e.target.closest('button');
            if (!button) return;

            // Use data-view attribute for reliable navigation
            const view = button.dataset.view;
            if (!view) return;

            // Update active state on all nav links
            document.querySelectorAll('aside nav button.nav-link').forEach(b => {
                b.classList.remove('active', 'bg-accent', 'text-accent-foreground');
                b.classList.add('text-muted-foreground', 'hover:bg-muted', 'hover:text-foreground');
            });
            button.classList.add('active', 'bg-accent', 'text-accent-foreground');
            button.classList.remove('text-muted-foreground', 'hover:bg-muted', 'hover:text-foreground');

            switchView(view);
        });
    });

    // Research View: Run Deep Research
    const forceResearchBtn = document.getElementById('forceResearchBtn');
    if (forceResearchBtn) {
        forceResearchBtn.addEventListener('click', () => {
            const news = document.getElementById('sourceNewsAPI')?.checked;
            const alpha = document.getElementById('sourceAlpha')?.checked;
            const finn = document.getElementById('sourceFinnhub')?.checked;

            if (!news && !alpha && !finn) {
                alert('Please select at least one data source');
                return;
            }

            // UI Feedback
            const originalV = forceResearchBtn.innerHTML;
            forceResearchBtn.disabled = true;
            forceResearchBtn.innerHTML = '<span class="animate-spin mr-2">⟳</span> Running...'; // Simple text spinner fallback

            fetch('/api/research/force', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sources: {
                        newsapi: news,
                        alphavantage: alpha,
                        finnhub: finn
                    }
                })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'error') {
                        alert('Error: ' + data.message);
                    } else {
                        console.log('Research started:', data);
                        // The socket log events will handle the UI updates in the 'Live News' section
                        // We might want to switch to the Log tab or just stay here
                        addLog('RESEARCH', 'Manual research triggered', 'info');
                    }
                })
                .catch(err => {
                    console.error('Research error:', err);
                    addLog('RESEARCH', 'Failed to trigger research', 'error');
                })
                .finally(() => {
                    forceResearchBtn.disabled = false;
                    forceResearchBtn.innerHTML = originalV;
                });
        });
    }

    // Scalping Bot Controls
    const startScalpBtn = document.getElementById('start-scalper-btn');
    const stopScalpBtn = document.getElementById('stop-scalper-btn');
    const updateScalpBtn = document.getElementById('update-scalp-config-btn');

    if (startScalpBtn) {
        startScalpBtn.addEventListener('click', () => {
            startScalpBtn.disabled = true;
            startScalpBtn.innerText = 'Starting...';

            fetch('/api/scalping/start', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        addLog('Scalper', 'Scalping bot started', 'success');
                        loadScalpingData(); // Immediate update
                    } else {
                        alert('Error: ' + data.message);
                        startScalpBtn.disabled = false;
                        startScalpBtn.innerText = 'Start Scalping';
                    }
                })
                .catch(err => {
                    console.error('Scalp start error:', err);
                    startScalpBtn.disabled = false;
                    startScalpBtn.innerText = 'Start Scalping';
                });
        });
    }

    if (stopScalpBtn) {
        stopScalpBtn.addEventListener('click', () => {
            stopScalpBtn.disabled = true;
            stopScalpBtn.innerText = 'Stopping...';

            fetch('/api/scalping/stop', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        addLog('Scalper', 'Scalping bot stopped', 'warning');
                        loadScalpingData();
                    } else {
                        alert('Error: ' + data.message);
                        stopScalpBtn.disabled = false;
                        stopScalpBtn.innerText = 'Stop';
                    }
                })
                .catch(err => {
                    console.error('Scalp stop error:', err);
                    stopScalpBtn.disabled = false;
                    stopScalpBtn.innerText = 'Stop';
                });
        });
    }

    if (updateScalpBtn) {
        updateScalpBtn.addEventListener('click', () => {
            const vol = parseFloat(document.getElementById('scalp-vol')?.value || 0.1);
            const tp = parseFloat(document.getElementById('scalp-tp')?.value || 0.5);
            const sl = parseFloat(document.getElementById('scalp-sl')?.value || 0.3);

            updateScalpBtn.disabled = true;
            updateScalpBtn.innerText = 'Updating...';

            fetch('/api/scalping/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    min_volatility: vol,
                    take_profit: tp,
                    stop_loss: sl
                })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        addLog('Scalper', 'Configuration updated', 'info');
                        alert('Configuration updated successfully');
                    } else {
                        alert('Error: ' + data.message);
                    }
                })
                .catch(err => console.error('Scalp config error:', err))
                .finally(() => {
                    updateScalpBtn.disabled = false;
                    updateScalpBtn.innerText = 'Update Config';
                });
        });
    }

    // Collapsible Logic
    const scalpHeader = document.getElementById('scalp-params-header');
    if (scalpHeader) {
        scalpHeader.addEventListener('click', () => {
            const content = document.getElementById('scalp-params-content');
            const chevron = document.getElementById('scalp-chevron');

            if (content) content.classList.toggle('hidden');
            if (chevron) {
                chevron.classList.toggle('rotate-180');
                // Force icon re-render if needed (though class toggle usually suffices for CSS transforms)
                if (window.lucide) window.lucide.createIcons();
            }
        });
    }

    // Strategy Chart Init
    // loadStrategyHistory();

    // Socket events
    socket.on('connect', () => {
        console.log('Connected to server');
        addLog('System', 'Connected to trading server', 'success');
        socket.emit('get_status'); // Request update
    });

    socket.on('log_message', (data) => {
        const source = data.source || 'System';
        addLog(source, data.message, data.level || 'info');
    });

    socket.on('bot_status', (data) => {
        console.log('Bot Status Update:', data);
        botRunning = data.running;

        // Update UI logic
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const statusPill = document.getElementById('botStatusPill');
        const statusText = document.getElementById('botStatusText');
        const statusIcon = statusPill ? statusPill.querySelector('i') : null;

        if (data.running) {
            // Bot is running
            if (startBtn) {
                startBtn.disabled = true;
                startBtn.innerText = 'Start Bot'; // Reset text
                startBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
            if (stopBtn) {
                stopBtn.disabled = false;
                stopBtn.innerText = 'Stop Bot'; // Reset text
                stopBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }

            if (statusPill && statusText && statusIcon) {
                statusPill.className = 'flex items-center gap-2 px-3 py-1.5 bg-success/10 rounded-full';
                statusIcon.className = 'w-2 h-2 fill-success text-success animate-pulse';
                statusText.className = 'text-[12px] font-medium text-success';
                statusText.innerText = 'Bot Running';
            }

        } else {
            // Bot is stopped
            if (startBtn) {
                startBtn.disabled = false;
                startBtn.innerText = 'Start Bot';
                startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
            if (stopBtn) {
                stopBtn.disabled = true;
                stopBtn.innerText = 'Stop Bot';
                stopBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }

            if (statusPill && statusText && statusIcon) {
                statusPill.className = 'flex items-center gap-2 px-3 py-1.5 bg-muted rounded-full';
                statusIcon.className = 'w-2 h-2 fill-muted-foreground text-muted-foreground';
                statusText.className = 'text-[12px] font-medium text-muted-foreground';
                statusText.innerText = 'Bot Idle';
            }
        }

        // Update AI reasoning dropdown if present
        const aiModeSelect = document.getElementById('aiModeSelect');
        if (aiModeSelect && data.reasoning_mode) {
            aiModeSelect.value = data.reasoning_mode;
        }
    });

    // Activity Log Events
    socket.on('activity_step', (data) => {
        // data = { text, status }
        addLog('Bot', data.text, 'info');

        // Update activity status indicator in Dashboard
        const statusEl = document.getElementById('activity-status');
        if (statusEl) {
            statusEl.innerText = 'Active';
            statusEl.className = 'text-[10px] bg-secondary px-2 py-0.5 rounded border border-border text-foreground animate-pulse';

            // Revert after 3 seconds of silence (optional visual polish)
            clearTimeout(window.activityTimeout);
            window.activityTimeout = setTimeout(() => {
                statusEl.innerText = 'Idle';
                statusEl.className = 'text-[10px] bg-background/50 px-2 py-0.5 rounded border border-border text-muted-foreground';
            }, 5000);
        }
    });

    socket.on('activity_start', (data) => {
        addLog('System', `Task Started: ${data.title}`, 'info');
    });

    socket.on('activity_complete', (data) => {
        addLog('System', `Task Complete. Success: ${data.success}`, data.success ? 'success' : 'error');
    });

    socket.on('decision_update', (data) => {
        // data = { type, data }
        addLog('Strategy', `Decision: ${data.type}`, 'success');
        // We could also update the decision timeline here if we had the logic
        loadStrategyHistory();
    });

    socket.on('research_log', (data) => {
        addLog('Research', data.message, 'info');
    });

    socket.on('status_update', (data) => {
        // Update Header Stats
        // Balance = Cash + Portfolio Value
        // In app.js: Balance = buying_power + portfolio_value. 
        // Let's match that logic.
        const balance = (data.buying_power || 0) + (data.portfolio_value || 0);

        // Find header elements - specific to v2 structure
        // We need to add IDs to index_v2.html header elements or select by text
        // Plan: Update index_v2.html to have IDs: headerBalance, headerDayPL, headerTotalPL
        const elBalance = document.getElementById('headerBalance');
        if (elBalance) elBalance.innerText = formatMoney(balance);

        // Unrealized P&L
        const elUnrealizedPL = document.getElementById('headerUnrealizedPL');
        if (elUnrealizedPL) {
            elUnrealizedPL.innerText = (data.total_pl >= 0 ? '+' : '') + formatMoney(data.total_pl);
            elUnrealizedPL.className = `text-sm font-semibold font-mono ${data.total_pl >= 0 ? 'text-success' : 'text-destructive'}`;
        }

        // Day P&L (For now using total_pl as active session P&L)
        const elDayPL = document.getElementById('headerDayPL');
        if (elDayPL) {
            elDayPL.innerText = (data.total_pl >= 0 ? '+' : '') + formatMoney(data.total_pl);
            elDayPL.className = `text-sm font-semibold font-mono ${data.total_pl >= 0 ? 'text-success' : 'text-destructive'}`;
        }

        const elTotalPL = document.getElementById('headerPL');
        if (elTotalPL) {
            elTotalPL.innerText = (data.total_pl >= 0 ? '+' : '') + formatMoney(data.total_pl);
            elTotalPL.className = `text-sm font-semibold font-mono ${data.total_pl >= 0 ? 'text-success' : 'text-destructive'}`;
        }
    });

    socket.on('portfolio_update', (data) => {
        // Update Ticker
        if (data && data.length > 0) {
            updateTickerBar(data.slice(0, 5)); // Show top 5 in ticker
        }

        // Update Holdings Table
        const tbody = document.getElementById('portfolioTableBody');
        if (tbody) {
            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-muted-foreground text-xs">No active holdings</td></tr>';
            } else {
                tbody.innerHTML = data.map(stock => {
                    const pl = (stock.current_price - stock.average_buy_price) * stock.quantity;
                    const plPercent = ((stock.current_price - stock.average_buy_price) / stock.average_buy_price * 100);
                    const isPos = pl >= 0;

                    return `
                        <tr class="hover:bg-muted/30 transition-colors">
                            <td class="p-3 font-medium text-foreground">${stock.symbol}</td>
                            <td class="p-3 text-right font-mono text-muted-foreground">${stock.quantity.toFixed(4)}</td>
                            <td class="p-3 text-right font-mono text-muted-foreground">$${stock.average_buy_price.toFixed(2)}</td>
                            <td class="p-3 text-right font-mono text-foreground">$${stock.current_price.toFixed(2)}</td>
                            <td class="p-3 text-right font-mono font-semibold ${isPos ? 'text-success' : 'text-destructive'}">
                                ${isPos ? '+' : ''}$${pl.toFixed(2)} (${plPercent.toFixed(2)}%)
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    });

    // Other socket handlers...
}

// Global interval variable
let viewInterval = null;

function switchView(view) {
    console.log('Switching to view:', view);
    currentView = view;

    // Clear previous interval if exists
    if (viewInterval) {
        clearInterval(viewInterval);
        viewInterval = null;
    }

    // Hide all views
    document.querySelectorAll('.view-section').forEach(el => el.style.display = 'none');

    // Show target view
    const target = document.getElementById(`${view}-view`);
    if (target) {
        target.style.display = 'block';
    }

    // Load data for view
    if (view === 'research') loadResearchData();
    if (view === 'day-trading') loadDayTradingData();
    if (view === 'scalping') {
        loadScalpingData();
        // Poll every 2 seconds
        viewInterval = setInterval(loadScalpingData, 2000);
    }
    if (view === 'trading') loadTradingDashboardStats();
    if (view === 'comparison') loadComparisonData();
    if (view === 'developer') loadDeveloperLog();
    if (view === 'history') loadTradeHistory(); // Reload history on view switch
}

// ... existing code ...

// Expose global
window.loadDeveloperLog = loadDeveloperLog;
window.loadTradeHistory = loadTradeHistory;

// Load Developer Log
async function loadDeveloperLog() {
    const container = document.getElementById('developerLogFeed');
    if (!container) return;

    container.innerHTML = '<div class="p-8 text-center text-muted-foreground text-xs"><span class="animate-pulse">Loading developer logs...</span></div>';

    try {
        const response = await fetch('/api/developer/log');
        const data = await response.json();
        const logs = data.logs || [];

        if (logs.length === 0) {
            container.innerHTML = '<div class="p-8 text-center text-muted-foreground text-xs">No logs found.</div>';
            return;
        }

        container.innerHTML = logs.map(entry => {
            const time = new Date(entry.timestamp).toLocaleString();
            const isChange = entry.type === 'change';

            if (isChange) {
                return `
                    <div class="p-4 bg-muted/10">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">Feature</span>
                            <span class="text-xs text-muted-foreground font-mono">${time}</span>
                        </div>
                        <h4 class="text-sm font-semibold text-foreground mb-1">${entry.title}</h4>
                        <p class="text-xs text-foreground/80 mb-2">${entry.description}</p>
                        ${entry.walkthrough_link ? `<div class="text-[10px] bg-muted inline-block px-2 py-1 rounded border border-border">Walkthrough applied from: <span class="font-mono text-xs opacity-70">${entry.walkthrough_link.split('/').pop()}</span></div>` : ''}
                    </div>
                `;
            } else {
                // Client Event / Debug
                return `
                    <div class="p-3 hover:bg-muted/5 transition-colors pl-8 relative">
                        <div class="absolute left-3 top-4 w-2 h-2 rounded-full bg-border"></div>
                        <div class="flex justify-between items-start">
                            <span class="text-[11px] font-mono font-semibold text-muted-foreground uppercase">${entry.event_type}</span>
                            <span class="text-[10px] text-muted-foreground/50 font-mono">${time}</span>
                        </div>
                        <div class="text-[11px] text-muted-foreground mt-0.5 font-mono overflow-hidden text-ellipsis">
                            ${JSON.stringify(entry.details).substring(0, 150)}
                        </div>
                    </div>
                `;
            }
        }).join('');

    } catch (e) {
        console.error("Error loading dev logs:", e);
        container.innerHTML = '<div class="p-4 text-xs text-destructive">Error loading data.</div>';
    }
}

// Load Full Trade History
async function loadTradeHistory() {
    // This assumes there's a table in the history view (we might need to check index_v2.html structure for it, or use existing one)
    // Looking at previous chats, we didn't explicitly build the History *table* dynamic logic in app_v2 yet, so adding it now.
    // We need to find where the history table is. Assuming ID 'historyTableBody'.

    // NOTE: In the original 'Wire Up' phase, we might not have fully implemented the history table loader.
    // Let's implement it robustly here.

    const tbody = document.getElementById('historyTableBody') || document.querySelector('#history-view tbody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-muted-foreground text-xs">Loading full history...</td></tr>';

    try {
        const response = await fetch('/api/trading/history');
        const data = await response.json();

        if (!data.trades || data.trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-muted-foreground text-xs">No trade history found.</td></tr>';
            return;
        }

        tbody.innerHTML = data.trades.map(trade => {
            const pnl = trade.pnl || 0;
            const isWin = pnl >= 0;
            return `
                <tr class="hover:bg-muted/30 transition-colors">
                    <td class="p-3 whitespace-nowrap text-xs text-muted-foreground font-mono">${new Date(trade.entry_time).toLocaleString()}</td>
                    <td class="p-3 font-medium text-foreground">${trade.symbol}</td>
                    <td class="p-3 text-xs uppercase bg-muted/30 rounded px-2 py-1 inline-block mt-2">${trade.strategy || 'Manual'}</td>
                    <td class="p-3 text-right font-mono text-muted-foreground">$${trade.entry_price.toFixed(2)}</td>
                    <td class="p-3 text-right font-mono text-foreground">$${trade.exit_price ? trade.exit_price.toFixed(2) : '-'}</td>
                    <td class="p-3 text-right font-mono font-semibold ${isWin ? 'text-success' : 'text-destructive'}">
                        ${trade.exit_price ? (isWin ? '+' : '') + '$' + pnl.toFixed(2) : '<span class="text-xs text-muted-foreground italic">Open</span>'}
                    </td>
                     <td class="p-3 text-xs text-muted-foreground max-w-[200px] truncate" title="${trade.notes || ''}">${trade.notes || '-'}</td>
                </tr>
            `;
        }).join('');

    } catch (e) {
        console.error("Error history:", e);
        tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-destructive text-xs">Failed to load history.</td></tr>';
    }
}

// Load Comparison Data
async function loadComparisonData() {
    const tbody = document.getElementById('comparisonTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-muted-foreground text-xs">Loading logs...</td></tr>';

    try {
        const response = await fetch('/api/logs/comparison');
        const data = await response.json();

        if (!data.logs || data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-muted-foreground text-xs">No comparison logs found yet. Run in "Advanced Mode" to generate data.</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.map(log => {
            const decisionColor =
                log.Decision === 'buy' ? 'text-success' :
                    log.Decision === 'sell' ? 'text-destructive' : 'text-muted-foreground';

            // Format timestamp for readability
            let timeStr = log.Timestamp;
            try {
                timeStr = new Date(log.Timestamp).toLocaleTimeString();
            } catch (e) { }

            return `
                <tr class="hover:bg-muted/30 transition-colors group">
                    <td class="p-3 font-mono text-xs text-muted-foreground whitespace-nowrap">${timeStr}</td>
                    <td class="p-3 font-medium text-foreground">${log.Symbol}</td>
                    <td class="p-3 font-semibold text-xs uppercase ${decisionColor}">${log.Decision}</td>
                    <td class="p-3 font-mono text-xs">${log.Confidence || '-'}</td>
                    <td class="p-3 text-xs text-foreground/80 font-mono">
                        <div class="line-clamp-2 group-hover:line-clamp-none transition-all duration-300">
                            ${(log.Full_Trace_Snippet || '').replace(/\\n/g, '<br>')}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading comparison logs:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-destructive text-xs">Failed to load logs.</td></tr>';
    }
}

// Load Research Data
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

function updateResearchSummary(summary) {
    if (!summary) return;
    const sentiment = summary.overall_sentiment || {};
    const avgSentiment = sentiment.average || 0;

    const elSentiment = document.getElementById('marketSentiment');
    if (elSentiment) {
        elSentiment.textContent = avgSentiment.toFixed(2);
        elSentiment.className = `text-xl font-mono font-semibold ${avgSentiment >= 0 ? 'text-success' : 'text-destructive'}`;
    }

    const breakdown = `${sentiment.positive || 0} pos / ${sentiment.negative || 0} neg`;
    if (document.getElementById('sentimentBreakdown'))
        document.getElementById('sentimentBreakdown').textContent = breakdown;

    if (document.getElementById('newsVolume'))
        document.getElementById('newsVolume').textContent = summary.news_count || 0;

    const accuracy = summary.prediction_accuracy || {};
    if (document.getElementById('predictionAccuracy'))
        document.getElementById('predictionAccuracy').textContent = accuracy.accuracy ? `${accuracy.accuracy.toFixed(1)}%` : '--%';
}

function updatePredictions(predictions) {
    const container = document.getElementById('predictionsList');
    if (!container) return;

    if (!predictions || predictions.length === 0) {
        container.innerHTML = '<div class="text-center p-8 text-muted-foreground text-xs">No active predictions</div>';
        return;
    }

    container.innerHTML = predictions.map(pred => {
        const confidence = pred.metadata?.confidence || 0;
        const symbol = pred.metadata?.symbol || 'N/A';
        const direction = pred.metadata?.direction || 'unknown';
        const colorClass = direction.toLowerCase() === 'buy' ? 'text-success' : 'text-destructive';

        return `
            <div class="bg-muted/30 p-3 rounded-md border border-border/50">
                <div class="flex justify-between items-center mb-1">
                    <span class="font-semibold text-xs ${colorClass}">${symbol} - ${direction.toUpperCase()}</span>
                    <span class="text-[10px] text-muted-foreground">Conf: ${(confidence * 100).toFixed(0)}%</span>
                </div>
                <div class="text-[11px] text-foreground/80 leading-snug">${pred.text}</div>
            </div>
        `;
    }).join('');
}

function updateTrends(trends) {
    const container = document.getElementById('trendsList');
    if (!container) return;

    if (!trends || trends.length === 0) {
        container.innerHTML = '<div class="text-center p-8 text-muted-foreground text-xs">No trends detected</div>';
        return;
    }

    container.innerHTML = trends.slice(0, 10).map(trend => {
        const type = trend.metadata?.type || 'general';
        const strength = trend.metadata?.strength || 0;

        return `
            <div class="bg-muted/30 p-3 rounded-md border border-border/50">
                <div class="flex justify-between items-center mb-1">
                    <span class="font-semibold text-xs capitalize text-primary">${type}</span>
                    <span class="text-[10px] text-muted-foreground">Strength: ${(strength * 100).toFixed(0)}%</span>
                </div>
                <div class="text-[11px] text-foreground/80 leading-snug">${trend.text}</div>
            </div>
        `;
    }).join('');
}

function updateNews(articles) {
    const container = document.getElementById('newsFeed');
    if (!container) return;

    if (!articles || articles.length === 0) {
        container.innerHTML = '<div class="text-center p-8 text-muted-foreground text-xs">No news available</div>';
        return;
    }

    container.innerHTML = articles.slice(0, 12).map(article => {
        const sentiment = article.sentiment || 0;
        const sentimentLabel = sentiment > 0.1 ? 'Pos' : sentiment < -0.1 ? 'Neg' : 'Neu';
        const sentimentClass = sentiment > 0.1 ? 'text-success bg-success/10' : sentiment < -0.1 ? 'text-destructive bg-destructive/10' : 'text-muted-foreground bg-muted';

        const date = new Date(article.published_at || article.datetime);
        const timeAgo = getTimeAgo(date);

        return `
            <div class="p-3 hover:bg-muted/50 transition-colors rounded-md border border-transparent hover:border-border/50">
                <div class="flex justify-between items-start mb-1">
                    <span class="text-[10px] font-medium text-primary">${article.source || 'Unknown'}</span>
                    <span class="text-[9px] px-1.5 py-0.5 rounded-full ${sentimentClass}">${sentimentLabel}</span>
                </div>
                <a href="${article.url}" target="_blank" class="block text-xs font-medium text-foreground hover:underline mb-1 line-clamp-2">${article.title}</a>
                <div class="flex justify-between items-center text-[10px] text-muted-foreground">
                    <span>${timeAgo}</span>
                    <span>${article.tickers?.join(', ') || ''}</span>
                </div>
            </div>
        `;
    }).join('');
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

// Load Day Trading Data
async function loadDayTradingData() {
    try {
        const response = await fetch('/api/day-trading/dashboard');
        const data = await response.json();

        // Update Stats
        const elPnL = document.getElementById('dayPnL');
        if (elPnL) {
            elPnL.textContent = data.pnl_formatted;
            elPnL.className = `text-xl font-mono font-semibold ${data.pnl >= 0 ? 'text-success' : 'text-destructive'}`;
        }

        const elTrades = document.getElementById('dayTradesCount');
        if (elTrades) elTrades.textContent = data.trades_count;

        const elWinRate = document.getElementById('dayWinRate');
        if (elWinRate) elWinRate.textContent = data.win_rate;

        const elTrend = document.getElementById('spyTrend');
        if (elTrend) elTrend.textContent = data.market_context.spy_trend;

        // Update Active Trades
        const tbody = document.getElementById('dayTradesBody');
        if (tbody) {
            if (data.active_trades.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="p-12 text-center text-muted-foreground">
                            <div class="flex flex-col items-center gap-2">
                                <i data-lucide="coffee" class="w-8 h-8 text-muted-foreground/50"></i>
                                <span class="text-[13px]">No active day trades</span>
                                <span class="text-[11px] text-muted-foreground/70">Waiting for setup...</span>
                            </div>
                        </td>
                    </tr>`;
                if (window.lucide) lucide.createIcons();
            } else {
                tbody.innerHTML = data.active_trades.map(trade => `
                    <tr class="hover:bg-muted/30 transition-colors">
                        <td class="p-3 font-medium text-foreground">${trade.symbol}</td>
                        <td class="p-3 text-right font-mono text-muted-foreground">$${trade.entry_price.toFixed(2)}</td>
                        <td class="p-3 text-right font-mono text-foreground">$${trade.current_price.toFixed(2)}</td>
                        <td class="p-3 text-right font-mono text-destructive">$${trade.stop_loss.toFixed(2)}</td>
                        <td class="p-3 text-right font-mono text-success">$${trade.target.toFixed(2)}</td>
                        <td class="p-3 text-right font-mono font-semibold ${trade.pnl >= 0 ? 'text-success' : 'text-destructive'}">
                            ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}
                        </td>
                        <td class="p-3 text-right font-mono text-xs text-muted-foreground">${trade.r_multiple.toFixed(2)}R</td>
                    </tr>
                `).join('');
            }
        }

        // Update Scanner
        updateScannerList('gappersList', data.scanner.gappers);
        updateScannerList('momentumList', data.scanner.momentum);

        // Load Watchlist too
        loadWatchlistData();

    } catch (error) {
        console.error('Error loading day trading data:', error);
    }
}

function updateScannerList(elementId, items) {
    const list = document.getElementById(elementId);
    if (!list) return;

    if (!items || items.length === 0) {
        list.innerHTML = '<li class="p-4 text-center text-[11px] text-muted-foreground">No candidates found</li>';
        return;
    }

    list.innerHTML = items.map(item => `
        <li class="p-2 hover:bg-muted/30 rounded flex items-center justify-between group">
            <div class="flex flex-col">
                <span class="text-[12px] font-semibold text-foreground">${item.symbol}</span>
                <span class="text-[10px] text-muted-foreground">${item.detail}</span>
            </div>
            <button class="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 bg-primary text-primary-foreground text-[10px] rounded hover:bg-primary/90">
                Analyze
            </button>
        </li>
    `).join('');
}

// Load Scalping Data
function loadScalpingData() {
    fetch('/api/scalping/status')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('scalper-status-badge');
            const startBtn = document.getElementById('start-scalper-btn');
            const stopBtn = document.getElementById('stop-scalper-btn');

            if (badge) {
                if (data.running) {
                    badge.textContent = 'RUNNING';
                    badge.className = 'px-2 py-1 rounded bg-success/10 text-success text-xs font-bold uppercase';
                } else {
                    badge.textContent = 'OFFLINE';
                    badge.className = 'px-2 py-1 rounded bg-destructive/10 text-destructive text-xs font-bold uppercase';
                }
            }

            // Update buttons independently of badge
            if (data.running) {
                if (startBtn) startBtn.disabled = true;
                if (stopBtn) stopBtn.disabled = false;
            } else {
                if (startBtn) startBtn.disabled = false;
                if (stopBtn) stopBtn.disabled = true;
            }

            const countEl = document.getElementById('scalper-pair-count');
            if (countEl) countEl.textContent = data.monitored_symbols.length;

            const log = document.getElementById('scalper-log');
            if (log) {
                log.innerHTML = '';

                if (data.active_trades && Object.keys(data.active_trades).length > 0) {
                    Object.entries(data.active_trades).forEach(([symbol, info]) => {
                        const div = document.createElement('div');
                        div.className = 'p-2 mb-1 rounded bg-muted/30 border border-border/50 text-[11px] font-mono';
                        const signalColor = info.signal === 'BUY' ? 'text-success' : 'text-destructive';
                        div.innerHTML = `
                            <div class="flex justify-between">
                                <span class="text-muted-foreground">${info.time}</span>
                                <span class="font-bold text-foreground">${symbol}</span>
                            </div>
                            <div class="flex justify-between mt-1">
                                <span class="${signalColor} font-semibold">${info.signal}</span>
                                <span>${(info.change * 100).toFixed(2)}%</span>
                                <span>$${info.price.toFixed(2)}</span>
                            </div>
                        `;
                        log.appendChild(div);
                    });

                    // Update last signal box
                    const lastKey = Object.keys(data.active_trades).pop();
                    const lastInfo = data.active_trades[lastKey];
                    const elLastSignal = document.getElementById('scalper-last-signal');
                    if (elLastSignal) {
                        elLastSignal.textContent = `${lastKey} ${lastInfo.signal}`;
                        elLastSignal.className = `font-mono font-bold ${lastInfo.signal === 'BUY' ? 'text-success' : 'text-destructive'}`;
                    }
                    const elLastTime = document.getElementById('scalper-last-time');
                    if (elLastTime) elLastTime.textContent = lastInfo.time;
                } else {
                    log.innerHTML = '<div class="text-center p-12 text-muted-foreground">Waiting for signals...</div>';
                }
            }
        })
        .catch(err => console.error('Error loading scalping data:', err));
}

// Load Trading Dashboard Stats
function loadTradingDashboardStats() {
    fetch('/api/day-trading/dashboard')
        .then(response => response.json())
        .then(data => {
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
            if (data.active_trades) {
                const el = document.getElementById('tradingOpenPos');
                if (el) el.textContent = data.active_trades.length;
            }
        })
        .catch(err => console.error('Error loading trading dashboard stats:', err));
}


// Initialize Scalper Listeners
document.addEventListener('DOMContentLoaded', () => {
    // --- SIMULATION BOT LOGIC ---
    const btnRunSim = document.getElementById('btnRunSim');
    if (btnRunSim) {
        btnRunSim.addEventListener('click', async () => {
            const startDate = document.getElementById('simStartDate').value;
            const endDate = document.getElementById('simEndDate').value;
            const universe = document.getElementById('simUniverse').value;
            const cash = document.getElementById('simCash').value;

            if (!startDate || !endDate) {
                alert('Please select start and end dates.');
                return;
            }

            btnRunSim.disabled = true;
            btnRunSim.textContent = 'Running Simulation (this may take a while)...';

            try {
                const response = await fetch('/api/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        start_date: startDate,
                        end_date: endDate,
                        universe: universe,
                        initial_cash: cash
                    })
                });

                const data = await response.json();

                if (data.error) {
                    alert('Simulation Error: ' + data.error);
                } else {
                    // Show results
                    document.getElementById('simResults').classList.remove('hidden');
                    document.getElementById('simFinalBalance').textContent = formatMoney(data.final_balance);
                    document.getElementById('simReturn').textContent = (data.total_return_pct * 100).toFixed(2) + '%';
                    document.getElementById('simTrades').textContent = data.trades;

                    if (data.total_return_pct >= 0) {
                        document.getElementById('simReturn').classList.add('text-success');
                        document.getElementById('simReturn').classList.remove('text-destructive');
                    } else {
                        document.getElementById('simReturn').classList.add('text-destructive');
                        document.getElementById('simReturn').classList.remove('text-success');
                    }
                }
            } catch (e) {
                console.error(e);
                alert('Failed to run simulation');
            } finally {
                btnRunSim.disabled = false;
                btnRunSim.textContent = 'Run Simulation';
            }
        });
    }

    const startBtn = document.getElementById('start-scalper-btn');
    const stopBtn = document.getElementById('stop-scalper-btn');

    // Scalper Listeners
    if (startBtn) {
        startBtn.addEventListener('click', () => {
            startBtn.disabled = true; // Immediate feedback
            fetch('/api/scalping/start', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    console.log(data.message);
                    if (data.status === 'error') {
                        startBtn.disabled = false; // Re-enable if failed
                        alert(data.message);
                    } else {
                        // Success: Keep disabled, let loadScalpingData update state
                        loadScalpingData();
                    }
                })
                .catch(err => {
                    console.error(err);
                    startBtn.disabled = false;
                });
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            stopBtn.disabled = true; // Immediate feedback
            fetch('/api/scalping/stop', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    console.log(data.message);
                    if (data.status === 'error') {
                        stopBtn.disabled = false; // Re-enable if failed
                        alert(data.message);
                    } else {
                        // Success: Keep disabled, let loadScalpingData update state
                        loadScalpingData();
                    }
                })
                .catch(err => {
                    console.error(err);
                    stopBtn.disabled = false;
                });
        });
    }

    // Day Trading: Add Stock Watchlist Listener
    const addStockBtn = document.getElementById('addStockBtn');
    const newStockInput = document.getElementById('newStockInput');

    if (addStockBtn && newStockInput) {
        addStockBtn.addEventListener('click', () => {
            const symbol = newStockInput.value.toUpperCase().trim();
            if (!symbol) return;

            addStockBtn.disabled = true; // Prevent double submit

            fetch('/api/watchlist/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: symbol })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        // Reload data
                        loadWatchlistData();
                        newStockInput.value = '';
                    } else {
                        alert(data.message || 'Failed to add stock');
                    }
                })
                .catch(err => console.error('Error adding stock:', err))
                .finally(() => {
                    addStockBtn.disabled = false;
                });
        });
    }

    // Panic Sell Listener
    const panicBtn = document.getElementById('panicSellBtn');
    if (panicBtn) {
        panicBtn.addEventListener('click', () => {
            if (!confirm('EXTREME WARNING: This will immediately close ALL open positions and cancel ALL orders.\n\nAre you sure you want to PANIC SELL?')) {
                return;
            }

            panicBtn.disabled = true;
            panicBtn.innerText = 'SELLING ALL...';

            fetch('/api/day-trading/panic', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        alert('PANIC SELL EXECUTED: ' + data.message);
                        // Force refresh of data
                        loadDayTradingData();
                        requestInitialData();
                    } else {
                        alert('Panic Sell Failed: ' + data.message);
                    }
                })
                .catch(err => {
                    console.error('Panic sell error:', err);
                    alert('Panic sell network error. Check console.');
                })
                .finally(() => {
                    panicBtn.disabled = false;
                    panicBtn.innerText = 'Panic Sell All';
                });
        });
    }

    // Connection Status Logic override
    socket.on('connect', () => {
        updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        updateConnectionStatus(false);
    });

    function updateConnectionStatus(connected) {
        const elStatus = document.getElementById('alpacaStatus');
        const elText = document.getElementById('alpacaStatusText');

        if (elStatus && elText) {
            if (connected) {
                elStatus.className = 'flex items-center gap-2 px-3 py-2 bg-success/10 rounded-md transition-colors';
                elText.className = 'text-[12px] font-medium text-success';
                elText.innerText = 'Alpaca Connected';
                // Icon handling if needed, but CSS handles color for SVG mainly
                const icon = elStatus.querySelector('svg');
                if (icon) icon.classList.replace('text-destructive', 'text-success');

            } else {
                elStatus.className = 'flex items-center gap-2 px-3 py-2 bg-destructive/10 rounded-md transition-colors';
                elText.className = 'text-[12px] font-medium text-destructive';
                elText.innerText = 'Disconnected';
                const icon = elStatus.querySelector('svg');
                if (icon) icon.classList.replace('text-success', 'text-destructive');
            }
        }
    }
});

// Helper for removing watchlist items (needs to be global or accessible)
window.removeFromWatchlist = function (symbol) {
    if (!confirm(`Remove ${symbol} from watchlist?`)) return;

    fetch('/api/watchlist/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                loadWatchlistData();
            } else {
                alert('Failed to remove: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(err => {
            console.error('Error removing from watchlist:', err);
            alert('Network error removing stock');
        });
};


// Load Watchlist Data
// Load Watchlist Data
async function loadWatchlistData() {
    try {
        const response = await fetch('/api/watchlist');
        const data = await response.json();
        const watchlist = data.watchlist || [];

        // Dynamic Ticker Tape Logic
        const tickerBar = document.getElementById('tickerBar');
        if (tickerBar) {
            let tickerItems = [...watchlist];
            
            // Fallbacks for the ticker tape if watchlist is small or empty to keep it looking lively
            if (tickerItems.length < 5) {
                const fallbacks = [
                    { symbol: 'BTC/USD', price: 65420.50, change: 2.45 },
                    { symbol: 'ETH/USD', price: 3480.20, change: -1.15 },
                    { symbol: 'SPY', price: 542.30, change: 0.85 },
                    { symbol: 'NVDA', price: 125.80, change: 4.62 },
                    { symbol: 'SOL/USD', price: 142.10, change: 5.12 },
                    { symbol: 'AAPL', price: 210.60, change: -0.32 }
                ];
                fallbacks.forEach(item => {
                    if (!tickerItems.some(i => i.symbol === item.symbol)) {
                        tickerItems.push(item);
                    }
                });
            }

            // Create two copies of the ticker items to enable seamless infinite loop scrolling
            const doubledItems = [...tickerItems, ...tickerItems];
            
            tickerBar.innerHTML = doubledItems.map(item => {
                const price = item.price || 0;
                const change = item.change || 0;
                const changeColor = change >= 0 ? 'text-success' : 'text-destructive';
                const changeIcon = change >= 0 ? '▲' : '▼';
                const changeSign = change >= 0 ? '+' : '';
                return `
                    <div class="inline-flex items-center gap-1.5 px-6 h-8 border-r border-border/50">
                        <span class="text-[12px] font-semibold text-foreground">${item.symbol}</span>
                        <span class="text-[12px] font-mono text-foreground font-medium">$${price.toFixed(2)}</span>
                        <span class="inline-flex items-center gap-0.5 text-[11px] font-mono ${changeColor}">
                            ${changeIcon} ${changeSign}${change.toFixed(2)}%
                        </span>
                    </div>
                `;
            }).join('');
        }

        const tbody = document.getElementById('watchlistBody');
        if (!tbody) return;

        if (watchlist.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="p-8 text-center text-muted-foreground text-xs">
                        No stocks in watchlist. Add one above.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = watchlist.map(item => {
            const price = item.price || 0;
            const change = item.change || 0;
            const changeClass = change >= 0 ? 'text-success' : 'text-destructive';
            const changeSign = change >= 0 ? '+' : '';

            return `
                <tr class="hover:bg-muted/30 transition-colors group">
                    <td class="p-3 font-medium text-foreground">${item.symbol}</td>
                    <td class="p-3 text-right font-mono text-foreground">$${price.toFixed(2)}</td>
                    <td class="p-3 text-right font-mono ${changeClass}">${changeSign}${change.toFixed(2)}%</td>
                    <td class="p-3 text-right">
                        <button onclick="removeFromWatchlist('${item.symbol}')" class="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-destructive/10 text-destructive rounded-sm">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading watchlist:', error);
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
                const balance = (data.buying_power || 0) + (data.portfolio_value || 0);
                const elBalance = document.getElementById('headerBalance');
                if (elBalance) elBalance.innerText = formatMoney(balance);

                const elUnrealizedPL = document.getElementById('headerUnrealizedPL');
                if (elUnrealizedPL) {
                    elUnrealizedPL.innerText = (data.total_pl >= 0 ? '+' : '') + formatMoney(data.total_pl);
                    elUnrealizedPL.className = `text-sm font-semibold font-mono ${data.total_pl >= 0 ? 'text-success' : 'text-destructive'}`;
                }

                const elDayPL = document.getElementById('headerDayPL');
                if (elDayPL) {
                    elDayPL.innerText = (data.total_pl >= 0 ? '+' : '') + formatMoney(data.total_pl);
                    elDayPL.className = `text-sm font-semibold font-mono ${data.total_pl >= 0 ? 'text-success' : 'text-destructive'}`;
                }
            }
        })
        .catch(err => console.error("HTTP Status Error:", err));
}

function addLog(source, message, level = 'info') {
    const targetIds = ['activity-log-list'];

    targetIds.forEach(id => {
        const logList = document.getElementById(id);
        if (!logList) return;

        // Create log item
        const div = document.createElement('div');

        // Style based on level
        let levelColor = 'text-muted-foreground';
        let icon = 'info';
        let bgColor = 'bg-muted/30';

        if (level === 'success') { levelColor = 'text-success'; icon = 'check-circle'; bgColor = 'bg-success/5'; }
        if (level === 'warning') { levelColor = 'text-warning'; icon = 'alert-triangle'; bgColor = 'bg-warning/5'; }
        if (level === 'error') { levelColor = 'text-destructive'; icon = 'x-circle'; bgColor = 'bg-destructive/5'; }

        div.className = `p-2.5 rounded-md border border-border/50 text-xs ${bgColor} animate-in fade-in slide-in-from-right-4 duration-300`;

        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

        div.innerHTML = `
            <div class="flex justify-between items-start mb-1">
                <span class="font-semibold text-[10px] uppercase tracking-wider ${levelColor}">${source}</span>
                <span class="text-[10px] text-muted-foreground/60 font-mono">${time}</span>
            </div>
            <p class="text-foreground/90 leading-snug">${message}</p>
        `;

        logList.prepend(div);

        // Force scroll to top (using timeout to ensure DOM update)
        setTimeout(() => {
            logList.scrollTop = 0;
        }, 10);

        // Limit log size (remove from bottom)
        if (logList.children.length > 100) {
            logList.removeChild(logList.lastChild);
        }
    });
}


function updateActivityStatus(statusText) {
    const statusEl = document.getElementById('activity-status');
    if (statusEl) {
        statusEl.textContent = statusText;
        // visual flare
        statusEl.classList.remove('text-muted-foreground');
        statusEl.classList.add('text-primary');
        setTimeout(() => {
            statusEl.classList.remove('text-primary');
            statusEl.classList.add('text-muted-foreground');
        }, 1000);
    }
}

function formatMoney(amount) {
    if (typeof amount !== 'number') return '$0.00';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

