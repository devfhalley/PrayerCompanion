/**
 * Global Volume Control for Prayer Alarm System
 * Provides a volume slider that's accessible from all pages
 */

// Global state
const volumeState = {
    currentVolume: 70, // Default volume (0-100)
    volumeElement: null,
    volumeSliderElement: null,
    volumeIconElement: null,
    isVisible: false
};

// Initialize the volume control
function initVolumeControl() {
    console.log('Initializing global volume control...');
    
    // Create volume control if it doesn't exist
    if (!document.getElementById('global-volume')) {
        // Create the volume container
        volumeState.volumeElement = document.createElement('div');
        volumeState.volumeElement.id = 'global-volume';
        volumeState.volumeElement.className = 'global-volume';
        
        // Create volume icon
        volumeState.volumeIconElement = document.createElement('div');
        volumeState.volumeIconElement.className = 'volume-icon';
        volumeState.volumeIconElement.innerHTML = '<i class="fas fa-volume-up"></i>';
        
        // Create the volume slider
        volumeState.volumeSliderElement = document.createElement('input');
        volumeState.volumeSliderElement.type = 'range';
        volumeState.volumeSliderElement.min = '0';
        volumeState.volumeSliderElement.max = '100';
        volumeState.volumeSliderElement.value = volumeState.currentVolume;
        volumeState.volumeSliderElement.className = 'volume-slider';
        
        // Create volume percentage display
        const volumePercentElement = document.createElement('div');
        volumePercentElement.className = 'volume-percent';
        volumePercentElement.textContent = volumeState.currentVolume + '%';
        
        // Add slider and percentage to volume element
        volumeState.volumeElement.appendChild(volumeState.volumeIconElement);
        volumeState.volumeElement.appendChild(volumeState.volumeSliderElement);
        volumeState.volumeElement.appendChild(volumePercentElement);
        
        // Add volume control to body
        document.body.appendChild(volumeState.volumeElement);
        
        // Add CSS for the volume control
        const style = document.createElement('style');
        style.textContent = `
            .global-volume {
                position: fixed;
                bottom: 40px; /* Position above the global ticker */
                right: 20px;
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 10px 15px;
                border-radius: 50px;
                z-index: 9998;
                display: flex;
                align-items: center;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
                transition: all 0.3s ease;
                opacity: 0.4;
            }
            
            .global-volume:hover {
                opacity: 1;
            }
            
            .volume-icon {
                margin-right: 10px;
                cursor: pointer;
            }
            
            .volume-icon i {
                font-size: 16px;
            }
            
            .volume-slider {
                width: 100px;
                margin: 0 10px;
                cursor: pointer;
                -webkit-appearance: none;
                appearance: none;
                height: 6px;
                background: #d3d3d3;
                outline: none;
                border-radius: 3px;
            }
            
            .volume-slider::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 16px;
                height: 16px;
                background: #4CAF50;
                cursor: pointer;
                border-radius: 50%;
            }
            
            .volume-slider::-moz-range-thumb {
                width: 16px;
                height: 16px;
                background: #4CAF50;
                cursor: pointer;
                border-radius: 50%;
                border: none;
            }
            
            .volume-percent {
                width: 40px;
                text-align: center;
                font-size: 12px;
            }
            
            @media (max-width: 768px) {
                .global-volume {
                    padding: 8px 12px;
                    bottom: 50px;
                }
                
                .volume-slider {
                    width: 80px;
                }
                
                .volume-percent {
                    font-size: 10px;
                    width: 30px;
                }
            }
        `;
        document.head.appendChild(style);
        
        // Add event listeners
        volumeState.volumeSliderElement.addEventListener('input', onVolumeChange);
        volumeState.volumeIconElement.addEventListener('click', toggleMute);
        
        // Make the volume control initially visible for 3 seconds
        showVolumeControl();
        setTimeout(hideVolumeControl, 3000);
    } else {
        volumeState.volumeElement = document.getElementById('global-volume');
        volumeState.volumeSliderElement = document.querySelector('.volume-slider');
        volumeState.volumeIconElement = document.querySelector('.volume-icon');
    }
    
    // Fetch current volume from server
    fetchCurrentVolume();
    
    // Listen for WebSocket volume updates
    listenForVolumeUpdates();
}

// Fetch the current volume from the server
async function fetchCurrentVolume() {
    try {
        const response = await fetch('/volume');
        if (response.ok) {
            const data = await response.json();
            updateVolumeUI(data.volume);
        } else {
            console.error('Failed to fetch volume:', response.status);
        }
    } catch (error) {
        console.error('Error fetching volume:', error);
    }
}

// Update the volume on the server
async function updateVolumeOnServer(volume) {
    try {
        const response = await fetch('/volume', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ volume }),
        });
        
        if (!response.ok) {
            console.error('Failed to update volume on server:', response.status);
        }
    } catch (error) {
        console.error('Error updating volume on server:', error);
    }
}

// Handle volume change events
function onVolumeChange(event) {
    const volume = parseInt(event.target.value, 10);
    updateVolumeUI(volume);
    updateVolumeOnServer(volume);
    
    // Make sure the volume control stays visible while adjusting
    clearTimeout(volumeState.hideTimeout);
    showVolumeControl();
    volumeState.hideTimeout = setTimeout(hideVolumeControl, 3000);
}

// Update the volume UI elements
function updateVolumeUI(volume) {
    volumeState.currentVolume = volume;
    
    // Update slider value
    if (volumeState.volumeSliderElement) {
        volumeState.volumeSliderElement.value = volume;
    }
    
    // Update percentage display
    const percentElement = document.querySelector('.volume-percent');
    if (percentElement) {
        percentElement.textContent = volume + '%';
    }
    
    // Update icon based on volume level
    updateVolumeIcon(volume);
}

// Update the volume icon based on the volume level
function updateVolumeIcon(volume) {
    if (!volumeState.volumeIconElement) return;
    
    let iconClass = 'fas ';
    
    if (volume === 0) {
        iconClass += 'fa-volume-mute';
    } else if (volume < 30) {
        iconClass += 'fa-volume-off';
    } else if (volume < 70) {
        iconClass += 'fa-volume-down';
    } else {
        iconClass += 'fa-volume-up';
    }
    
    volumeState.volumeIconElement.innerHTML = `<i class="${iconClass}"></i>`;
}

// Toggle mute (set volume to 0 or restore previous volume)
function toggleMute() {
    if (volumeState.currentVolume > 0) {
        // Store current volume before muting
        volumeState.previousVolume = volumeState.currentVolume;
        updateVolumeUI(0);
        updateVolumeOnServer(0);
    } else {
        // Restore previous volume or default to 70%
        const newVolume = volumeState.previousVolume || 70;
        updateVolumeUI(newVolume);
        updateVolumeOnServer(newVolume);
    }
    
    // Make volume control visible for a few seconds after toggling mute
    clearTimeout(volumeState.hideTimeout);
    showVolumeControl();
    volumeState.hideTimeout = setTimeout(hideVolumeControl, 3000);
}

// Show the volume control
function showVolumeControl() {
    if (volumeState.volumeElement) {
        volumeState.volumeElement.style.opacity = '1';
        volumeState.isVisible = true;
    }
}

// Hide the volume control
function hideVolumeControl() {
    if (volumeState.volumeElement) {
        volumeState.volumeElement.style.opacity = '0.4';
        volumeState.isVisible = false;
    }
}

// Listen for volume updates via WebSocket
function listenForVolumeUpdates() {
    // If global ticker's WebSocket is available, use that for volume updates
    if (window.tickerState && window.tickerState.wsConnection) {
        const originalOnMessage = window.tickerState.wsConnection.onmessage;
        
        window.tickerState.wsConnection.onmessage = function(event) {
            // Call the original handler
            if (originalOnMessage) {
                originalOnMessage(event);
            }
            
            try {
                if (!event || !event.data) return;
                
                const message = JSON.parse(event.data);
                
                // Handle volume changed message
                if (message && message.type === 'volume_changed') {
                    console.log('Volume update received via WebSocket:', message.volume);
                    updateVolumeUI(message.volume);
                }
            } catch (error) {
                console.error('Error processing WebSocket message in volume control:', error);
            }
        };
    }
}

// Initialize when the document is ready and after global ticker is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Wait for global ticker to initialize
    setTimeout(initVolumeControl, 500);
});