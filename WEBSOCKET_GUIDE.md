# WebSocket Support Guide

The Prayer Alarm System provides real-time functionality through WebSockets, enabling features like push-to-talk and instant audio notifications. This guide explains how to manage WebSocket functionality across different environments.

## WebSocket Features

1. **Push-to-Talk**: Allows real-time voice communication
2. **Audio Status Updates**: Provides instant feedback about what's currently playing
3. **Prayer Time Notifications**: Delivers real-time alerts for upcoming prayers

## Environment Variables

WebSocket behavior can be controlled through two main environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `ENABLE_WEBSOCKETS` | Force enable WebSockets regardless of environment | `false` |
| `BYPASS_REPLIT_CHECK` | Skip the Replit environment detection | `false` |

## Usage in Different Environments

### Replit (Development)

WebSockets are automatically disabled in Replit due to infrastructure limitations. However, you can test the UI with:

```
ENABLE_WEBSOCKETS=true BYPASS_REPLIT_CHECK=true python raspberry_pi/serve_dual.py
```

This won't make WebSockets fully functional but allows testing the interface.

### Local Development

WebSockets work locally with no special configuration:

```bash
python raspberry_pi/serve_dual.py
```

### Production Deployment

For production, both variables should be explicitly set to ensure reliable behavior:

```bash
ENABLE_WEBSOCKETS=true BYPASS_REPLIT_CHECK=true python raspberry_pi/serve_dual.py
```

Or in a systemd service file:

```ini
[Service]
Environment="ENABLE_WEBSOCKETS=true"
Environment="BYPASS_REPLIT_CHECK=true"
```

## Using a .env File

Create a `.env` file in the project root:

```
ENABLE_WEBSOCKETS=true
BYPASS_REPLIT_CHECK=true
```

The system will automatically load these variables when starting.

## Troubleshooting WebSocket Issues

### Connection Fails

If WebSocket connections fail:

1. Check that you're using HTTPS (required by modern browsers)
2. Verify network/firewall settings allow WebSocket connections
3. Confirm environment variables are correctly set

### Replit Limitations

Note that even with the environment variables set, WebSockets may not work fully in Replit due to infrastructure limitations. The UI will adapt to show fallback functionality when WebSockets are unavailable.

### Browser Support

Push-to-Talk requires a modern browser with WebSocket and audio API support:
- Chrome (recommended)
- Firefox
- Safari 12+
- Edge (Chromium-based)

## For More Information

For complete deployment instructions that ensure WebSockets work properly, see the [DEPLOYMENT.md](./DEPLOYMENT.md) file.