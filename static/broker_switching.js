// ==========================================
// BROKER SWITCHING
// ==========================================

function switchBroker(broker) {
    // Hide all broker sections
    document.querySelectorAll('.broker-section').forEach(section => {
        section.style.display = 'none';
    });

    // Show selected broker section
    const selectedSection = document.getElementById(`${broker}-section`);
    if (selectedSection) {
        selectedSection.style.display = 'block';
    }

    // Update active tab
    document.querySelectorAll('.broker-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    const activeTab = document.querySelector(`[data-broker="${broker}"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }

    // Notify backend
    fetch('/api/broker/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ broker: broker })
    })
        .then(response => response.json())
        .then(data => {
            addLog(`Switched to ${broker === 'ibkr' ? 'IBKR (Advanced)' : 'Robinhood (Basic)'}`, 'info');

            // Load appropriate data
            if (broker === 'ibkr') {
                loadIBKRData();
            } else {
                requestInitialData();
            }
        })
        .catch(error => {
            console.error('Error switching broker:', error);
            addLog('Error switching broker', 'error');
        });
}

function switchToIBKR() {
    if (confirm('Switch to IBKR? Make sure TWS/IB Gateway is running.')) {
        switchBroker('ibkr');
    }
}

function loadIBKRData() {
    fetch('/api/ibkr/dashboard')
        .then(response => response.json())
        .then(data => {
            // Update stats
            document.getElementById('ibkrLongCount').textContent = data.long_count || 0;
            document.getElementById('ibkrShortCount').textContent = data.short_count || 0;
            document.getElementById('ibkrDayPnL').textContent = data.day_pnl_formatted || '$0.00';

            // Update positions table
            updateIBKRPositions(data.positions || []);
        })
        .catch(error => {
            console.error('Error loading IBKR data:', error);
            addLog('Error loading IBKR data', 'error');
        });
}

function updateIBKRPositions(positions) {
    const tbody = document.getElementById('ibkrPositionsBody');
    if (!tbody) return;

    if (positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No active positions</td></tr>';
        return;
    }

    tbody.innerHTML = positions.map(pos => `
        <tr>
            <td><strong>${pos.symbol}</strong></td>
            <td><span class="badge ${pos.side}">${pos.side.toUpperCase()}</span></td>
            <td>$${pos.entry_price.toFixed(2)}</td>
            <td>$${pos.current_price.toFixed(2)}</td>
            <td>$${pos.stop_loss.toFixed(2)}</td>
            <td>$${pos.target.toFixed(2)}</td>
            <td class="${pos.pnl >= 0 ? 'positive' : 'negative'}">$${pos.pnl.toFixed(2)}</td>
            <td>${pos.r_multiple.toFixed(2)}R</td>
        </tr>
    `).join('');
}

function toggleLevel2() {
    alert('Level 2 data viewer coming soon!');
}
