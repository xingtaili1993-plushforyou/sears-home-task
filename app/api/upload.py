"""Routes for image upload functionality."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import ImageService, EmailService
from app.schemas import ImageUploadCreate, ImageUploadResponse
from app.config import settings

router = APIRouter()


@router.post("/image-upload-request", response_model=ImageUploadResponse)
async def create_image_upload_request(
    request_data: ImageUploadCreate,
    db: Session = Depends(get_db)
):
    """
    Create an image upload request and send email to customer.
    
    This is called by the voice agent when visual diagnosis would be helpful.
    """
    image_service = ImageService(db)
    email_service = EmailService()
    
    # Create the upload request
    upload_request = image_service.create_upload_request(
        customer_id=request_data.customer_id,
        email=request_data.email,
        appliance_type=request_data.appliance_type,
        issue_description=request_data.issue_description,
        call_sid=request_data.call_sid
    )
    
    # Generate the upload URL
    upload_url = image_service.get_upload_url(upload_request.upload_token)
    
    # Send the email
    email_sent = await email_service.send_image_upload_link(
        to_email=request_data.email,
        upload_url=upload_url,
        appliance_type=request_data.appliance_type
    )
    
    if not email_sent:
        # Log but don't fail - the URL is still valid
        pass
    
    return ImageUploadResponse(
        id=upload_request.id,
        upload_token=upload_request.upload_token,
        upload_url=upload_url,
        email_sent_to=upload_request.email_sent_to,
        expires_at=upload_request.expires_at,
        is_used=upload_request.is_used,
        image_analysis=upload_request.image_analysis
    )


@router.get("/upload/{token}", response_class=HTMLResponse)
async def upload_page(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Serve the image upload page.
    
    This is the page customers see when they click the email link.
    """
    image_service = ImageService(db)
    
    # Validate the token
    is_valid, error = image_service.validate_upload_token(token)
    
    if not is_valid:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Upload Error - Sears Home Services</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                    .error {{ color: #cc0000; background: #fff0f0; padding: 20px; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <h1>Sears Home Services</h1>
                <div class="error">
                    <h2>Upload Link Invalid</h2>
                    <p>{error}</p>
                    <p>Please contact us for a new upload link.</p>
                </div>
            </body>
            </html>
            """,
            status_code=400
        )
    
    # Return the upload form
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Upload Photo - Sears Home Services</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ box-sizing: border-box; }}
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 600px; 
                    margin: 0 auto; 
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #003366;
                    margin-bottom: 10px;
                }}
                .upload-area {{
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                    padding: 40px 20px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s;
                    margin-bottom: 20px;
                }}
                .upload-area:hover {{
                    border-color: #0066cc;
                    background: #f0f7ff;
                }}
                .upload-area.dragover {{
                    border-color: #0066cc;
                    background: #e6f2ff;
                }}
                .upload-area input {{
                    display: none;
                }}
                .upload-icon {{
                    font-size: 48px;
                    color: #666;
                }}
                .preview {{
                    display: none;
                    margin: 20px 0;
                    text-align: center;
                }}
                .preview img {{
                    max-width: 100%;
                    max-height: 300px;
                    border-radius: 8px;
                }}
                .submit-btn {{
                    width: 100%;
                    padding: 15px;
                    background: #0066cc;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.3s;
                }}
                .submit-btn:hover {{
                    background: #0055aa;
                }}
                .submit-btn:disabled {{
                    background: #ccc;
                    cursor: not-allowed;
                }}
                .tips {{
                    background: #f0f7ff;
                    padding: 15px;
                    border-radius: 8px;
                    margin-top: 20px;
                }}
                .tips h3 {{
                    margin-top: 0;
                    color: #003366;
                }}
                .tips ul {{
                    margin: 0;
                    padding-left: 20px;
                }}
                .success {{
                    display: none;
                    text-align: center;
                    padding: 40px;
                }}
                .success-icon {{
                    font-size: 64px;
                    color: #00aa00;
                }}
                .loading {{
                    display: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📷 Upload Appliance Photo</h1>
                    <p>Help us diagnose your appliance issue</p>
                </div>
                
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="upload-area" id="uploadArea">
                        <input type="file" id="fileInput" name="image" accept="image/*" capture="environment">
                        <div class="upload-icon">📁</div>
                        <p>Tap to take a photo or select from gallery</p>
                        <p style="color: #666; font-size: 14px;">Supports JPG, PNG, HEIC</p>
                    </div>
                    
                    <div class="preview" id="preview">
                        <img id="previewImage" src="" alt="Preview">
                        <p style="color: #666;">Looking good! Click upload when ready.</p>
                    </div>
                    
                    <button type="submit" class="submit-btn" id="submitBtn" disabled>
                        <span class="btn-text">Upload Photo</span>
                        <span class="loading">Uploading...</span>
                    </button>
                </form>
                
                <div class="tips">
                    <h3>📌 Tips for a helpful photo</h3>
                    <ul>
                        <li>Take the photo in good lighting</li>
                        <li>Include any error codes on the display</li>
                        <li>Show the area with the problem</li>
                        <li>Include any visible damage</li>
                    </ul>
                </div>
                
                <div class="success" id="successMessage">
                    <div class="success-icon">✅</div>
                    <h2>Photo Uploaded Successfully!</h2>
                    <p>Thank you! Our team will analyze your photo and use it to better diagnose the issue.</p>
                    <p style="color: #666;">You can close this page now.</p>
                </div>
            </div>
            
            <script>
                const uploadArea = document.getElementById('uploadArea');
                const fileInput = document.getElementById('fileInput');
                const preview = document.getElementById('preview');
                const previewImage = document.getElementById('previewImage');
                const submitBtn = document.getElementById('submitBtn');
                const uploadForm = document.getElementById('uploadForm');
                const successMessage = document.getElementById('successMessage');
                
                // Click to upload
                uploadArea.addEventListener('click', () => fileInput.click());
                
                // Drag and drop
                uploadArea.addEventListener('dragover', (e) => {{
                    e.preventDefault();
                    uploadArea.classList.add('dragover');
                }});
                
                uploadArea.addEventListener('dragleave', () => {{
                    uploadArea.classList.remove('dragover');
                }});
                
                uploadArea.addEventListener('drop', (e) => {{
                    e.preventDefault();
                    uploadArea.classList.remove('dragover');
                    const file = e.dataTransfer.files[0];
                    if (file && file.type.startsWith('image/')) {{
                        fileInput.files = e.dataTransfer.files;
                        showPreview(file);
                    }}
                }});
                
                // File selected
                fileInput.addEventListener('change', (e) => {{
                    const file = e.target.files[0];
                    if (file) {{
                        showPreview(file);
                    }}
                }});
                
                function showPreview(file) {{
                    const reader = new FileReader();
                    reader.onload = (e) => {{
                        previewImage.src = e.target.result;
                        preview.style.display = 'block';
                        uploadArea.style.display = 'none';
                        submitBtn.disabled = false;
                    }};
                    reader.readAsDataURL(file);
                }}
                
                // Form submit
                uploadForm.addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    
                    const file = fileInput.files[0];
                    if (!file) return;
                    
                    submitBtn.disabled = true;
                    submitBtn.querySelector('.btn-text').style.display = 'none';
                    submitBtn.querySelector('.loading').style.display = 'inline';
                    
                    const formData = new FormData();
                    formData.append('image', file);
                    
                    try {{
                        const response = await fetch('/upload/{token}/submit', {{
                            method: 'POST',
                            body: formData
                        }});
                        
                        if (response.ok) {{
                            uploadForm.style.display = 'none';
                            document.querySelector('.tips').style.display = 'none';
                            successMessage.style.display = 'block';
                        }} else {{
                            const error = await response.json();
                            alert('Upload failed: ' + (error.detail || 'Unknown error'));
                            submitBtn.disabled = false;
                            submitBtn.querySelector('.btn-text').style.display = 'inline';
                            submitBtn.querySelector('.loading').style.display = 'none';
                        }}
                    }} catch (error) {{
                        alert('Upload failed. Please try again.');
                        submitBtn.disabled = false;
                        submitBtn.querySelector('.btn-text').style.display = 'inline';
                        submitBtn.querySelector('.loading').style.display = 'none';
                    }}
                }});
            </script>
        </body>
        </html>
        """
    )


@router.post("/upload/{token}/submit")
async def submit_upload(
    token: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Handle the actual image upload submission.
    """
    image_service = ImageService(db)
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/heic"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Please upload a JPG, PNG, or HEIC image."
        )
    
    # Check file size
    max_size = settings.max_image_size_mb * 1024 * 1024
    content = await image.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_image_size_mb}MB."
        )
    
    # Save the image
    success, result = await image_service.save_uploaded_image(
        token=token,
        image_data=content,
        filename=image.filename or "upload.jpg"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    # Trigger image analysis in background
    try:
        await image_service.analyze_image(token)
    except Exception as e:
        # Log but don't fail the upload
        pass
    
    return {"message": "Upload successful", "path": result}


@router.get("/upload/{token}/analysis")
async def get_image_analysis(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get the analysis results for an uploaded image.
    """
    image_service = ImageService(db)
    upload_request = image_service.get_upload_request_by_token(token)
    
    if not upload_request:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    if not upload_request.image_analysis:
        # Try to analyze if not done yet
        if upload_request.image_path:
            success, analysis = await image_service.analyze_image(token)
            if success:
                return {"analysis": analysis}
        
        raise HTTPException(status_code=404, detail="No analysis available yet")
    
    return {"analysis": upload_request.image_analysis}
