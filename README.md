# SIP Trunking SaaS Platform

A comprehensive SIP (Session Initiation Protocol) trunking solution built for SaaS applications. This platform enables voice communication over IP networks with a complete REST API, WebSocket support, user management, and call tracking.

## Features

### Core SIP Functionality
- **SIP Server**: Handles SIP protocol messages (INVITE, ACK, BYE, CANCEL, etc.)
- **SIP Client**: Initiates and receives calls
- **Call Management**: Track active calls and manage call state
- **RTP Support**: Real-time Transport Protocol for audio streaming
- **Codec Support**: Multiple audio codec options (PCMU, PCMA, G.729, etc.)

### SaaS Features
- **REST API**: Complete FastAPI-based REST API for SIP operations
- **User Authentication**: JWT-based authentication and authorization
- **Multi-tenant Support**: Multiple users with separate SIP accounts
- **Call History**: Database-backed call records and analytics
- **WebSocket Support**: Real-time call status updates
- **Database Models**: SQLAlchemy models for users, accounts, and calls
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## Architecture

```
┌─────────────┐         SIP Protocol         ┌─────────────┐
│ SIP Client  │◄────────────────────────────►│ SIP Server  │
│             │                               │             │
│             │         RTP Media             │             │
│             │◄────────────────────────────►│             │
└─────────────┘                               └─────────────┘
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd SIP-Trunking
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Edit `config/server_config.yaml` to configure the SIP server:
- Server IP and port
- Domain/realm
- Authentication credentials
- Codec preferences

Edit `config/client_config.yaml` to configure the SIP client:
- Server address
- Client credentials
- Local RTP port range

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

The database will be automatically initialized on first API startup.

### 3. Start the API Server

```bash
python run_server.py
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### 4. Use the Web Dashboard

Open `web/dashboard.html` in your browser for a graphical interface to:
- Register/login users
- Manage SIP accounts
- Make calls
- Monitor calls in real-time via WebSocket

### 4. Start the SIP Server (Optional - for standalone SIP server)

```bash
python examples/server_example.py
```

## API Usage

### Authentication

```python
import requests

# Register a new user
response = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "user@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
})

# Login
response = requests.post("http://localhost:8000/api/v1/auth/login", data={
    "username": "testuser",
    "password": "password123"
})
token = response.json()["access_token"]
```

### Create SIP Account

```python
headers = {"Authorization": f"Bearer {token}"}

response = requests.post("http://localhost:8000/api/v1/accounts", headers=headers, json={
    "account_name": "My SIP Account",
    "username": "sipuser",
    "password": "sippass",
    "server_host": "sip.provider.com",
    "server_port": 5060,
    "domain": "provider.com"
})
account = response.json()
```

### Make a Call

```python
response = requests.post("http://localhost:8000/api/v1/calls", headers=headers, json={
    "sip_account_id": account["id"],
    "to_uri": "sip:user@example.com"
})
call = response.json()
```

### Get Call Status

```python
response = requests.get(
    f"http://localhost:8000/api/v1/calls/{call['call_id']}/status",
    headers=headers
)
status = response.json()
```

### WebSocket for Real-time Updates

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/calls');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Call update:', data);
};
```

## Direct SIP Client Usage

For direct SIP client usage without the API:

```python
from src.client.sip_client import SIPClient

client = SIPClient(config_path='config/client_config.yaml')
client.start()
client.register()
call_id = client.make_call('sip:user@example.com')
# ... handle call
client.hangup(call_id)
client.stop()
```

## Project Structure

```
SIP-Trunking/
├── src/
│   ├── api/                    # REST API Layer
│   │   ├── main.py            # FastAPI application
│   │   └── routes/            # API routes
│   │       ├── auth.py        # Authentication endpoints
│   │       ├── accounts.py    # SIP account management
│   │       ├── calls.py       # Call management
│   │       └── websocket.py   # WebSocket endpoints
│   ├── database/              # Database models and config
│   │   ├── models.py          # SQLAlchemy models
│   │   └── database.py        # Database session management
│   ├── services/              # Business logic services
│   │   ├── call_service.py   # Call management service
│   │   └── websocket_manager.py  # WebSocket manager
│   ├── server/                # SIP Server
│   │   ├── sip_server.py
│   │   └── call_handler.py
│   ├── client/                # SIP Client
│   │   ├── sip_client.py
│   │   └── call_manager.py
│   ├── protocol/              # SIP Protocol Implementation
│   │   ├── sip_message.py
│   │   ├── sip_parser.py
│   │   └── sip_utils.py
│   └── media/                 # Media Handling
│       ├── rtp_handler.py
│       └── codec_manager.py
├── config/
│   ├── server_config.yaml     # Server configuration
│   └── client_config.yaml     # Client configuration
├── examples/
│   ├── basic_call.py          # Basic call example
│   ├── server_example.py      # Server example
│   └── api_usage.py           # API usage examples
├── run_server.py              # API server startup script
├── requirements.txt
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get access token
- `GET /api/v1/auth/me` - Get current user information

### SIP Accounts
- `POST /api/v1/accounts` - Create a SIP account
- `GET /api/v1/accounts` - List all SIP accounts
- `GET /api/v1/accounts/{id}` - Get SIP account details
- `PUT /api/v1/accounts/{id}` - Update SIP account
- `DELETE /api/v1/accounts/{id}` - Delete SIP account

### Calls
- `POST /api/v1/calls` - Initiate a new call
- `GET /api/v1/calls` - List all calls
- `GET /api/v1/calls/{call_id}` - Get call details
- `GET /api/v1/calls/{call_id}/status` - Get call status
- `POST /api/v1/calls/{call_id}/hangup` - Hang up a call

### WebSocket
- `WS /api/v1/ws/calls` - Real-time call updates
- `WS /api/v1/ws/calls/{call_id}` - Call-specific updates

## SIP Protocol Overview

SIP (Session Initiation Protocol) is an application-layer protocol for establishing, modifying, and terminating multimedia sessions. Key SIP methods:

- **INVITE**: Initiates a call
- **ACK**: Confirms final response to INVITE
- **BYE**: Terminates a call
- **CANCEL**: Cancels a pending request
- **REGISTER**: Registers a user's location
- **OPTIONS**: Queries server capabilities

## Database Schema

- **Users**: User accounts for the SaaS platform
- **SIPAccounts**: SIP account configurations per user
- **Calls**: Active and historical call records
- **CallRecords**: Detailed call event logs

## Security Considerations

- Passwords are hashed using bcrypt
- JWT tokens for API authentication
- CORS configuration for web clients
- SIP passwords should be encrypted in production
- Use HTTPS/WSS in production environments

## Development

### Running Tests

```bash
# Add tests when implemented
pytest tests/
```

### Database Migrations

```bash
# Using Alembic (when configured)
alembic upgrade head
```

## Production Deployment

1. Update `config/server_config.yaml` with production settings
2. Use a production database (PostgreSQL recommended)
3. Set secure `secret_key` for JWT tokens
4. Configure proper CORS origins
5. Use environment variables for sensitive data
6. Enable HTTPS/TLS for API endpoints
7. Configure firewall rules for SIP ports (5060/5061)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

