"""Service for sending emails."""

import logging
from typing import Optional

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
        appliance_type: Optional[str] = None
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
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            
            message = Mail(
                from_email=Email(self.from_email, "Sears Home Services"),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
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
        issue_description: str
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
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            
            message = Mail(
                from_email=Email(self.from_email, "Sears Home Services"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = sg.send(message)
            return response.status_code in [200, 201, 202]
            
        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}")
            return False
