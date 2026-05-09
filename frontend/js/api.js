const API_BASE_URL = 'http://localhost:8000';

async function fetchDashboardData() {
    try {
        const response = await fetch(`${API_BASE_URL}/analytics/dashboard`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
        return null;
    }
}

// Add other API calls here as needed
