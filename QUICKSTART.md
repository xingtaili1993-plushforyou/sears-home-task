# Quick Start Guide

Get the SEARS Voice AI Diagnostic Agent running in 5 minutes.

## Prerequisites

- Docker & Docker Compose installed
- Twilio account with phone number
- OpenAI API key (with Realtime API access)
- ngrok account (free tier works)

## Step 1: Configure Environment

```bash
# Copy the example environment file
cp env.example.txt .env

# Edit .env with your credentials
# Required:
#   - OPENAI_API_KEY
#   - TWILIO_ACCOUNT_SID
#   - TWILIO_AUTH_TOKEN
#   - TWILIO_PHONE_NUMBER
```

## Step 2: Start the Application

```bash
# Start all services (app, database, redis)
docker-compose up -d

# Check logs to verify startup
docker-compose logs -f app
```

Wait until you see "Application ready" in the logs.

## Step 3: Expose to Internet (Development)

```bash
# In a new terminal
ngrok http 8000

# Copy the https URL (e.g., https://abc123.ngrok.io)
```

Update `.env` with your ngrok URL:
```
BASE_URL=https://abc123.ngrok.io
```

Restart the app:
```bash
docker-compose restart app
```

## Step 4: Configure Twilio

### Option A: Using the setup script
```bash
# Activate virtual environment or use docker
docker-compose exec app python scripts/setup_twilio.py --base-url https://your-ngrok-url.ngrok.io
```

### Option B: Manual configuration
1. Go to [Twilio Console](https://console.twilio.com)
2. Phone Numbers → Manage → Active Numbers
3. Click your phone number
4. Under "Voice & Fax":
   - **A Call Comes In**: Webhook
   - **URL**: `https://your-ngrok-url.ngrok.io/voice/incoming-call`
   - **HTTP Method**: POST

## Step 5: Test!

Call your Twilio phone number and start talking to the AI agent!

## Verify Setup

Check these endpoints:
- Health: http://localhost:8000/api/health
- Docs: http://localhost:8000/docs
- Voice Config: http://localhost:8000/voice/test

## Troubleshooting

### "No technicians found"
The database seeds automatically on first run. If issues persist:
```bash
docker-compose exec app python -c "from app.database import get_db_context; from app.seed_data import seed_database; 
with get_db_context() as db: seed_database(db)"
```

### WebSocket connection fails
- Ensure ngrok is running and URL is correct
- Check that BASE_URL in .env matches your ngrok URL
- Verify Twilio webhook is configured correctly

### OpenAI errors
- Verify API key is correct
- Ensure you have access to the Realtime API
- Check OpenAI dashboard for usage limits

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
