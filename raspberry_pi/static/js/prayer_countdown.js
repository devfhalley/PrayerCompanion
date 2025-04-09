/**
 * Prayer Countdown Widget JS
 * Displays a countdown to the next prayer time with animated display and progress bar
 */

// Helper function to format date as YYYY-MM-DD
function formatDateYMD(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function initializePrayerCountdown(options = {}) {
    // Default options
    const defaultOptions = {
        containerId: 'prayer-countdown',
        isFloating: false,
        prayerTimesState: window.prayerTimesState || {
            currentPrayerTimes: [],
            dateSelector: null
        }
    };

    // Merge options
    const settings = {...defaultOptions, ...options};
    
    // Get elements
    const countdownWidget = document.getElementById(settings.containerId);
    if (!countdownWidget) {
        console.error(`Countdown widget container #${settings.containerId} not found`);
        return;
    }
    
    const countdownHoursEl = countdownWidget.querySelector('.countdown-value.hours');
    const countdownMinutesEl = countdownWidget.querySelector('.countdown-value.minutes');
    const countdownSecondsEl = countdownWidget.querySelector('.countdown-value.seconds');
    const progressFillEl = countdownWidget.querySelector('.prayer-progress-fill');
    
    if (!countdownHoursEl || !countdownMinutesEl || !countdownSecondsEl || !progressFillEl) {
        console.error('One or more countdown elements not found');
        return;
    }
    
    // Track previous values for animation
    let prevHours = null;
    let prevMinutes = null;
    let prevSeconds = null;
    
    // Track initial time difference for progress bar
    let initialTimeBetweenPrayers = null;
    
    // Add close button if floating
    if (settings.isFloating) {
        const closeButton = document.createElement('button');
        closeButton.className = 'countdown-close-btn';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', function() {
            countdownWidget.classList.add('hidden');
            // Save preference in localStorage
            localStorage.setItem('countdown_widget_hidden', 'true');
        });
        countdownWidget.appendChild(closeButton);
        
        // Check if widget was previously hidden
        if (localStorage.getItem('countdown_widget_hidden') === 'true') {
            countdownWidget.classList.add('hidden');
        }
    }
    
    function updateCountdown() {
        const now = new Date();
        let nextPrayerTime = null;
        let nextPrayerName = null;
        let prevPrayerTime = null;
        
        // Find the next prayer
        if (settings.prayerTimesState.currentPrayerTimes && 
            Array.isArray(settings.prayerTimesState.currentPrayerTimes)) {
            
            for (let i = 0; i < settings.prayerTimesState.currentPrayerTimes.length; i++) {
                const prayer = settings.prayerTimesState.currentPrayerTimes[i];
                if (!prayer || !prayer.time) continue;
                
                const prayerTime = new Date(prayer.time);
                if (prayerTime > now) {
                    nextPrayerTime = prayerTime;
                    nextPrayerName = prayer.name;
                    
                    // Find previous prayer for progress bar calculation
                    if (i > 0) {
                        prevPrayerTime = new Date(settings.prayerTimesState.currentPrayerTimes[i-1].time);
                    } else if (i === 0 && settings.prayerTimesState.currentPrayerTimes.length > 0) {
                        // If it's the first prayer of the day, use 12am as starting point
                        prevPrayerTime = new Date(now);
                        prevPrayerTime.setHours(0, 0, 0, 0);
                    }
                    break;
                }
            }
        }
        
        // If no next prayer or not on today's date, hide countdown
        const selectedDate = settings.prayerTimesState.dateSelector ? 
            new Date(settings.prayerTimesState.dateSelector.value) : 
            new Date();
        
        const isToday = selectedDate.toDateString() === now.toDateString();
        
        if (!nextPrayerTime || !isToday) {
            countdownWidget.style.display = 'none';
            return;
        } else {
            countdownWidget.style.display = 'block';
        }
        
        // Calculate time difference
        const timeDiff = nextPrayerTime - now;
        
        // Calculate hours, minutes, seconds
        const hours = Math.floor(timeDiff / (1000 * 60 * 60));
        const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
        
        // For progress bar - calculate total time between prayers
        if (prevPrayerTime && initialTimeBetweenPrayers === null) {
            initialTimeBetweenPrayers = nextPrayerTime - prevPrayerTime;
        } else if (initialTimeBetweenPrayers === null) {
            // If we can't determine previous prayer, use 6 hours as default
            initialTimeBetweenPrayers = 6 * 60 * 60 * 1000;
        }
        
        // Update countdown header
        const countdownHeader = countdownWidget.querySelector('.countdown-header');
        if (countdownHeader) {
            countdownHeader.textContent = `Time Remaining Until ${nextPrayerName}`;
        }
        
        // Update hours with animation if changed
        if (hours !== prevHours) {
            updateCountdownValue(countdownHoursEl, hours, prevHours !== null);
            prevHours = hours;
        }
        
        // Update minutes with animation if changed
        if (minutes !== prevMinutes) {
            updateCountdownValue(countdownMinutesEl, minutes, prevMinutes !== null);
            prevMinutes = minutes;
        }
        
        // Update seconds with animation if changed
        if (seconds !== prevSeconds) {
            updateCountdownValue(countdownSecondsEl, seconds, prevSeconds !== null);
            prevSeconds = seconds;
        }
        
        // Update progress bar
        const progressPercentage = 100 - (timeDiff / initialTimeBetweenPrayers * 100);
        progressFillEl.style.width = `${Math.min(Math.max(progressPercentage, 0), 100)}%`;
        
        // Change progress bar color based on time remaining
        if (timeDiff < 10 * 60 * 1000) { // Less than 10 minutes
            progressFillEl.style.backgroundColor = '#F44336'; // Red
        } else if (timeDiff < 30 * 60 * 1000) { // Less than 30 minutes
            progressFillEl.style.backgroundColor = '#FF9800'; // Orange
        } else {
            progressFillEl.style.backgroundColor = '#4CAF50'; // Green
        }
    }
    
    // Helper function to update countdown value with animation
    function updateCountdownValue(element, value, animate) {
        const formattedValue = value.toString().padStart(2, '0');
        
        if (animate) {
            // Add animation class
            element.classList.add('animate');
            
            // Remove animation class after animation completes
            setTimeout(() => {
                element.classList.remove('animate');
            }, 500);
        }
        
        element.textContent = formattedValue;
    }
    
    // Initialize countdown widget
    function initialize() {
        // Fetch prayer times if not already available
        if (!settings.prayerTimesState.currentPrayerTimes || 
            settings.prayerTimesState.currentPrayerTimes.length === 0) {
            
            console.log('Fetching prayer times for countdown widget');
            
            // Check if the fetchPrayerTimes function is available (defined in prayer_times.html)
            if (typeof fetchPrayerTimes === 'function') {
                fetchPrayerTimes(formatDateYMD(new Date()))
                    .then(prayerTimes => {
                        settings.prayerTimesState.currentPrayerTimes = prayerTimes;
                        updateCountdown();
                    })
                    .catch(error => {
                        console.error('Error fetching prayer times for countdown widget:', error);
                    });
            } else {
                // Direct API call if fetchPrayerTimes is not available
                fetch('/prayer-times')
                    .then(response => response.json())
                    .then(prayerTimes => {
                        settings.prayerTimesState.currentPrayerTimes = prayerTimes;
                        updateCountdown();
                    })
                    .catch(error => {
                        console.error('Error fetching prayer times for countdown widget:', error);
                    });
            }
        } else {
            updateCountdown();
        }
        
        // Update countdown every second
        setInterval(updateCountdown, 1000);
    }
    
    // Initialize on load
    initialize();
    
    // Return public API
    return {
        update: updateCountdown,
        show: function() {
            countdownWidget.classList.remove('hidden');
            localStorage.removeItem('countdown_widget_hidden');
        },
        hide: function() {
            countdownWidget.classList.add('hidden');
            localStorage.setItem('countdown_widget_hidden', 'true');
        },
        toggle: function() {
            if (countdownWidget.classList.contains('hidden')) {
                this.show();
            } else {
                this.hide();
            }
        }
    };
}

/**
 * Creates and injects a floating prayer countdown widget into the page
 * @param {Object} prayerTimesState - Optional state object containing prayer times
 * @returns {Object} Widget controller with show/hide/toggle methods
 */
function createFloatingCountdownWidget(prayerTimesState) {
    // Check if we're on the prayer times page (don't add floating widget there)
    if (window.location.pathname.includes('/web/prayer-times')) {
        return null;
    }
    
    // Check if we already have a floating widget
    if (document.getElementById('floating-prayer-countdown')) {
        return null;
    }
    
    // Create widget container
    const widgetContainer = document.createElement('div');
    widgetContainer.id = 'floating-prayer-countdown';
    widgetContainer.className = 'prayer-countdown floating';
    
    // Add widget content
    widgetContainer.innerHTML = `
        <div class="countdown-header">Time Until Next Prayer</div>
        <div class="countdown-timer">
            <div class="countdown-segment">
                <div class="countdown-value hours">00</div>
                <div class="countdown-label">Hours</div>
            </div>
            <div class="countdown-separator">:</div>
            <div class="countdown-segment">
                <div class="countdown-value minutes">00</div>
                <div class="countdown-label">Minutes</div>
            </div>
            <div class="countdown-separator">:</div>
            <div class="countdown-segment">
                <div class="countdown-value seconds">00</div>
                <div class="countdown-label">Seconds</div>
            </div>
        </div>
        <div class="prayer-progress-bar">
            <div class="prayer-progress-fill"></div>
        </div>
    `;
    
    // Add CSS for floating widget if not already in stylesheet
    if (!document.getElementById('floating-countdown-styles')) {
        const style = document.createElement('style');
        style.id = 'floating-countdown-styles';
        style.textContent = `
            .prayer-countdown.floating {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 280px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                padding: 15px;
                z-index: 1000;
                transition: opacity 0.3s, transform 0.3s;
            }
            
            .prayer-countdown.floating.hidden {
                opacity: 0;
                transform: translateY(20px);
                pointer-events: none;
            }
            
            .countdown-close-btn {
                position: absolute;
                top: 5px;
                right: 5px;
                width: 20px;
                height: 20px;
                background: none;
                border: none;
                font-size: 16px;
                cursor: pointer;
                color: #777;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
            }
            
            .countdown-close-btn:hover {
                color: #333;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Append to body
    document.body.appendChild(widgetContainer);
    
    // Initialize and return the widget controller
    return initializePrayerCountdown({
        containerId: 'floating-prayer-countdown',
        isFloating: true,
        prayerTimesState: prayerTimesState
    });
}