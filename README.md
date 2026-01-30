# SEARS Home Services - Voice AI Diagnostic Agent

A sophisticated voice AI system that assists customers experiencing issues with their home appliances through natural phone conversations. The agent guides callers through diagnostic steps, provides troubleshooting guidance, and schedules technician visits when needed.

## 🎯 Features

### Tier 1: Core Functionality
- **Natural Voice Conversations**: Real-time voice interaction using OpenAI's Realtime API
- **Appliance Identification**: Automatically identifies appliance types through conversation
- **Symptom Collection**: Gathers relevant problem details, error codes, and symptoms
- **Diagnostic Guidance**: Provides appliance-specific troubleshooting steps
- **Conversation Memory**: Maintains context throughout the call

### Tier 2: Technician Scheduling
- **Smart Matching**: Finds technicians by zip code and appliance specialty
- **Real-time Availability**: Shows available appointment slots
- **Automated Booking**: Books appointments with confirmation numbers
- **Voice Confirmation**: Verbally confirms all appointment details

### Tier 3: Visual Diagnosis
- **Email Integration**: Sends upload links via email
- **Image Upload Portal**: Mobile-friendly image upload page
- **Computer Vision Analysis**: Uses GPT-4 Vision for appliance diagnosis
- **Enhanced Troubleshooting**: Provides specific guidance based on visual analysis

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Phone Call    │────▶│     Twilio      │────▶│   FastAPI App   │
│   (Customer)    │     │   (Telephony)   │     │   (Backend)     │
│                 │◀────│                 │◀────│                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
               ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
               │                 │             │                 │             │                 │
               │  OpenAI        │             │   PostgreSQL    │             │   SendGrid      │
               │  Realtime API   │             │   (Database)    │             │   (Email)       │
               │                 │             │                 │             │                 │
               └─────────────────┘             └─────────────────┘             └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Twilio Account (with phone number)
- OpenAI API Key (with Realtime API access)
- ngrok (for local development)

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd sears-voice-ai

# Copy environment template
cp env.example.txt .env

# Edit .env with your credentials
```

### 2. Start with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app
```

### 3. Expose Local Server (Development)

```bash
# In a new terminal, start ngrok
ngrok http 8000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Update BASE_URL in your .env file
# Restart the app: docker-compose restart app
```

### 4. Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to Phone Numbers → Manage → Active Numbers
3. Select your phone number
4. Under "Voice & Fax", set:
   - **A Call Comes In**: Webhook
   - **URL**: `https://your-ngrok-url.ngrok.io/voice/incoming-call`
   - **HTTP Method**: POST

### 5. Configure SendGrid (Optional for Tier 3)

For image upload functionality:
1. Create a free SendGrid account at https://signup.sendgrid.com/
2. Verify your sender email at Settings → Sender Authentication
3. Create a "Full Access" API key at Settings → API Keys
4. Add to `.env`:
   ```
   SENDGRID_API_KEY=SG.your_api_key_here
   SENDGRID_FROM_EMAIL=your-verified@email.com
   ```

**Note for Demo:** The "From" email will be your verified personal email (e.g., `xingtaili1993@gmail.com`) with display name "Sears Home Services". In production, this would use an official `@sears.com` domain.

### 6. Test the System

Call your Twilio phone number and interact with the AI agent!

## 📁 Project Structure

```
sears-voice-ai/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── seed_data.py         # Sample data for technicians
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # REST API endpoints
│   │   ├── voice.py         # Twilio voice webhooks
│   │   └── upload.py        # Image upload endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # SQLAlchemy base
│   │   ├── technician.py    # Technician models
│   │   ├── availability.py  # Scheduling models
│   │   └── customer.py      # Customer models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── technician.py    # Technician schemas
│   │   ├── appointment.py   # Appointment schemas
│   │   ├── customer.py      # Customer schemas
│   │   └── conversation.py  # Conversation state
│   ├── services/
│   │   ├── __init__.py
│   │   ├── technician_service.py
│   │   ├── scheduling_service.py
│   │   ├── customer_service.py
│   │   ├── diagnostic_service.py
│   │   ├── email_service.py
│   │   └── image_service.py
│   └── voice/
│       ├── __init__.py
│       ├── session_manager.py  # Conversation state management
│       ├── agent.py            # AI agent with tools
│       └── realtime_handler.py # OpenAI Realtime API handler
├── uploads/                 # Uploaded images
├── docker-compose.yml       # Production Docker config
├── docker-compose.dev.yml   # Development Docker config
├── Dockerfile
├── requirements.txt
├── env.example.txt
└── README.md
```

## 🔧 API Endpoints

### Voice
- `POST /voice/incoming-call` - Twilio webhook for incoming calls
- `POST /voice/call-status` - Call status updates
- `WS /voice/media-stream/{call_sid}` - WebSocket for audio streaming

### Scheduling
- `GET /api/availability` - Get available appointment slots
- `POST /api/appointments` - Book an appointment
- `GET /api/appointments/{id}` - Get appointment details
- `DELETE /api/appointments/{id}` - Cancel appointment

### Technicians
- `GET /api/technicians` - List all technicians
- `GET /api/technicians/search/by-criteria` - Search by zip/specialty

### Image Upload
- `POST /image-upload-request` - Create upload request
- `GET /upload/{token}` - Upload page
- `POST /upload/{token}/submit` - Submit image
- `GET /upload/{token}/analysis` - Get image analysis

### Diagnostics
- `GET /api/diagnostics/appliances` - List supported appliances
- `GET /api/diagnostics/{type}/symptoms` - Get common symptoms
- `POST /api/diagnostics/{type}/troubleshoot` - Get troubleshooting steps

## 🗄️ Database Schema

### Technicians
- Personal info (name, email, phone)
- Employment details (employee_id, experience)
- Specialties (appliance types)
- Service areas (zip codes)

### Time Slots
- Available appointment windows
- 2-hour windows (8-10, 10-12, 1-3, 3-5)
- Linked to technicians

### Appointments
- Links customer, technician, and time slot
- Confirmation number
- Status tracking
- Issue details

### Customers
- Contact information
- Address details
- Appointment history

## 🛠️ Development

### Running Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL (or use SQLite for development)
# Update DATABASE_URL in .env

# Run the application
uvicorn app.main:app --reload
```

### Running Tests

```bash
pytest tests/ -v
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Yes |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `BASE_URL` | Public URL for webhooks | Yes |
| `SENDGRID_API_KEY` | SendGrid API key | No |
| `OPENAI_VOICE` | TTS voice (alloy, nova, etc.) | No |

## 🔒 Security Notes

- Never commit `.env` files
- Use environment variables for all secrets
- Configure CORS appropriately in production
- Use HTTPS for all webhooks
- Validate all user inputs

## 📄 License

This project was created as a technical assessment. All work remains the intellectual property of the author.

## 🤝 Support

For questions about this implementation, please contact the author.
