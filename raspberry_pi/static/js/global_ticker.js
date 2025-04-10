/**
 * Global Ticker for Prayer Alarm System
 * Displays adhan notifications and other important messages at the bottom of all pages
 * Matches the orange Adhan ticker style and content from the Prayer Times page
 */

// Global state
const tickerState = {
    isAdhanPlaying: false,
    currentMessage: '',
    wsConnection: null,
    tickerElement: null,
    tickerContentElement: null,
    currentPrayerTimes: []
};

// Initialize the global ticker
function initGlobalTicker() {
    console.log('Initializing global ticker...');
    
    // Check if user has previously closed the ticker
    const isTickerHidden = localStorage.getItem('global_ticker_hidden') === 'true';
    
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
        tickerState.tickerContentElement.innerHTML = '<i class="fas fa-info-circle"></i> Waiting for prayer time information... <i class="fas fa-clock"></i>';
        
        // Create close button
        const closeButton = document.createElement('button');
        closeButton.className = 'ticker-close-btn';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', function() {
            hideGlobalTicker();
            // Save preference in localStorage
            localStorage.setItem('global_ticker_hidden', 'true');
        });
        
        // Add content and close button to ticker
        tickerState.tickerElement.appendChild(tickerState.tickerContentElement);
        tickerState.tickerElement.appendChild(closeButton);
        
        // Add ticker to body and check if it should be hidden
        document.body.appendChild(tickerState.tickerElement);
        
        // If user previously closed the ticker, keep it hidden
        if (isTickerHidden) {
            hideGlobalTicker();
        }
        
        // Add CSS for the ticker - using orange adhan ticker style
        const style = document.createElement('style');
        style.textContent = `
            .global-ticker {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background-color: var(--accent-color, #FF9800); /* Orange color from accent-color variable */
                color: white;
                padding: 10px 15px;
                z-index: 9999;
                overflow: hidden;
                box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.2);
                transition: transform 0.5s ease;
            }
            
            .global-ticker.hidden {
                transform: translateY(100%);
            }
            
            .global-ticker .ticker-content {
                display: inline-block;
                white-space: nowrap;
                animation: ticker-slide 20s linear infinite;
                padding-right: 50px;
            }
            
            .adhan-playing .global-ticker {
                background-color: var(--error-color, #F44336); /* Red color during adhan */
                font-weight: bold;
            }
            
            @keyframes ticker-slide {
                0% { transform: translateX(100%); }
                100% { transform: translateX(-100%); }
            }
            
            .global-ticker .ticker-content i {
                margin: 0 5px;
            }
            
            .global-ticker .ticker-close-btn {
                position: absolute;
                top: 50%;
                right: 10px;
                transform: translateY(-50%);
                background: rgba(0, 0, 0, 0.2);
                color: white;
                border: none;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                line-height: 24px;
                font-size: 16px;
                text-align: center;
                cursor: pointer;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.3s;
            }
            
            .global-ticker .ticker-close-btn:hover {
                background: rgba(0, 0, 0, 0.4);
            }
            
            .global-ticker .stop-audio-btn {
                display: inline-block;
                margin-left: 15px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 14px;
                cursor: pointer;
                transition: background-color 0.3s;
                vertical-align: middle;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
            }
            
            .global-ticker .stop-audio-btn:hover {
                background-color: #d32f2f;
            }
            
            .global-ticker .stop-audio-btn i {
                margin-right: 4px;
            }
            
            @media (max-width: 768px) {
                .global-ticker {
                    font-size: 14px;
                    padding: 8px 10px;
                }
                
                .global-ticker .ticker-close-btn {
                    width: 20px;
                    height: 20px;
                    line-height: 20px;
                    font-size: 14px;
                }
                
                .global-ticker .stop-audio-btn {
                    padding: 2px 6px;
                    font-size: 12px;
                    margin-left: 8px;
                }
            }
        `;
        document.head.appendChild(style);
    } else {
        tickerState.tickerElement = document.getElementById('global-ticker');
        tickerState.tickerContentElement = document.getElementById('global-ticker-content');
        
        // If user previously closed the ticker, keep it hidden
        if (isTickerHidden) {
            hideGlobalTicker();
        }
    }
    
    // Fetch prayer times for the ticker
    fetchPrayerTimesForTicker();
    
    // Setup WebSocket connection
    setupGlobalWebSocket();
    
    // Start ticker update interval - update every minute
    setInterval(updateTickerContent, 60000);
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
        
        // Update with Adhan ticker style content
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-volume-up"></i> 
            ADHAN PLAYING NOW: <strong>${prayerName}</strong> Prayer 
            <i class="fas fa-volume-up"></i>
            <button class="stop-audio-btn" onclick="stopAudio(); return false;"><i class="fas fa-stop"></i> Stop</button>
        `;
        
        // Always show the ticker for adhan notifications regardless of user preference
        showGlobalTicker();
        
        // Clear any existing timeout
        if (tickerState.adhanPlayingTimeoutId) {
            clearTimeout(tickerState.adhanPlayingTimeoutId);
        }
        
        // Set a timeout to reset the adhan playing status after 5 minutes
        tickerState.adhanPlayingTimeoutId = setTimeout(() => {
            document.body.classList.remove('adhan-playing');
            tickerState.isAdhanPlaying = false;
            
            // Refresh prayer times and update ticker
            fetchPrayerTimesForTicker();
        }, 5 * 60 * 1000); // 5 minutes
    } else if (message && message.type === 'prayer_times_updated') {
        // Prayer times were updated, refresh our data
        console.log('Prayer times update notification received via WebSocket');
        fetchPrayerTimesForTicker();
    }
}

// Fetch prayer times for ticker
function fetchPrayerTimesForTicker() {
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    console.log('Fetching prayer times for ticker...');
    
    fetch('/prayer-times')
        .then(response => response.json())
        .then(prayerTimes => {
            console.log('Prayer times fetched for ticker:', prayerTimes);
            tickerState.currentPrayerTimes = prayerTimes;
            updateTickerContent();
        })
        .catch(error => {
            console.error('Error fetching prayer times for ticker:', error);
            // Show error in ticker
            if (tickerState.tickerContentElement) {
                tickerState.tickerContentElement.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i> 
                    Error loading prayer times 
                    <i class="fas fa-clock"></i> Current time: ${new Date().toLocaleTimeString()}
                `;
            }
        });
}

// Update the ticker content with prayer time information
function updateTickerContent() {
    if (!tickerState.tickerContentElement) {
        console.error('Ticker content element not found');
        return;
    }
    
    const now = new Date();
    const prayerTimes = tickerState.currentPrayerTimes;
    
    // Validate that prayerTimes exists and is an array
    if (!prayerTimes || !Array.isArray(prayerTimes) || prayerTimes.length === 0) {
        console.log('No prayer times available for ticker update');
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-info-circle"></i> 
            Waiting for prayer time information... 
            <i class="fas fa-clock"></i> Current time: ${new Date().toLocaleTimeString()}
        `;
        return;
    }
    
    // Find the next prayer
    let nextPrayer = null;
    for (let i = 0; i < prayerTimes.length; i++) {
        if (!prayerTimes[i] || !prayerTimes[i].time) {
            console.error('Invalid prayer time entry at index', i, prayerTimes[i]);
            continue;
        }
        
        const prayerTime = new Date(prayerTimes[i].time);
        if (prayerTime > now) {
            nextPrayer = prayerTimes[i];
            break;
        }
    }
    
    if (nextPrayer) {
        const prayerTime = new Date(nextPrayer.time);
        const timeString = prayerTime.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
        
        // Calculate time until next prayer
        const timeDiff = prayerTime - now;
        const hours = Math.floor(timeDiff / (1000 * 60 * 60));
        const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
        
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-mosque"></i> Next Prayer: <strong>${nextPrayer.name}</strong> at ${timeString} 
            (${hours > 0 ? hours + ' hours and ' : ''}${minutes} minutes from now) 
            <i class="fas fa-clock"></i> Current time: ${new Date().toLocaleTimeString()}
        `;
        
        // Check if it's adhan time (within 1 minute)
        if (timeDiff <= 60 * 1000) {
            document.body.classList.add('adhan-playing');
            tickerState.tickerContentElement.innerHTML = `
                <i class="fas fa-volume-up"></i> 
                ADHAN PLAYING NOW: <strong>${nextPrayer.name}</strong> Prayer 
                <i class="fas fa-volume-up"></i>
                <button class="stop-audio-btn" onclick="stopAudio(); return false;"><i class="fas fa-stop"></i> Stop</button>
            `;
            tickerState.isAdhanPlaying = true;
            
            // Always show ticker for adhan
            showGlobalTicker();
        } else {
            if (!tickerState.isAdhanPlaying) {
                document.body.classList.remove('adhan-playing');
            }
        }
    } else {
        // All prayers for today have passed
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-moon"></i> All prayers for today have passed. 
            <i class="fas fa-clock"></i> Current time: ${new Date().toLocaleTimeString()}
        `;
        if (!tickerState.isAdhanPlaying) {
            document.body.classList.remove('adhan-playing');
        }
    }
}

// Update the ticker content with a custom message
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

// Function to stop all playing audio
function stopAudio() {
    console.log('Stopping all audio playback');
    fetch('/stop-audio', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Audio stopped successfully:', data);
        // Update the UI to reflect that audio is no longer playing
        document.body.classList.remove('adhan-playing');
        tickerState.isAdhanPlaying = false;
        
        // Refresh prayer times and update ticker
        fetchPrayerTimesForTicker();
    })
    .catch(error => {
        console.error('Error stopping audio:', error);
    });
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', initGlobalTicker);