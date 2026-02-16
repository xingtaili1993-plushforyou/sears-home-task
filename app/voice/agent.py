"""Voice AI Agent with conversation logic and tool calling."""

import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.database import get_db_context
from app.schemas.conversation import ConversationState
from app.services import CustomerService, DiagnosticService, ImageService, SchedulingService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# World-class system prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Samantha, a warm and highly skilled customer service agent for \
Sears Home Services. You help customers diagnose issues with their home appliances, guide \
them through troubleshooting, and schedule technician visits when needed.

## Your Personality
- Genuinely warm, patient, and empathetic — you sound like a trusted neighbor who happens \
  to be an appliance expert
- Professional yet conversational — never robotic or scripted
- Proactive — anticipate what the customer needs before they ask
- Reassuring — remind them that most issues are fixable and they called the right place
- Use natural speech patterns: "Got it", "I see", "That makes sense", "Great question"
- Use brief verbal affirmations: "Mmhmm", "Right", "Of course"

## Conversation Flow
1. **Greeting**: Warm welcome — use the customer's name if you know it
2. **Identify Appliance**: Determine which appliance is having issues
3. **Gather Symptoms**: Understand the problem — symptoms, when it started, error codes
4. **Diagnostic**: Ask targeted follow-up questions based on appliance + symptoms
5. **Troubleshooting**: Walk them through 2-3 quick steps that might fix it
6. **Scheduling**: If unresolved, offer to schedule a technician visit
7. **Image Capture**: Offer a photo upload link for better diagnosis
8. **Confirmation**: Summarize everything and confirm next steps
9. **Wrap-Up**: Offer to send a call summary email, thank them warmly

## Critical Guidelines

### Voice Conversation Best Practices
- Keep responses to 1-3 sentences — this is a phone call, not an essay
- Ask ONE question at a time
- Always acknowledge what the customer said before moving forward:
  "Got it — so the washer stops mid-cycle. Let me look into that."
- Summarize before taking action: "So just to confirm, you have a Samsung washer \
  that's about 5 years old and it stops during the spin cycle — is that right?"
- Use conversational transitions: "Let me check that for you...", \
  "Good news...", "Here's what I'd suggest..."
- When looking something up, tell them: "Bear with me one moment while I check that..."

### Frustration Detection & Empathy (CRITICAL)
- If the customer sounds frustrated, repeats themselves, or uses negative language, \
  ALWAYS acknowledge it first:
  "I can hear this has been really frustrating, and I'm sorry you're dealing with this. \
  Let's get this sorted out for you right now."
- If the customer has tried troubleshooting already, don't make them repeat steps. \
  Skip ahead to scheduling.
- After 2 failed troubleshooting steps, proactively offer to skip to scheduling: \
  "I think at this point, it would be best to have one of our expert technicians \
  take a look. Would you like me to find an available appointment?"
- If the customer has been on the call for a while without resolution, offer a human: \
  "I want to make sure we get you the best help possible. Would you like me to \
  connect you with a specialist who can dive deeper into this?"

### Human Escalation (THE MOST IMPORTANT RULE)
- The customer can ALWAYS reach a human. This is non-negotiable.
- If the customer says anything like "talk to a person", "real person", \
  "human agent", "speak to someone", "supervisor", "manager" — \
  IMMEDIATELY offer to transfer. No resistance. No convincing.
  Say: "Of course — let me connect you with a specialist right away. \
  I'll pass along everything we've discussed so you won't need to repeat yourself."
- For SAFETY issues (gas leak, burning smell, sparks, electrical fire, flooding): \
  Immediately say: "For your safety, I want to connect you with our emergency team \
  right away. Please step away from the appliance if you haven't already." \
  Then use transfer_to_human with urgency "emergency".
- Use the transfer_to_human tool to initiate the transfer.

### Collecting Email Addresses and Phone Numbers (IMPORTANT)
- Email addresses are very hard to get right over the phone. ALWAYS spell the \
  email back to the customer letter by letter to confirm: \
  "Just to make sure I have that right — that's X-I-N-G-T-A-I-L-I-1-9-9-3 \
  at gmail dot com, correct?"
- For phone numbers, read them back in groups: "That's 510-402-5551, right?"
- If the customer corrects you, repeat the corrected version to confirm.

### Closing the Call Well
- Before ending, ask: "Before we wrap up, would you like me to send you an email \
  summary of everything we discussed today? That way you'll have all the details \
  in one place."
- If they booked an appointment, confirm: "You'll also receive a text message \
  with your confirmation details."
- End warmly: "Thank you for calling Sears Home Services, [name]. \
  Is there anything else I can help you with today?"

## Tool Usage
- Explain what you're doing before calling a tool
- After getting results, present them conversationally — don't just read raw data
- For scheduling, present the top 2-3 options and ask which works best
"""


class VoiceAgent:
    """
    AI Agent for handling voice conversations about appliance diagnosis.

    Manages conversation logic, tool definitions, and generates
    appropriate responses based on the conversation state.
    """

    def __init__(self):
        self.diagnostic_service = DiagnosticService()

    def get_system_prompt(self, session: ConversationState) -> str:
        """Get the system prompt with current session context."""
        context_parts = [SYSTEM_PROMPT]

        # Add returning customer context
        if session.key_facts:
            context_parts.append("\n## Current Conversation Context")
            for fact in session.key_facts:
                context_parts.append(f"- {fact}")

        # Add diagnostic info if gathered
        diag = session.diagnostic
        if diag.appliance_type:
            context_parts.append(f"\nAppliance: {diag.appliance_type}")
        if diag.primary_symptom:
            context_parts.append(f"Main Issue: {diag.primary_symptom}")
        if diag.additional_symptoms:
            context_parts.append(
                f"Other Symptoms: {', '.join(diag.additional_symptoms)}"
            )

        # Add scheduling info if gathered
        sched = session.scheduling
        if sched.customer_zip_code:
            context_parts.append(f"Customer Zip Code: {sched.customer_zip_code}")
        if sched.customer_name:
            context_parts.append(f"Customer Name: {sched.customer_name}")

        return "\n".join(context_parts)

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tool definitions for the AI agent."""
        return [
            {
                "type": "function",
                "name": "get_troubleshooting_steps",
                "description": (
                    "Get troubleshooting steps for a specific appliance issue. "
                    "Use this to guide the customer through basic fixes before "
                    "scheduling a technician."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appliance_type": {
                            "type": "string",
                            "description": (
                                "The type of appliance (washer, dryer, "
                                "refrigerator, dishwasher, oven, hvac, etc.)"
                            ),
                        },
                        "symptom": {
                            "type": "string",
                            "description": (
                                "The main symptom or issue the customer "
                                "is experiencing"
                            ),
                        },
                    },
                    "required": ["appliance_type", "symptom"],
                },
            },
            {
                "type": "function",
                "name": "check_technician_availability",
                "description": (
                    "Check available appointment slots for a technician visit. "
                    "Use this when the customer needs to schedule a service call."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "zip_code": {
                            "type": "string",
                            "description": "The customer's 5-digit zip code",
                        },
                        "appliance_type": {
                            "type": "string",
                            "description": (
                                "The type of appliance that needs service"
                            ),
                        },
                        "preferred_time": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "any"],
                            "description": (
                                "Customer's preferred time of day for the "
                                "appointment"
                            ),
                        },
                    },
                    "required": ["zip_code", "appliance_type"],
                },
            },
            {
                "type": "function",
                "name": "book_appointment",
                "description": (
                    "Book a technician appointment. Only use this after "
                    "confirming the date and time with the customer."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot_id": {
                            "type": "integer",
                            "description": "The ID of the time slot to book",
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "The customer's full name",
                        },
                        "customer_zip_code": {
                            "type": "string",
                            "description": "The customer's zip code",
                        },
                        "appliance_type": {
                            "type": "string",
                            "description": "The type of appliance",
                        },
                        "issue_description": {
                            "type": "string",
                            "description": "Brief description of the issue",
                        },
                    },
                    "required": [
                        "slot_id",
                        "customer_name",
                        "appliance_type",
                        "issue_description",
                    ],
                },
            },
            {
                "type": "function",
                "name": "request_image_upload",
                "description": (
                    "Send the customer a link to upload a photo of their "
                    "appliance. Use this when a visual would help diagnose "
                    "the issue."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": (
                                "The customer's email address to send the "
                                "upload link"
                            ),
                        },
                        "appliance_type": {
                            "type": "string",
                            "description": (
                                "The type of appliance to photograph"
                            ),
                        },
                        "specific_area": {
                            "type": "string",
                            "description": (
                                "Specific area or part to photograph (optional)"
                            ),
                        },
                    },
                    "required": ["email"],
                },
            },
            {
                "type": "function",
                "name": "update_customer_info",
                "description": "Update the customer's information in the system.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Customer's name",
                        },
                        "email": {
                            "type": "string",
                            "description": "Customer's email address",
                        },
                        "zip_code": {
                            "type": "string",
                            "description": "Customer's zip code",
                        },
                        "address": {
                            "type": "string",
                            "description": "Customer's street address",
                        },
                    },
                },
            },
            # ---------- NEW TOOLS ----------
            {
                "type": "function",
                "name": "transfer_to_human",
                "description": (
                    "Transfer the customer to a live human agent. Use this "
                    "when the customer asks for a real person, expresses "
                    "repeated frustration, has a safety concern, or the issue "
                    "is beyond your diagnostic ability. Always pass along the "
                    "conversation context so they don't have to repeat themselves."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": (
                                "Why the customer is being transferred "
                                "(e.g., 'customer requested', 'safety concern', "
                                "'complex issue')"
                            ),
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["normal", "high", "emergency"],
                            "description": (
                                "Urgency level. Use 'emergency' for safety "
                                "issues like gas leaks or fire."
                            ),
                        },
                        "department": {
                            "type": "string",
                            "enum": [
                                "general_support",
                                "scheduling",
                                "technical",
                                "emergency",
                            ],
                            "description": "The department to transfer to.",
                        },
                        "summary": {
                            "type": "string",
                            "description": (
                                "Brief summary of the conversation so far "
                                "for the human agent."
                            ),
                        },
                    },
                    "required": ["reason", "urgency", "department", "summary"],
                },
            },
            {
                "type": "function",
                "name": "send_call_summary",
                "description": (
                    "Send the customer an email summary of the call including "
                    "what was discussed, troubleshooting steps tried, "
                    "appointment details, and next steps. Use this at the end "
                    "of the call when the customer agrees to receive a summary."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Customer's email address",
                        },
                        "summary_notes": {
                            "type": "string",
                            "description": (
                                "Key points to include in the summary"
                            ),
                        },
                    },
                    "required": ["email"],
                },
            },
            {
                "type": "function",
                "name": "send_sms_confirmation",
                "description": (
                    "Send an SMS text message to the customer's phone with "
                    "appointment confirmation details. Call this automatically "
                    "after booking an appointment."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {
                            "type": "string",
                            "description": "Customer's phone number",
                        },
                        "confirmation_number": {
                            "type": "string",
                            "description": "The appointment confirmation number",
                        },
                        "appointment_details": {
                            "type": "string",
                            "description": (
                                "Human-readable appointment details "
                                "(date, time, technician)"
                            ),
                        },
                    },
                    "required": [
                        "phone",
                        "confirmation_number",
                        "appointment_details",
                    ],
                },
            },
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session: ConversationState,
    ) -> str:
        """Execute a tool call and return the result."""
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "get_troubleshooting_steps":
                return await self._get_troubleshooting(
                    arguments["appliance_type"], arguments["symptom"]
                )

            elif tool_name == "check_technician_availability":
                return await self._check_availability(
                    arguments["zip_code"],
                    arguments["appliance_type"],
                    arguments.get("preferred_time", "any"),
                    session,
                )

            elif tool_name == "book_appointment":
                return await self._book_appointment(
                    arguments["slot_id"],
                    arguments["customer_name"],
                    arguments.get(
                        "customer_zip_code",
                        session.scheduling.customer_zip_code,
                    ),
                    arguments["appliance_type"],
                    arguments["issue_description"],
                    session,
                )

            elif tool_name == "request_image_upload":
                return await self._request_image(
                    arguments["email"],
                    arguments.get(
                        "appliance_type", session.diagnostic.appliance_type
                    ),
                    arguments.get("specific_area"),
                    session,
                )

            elif tool_name == "update_customer_info":
                return await self._update_customer(arguments, session)

            elif tool_name == "transfer_to_human":
                return await self._transfer_to_human(arguments, session)

            elif tool_name == "send_call_summary":
                return await self._send_call_summary(arguments, session)

            elif tool_name == "send_sms_confirmation":
                return await self._send_sms_confirmation(arguments, session)

            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return (
                "I encountered an issue while processing that. "
                "Let me try another approach."
            )

    # ------------------------------------------------------------------
    # Existing tool implementations
    # ------------------------------------------------------------------

    async def _get_troubleshooting(
        self, appliance_type: str, symptom: str
    ) -> str:
        """Get troubleshooting steps for an issue."""
        steps = self.diagnostic_service.get_troubleshooting_steps(
            appliance_type, symptom
        )
        if steps:
            formatted = "\n".join(f"- {step}" for step in steps[:5])
            return (
                f"Troubleshooting steps for {appliance_type} "
                f"with '{symptom}':\n{formatted}"
            )
        return (
            "I don't have specific troubleshooting steps for that issue, "
            "but general steps like checking power and resetting the "
            "appliance may help."
        )

    async def _check_availability(
        self,
        zip_code: str,
        appliance_type: str,
        preferred_time: str,
        session: ConversationState,
    ) -> str:
        """Check technician availability."""
        with get_db_context() as db:
            scheduling_service = SchedulingService(db)
            normalized = self.diagnostic_service.normalize_appliance_type(
                appliance_type
            )
            if not normalized:
                normalized = appliance_type.lower()

            slots = scheduling_service.get_available_slots(
                zip_code=zip_code,
                appliance_type=normalized,
                time_preference=(
                    preferred_time if preferred_time != "any" else None
                ),
            )
            if not slots:
                return (
                    f"I'm sorry, I couldn't find any available technicians "
                    f"for {appliance_type} service in the {zip_code} area. "
                    f"Would you like to try a different date range or check "
                    f"nearby zip codes?"
                )

            session.scheduling.customer_zip_code = zip_code

            descs = []
            for slot in slots[:5]:
                d = slot.date.strftime("%A, %B %d")
                s = slot.start_time.strftime("%I:%M %p").lstrip("0")
                e = slot.end_time.strftime("%I:%M %p").lstrip("0")
                descs.append(
                    f"Slot {slot.slot_id}: {d} from {s} to {e} "
                    f"with {slot.technician_name}"
                )
            return (
                f"Available appointments in {zip_code}:\n"
                + "\n".join(descs)
            )

    async def _book_appointment(
        self,
        slot_id: int,
        customer_name: str,
        customer_zip_code: str,
        appliance_type: str,
        issue_description: str,
        session: ConversationState,
    ) -> str:
        """Book an appointment."""
        with get_db_context() as db:
            scheduling_service = SchedulingService(db)
            customer_service = CustomerService(db)

            customer_id = session.customer_id
            if customer_id:
                parts = customer_name.split(None, 1)
                first_name = parts[0] if parts else customer_name
                last_name = parts[1] if len(parts) > 1 else ""
                customer_service.update_customer(
                    customer_id,
                    first_name=first_name,
                    last_name=last_name,
                    zip_code=customer_zip_code,
                )

            normalized = self.diagnostic_service.normalize_appliance_type(
                appliance_type
            )
            if not normalized:
                normalized = appliance_type.lower()

            appointment, error = scheduling_service.book_appointment(
                customer_id=customer_id,
                time_slot_id=slot_id,
                appliance_type=normalized,
                issue_description=issue_description,
                symptoms=session.diagnostic.primary_symptom,
                call_sid=session.call_sid,
            )
            if error:
                return (
                    f"I wasn't able to book that appointment: {error}. "
                    f"Let me check other available times."
                )

            session.appointment_id = appointment.id
            session.appointment_confirmation = appointment.confirmation_number

            details = scheduling_service.format_appointment_details(appointment)
            return (
                f"Appointment booked successfully!\n"
                f"Confirmation Number: {details['confirmation_number']}\n"
                f"Date: {details['date']}\n"
                f"Time: {details['time_window']}\n"
                f"Technician: {details['technician_name']}\n"
                f"Service: {details['appliance_type']} - "
                f"{details['issue_description']}"
            )

    async def _request_image(
        self,
        email: str,
        appliance_type: Optional[str],
        specific_area: Optional[str],
        session: ConversationState,
    ) -> str:
        """Request an image upload from the customer."""
        with get_db_context() as db:
            image_service = ImageService(db)
            upload_request = image_service.create_upload_request(
                customer_id=session.customer_id,
                email=email,
                appliance_type=appliance_type,
                issue_description=session.diagnostic.primary_symptom,
                call_sid=session.call_sid,
            )
            upload_url = image_service.get_upload_url(
                upload_request.upload_token
            )

            session.image_upload_requested = True
            session.image_upload_token = upload_request.upload_token
            session.scheduling.customer_email = email

        # Actually send the email (outside the db context)
        from app.services.email_service import EmailService

        email_service = EmailService()
        sent = await email_service.send_image_upload_link(
            to_email=email,
            upload_url=upload_url,
            customer_name=session.scheduling.customer_name,
            appliance_type=appliance_type,
        )

        if sent:
            msg = f"I've sent an email to {email} with a link to upload a photo"
        else:
            msg = (
                f"I tried to send an email to {email} but there was an "
                f"issue. The upload link is: {upload_url}"
            )

        if specific_area:
            msg += f" of the {specific_area}"
        elif appliance_type:
            msg += f" of your {appliance_type}"
        msg += ". The link will be valid for 24 hours."
        return msg

    async def _update_customer(
        self, updates: Dict[str, Any], session: ConversationState
    ) -> str:
        """Update customer information."""
        with get_db_context() as db:
            customer_service = CustomerService(db)
            if session.customer_id:
                kw: Dict[str, Any] = {}
                if "name" in updates:
                    parts = updates["name"].split(None, 1)
                    kw["first_name"] = parts[0] if parts else updates["name"]
                    kw["last_name"] = parts[1] if len(parts) > 1 else None
                    session.scheduling.customer_name = updates["name"]
                if "email" in updates:
                    kw["email"] = updates["email"]
                    session.scheduling.customer_email = updates["email"]
                if "zip_code" in updates:
                    kw["zip_code"] = updates["zip_code"]
                    session.scheduling.customer_zip_code = updates["zip_code"]
                if "address" in updates:
                    kw["address_line1"] = updates["address"]
                    session.scheduling.customer_address = updates["address"]
                customer_service.update_customer(session.customer_id, **kw)
            return "Customer information updated."

    # ------------------------------------------------------------------
    # NEW tool implementations
    # ------------------------------------------------------------------

    async def _transfer_to_human(
        self, arguments: Dict[str, Any], session: ConversationState
    ) -> str:
        """Transfer to a live human agent."""
        reason = arguments.get("reason", "customer request")
        urgency = arguments.get("urgency", "normal")
        department = arguments.get("department", "general_support")
        summary = arguments.get("summary", "")

        logger.info(
            f"TRANSFER REQUEST — reason={reason}, urgency={urgency}, "
            f"dept={department}, call_sid={session.call_sid}"
        )

        # Store transfer context on the session for the human agent
        session.add_fact(f"Transfer requested: {reason}")
        session.add_fact(f"Conversation summary for agent: {summary}")

        department_names = {
            "general_support": "General Support",
            "scheduling": "Scheduling",
            "technical": "Technical Support",
            "emergency": "Emergency Services",
        }
        dept_name = department_names.get(department, "General Support")

        if urgency == "emergency":
            return (
                f"EMERGENCY TRANSFER initiated to {dept_name}. "
                f"The customer should stay on the line. "
                f"Summary passed to agent: {summary}"
            )
        return (
            f"Transfer initiated to {dept_name}. "
            f"Estimated wait time: under 2 minutes. "
            f"Conversation summary has been passed to the next agent so "
            f"the customer won't need to repeat themselves."
        )

    async def _send_call_summary(
        self, arguments: Dict[str, Any], session: ConversationState
    ) -> str:
        """Send a post-call summary email."""
        email = arguments.get("email", session.scheduling.customer_email)
        notes = arguments.get("summary_notes", "")

        if not email:
            return "No email address available. Ask the customer for their email."

        from app.services.email_service import EmailService

        email_service = EmailService()
        success = await email_service.send_call_summary(
            to_email=email,
            customer_name=session.scheduling.customer_name or "Valued Customer",
            appliance_type=session.diagnostic.appliance_type,
            primary_symptom=session.diagnostic.primary_symptom,
            troubleshooting_steps=session.diagnostic.troubleshooting_steps_tried,
            appointment_confirmation=session.appointment_confirmation,
            key_facts=session.key_facts,
            summary_notes=notes,
        )

        if success:
            return f"Call summary email sent to {email} successfully."
        return "There was an issue sending the summary email, but the customer can call back for details."

    async def _send_sms_confirmation(
        self, arguments: Dict[str, Any], session: ConversationState
    ) -> str:
        """Send an SMS appointment confirmation."""
        phone = arguments.get("phone", session.customer_phone)
        conf_num = arguments.get("confirmation_number", "")
        details = arguments.get("appointment_details", "")

        from app.services.sms_service import SMSService

        sms_service = SMSService()
        success = await sms_service.send_appointment_confirmation(
            to_phone=phone,
            confirmation_number=conf_num,
            appointment_details=details,
        )

        if success:
            return f"SMS confirmation sent to {phone}."
        return "SMS could not be sent, but the customer has the confirmation number verbally."

    # ------------------------------------------------------------------
    # Initial greeting
    # ------------------------------------------------------------------

    def get_initial_message(self) -> str:
        """Get the initial greeting message."""
        return (
            "Thank you for calling Sears Home Services! "
            "This is Samantha. I'm here to help you with any appliance "
            "issues you might be experiencing. "
            "What can I help you with today?"
        )

    def get_returning_customer_greeting(
        self, customer_name: str, history_summary: str
    ) -> str:
        """Get a personalised greeting for a returning customer."""
        return (
            f"Welcome back to Sears Home Services, {customer_name}! "
            f"This is Samantha. {history_summary} "
            f"How can I help you today?"
        )
