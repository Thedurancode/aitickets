"""
YouTube video download service using yt-dlp.

Downloads YouTube videos as MP4 files to the uploads directory,
then updates the event's video URL field from the YouTube URL to the
local MP4 path. Designed to run as a background task.
"""

import logging
import uuid
from pathlib import Path

from app.config import get_settings
from app.database import SessionLocal
from app.models import Event

logger = logging.getLogger(__name__)


def is_youtube_url(url: str) -> bool:
    """Check if a URL is a YouTube URL."""
    if not url:
        return False
    return any(x in url for x in ["youtube.com", "youtu.be"])


def _cleanup_old_video(old_url: str):
    """Delete a previously-downloaded MP4 if it's a local upload."""
    if not old_url or not old_url.startswith("/uploads/"):
        return
    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    filename = old_url.replace("/uploads/", "", 1)
    filepath = uploads_dir / filename
    try:
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Cleaned up old video: {filepath}")
    except Exception as e:
        logger.warning(f"Failed to clean up old video {filepath}: {e}")


def download_youtube_video(
    event_id: int,
    field_name: str,
    youtube_url: str,
    old_url: str = None,
) -> dict:
    """
    Download a YouTube video as MP4 using yt-dlp.

    Blocking function meant to run in a background thread/task.
    Saves to uploads dir, updates DB field, cleans up old file.
    """
    import yt_dlp

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    short_id = uuid.uuid4().hex[:8]
    field_tag = "promo" if "promo" in field_name else "recap"
    filename = f"video_ev{event_id}_{field_tag}_{short_id}.mp4"
    output_path = uploads_dir / filename

    logger.info(
        f"Starting YouTube download for event {event_id} "
        f"({field_name}): {youtube_url}"
    )

    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "outtmpl": str(output_path),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "max_filesize": 200 * 1024 * 1024,
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        logger.error(
            f"yt-dlp download failed for event {event_id} "
            f"({field_name}): {e}"
        )
        if output_path.exists():
            output_path.unlink()
        return {"success": False, "error": str(e)}

    if not output_path.exists() or output_path.stat().st_size == 0:
        logger.error(
            f"Download produced no output for event {event_id} ({field_name})"
        )
        if output_path.exists():
            output_path.unlink()
        return {"success": False, "error": "Download produced no output file"}

    mp4_url = f"/uploads/{filename}"
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(
        f"Download complete for event {event_id} ({field_name}): "
        f"{filename} ({file_size_mb:.1f} MB)"
    )

    # Update the database
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if event:
            current_value = getattr(event, field_name, None)
            if current_value == youtube_url:
                setattr(event, field_name, mp4_url)
                db.commit()
                logger.info(
                    f"Updated event {event_id}.{field_name} -> {mp4_url}"
                )
            else:
                logger.warning(
                    f"Event {event_id}.{field_name} was changed during "
                    f"download (now: {current_value}). Discarding download."
                )
                output_path.unlink()
                return {
                    "success": False,
                    "error": "URL was changed during download",
                }
        else:
            logger.warning(f"Event {event_id} not found after download")
            output_path.unlink()
            return {"success": False, "error": "Event not found"}
    finally:
        db.close()

    # Clean up old video file if it was a local upload
    if old_url:
        _cleanup_old_video(old_url)

    return {"success": True, "mp4_url": mp4_url, "size_mb": round(file_size_mb, 1)}


async def trigger_video_download_async(
    event_id: int,
    field_name: str,
    youtube_url: str,
    old_url: str = None,
):
    """
    Async wrapper that runs the blocking download in a thread pool executor.
    Broadcasts SSE event on completion.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        download_youtube_video,
        event_id,
        field_name,
        youtube_url,
        old_url,
    )

    if result.get("success"):
        try:
            from app.routers.mcp import sse_manager

            await sse_manager.broadcast("video_downloaded", {
                "event_id": event_id,
                "field": field_name,
                "mp4_url": result["mp4_url"],
                "size_mb": result.get("size_mb"),
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast SSE for video download: {e}")

    return result
