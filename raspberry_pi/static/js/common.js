// Common JavaScript functions for Prayer Alarm Web Interface

// Update current time display
function updateCurrentTime() {
    const currentTimeElement = document.getElementById('current-time');
    if (currentTimeElement) {
        const now = new Date();
        const options = { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        };
        currentTimeElement.textContent = now.toLocaleDateString('en-US', options);
    }
}

// Format time from a date string
function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// Format date as YYYY-MM-DD
function formatDateYMD(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Show a notification
function showNotification(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Make an API request with error handling
async function apiRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'An error occurred');
        }
        
        return result;
    } catch (error) {
        console.error('API request error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// Initialize common elements
document.addEventListener('DOMContentLoaded', function() {
    // Start updating time if the element exists
    if (document.getElementById('current-time')) {
        updateCurrentTime();
        setInterval(updateCurrentTime, 1000);
    }
    
    // Add form submission handling
    const forms = document.querySelectorAll('form.api-form');
    forms.forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(form);
            const data = {};
            
            formData.forEach((value, key) => {
                // Handle checkbox values
                if (form.elements[key].type === 'checkbox') {
                    data[key] = form.elements[key].checked;
                } else {
                    data[key] = value;
                }
            });
            
            try {
                const url = form.getAttribute('data-api-url') || form.action;
                const method = form.getAttribute('data-api-method') || 'POST';
                
                const result = await apiRequest(url, method, data);
                
                if (result.status === 'success') {
                    showNotification(result.message || 'Operation completed successfully');
                    
                    // Check if we need to redirect
                    const redirect = form.getAttribute('data-redirect');
                    if (redirect) {
                        window.location.href = redirect;
                    }
                }
            } catch (error) {
                // Error is already handled in apiRequest
            }
        });
    });
});
