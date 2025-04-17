/**
 * Global Ticker for Prayer Alarm System
 * Displays adhan notifications and other important messages at the bottom of all pages
 * Matches the orange Adhan ticker style and content from the Prayer Times page
 */

// Function to save ticker state to localStorage
function saveTickerState() {
    const stateToSave = {
        isAdhanPlaying: tickerState.isAdhanPlaying,
        isAlarmPlaying: tickerState.isAlarmPlaying,
        isMurattalPlaying: tickerState.isMurattalPlaying,
        currentMessage: tickerState.currentMessage,
        adhanInfo: tickerState.adhanInfo,
        alarmInfo: tickerState.alarmInfo,
        murattalInfo: tickerState.murattalInfo,
        lastUpdated: new Date().getTime()
    };
    localStorage.setItem('global_ticker_state', JSON.stringify(stateToSave));
}

// Function to load ticker state from localStorage
function loadTickerState() {
    try {
        const savedState = localStorage.getItem('global_ticker_state');
        if (savedState) {
            const parsedState = JSON.parse(savedState);
            
            // Only restore state if it's recent (less than 5 minutes old)
            const now = new Date().getTime();
            const fiveMinutes = 5 * 60 * 1000;
            if (parsedState.lastUpdated && (now - parsedState.lastUpdated < fiveMinutes)) {
                tickerState.isAdhanPlaying = parsedState.isAdhanPlaying || false;
                tickerState.isAlarmPlaying = parsedState.isAlarmPlaying || false;
                tickerState.isMurattalPlaying = parsedState.isMurattalPlaying || false;
                tickerState.currentMessage = parsedState.currentMessage || '';
                tickerState.adhanInfo = parsedState.adhanInfo;
                tickerState.alarmInfo = parsedState.alarmInfo;
                tickerState.murattalInfo = parsedState.murattalInfo;
                
                // Update body classes to match saved state
                if (tickerState.isAdhanPlaying) {
                    document.body.classList.add('adhan-playing');
                }
                if (tickerState.isAlarmPlaying) {
                    document.body.classList.add('alarm-playing');
                }
                if (tickerState.isMurattalPlaying) {
                    document.body.classList.add('murattal-playing');
                }
                
                return true;
            }
        }
    } catch (e) {
        console.error('Error loading ticker state from localStorage:', e);
    }
    return false;
}

// Update ticker content based on saved state
function updateTickerFromSavedState() {
    if (tickerState.isAdhanPlaying && tickerState.adhanInfo) {
        const prayerName = tickerState.adhanInfo.prayer || 'Unknown';
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-volume-up"></i> 
            ADHAN PLAYING NOW: <strong>${prayerName}</strong> Prayer 
            <i class="fas fa-volume-up"></i>
            <button class="stop-audio-btn" onclick="stopAudio(); return false;"><i class="fas fa-stop"></i> Stop</button>
        `;
        showGlobalTicker();
    } 
    else if (tickerState.isAlarmPlaying && tickerState.alarmInfo) {
        const alarmLabel = tickerState.alarmInfo.alarm_label || 'Alarm';
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-bell"></i> 
            ALARM: <strong>${alarmLabel}</strong>
            <i class="fas fa-bell"></i>
            <button class="stop-audio-btn" onclick="stopAudio(); return false;"><i class="fas fa-stop"></i> Stop</button>
        `;
        showGlobalTicker();
    }
    else if (tickerState.isMurattalPlaying && tickerState.murattalInfo) {
        const murattalName = tickerState.murattalInfo.murattal_name || 'Murattal';
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-music"></i> 
            MURATTAL PLAYING: <strong>${murattalName}</strong>
            <i class="fas fa-music"></i>
            <button class="stop-audio-btn" onclick="stopAudio(); return false;"><i class="fas fa-stop"></i> Stop</button>
        `;
        showGlobalTicker();
    }
}

// Global state
const tickerState = {
    isAdhanPlaying: false,
    isAlarmPlaying: false,
    isMurattalPlaying: false,
    alarmPlayingTimeoutId: null,
    adhanPlayingTimeoutId: null,
    murattalPlayingTimeoutId: null,
    currentMessage: '',
    wsConnection: null,
    tickerElement: null,
    tickerContentElement: null,
    currentPrayerTimes: [],
    reconnectAttempts: 0,
    // Additional state for details
    adhanInfo: null, // Will hold prayer name when adhan is playing
    alarmInfo: null, // Will hold alarm label when alarm is playing
    murattalInfo: null // Will hold murattal name when murattal is playing
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
            
            .alarm-playing .global-ticker {
                background-color: var(--warning-color, #FF9800); /* Orange color during alarm */
                font-weight: bold;
            }
            
            .murattal-playing .global-ticker {
                background-color: var(--success-color, #4CAF50); /* Green color during murattal */
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
    
    // Load saved state from localStorage
    const stateLoaded = loadTickerState();
    if (stateLoaded) {
        // Update ticker content based on loaded state
        updateTickerFromSavedState();
    }
}

// Setup WebSocket connection for real-time updates
function setupGlobalWebSocket() {
    // Use the isReplitEnvironment helper function if available, otherwise fallback to simple check
    const inReplitEnv = (typeof isReplitEnvironment === 'function') ? 
                         isReplitEnvironment() : 
                         window.location.host.includes('replit');
    
    // In Replit, don't even attempt to connect - WebSockets don't work well
    if (inReplitEnv) {
        console.log('Replit environment detected in global_ticker.js - WebSockets are disabled');
        console.info('Real-time updates via WebSockets are only available when deployed');
        tickerState.wsDisabled = true;
        return;
    }
    
    // Also check if WebSockets are already disabled by websocket_client.js
    if (window.webSocketsDisabled === true) {
        console.log('WebSockets already disabled by websocket_client.js');
        tickerState.wsDisabled = true;
        return;
    }
    
    // Below this point is only executed in non-Replit environments
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
            // Use the WebSocket URL helper function which handles different environments
            if (typeof getWebSocketUrl === 'function') {
                // If websocket_client.js is loaded, use its helper function
                const wsUrl = getWebSocketUrl();
                console.log('Setting up global WebSocket connection to:', wsUrl);
                tickerState.wsConnection = new WebSocket(wsUrl);
            } else {
                // Fallback to direct URL construction if the helper isn't available
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.host;
                const wsUrl = `${protocol}//${host}/ws`;
                console.log('Setting up global WebSocket connection to:', wsUrl);
                tickerState.wsConnection = new WebSocket(wsUrl);
            }
            
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
                console.log(`Global WebSocket connection closed (code: ${event.code}, reason: ${event.reason})`);
                
                // Skip reconnection if explicitly disabled
                if (tickerState.wsDisabled) {
                    console.info("WebSocket reconnection disabled");
                    return;
                }
                
                // Implement exponential backoff for reconnection
                tickerState.reconnectAttempts++;
                const delay = Math.min(30000, Math.pow(1.5, tickerState.reconnectAttempts) * 1000);
                console.log(`Reconnecting in ${Math.round(delay/1000)} seconds (attempt ${tickerState.reconnectAttempts})`);
                
                setTimeout(setupGlobalWebSocket, delay);
            };
            
            // Error occurred
            tickerState.wsConnection.onerror = function(error) {
                console.warn('WebSocket error occurred:', error);
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
        
        // Increment reconnect counter
        if (!tickerState.reconnectAttempts) {
            tickerState.reconnectAttempts = 0;
        }
        tickerState.reconnectAttempts++;
        
        // Add a longer delay for critical errors
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
        tickerState.adhanInfo = {
            prayer: message.prayer || 'Unknown',
            timestamp: message.timestamp || Date.now()
        };
        
        const prayerName = tickerState.adhanInfo.prayer;
        
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
            tickerState.adhanInfo = null;
            
            // Save state after changes
            saveTickerState();
            
            // Refresh prayer times and update ticker
            fetchPrayerTimesForTicker();
        }, 5 * 60 * 1000); // 5 minutes
        
        // Save state to localStorage
        saveTickerState();
    } 
    // Handle alarm playing message
    else if (message && message.type === 'alarm_playing') {
        console.log('Global alarm playing notification received:', message);
        
        document.body.classList.add('alarm-playing');
        tickerState.isAlarmPlaying = true;
        tickerState.alarmInfo = {
            alarm_label: message.alarm_label || 'Alarm',
            alarm_id: message.alarm_id,
            timestamp: message.timestamp || Date.now()
        };
        
        const alarmLabel = tickerState.alarmInfo.alarm_label;
        
        // Update with Alarm ticker style content
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-bell"></i> 
            ALARM: <strong>${alarmLabel}</strong>
            <i class="fas fa-bell"></i>
            <button class="stop-audio-btn" onclick="stopAudio(); return false;"><i class="fas fa-stop"></i> Stop</button>
        `;
        
        // Always show the ticker for alarm notifications regardless of user preference
        showGlobalTicker();
        
        // Clear any existing timeout
        if (tickerState.alarmPlayingTimeoutId) {
            clearTimeout(tickerState.alarmPlayingTimeoutId);
        }
        
        // Set a timeout to reset the alarm playing status after 5 minutes
        tickerState.alarmPlayingTimeoutId = setTimeout(() => {
            document.body.classList.remove('alarm-playing');
            tickerState.isAlarmPlaying = false;
            tickerState.alarmInfo = null;
            
            // Save state after changes
            saveTickerState();
            
            // Refresh prayer times and update ticker
            fetchPrayerTimesForTicker();
        }, 5 * 60 * 1000); // 5 minutes
        
        // Save state to localStorage
        saveTickerState();
    }
    // Handle murattal playing message
    else if (message && message.type === 'murattal_playing') {
        console.log('Global murattal playing notification received:', message);
        
        document.body.classList.add('murattal-playing');
        tickerState.isMurattalPlaying = true;
        tickerState.murattalInfo = {
            murattal_name: message.murattal_name || 'Murattal',
            file_path: message.file_path,
            timestamp: message.timestamp || Date.now()
        };
        
        const murattalName = tickerState.murattalInfo.murattal_name;
        
        // Update with Murattal ticker style content - using green color for murattal
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-music"></i> 
            MURATTAL PLAYING: <strong>${murattalName}</strong>
            <i class="fas fa-music"></i>
            <button class="stop-audio-btn" onclick="stopAudio(); return false;"><i class="fas fa-stop"></i> Stop</button>
        `;
        
        // Always show the ticker for murattal notifications regardless of user preference
        showGlobalTicker();
        
        // Clear any existing timeout
        if (tickerState.murattalPlayingTimeoutId) {
            clearTimeout(tickerState.murattalPlayingTimeoutId);
        }
        
        // Set a timeout to reset the murattal playing status after 5 minutes
        tickerState.murattalPlayingTimeoutId = setTimeout(() => {
            document.body.classList.remove('murattal-playing');
            tickerState.isMurattalPlaying = false;
            tickerState.murattalInfo = null;
            
            // Save state after changes
            saveTickerState();
            
            // Refresh prayer times and update ticker
            fetchPrayerTimesForTicker();
        }, 5 * 60 * 1000); // 5 minutes
        
        // Save state to localStorage
        saveTickerState();
    }
    else if (message && message.type === 'prayer_times_updated') {
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
            if (!tickerState.isAdhanPlaying && !tickerState.isAlarmPlaying) {
                document.body.classList.remove('adhan-playing');
                document.body.classList.remove('alarm-playing');
            }
        }
    } else {
        // All prayers for today have passed
        tickerState.tickerContentElement.innerHTML = `
            <i class="fas fa-moon"></i> All prayers for today have passed. 
            <i class="fas fa-clock"></i> Current time: ${new Date().toLocaleTimeString()}
        `;
        if (!tickerState.isAdhanPlaying && !tickerState.isAlarmPlaying) {
            document.body.classList.remove('adhan-playing');
            document.body.classList.remove('alarm-playing');
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
        document.body.classList.remove('alarm-playing');
        document.body.classList.remove('murattal-playing');
        tickerState.isAdhanPlaying = false;
        tickerState.isAlarmPlaying = false;
        tickerState.isMurattalPlaying = false;
        
        // Clear reference to playing items
        tickerState.adhanInfo = null;
        tickerState.alarmInfo = null;
        tickerState.murattalInfo = null;
        
        // Clear any pending timeouts
        if (tickerState.adhanPlayingTimeoutId) {
            clearTimeout(tickerState.adhanPlayingTimeoutId);
        }
        
        if (tickerState.alarmPlayingTimeoutId) {
            clearTimeout(tickerState.alarmPlayingTimeoutId);
        }
        
        if (tickerState.murattalPlayingTimeoutId) {
            clearTimeout(tickerState.murattalPlayingTimeoutId);
        }
        
        // Save the updated state to localStorage
        saveTickerState();
        
        // Refresh prayer times and update ticker
        fetchPrayerTimesForTicker();
    })
    .catch(error => {
        console.error('Error stopping audio:', error);
    });
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', initGlobalTicker);