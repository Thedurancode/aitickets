"""
Event Auto-Onboarding Service

Automatically handles event lifecycle tasks:
- Run research agent and generate marketing plan
- Create event flyer with AI
- Launch Meta ad campaigns
- Set up email/SMS campaigns

Triggered automatically when events are created.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models import Event, MetaAdCampaign, MetaAdStatus, MetaAdObjective
from app.config import get_settings


async def auto_onboard_event(
    db: Session,
    event_id: int,
    skip_research: bool = False,
    skip_flyer: bool = False,
    skip_meta_ads: bool = False,
) -> Dict:
    """
    Automatically onboard a new event with full marketing automation.

    Steps:
    1. Run research agent and generate marketing plan
    2. Generate AI event flyer
    3. Create Meta ad campaigns based on marketing plan
    4. Set up email/SMS campaign schedules
    5. Configure dynamic pricing (if applicable)

    Args:
        db: Database session
        event_id: Event ID to onboard
        skip_research: Skip research agent (default False)
        skip_flyer: Skip flyer generation (default False)
        skip_meta_ads: Skip Meta ads creation (default False)

    Returns:
        Dict with onboarding results and next steps
    """
    settings = get_settings()
    results = {
        "event_id": event_id,
        "onboarding_started_at": datetime.utcnow().isoformat(),
        "steps_completed": [],
        "steps_failed": [],
        "warnings": [],
    }

    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    results["event_name"] = event.name

    # Step 1: Run Research Agent
    if not skip_research:
        try:
            from app.services.event_research_agent import run_event_research_agent

            research_report = await run_event_research_agent(
                db, event_id, include_ai_plan=True, include_artist_research=True
            )

            if "error" not in research_report:
                results["steps_completed"].append("research_agent")
                results["research_report"] = {
                    "completed": True,
                    "marketing_plan_generated": "marketing_plan" in research_report,
                    "artist_researched": "artist_research" in research_report,
                }

                # Update event description if enhanced version available
                if research_report.get("enhanced_description") and not event.description:
                    event.description = research_report["enhanced_description"]
                    db.commit()
                    results["description_enhanced"] = True

                # Cache artist info for reference
                if research_report.get("artist_research"):
                    artist_data = research_report["artist_research"]
                    results["artist_info"] = {
                        "name": artist_data.get("artist_name"),
                        "genre": artist_data.get("genre"),
                        "social_media": artist_data.get("social_media"),
                    }

                # Cache the research for other steps
                from app.routers.event_research import research_cache
                research_cache[event_id] = research_report
            else:
                results["steps_failed"].append({
                    "step": "research_agent",
                    "error": research_report["error"]
                })
                research_report = None

        except Exception as e:
            results["steps_failed"].append({
                "step": "research_agent",
                "error": str(e)
            })
            research_report = None
    else:
        research_report = None
        results["warnings"].append("Research agent skipped")

    # Step 2: Generate Event Flyer
    if not skip_flyer:
        try:
            flyer_result = await _generate_event_flyer(db, event_id, event)

            if flyer_result.get("success"):
                results["steps_completed"].append("flyer_generation")
                results["flyer"] = {
                    "image_url": flyer_result.get("image_url"),
                    "template_used": flyer_result.get("template_id"),
                }

                # Update event with flyer URL
                if flyer_result.get("image_url"):
                    event.image_url = flyer_result["image_url"]
                    db.commit()
            else:
                results["steps_failed"].append({
                    "step": "flyer_generation",
                    "error": flyer_result.get("error", "Unknown error")
                })

        except Exception as e:
            results["steps_failed"].append({
                "step": "flyer_generation",
                "error": str(e)
            })
    else:
        results["warnings"].append("Flyer generation skipped")

    # Step 3: Create Meta Ad Campaigns
    if not skip_meta_ads and research_report:
        try:
            marketing_plan = research_report.get("marketing_plan", {})
            ads_result = await _create_meta_ads_from_plan(
                db, event_id, event, marketing_plan, results.get("flyer", {}).get("image_url")
            )

            if ads_result.get("success"):
                results["steps_completed"].append("meta_ads_creation")
                results["meta_ads"] = {
                    "campaigns_created": ads_result.get("campaigns_created", 0),
                    "campaign_ids": ads_result.get("campaign_ids", []),
                    "budget_allocated": ads_result.get("total_budget_cents", 0),
                }
            else:
                results["steps_failed"].append({
                    "step": "meta_ads_creation",
                    "error": ads_result.get("error", "Unknown error")
                })

        except Exception as e:
            results["steps_failed"].append({
                "step": "meta_ads_creation",
                "error": str(e)
            })
    else:
        if skip_meta_ads:
            results["warnings"].append("Meta ads creation skipped")
        elif not research_report:
            results["warnings"].append("Meta ads skipped (no marketing plan)")

    # Step 4: Schedule Email/SMS Campaigns
    try:
        campaign_result = await _schedule_marketing_campaigns(db, event_id, event, research_report)

        if campaign_result.get("success"):
            results["steps_completed"].append("campaign_scheduling")
            results["campaigns"] = {
                "email_scheduled": campaign_result.get("email_scheduled", False),
                "sms_scheduled": campaign_result.get("sms_scheduled", False),
            }
    except Exception as e:
        results["warnings"].append(f"Campaign scheduling: {str(e)}")

    # Step 5: Configure Dynamic Pricing (if high-value event)
    try:
        pricing_result = await _configure_dynamic_pricing(db, event_id, research_report)

        if pricing_result.get("configured"):
            results["steps_completed"].append("dynamic_pricing_setup")
            results["dynamic_pricing"] = pricing_result
    except Exception as e:
        results["warnings"].append(f"Dynamic pricing setup: {str(e)}")

    # Summary
    results["onboarding_completed_at"] = datetime.utcnow().isoformat()
    results["success_rate"] = f"{len(results['steps_completed'])}/{len(results['steps_completed']) + len(results['steps_failed'])}"

    return results


async def _generate_event_flyer(db: Session, event_id: int, event: Event) -> Dict:
    """Generate AI flyer for event using templates."""
    try:
        from app.services.flyer_generation import generate_flyer_with_template
        from app.models import FlyerTemplate

        # Get a template (use first available, or most used)
        template = (
            db.query(FlyerTemplate)
            .order_by(FlyerTemplate.times_used.desc())
            .first()
        )

        if not template:
            return {
                "error": "No flyer templates available",
                "suggestion": "Upload templates via /api/flyer-templates"
            }

        # Generate flyer
        result = await generate_flyer_with_template(
            db=db,
            event_id=event_id,
            template_id=template.id,
            prompt_overrides=None,
        )

        return result

    except ImportError:
        return {
            "error": "Flyer generation service not available",
            "fallback": "Use manual flyer upload"
        }
    except Exception as e:
        return {"error": str(e)}


async def _create_meta_ads_from_plan(
    db: Session,
    event_id: int,
    event: Event,
    marketing_plan: Dict,
    flyer_url: Optional[str],
) -> Dict:
    """Create Meta ad campaigns based on marketing plan."""
    settings = get_settings()

    if not settings.meta_access_token:
        return {"error": "Meta access token not configured"}

    # Extract campaign details from marketing plan
    channel_strategy = marketing_plan.get("channel_strategy", {})
    meta_ads_config = channel_strategy.get("meta_ads", {})

    if not meta_ads_config or meta_ads_config.get("priority") == "LOW":
        return {"skipped": True, "reason": "Meta ads not prioritized in marketing plan"}

    # Calculate budget from plan
    budget_percent = meta_ads_config.get("budget_percent", 40)
    # Default total marketing budget: $500 for events
    total_marketing_budget_cents = 50000  # $500
    meta_budget_cents = int(total_marketing_budget_cents * budget_percent / 100)

    # Extract messaging from plan
    messaging = marketing_plan.get("key_messaging", {})
    headline = messaging.get("headline", f"Don't Miss {event.name}!")
    description = messaging.get("subheadline", f"{event.event_date} at {event.event_time}")
    primary_text = messaging.get("urgency_message", "Limited tickets available!")

    # Create campaign in database
    campaign = MetaAdCampaign(
        event_id=event_id,
        name=f"{event.name} - {event.event_date}",
        status=MetaAdStatus.DRAFT,
        objective=MetaAdObjective.TRAFFIC,
        budget_type="daily",
        budget_cents=meta_budget_cents // 14,  # Spread over 2 weeks
        targeting_radius_miles=10,
        age_min=21,
        age_max=55,
        genders="all",
        primary_text=primary_text,
        headline=headline,
        description=description,
        call_to_action="GET_TICKETS",
        image_url=flyer_url or event.image_url,
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "success": True,
        "campaigns_created": 1,
        "campaign_ids": [campaign.id],
        "total_budget_cents": meta_budget_cents,
        "daily_budget_cents": meta_budget_cents // 14,
        "note": "Campaign created as DRAFT. Activate via /api/meta-ads endpoints"
    }


async def _schedule_marketing_campaigns(
    db: Session,
    event_id: int,
    event: Event,
    research_report: Optional[Dict],
) -> Dict:
    """Schedule email/SMS campaigns based on timing strategy."""
    if not research_report:
        return {"success": False, "reason": "No marketing plan available"}

    from app.models import MarketingCampaign
    from datetime import datetime, timedelta

    marketing_plan = research_report.get("marketing_plan", {})
    timing = marketing_plan.get("timing_strategy", {})
    key_messaging = marketing_plan.get("key_messaging", {})

    campaigns_created = []

    # Parse event date to calculate send times
    try:
        event_datetime = datetime.strptime(f"{event.event_date} {event.event_time}", "%Y-%m-%d %H:%M")
        days_until = (event_datetime - datetime.now()).days

        # Create early bird campaign (2 weeks before or immediately if < 14 days)
        if days_until > 7:
            early_bird_date = event_datetime - timedelta(days=min(14, days_until - 7))
            early_campaign = MarketingCampaign(
                name=f"{event.name} - Early Bird Announcement",
                campaign_type="email",
                subject=key_messaging.get("headline", f"Don't Miss {event.name}!"),
                content=f"{key_messaging.get('value_proposition', '')} Get your tickets early!",
                target_event_id=event_id,
                target_all=True,
                scheduled_send_time=early_bird_date,
                status="scheduled",
            )
            db.add(early_campaign)
            campaigns_created.append("early_bird_email")

        # Create final push campaign (3-7 days before)
        if days_until > 3:
            final_push_date = event_datetime - timedelta(days=min(5, days_until - 1))
            final_campaign = MarketingCampaign(
                name=f"{event.name} - Final Push",
                campaign_type="email",
                subject=key_messaging.get("urgency_message", "Last Chance to Get Tickets!"),
                content=f"{key_messaging.get('emotional_hook', '')} Don't miss out - tickets are selling fast!",
                target_event_id=event_id,
                target_all=True,
                scheduled_send_time=final_push_date,
                status="scheduled",
            )
            db.add(final_campaign)
            campaigns_created.append("final_push_email")

        # Create SMS reminder (24-48 hours before if high priority)
        channel_strategy = marketing_plan.get("channel_strategy", {})
        sms_config = channel_strategy.get("sms", {})

        if sms_config.get("priority") in ["HIGH", "MEDIUM"] and days_until > 1:
            sms_date = event_datetime - timedelta(days=1)
            sms_campaign = MarketingCampaign(
                name=f"{event.name} - SMS Reminder",
                campaign_type="sms",
                subject="Event Reminder",
                content=f"Reminder: {event.name} tomorrow at {event.event_time}! See you there!",
                target_event_id=event_id,
                target_all=False,  # Only ticket holders
                scheduled_send_time=sms_date,
                status="scheduled",
            )
            db.add(sms_campaign)
            campaigns_created.append("reminder_sms")

        db.commit()

        return {
            "success": True,
            "campaigns_created": len(campaigns_created),
            "campaign_types": campaigns_created,
            "timing_strategy": timing,
            "note": f"Created {len(campaigns_created)} scheduled campaigns. View at /api/marketing-campaigns"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "note": "Failed to schedule campaigns"
        }


async def _configure_dynamic_pricing(
    db: Session,
    event_id: int,
    research_report: Optional[Dict],
) -> Dict:
    """Auto-configure dynamic pricing based on event analysis."""
    if not research_report:
        return {"configured": False, "reason": "No research data"}

    from app.services.dynamic_pricing import enable_dynamic_pricing
    from app.models import TicketTier

    event_context = research_report.get("event_context", {})
    pricing = event_context.get("pricing", {})

    # Only enable for higher-priced events (avg > $30)
    avg_price = pricing.get("avg_cents", 0)

    if avg_price < 3000:
        return {
            "configured": False,
            "reason": f"Average price ${avg_price/100:.2f} too low for dynamic pricing"
        }

    # Enable dynamic pricing for all tiers
    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    configured_tiers = []

    for tier in tiers:
        # Set 20% range (min 80%, max 150% of base)
        min_price = int(tier.price * 0.8)
        max_price = int(tier.price * 1.5)

        result = enable_dynamic_pricing(db, tier.id, min_price, max_price)

        if result.get("success"):
            configured_tiers.append({
                "tier_id": tier.id,
                "tier_name": tier.name,
                "base_price": tier.price,
                "min_price": min_price,
                "max_price": max_price,
            })

    return {
        "configured": True,
        "tiers_configured": len(configured_tiers),
        "tiers": configured_tiers,
    }


def get_onboarding_status(event_id: int) -> Dict:
    """
    Check if event has been onboarded and what steps completed.

    This would check various services to see what's been set up.
    """
    from app.routers.event_research import research_cache

    status = {
        "event_id": event_id,
        "research_completed": event_id in research_cache,
        "flyer_generated": False,  # Check if event.image_url exists
        "meta_ads_created": False,  # Check MetaAdCampaign table
        "campaigns_scheduled": False,  # Check MarketingCampaign table
        "dynamic_pricing_enabled": False,  # Check TicketTier.dynamic_pricing_enabled
    }

    return status
