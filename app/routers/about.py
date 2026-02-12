"""API endpoints for managing the About Us page content."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AboutSection
from app.schemas import AboutSectionUpdate, TeamMemberAdd

router = APIRouter(prefix="/about", tags=["about"])

# Valid section keys
VALID_KEYS = {
    "hero_title", "hero_subtitle", "hero_image_url",
    "mission_title", "mission_content",
    "story_title", "story_content",
    "team_members",
    "contact_email", "contact_phone", "contact_address",
    "social_links",
}


def _get_all_sections(db: Session) -> dict:
    """Return all about sections as {key: content} dict."""
    rows = db.query(AboutSection).all()
    return {row.section_key: row.content for row in rows}


@router.get("")
def get_about(db: Session = Depends(get_db)):
    """Get all About Us page sections."""
    return _get_all_sections(db)


@router.put("/{section_key}")
def update_section(section_key: str, body: AboutSectionUpdate, db: Session = Depends(get_db)):
    """Update a single section of the About Us page."""
    if section_key not in VALID_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid section key: {section_key}")

    row = db.query(AboutSection).filter(AboutSection.section_key == section_key).first()
    if not row:
        row = AboutSection(section_key=section_key, content=body.content)
        db.add(row)
    else:
        row.content = body.content
    db.commit()
    db.refresh(row)
    return {"section_key": row.section_key, "content": row.content, "updated_at": str(row.updated_at)}


@router.post("/team-member")
def add_team_member(body: TeamMemberAdd, db: Session = Depends(get_db)):
    """Add a team member to the About Us page."""
    row = db.query(AboutSection).filter(AboutSection.section_key == "team_members").first()
    if not row:
        row = AboutSection(section_key="team_members", content="[]")
        db.add(row)
        db.flush()

    members = json.loads(row.content) if row.content else []
    member = {"name": body.name, "role": body.role}
    if body.bio:
        member["bio"] = body.bio
    if body.photo_url:
        member["photo_url"] = body.photo_url
    members.append(member)
    row.content = json.dumps(members)
    db.commit()
    return {"message": f"Added {body.name} ({body.role}) to team", "team_members": members}


@router.delete("/team-member/{name}")
def remove_team_member(name: str, db: Session = Depends(get_db)):
    """Remove a team member by name."""
    row = db.query(AboutSection).filter(AboutSection.section_key == "team_members").first()
    if not row or not row.content:
        raise HTTPException(status_code=404, detail="No team members found")

    members = json.loads(row.content)
    original_count = len(members)
    members = [m for m in members if m.get("name", "").lower() != name.lower()]

    if len(members) == original_count:
        raise HTTPException(status_code=404, detail=f"Team member '{name}' not found")

    row.content = json.dumps(members)
    db.commit()
    return {"message": f"Removed {name} from team", "team_members": members}
