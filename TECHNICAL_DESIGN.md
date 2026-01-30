# Technical Design Document

## SEARS Home Services - Voice AI Diagnostic Agent

**Author:** AI Engineering Candidate  
**Date:** January 2026  
**Version:** 1.0

---

## 1. Executive Summary

This document describes the architecture and design decisions for a voice-based AI system that assists customers with home appliance diagnostics. The system handles inbound phone calls, guides customers through troubleshooting, and schedules technician visits when needed.

---

## 2. Architectural Decisions

### 2.1 Technology Stack Selection

| Component | Choice | Alternatives Considered | Rationale |
|-----------|--------|------------------------|-----------|
| **Telephony** | Twilio | Vonage, Telnyx, Plivo | Industry leader, excellent documentation, robust WebSocket support for media streams, mature Python SDK |
| **Voice AI** | OpenAI Realtime API | Deepgram + GPT-4 + ElevenLabs | Single API for speech-to-speech reduces latency (~300ms vs ~800ms for chained services), native function calling, consistent voice quality |
| **LLM** | GPT-4o | Claude 3, Gemini | Best balance of speed and capability, required for Realtime API, excellent function calling |
| **Database** | PostgreSQL | SQLite, MongoDB | ACID compliance for booking integrity, excellent query capabilities for availability matching, production-ready |
| **Backend** | FastAPI | Flask, Django | Native async support crucial for WebSocket handling, automatic OpenAPI docs, Pydantic integration |
| **Vision** | GPT-4 Vision | Google Vision, AWS Rekognition | Integrated with existing OpenAI infrastructure, excellent at contextual understanding vs. just object detection |

### 2.2 Key Architectural Patterns

#### Real-Time Voice Pipeline

```
Customer Phone → Twilio → WebSocket → Our Server → OpenAI Realtime API
                                ↑                          ↓
                                └──────── Audio ───────────┘
```

**Decision:** Use OpenAI's Realtime API for voice-to-voice conversation rather than chaining separate STT → LLM → TTS services.

**Rationale:**
- **Latency:** Single round-trip (~300ms) vs. three services (~800-1200ms)
- **Natural interruption handling:** Built-in voice activity detection
- **Consistent voice:** Same voice throughout conversation
- **Function calling:** Native tool use without breaking audio stream

**Tradeoff:** Requires OpenAI Realtime API access (newer feature), less flexibility in mixing providers.

#### Session Management

**Decision:** In-memory session storage with option for Redis in production.

**Rationale:**
- Simplifies development and testing
- Single-server deployment for assessment
- Easy migration to Redis for horizontal scaling
- Conversation state is transient (per-call)

**Tradeoff:** Sessions lost on server restart; acceptable for voice calls.

#### Database Schema Design

**Decision:** Normalized relational schema with separate tables for technicians, specialties, service areas, and time slots.

**Rationale:**
- **Flexibility:** Technicians can have multiple specialties and service areas
- **Query efficiency:** Fast lookups for availability matching
- **Data integrity:** Foreign keys ensure valid relationships
- **Scheduling accuracy:** Separate time slots prevent double-booking

---

## 3. System Components

### 3.1 Voice Agent (`app/voice/agent.py`)

The AI agent is designed with:

1. **Persona:** Friendly, professional "Alex" character
2. **Conversation flow:** Structured phases (greeting → identify → diagnose → schedule)
3. **Tools:** Function calling for database operations
4. **Memory:** Session state preserves context

**Key Design Decisions:**

- **One question at a time:** Optimized for voice comprehension
- **Acknowledgment before questions:** Natural conversation flow
- **Explicit confirmation:** All bookings confirmed verbally
- **Graceful fallbacks:** Unknown situations handled smoothly

### 3.2 Diagnostic Knowledge Base (`app/services/diagnostic_service.py`)

**Structure:**
```python
DIAGNOSTIC_KNOWLEDGE = {
    "appliance_type": {
        "common_symptoms": [...],
        "diagnostic_questions": [...],
        "troubleshooting": {
            "symptom": ["step1", "step2", ...]
        }
    }
}
```

**Rationale:** Static knowledge base rather than LLM-generated troubleshooting because:
- Consistent, verified repair advice
- No risk of hallucinated steps
- Faster response (no LLM call)
- Easier to update and maintain

### 3.3 Scheduling System

**Availability Matching Algorithm:**
```sql
SELECT slots, technicians
WHERE service_area.zip_code = customer_zip
  AND specialty.appliance_type = customer_appliance
  AND slot.is_available = true
  AND slot.date BETWEEN start AND end
ORDER BY date, start_time
```

**Design Decisions:**
- **2-hour appointment windows:** Industry standard, balances precision and flexibility
- **14-day lookahead:** Sufficient for most scheduling needs
- **Automatic slot blocking:** Prevents race conditions in booking
- **Confirmation numbers:** Human-readable format (SHS-XXXXXXXX)

### 3.4 Image Upload System

**Flow:**
1. Agent asks for email during call
2. System generates unique token, sends email
3. Customer uploads via mobile-friendly web page
4. GPT-4 Vision analyzes image
5. Analysis available for future calls or technician

**Security Considerations:**
- Time-limited tokens (24 hours)
- Single-use links
- File type validation
- Size limits

---

## 4. Tradeoffs and Considerations

### 4.1 Latency vs. Capability

**Choice:** Prioritize low latency with Realtime API

**Tradeoff:** Cannot use Claude or other providers for voice, but sub-second response time is critical for natural conversation.

### 4.2 Complexity vs. Maintainability

**Choice:** Modular service architecture

**Tradeoff:** More files and abstractions, but:
- Each component is testable in isolation
- Easy to swap implementations
- Clear separation of concerns

### 4.3 Cost vs. Features

**Choice:** Use OpenAI for all AI features

**Tradeoff:** Higher per-call cost than open-source alternatives, but:
- Significantly reduced development time
- Better quality responses
- Single vendor relationship

### 4.4 Stateful vs. Stateless

**Choice:** Stateful sessions with conversation memory

**Tradeoff:** More complex scaling, but:
- Natural conversation flow
- No repeated questions
- Better customer experience

---

## 5. Scalability Considerations

### Current Implementation (Single Server)
- Suitable for ~100 concurrent calls
- In-memory session storage
- Single PostgreSQL instance

### Production Scaling Path
1. **Redis for sessions:** Enable horizontal scaling
2. **Load balancer:** Distribute WebSocket connections
3. **Database replicas:** Read replicas for availability queries
4. **CDN:** Static assets and upload pages

---

## 6. Security Architecture

### Authentication
- Twilio webhook signature validation
- API key authentication for internal endpoints

### Data Protection
- HTTPS for all communications
- Environment variables for secrets
- No PII in logs

### Input Validation
- Pydantic schemas for all inputs
- File type and size validation
- SQL injection prevention via ORM

---

## 7. Testing Strategy

### Unit Tests
- Service layer logic
- Schema validation
- Tool execution

### Integration Tests
- Database operations
- API endpoints
- WebSocket connections

### End-to-End Tests
- Full call simulation (Twilio test credentials)
- Appointment booking flow
- Image upload flow

---

## 8. Deployment

### Development
```bash
docker-compose -f docker-compose.dev.yml up
ngrok http 8000
# Configure Twilio webhook
```

### Production
```bash
docker-compose up -d
# Configure DNS, SSL, monitoring
```

### Environment Requirements
- Docker & Docker Compose
- PostgreSQL 15+
- Redis (optional, for scaling)
- Twilio account with phone number
- OpenAI API access (including Realtime API)

---

## 9. Future Enhancements

1. **Multi-language support:** Leverage Realtime API's language capabilities
2. **Callback scheduling:** Allow customers to request callbacks
3. **Parts ordering:** Integrate with inventory system
4. **Sentiment analysis:** Detect frustrated customers for escalation
5. **Analytics dashboard:** Call metrics, common issues, resolution rates

---

## 10. Conclusion

This architecture balances practical engineering constraints with a high-quality user experience. The choice of OpenAI's Realtime API as the core voice technology enables natural, low-latency conversations while the modular backend design ensures maintainability and future scalability.

The system successfully implements all three tiers of requirements:
- **Tier 1:** Natural voice diagnosis with conversation memory
- **Tier 2:** Intelligent technician scheduling
- **Tier 3:** Image-based visual diagnosis

The codebase is production-ready with Docker deployment, comprehensive error handling, and clear documentation.
