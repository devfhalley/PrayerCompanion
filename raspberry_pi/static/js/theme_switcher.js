/**
 * Theme Switcher
 * This script handles toggling between light and dark theme
 * with smooth transitions and localStorage persistence
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const themeToggle = document.getElementById('theme-toggle');
    const darkIcon = document.getElementById('theme-toggle-dark-icon');
    const lightIcon = document.getElementById('theme-toggle-light-icon');
    
    // Check for saved user preference, if any
    const userTheme = localStorage.getItem('theme');
    
    // Set the initial theme based on user preference or system preference
    if (userTheme === 'dark' || (!userTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        darkIcon.style.display = 'none';
        lightIcon.style.display = 'block';
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        darkIcon.style.display = 'block';
        lightIcon.style.display = 'none';
    }
    
    // Toggle theme when the button is clicked
    themeToggle.addEventListener('click', function() {
        let currentTheme = document.documentElement.getAttribute('data-theme');
        let newTheme;
        
        if (currentTheme === 'light') {
            newTheme = 'dark';
            darkIcon.style.display = 'none';
            lightIcon.style.display = 'block';
        } else {
            newTheme = 'light';
            darkIcon.style.display = 'block';
            lightIcon.style.display = 'none';
        }
        
        // Apply the new theme
        document.documentElement.setAttribute('data-theme', newTheme);
        
        // Save the preference to localStorage
        localStorage.setItem('theme', newTheme);
        
        // Add a slight animation to indicate the theme change
        themeToggle.classList.add('animate-toggle');
        setTimeout(() => {
            themeToggle.classList.remove('animate-toggle');
        }, 300);
    });
    
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