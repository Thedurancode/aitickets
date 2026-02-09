import requests

from app.config import get_settings


def _get_base_url() -> str:
    """Get Postiz API base URL."""
    settings = get_settings()
    return f"{settings.postiz_url.rstrip('/')}/public/v1"


def _get_headers() -> dict | None:
    """Get Postiz API headers. Returns None if not configured."""
    settings = get_settings()
    if not settings.postiz_api_key:
        return None
    return {
        "Content-Type": "application/json",
        "Authorization": settings.postiz_api_key,
    }


def get_integrations() -> dict:
    """
    Get all connected social media integrations (accounts/channels).
    Each integration has an id and platform type needed for posting.
    """
    headers = _get_headers()
    if not headers:
        return {"success": False, "error": "Postiz not configured (missing API key)"}

    try:
        r = requests.get(
            f"{_get_base_url()}/integrations",
            headers=headers,
            timeout=30,
        )
        data = r.json()
        if r.status_code >= 400:
            return {"success": False, "error": data}
        return {"success": True, "data": data}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def post_to_social(
    text: str,
    integration_ids: list[str],
    post_type: str = "now",
    schedule_date: str | None = None,
    image_urls: list[str] | None = None,
) -> dict:
    """
    Post to one or more social media channels via Postiz.

    Args:
        text: The post content.
        integration_ids: List of Postiz integration/channel IDs to post to.
        post_type: "now" for immediate, "schedule" for scheduled, "draft" for draft.
        schedule_date: ISO 8601 datetime (required if post_type is "schedule").
        image_urls: Optional list of public image URLs to attach.

    Returns:
        dict with success status and Postiz response or error.
    """
    headers = _get_headers()
    if not headers:
        return {"success": False, "error": "Postiz not configured (missing API key)"}

    if post_type == "schedule" and not schedule_date:
        return {"success": False, "error": "schedule_date is required for scheduled posts"}

    # Build a post entry for each integration
    posts = []
    for integration_id in integration_ids:
        post_value = [{"content": text}]
        if image_urls:
            post_value[0]["image"] = [{"path": url} for url in image_urls]

        posts.append({
            "integration": {"id": integration_id},
            "value": post_value,
        })

    payload = {
        "type": post_type,
        "posts": posts,
    }
    if schedule_date:
        payload["date"] = schedule_date

    try:
        r = requests.post(
            f"{_get_base_url()}/posts",
            json=payload,
            headers=headers,
            timeout=30,
        )
        data = r.json()
        if r.status_code >= 400:
            return {"success": False, "error": data}
        return {"success": True, "data": data}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def delete_social_post(post_id: str) -> dict:
    """Delete a previously published social media post."""
    headers = _get_headers()
    if not headers:
        return {"success": False, "error": "Postiz not configured (missing API key)"}

    try:
        r = requests.delete(
            f"{_get_base_url()}/posts/{post_id}",
            headers=headers,
            timeout=30,
        )
        data = r.json()
        if r.status_code >= 400:
            return {"success": False, "error": data}
        return {"success": True, "data": data}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}
