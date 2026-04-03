"""
Unified Social Media Publishing Service

Publishes events to all connected social media platforms:
- Twitter/X
- Facebook
- Instagram
- TikTok
- LinkedIn
- YouTube Community Posts
- Threads
- Pinterest

Uses platform-specific APIs and Postiz for unified scheduling.
"""
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Event, SocialMediaPost
from app.config import get_settings

logger = logging.getLogger(__name__)


class SocialMediaPublisher:
    """Unified social media publishing service."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def update_event_on_social_media(
        self,
        event_id: int,
        platforms: Optional[List[str]] = None
    ) -> Dict:
        """
        Update existing social media posts with latest event/ticket information.

        Args:
            event_id: Event ID to update
            platforms: List of platforms to update (None = all platforms with posts)

        Returns:
            Dictionary with update results per platform
        """
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Find existing posts for this event
        query = self.db.query(SocialMediaPost).filter(
            SocialMediaPost.event_id == event_id,
            SocialMediaPost.is_deleted == False
        )

        if platforms:
            query = query.filter(SocialMediaPost.platform.in_(platforms))

        existing_posts = query.all()

        if not existing_posts:
            return {
                "event_id": event_id,
                "event_name": event.name,
                "status": "no_posts",
                "message": "No existing posts found to update",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Generate fresh content with latest ticket info
        content = self._generate_event_content(event)

        results = {}

        # Update each platform
        for post in existing_posts:
            try:
                result = self._update_platform_post(event, post, content)
                results[post.platform] = result

                if result.get("status") == "success":
                    # Update our record
                    post.last_updated_at = datetime.utcnow()
                    post.content = content.get(self._get_content_version_for_platform(post.platform))
                    self.db.commit()

                logger.info(f"Updated post {post.id} on {post.platform}: {result}")

            except Exception as e:
                logger.error(f"Error updating {post.platform}: {e}")
                results[post.platform] = {"status": "error", "error": str(e)}

        return {
            "event_id": event_id,
            "event_name": event.name,
            "posts_attempted": len(existing_posts),
            "posts_succeeded": sum(1 for r in results.values() if r.get("status") == "success"),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def update_event_status_everywhere(
        self,
        event_id: int,
        status: str,  # "published", "draft", "cancelled", "paused"
        platforms: Optional[List[str]] = None
    ) -> Dict:
        """
        Update event status across all platforms.

        Args:
            event_id: Event ID
            status: New status (published, draft, cancelled, paused)
            platforms: List of platforms to update (None = all enabled)

        Returns:
            Dictionary with update results per platform
        """
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Determine which platforms to update
        if platforms is None:
            platforms = self._get_enabled_platforms()

        results = {}

        # Update status on each platform
        for platform in platforms:
            try:
                if status == "draft" or status == "paused":
                    # Unpublish/hide the event
                    result = self._unpublish_from_platform(event, platform)
                elif status == "cancelled":
                    # Cancel/delete the event
                    result = self._cancel_on_platform(event, platform)
                elif status == "published":
                    # Republish the event
                    content = self._generate_event_content(event)
                    result = self._publish_to_platform(event, content, platform, None)
                else:
                    result = {"status": "error", "error": f"Unknown status: {status}"}

                results[platform] = result
                logger.info(f"Updated event {event_id} status to '{status}' on {platform}: {result}")

            except Exception as e:
                logger.error(f"Error updating status on {platform}: {e}")
                results[platform] = {"status": "error", "error": str(e)}

        return {
            "event_id": event_id,
            "event_name": event.name,
            "new_status": status,
            "platforms_attempted": len(platforms),
            "platforms_succeeded": sum(1 for r in results.values() if r.get("status") == "success"),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def publish_event_to_all_platforms(
        self,
        event_id: int,
        platforms: Optional[List[str]] = None,
        schedule_time: Optional[datetime] = None
    ) -> Dict:
        """
        Publish event to all enabled social media platforms.

        Args:
            event_id: Event ID to publish
            platforms: List of platforms to publish to (None = all enabled)
            schedule_time: When to post (None = post immediately)

        Returns:
            Dictionary with publish results per platform
        """
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Generate content for the event
        content = self._generate_event_content(event)

        # Determine which platforms to publish to
        if platforms is None:
            platforms = self._get_enabled_platforms()

        results = {}

        # Publish to each platform
        for platform in platforms:
            try:
                result = self._publish_to_platform(event, content, platform, schedule_time)
                results[platform] = result

                # Save post record if successful
                if result.get("status") == "success" and result.get("post_id"):
                    self._save_social_media_post(
                        event_id=event_id,
                        platform=platform,
                        post_id=result["post_id"],
                        post_url=result.get("url"),
                        content=content.get(self._get_content_version_for_platform(platform)),
                        image_url=content.get("image_url"),
                        scheduled_for=schedule_time
                    )

                logger.info(f"Published event {event_id} to {platform}: {result}")

            except Exception as e:
                logger.error(f"Error publishing to {platform}: {e}")
                results[platform] = {"status": "error", "error": str(e)}

        return {
            "event_id": event_id,
            "event_name": event.name,
            "platforms_attempted": len(platforms),
            "platforms_succeeded": sum(1 for r in results.values() if r.get("status") == "success"),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _publish_to_platform(
        self,
        event: Event,
        content: Dict,
        platform: str,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Route to the appropriate platform-specific publish method."""
        if platform == "twitter":
            return self._publish_to_twitter(event, content, schedule_time)
        elif platform == "facebook":
            return self._publish_to_facebook(event, content, schedule_time)
        elif platform == "instagram":
            return self._publish_to_instagram(event, content, schedule_time)
        elif platform == "tiktok":
            return self._publish_to_tiktok(event, content, schedule_time)
        elif platform == "linkedin":
            return self._publish_to_linkedin(event, content, schedule_time)
        elif platform == "youtube":
            return self._publish_to_youtube(event, content, schedule_time)
        elif platform == "threads":
            return self._publish_to_threads(event, content, schedule_time)
        elif platform == "pinterest":
            return self._publish_to_pinterest(event, content, schedule_time)
        elif platform == "postiz":
            return self._publish_via_postiz(event, content, platforms, schedule_time)
        else:
            return {"status": "error", "error": f"Unknown platform: {platform}"}

    def _generate_event_content(self, event: Event) -> Dict[str, str]:
        """
        Generate platform-optimized content for the event.

        Returns:
            Dictionary with content variations for different platforms
        """
        # Base content
        event_url = f"{self.settings.base_url}/events/{event.id}"

        # Parse event_date (stored as string in YYYY-MM-DD format)
        if event.event_date:
            try:
                from datetime import datetime as dt
                date_obj = dt.strptime(event.event_date, "%Y-%m-%d")
                event_date = date_obj.strftime("%B %d, %Y")
            except:
                event_date = event.event_date
        else:
            event_date = "TBA"

        # Parse event_time (stored as string in HH:MM format)
        if event.event_time:
            try:
                from datetime import datetime as dt
                time_obj = dt.strptime(event.event_time, "%H:%M")
                event_time = time_obj.strftime("%I:%M %p")
            except:
                event_time = event.event_time
        else:
            event_time = ""

        # Get location from venue
        location = event.venue.name if event.venue else 'TBA'

        # Get ticket tier information
        ticket_info = self._generate_ticket_info(event)

        # Generate description (use event description or generate from AI)
        description = event.description or f'Join us for an unforgettable experience at {event.name}!'
        short_description = description[:150] + '...' if len(description) > 150 else description

        # Short version (Twitter, Threads - 280 chars)
        short = f"🎉 {event.name}\n📅 {event_date} {event_time}\n📍 {location}\n\n{ticket_info['short']}\n\n🎟️ Get tickets: {event_url}"

        # Medium version (Instagram caption, Facebook)
        medium = f"""🎉 {event.name}

📅 {event_date} at {event_time}
📍 {location}

{short_description}

{ticket_info['medium']}

🎟️ Tickets available now!
{event_url}

{self._generate_hashtags(event)}"""

        # Long version (LinkedIn, Facebook detailed)
        long = f"""🎉 Exciting News: {event.name}

We're thrilled to announce {event.name}!

📅 Date: {event_date}
🕐 Time: {event_time}
📍 Location: {location}

{description}

{ticket_info['long']}

🎟️ Secure your tickets now: {event_url}

Don't miss out on this amazing event!

{self._generate_hashtags(event)}"""

        # Get flyer/image URL if available
        image_url = None
        if hasattr(event, 'flyer_url') and event.flyer_url:
            image_url = event.flyer_url
        elif hasattr(event, 'image_url') and event.image_url:
            image_url = event.image_url

        return {
            "short": short,
            "medium": medium,
            "long": long,
            "image_url": image_url,
            "event_url": event_url,
            "event_name": event.name,
            "event_date": event_date,
            "event_time": event_time,
            "hashtags": self._generate_hashtags(event)
        }

    def _generate_ticket_info(self, event: Event) -> Dict[str, str]:
        """
        Generate ticket information text for different platforms.

        Returns:
            Dictionary with short, medium, and long ticket descriptions
        """
        # Get ticket tiers for this event
        ticket_tiers = event.ticket_tiers if hasattr(event, 'ticket_tiers') else []

        if not ticket_tiers or len(ticket_tiers) == 0:
            return {
                "short": "🎟️ Tickets available",
                "medium": "🎟️ Tickets available now!",
                "long": "🎟️ Tickets: Available now - secure your spot!"
            }

        # Sort by price
        sorted_tiers = sorted(ticket_tiers, key=lambda t: t.price)

        # Get price range
        min_price = sorted_tiers[0].price / 100  # Convert cents to dollars
        max_price = sorted_tiers[-1].price / 100

        # Check availability
        total_available = sum(tier.quantity_available - tier.quantity_sold for tier in ticket_tiers if tier.quantity_available)
        total_capacity = sum(tier.quantity_available for tier in ticket_tiers if tier.quantity_available)
        sold_out = total_available == 0

        if sold_out:
            return {
                "short": "🔴 SOLD OUT",
                "medium": "🔴 SOLD OUT - Join waitlist!",
                "long": "🔴 This event is SOLD OUT! Join our waitlist for updates on additional tickets."
            }

        # Calculate urgency
        percent_sold = (total_capacity - total_available) / total_capacity if total_capacity > 0 else 0
        is_selling_fast = percent_sold > 0.7
        low_availability = total_available < 50

        # Short version (for Twitter)
        if len(ticket_tiers) == 1:
            short = f"💵 ${min_price:.0f}"
        else:
            short = f"💵 ${min_price:.0f}-${max_price:.0f}"

        if low_availability:
            short += f" • Only {total_available} left!"
        elif is_selling_fast:
            short += " • Selling fast!"

        # Medium version (for Instagram/Facebook)
        medium = "🎟️ Ticket Options:\n"
        for tier in sorted_tiers[:3]:  # Show top 3 tiers
            available = tier.quantity_available - tier.quantity_sold if tier.quantity_available else "∞"
            medium += f"  • {tier.name}: ${tier.price/100:.0f}"
            if tier.quantity_available:
                medium += f" ({available} left)"
            medium += "\n"

        if is_selling_fast:
            medium += "\n⚡ Selling fast - don't miss out!"
        elif low_availability:
            medium += f"\n⚠️ Limited availability - only {total_available} tickets remaining!"

        # Long version (for LinkedIn)
        long = "🎟️ Ticket Information:\n\n"
        for tier in sorted_tiers:
            available = tier.quantity_available - tier.quantity_sold if tier.quantity_available else "Unlimited"
            long += f"• {tier.name} - ${tier.price/100:.2f}\n"
            if tier.description:
                long += f"  {tier.description}\n"
            if tier.quantity_available:
                long += f"  Availability: {available} / {tier.quantity_available} remaining\n"
            long += "\n"

        if is_selling_fast:
            long += "⚡ This event is selling fast! Over 70% of tickets have been sold.\n"
        elif low_availability:
            long += f"⚠️ Limited availability - only {total_available} tickets remaining!\n"

        long += "\nSecure your tickets before they're gone!"

        return {
            "short": short,
            "medium": medium.strip(),
            "long": long.strip()
        }

    def _generate_hashtags(self, event: Event) -> str:
        """Generate relevant hashtags for the event."""
        base_tags = ["#Events", "#LiveEvents"]

        # Add event name as hashtag
        if event.name:
            event_tag = f"#{event.name.replace(' ', '').replace('-', '')}"
            base_tags.append(event_tag)

        # Add category tags if available
        if hasattr(event, 'categories') and event.categories:
            for category in event.categories:
                cat_tag = f"#{category.name.replace(' ', '')}"
                base_tags.append(cat_tag)

        # Add location tag from venue if available
        if event.venue and event.venue.address:
            # Extract city from address
            address_parts = event.venue.address.split(',')
            if len(address_parts) >= 2:
                city = address_parts[-2].strip()  # Usually city is second to last
                base_tags.append(f"#{city.replace(' ', '')}")

        return " ".join(base_tags[:5])  # Limit to 5 hashtags

    def _get_enabled_platforms(self) -> List[str]:
        """Get list of platforms that are configured and enabled."""
        platforms = []

        if self.settings.twitter_api_key:
            platforms.append("twitter")
        if self.settings.meta_access_token:
            platforms.extend(["facebook", "instagram", "threads"])
        if self.settings.tiktok_access_token:
            platforms.append("tiktok")
        if self.settings.linkedin_access_token:
            platforms.append("linkedin")
        if self.settings.youtube_api_key:
            platforms.append("youtube")
        if self.settings.pinterest_access_token:
            platforms.append("pinterest")
        if self.settings.postiz_api_key:
            platforms.append("postiz")

        return platforms

    # ============== Platform-Specific Publishing Methods ==============

    def _publish_to_twitter(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event to Twitter/X."""
        if not self.settings.twitter_api_key:
            return {"status": "skipped", "reason": "Twitter API not configured"}

        try:
            import tweepy

            # Authenticate
            client = tweepy.Client(
                bearer_token=self.settings.twitter_bearer_token,
                consumer_key=self.settings.twitter_api_key,
                consumer_secret=self.settings.twitter_api_secret,
                access_token=self.settings.twitter_access_token,
                access_token_secret=self.settings.twitter_access_secret
            )

            # Create tweet
            text = content["short"]

            # Upload media if available
            media_ids = []
            if content["image_url"]:
                # Note: Would need to download image and upload to Twitter
                # Simplified for now
                pass

            # Post tweet
            response = client.create_tweet(text=text, media_ids=media_ids if media_ids else None)

            return {
                "status": "success",
                "platform": "twitter",
                "post_id": response.data['id'],
                "url": f"https://twitter.com/user/status/{response.data['id']}"
            }

        except Exception as e:
            logger.error(f"Twitter publish error: {e}")
            return {"status": "error", "error": str(e)}

    def _publish_to_facebook(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event to Facebook."""
        if not self.settings.meta_access_token or not self.settings.facebook_page_id:
            return {"status": "skipped", "reason": "Facebook API not configured"}

        try:
            url = f"https://graph.facebook.com/v18.0/{self.settings.facebook_page_id}/feed"

            data = {
                "message": content["medium"],
                "access_token": self.settings.meta_access_token
            }

            if content["image_url"]:
                data["link"] = content["image_url"]

            if schedule_time:
                data["scheduled_publish_time"] = int(schedule_time.timestamp())
                data["published"] = False

            response = requests.post(url, data=data)
            response.raise_for_status()
            result = response.json()

            return {
                "status": "success",
                "platform": "facebook",
                "post_id": result.get("id"),
                "url": f"https://facebook.com/{result.get('id')}"
            }

        except Exception as e:
            logger.error(f"Facebook publish error: {e}")
            return {"status": "error", "error": str(e)}

    def _publish_to_instagram(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event to Instagram."""
        if not self.settings.meta_access_token or not self.settings.instagram_account_id:
            return {"status": "skipped", "reason": "Instagram API not configured"}

        if not content["image_url"]:
            return {"status": "skipped", "reason": "Instagram requires an image"}

        try:
            # Instagram requires image URL to create media container
            url = f"https://graph.facebook.com/v18.0/{self.settings.instagram_account_id}/media"

            data = {
                "image_url": content["image_url"],
                "caption": content["medium"],
                "access_token": self.settings.meta_access_token
            }

            # Create media container
            response = requests.post(url, data=data)
            response.raise_for_status()
            container_id = response.json()["id"]

            # Publish media container
            publish_url = f"https://graph.facebook.com/v18.0/{self.settings.instagram_account_id}/media_publish"
            publish_data = {
                "creation_id": container_id,
                "access_token": self.settings.meta_access_token
            }

            response = requests.post(publish_url, data=publish_data)
            response.raise_for_status()
            result = response.json()

            return {
                "status": "success",
                "platform": "instagram",
                "post_id": result.get("id")
            }

        except Exception as e:
            logger.error(f"Instagram publish error: {e}")
            return {"status": "error", "error": str(e)}

    def _publish_to_tiktok(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event to TikTok."""
        if not self.settings.tiktok_access_token:
            return {"status": "skipped", "reason": "TikTok API not configured"}

        # TikTok requires video content
        return {"status": "skipped", "reason": "TikTok requires video content (not yet implemented)"}

    def _publish_to_linkedin(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event to LinkedIn."""
        if not self.settings.linkedin_access_token:
            return {"status": "skipped", "reason": "LinkedIn API not configured"}

        try:
            headers = {
                "Authorization": f"Bearer {self.settings.linkedin_access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }

            # Get user URN (would need to be cached/configured)
            person_urn = self.settings.linkedin_person_urn  # Need to add to config

            data = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content["long"]
                        },
                        "shareMediaCategory": "ARTICLE" if content["image_url"] else "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            if content["image_url"]:
                data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                    "status": "READY",
                    "originalUrl": content["image_url"]
                }]

            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()

            return {
                "status": "success",
                "platform": "linkedin",
                "post_id": result.get("id")
            }

        except Exception as e:
            logger.error(f"LinkedIn publish error: {e}")
            return {"status": "error", "error": str(e)}

    def _publish_to_youtube(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event as YouTube Community Post."""
        if not self.settings.youtube_api_key:
            return {"status": "skipped", "reason": "YouTube API not configured"}

        # YouTube Community Posts API implementation
        return {"status": "skipped", "reason": "YouTube Community Posts not yet implemented"}

    def _publish_to_threads(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event to Threads (Meta)."""
        if not self.settings.meta_access_token:
            return {"status": "skipped", "reason": "Threads (Meta) API not configured"}

        # Threads uses similar API to Instagram
        return {"status": "skipped", "reason": "Threads publishing not yet implemented"}

    def _publish_to_pinterest(
        self,
        event: Event,
        content: Dict,
        schedule_time: Optional[datetime]
    ) -> Dict:
        """Publish event to Pinterest."""
        if not self.settings.pinterest_access_token:
            return {"status": "skipped", "reason": "Pinterest API not configured"}

        return {"status": "skipped", "reason": "Pinterest publishing not yet implemented"}

    def _publish_via_postiz(
        self,
        event: Event,
        content: Dict,
        platforms: List[str],
        schedule_time: Optional[datetime]
    ) -> Dict:
        """
        Publish event via Postiz (multi-platform publishing tool).

        Postiz can handle: Facebook, Instagram, Twitter, LinkedIn, TikTok,
        YouTube, Pinterest, Reddit all in one API call.
        """
        if not self.settings.postiz_api_key:
            return {"status": "skipped", "reason": "Postiz API not configured"}

        try:
            headers = {
                "Authorization": f"Bearer {self.settings.postiz_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "text": content["medium"],
                "platforms": platforms,
                "mediaUrls": [content["image_url"]] if content["image_url"] else [],
                "scheduleDate": schedule_time.isoformat() if schedule_time else None
            }

            response = requests.post(
                f"{self.settings.postiz_url}/posts",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()

            return {
                "status": "success",
                "platform": "postiz",
                "post_id": result.get("id"),
                "platforms_published": result.get("platforms", [])
            }

        except Exception as e:
            logger.error(f"Postiz publish error: {e}")
            return {"status": "error", "error": str(e)}

    # ============== Status Management Methods ==============

    def _unpublish_from_platform(self, event: Event, platform: str) -> Dict:
        """Unpublish/hide event on a platform (set to draft/paused)."""
        if platform == "twitter":
            # Twitter doesn't support unpublishing - would need to delete tweet
            return {"status": "info", "message": "Twitter doesn't support draft mode. Delete tweet to unpublish."}

        elif platform == "facebook":
            if not self.settings.meta_access_token or not self.settings.facebook_page_id:
                return {"status": "skipped", "reason": "Facebook API not configured"}

            # Get post ID from event metadata (would need to store this when publishing)
            post_id = event.social_media_posts.get("facebook_post_id") if hasattr(event, 'social_media_posts') else None
            if not post_id:
                return {"status": "skipped", "reason": "No Facebook post ID found"}

            try:
                # Unpublish the post (set published=false)
                url = f"https://graph.facebook.com/v18.0/{post_id}"
                data = {
                    "is_published": False,
                    "access_token": self.settings.meta_access_token
                }
                response = requests.post(url, data=data)
                response.raise_for_status()

                return {"status": "success", "message": "Unpublished from Facebook"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        elif platform == "instagram":
            # Instagram doesn't support unpublishing - would need to delete
            return {"status": "info", "message": "Instagram doesn't support draft mode. Delete post to unpublish."}

        elif platform == "linkedin":
            # LinkedIn doesn't support unpublishing - would need to delete
            return {"status": "info", "message": "LinkedIn doesn't support draft mode. Delete post to unpublish."}

        elif platform == "postiz":
            # Postiz may support draft mode depending on platform
            return {"status": "info", "message": "Contact Postiz to manage post status"}

        else:
            return {"status": "skipped", "reason": f"Unpublish not implemented for {platform}"}

    def _cancel_on_platform(self, event: Event, platform: str) -> Dict:
        """Cancel/delete event on a platform."""
        if platform == "twitter":
            if not self.settings.twitter_bearer_token:
                return {"status": "skipped", "reason": "Twitter API not configured"}

            tweet_id = event.social_media_posts.get("twitter_tweet_id") if hasattr(event, 'social_media_posts') else None
            if not tweet_id:
                return {"status": "skipped", "reason": "No Twitter tweet ID found"}

            try:
                import tweepy
                client = tweepy.Client(bearer_token=self.settings.twitter_bearer_token)
                client.delete_tweet(tweet_id)
                return {"status": "success", "message": "Deleted tweet"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        elif platform == "facebook":
            if not self.settings.meta_access_token:
                return {"status": "skipped", "reason": "Facebook API not configured"}

            post_id = event.social_media_posts.get("facebook_post_id") if hasattr(event, 'social_media_posts') else None
            if not post_id:
                return {"status": "skipped", "reason": "No Facebook post ID found"}

            try:
                url = f"https://graph.facebook.com/v18.0/{post_id}"
                params = {"access_token": self.settings.meta_access_token}
                response = requests.delete(url, params=params)
                response.raise_for_status()
                return {"status": "success", "message": "Deleted Facebook post"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        elif platform == "instagram":
            # Instagram deletion requires specific permissions
            return {"status": "info", "message": "Instagram post deletion requires manual action or Instagram Graph API permissions"}

        elif platform == "linkedin":
            if not self.settings.linkedin_access_token:
                return {"status": "skipped", "reason": "LinkedIn API not configured"}

            post_urn = event.social_media_posts.get("linkedin_post_urn") if hasattr(event, 'social_media_posts') else None
            if not post_urn:
                return {"status": "skipped", "reason": "No LinkedIn post URN found"}

            try:
                headers = {
                    "Authorization": f"Bearer {self.settings.linkedin_access_token}",
                    "X-Restli-Protocol-Version": "2.0.0"
                }
                url = f"https://api.linkedin.com/v2/ugcPosts/{post_urn}"
                response = requests.delete(url, headers=headers)
                response.raise_for_status()
                return {"status": "success", "message": "Deleted LinkedIn post"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        else:
            return {"status": "skipped", "reason": f"Cancel not implemented for {platform}"}

    # ============== Helper Methods ==============

    def _save_social_media_post(
        self,
        event_id: int,
        platform: str,
        post_id: str,
        post_url: Optional[str],
        content: str,
        image_url: Optional[str],
        scheduled_for: Optional[datetime]
    ):
        """Save social media post record to database."""
        post = SocialMediaPost(
            event_id=event_id,
            platform=platform,
            platform_post_id=post_id,
            post_url=post_url,
            content=content,
            image_url=image_url,
            scheduled_for=scheduled_for,
            published_at=datetime.utcnow() if not scheduled_for else scheduled_for
        )
        self.db.add(post)
        self.db.commit()
        logger.info(f"Saved {platform} post record for event {event_id}")

    def _get_content_version_for_platform(self, platform: str) -> str:
        """Get appropriate content version key for platform."""
        if platform in ["twitter", "threads"]:
            return "short"
        elif platform in ["facebook", "instagram"]:
            return "medium"
        elif platform == "linkedin":
            return "long"
        else:
            return "medium"  # Default

    def _update_platform_post(
        self,
        event: Event,
        post: SocialMediaPost,
        content: Dict
    ) -> Dict:
        """Update existing post on specific platform."""
        platform = post.platform

        if platform == "twitter":
            return self._update_twitter_post(post, content)
        elif platform == "facebook":
            return self._update_facebook_post(post, content)
        elif platform == "instagram":
            return self._update_instagram_post(post, content)
        elif platform == "linkedin":
            return self._update_linkedin_post(post, content)
        else:
            return {"status": "skipped", "reason": f"Update not supported for {platform}"}

    def _update_twitter_post(self, post: SocialMediaPost, content: Dict) -> Dict:
        """
        Update Twitter post.
        Note: Twitter doesn't support editing tweets, so we delete and repost.
        """
        try:
            import tweepy

            client = tweepy.Client(
                bearer_token=self.settings.twitter_bearer_token,
                consumer_key=self.settings.twitter_api_key,
                consumer_secret=self.settings.twitter_api_secret,
                access_token=self.settings.twitter_access_token,
                access_token_secret=self.settings.twitter_access_secret
            )

            # Delete old tweet
            client.delete_tweet(post.platform_post_id)

            # Create new tweet
            response = client.create_tweet(text=content["short"])

            # Update post record
            post.platform_post_id = response.data['id']
            post.post_url = f"https://twitter.com/user/status/{response.data['id']}"
            self.db.commit()

            return {
                "status": "success",
                "message": "Updated Twitter post (deleted old, created new)",
                "post_id": response.data['id']
            }

        except Exception as e:
            logger.error(f"Twitter update error: {e}")
            return {"status": "error", "error": str(e)}

    def _update_facebook_post(self, post: SocialMediaPost, content: Dict) -> Dict:
        """Update Facebook post (if supported by page permissions)."""
        try:
            url = f"https://graph.facebook.com/v18.0/{post.platform_post_id}"
            data = {
                "message": content["medium"],
                "access_token": self.settings.meta_access_token
            }

            response = requests.post(url, data=data)
            response.raise_for_status()

            return {
                "status": "success",
                "message": "Updated Facebook post"
            }

        except requests.HTTPError as e:
            # Facebook may not allow editing depending on permissions
            if e.response.status_code == 400:
                return {
                    "status": "skipped",
                    "reason": "Facebook post editing not allowed (depends on permissions)"
                }
            return {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"Facebook update error: {e}")
            return {"status": "error", "error": str(e)}

    def _update_instagram_post(self, post: SocialMediaPost, content: Dict) -> Dict:
        """Instagram does not support editing captions after posting."""
        return {
            "status": "skipped",
            "reason": "Instagram does not support editing post captions"
        }

    def _update_linkedin_post(self, post: SocialMediaPost, content: Dict) -> Dict:
        """
        Update LinkedIn post.
        Note: LinkedIn API has limited edit support; may need to delete and recreate.
        """
        return {
            "status": "skipped",
            "reason": "LinkedIn does not support editing posts via API (delete and recreate required)"
        }


def get_social_media_publisher(db: Session) -> SocialMediaPublisher:
    """Factory function to get social media publisher instance."""
    return SocialMediaPublisher(db)
