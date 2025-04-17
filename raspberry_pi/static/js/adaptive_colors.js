/**
 * Adaptive Color Palette Based on Time of Day
 * 
 * This script changes the application's color palette based on the time of day,
 * creating a more dynamic and time-aware user interface.
 */

// Initialize the color palette system
document.addEventListener('DOMContentLoaded', function() {
    // Set up the initial color palette
    updateColorPalette();
    
    // Update the color palette every minute
    setInterval(updateColorPalette, 60000);
});

/**
 * Updates the color palette based on the current time of day
 */
function updateColorPalette() {
    const now = new Date();
    const hour = now.getHours();
    
    // Determine the time of day
    let timeOfDay;
    let colors;
    
    if (hour >= 5 && hour < 10) {
        timeOfDay = 'morning';
        colors = getMorningPalette();
    } else if (hour >= 10 && hour < 16) {
        timeOfDay = 'daytime';
        colors = getDaytimePalette();
    } else if (hour >= 16 && hour < 19) {
        timeOfDay = 'evening';
        colors = getEveningPalette();
    } else {
        timeOfDay = 'night';
        colors = getNightPalette();
    }
    
    // Apply the color palette to the document
    document.documentElement.setAttribute('data-time', timeOfDay);
    
    // Set the CSS variables for the colors
    for (const [key, value] of Object.entries(colors)) {
        document.documentElement.style.setProperty(`--${key}`, value);
    }
    
    // Log the change for debugging
    console.log(`Applied ${timeOfDay} color palette at ${now.toLocaleTimeString()}`);
}

/**
 * Morning palette (5:00 AM - 9:59 AM)
 * Soft, energizing colors with warm tones
 */
function getMorningPalette() {
    return {
        'primary-color': '#7cb342',        // Fresh green
        'secondary-color': '#ffb74d',      // Warm orange
        'accent-color': '#ff9800',         // Sunlight orange
        'header-bg': 'linear-gradient(135deg, #9ccc65, #7cb342)', // Morning gradient
        'card-highlight': 'rgba(255, 183, 77, 0.1)'  // Soft orange highlight
    };
}

/**
 * Daytime palette (10:00 AM - 3:59 PM)
 * Bright, clear colors with good contrast
 */
function getDaytimePalette() {
    return {
        'primary-color': '#4CAF50',        // Standard green
        'secondary-color': '#2196F3',      // Standard blue
        'accent-color': '#FF9800',         // Standard orange
        'header-bg': 'linear-gradient(135deg, #4CAF50, #2c6c3b)', // Default gradient
        'card-highlight': 'rgba(33, 150, 243, 0.1)'  // Soft blue highlight
    };
}

/**
 * Evening palette (4:00 PM - 6:59 PM)
 * Warm, golden-hour inspired colors
 */
function getEveningPalette() {
    return {
        'primary-color': '#ff7043',        // Sunset orange
        'secondary-color': '#7986cb',      // Twilight blue
        'accent-color': '#ffa726',         // Golden yellow
        'header-bg': 'linear-gradient(135deg, #ff7043, #c63f17)', // Sunset gradient
        'card-highlight': 'rgba(255, 167, 38, 0.1)'  // Soft gold highlight
    };
}

/**
 * Night palette (7:00 PM - 4:59 AM)
 * Darker, relaxing colors with blue tones
 */
function getNightPalette() {
    return {
        'primary-color': '#5c6bc0',        // Deep indigo
        'secondary-color': '#78909c',      // Blue grey
        'accent-color': '#7e57c2',         // Soft purple
        'header-bg': 'linear-gradient(135deg, #5c6bc0, #3949ab)', // Night gradient
        'card-highlight': 'rgba(126, 87, 194, 0.1)'  // Soft purple highlight
    };
}