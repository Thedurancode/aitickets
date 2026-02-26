"""Flyer Templates router for template-based flyer generation.

Provides endpoints for:
- Template CRUD operations
- Magic link generation for template upload/selection via SMS
- Template selection interface
- Flyer generation using templates
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Event, FlyerTemplate
from app.schemas import (
    FlyerTemplateCreate,
    FlyerTemplateUpdate,
    FlyerTemplateResponse,
    FlyerTemplateMagicLinkRequest,
    GenerateFlyerFromTemplateRequest,
)
from app.services.flyer_template import (
    generate_flyer_from_template,
    create_template_upload_token,
    get_templates_for_selection,
    validate_template_token,
    mark_token_used,
)
from app.config import get_settings

router = APIRouter(prefix="/api/flyer-templates", tags=["flyer-templates"])
settings = get_settings()


# ============== Template CRUD Endpoints ==============

@router.get("/", response_model=list[FlyerTemplateResponse])
def list_templates(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|times_used|name)$"),
    db: Session = Depends(get_db),
):
    """List all flyer templates with pagination and sorting."""
    query = db.query(FlyerTemplate)

    # Apply sorting
    if sort_by == "times_used":
        query = query.order_by(FlyerTemplate.times_used.desc())
    elif sort_by == "name":
        query = query.order_by(FlyerTemplate.name)
    else:  # created_at
        query = query.order_by(FlyerTemplate.created_at.desc())

    templates = query.offset(skip).limit(limit).all()
    return templates


@router.get("/featured", response_model=list[FlyerTemplateResponse])
def get_featured_templates(
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Get featured templates (most used)."""
    templates = (
        db.query(FlyerTemplate)
        .filter(FlyerTemplate.times_used > 0)
        .order_by(FlyerTemplate.times_used.desc())
        .limit(limit)
        .all()
    )
    return templates


@router.get("/{template_id}", response_model=FlyerTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a template by ID."""
    template = db.query(FlyerTemplate).filter(FlyerTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/", response_model=FlyerTemplateResponse, status_code=201)
def create_template(
    template: FlyerTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new flyer template."""
    db_template = FlyerTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.put("/{template_id}", response_model=FlyerTemplateResponse)
def update_template(
    template_id: int,
    template: FlyerTemplateUpdate,
    db: Session = Depends(get_db),
):
    """Update a template."""
    db_template = db.query(FlyerTemplate).filter(FlyerTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = template.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_template, field, value)

    db.commit()
    db.refresh(db_template)
    return db_template


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template."""
    db_template = db.query(FlyerTemplate).filter(FlyerTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(db_template)
    db.commit()
    return {"message": f"Template '{db_template.name}' deleted"}


# ============== Magic Link Endpoints ==============

class MagicLinkResponse(BaseModel):
    """Response for magic link creation."""
    success: bool
    token: str
    upload_url: str
    expires_at: str
    message: str


@router.post("/magic-link", response_model=MagicLinkResponse)
def send_magic_link(
    request_data: FlyerTemplateMagicLinkRequest,
    db: Session = Depends(get_db),
):
    """Send a magic link via SMS for template upload/selection.

    The user receives an SMS with a secure link to:
    1. Browse available templates
    2. Upload their own template
    3. Select a template for the event
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == request_data.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = create_template_upload_token(
        db=db,
        event_id=request_data.event_id,
        phone=request_data.phone,
        expires_hours=request_data.expires_hours,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


class TemplateSelectionResponse(BaseModel):
    """Response for template selection via magic link."""
    templates: list[dict]
    count: int
    event: Optional[dict] = None


@router.get("/select/{token}", response_model=TemplateSelectionResponse)
def get_templates_for_magic_link(
    token: str,
    event_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get templates available for selection via magic link.

    This endpoint is accessed from the SMS magic link.
    Returns all templates that can be used for flyer generation.
    """
    result = get_templates_for_selection(db, token)

    # If event_id provided, include event info
    if event_id:
        event = db.query(Event).filter(Event.id == event_id).first()
        if event:
            result["event"] = {
                "id": event.id,
                "name": event.name,
                "date": str(event.event_date) if event.event_date else None,
                "time": str(event.event_time) if event.event_time else None,
                "image_url": event.image_url,
            }

    return result


# ============== Flyer Generation Endpoints ==============

class FlyerGenerationResponse(BaseModel):
    """Response for flyer generation."""
    success: bool
    event_id: int
    event_name: str
    template_id: int
    template_name: str
    image_url: str
    message: str


@router.post("/generate", response_model=FlyerGenerationResponse)
def generate_flyer(
    request_data: GenerateFlyerFromTemplateRequest,
    event_id: int,
    db: Session = Depends(get_db),
):
    """Generate a flyer for an event using a template.

    The AI vision model analyzes the template to understand:
    - Layout and composition
    - Typography hierarchy
    - Color scheme
    - Visual elements

    Then generates a new flyer with event content matching that style.
    """
    result = generate_flyer_from_template(
        db=db,
        event_id=event_id,
        template_id=request_data.template_id,
        prompt_overrides=request_data.prompt_overrides,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/events/{event_id}/generate/{template_id}")
def generate_flyer_for_event(
    event_id: int,
    template_id: int,
    prompt_overrides: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Quick endpoint to generate flyer directly from URL path.

    Useful for magic link flow where user selects template.
    """
    result = generate_flyer_from_template(
        db=db,
        event_id=event_id,
        template_id=template_id,
        prompt_overrides=prompt_overrides,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# ============== Public HTML Pages ==============

@router.get("/select/{token}", response_class=HTMLResponse, include_in_schema=False)
async def template_selection_page(
    token: str,
    db: Session = Depends(get_db),
):
    """Public page for selecting flyer templates via SMS magic link.

    Shows available templates and current event image. No login required - token auth only.
    """
    # Validate token and get templates
    result = get_templates_for_selection(db, token)

    if "error" in result:
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
        <p class="text-gray-400 mb-6">This template selection link has expired or is invalid.</p>
        <p class="text-sm text-gray-500">Please request a new template selection link.</p>
    </div>
</body>
</html>""")

    event = result["event"]
    templates = result["templates"]
    settings = get_settings()
    org_color = settings.org_color or "#CE1141"

    # Build templates HTML
    templates_html = ""
    for t in templates:
        templates_html += f"""
        <div class="template-card bg-gray-800 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-white transition-all"
             data-template-id="{t['id']}"
             data-template-name="{t['name']}">
            <img src="{t['image_url']}" alt="{t['name']}" class="w-full h-48 object-cover">
            <div class="p-4">
                <h3 class="font-semibold mb-1">{t['name']}</h3>
                <p class="text-sm text-gray-400 mb-2">{t.get('description') or 'No description'}</p>
                <p class="text-xs text-gray-500">Used {t['times_used']} times</p>
            </div>
        </div>
        """

    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Choose Flyer Template | {event['name']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen py-8 px-4">
    <div class="max-w-4xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold mb-2">🎨 Choose a Flyer Template</h1>
            <p class="text-gray-400">{event['name']}</p>
            <p class="text-sm text-gray-500">{event.get('date') or 'Date TBD'} {event.get('time') or ''}</p>
        </div>

        <!-- Current Event Image -->
        <div class="mb-8">
            <h2 class="text-lg font-semibold mb-4">Current Event Image</h2>
            {f'<div class="bg-gray-800 rounded-lg overflow-hidden"><img src="{event['current_image_url']}" alt="Current event image" class="w-full h-auto"></div>' if event.get('current_image_url') else '<div class="bg-gray-800 rounded-lg p-8 text-center text-gray-500">No current image</div>'}
        </div>

        <!-- Templates Grid -->
        <div class="mb-8">
            <h2 class="text-lg font-semibold mb-4">Select a Template</h2>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-4" id="templates-grid">
                {templates_html}
            </div>
        </div>

        <!-- Selected Template & Generate Button -->
        <div id="generate-section" class="bg-gray-800 rounded-lg p-6 hidden">
            <h3 class="text-lg font-semibold mb-2">Selected: <span id="selected-name">None</span></h3>
            <p class="text-gray-400 mb-4">Click "Generate Flyer" to create a new event image using this template style.</p>
            <button id="generate-btn"
                    class="w-full py-3 rounded-lg font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    style="background-color: {org_color};">
                Generating... <span id="loading-spinner" class="inline-block animate-spin ml-2">⏳</span>
            </button>
        </div>

        <!-- Success Message -->
        <div id="success-message" class="hidden bg-green-900 border border-green-700 rounded-lg p-6 mt-6">
            <div class="text-center">
                <div class="text-4xl mb-4">🎉</div>
                <h3 class="text-xl font-bold mb-2">Flyer Generated!</h3>
                <p class="text-gray-300 mb-4">Your new event flyer is ready.</p>
                <img id="generated-image" src="" alt="Generated flyer" class="w-full rounded-lg mb-4">
                <a href="/events/{event['id']}" class="inline-block px-6 py-2 rounded-lg font-medium text-white" style="background-color: {org_color};">
                    View Event Page
                </a>
            </div>
        </div>

        <!-- Error Message -->
        <div id="error-message" class="hidden bg-red-900 border border-red-700 rounded-lg p-6 mt-6">
            <p class="text-center" id="error-text">Error generating flyer</p>
        </div>
    </div>

    <script>
        const token = "{token}";
        const eventId = {event['id']};
        const apiBase = "{settings.base_url.rstrip('/')}/api";
        let selectedTemplateId = null;
        let selectedTemplateName = null;

        // Template selection
        document.querySelectorAll('.template-card').forEach(card => {{
            card.addEventListener('click', () => {{
                // Remove previous selection
                document.querySelectorAll('.template-card').forEach(c => c.classList.remove('ring-2', 'ring-white'));

                // Add selection to clicked card
                card.classList.add('ring-2', 'ring-white');
                selectedTemplateId = parseInt(card.dataset.templateId);
                selectedTemplateName = card.dataset.templateName;

                // Show generate section
                document.getElementById('selected-name').textContent = selectedTemplateName;
                document.getElementById('generate-section').classList.remove('hidden');
            }});
        }});

        // Generate flyer
        document.getElementById('generate-btn').addEventListener('click', async () => {{
            if (!selectedTemplateId) return;

            const btn = document.getElementById('generate-btn');
            btn.disabled = true;
            btn.innerHTML = 'Generating... <span id="loading-spinner" class="inline-block animate-spin ml-2">⏳</span>';

            try {{
                const response = await fetch(`${{apiBase}}/flyer-templates/events/${{eventId}}/generate/${{selectedTemplateId}}`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                }});

                const data = await response.json();

                if (data.success) {{
                    // Show success
                    document.getElementById('generated-image').src = data.image_url;
                    document.getElementById('success-message').classList.remove('hidden');
                    document.getElementById('generate-section').classList.add('hidden');

                    // Scroll to success message
                    document.getElementById('success-message').scrollIntoView({{ behavior: 'smooth' }});
                }} else {{
                    throw new Error(data.error || 'Generation failed');
                }}
            }} catch (error) {{
                console.error('Error generating flyer:', error);
                document.getElementById('error-text').textContent = error.message || 'Failed to generate flyer. Please try again.';
                document.getElementById('error-message').classList.remove('hidden');
                btn.disabled = false;
                btn.textContent = 'Generate Flyer';
            }}
        }});
    </script>
</body>
</html>""")
