# Installing Prayer Alarm as a System Service

This guide will help you set up the Prayer Alarm application to start automatically when your Raspberry Pi boots up.

## Prerequisites

1. Make sure all required dependencies are installed:
   ```
   pip3 install flask flask_sock gtts pydub pygame requests schedule
   ```

2. Run the test script to verify your setup:
   ```
   ./test_service.sh
   ```
   
   Fix any issues before proceeding with the service installation.

## Installation Steps

1. Copy the service file to the systemd directory:
   ```
   sudo cp prayer_alarm.service /etc/systemd/system/
   ```

2. Make sure the paths in the service file match your installation:
   - Edit `/etc/systemd/system/prayer_alarm.service` if needed
   - Change the `WorkingDirectory` to match where you installed the application
   - Update the `User` to match your Raspberry Pi username (default is 'pi')

3. Reload the systemd daemon to recognize the new service:
   ```
   sudo systemctl daemon-reload
   ```

4. Enable the service to start at boot:
   ```
   sudo systemctl enable prayer_alarm.service
   ```

5. Start the service immediately:
   ```
   sudo systemctl start prayer_alarm.service
   ```

## Managing the Service

- Check service status:
  ```
  sudo systemctl status prayer_alarm.service
  ```

- Stop the service:
  ```
  sudo systemctl stop prayer_alarm.service
  ```

- Restart the service:
  ```
  sudo systemctl restart prayer_alarm.service
  ```

- View service logs:
  ```
  sudo journalctl -u prayer_alarm.service
  ```
  
  To see only the most recent logs:
  ```
  sudo journalctl -u prayer_alarm.service -n 50
  ```
  
  To follow logs in real-time:
  ```
  sudo journalctl -u prayer_alarm.service -f
  ```

## Troubleshooting

If the service fails to start:

1. Check the logs for errors:
   ```
   sudo journalctl -u prayer_alarm.service -n 50
   ```

2. Verify the file paths in the service file are correct.

3. Make sure the Python environment has all required dependencies installed.

4. Check permissions of the application directory and files.

5. Audio device permissions:
   - Make sure the user running the service has permission to access audio devices:
     ```
     sudo usermod -a -G audio pi
     ```
   - You may need to reboot after adding the user to the audio group:
     ```
     sudo reboot
     ```

6. If Python fails to find the system audio device, try installing additional audio libraries:
   ```
   sudo apt-get install -y alsa-utils
   sudo apt-get install -y libasound2-dev
   ```