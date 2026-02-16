"""Service for sending emails."""

import logging
from datetime import datetime
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending transactional emails."""

    def __init__(self):
        self.from_email = settings.sendgrid_from_email
        self.api_key = settings.sendgrid_api_key

    async def send_image_upload_link(
        self,
        to_email: str,
        upload_url: str,
        customer_name: Optional[str] = None,
        appliance_type: Optional[str] = None,
    ) -> bool:
        """
        Send an email with the image upload link.

        Returns True if sent successfully, False otherwise.
        """
        name = customer_name or "Valued Customer"
        appliance = appliance_type or "your appliance"

        subject = "Sears Home Services - Upload Photo of Your Appliance"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .button {{ 
                    display: inline-block; 
                    padding: 15px 30px; 
                    background-color: #0066cc; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ padding: 20px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Sears Home Services</h1>
                </div>
                <div class="content">
                    <p>Dear {name},</p>
                    
                    <p>Thank you for contacting Sears Home Services about {appliance}.</p>
                    
                    <p>To help us better diagnose the issue, please upload a photo of your appliance 
                    using the link below. A clear photo can help our technicians understand the 
                    problem before they arrive.</p>
                    
                    <p style="text-align: center;">
                        <a href="{upload_url}" class="button">Upload Photo</a>
                    </p>
                    
                    <p><strong>Tips for a helpful photo:</strong></p>
                    <ul>
                        <li>Take the photo in good lighting</li>
                        <li>Include any error codes or displays if visible</li>
                        <li>Show the area where the problem is occurring</li>
                        <li>If there's visible damage, include that in the photo</li>
                    </ul>
                    
                    <p>This link will expire in 24 hours. If you need a new link, please call us back.</p>
                    
                    <p>Thank you for choosing Sears Home Services!</p>
                </div>
                <div class="footer">
                    <p>This email was sent by Sears Home Services.</p>
                    <p>If you did not request this email, please disregard it.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Dear {name},
        
        Thank you for contacting Sears Home Services about {appliance}.
        
        To help us better diagnose the issue, please upload a photo of your appliance 
        using the link below:
        
        {upload_url}
        
        Tips for a helpful photo:
        - Take the photo in good lighting
        - Include any error codes or displays if visible
        - Show the area where the problem is occurring
        - If there's visible damage, include that in the photo
        
        This link will expire in 24 hours.
        
        Thank you for choosing Sears Home Services!
        """

        # If SendGrid API key is not configured, log and return
        if not self.api_key:
            logger.warning(
                f"SendGrid API key not configured. Would send email to {to_email} "
                f"with upload URL: {upload_url}"
            )
            # In development, we'll consider this a success
            return True

        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)

            message = Mail(
                from_email=Email(self.from_email, "Sears Home Services"),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content),
            )

            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(
                    f"Failed to send email: {response.status_code} - {response.body}"
                )
                return False

        except ImportError:
            logger.warning("SendGrid package not installed. Email not sent.")
            return True  # Return True in development
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False

    async def send_appointment_confirmation(
        self,
        to_email: str,
        customer_name: str,
        confirmation_number: str,
        appointment_date: str,
        appointment_time: str,
        technician_name: str,
        appliance_type: str,
        issue_description: str,
    ) -> bool:
        """Send appointment confirmation email."""

        subject = f"Appointment Confirmed - {confirmation_number}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .details {{ background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ padding: 20px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Appointment Confirmed</h1>
                </div>
                <div class="content">
                    <p>Dear {customer_name},</p>
                    
                    <p>Your service appointment has been confirmed!</p>
                    
                    <div class="details">
                        <p><strong>Confirmation Number:</strong> {confirmation_number}</p>
                        <p><strong>Date:</strong> {appointment_date}</p>
                        <p><strong>Time Window:</strong> {appointment_time}</p>
                        <p><strong>Technician:</strong> {technician_name}</p>
                        <p><strong>Appliance:</strong> {appliance_type}</p>
                        <p><strong>Issue:</strong> {issue_description}</p>
                    </div>
                    
                    <p><strong>What to expect:</strong></p>
                    <ul>
                        <li>Your technician will call when they're on their way</li>
                        <li>Please ensure access to the appliance</li>
                        <li>Have any warranty information available if applicable</li>
                    </ul>
                    
                    <p>Need to reschedule? Call us at 1-800-4-MY-HOME.</p>
                </div>
                <div class="footer">
                    <p>Sears Home Services - Trusted repairs since 1956</p>
                </div>
            </div>
        </body>
        </html>
        """

        if not self.api_key:
            logger.warning(f"Would send confirmation email to {to_email}")
            return True

        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)

            message = Mail(
                from_email=Email(self.from_email, "Sears Home Services"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            response = sg.send(message)
            return response.status_code in [200, 201, 202]

        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}")
            return False

    async def send_call_summary(
        self,
        to_email: str,
        customer_name: str = "Valued Customer",
        appliance_type: Optional[str] = None,
        primary_symptom: Optional[str] = None,
        troubleshooting_steps: Optional[List[str]] = None,
        appointment_confirmation: Optional[str] = None,
        key_facts: Optional[List[str]] = None,
        summary_notes: str = "",
    ) -> bool:
        """Send a post-call summary email to the customer."""
        appliance = appliance_type or "your appliance"
        symptom = primary_symptom or "the reported issue"
        now_str = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")

        # Build troubleshooting section
        ts_html = ""
        if troubleshooting_steps:
            steps_li = "".join(f"<li>{s}</li>" for s in troubleshooting_steps)
            ts_html = f"""
            <h3 style="color:#003366;">Troubleshooting Steps Discussed</h3>
            <ol>{steps_li}</ol>"""

        # Build appointment section
        appt_html = ""
        if appointment_confirmation:
            appt_html = f"""
            <div style="background:#e8f5e9;padding:15px;border-radius:5px;margin:15px 0;">
                <h3 style="color:#2e7d32;margin-top:0;">Appointment Booked</h3>
                <p><strong>Confirmation Number:</strong> {appointment_confirmation}</p>
                <p>Your technician will call when they are on their way. Please ensure
                access to the appliance and have warranty information ready if applicable.</p>
            </div>"""

        # Build key-facts section (filter out raw transcripts)
        facts_html = ""
        if key_facts:
            filtered = [f for f in key_facts if not f.startswith("User said:")]
            if filtered:
                facts_li = "".join(f"<li>{f}</li>" for f in filtered[:10])
                facts_html = f"""
                <h3 style="color:#003366;">Key Details</h3>
                <ul>{facts_li}</ul>"""

        notes_html = ""
        if summary_notes:
            notes_html = f"""
            <h3 style="color:#003366;">Additional Notes</h3>
            <p>{summary_notes}</p>"""

        subject = "Your Sears Home Services Call Summary"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Call Summary</h1>
                    <p style="margin:0;font-size:14px;">{now_str}</p>
                </div>
                <div class="content">
                    <p>Dear {customer_name},</p>
                    <p>Thank you for calling Sears Home Services. Here is a summary
                    of your call today regarding <strong>{appliance}</strong>
                    ({symptom}).</p>
                    {ts_html}
                    {appt_html}
                    {facts_html}
                    {notes_html}
                    <h3 style="color:#003366;">Need More Help?</h3>
                    <ul>
                        <li>Call us anytime at <strong>1-800-4-MY-HOME</strong></li>
                        <li>Visit <a href="https://www.searshomeservices.com">
                            searshomeservices.com</a></li>
                    </ul>
                    <p style="margin-top:20px;padding-top:15px;border-top:1px solid #ddd;
                       font-size:13px;color:#888;">
                        How was your experience? We'd love your feedback — simply reply
                        to this email.</p>
                </div>
                <div class="footer">
                    <p>Sears Home Services — Trusted repairs since 1956</p>
                </div>
            </div>
        </body>
        </html>
        """

        if not self.api_key:
            logger.warning(f"Would send call summary email to {to_email}")
            return True

        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            message = Mail(
                from_email=Email(self.from_email, "Sears Home Services"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )
            response = sg.send(message)
            if response.status_code in [200, 201, 202]:
                logger.info(f"Call summary email sent to {to_email}")
                return True
            logger.error(f"Call summary email failed: {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Error sending call summary email: {str(e)}")
            return False

    async def send_image_analysis(
        self,
        to_email: str,
        appliance_type: Optional[str] = None,
        analysis: str = "",
    ) -> bool:
        """Send the GPT-4 Vision analysis results to the customer."""
        appliance = appliance_type or "your appliance"
        subject = "Sears Home Services - Your Appliance Photo Analysis"

        # Convert newlines in analysis to <br> for HTML
        analysis_html = analysis.replace("\n", "<br>")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6;
                       color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto;
                             padding: 20px; }}
                .header {{ background-color: #003366; color: white;
                          padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .analysis {{ background: white; padding: 20px;
                            border-radius: 8px; margin: 15px 0;
                            border-left: 4px solid #0066cc; }}
                .footer {{ padding: 20px; font-size: 12px; color: #666;
                          text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Photo Analysis Results</h1>
                </div>
                <div class="content">
                    <p>Thank you for uploading a photo of {appliance}.
                    Our AI has analyzed the image. Here are the findings:</p>

                    <div class="analysis">
                        {analysis_html}
                    </div>

                    <p><strong>What happens next?</strong></p>
                    <ul>
                        <li>If you have a technician visit scheduled, they
                            will review this analysis before arriving.</li>
                        <li>If you need to schedule a visit, call us at
                            <strong>1-800-4-MY-HOME</strong>.</li>
                    </ul>

                    <p style="margin-top:20px;font-size:13px;color:#888;">
                    Note: This analysis is generated by AI and is meant to
                    assist our technicians. A professional inspection may
                    reveal additional findings.</p>
                </div>
                <div class="footer">
                    <p>Sears Home Services — Trusted repairs since 1956</p>
                </div>
            </div>
        </body>
        </html>
        """

        if not self.api_key:
            logger.warning(f"Would send image analysis email to {to_email}")
            return True

        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            message = Mail(
                from_email=Email(self.from_email, "Sears Home Services"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )
            response = sg.send(message)
            if response.status_code in [200, 201, 202]:
                logger.info(f"Image analysis email sent to {to_email}")
                return True
            logger.error(f"Image analysis email failed: {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Error sending image analysis email: {str(e)}")
            return False
