# Django Channels WebSocket Implementation

## Overview
The chat application now supports real-time messaging using Django Channels and WebSockets, with automatic fallback to polling if WebSocket connection fails.

## Requirements
- Redis server running on localhost:6379
- Django Channels packages (already installed)

## Running the Application

### Development Server with WebSocket Support
Instead of the regular Django development server, use Daphne:

```bash
daphne -b 127.0.0.1 -p 8000 core.asgi:application
```

Or use Django's runserver which now supports ASGI:

```bash
python manage.py runserver
```

### Redis Server
Make sure Redis is running:

```bash
# Windows
# Download Redis from: https://github.com/microsoftarchive/redis/releases
# Run redis-server.exe

# Linux/Mac
redis-server
```

## Features

### Real-time Messaging
- Messages appear instantly for all participants
- No page refresh required
- Automatic reconnection on connection loss

### Typing Indicators
- Shows when other user is typing
- Real-time updates

### Read Receipts
- Messages marked as read automatically
- Visual indicators for read status

### User Presence
- Notifications when users join/leave chat
- Real-time user status

### Fallback Mechanism
- Automatically falls back to 5-second polling if WebSocket fails
- Seamless user experience

## Testing

### Manual Testing
1. Open two browser windows
2. Log in as different users
3. Start a chat between them
4. Send messages and observe real-time updates

### Command-line Testing
```bash
python manage.py test_websocket
```

## Architecture

### WebSocket URL Pattern
```
ws://localhost:8000/ws/chat/<room_id>/
```

### Message Types
- `message`: Regular chat message
- `typing`: Typing indicator
- `mark_read`: Mark messages as read
- `user_join`: User joined notification
- `user_leave`: User left notification

### Consumer
Located in `chat/consumers.py`, handles all WebSocket events and database operations.

### Routing
Configured in `chat/routing.py` and `core/asgi.py`.

## Troubleshooting

### WebSocket Connection Failed
1. Check if Redis is running
2. Verify CHANNEL_LAYERS configuration in settings.py
3. Ensure using Daphne or ASGI-compatible server

### Messages Not Appearing
1. Check browser console for WebSocket errors
2. Verify user permissions for chat room
3. Check Django logs for errors

### Fallback to Polling
If WebSocket fails, the app automatically falls back to polling. Check console for "Falling back to polling mechanism" message.