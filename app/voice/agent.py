"""Voice AI Agent with conversation logic and tool calling."""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from app.config import settings
from app.schemas.conversation import ConversationState, ConversationPhase, DiagnosticInfo
from app.services import DiagnosticService, SchedulingService, CustomerService, ImageService
from app.database import get_db_context

logger = logging.getLogger(__name__)


# System prompt for the voice agent
SYSTEM_PROMPT = """You are a friendly and professional customer service agent for Sears Home Services. You help customers diagnose issues with their home appliances and schedule technician visits when needed.

## Your Personality
- Warm, patient, and empathetic
- Professional but conversational
- Clear and concise in your responses
- Proactive in offering help

## Conversation Flow
1. **Greeting**: Welcome the caller warmly and ask how you can help
2. **Identify Appliance**: Determine what appliance is having issues
3. **Gather Symptoms**: Understand what's wrong - symptoms, when it started, error codes
4. **Diagnostic**: Ask targeted questions based on the appliance and symptoms
5. **Troubleshooting**: Guide through basic troubleshooting steps
6. **Scheduling**: If unresolved, offer to schedule a technician visit
7. **Image Capture**: Optionally request a photo for better diagnosis
8. **Confirmation**: Summarize and confirm any scheduled appointments

## Important Guidelines
- Keep responses brief and natural for voice conversation (1-3 sentences typically)
- Ask ONE question at a time
- Acknowledge what the customer tells you before asking the next question
- Use the customer's name if provided
- Don't repeat information the customer has already given
- If the customer seems frustrated, acknowledge their frustration before helping
- Always confirm scheduling details before finalizing

## Tool Usage
You have access to tools to:
- Look up available appointment slots
- Book appointments
- Get troubleshooting steps for specific issues
- Request image uploads for visual diagnosis

Use these tools when appropriate, but always explain what you're doing in natural language.

## Example Phrases
- "I'd be happy to help you with that."
- "Let me look up some available times for a technician in your area."
- "Before I schedule a technician, let's try a couple of things that might fix this."
- "I understand how frustrating that must be."
- "Great news - I found an opening that works with your schedule."
"""


class VoiceAgent:
    """
    AI Agent for handling voice conversations about appliance diagnosis.
    
    This class manages the conversation logic, tool definitions, and
    generates appropriate responses based on the conversation state.
    """
    
    def __init__(self):
        self.diagnostic_service = DiagnosticService()
    
    def get_system_prompt(self, session: ConversationState) -> str:
        """Get the system prompt with current session context."""
        context_parts = [SYSTEM_PROMPT]
        
        # Add current conversation context
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
            context_parts.append(f"Other Symptoms: {', '.join(diag.additional_symptoms)}")
        
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
                "description": "Get troubleshooting steps for a specific appliance issue. Use this to guide the customer through basic fixes before scheduling a technician.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appliance_type": {
                            "type": "string",
                            "description": "The type of appliance (washer, dryer, refrigerator, dishwasher, oven, hvac, etc.)"
                        },
                        "symptom": {
                            "type": "string",
                            "description": "The main symptom or issue the customer is experiencing"
                        }
                    },
                    "required": ["appliance_type", "symptom"]
                }
            },
            {
                "type": "function",
                "name": "check_technician_availability",
                "description": "Check available appointment slots for a technician visit. Use this when the customer needs to schedule a service call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "zip_code": {
                            "type": "string",
                            "description": "The customer's 5-digit zip code"
                        },
                        "appliance_type": {
                            "type": "string",
                            "description": "The type of appliance that needs service"
                        },
                        "preferred_time": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "any"],
                            "description": "Customer's preferred time of day for the appointment"
                        }
                    },
                    "required": ["zip_code", "appliance_type"]
                }
            },
            {
                "type": "function",
                "name": "book_appointment",
                "description": "Book a technician appointment. Only use this after confirming the date and time with the customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot_id": {
                            "type": "integer",
                            "description": "The ID of the time slot to book"
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "The customer's full name"
                        },
                        "customer_zip_code": {
                            "type": "string",
                            "description": "The customer's zip code"
                        },
                        "appliance_type": {
                            "type": "string",
                            "description": "The type of appliance"
                        },
                        "issue_description": {
                            "type": "string",
                            "description": "Brief description of the issue"
                        }
                    },
                    "required": ["slot_id", "customer_name", "appliance_type", "issue_description"]
                }
            },
            {
                "type": "function",
                "name": "request_image_upload",
                "description": "Send the customer a link to upload a photo of their appliance. Use this when a visual would help diagnose the issue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The customer's email address to send the upload link"
                        },
                        "appliance_type": {
                            "type": "string",
                            "description": "The type of appliance to photograph"
                        },
                        "specific_area": {
                            "type": "string",
                            "description": "Specific area or part to photograph (optional)"
                        }
                    },
                    "required": ["email"]
                }
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
                            "description": "Customer's name"
                        },
                        "email": {
                            "type": "string",
                            "description": "Customer's email address"
                        },
                        "zip_code": {
                            "type": "string",
                            "description": "Customer's zip code"
                        },
                        "address": {
                            "type": "string",
                            "description": "Customer's street address"
                        }
                    }
                }
            }
        ]
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session: ConversationState
    ) -> str:
        """Execute a tool call and return the result."""
        
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        try:
            if tool_name == "get_troubleshooting_steps":
                return await self._get_troubleshooting(
                    arguments["appliance_type"],
                    arguments["symptom"]
                )
            
            elif tool_name == "check_technician_availability":
                return await self._check_availability(
                    arguments["zip_code"],
                    arguments["appliance_type"],
                    arguments.get("preferred_time", "any"),
                    session
                )
            
            elif tool_name == "book_appointment":
                return await self._book_appointment(
                    arguments["slot_id"],
                    arguments["customer_name"],
                    arguments.get("customer_zip_code", session.scheduling.customer_zip_code),
                    arguments["appliance_type"],
                    arguments["issue_description"],
                    session
                )
            
            elif tool_name == "request_image_upload":
                return await self._request_image(
                    arguments["email"],
                    arguments.get("appliance_type", session.diagnostic.appliance_type),
                    arguments.get("specific_area"),
                    session
                )
            
            elif tool_name == "update_customer_info":
                return await self._update_customer(arguments, session)
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return f"I encountered an issue while processing that. Let me try another approach."
    
    async def _get_troubleshooting(
        self,
        appliance_type: str,
        symptom: str
    ) -> str:
        """Get troubleshooting steps for an issue."""
        steps = self.diagnostic_service.get_troubleshooting_steps(
            appliance_type, symptom
        )
        
        if steps:
            formatted_steps = "\n".join(f"- {step}" for step in steps[:5])
            return f"Troubleshooting steps for {appliance_type} with '{symptom}':\n{formatted_steps}"
        else:
            return f"I don't have specific troubleshooting steps for that issue, but general steps like checking power and resetting the appliance may help."
    
    async def _check_availability(
        self,
        zip_code: str,
        appliance_type: str,
        preferred_time: str,
        session: ConversationState
    ) -> str:
        """Check technician availability."""
        with get_db_context() as db:
            scheduling_service = SchedulingService(db)
            
            # Normalize appliance type
            normalized_type = self.diagnostic_service.normalize_appliance_type(appliance_type)
            if not normalized_type:
                normalized_type = appliance_type.lower()
            
            slots = scheduling_service.get_available_slots(
                zip_code=zip_code,
                appliance_type=normalized_type,
                time_preference=preferred_time if preferred_time != "any" else None
            )
            
            if not slots:
                return f"I'm sorry, I couldn't find any available technicians for {appliance_type} service in the {zip_code} area. Would you like to try a different date range or check nearby zip codes?"
            
            # Store in session for booking
            session.scheduling.customer_zip_code = zip_code
            
            # Format the first few available slots
            slot_descriptions = []
            for i, slot in enumerate(slots[:5]):
                date_str = slot.date.strftime("%A, %B %d")
                start_str = slot.start_time.strftime("%I:%M %p").lstrip("0")
                end_str = slot.end_time.strftime("%I:%M %p").lstrip("0")
                slot_descriptions.append(
                    f"Slot {slot.slot_id}: {date_str} from {start_str} to {end_str} with {slot.technician_name}"
                )
            
            result = f"Available appointments in {zip_code}:\n" + "\n".join(slot_descriptions)
            return result
    
    async def _book_appointment(
        self,
        slot_id: int,
        customer_name: str,
        customer_zip_code: str,
        appliance_type: str,
        issue_description: str,
        session: ConversationState
    ) -> str:
        """Book an appointment."""
        with get_db_context() as db:
            scheduling_service = SchedulingService(db)
            customer_service = CustomerService(db)
            
            # Ensure we have a customer record
            customer_id = session.customer_id
            if customer_id:
                # Update customer with name
                parts = customer_name.split(None, 1)
                first_name = parts[0] if parts else customer_name
                last_name = parts[1] if len(parts) > 1 else ""
                
                customer_service.update_customer(
                    customer_id,
                    first_name=first_name,
                    last_name=last_name,
                    zip_code=customer_zip_code
                )
            
            # Normalize appliance type
            normalized_type = self.diagnostic_service.normalize_appliance_type(appliance_type)
            if not normalized_type:
                normalized_type = appliance_type.lower()
            
            # Book the appointment
            appointment, error = scheduling_service.book_appointment(
                customer_id=customer_id,
                time_slot_id=slot_id,
                appliance_type=normalized_type,
                issue_description=issue_description,
                symptoms=session.diagnostic.primary_symptom,
                call_sid=session.call_sid
            )
            
            if error:
                return f"I wasn't able to book that appointment: {error}. Let me check other available times."
            
            # Store in session
            session.appointment_id = appointment.id
            session.appointment_confirmation = appointment.confirmation_number
            
            # Get formatted details
            details = scheduling_service.format_appointment_details(appointment)
            
            return (
                f"Appointment booked successfully!\n"
                f"Confirmation Number: {details['confirmation_number']}\n"
                f"Date: {details['date']}\n"
                f"Time: {details['time_window']}\n"
                f"Technician: {details['technician_name']}\n"
                f"Service: {details['appliance_type']} - {details['issue_description']}"
            )
    
    async def _request_image(
        self,
        email: str,
        appliance_type: Optional[str],
        specific_area: Optional[str],
        session: ConversationState
    ) -> str:
        """Request an image upload from the customer."""
        with get_db_context() as db:
            image_service = ImageService(db)
            
            # Create upload request
            upload_request = image_service.create_upload_request(
                customer_id=session.customer_id,
                email=email,
                appliance_type=appliance_type,
                issue_description=session.diagnostic.primary_symptom,
                call_sid=session.call_sid
            )
            
            # Store in session
            session.image_upload_requested = True
            session.image_upload_token = upload_request.upload_token
            session.scheduling.customer_email = email
            
            instructions = f"I've sent an email to {email} with a link to upload a photo"
            if specific_area:
                instructions += f" of the {specific_area}"
            elif appliance_type:
                instructions += f" of your {appliance_type}"
            instructions += ". The link will be valid for 24 hours."
            
            return instructions
    
    async def _update_customer(
        self,
        updates: Dict[str, Any],
        session: ConversationState
    ) -> str:
        """Update customer information."""
        with get_db_context() as db:
            customer_service = CustomerService(db)
            
            if session.customer_id:
                # Parse name if provided
                update_kwargs = {}
                if "name" in updates:
                    parts = updates["name"].split(None, 1)
                    update_kwargs["first_name"] = parts[0] if parts else updates["name"]
                    update_kwargs["last_name"] = parts[1] if len(parts) > 1 else None
                    session.scheduling.customer_name = updates["name"]
                
                if "email" in updates:
                    update_kwargs["email"] = updates["email"]
                    session.scheduling.customer_email = updates["email"]
                
                if "zip_code" in updates:
                    update_kwargs["zip_code"] = updates["zip_code"]
                    session.scheduling.customer_zip_code = updates["zip_code"]
                
                if "address" in updates:
                    update_kwargs["address_line1"] = updates["address"]
                    session.scheduling.customer_address = updates["address"]
                
                customer_service.update_customer(session.customer_id, **update_kwargs)
            
            return "Customer information updated."
    
    def get_initial_message(self) -> str:
        """Get the initial greeting message."""
        return (
            "Thank you for calling Sears Home Services. "
            "My name is Alex, and I'm here to help you with any appliance issues you might be experiencing. "
            "What can I help you with today?"
        )
