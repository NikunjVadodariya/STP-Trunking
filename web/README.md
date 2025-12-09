# Web Dashboard

A modern HTML dashboard for interacting with the SIP Trunking API.

## Features

- **User Authentication**: Register and login
- **SIP Account Management**: Create and manage SIP accounts
- **Make Calls**: Initiate calls through the API
- **Call Management**: View active calls and hang up
- **Real-time Updates**: WebSocket connection for live call status updates

## Usage

1. Make sure the API server is running:
   ```bash
   python run_server.py
   ```

2. Open `dashboard.html` in a web browser

3. Register a new account or login with existing credentials

4. Create a SIP account with your provider details

5. Make calls and monitor them in real-time

## API Endpoints Used

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/accounts` - List SIP accounts
- `POST /api/v1/accounts` - Create SIP account
- `DELETE /api/v1/accounts/{id}` - Delete SIP account
- `POST /api/v1/calls` - Make a call
- `GET /api/v1/calls` - List calls
- `POST /api/v1/calls/{call_id}/hangup` - Hang up a call

## WebSocket

- `ws://localhost:8000/api/v1/ws/calls` - Real-time call updates

## Configuration

If your API is running on a different host/port, update the constants in the JavaScript:

```javascript
const API_BASE = 'http://localhost:8000/api/v1';
const WS_BASE = 'ws://localhost:8000/api/v1/ws';
```

## Browser Compatibility

Works in all modern browsers that support:
- Fetch API
- WebSocket API
- ES6 JavaScript

