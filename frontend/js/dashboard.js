document.addEventListener('DOMContentLoaded', async () => {
    const data = await fetchDashboardData();
    if (!data) return;

    // Update summary cards
    if (data.summary) {
        document.getElementById('total-medicines').textContent = data.summary.total_medicines.toLocaleString();
        document.getElementById('low-stock').textContent = data.summary.low_stock_count;
        document.getElementById('expiry-alerts').textContent = data.summary.expiry_alert_count;
        document.getElementById('today-revenue').textContent = `₹${data.summary.today_revenue.toLocaleString()}`;
    }

    // Update recent bills
    if (data.recent_bills) {
        const tbody = document.getElementById('recent-bills-list');
        tbody.innerHTML = '';
        data.recent_bills.forEach(bill => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-outline-variant/50 hover:bg-surface-container-low transition-colors';
            
            // Format ID
            const idTd = document.createElement('td');
            idTd.className = 'py-md px-md text-primary';
            idTd.textContent = `#BL-${bill.id}`;
            tr.appendChild(idTd);

            // Format Customer
            const customerTd = document.createElement('td');
            customerTd.className = 'py-md px-md text-on-surface';
            customerTd.textContent = bill.customer_name || 'Walk-in';
            tr.appendChild(customerTd);

            // Format Amount
            const amountTd = document.createElement('td');
            amountTd.className = 'py-md px-md text-on-surface text-right';
            amountTd.textContent = `₹${bill.total_amount}`;
            tr.appendChild(amountTd);

            // Format Status (Mocking PAID for now, backend could provide actual status)
            const statusTd = document.createElement('td');
            statusTd.className = 'py-md px-md text-center';
            statusTd.innerHTML = `<span class="inline-flex items-center px-2 py-1 rounded bg-secondary-container/30 text-on-secondary-container text-[10px] font-bold tracking-wider">PAID</span>`;
            tr.appendChild(statusTd);

            tbody.appendChild(tr);
        });
    }

    // Note: The chart will remain mocked for now, but could be updated using a charting library and data.revenue_trend
});
