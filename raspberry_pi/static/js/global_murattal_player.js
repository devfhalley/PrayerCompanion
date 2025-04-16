/**
 * Global Murattal Player
 * This script provides a persistent sticky player for Murattal across all pages
 * 
 * Features:
 * - Displays murattal player on all pages, not just the murattal page
 * - Maintains player state when navigating between pages
 * - Shows "Now Playing" or "Last Played" based on playback state
 */

document.addEventListener('DOMContentLoaded', function() {
    // Don't initialize on the murattal page itself since it has its own player logic
    if (window.location.pathname.includes('/murattal')) {
        console.log("Skipping global murattal player on murattal page");
        return;
    }
    
    console.log("Initializing global murattal player");
    
    // Add basic styles if CSS failed to load
    ensureBasicStyles();
    
    // Global player state
    const playerState = {
        currentTrack: null,
        isPlaying: false,
        isPaused: false,
        statusCheckInterval: null
    };

    // Check initial status when page loads
    checkInitialStatus();
    
    // Function to check if murattal is playing when the page loads
    async function checkInitialStatus() {
        try {
            const response = await fetch('/status');
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Check if there's a murattal track in the response
            if (data.audio_status && 
                data.audio_status.type === 'murattal' && 
                data.audio_status.murattal_details) {
                
                const murattalDetails = data.audio_status.murattal_details;
                console.log("Found murattal information on page load:", murattalDetails, "playing:", data.audio_playing);
                
                // Update player state
                playerState.isPlaying = data.audio_playing;
                playerState.isPaused = false;
                playerState.currentTrack = {
                    name: murattalDetails.name,
                    path: murattalDetails.file_path
                };
            }
        } catch (error) {
            console.error("Error checking initial murattal status:", error);
        }
        
        // Always create the sticky player, even if no track is currently playing
        createStickyPlayer();
        updateStickyPlayer();
        
        // Start regular status checks
        startStatusCheck();
    }
    
    // Track consecutive failures for status checks
    let statusFailCount = 0;
    const MAX_CONSECUTIVE_FAILURES = 5;
    
    // Start regular status checks
    function startStatusCheck() {
        // Check status every second
        playerState.statusCheckInterval = setInterval(async () => {
            try {
                // Add cache busting to prevent ERR_TOO_MANY_RETRIES
                const timestamp = Date.now();
                const response = await fetch(`/status?t=${timestamp}`, {
                    method: 'GET',
                    headers: {
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    },
                    // Set a reasonable timeout
                    signal: AbortSignal.timeout(3000)
                });
                
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                // Reset failure count on success
                statusFailCount = 0;
                
                // Check if there's any murattal info in the response
                if (data.audio_status && 
                    data.audio_status.type === 'murattal' && 
                    data.audio_status.murattal_details) {
                    
                    const murattalDetails = data.audio_status.murattal_details;
                    const isActuallyPlaying = data.audio_playing;
                    
                    // Check if this is a different track than what we're currently tracking
                    const isNewTrack = !playerState.currentTrack || 
                                       playerState.currentTrack.name !== murattalDetails.name;
                    
                    // Check if play state has changed
                    const playStateChanged = playerState.isPlaying !== isActuallyPlaying;
                    
                    // Only update if there's a change to track or play state
                    if (isNewTrack || playStateChanged) {
                        console.log("Murattal status update:", {
                            isActuallyPlaying, 
                            trackName: murattalDetails.name,
                            isNewTrack,
                            playStateChanged
                        });
                        
                        // Update state
                        playerState.isPlaying = isActuallyPlaying;
                        playerState.isPaused = false;
                        playerState.currentTrack = {
                            name: murattalDetails.name,
                            path: murattalDetails.file_path
                        };
                        
                        // Make sure sticky player is created for both playing and past tracks
                        createStickyPlayer();
                        updateStickyPlayer();
                    }
                } else if (playerState.isPlaying) {
                    // No murattal info at all, and we thought something was playing
                    console.log("No murattal info in status, resetting player state");
                    
                    // Reset playback state but keep track info
                    playerState.isPlaying = false;
                    playerState.isPaused = false;
                    
                    // Update sticky player if it exists
                    updateStickyPlayer();
                }
            } catch (error) {
                console.error("Error checking audio status:", error);
                
                // Increment failure count
                statusFailCount++;
                
                // If we've had too many consecutive failures, slow down the polling rate
                if (statusFailCount >= MAX_CONSECUTIVE_FAILURES) {
                    console.warn(`Too many consecutive murattal status check failures (${statusFailCount}), reducing polling rate`);
                    
                    // Clear current interval and set a slower one
                    if (playerState.statusCheckInterval) {
                        clearInterval(playerState.statusCheckInterval);
                        playerState.statusCheckInterval = setInterval(async () => {
                            // Same function but with less frequent calls
                            try {
                                const timestamp = Date.now();
                                const response = await fetch(`/status?t=${timestamp}`, {
                                    method: 'GET',
                                    headers: {
                                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                                        'Pragma': 'no-cache',
                                        'Expires': '0'
                                    },
                                    signal: AbortSignal.timeout(3000)
                                });
                                
                                if (response.ok) {
                                    // If we succeed after slowing down, reset to normal speed
                                    console.log("Status check successful after slowing down, resuming normal polling rate");
                                    clearInterval(playerState.statusCheckInterval);
                                    statusFailCount = 0;
                                    startStatusCheck(); // Restart with normal interval
                                    return;
                                }
                            } catch (e) {
                                console.error("Still having errors with slower polling rate:", e);
                            }
                        }, 5000); // Check every 5 seconds instead of 1
                    }
                }
            }
        }, 1000);
    }
    
    // Create a sticky player that stays at the bottom of the page
    function createStickyPlayer() {
        if (document.getElementById('sticky-player')) return;
        
        const stickyPlayer = document.createElement('div');
        stickyPlayer.id = 'sticky-player';
        stickyPlayer.className = 'sticky-player';
        
        stickyPlayer.innerHTML = `
            <div class="sticky-player-inner">
                <div class="sticky-player-info">
                    <div class="sticky-player-title" id="sticky-player-title">
                        ${playerState.currentTrack ? playerState.currentTrack.name : 'No track selected'}
                    </div>
                    <a href="${window.appRoutes?.murattalPage || '/web/murattal'}" class="sticky-player-link">Open Full Player</a>
                </div>
                <div class="sticky-player-controls">
                    <button id="sticky-play-button" class="player-btn primary-btn"><i class="fas fa-play"></i></button>
                    <button id="sticky-pause-button" class="player-btn primary-btn hidden"><i class="fas fa-pause"></i></button>
                    <button id="sticky-stop-button" class="player-btn"><i class="fas fa-stop"></i></button>
                </div>
            </div>
        `;
        
        document.body.appendChild(stickyPlayer);
        
        // Add event listeners to sticky player controls
        document.getElementById('sticky-play-button').addEventListener('click', playCurrentTrack);
        document.getElementById('sticky-pause-button').addEventListener('click', pausePlayback);
        document.getElementById('sticky-stop-button').addEventListener('click', stopPlayback);
        
        // Update player initially
        updateStickyPlayer();
    }
    
    // Update the sticky player based on the current state
    function updateStickyPlayer() {
        const stickyPlayer = document.getElementById('sticky-player');
        if (!stickyPlayer) return;
        
        const stickyTitle = document.getElementById('sticky-player-title');
        const stickyPlayButton = document.getElementById('sticky-play-button');
        const stickyPauseButton = document.getElementById('sticky-pause-button');
        const stickyStopButton = document.getElementById('sticky-stop-button');
        
        // Update title
        if (stickyTitle) {
            if (playerState.currentTrack) {
                const statusPrefix = playerState.isPlaying ? "Now Playing" : "Last Played";
                stickyTitle.textContent = `${statusPrefix}: ${playerState.currentTrack.name}`;
            } else {
                stickyTitle.textContent = 'Murattal Player - Click "Open Full Player" to browse tracks';
            }
        }
        
        // Buttons should be disabled if no track is selected
        if (stickyPlayButton && stickyPauseButton && stickyStopButton) {
            if (!playerState.currentTrack) {
                stickyPlayButton.disabled = true;
                stickyStopButton.disabled = true;
            } else {
                stickyPlayButton.disabled = false;
                stickyStopButton.disabled = false;
            }
            
            // Update play/pause button visibility based on play state
            if (playerState.isPlaying) {
                stickyPlayButton.classList.add('hidden');
                stickyPauseButton.classList.remove('hidden');
            } else {
                stickyPlayButton.classList.remove('hidden');
                stickyPauseButton.classList.add('hidden');
            }
        }
    }
    
    // Play current track with improved error handling
    function playCurrentTrack() {
        if (!playerState.currentTrack) return;
        
        // Show visual feedback that the request is being processed
        const playButton = document.getElementById('sticky-play-button');
        if (playButton) {
            playButton.disabled = true;
            playButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
        
        fetch('/murattal/play', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache, no-store, must-revalidate'
            },
            body: JSON.stringify({
                file_path: playerState.currentTrack.path
            }),
            // Add request timeout
            signal: AbortSignal.timeout(5000)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                playerState.isPlaying = true;
                playerState.isPaused = false;
                updateStickyPlayer();
            } else {
                console.error('Error playing murattal:', data.message);
                // Reset button in case of error
                if (playButton) {
                    playButton.disabled = false;
                    playButton.innerHTML = '<i class="fas fa-play"></i>';
                }
                
                // Show error toast
                showErrorToast('Failed to play track');
            }
        })
        .catch(error => {
            console.error('Error playing murattal:', error);
            // Reset button in case of error
            if (playButton) {
                playButton.disabled = false;
                playButton.innerHTML = '<i class="fas fa-play"></i>';
            }
            
            // Show error toast
            showErrorToast('Request failed. Please try again.');
        });
    }
    
    // Helper function to show error toast
    function showErrorToast(message) {
        // Create toast element if it doesn't exist
        let toast = document.getElementById('error-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'error-toast';
            toast.className = 'error-toast';
            document.body.appendChild(toast);
            
            // Add toast styles if they don't exist
            if (!document.getElementById('toast-styles')) {
                const style = document.createElement('style');
                style.id = 'toast-styles';
                style.textContent = `
                    .error-toast {
                        position: fixed;
                        bottom: 120px;
                        left: 50%;
                        transform: translateX(-50%);
                        background-color: var(--error-color, #e74c3c);
                        color: white;
                        padding: 12px 20px;
                        border-radius: 4px;
                        z-index: 2000;
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                        font-size: 14px;
                        opacity: 0;
                        visibility: hidden;
                        transition: opacity 0.3s, visibility 0.3s;
                    }
                    .error-toast.show {
                        opacity: 1;
                        visibility: visible;
                    }
                `;
                document.head.appendChild(style);
            }
        }
        
        // Set toast message and show it
        toast.textContent = message;
        toast.classList.add('show');
        
        // Hide toast after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    // Pause playback
    function pausePlayback() {
        // No direct pause API available, so we use stop
        stopPlayback();
    }
    
    // Stop playback with improved error handling
    function stopPlayback() {
        // Show visual feedback that the request is being processed
        const stopButton = document.getElementById('sticky-stop-button');
        if (stopButton) {
            stopButton.disabled = true;
            stopButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
        
        fetch('/stop-audio', {
            method: 'POST',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate'
            },
            // Add request timeout
            signal: AbortSignal.timeout(5000)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                playerState.isPlaying = false;
                updateStickyPlayer();
            } else {
                console.error('Error stopping audio:', data.message);
                // Reset button in case of error
                if (stopButton) {
                    stopButton.disabled = false;
                    stopButton.innerHTML = '<i class="fas fa-stop"></i>';
                }
                showErrorToast('Failed to stop playback');
            }
        })
        .catch(error => {
            console.error('Error stopping audio:', error);
            // Reset button in case of error
            if (stopButton) {
                stopButton.disabled = false;
                stopButton.innerHTML = '<i class="fas fa-stop"></i>';
            }
            showErrorToast('Request failed. Please try again.');
        });
    }
    
    // Function to ensure basic styles are available
    function ensureBasicStyles() {
        // Check if stylesheet already exists
        const existingStyle = document.getElementById('fallback-murattal-styles');
        if (existingStyle) return;
        
        // Create a style element with essential styles
        const style = document.createElement('style');
        style.id = 'fallback-murattal-styles';
        style.textContent = `
            /* Light Theme Fallback */
            :root {
                --primary-color: #2b8a3e;
                --accent-color: #fd7e14;
                --text-color: #333;
                --bg-color: #ffffff;
                --light-bg: #f5f5f5;
                --divider-color: #ddd;
                --card-bg: #ffffff;
                --shadow-color: rgba(0, 0, 0, 0.1);
            }
            
            /* Dark Theme Fallback */
            [data-theme="dark"] {
                --primary-color: #4caf50;
                --accent-color: #ff9800;
                --text-color: #f0f0f0;
                --bg-color: #121212;
                --light-bg: #1e1e1e;
                --divider-color: #333333;
                --card-bg: #1e1e1e;
                --shadow-color: rgba(0, 0, 0, 0.3);
            }
            
            /* Sticky Player Styles */
            .sticky-player {
                position: fixed;
                bottom: 50px;
                left: 0;
                right: 0;
                background-color: var(--card-bg, #ffffff);
                box-shadow: 0 -2px 10px var(--shadow-color, rgba(0, 0, 0, 0.1));
                padding: 10px 20px;
                z-index: 1000;
                border-top: 3px solid var(--primary-color, #2b8a3e);
                transition: background-color 0.3s ease, box-shadow 0.3s ease;
            }
            
            .sticky-player-inner {
                max-width: 1000px;
                margin: 0 auto;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .sticky-player-info {
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            
            .sticky-player-title {
                font-weight: bold;
                font-size: 16px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 300px;
                color: var(--text-color, #333);
            }
            
            .sticky-player-link {
                font-size: 12px;
                color: var(--primary-color, #2b8a3e);
                text-decoration: none;
                margin-top: 4px;
                transition: color 0.3s ease;
            }
            
            .sticky-player-link:hover {
                text-decoration: underline;
            }
            
            .sticky-player-controls {
                display: flex;
                gap: 10px;
            }
            
            .player-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: none;
                background-color: var(--light-bg, #e9e9e9);
                color: var(--text-color, #333);
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
            }
            
            .player-btn.primary-btn {
                background-color: var(--primary-color, #2b8a3e);
                color: white;
                width: 45px;
                height: 45px;
            }
            
            .player-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 2px 5px var(--shadow-color, rgba(0, 0, 0, 0.1));
            }
            
            .player-btn.hidden {
                display: none;
            }
            
            .player-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }
        `;
        
        // Add to document head
        document.head.appendChild(style);
        console.log("Added fallback murattal player styles with theme support");
    }
});