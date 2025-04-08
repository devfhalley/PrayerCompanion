#!/bin/bash

# This script tests whether the prayer_alarm.service can run the application
# without errors. This should be run before installing the system service.

echo "Testing Prayer Alarm service configuration..."
echo "----------------------------------------"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Please install it first."
    exit 1
fi

# Check if the app.py file exists
if [ ! -f "app.py" ]; then
    echo "ERROR: app.py not found in the current directory."
    echo "Please run this script from the raspberry_pi directory."
    exit 1
fi

# Check for required Python dependencies
echo "Checking Python dependencies..."
REQUIRED_PACKAGES=("flask" "flask_sock" "gtts" "pydub" "pygame" "requests" "schedule")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" &> /dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo "ERROR: The following Python packages are missing:"
    for package in "${MISSING_PACKAGES[@]}"; do
        echo "  - $package"
    done
    echo "Please install them with: pip3 install ${MISSING_PACKAGES[*]}"
    exit 1
fi

# Check if the required directories exist
if [ ! -d "sounds" ]; then
    echo "WARNING: 'sounds' directory not found. Creating it..."
    mkdir -p sounds
fi

if [ ! -d "murattal" ]; then
    echo "WARNING: 'murattal' directory not found. Creating it..."
    mkdir -p murattal
fi

# Check if the service file exists
if [ ! -f "prayer_alarm.service" ]; then
    echo "ERROR: prayer_alarm.service file not found."
    exit 1
fi

echo "All checks passed! The service configuration looks good."
echo "To install the service on your Raspberry Pi, follow these steps:"
echo "1. Copy all files to your Raspberry Pi"
echo "2. Follow the instructions in the INSTALL_SERVICE.md file"
echo "----------------------------------------"

# Try to start the application in the background and test if it's working
echo "Attempting to start the application in test mode for 5 seconds..."
python3 app.py > /dev/null 2>&1 &
PID=$!

# Wait for 5 seconds 
sleep 5

# Check if the process is still running
if kill -0 $PID 2>/dev/null; then
    echo "SUCCESS: Application started successfully!"
    # Kill the process
    kill $PID
    exit 0
else
    echo "ERROR: Application failed to start and stay running."
    echo "Check the application logs for details."
    exit 1
fi