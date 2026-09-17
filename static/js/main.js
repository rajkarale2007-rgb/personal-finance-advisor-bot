document.addEventListener('DOMContentLoaded', () => {
    let activeContributeGoalId = null;

    // Elements
    const monthPicker = document.getElementById('monthPicker');
    const incomeDate = document.getElementById('incomeDate');
    const expenseDate = document.getElementById('expenseDate');
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const toggleGoalFormBtn = document.getElementById('toggleGoalFormBtn');
    const goalForm = document.getElementById('goalForm');
    const contributeModal = document.getElementById('contributeModal');
    const cancelContributeBtn = document.getElementById('cancelContributeBtn');
    const confirmContributeBtn = document.getElementById('confirmContributeBtn');
    const contributeAmountInput = document.getElementById('contributeAmount');

    // Default dates
    const currentDate = new Date();
    const currentYearMonth = currentDate.toISOString().slice(0, 7);
    const currentFullDate = currentDate.toISOString().slice(0, 10);

    if (monthPicker) monthPicker.value = currentYearMonth;
    if (incomeDate) incomeDate.value = currentFullDate;
    if (expenseDate) expenseDate.value = currentFullDate;

    // Load initial dashboard
    if (monthPicker) {
        loadDashboardData(monthPicker.value);

        monthPicker.addEventListener('change', (e) => {
            loadDashboardData(e.target.value);
        });
    }

    // Export CSV Handler
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => {
            const activeMonth = monthPicker ? monthPicker.value : currentYearMonth;
            window.location.href = `/api/export/csv?month=${activeMonth}`;
        });
    }

    // Toggle Goal Form Visibility
    if (toggleGoalFormBtn && goalForm) {
        toggleGoalFormBtn.addEventListener('click', () => {
            const isHidden = goalForm.style.display === 'none' || !goalForm.style.display;
            goalForm.style.display = isHidden ? 'block' : 'none';
            toggleGoalFormBtn.textContent = isHidden ? '✕ Close' : '+ New Goal';
        });
    }

    // Handle Income Form Submission
    const incomeForm = document.getElementById('incomeForm');
    if (incomeForm) {
        incomeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const month = monthPicker.value;
            const source = document.getElementById('incomeSource').value;
            const amount = parseFloat(document.getElementById('incomeAmount').value);
            const date = document.getElementById('incomeDate').value;

            try {
                const response = await fetch('/api/income', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ month, source, amount, date })
                });

                if (response.ok) {
                    loadDashboardData(month);
                    document.getElementById('incomeSource').value = '';
                    document.getElementById('incomeAmount').value = '';
                } else {
                    const err = await response.json();
                    alert(err.error || 'Failed to record income.');
                }
            } catch (error) {
                console.error('Error saving income:', error);
            }
        });
    }

    // Handle Expense Form Submission
    const expenseForm = document.getElementById('expenseForm');
    if (expenseForm) {
        expenseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const month = monthPicker.value;
            const date = document.getElementById('expenseDate').value;
            const category = document.getElementById('expenseCategory').value;
            const amount = parseFloat(document.getElementById('expenseAmount').value);
            const description = document.getElementById('expenseDescription').value;

            try {
                const response = await fetch('/api/expense', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ month, date, category, amount, description })
                });

                if (response.ok) {
                    loadDashboardData(month);
                    document.getElementById('expenseAmount').value = '';
                    document.getElementById('expenseDescription').value = '';
                } else {
                    const err = await response.json();
                    alert(err.error || 'Failed to add expense.');
                }
            } catch (error) {
                console.error('Error adding expense:', error);
            }
        });
    }

    // Handle Goal Form Submission
    if (goalForm) {
        goalForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('goalName').value;
            const target_amount = parseFloat(document.getElementById('goalTarget').value);
            const deadline = document.getElementById('goalDeadline').value;

            try {
                const response = await fetch('/api/goals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, target_amount, deadline })
                });

                if (response.ok) {
                    loadDashboardData(monthPicker.value);
                    document.getElementById('goalName').value = '';
                    document.getElementById('goalTarget').value = '';
                    document.getElementById('goalDeadline').value = '';
                    goalForm.style.display = 'none';
                    if (toggleGoalFormBtn) toggleGoalFormBtn.textContent = '+ New Goal';
                } else {
                    const err = await response.json();
                    alert(err.error || 'Failed to create goal.');
                }
            } catch (error) {
                console.error('Error adding goal:', error);
            }
        });
    }

    // Contribute Modal Cancel
    if (cancelContributeBtn && contributeModal) {
        cancelContributeBtn.addEventListener('click', () => {
            contributeModal.classList.remove('active');
            activeContributeGoalId = null;
            contributeAmountInput.value = '';
        });
    }

    // Contribute Modal Confirm
    if (confirmContributeBtn && contributeModal) {
        confirmContributeBtn.addEventListener('click', async () => {
            if (!activeContributeGoalId) return;
            const amount = parseFloat(contributeAmountInput.value);
            if (!amount || amount <= 0) {
                alert('Please enter a valid contribution amount.');
                return;
            }

            try {
                const response = await fetch(`/api/goals/${activeContributeGoalId}/contribute`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount })
                });

                if (response.ok) {
                    contributeModal.classList.remove('active');
                    activeContributeGoalId = null;
                    contributeAmountInput.value = '';
                    loadDashboardData(monthPicker.value);
                } else {
                    const err = await response.json();
                    alert(err.error || 'Failed to contribute to goal.');
                }
            } catch (error) {
                console.error('Error contributing to goal:', error);
            }
        });
    }

    // Expose helpers to window for inline onclick handlers
    window.deleteIncome = deleteIncome;
    window.deleteExpense = deleteExpense;
    window.deleteGoal = deleteGoal;
    window.openContributeModal = (goalId, goalName) => {
        activeContributeGoalId = goalId;
        document.getElementById('modalGoalTitle').textContent = `Contribute to: ${goalName}`;
        contributeModal.classList.add('active');
        contributeAmountInput.focus();
    };
});

// Fetch and Render Dashboard Data
async function loadDashboardData(month) {
    try {
        const response = await fetch(`/api/data?month=${month}`);
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();

        // 1. Update Metrics Cards
        document.getElementById('totalIncome').textContent = `$${data.income.toFixed(2)}`;
        document.getElementById('totalExpenses').textContent = `$${data.total_expenses.toFixed(2)}`;

        const netSavingsElem = document.getElementById('netSavings');
        netSavingsElem.textContent = `$${data.net_savings.toFixed(2)}`;
        netSavingsElem.className = `amount ${data.net_savings >= 0 ? 'savings-text' : 'expense-text'}`;

        // 2. Update Income Streams List
        const incomeStreamsList = document.getElementById('incomeStreamsList');
        incomeStreamsList.innerHTML = '';
        if (data.income_sources.length === 0) {
            incomeStreamsList.innerHTML = `<p class="text-muted">No income streams logged yet.</p>`;
        } else {
            data.income_sources.forEach(inc => {
                const div = document.createElement('div');
                div.className = 'stream-row';
                div.innerHTML = `
                    <div class="stream-left">
                        <span class="stream-source">${escapeHtml(inc.source)}</span>
                        <span class="stream-date">${inc.date}</span>
                    </div>
                    <div class="stream-right">
                        <span class="stream-amt">+$${inc.amount.toFixed(2)}</span>
                        <button class="btn btn-danger btn-sm" onclick="deleteIncome(${inc.id})">✕</button>
                    </div>
                `;
                incomeStreamsList.appendChild(div);
            });
        }

        // 3. Update Goals List
        const goalsContainer = document.getElementById('goalsContainer');
        goalsContainer.innerHTML = '';
        if (data.goals.length === 0) {
            goalsContainer.innerHTML = `<p class="text-muted">No savings goals created yet. Set a target to build financial momentum!</p>`;
        } else {
            data.goals.forEach(g => {
                const card = document.createElement('div');
                card.className = 'goal-card';
                card.innerHTML = `
                    <div class="goal-header">
                        <span class="goal-name">${escapeHtml(g.name)}</span>
                        <span class="goal-deadline">Target: ${g.deadline}</span>
                    </div>
                    <div class="goal-progress-bar">
                        <div class="goal-progress-fill" style="width: ${g.progress_pct}%"></div>
                    </div>
                    <div class="goal-footer">
                        <span><strong>$${g.current_amount.toFixed(2)}</strong> / $${g.target_amount.toFixed(2)} (${g.progress_pct}%)</span>
                        <div class="goal-actions">
                            <button class="btn btn-sm btn-outline" onclick="openContributeModal(${g.id}, '${escapeQuotes(g.name)}')">+ Add Funds</button>
                            <button class="btn btn-danger btn-sm" onclick="deleteGoal(${g.id})">Delete</button>
                        </div>
                    </div>
                `;
                goalsContainer.appendChild(card);
            });
        }

        // 4. Update Insights List & AI Engine Badge
        const aiEngineBadge = document.getElementById('aiEngineBadge');
        if (aiEngineBadge && data.ai_engine) {
            aiEngineBadge.textContent = data.ai_engine;
            if (data.ai_engine.includes('Gemini')) {
                aiEngineBadge.className = 'badge badge-ai';
            } else {
                aiEngineBadge.className = 'badge badge-local';
            }
        }

        const insightsList = document.getElementById('insightsList');
        insightsList.innerHTML = '';
        data.insights.forEach(insight => {
            const li = document.createElement('li');
            li.textContent = insight;
            insightsList.appendChild(li);
        });

        // 5. Update Expense Transactions Table
        const tableBody = document.getElementById('transactionTableBody');
        tableBody.innerHTML = '';

        if (data.transactions.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center">No transactions recorded for this month.</td></tr>`;
        } else {
            data.transactions.forEach(tx => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${tx.date}</td>
                    <td><strong>${escapeHtml(tx.category)}</strong></td>
                    <td>${escapeHtml(tx.description || '-')}</td>
                    <td>$${tx.amount.toFixed(2)}</td>
                    <td><button class="btn btn-danger btn-sm" onclick="deleteExpense(${tx.id})">Delete</button></td>
                `;
                tableBody.appendChild(row);
            });
        }

        // 6. Render Chart
        renderSpendingChart(data.category_breakdown);

    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Delete Handlers
async function deleteIncome(id) {
    if (!confirm('Are you sure you want to delete this income entry?')) return;
    try {
        const res = await fetch(`/api/income/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadDashboardData(document.getElementById('monthPicker').value);
        } else {
            alert('Failed to delete income.');
        }
    } catch (e) {
        console.error('Error deleting income:', e);
    }
}

async function deleteExpense(id) {
    if (!confirm('Are you sure you want to delete this expense?')) return;
    try {
        const res = await fetch(`/api/expense/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadDashboardData(document.getElementById('monthPicker').value);
        } else {
            alert('Failed to delete expense.');
        }
    } catch (e) {
        console.error('Error deleting expense:', e);
    }
}

async function deleteGoal(id) {
    if (!confirm('Are you sure you want to delete this savings goal?')) return;
    try {
        const res = await fetch(`/api/goals/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadDashboardData(document.getElementById('monthPicker').value);
        } else {
            alert('Failed to delete goal.');
        }
    } catch (e) {
        console.error('Error deleting goal:', e);
    }
}

// Render Chart.js
function renderSpendingChart(breakdown) {
    const ctx = document.getElementById('spendingChart').getContext('2d');
    const categories = Object.keys(breakdown);
    const amounts = Object.values(breakdown);

    if (window.spendingChartInstance) {
        window.spendingChartInstance.destroy();
    }

    if (categories.length === 0) {
        window.spendingChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['No Expenses Logged'],
                datasets: [{ data: [1], backgroundColor: ['#e2e8f0'] }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
        return;
    }

    const palette = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
        '#8b5cf6', '#06b6d4', '#ec4899', '#64748b'
    ];

    window.spendingChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: categories,
            datasets: [{
                data: amounts,
                backgroundColor: palette.slice(0, categories.length),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { family: 'Inter', size: 12 } }
                }
            }
        }
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

function escapeQuotes(str) {
    if (!str) return '';
    return str.replace(/'/g, "\\'");
}