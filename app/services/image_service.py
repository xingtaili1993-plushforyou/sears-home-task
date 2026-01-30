"""Service for image upload and analysis."""

import secrets
import logging
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Customer, ImageUploadRequest

logger = logging.getLogger(__name__)

# Directory for storing uploaded images
UPLOAD_DIR = Path("uploads/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ImageService:
    """Service for managing image uploads and analysis."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_upload_request(
        self,
        customer_id: int,
        email: str,
        appliance_type: Optional[str] = None,
        issue_description: Optional[str] = None,
        call_sid: Optional[str] = None
    ) -> ImageUploadRequest:
        """
        Create a new image upload request with a unique token.
        
        Returns the upload request with the unique URL.
        """
        # Generate unique token
        token = secrets.token_urlsafe(32)
        
        # Set expiry time
        expires_at = datetime.utcnow() + timedelta(hours=settings.upload_url_expiry_hours)
        
        # Create the request record
        upload_request = ImageUploadRequest(
            customer_id=customer_id,
            upload_token=token,
            email_sent_to=email,
            email_sent_at=datetime.utcnow(),
            expires_at=expires_at,
            appliance_type=appliance_type,
            issue_description=issue_description,
            call_sid=call_sid
        )
        
        self.db.add(upload_request)
        self.db.commit()
        self.db.refresh(upload_request)
        
        return upload_request
    
    def get_upload_url(self, token: str) -> str:
        """Generate the full upload URL for a token."""
        return f"{settings.base_url}/upload/{token}"
    
    def get_upload_request_by_token(
        self, 
        token: str
    ) -> Optional[ImageUploadRequest]:
        """Get an upload request by its token."""
        return self.db.query(ImageUploadRequest).filter(
            ImageUploadRequest.upload_token == token
        ).first()
    
    def validate_upload_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an upload token.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        request = self.get_upload_request_by_token(token)
        
        if not request:
            return False, "Invalid upload link"
        
        if request.is_used:
            return False, "This upload link has already been used"
        
        if request.is_expired:
            return False, "This upload link has expired"
        
        return True, None
    
    async def save_uploaded_image(
        self,
        token: str,
        image_data: bytes,
        filename: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Save an uploaded image and mark the request as used.
        
        Returns:
            Tuple of (success, error_or_path)
        """
        # Validate the token
        is_valid, error = self.validate_upload_token(token)
        if not is_valid:
            return False, error
        
        request = self.get_upload_request_by_token(token)
        
        # Generate a unique filename
        ext = Path(filename).suffix or ".jpg"
        safe_filename = f"{token}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = UPLOAD_DIR / safe_filename
        
        try:
            # Save the file
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            # Update the request record
            request.is_used = True
            request.uploaded_at = datetime.utcnow()
            request.image_filename = safe_filename
            request.image_path = str(file_path)
            
            self.db.commit()
            
            logger.info(f"Image saved: {file_path}")
            return True, str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            return False, f"Error saving image: {str(e)}"
    
    async def analyze_image(
        self,
        token: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Analyze an uploaded image using GPT-4 Vision.
        
        Returns:
            Tuple of (success, analysis_or_error)
        """
        request = self.get_upload_request_by_token(token)
        
        if not request or not request.image_path:
            return False, "No image found for this upload"
        
        try:
            # Read the image
            with open(request.image_path, "rb") as f:
                image_data = f.read()
            
            # Encode as base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            
            # Determine the media type
            ext = Path(request.image_path).suffix.lower()
            media_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }
            media_type = media_types.get(ext, "image/jpeg")
            
            # Call GPT-4 Vision for analysis
            analysis = await self._call_vision_api(
                image_base64,
                media_type,
                request.appliance_type,
                request.issue_description
            )
            
            # Save the analysis
            request.image_analysis = analysis
            self.db.commit()
            
            return True, analysis
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return False, f"Error analyzing image: {str(e)}"
    
    async def _call_vision_api(
        self,
        image_base64: str,
        media_type: str,
        appliance_type: Optional[str],
        issue_description: Optional[str]
    ) -> str:
        """Call GPT-4 Vision API to analyze the appliance image."""
        
        import openai
        
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Build the context
        context = "You are an expert appliance technician analyzing an image."
        if appliance_type:
            context += f" The customer reports this is a {appliance_type}."
        if issue_description:
            context += f" The reported issue is: {issue_description}"
        
        prompt = f"""{context}

Please analyze this image and provide:
1. Confirmation of the appliance type (or identification if not provided)
2. Any visible issues, damage, or abnormalities
3. Specific observations that could help with diagnosis
4. Recommendations for the technician or customer

Be specific and technical where appropriate, but explain in terms a homeowner can understand."""
        
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Vision API error: {str(e)}")
            raise
