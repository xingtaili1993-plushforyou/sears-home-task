# SEARS Home Services - Voice AI Diagnostic Agent

A production-grade voice AI system that assists customers experiencing issues with their home appliances through natural phone conversations. The agent -- named **Samantha** -- guides callers through diagnostic steps, provides empathetic troubleshooting guidance, schedules technician visits, and follows up with email summaries and SMS confirmations.

## Features

### Core Voice AI
- **Natural Voice Conversations**: Real-time voice interaction using OpenAI's Realtime API with low-latency audio streaming
- **Warm, Empathetic Persona**: "Samantha" uses the shimmer voice for a natural, caring tone
- **Appliance Identification**: Automatically identifies appliance types through conversation
- **Symptom Collection**: Gathers problem details, error codes, and symptoms
- **Diagnostic Guidance**: Provides appliance-specific troubleshooting steps
- **Conversation Memory**: Maintains full context throughout the call

### Intelligent Scheduling
- **Smart Matching**: Finds technicians by zip code and appliance specialty
- **Real-time Availability**: Shows available appointment slots (auto-refreshed on startup)
- **Automated Booking**: Books appointments with confirmation numbers
- **Voice Confirmation**: Verbally confirms all appointment details

### Visual Diagnosis
- **Email Integration**: Sends upload links via SendGrid
- **Image Upload Portal**: Mobile-friendly image upload page
- **Computer Vision Analysis**: Uses GPT-4 Vision for appliance diagnosis
- **Analysis Email**: Sends AI analysis results back to the customer

### World-Class Agent Upgrades (v2.0)
- **Returning Customer Recognition**: Greets returning customers by name with history context
- **Frustration Detection & Empathy**: Detects customer frustration and responds with de-escalation
- **Human Escalation**: Seamless transfer to live agents with context handoff
- **Post-Call Summary Email**: Professional HTML email summarizing the call, troubleshooting steps, and appointment details
- **SMS Confirmations**: Sends text message appointment confirmations via Twilio
- **Live Dashboard**: Real-time web dashboard showing transcript, tool calls, and sentiment
- **Email/Phone Verification**: Spells back emails letter-by-letter and reads phone numbers in groups for accuracy

## Architecture

```
Phone Call ──▶ Twilio ──▶ ngrok (HTTPS) ──▶ EC2 / Local
                                               │
                                     ┌─────────┼─────────┐
                                     │         │         │
                                     ▼         ▼         ▼
                                  FastAPI   PostgreSQL  Redis
                                  :8000      :5432     :6379
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
              OpenAI Realtime   SendGrid (Email)  Twilio (SMS)
              + GPT-4 Vision
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Twilio Account (with phone number)
- OpenAI API Key (with Realtime API access)
- ngrok account (free tier works)
- SendGrid API Key (optional, for email features)

### 1. Clone and Configure

```bash
git clone https://github.com/xingtaili1993-plushforyou/sears-home-task.git
cd sears-home-task

# Copy environment template and fill in your credentials
cp env.example.txt .env
```

### 2. Start with Docker Compose

```bash
docker compose up -d --build

# Verify all services are running
docker compose ps

# Check logs
docker compose logs -f app
```

### 3. Expose via ngrok

```bash
ngrok http 8000

# Copy the HTTPS URL and update BASE_URL in .env
# Then restart: docker compose restart app
```

### 4. Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com)
2. Phone Numbers > Manage > Active Numbers
3. Select your phone number
4. Under "Voice Configuration", set:
   - **A Call Comes In**: Webhook
   - **URL**: `https://your-ngrok-url/voice/incoming-call`
   - **HTTP Method**: POST

### 5. Test

Call your Twilio phone number and talk to Samantha!

## EC2 Deployment

The application is deployed on AWS EC2 for production use.

### Infrastructure
- **Instance**: t3.medium (2 vCPU, 4 GiB RAM), Ubuntu 24.04 LTS
- **Storage**: 30 GiB gp3
- **HTTPS**: ngrok tunnel with static domain
- **Containers**: Docker Compose (app + PostgreSQL + Redis)

### Deploy to EC2

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install ngrok
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
  && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list \
  && sudo apt update && sudo apt install ngrok

# Clone, configure, and start
git clone https://github.com/xingtaili1993-plushforyou/sears-home-task.git
cd sears-home-task
nano .env  # Add your credentials
docker compose up -d --build

# Start ngrok in a screen session
ngrok config add-authtoken <YOUR_TOKEN>
screen -dmS ngrok ngrok http 8000 --domain=your-domain.ngrok-free.app
```

### Verify Deployment
- Root: `https://your-domain.ngrok-free.app/`
- Health: `https://your-domain.ngrok-free.app/api/health`
- Dashboard: `https://your-domain.ngrok-free.app/dashboard`
- API Docs: `https://your-domain.ngrok-free.app/docs`

## Project Structure

```
sears-home-task/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration management
│   ├── database.py              # Database connection
│   ├── seed_data.py             # Seed data with auto time-slot refresh
│   ├── api/
│   │   ├── routes.py            # REST API endpoints
│   │   ├── voice.py             # Twilio voice webhooks + transfer
│   │   ├── upload.py            # Image upload endpoints
│   │   └── dashboard.py         # Live dashboard page + WebSocket
│   ├── models/
│   │   ├── base.py              # SQLAlchemy base
│   │   ├── technician.py        # Technician models
│   │   ├── availability.py      # Scheduling models
│   │   └── customer.py          # Customer models
│   ├── schemas/
│   │   ├── technician.py        # Technician schemas
│   │   ├── appointment.py       # Appointment schemas
│   │   ├── customer.py          # Customer schemas
│   │   └── conversation.py      # Conversation state
│   ├── services/
│   │   ├── technician_service.py
│   │   ├── scheduling_service.py
│   │   ├── customer_service.py  # Includes customer history lookup
│   │   ├── diagnostic_service.py
│   │   ├── email_service.py     # Call summary + image analysis emails
│   │   ├── image_service.py
│   │   └── sms_service.py       # SMS confirmations via Twilio
│   └── voice/
│       ├── session_manager.py   # Conversation state management
│       ├── agent.py             # AI agent (Samantha) with 8 tools
│       └── realtime_handler.py  # OpenAI Realtime API + dashboard broadcast
├── tests/
│   ├── test_voice_agent.py      # Agent tool tests
│   ├── test_services.py         # Service layer tests
│   ├── test_api.py              # API endpoint tests
│   └── ...
├── .github/
│   └── workflows/
│       └── ci.yml               # CI pipeline (lint + test + Docker build)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml               # Black, isort, pytest config
├── .flake8                      # Flake8 config
└── Makefile
```

## API Endpoints

### Voice
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice/incoming-call` | Twilio webhook for incoming calls |
| POST | `/voice/call-status` | Call status updates |
| WS | `/voice/media-stream/{call_sid}` | WebSocket for audio streaming |
| POST | `/voice/transfer/{call_sid}` | Transfer call to human agent |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Live conversation dashboard |
| WS | `/dashboard/ws` | Dashboard WebSocket feed |

### Scheduling
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/availability` | Get available appointment slots |
| POST | `/api/appointments` | Book an appointment |
| GET | `/api/appointments/{id}` | Get appointment details |
| DELETE | `/api/appointments/{id}` | Cancel appointment |

### Technicians
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/technicians` | List all technicians |
| GET | `/api/technicians/search/by-criteria` | Search by zip/specialty |

### Image Upload
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/image-upload-request` | Create upload request |
| GET | `/upload/{token}` | Upload page |
| POST | `/upload/{token}/submit` | Submit image |
| GET | `/upload/{token}/analysis` | Get image analysis |

### Diagnostics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/diagnostics/appliances` | List supported appliances |
| GET | `/api/diagnostics/{type}/symptoms` | Get common symptoms |
| POST | `/api/diagnostics/{type}/troubleshoot` | Get troubleshooting steps |

## AI Agent Tools

The voice agent (Samantha) has 8 tools available during calls:

| Tool | Description |
|------|-------------|
| `get_troubleshooting_steps` | Retrieve diagnostic steps for an appliance + symptom |
| `check_technician_availability` | Search for available technicians by zip code |
| `book_appointment` | Book a technician appointment |
| `request_image_upload` | Send an image upload link to the customer's email |
| `update_customer_info` | Update customer name, email, or address |
| `transfer_to_human` | Transfer the call to a live human agent |
| `send_call_summary` | Email a post-call summary to the customer |
| `send_sms_confirmation` | Send an SMS appointment confirmation |

## CI/CD Pipeline

The project uses a full CI/CD pipeline via GitHub Actions (`.github/workflows/ci.yml`), triggered on every push and pull request to `main`.

### Pipeline Overview

```
git push to main
       │
       ▼
  GitHub Actions
       │
       ├── Lint Job ──────────▶ black --check . (formatting)
       │                        isort --check . (import ordering)
       │                        flake8 (style / unused imports)
       │
       ├── Test Job ──────────▶ pytest --cov=app (unit tests + coverage)
       │                        Uploads coverage-report artifact
       │
       └── Docker Build Job ──▶ docker build -t sears-voice-ai:test .
                                Validates image builds successfully
```

### CI Jobs Detail

| Job | Runtime | What It Checks |
|-----|---------|----------------|
| **Lint** | ~25s | Code formatting (black), import order (isort), style rules (flake8) |
| **Test** | ~35s | All unit tests with `pytest`, generates XML coverage report |
| **Docker Build** | ~50s | Full Docker image build to catch dependency or build issues |

All three jobs run in parallel on `ubuntu-latest` with Python 3.12.

### Deployment to EC2

After CI passes, deployment to the EC2 production server is done via SSH:

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Pull latest changes and rebuild
cd sears-home-task
git pull origin main
docker compose down
docker compose up -d --build

# Verify
docker compose ps
curl http://localhost:8000/api/health
```

### Code Quality Tools

| Tool | Config File | Purpose |
|------|-------------|---------|
| black | `pyproject.toml` | Auto-formatting (line length 88) |
| isort | `pyproject.toml` | Import sorting (black-compatible profile) |
| flake8 | `.flake8` | Linting (max line 120, per-file ignores) |
| pytest | `pyproject.toml` | Testing (async mode auto, verbose output) |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key (with Realtime API access) | Yes |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Yes |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `BASE_URL` | Public HTTPS URL (ngrok URL) | Yes |
| `SENDGRID_API_KEY` | SendGrid API key for emails | No |
| `SENDGRID_FROM_EMAIL` | Verified sender email | No |
| `OPENAI_VOICE` | TTS voice (default: shimmer) | No |
| `REDIS_URL` | Redis connection string | No |

## Testing

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=term-missing -v

# Run specific test file
pytest tests/test_voice_agent.py -v
```

## Security Notes

- Never commit `.env` files (it's in `.gitignore`)
- Use environment variables for all secrets
- On EC2, restrict `.env` permissions: `chmod 600 .env`
- Use HTTPS (via ngrok) for all webhooks
- Twilio webhook validation is enabled

## License

This project was created as a technical assessment for Sears Home Services AI Engineer position.
