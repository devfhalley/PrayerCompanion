/**
 * Audio Status Monitor
 * This script periodically checks if audio is playing on the server
 * and displays a visual indicator in the web interface.
 */

// DOM elements
let audioStatusElement = null;
let statusInterval = null;

// Initialize the audio status monitor
function initAudioStatusMonitor() {
    console.log("Initializing audio status monitor...");
    
    // Create audio status element if it doesn't exist
    if (!document.getElementById('audio-status')) {
        audioStatusElement = document.createElement('div');
        audioStatusElement.id = 'audio-status';
        audioStatusElement.className = 'audio-status hidden';
        audioStatusElement.innerHTML = `
            <div class="audio-status-icon">
                <span class="playing-icon">🔊</span>
            </div>
            <div class="audio-status-text">
                <span class="audio-type">Loading...</span>
            </div>
        `;
        document.body.appendChild(audioStatusElement);
        
        // Add CSS for the audio status element
        const style = document.createElement('style');
        style.textContent = `
            .audio-status {
                position: fixed;
                top: 20px;
                right: 20px;
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                display: flex;
                align-items: center;
                z-index: 9999;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                transition: opacity 0.3s ease-in-out;
            }
            .audio-status.hidden {
                opacity: 0;
                pointer-events: none;
            }
            .audio-status-icon {
                margin-right: 10px;
                font-size: 1.2em;
            }
            .audio-status-text {
                font-size: 0.9em;
            }
            .playing-icon {
                display: inline-block;
                animation: pulsate 1s infinite;
            }
            @keyframes pulsate {
                0% { opacity: 0.5; }
                50% { opacity: 1; }
                100% { opacity: 0.5; }
            }
        `;
        document.head.appendChild(style);
    } else {
        audioStatusElement = document.getElementById('audio-status');
    }
    
    // Start periodic status check
    if (statusInterval) {
        clearInterval(statusInterval);
    }
    
    statusInterval = setInterval(checkAudioStatus, 1000);
    
    // Initial check
    checkAudioStatus();
}

// Track consecutive failures
let audioStatusFailCount = 0;
const MAX_CONSECUTIVE_FAILURES = 5;

// Check if audio is currently playing on the server
async function checkAudioStatus() {
    try {
        // Add a cache-busting parameter
        const timestamp = Date.now();
        const response = await fetch(`/status?t=${timestamp}`, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
            // Increase timeout for Replit environment - using 20 seconds instead of 8
            signal: AbortSignal.timeout(20000)
        });
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Reset failure count on success
        audioStatusFailCount = 0;
        
        if (data.audio_playing) {
            showAudioPlaying(data.audio_type);
        } else {
            hideAudioPlaying();
        }
    } catch (error) {
        console.error('Error checking audio status:', error);
        
        // Show user-friendly message for timeout errors
        if (error.name === 'TimeoutError') {
            console.warn('Request timed out - this is normal in the Replit environment and will be retried automatically');
        }
        
        // Increment failure count
        audioStatusFailCount++;
        
        // Hide the status indicator
        hideAudioPlaying();
        
        // If we've had too many consecutive failures, slow down the polling rate
        if (audioStatusFailCount > MAX_CONSECUTIVE_FAILURES) {
            console.warn(`Too many consecutive audio status check failures (${audioStatusFailCount}), reducing polling rate`);
            
            // Slow down the interval after too many failures
            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = setInterval(checkAudioStatus, 5000); // Check every 5 seconds instead of 1
            }
        }
    }
}

// Show the audio playing indicator
function showAudioPlaying(audioType) {
    if (audioStatusElement) {
        audioStatusElement.classList.remove('hidden');
        const audioTypeElement = audioStatusElement.querySelector('.audio-type');
        if (audioTypeElement) {
            audioTypeElement.textContent = `Playing: ${audioType}`;
        }
    }
}

// Hide the audio playing indicator
function hideAudioPlaying() {
    if (audioStatusElement) {
        audioStatusElement.classList.add('hidden');
    }
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', initAudioStatusMonitor);