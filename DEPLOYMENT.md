# Prayer Alarm System - Deployment Guide

This guide provides instructions for deploying the Prayer Alarm System to different environments, with particular focus on ensuring WebSocket functionality works correctly.

## Table of Contents
1. [Environment Variables](#environment-variables)
2. [Deploying to Raspberry Pi](#deploying-to-raspberry-pi)
3. [Deploying to a VPS/Cloud Server](#deploying-to-a-vpscloud-server)
4. [Setting up HTTPS](#setting-up-https)
5. [Testing Your Deployment](#testing-your-deployment)
6. [Troubleshooting](#troubleshooting)

## Environment Variables

The Prayer Alarm System uses environment variables to control certain features, particularly WebSockets. You can set these in a `.env` file or directly in your server environment.

### Key Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ENABLE_WEBSOCKETS` | Force enable WebSockets regardless of environment | `false` |
| `BYPASS_REPLIT_CHECK` | Skip the Replit environment detection | `false` |
| `DATABASE_URL` | PostgreSQL database connection string | Varies by environment |

### Setting Environment Variables

**Option 1: Using a .env file**
```
# .env file
ENABLE_WEBSOCKETS=true
BYPASS_REPLIT_CHECK=true
```

**Option 2: Setting in Linux environment**
```bash
export ENABLE_WEBSOCKETS=true
export BYPASS_REPLIT_CHECK=true
```

**Option 3: Setting in systemd service file**
```ini
[Service]
Environment="ENABLE_WEBSOCKETS=true"
Environment="BYPASS_REPLIT_CHECK=true"
```

## Deploying to Raspberry Pi

### 1. Transfer Files

```bash
# Option 1: Git clone method
git clone <repository-url> /home/pi/prayer_alarm

# Option 2: Direct transfer
scp -r raspberry_pi/ pi@<raspberry-ip>:/home/pi/prayer_alarm
```

### 2. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-pygame postgresql libpq-dev

cd /home/pi/prayer_alarm
pip3 install -r requirements.txt
```

### 3. Set Up PostgreSQL Database

```bash
sudo -u postgres createuser prayer_user
sudo -u postgres createdb prayer_db
sudo -u postgres psql -c "ALTER USER prayer_user WITH PASSWORD 'your-secure-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE prayer_db TO prayer_user;"
```

### 4. Create .env File

```bash
cat > /home/pi/prayer_alarm/.env << EOF
ENABLE_WEBSOCKETS=true
BYPASS_REPLIT_CHECK=true
DATABASE_URL=postgresql://prayer_user:your-secure-password@localhost/prayer_db
EOF
```

### 5. Configure as a Service

```bash
sudo cp /home/pi/prayer_alarm/raspberry_pi/prayer_alarm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable prayer_alarm
sudo systemctl start prayer_alarm
```

### 6. Check Service Status

```bash
sudo systemctl status prayer_alarm
sudo journalctl -u prayer_alarm -f
```

## Deploying to a VPS/Cloud Server

### 1. Provision a Server

- Recommended: Ubuntu 20.04 LTS or newer
- Minimum 1GB RAM
- 1 CPU core
- 10GB disk space

### 2. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql nginx certbot python3-certbot-nginx
```

### 3. Set Up PostgreSQL Database

```bash
sudo -u postgres createuser prayer_user
sudo -u postgres createdb prayer_db
sudo -u postgres psql -c "ALTER USER prayer_user WITH PASSWORD 'your-secure-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE prayer_db TO prayer_user;"
```

### 4. Create Application Directory & Virtual Environment

```bash
mkdir -p /opt/prayer_alarm
cp -r . /opt/prayer_alarm/

cd /opt/prayer_alarm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Set Up NGINX

Create an NGINX config file at `/etc/nginx/sites-available/prayer_alarm`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;  # Replace with your domain name

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/prayer_alarm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Create a Systemd Service

Create a file at `/etc/systemd/system/prayer_alarm.service`:

```ini
[Unit]
Description=Prayer Alarm Service
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/opt/prayer_alarm
Environment="ENABLE_WEBSOCKETS=true"
Environment="BYPASS_REPLIT_CHECK=true"
Environment="DATABASE_URL=postgresql://prayer_user:your-secure-password@localhost/prayer_db"
ExecStart=/opt/prayer_alarm/venv/bin/python raspberry_pi/serve_dual.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable prayer_alarm
sudo systemctl start prayer_alarm
```

## Setting up HTTPS

For WebSockets to work reliably, HTTPS is strongly recommended (and required by many modern browsers).

### Using Let's Encrypt

```bash
sudo certbot --nginx -d yourdomain.com
```

Certbot will automatically update your NGINX configuration. Test automatic renewal:

```bash
sudo certbot renew --dry-run
```

### Using Self-Signed Certificates (Development only)

For testing purposes, you can generate self-signed certificates:

```bash
cd /opt/prayer_alarm/raspberry_pi/ssl
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes
```

Then use the HTTPS server option in `serve_dual.py` instead of the standard HTTP server.

## Testing Your Deployment

1. Visit your domain in a browser
2. Navigate to the Push-to-Talk page
3. Check the browser console for WebSocket connection status
4. Test audio functionality

## Troubleshooting

### WebSockets Not Working

1. Check browser console for WebSocket errors
2. Verify your server has HTTPS properly configured
3. Ensure NGINX is configured with WebSocket support
4. Check if WebSockets are being forcibly enabled with environment variables

### Database Connection Issues

1. Verify the `DATABASE_URL` environment variable
2. Check if PostgreSQL is running: `sudo systemctl status postgresql`
3. Ensure the database user has proper permissions

### Audio Not Playing

1. Check if `pygame` is properly installed
2. Verify audio files exist in the expected directories
3. Check system sound settings and permissions

### Service Won't Start

1. Check service logs: `sudo journalctl -u prayer_alarm -f`
2. Verify all dependencies are properly installed
3. Check file permissions in the application directory

## Best Practices

1. **Backups**: Regularly backup your database
   ```bash
   pg_dump -U prayer_user prayer_db > backup_$(date +%Y%m%d).sql
   ```

2. **Updates**: Keep your system updated
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Monitoring**: Set up basic monitoring for your service
   ```bash
   sudo apt install -y htop
   ```

4. **Log Rotation**: Configure log rotation to prevent disk space issues
   ```bash
   sudo nano /etc/logrotate.d/prayer_alarm
   ```

   Add the following configuration:
   ```
   /opt/prayer_alarm/logs/*.log {
       weekly
       rotate 12
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

---

By following this guide, you should have a fully functional Prayer Alarm System deployed on your chosen platform with working WebSockets for real-time functionality.