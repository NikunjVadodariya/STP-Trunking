# Quick Start Guide

## 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## 2. Start the API Server

```bash
python run_server.py
```

The API will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## 3. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'
```

## 4. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

Save the `access_token` from the response.

## 5. Create a SIP Account

```bash
curl -X POST "http://localhost:8000/api/v1/accounts" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "My SIP Account",
    "username": "sipuser",
    "password": "sippass",
    "server_host": "sip.provider.com",
    "server_port": 5060,
    "domain": "provider.com"
  }'
```

Save the `id` from the response.

## 6. Make a Call

```bash
curl -X POST "http://localhost:8000/api/v1/calls" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sip_account_id": 1,
    "to_uri": "sip:user@example.com"
  }'
```

## 7. Check Call Status

```bash
curl -X GET "http://localhost:8000/api/v1/calls/CALL_ID/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 8. Hang Up

```bash
curl -X POST "http://localhost:8000/api/v1/calls/CALL_ID/hangup" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## WebSocket Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/calls');

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Call update:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};
```

## Python Client Example

See `examples/api_usage.py` for a complete Python example.

## Next Steps

1. Configure your SIP provider settings in the SIP account
2. Set up proper authentication and security
3. Customize the API endpoints as needed
4. Add webhooks for call events
5. Implement call recording and analytics

