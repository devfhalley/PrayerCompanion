/**
 * Enhanced WebSocket Client
 * This script provides a robust WebSocket client implementation with automatic reconnection,
 * heartbeat mechanism, and error handling for Replit environment.
 * 
 * Note: WebSockets are disabled in Replit environment due to compatibility issues.
 * Full functionality available when deployed to a real server.
 */

class ReliableWebSocket {
    constructor(url, options = {}) {
        // Check if we're in Replit environment - completely disable WebSockets if so
        this.inReplitEnvironment = window.location.host.includes('replit');
        
        this.url = url;
        this.options = Object.assign({
            debug: false,
            reconnectInterval: 2000,
            maxReconnectAttempts: 10,
            heartbeatInterval: 15000,
            heartbeatMessage: { type: 'ping', timestamp: Date.now() },
            messageHandlers: {},
            onOpen: null,
            onClose: null,
            onError: null,
            onMessage: null,
            onReconnect: null,
            onMaxReconnectsExceeded: null
        }, options);
        
        this.ws = null;
        this.reconnectAttempts = 0;
        this.heartbeatTimer = null;
        this.connectionTimer = null;
        this.manualClose = false;
        
        // In Replit, we completely disable WebSockets to avoid errors
        if (this.inReplitEnvironment) {
            console.log('Replit environment detected - WebSockets are disabled');
            console.info('Real-time updates via WebSockets are only available when deployed');
        }
        
        this.connect();
    }
    
    // Connect to WebSocket server
    connect() {
        // In Replit environment, don't attempt to connect at all
        if (this.inReplitEnvironment) {
            if (this.options.debug) {
                console.log('WebSocket: Connection skipped in Replit environment');
            }
            return;
        }
        
        // Clear any existing connection
        this.cleanup();
        
        // Log connection attempt
        if (this.options.debug) {
            console.log(`WebSocket: Connecting to ${this.url}`);
        }
        
        try {
            // Create a new WebSocket connection
            this.ws = new WebSocket(this.url);
            
            // Setup connection timeout
            this.connectionTimer = setTimeout(() => {
                if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
                    if (this.options.debug) {
                        console.warn('WebSocket: Connection timeout, closing and retrying');
                    }
                    this.ws.close();
                    this.reconnect();
                }
            }, 10000); // 10 second timeout for initial connection
            
            // Setup event handlers
            this.ws.onopen = this._onOpen.bind(this);
            this.ws.onclose = this._onClose.bind(this);
            this.ws.onerror = this._onError.bind(this);
            this.ws.onmessage = this._onMessage.bind(this);
        } catch (error) {
            if (this.options.debug) {
                console.error('WebSocket: Error creating connection', error);
            }
            this.reconnect();
        }
    }
    
    // Send data through the WebSocket
    send(data) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            if (this.options.debug) {
                console.warn('WebSocket: Cannot send message, connection not open');
            }
            return false;
        }
        
        try {
            // Convert data to JSON string if it's an object
            const message = typeof data === 'object' ? JSON.stringify(data) : data;
            this.ws.send(message);
            return true;
        } catch (error) {
            if (this.options.debug) {
                console.error('WebSocket: Error sending message', error);
            }
            return false;
        }
    }
    
    // Close the WebSocket connection
    close() {
        this.manualClose = true;
        this.cleanup();
        if (this.ws) {
            this.ws.close();
        }
    }
    
    // Check if WebSocket is connected
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
    
    // Add an event handler for a specific message type
    addMessageHandler(messageType, handler) {
        this.options.messageHandlers[messageType] = handler;
    }
    
    // Internal event handlers
    _onOpen(event) {
        if (this.options.debug) {
            console.log('WebSocket: Connection established');
        }
        
        // Clear connection timeout
        if (this.connectionTimer) {
            clearTimeout(this.connectionTimer);
            this.connectionTimer = null;
        }
        
        // Reset reconnect attempts counter
        this.reconnectAttempts = 0;
        
        // Start heartbeat
        this._startHeartbeat();
        
        // Send a client_connect message to identify ourselves to the server
        this.send({
            type: 'client_connect',
            client_info: {
                device: navigator.userAgent,
                page: window.location.pathname,
                timestamp: Date.now()
            }
        });
        
        // Call user callback if provided
        if (typeof this.options.onOpen === 'function') {
            this.options.onOpen(event);
        }
    }
    
    _onClose(event) {
        if (this.options.debug) {
            console.log(`WebSocket: Connection closed (code: ${event.code}, reason: ${event.reason})`);
        }
        
        // Clean up
        this.cleanup();
        
        // Call user callback if provided
        if (typeof this.options.onClose === 'function') {
            this.options.onClose(event);
        }
        
        // Reconnect if this wasn't a manual close
        if (!this.manualClose) {
            this.reconnect();
        }
    }
    
    _onError(event) {
        if (this.options.debug) {
            console.error('WebSocket: Error occurred', event);
        }
        
        // Call user callback if provided
        if (typeof this.options.onError === 'function') {
            this.options.onError(event);
        }
    }
    
    _onMessage(event) {
        try {
            // Attempt to parse the message as JSON
            const data = JSON.parse(event.data);
            
            // Special handling for pong messages
            if (data.type === 'pong') {
                if (this.options.debug) {
                    console.log('WebSocket: Received pong response from server');
                }
                // The heartbeat is working, no need for additional processing
                return;
            }
            
            // Special handling for welcome messages
            if (data.type === 'welcome') {
                if (this.options.debug) {
                    console.log('WebSocket: Received welcome message from server');
                }
                // This confirms the connection is established and working
                return;
            }
            
            // Handle via registered message handler if available
            if (data.type && this.options.messageHandlers[data.type]) {
                this.options.messageHandlers[data.type](data);
                return;
            }
            
            // Call general message handler if provided
            if (typeof this.options.onMessage === 'function') {
                this.options.onMessage(data, event);
            }
        } catch (error) {
            // Message is not valid JSON, pass the raw event
            if (this.options.debug) {
                console.warn('WebSocket: Received non-JSON message', event.data);
            }
            
            if (typeof this.options.onMessage === 'function') {
                this.options.onMessage(event.data, event);
            }
        }
    }
    
    // Start heartbeat mechanism to keep connection alive
    _startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.ws.readyState === WebSocket.OPEN) {
                // Send heartbeat message
                const heartbeatMsg = Object.assign({}, this.options.heartbeatMessage, {
                    timestamp: Date.now()
                });
                this.send(heartbeatMsg);
                
                if (this.options.debug) {
                    console.log('WebSocket: Sent heartbeat');
                }
            } else {
                // Connection is not open, stop heartbeat and try to reconnect
                this.cleanup();
                this.reconnect();
            }
        }, this.options.heartbeatInterval);
    }
    
    // Clean up timers and resources
    cleanup() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
        
        if (this.connectionTimer) {
            clearTimeout(this.connectionTimer);
            this.connectionTimer = null;
        }
    }
    
    // Attempt to reconnect with backoff
    reconnect() {
        // In Replit environment, don't attempt to reconnect at all
        if (this.inReplitEnvironment) {
            if (this.options.debug) {
                console.log('WebSocket: Reconnection skipped in Replit environment');
            }
            return;
        }
        
        this.reconnectAttempts++;
        
        if (this.reconnectAttempts > this.options.maxReconnectAttempts) {
            if (this.options.debug) {
                console.error(`WebSocket: Max reconnect attempts (${this.options.maxReconnectAttempts}) exceeded`);
            }
            
            // Call max reconnects exceeded callback if provided
            if (typeof this.options.onMaxReconnectsExceeded === 'function') {
                this.options.onMaxReconnectsExceeded();
            }
            
            return;
        }
        
        // Calculate reconnect delay with exponential backoff
        const delay = Math.min(
            this.options.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1),
            30000 // Max 30 seconds
        );
        
        if (this.options.debug) {
            console.log(`WebSocket: Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        }
        
        // Call reconnect callback if provided
        if (typeof this.options.onReconnect === 'function') {
            this.options.onReconnect(this.reconnectAttempts, delay);
        }
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }
}

// Helper function to create the correct WebSocket URL based on window location
function getWebSocketUrl(path = '/ws') {
    // Check if we're in Replit environment - if so, return null to prevent connection attempts
    const inReplitEnv = isReplitEnvironment();
    if (inReplitEnv) {
        console.info('In Replit environment - WebSockets disabled');
        return null;
    }
    
    // Only proceed with URL construction for non-Replit environments
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    // Return standard WebSocket URL
    return `${protocol}//${host}${path}`;
}

// Helper function to detect Replit environment
function isReplitEnvironment() {
    const host = window.location.host || '';
    const isReplit = host.includes('replit') || 
                    host.includes('.repl.co') || 
                    host.includes('.repl.dev') || 
                    host.includes('.repl.run') ||
                    window.location.hostname.match(/^\d+\.\d+\.\d+\.\d+$/) || // IP address (Replit internal routing)
                    host.includes('.id.repl.co') ||
                    window.location.hostname === '0.0.0.0' ||
                    window.location.hostname === 'localhost';
    
    console.log("Environment detection: ", {
        host: host,
        hostname: window.location.hostname,
        isReplit: isReplit
    });
    
    // Always return true for now to ensure WebSockets are disabled in problematic environments
    return true;
}

// Setup global WebSocket connection
let globalWs = null;

function setupGlobalWebSocket() {
    // Check if we're in Replit environment - don't even attempt to create WebSockets if we are
    const inReplitEnvironment = isReplitEnvironment();
    if (inReplitEnvironment) {
        console.log('Replit environment detected - WebSockets are disabled');
        console.info('Real-time updates via WebSockets are only available when deployed');
        
        // Update UI elements to show disconnected status in Replit
        document.querySelectorAll('.ws-status-indicator').forEach(el => {
            el.classList.remove('connected');
            el.classList.add('disconnected');
            if (el.textContent) {
                el.textContent = 'Disabled in Replit';
            }
        });
        
        // Set a global flag to indicate WebSockets are disabled
        window.webSocketsDisabled = true;
        
        return null;
    }
    
    // Only proceed with WebSocket creation in non-Replit environments
    const wsUrl = getWebSocketUrl();
    
    // Double-check that we have a valid WebSocket URL
    if (!wsUrl) {
        console.warn('No valid WebSocket URL available - skipping WebSocket connection');
        return null;
    }
    
    console.log('Setting up global WebSocket connection to:', wsUrl);
    
    globalWs = new ReliableWebSocket(wsUrl, {
        debug: true,
        onOpen: () => {
            console.log('Global WebSocket connection established successfully');
            
            // Update any UI elements that depend on WebSocket status
            document.querySelectorAll('.ws-status-indicator').forEach(el => {
                el.classList.remove('disconnected');
                el.classList.add('connected');
                if (el.textContent) {
                    el.textContent = 'Connected';
                }
            });
        },
        onClose: () => {
            console.log('Global WebSocket connection closed');
            
            // Update any UI elements that depend on WebSocket status
            document.querySelectorAll('.ws-status-indicator').forEach(el => {
                el.classList.remove('connected');
                el.classList.add('disconnected');
                if (el.textContent) {
                    el.textContent = 'Disconnected';
                }
            });
        },
        onError: (error) => {
            console.error('Global WebSocket error:', error);
        },
        onMessage: (data) => {
            console.log('Global WebSocket message received:', data);
            
            // Special handling for specific message types
            if (data.type === 'pong') {
                console.log('Received pong response from server');
            } else if (data.type === 'audio_status_change') {
                // Handle audio status change notification
                updateAudioStatusUI(data.status);
            } else if (data.type === 'prayer_time_notification') {
                // Handle prayer time notification
                showPrayerNotification(data);
            } else if (data.type === 'adhan_playing') {
                // Handle adhan playing notification
                showAdhanNotification(data);
            }
        }
    });
    
    // Make the WebSocket accessible globally
    window.globalWs = globalWs;
    
    return globalWs;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setupGlobalWebSocket();
});