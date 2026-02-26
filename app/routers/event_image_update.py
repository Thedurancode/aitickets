"""
Event Image Update Router - Token-based image updates via SMS magic link
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import shutil

from app.database import get_db
from app.services.event_image_update import (
    generate_image_update_token,
    validate_token,
    update_event_image,
    get_token_info,
)
from app.config import get_settings


router = APIRouter(prefix="/api/event-image-update", tags=["event-image-update"])


# ============== Schemas ==============


class GenerateTokenRequest(BaseModel):
    """Request to generate an image update token."""
    event_id: int = Field(..., description="Event to update")
    phone: str = Field(..., description="Phone number to send SMS to")
    expires_hours: int = Field(24, ge=1, le=168, description="Token expiration in hours")


class UpdateImageRequest(BaseModel):
    """Request to update an event image."""
    token: str = Field(..., description="Image update token")
    image_url: str = Field(..., description="New image URL (uploaded to uploads/)")


# ============== API Endpoints ==============


@router.post("/generate-token")
async def generate_token(
    request: GenerateTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a token for event image update and send SMS with magic link.

    The SMS contains a link to a simple upload page where the promoter can
    upload a new image without logging in.
    """
    result = generate_image_update_token(
        db=db,
        event_id=request.event_id,
        phone=request.phone,
        expires_hours=request.expires_hours,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.post("/update")
async def update_image(
    request: UpdateImageRequest,
    db: Session = Depends(get_db)
):
    """Update an event's image URL using a valid token."""
    result = update_event_image(
        db=db,
        token=request.token,
        new_image_url=request.image_url,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.get("/validate/{token}")
async def validate(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate a token and return event information for the upload page.

    Used by the upload page to check if the token is valid and show current image.
    """
    result = get_token_info(db, token)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.post("/upload")
async def upload_image(
    token: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an image file and update the event image in one step.

    Validates the token, uploads the file to the uploads directory,
    and updates the event's image_url.
    """
    # Validate token first
    token_info = get_token_info(db, token)
    if "error" in token_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )

    # Upload file
    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    # Generate unique filename
    file_extension = Path(file.filename).suffix or ".png"
    unique_filename = f"event_{token_info['event']['id']}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = uploads_dir / unique_filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

    # Generate URL
    base_url = settings.base_url.rstrip("/")
    image_url = f"{base_url}/uploads/{unique_filename}"

    # Update event image
    result = update_event_image(
        db=db,
        token=token,
        new_image_url=image_url,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return {
        "success": True,
        "image_url": image_url,
        **result
    }


# ============== Public HTML Pages ==============


@router.get("/update-event-image/{token}", response_class=HTMLResponse)
async def image_update_page(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Public page for updating event images via SMS magic link.

    Shows current image and upload form. No login required - token auth only.
    """
    # Validate token and get event info
    token_info = get_token_info(db, token)

    if "error" in token_info:
        # Invalid/expired token page
        settings = get_settings()
        return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Expired | {settings.org_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex items-center justify-center px-4">
    <div class="text-center max-w-md">
        <div class="text-6xl mb-6">⚠️</div>
        <h1 class="text-2xl font-bold mb-4 text-red-400">Link Expired or Invalid</h1>
        <p class="text-gray-400 mb-6">This image update link has expired or is invalid.</p>
        <p class="text-sm text-gray-500">Please request a new image update link.</p>
    </div>
</body>
</html>""")

    event = token_info["event"]
    settings = get_settings()

    # Determine if there's a current image
    current_image = event.get("current_image_url")
    has_current_image = bool(current_image)

    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Update Event Image | {event['name']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen py-8 px-4">
    <div class="max-w-2xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold mb-2">📸 Update Event Image</h1>
            <p class="text-gray-400">{event['name']}</p>
            <p class="text-sm text-gray-500">{event['date']} at {event['time']}</p>
        </div>

        <!-- Current Image -->
        <div class="mb-8">
            <h2 class="text-lg font-semibold mb-4">Current Image</h2>
            {f'<div class="bg-gray-800 rounded-lg overflow-hidden"><img src="{current_image}" alt="Current event image" class="w-full h-auto"></div>' if has_current_image else '<div class="bg-gray-800 rounded-lg p-8 text-center text-gray-500">No current image</div>'}
        </div>

        <!-- Upload Form -->
        <div class="bg-gray-800 rounded-lg p-6">
            <h2 class="text-lg font-semibold mb-4">Upload New Image</h2>

            <form id="uploadForm" enctype="multipart/form-data" class="space-y-4">
                <input type="hidden" name="token" value="{token}">

                <!-- File Drop Zone -->
                <div id="dropZone" class="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-gray-500 transition-colors cursor-pointer">
                    <input type="file" id="fileInput" name="file" accept="image/*" class="hidden" required>
                    <div class="text-gray-400">
                        <svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                        </svg>
                        <p class="text-lg mb-2">Click to upload or drag and drop</p>
                        <p class="text-sm text-gray-500">PNG, JPG, GIF up to 10MB</p>
                    </div>
                    <p id="fileName" class="mt-2 text-sm text-green-400 hidden"></p>
                </div>

                <!-- Preview -->
                <div id="preview" class="hidden">
                    <img id="previewImage" src="" alt="Preview" class="w-full h-auto rounded-lg">
                </div>

                <!-- Upload Button -->
                <button type="submit" id="submitBtn" disabled class="w-full py-3 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed" style="background-color: {settings.org_color};">
                    <span id="btnText">Upload New Image</span>
                    <span id="btnLoading" class="hidden">Uploading...</span>
                </button>
            </form>

            <!-- Success Message -->
            <div id="successMsg" class="hidden mt-4 p-4 bg-green-900 border border-green-700 rounded-lg">
                <p class="text-green-300 font-medium">✅ Image updated successfully!</p>
                <p class="text-sm text-green-400 mt-1">The event image has been updated.</p>
            </div>

            <!-- Error Message -->
            <div id="errorMsg" class="hidden mt-4 p-4 bg-red-900 border border-red-700 rounded-lg">
                <p class="text-red-300 font-medium">❌ Upload failed</p>
                <p id="errorText" class="text-sm text-red-400 mt-1"></p>
            </div>
        </div>

        <!-- Info -->
        <div class="mt-6 text-center text-sm text-gray-500">
            <p>💡 Tip: Use a high-quality image (recommended 1200x630px for Facebook/Instagram ads)</p>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileName = document.getElementById('fileName');
        const preview = document.getElementById('preview');
        const previewImage = document.getElementById('previewImage');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const btnLoading = document.getElementById('btnLoading');
        const uploadForm = document.getElementById('uploadForm');
        const successMsg = document.getElementById('successMsg');
        const errorMsg = document.getElementById('errorMsg');
        const errorText = document.getElementById('errorText');

        // Click to upload
        dropZone.addEventListener('click', () => fileInput.click());

        // File selected
        fileInput.addEventListener('change', handleFileSelect);

        // Drag and drop
        dropZone.addEventListener('dragover', (e) => {{
            e.preventDefault();
            dropZone.classList.add('border-gray-400');
        }});

        dropZone.addEventListener('dragleave', () => {{
            dropZone.classList.remove('border-gray-400');
        }});

        dropZone.addEventListener('drop', (e) => {{
            e.preventDefault();
            dropZone.classList.remove('border-gray-400');
            if (e.dataTransfer.files.length) {{
                fileInput.files = e.dataTransfer.files;
                handleFileSelect();
            }}
        }});

        function handleFileSelect() {{
            const file = fileInput.files[0];
            if (file) {{
                fileName.textContent = 'Selected: ' + file.name;
                fileName.classList.remove('hidden');
                submitBtn.disabled = false;

                // Show preview
                const reader = new FileReader();
                reader.onload = (e) => {{
                    previewImage.src = e.target.result;
                    preview.classList.remove('hidden');
                }};
                reader.readAsDataURL(file);
            }}
        }}

        // Form submit
        uploadForm.addEventListener('submit', async (e) => {{
            e.preventDefault();

            btnText.classList.add('hidden');
            btnLoading.classList.remove('hidden');
            submitBtn.disabled = true;
            successMsg.classList.add('hidden');
            errorMsg.classList.add('hidden');

            const formData = new FormData();
            formData.append('token', '{token}');
            formData.append('file', fileInput.files[0]);

            try {{
                const response = await fetch('/api/event-image-update/upload', {{
                    method: 'POST',
                    body: formData
                }});

                const result = await response.json();

                if (result.success) {{
                    successMsg.classList.remove('hidden');
                    // Update current image display
                    location.reload();
                }} else {{
                    errorText.textContent = result.error || 'Upload failed';
                    errorMsg.classList.remove('hidden');
                    submitBtn.disabled = false;
                }}
            }} catch (err) {{
                errorText.textContent = 'Network error. Please try again.';
                errorMsg.classList.remove('hidden');
                submitBtn.disabled = false;
            }}

            btnText.classList.remove('hidden');
            btnLoading.classList.add('hidden');
        }});
    </script>
</body>
</html>""")
