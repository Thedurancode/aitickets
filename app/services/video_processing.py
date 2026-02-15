"""Post-upload video processing: trim to max duration and compress."""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from app.services.highlight_video import _probe_duration

logger = logging.getLogger(__name__)

MAX_DURATION_SECONDS = 30
FFMPEG_TIMEOUT = 120


def process_uploaded_video(file_path: str) -> bool:
    """
    Trim and compress a video file in-place.

    Trims to 30s max, re-encodes to H.264 720p with AAC audio.
    On failure, leaves the original file untouched.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning("Video file not found for processing: %s", file_path)
        return False

    duration = _probe_duration(file_path)
    trim_args = []
    if duration > MAX_DURATION_SECONDS:
        trim_args = ["-t", str(MAX_DURATION_SECONDS)]
        logger.info("Trimming video from %.1fs to %ds: %s", duration, MAX_DURATION_SECONDS, path.name)

    tmp_path = None
    try:
        fd, tmp_path_str = tempfile.mkstemp(suffix=".mp4", dir=str(path.parent))
        os.close(fd)
        tmp_path = Path(tmp_path_str)

        cmd = [
            "ffmpeg", "-y",
            "-i", file_path,
            *trim_args,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            str(tmp_path),
        ]

        subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT, check=True)

        if not tmp_path.exists() or tmp_path.stat().st_size == 0:
            logger.warning("FFmpeg produced empty output for %s", path.name)
            return False

        os.replace(str(tmp_path), file_path)
        tmp_path = None

        logger.info("Video processed successfully: %s", path.name)
        return True

    except subprocess.CalledProcessError as e:
        logger.warning("FFmpeg failed for %s: %s", path.name, e.stderr[:500] if e.stderr else "")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg timed out (%ds) for %s", FFMPEG_TIMEOUT, path.name)
        return False
    except Exception:
        logger.exception("Unexpected error processing video %s", path.name)
        return False
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
