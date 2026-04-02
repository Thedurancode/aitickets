"""
Auto-Generate Ad Campaigns from Research
Creates Meta Ads, Google Ads, Email, and Social Media campaigns
"""

import json
from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Event, AdCampaign, AdCreative


def get_all_artist_images(research_report: Dict) -> List[Dict]:
    """
    Get ALL available images from research.

    Returns list with metadata:
    - url: Image URL
    - source: 'spotify', 'youtube', 'wikipedia'
    - type: 'profile', 'album', 'thumbnail', 'photo'
    """
    images = []

    # Spotify images
    spotify = research_report.get('spotify_research', {})
    if spotify and not spotify.get('error'):
        if spotify.get('profile_image'):
            images.append({
                'url': spotify['profile_image'],
                'source': 'spotify',
                'type': 'profile',
                'resolution': '640x640',
                'priority': 1
            })

        for track in spotify.get('top_tracks', [])[:3]:
            if track.get('album_image'):
                images.append({
                    'url': track['album_image'],
                    'source': 'spotify',
                    'type': 'album',
                    'resolution': '640x640',
                    'priority': 3
                })

    # Wikipedia images
    wikipedia = research_report.get('wikipedia_research', {})
    if wikipedia and wikipedia.get('image_url'):
        images.append({
            'url': wikipedia['image_url'],
            'source': 'wikipedia',
            'type': 'photo',
            'resolution': 'varies',
            'priority': 2
        })

    # YouTube thumbnails
    youtube = research_report.get('youtube_research', {})
    if youtube and not youtube.get('error'):
        for video in youtube.get('top_videos', [])[:3]:
            if video.get('thumbnail'):
                images.append({
                    'url': video['thumbnail'],
                    'source': 'youtube',
                    'type': 'thumbnail',
                    'resolution': '1280x720',
                    'priority': 4
                })

    # Sort by priority
    images.sort(key=lambda x: x['priority'])

    return images


def get_best_artist_image(research_report: Dict) -> str:
    """
    Automatically select best artist image.
    Priority: Spotify > Wikipedia > YouTube > Album
    """
    images = get_all_artist_images(research_report)
    return images[0]['url'] if images else None


def generate_meta_awareness_campaign(
    event: Event,
    research_report: Dict,
    budget: int = 50000
) -> tuple[AdCampaign, List[AdCreative]]:
    """
    Generate Meta Ads Awareness Campaign
    Focus: Reach new audiences, introduce artist
    """

    artist_research = research_report.get('artist_research', {})
    marketing_plan = research_report.get('marketing_plan', {})
    images = get_all_artist_images(research_report)

    artist_name = artist_research.get('name', event.name.split('-')[0].strip())
    genre = artist_research.get('genre', 'music')
    target_audience = marketing_plan.get('target_audience', {})

    # Create campaign
    campaign = AdCampaign(
        event_id=event.id,
        platform="meta",
        campaign_type="awareness",
        name=f"{artist_name} - Awareness Campaign",
        objective="REACH",
        budget_total=budget,
        budget_daily=int(budget / 45),  # ~45 days before event
        status="draft",
        start_date=event.event_date - timedelta(days=45),
        end_date=event.event_date,
        settings=json.dumps({
            "optimization_goal": "REACH",
            "billing_event": "IMPRESSIONS"
        })
    )

    ad_creatives = []

    # Get audience data
    age_range = target_audience.get('age_range', {})
    age_min = age_range.get('min', 18) if isinstance(age_range, dict) else 18
    age_max = age_range.get('max', 65) if isinstance(age_range, dict) else 65

    primary_audience = target_audience.get('primary', '') if isinstance(target_audience, dict) else str(target_audience)

    # Ad 1: Spanish headline + Spotify profile image
    if images:
        ad_creatives.append(AdCreative(
            platform="facebook",
            format="image",
            name=f"{artist_name} - Spanish Awareness 1",
            headline=f"¡{artist_name} Live! 🔥",
            body=f"El {artist_research.get('genre_label', 'artista')} viene el {event.event_date.strftime('%B %d')}. ¡No te lo pierdas! Boletos ya disponibles.",
            cta="Learn More",
            image_url=images[0]['url'],
            link_url=f"https://ai-tickets.com/events/{event.id}",
            target_audience=json.dumps({
                "age_min": age_min,
                "age_max": age_max,
                "genders": ["all"],
                "locations": [{"type": "city", "radius": 25}],
                "languages": ["Spanish", "English"],
                "interests": [artist_name, genre, "Concerts", "Live Music"]
            }),
            placements=json.dumps(["facebook_feed", "instagram_feed"]),
            status="draft"
        ))

    # Ad 2: English headline + album artwork
    if len(images) > 1:
        ad_creatives.append(AdCreative(
            platform="instagram",
            format="image",
            name=f"{artist_name} - English Awareness 2",
            headline=f"{artist_name} - Live in Concert!",
            body=f"Experience {artist_name} live on {event.event_date.strftime('%B %d')}! Get your tickets now for an unforgettable night!",
            cta="See Event",
            image_url=images[1]['url'],
            link_url=f"https://ai-tickets.com/events/{event.id}",
            target_audience=json.dumps({
                "age_min": age_min,
                "age_max": age_max,
                "genders": ["all"],
                "locations": [{"type": "city", "radius": 25}],
                "languages": ["English"],
                "interests": [artist_name, genre, "Live Events"]
            }),
            placements=json.dumps(["instagram_feed", "instagram_stories"]),
            status="draft"
        ))

    # Ad 3: Event details + venue info
    ad_creatives.append(AdCreative(
        platform="facebook",
        format="image",
        name=f"{artist_name} - Event Details",
        headline=f"🎵 {artist_name} at {event.venue.name if event.venue else 'venue'}",
        body=f"{event.event_date.strftime('%B %d, %Y')} • {event.event_time}\n\nDoors open: {event.doors_open_time}\nLocation: {event.venue.name if event.venue else 'TBA'}\n\nDon't miss this incredible show! Limited tickets available.",
        cta="Buy Tickets",
        image_url=images[0]['url'] if images else None,
        link_url=f"https://ai-tickets.com/events/{event.id}",
        target_audience=json.dumps({
            "age_min": age_min,
            "age_max": age_max,
            "genders": ["all"],
            "locations": [{"type": "city", "radius": 30}],
            "interests": [artist_name, "Concert Tickets", "Live Entertainment"]
        }),
        placements=json.dumps(["facebook_feed", "instagram_feed"]),
        status="draft"
    ))

    return campaign, ad_creatives


def generate_meta_conversion_campaign(
    event: Event,
    research_report: Dict,
    budget: int = 80000
) -> tuple[AdCampaign, List[AdCreative]]:
    """
    Generate Meta Ads Conversion Campaign
    Focus: Direct ticket sales
    """

    artist_research = research_report.get('artist_research', {})
    marketing_plan = research_report.get('marketing_plan', {})
    images = get_all_artist_images(research_report)

    artist_name = artist_research.get('name', event.name.split('-')[0].strip())

    campaign = AdCampaign(
        event_id=event.id,
        platform="meta",
        campaign_type="conversion",
        name=f"{artist_name} - Ticket Sales Campaign",
        objective="CONVERSIONS",
        budget_total=budget,
        budget_daily=int(budget / 25),  # Last 25 days
        status="draft",
        start_date=event.event_date - timedelta(days=25),
        end_date=event.event_date - timedelta(days=1),
        settings=json.dumps({
            "optimization_goal": "CONVERSIONS",
            "billing_event": "IMPRESSIONS",
            "conversion_event": "Purchase"
        })
    )

    ad_creatives = []

    # Ad 1: Urgency messaging
    ad_creatives.append(AdCreative(
        platform="facebook",
        format="image",
        name=f"{artist_name} - Limited Tickets",
        headline=f"⏰ Limited Tickets! {artist_name} - {event.event_date.strftime('%b %d')}",
        body=f"VIP packages selling out fast! Don't miss {artist_name} live. Secure your tickets now before it's too late! 🎟️",
        cta="Buy Tickets",
        image_url=images[0]['url'] if images else None,
        link_url=f"https://ai-tickets.com/events/{event.id}",
        target_audience=json.dumps({
            "age_min": 21,
            "age_max": 45,
            "interests": [artist_name, "Concert Tickets", "Live Music Events"],
            "behaviors": ["Engaged Shoppers", "Frequent Event Goers"]
        }),
        placements=json.dumps(["facebook_feed", "instagram_feed", "instagram_stories"]),
        status="draft"
    ))

    # Ad 2: Social proof
    ad_creatives.append(AdCreative(
        platform="instagram",
        format="image",
        name=f"{artist_name} - Social Proof",
        headline=f"Join Thousands! {artist_name} Live 🎤",
        body=f"Thousands of fans already have their tickets. Be part of the biggest event of the year! Get your tickets now!",
        cta="Get Tickets",
        image_url=images[1]['url'] if len(images) > 1 else (images[0]['url'] if images else None),
        link_url=f"https://ai-tickets.com/events/{event.id}",
        target_audience=json.dumps({
            "age_min": 18,
            "age_max": 40,
            "interests": [artist_name, "Live Concerts"],
            "behaviors": ["Engaged Shoppers"]
        }),
        placements=json.dumps(["instagram_feed", "instagram_stories", "facebook_feed"]),
        status="draft"
    ))

    return campaign, ad_creatives


def generate_google_search_campaign(
    event: Event,
    research_report: Dict,
    budget: int = 60000
) -> tuple[AdCampaign, List[AdCreative]]:
    """
    Generate Google Search Ads Campaign
    """

    artist_research = research_report.get('artist_research', {})
    artist_name = artist_research.get('name', event.name.split('-')[0].strip())
    genre = artist_research.get('genre', 'music')
    venue_city = event.venue.address.split(',')[-2].strip() if event.venue and event.venue.address else "city"

    campaign = AdCampaign(
        event_id=event.id,
        platform="google",
        campaign_type="search",
        name=f"{artist_name} - Search Campaign",
        objective="CONVERSIONS",
        budget_total=budget,
        budget_daily=int(budget / 30),
        status="draft",
        start_date=event.event_date - timedelta(days=30),
        end_date=event.event_date,
        settings=json.dumps({
            "campaign_type": "SEARCH",
            "bidding_strategy": "TARGET_CPA"
        })
    )

    ad_creatives = []

    # Search Ad 1: Brand keywords
    ad_creatives.append(AdCreative(
        platform="google_search",
        format="text",
        name=f"{artist_name} - Brand Search",
        headline=f"{artist_name} Tickets {venue_city}",
        body=f"Official Tickets For {artist_name}. {event.event_date.strftime('%B %d')} at {event.venue.name if event.venue else 'venue'}. VIP Packages Available. Buy Now!",
        cta="Buy Tickets",
        link_url=f"https://ai-tickets.com/events/{event.id}",
        target_audience=json.dumps({
            "keywords": [
                f"{artist_name.lower()} tickets",
                f"{artist_name.lower()} concert {venue_city.lower()}",
                f"{artist_name.lower()} tour {event.event_date.year}"
            ],
            "match_type": "EXACT"
        }),
        status="draft"
    ))

    # Search Ad 2: Genre keywords
    ad_creatives.append(AdCreative(
        platform="google_search",
        format="text",
        name=f"{genre} Concert Search",
        headline=f"{genre.title()} Concert - {artist_name}",
        body=f"See {artist_name} Live! Best {genre} concert this year. {event.event_date.strftime('%B %d')}. Limited tickets available. Book now!",
        cta="Get Tickets",
        link_url=f"https://ai-tickets.com/events/{event.id}",
        target_audience=json.dumps({
            "keywords": [
                f"{genre.lower()} concert {venue_city.lower()}",
                f"{genre.lower()} concert tickets",
                f"live {genre.lower()} music"
            ],
            "match_type": "PHRASE"
        }),
        status="draft"
    ))

    return campaign, ad_creatives


def generate_email_campaign(
    event: Event,
    research_report: Dict
) -> tuple[AdCampaign, List[AdCreative]]:
    """
    Generate Email Campaign Series
    """

    artist_research = research_report.get('artist_research', {})
    artist_name = artist_research.get('name', event.name.split('-')[0].strip())

    campaign = AdCampaign(
        event_id=event.id,
        platform="email",
        campaign_type="nurture",
        name=f"{artist_name} - Email Series",
        objective="ENGAGEMENT",
        budget_total=0,  # Owned channel
        status="draft",
        start_date=event.event_date - timedelta(days=30),
        end_date=event.event_date,
    )

    ad_creatives = []

    # Email 1: Announcement
    ad_creatives.append(AdCreative(
        platform="email",
        format="html",
        name=f"{artist_name} - Announcement Email",
        headline=f"🔥 {artist_name} is Coming! - {event.event_date.strftime('%B %d')}",
        body=f"""
        <h1>Don't Miss {artist_name} Live!</h1>
        <p>We're excited to announce {artist_name} will be performing on {event.event_date.strftime('%B %d, %Y')} at {event.venue.name if event.venue else 'our venue'}!</p>
        <p>Get your tickets now before they sell out!</p>
        <a href="https://ai-tickets.com/events/{event.id}" style="background: #ff4500; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Get Tickets Now</a>
        """,
        cta="Get Tickets Now",
        link_url=f"https://ai-tickets.com/events/{event.id}",
        status="draft"
    ))

    # Email 2: Last Chance
    ad_creatives.append(AdCreative(
        platform="email",
        format="html",
        name=f"{artist_name} - Last Chance Email",
        headline=f"⏰ LAST CHANCE: {artist_name} - 2 Days Away!",
        body=f"""
        <h1>Final Tickets Available!</h1>
        <p>{artist_name} performs in just 2 days on {event.event_date.strftime('%B %d')}!</p>
        <p>This is your last chance to secure tickets. Don't miss out on this incredible show!</p>
        <a href="https://ai-tickets.com/events/{event.id}" style="background: #ff4500; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Get Final Tickets</a>
        """,
        cta="Get Final Tickets",
        link_url=f"https://ai-tickets.com/events/{event.id}",
        status="draft"
    ))

    return campaign, ad_creatives


def generate_all_campaigns(
    db: Session,
    event_id: int,
    research_report: Dict
) -> Dict:
    """
    Generate ALL ad campaigns for an event
    Returns summary of created campaigns
    """

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found")

    all_campaigns = []
    all_ads = []

    # 1. Meta Awareness
    campaign, ads = generate_meta_awareness_campaign(event, research_report, budget=50000)
    all_campaigns.append(campaign)
    all_ads.extend(ads)

    # 2. Meta Conversion
    campaign, ads = generate_meta_conversion_campaign(event, research_report, budget=80000)
    all_campaigns.append(campaign)
    all_ads.extend(ads)

    # 3. Google Search
    campaign, ads = generate_google_search_campaign(event, research_report, budget=60000)
    all_campaigns.append(campaign)
    all_ads.extend(ads)

    # 4. Email
    campaign, ads = generate_email_campaign(event, research_report)
    all_campaigns.append(campaign)
    all_ads.extend(ads)

    # Save to database
    for campaign in all_campaigns:
        db.add(campaign)

    db.commit()

    # Refresh to get IDs
    for campaign in all_campaigns:
        db.refresh(campaign)

    # Link ads to campaigns and save
    idx = 0
    for campaign in all_campaigns:
        campaign_ad_count = len([a for a in all_ads[idx:] if True])
        if campaign.campaign_type == "awareness":
            campaign_ad_count = 3
        elif campaign.campaign_type == "conversion":
            campaign_ad_count = 2
        elif campaign.campaign_type == "search":
            campaign_ad_count = 2
        else:  # email
            campaign_ad_count = 2

        for i in range(campaign_ad_count):
            if idx < len(all_ads):
                all_ads[idx].ad_campaign_id = campaign.id
                db.add(all_ads[idx])
                idx += 1

    db.commit()

    # Return summary
    total_budget = sum(c.budget_total for c in all_campaigns)

    return {
        "success": True,
        "event_id": event_id,
        "campaigns_created": len(all_campaigns),
        "ads_created": len(all_ads),
        "total_budget": total_budget,
        "total_budget_formatted": f"${total_budget/100:.2f}",
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "platform": c.platform,
                "type": c.campaign_type,
                "ads_count": len([a for a in all_ads if a.ad_campaign_id == c.id]),
                "budget": f"${c.budget_total/100:.2f}"
            }
            for c in all_campaigns
        ]
    }
