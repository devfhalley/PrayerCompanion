/**
 * Theme Switcher
 * This script handles toggling between themes
 * with smooth transitions and localStorage persistence
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const themeToggle = document.getElementById('theme-toggle');
    const darkIcon = document.getElementById('theme-toggle-dark-icon');
    const lightIcon = document.getElementById('theme-toggle-light-icon');
    
    // Check for saved user preference, if any
    const userTheme = localStorage.getItem('theme');
    
    // Theme palette selector
    const themePaletteSelector = document.getElementById('theme-palette-selector');
    
    // List of available themes
    const availableThemes = ['light', 'dark', 'ocean', 'desert', 'lavender', 'mint'];
    
    // Set the initial theme based on user preference or system preference
    let initialTheme = 'light';
    
    // Handle legacy theme setting or set system default
    if (userTheme === 'dark' || (!userTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        initialTheme = 'dark';
    } else if (availableThemes.includes(userTheme)) {
        initialTheme = userTheme;
    }
    
    // Apply the initial theme
    document.documentElement.setAttribute('data-theme', initialTheme);
    
    // Update theme toggle button icons
    if (initialTheme === 'dark' || ['ocean', 'desert', 'lavender', 'mint'].includes(initialTheme)) {
        darkIcon.style.display = 'none';
        lightIcon.style.display = 'block';
    } else {
        darkIcon.style.display = 'block';
        lightIcon.style.display = 'none';
    }
    
    // Set initial selection in theme palette dropdown if it exists
    if (themePaletteSelector) {
        themePaletteSelector.value = initialTheme;
        
        // Listen for theme palette changes
        themePaletteSelector.addEventListener('change', function() {
            const newTheme = this.value;
            changeTheme(newTheme);
        });
    }
    
    // Toggle between light and dark theme when the button is clicked
    themeToggle.addEventListener('click', function() {
        let currentTheme = document.documentElement.getAttribute('data-theme');
        let newTheme;
        
        // Main toggle just switches between light and dark
        if (currentTheme === 'light' || 
            currentTheme === 'ocean' || 
            currentTheme === 'desert' || 
            currentTheme === 'lavender' || 
            currentTheme === 'mint') {
            newTheme = 'dark';
        } else {
            newTheme = 'light';
        }
        
        changeTheme(newTheme);
        
        // Update theme palette selector if it exists
        if (themePaletteSelector) {
            themePaletteSelector.value = newTheme;
        }
    });
    
    // Function to change theme
    function changeTheme(newTheme) {
        // Apply the new theme
        document.documentElement.setAttribute('data-theme', newTheme);
        
        // Save the preference to localStorage
        localStorage.setItem('theme', newTheme);
        
        // Update toggle button icons
        if (newTheme === 'dark' || ['ocean', 'desert', 'lavender', 'mint'].includes(newTheme)) {
            darkIcon.style.display = 'none';
            lightIcon.style.display = 'block';
        } else {
            darkIcon.style.display = 'block';
            lightIcon.style.display = 'none';
        }
        
        // Add a slight animation to indicate the theme change
        themeToggle.classList.add('animate-toggle');
        setTimeout(() => {
            themeToggle.classList.remove('animate-toggle');
        }, 300);
    }
    
    // Enhance keyboard accessibility
    themeToggle.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            themeToggle.click();
        }
    });
    
    // Add keyframe animation for theme toggle button
    const style = document.createElement('style');
    style.textContent = `
        @keyframes rotate-toggle {
            0% { transform: rotate(0); }
            100% { transform: rotate(360deg); }
        }
        
        .animate-toggle {
            animation: rotate-toggle 0.3s ease-in-out;
        }
    `;
    document.head.appendChild(style);
});