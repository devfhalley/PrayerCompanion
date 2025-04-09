/**
 * Global Ticker for Prayer Alarm System
 * Displays adhan notifications and other important messages at the bottom of all pages
 */

// Global state
const tickerState = {
    isAdhanPlaying: false,
    currentMessage: '',
    wsConnection: null,
    tickerElement: null,
    tickerContentElement: null
};

// Initialize the global ticker
function initGlobalTicker() {
    console.log('Initializing global ticker...');
    
    // Create ticker element if it doesn't exist
    if (!document.getElementById('global-ticker')) {
        // Create the ticker container
        tickerState.tickerElement = document.createElement('div');
        tickerState.tickerElement.id = 'global-ticker';
        tickerState.tickerElement.className = 'global-ticker';
        
        // Create the ticker content
        tickerState.tickerContentElement = document.createElement('div');
        tickerState.tickerContentElement.id = 'global-ticker-content';
        tickerState.tickerContentElement.className = 'ticker-content';
        tickerState.tickerContentElement.innerHTML = 'Prayer Alarm System';
        
        // Add content to ticker
        tickerState.tickerElement.appendChild(tickerState.tickerContentElement);
        
        // Add ticker to body
        document.body.appendChild(tickerState.tickerElement);
        
        // Add CSS for the ticker
        const style = document.createElement('style');
        style.textContent = `
            .global-ticker {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 10px 0;
                z-index: 9999;
                text-align: center;
                font-size: 16px;
                box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.2);
                transition: transform 0.5s ease;
            }
            
            .global-ticker.hidden {
                transform: translateY(100%);
            }
            
            .global-ticker .ticker-content {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                animation: ticker-scroll 20s linear infinite;
                padding: 0 20px;
            }
            
            .adhan-playing .global-ticker {
                background-color: #4CAF50;
                font-weight: bold;
            }
            
            @keyframes ticker-scroll {
                0% { transform: translateX(100%); }
                100% { transform: translateX(-100%); }
            }
            
            @media (max-width: 768px) {
                .global-ticker {
                    font-size: 14px;
                    padding: 8px 0;
                }
            }
        `;
        document.head.appendChild(style);
    } else {
        tickerState.tickerElement = document.getElementById('global-ticker');
        tickerState.tickerContentElement = document.getElementById('global-ticker-content');
    }
    
    // Setup WebSocket connection
    setupGlobalWebSocket();
    
    // Initial update
    updateGlobalTicker('Prayer Alarm System');
}

// Setup WebSocket connection for real-time updates
function setupGlobalWebSocket() {
    try {
        // Close existing connection if it exists
        if (tickerState.wsConnection) {
            try {
                if ([WebSocket.OPEN, WebSocket.CONNECTING].includes(tickerState.wsConnection.readyState)) {
                    tickerState.wsConnection.close();
                }
            } catch (e) {
                console.warn('Error closing existing WebSocket connection:', e);
            }
        }
        
        // Create new connection with explicit error handling
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            // Fallback to IP if needed
            const wsUrl = `${protocol}//${host}/ws`;
            console.log('Setting up global WebSocket connection to:', wsUrl);
            
            tickerState.wsConnection = new WebSocket(wsUrl);
            
            // Handle connection was established
            tickerState.wsConnection.onopen = function() {
                console.log('Global WebSocket connection established successfully');
                
                // Reset reconnection attempts on successful connection
                if (tickerState.reconnectAttempts) {
                    tickerState.reconnectAttempts = 0;
                }
                
                // Send a ping message to verify connection is working
                try {
                    tickerState.wsConnection.send(JSON.stringify({
                        type: 'ping',
                        timestamp: Date.now()
                    }));
                } catch (e) {
                    console.warn('Failed to send ping message:', e);
                }
            };
            
            // Handle incoming messages
            tickerState.wsConnection.onmessage = function(event) {
                try {
                    if (!event || !event.data) {
                        console.warn('Received empty WebSocket message');
                        return;
                    }
                    
                    const message = JSON.parse(event.data);
                    console.log('Global WebSocket message received:', message);
                    
                    // Special case for ping response
                    if (message.type === 'pong') {
                        console.log('Received pong response from server');
                        return;
                    }
                    
                    handleGlobalWebSocketMessage(message);
                } catch (error) {
                    console.error('Error processing global WebSocket message:', error);
                }
            };
            
            // Track reconnection attempts
            if (!tickerState.reconnectAttempts) {
                tickerState.reconnectAttempts = 0;
            }
            
            // Connection was closed
            tickerState.wsConnection.onclose = function(event) {
                console.log(`Global WebSocket connection closed (code: ${event.code}, reason: ${event.reason}), attempting to reconnect...`);
                
                // Implement exponential backoff for reconnection
                tickerState.reconnectAttempts++;
                const delay = Math.min(30000, Math.pow(1.5, tickerState.reconnectAttempts) * 1000);
                console.log(`Reconnecting in ${Math.round(delay/1000)} seconds (attempt ${tickerState.reconnectAttempts})`);
                
                setTimeout(setupGlobalWebSocket, delay);
            };
            
            // Error occurred
            tickerState.wsConnection.onerror = function(error) {
                console.error('Global WebSocket error:', error);
                // Don't attempt to reconnect here, let the onclose handler do it
            };
        } catch (socketError) {
            console.error('Failed to create WebSocket connection:', socketError);
            // Implement exponential backoff for reconnection
            if (!tickerState.reconnectAttempts) {
                tickerState.reconnectAttempts = 0;
            }
            tickerState.reconnectAttempts++;
            const delay = Math.min(30000, Math.pow(1.5, tickerState.reconnectAttempts) * 1000);
            console.log(`Will retry WebSocket connection in ${Math.round(delay/1000)} seconds (attempt ${tickerState.reconnectAttempts})`);
            setTimeout(setupGlobalWebSocket, delay);
        }
    } catch (outerError) {
        console.error('Critical error in setupGlobalWebSocket:', outerError);
        setTimeout(setupGlobalWebSocket, 10000);
    }
}

// Handle WebSocket messages
function handleGlobalWebSocketMessage(message) {
    // Handle adhan playing message
    if (message && message.type === 'adhan_playing') {
        console.log('Global adhan playing notification received:', message);
        
        document.body.classList.add('adhan-playing');
        tickerState.isAdhanPlaying = true;
        
        const prayerName = message.prayer || 'Unknown';
        const prayerTime = message.time || '';
        
        updateGlobalTicker(`🔊 ADHAN PLAYING NOW: ${prayerName} Prayer at ${prayerTime} 🔊`);
        
        // Clear any existing timeout
        if (tickerState.adhanPlayingTimeoutId) {
            clearTimeout(tickerState.adhanPlayingTimeoutId);
        }
        
        // Set a timeout to reset the adhan playing status after 5 minutes
        tickerState.adhanPlayingTimeoutId = setTimeout(() => {
            document.body.classList.remove('adhan-playing');
            tickerState.isAdhanPlaying = false;
            updateGlobalTicker('Prayer Alarm System');
        }, 5 * 60 * 1000); // 5 minutes
    }
}

// Update the ticker content
function updateGlobalTicker(message) {
    if (tickerState.tickerContentElement) {
        tickerState.currentMessage = message;
        tickerState.tickerContentElement.innerHTML = message;
    }
}

// Show the ticker
function showGlobalTicker() {
    if (tickerState.tickerElement) {
        tickerState.tickerElement.classList.remove('hidden');
    }
}

// Hide the ticker
function hideGlobalTicker() {
    if (tickerState.tickerElement) {
        tickerState.tickerElement.classList.add('hidden');
    }
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', initGlobalTicker);