"""
Auto-generate highlight recap video from attendee-uploaded photos and videos.

Uses FFmpeg (already installed in Docker) to:
1. Select best photos by file size / resolution
2. Convert photos to short clips with Ken Burns zoom
3. Trim video clips to first N seconds
4. Concatenate everything with crossfade transitions
5. Overlay event name / date text
6. Optional background music
7. Output a shareable 720p MP4

Designed to run as a background task (blocking I/O).
"""

import base64
import logging
import subprocess
import tempfile
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import SessionLocal
from app.models import Event, EventPhoto

# MediaPipe face/smile detection (optional dependency)
try:
    import mediapipe as _mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

_FACE_LANDMARKER_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
_FACE_LANDMARKER_PATH = Path(tempfile.gettempdir()) / "face_landmarker.task"

logger = logging.getLogger(__name__)

# -- Constants --
PHOTO_DURATION = 3          # seconds each photo is shown
VIDEO_CLIP_MAX = 8          # max seconds per video clip
MAX_PHOTOS = 25             # limit photos in highlight
MAX_VIDEOS = 10             # limit video clips
CROSSFADE_DURATION = 0.8    # seconds of crossfade between clips
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
OUTPUT_FPS = 30

# AI scoring
AI_SCORING_MODEL = "gpt-4o"
AI_DETAIL_LEVEL = "low"             # 85 tokens per image
VIDEO_KEYFRAME_INTERVAL = 5         # extract 1 frame per N seconds
AI_BATCH_SIZE = 20                  # max images per API call

# MediaPipe scoring
MP_MAX_FACES = 10
MP_MIN_DETECTION_CONFIDENCE = 0.5


class MediaScore(BaseModel):
    """AI-generated score for a single media keyframe."""
    image_index: int = Field(description="0-based index of the image in the batch")
    energy: int = Field(ge=1, le=10, description="Energy/excitement level")
    composition: int = Field(ge=1, le=10, description="Visual quality and framing")
    people: int = Field(ge=1, le=10, description="People visibility and prominence")
    emotion: int = Field(ge=1, le=10, description="Fun factor, smiles, celebration")
    description: str = Field(description="Brief 5-word description")


class ScoringResponse(BaseModel):
    """Batch scoring response from AI."""
    scores: list[MediaScore]


def _select_best_photos(photos: list[dict], max_count: int = MAX_PHOTOS) -> list[dict]:
    """Select best photos by file size (proxy for quality/resolution)."""
    uploads_dir = Path(get_settings().uploads_dir)

    scored = []
    for p in photos:
        filepath = uploads_dir / p["filename"]
        if not filepath.exists():
            continue
        size = filepath.stat().st_size
        scored.append({**p, "_score": size, "_path": str(filepath)})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored[:max_count]


def _select_videos(videos: list[dict], max_count: int = MAX_VIDEOS) -> list[dict]:
    """Select video clips, largest files first."""
    uploads_dir = Path(get_settings().uploads_dir)

    result = []
    for v in videos:
        filepath = uploads_dir / v["filename"]
        if not filepath.exists():
            continue
        size = filepath.stat().st_size
        result.append({**v, "_score": size, "_path": str(filepath)})

    result.sort(key=lambda x: x["_score"], reverse=True)
    return result[:max_count]


def _probe_duration(filepath: str) -> float:
    """Get duration of a video file in seconds."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _encode_image_base64(image_path: str) -> str | None:
    """Resize image to 512px wide via FFmpeg and return base64 string."""
    try:
        tmp_thumb = image_path + ".thumb.jpg"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", image_path,
                    "-vf", "scale=512:-1",
                    "-q:v", "5",
                    "-frames:v", "1",
                    tmp_thumb,
                ],
                capture_output=True, timeout=10, check=True,
            )
            target = tmp_thumb
        except Exception:
            target = image_path

        with open(target, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")

        if Path(tmp_thumb).exists() and tmp_thumb != image_path:
            Path(tmp_thumb).unlink(missing_ok=True)

        return data
    except Exception as e:
        logger.warning(f"Failed to encode image {image_path}: {e}")
        return None


def _extract_video_keyframes(video_path: str, tmpdir: str) -> list[dict]:
    """Extract 1 keyframe per VIDEO_KEYFRAME_INTERVAL seconds as small JPEGs."""
    duration = _probe_duration(video_path)
    if duration <= 0:
        return []

    prefix = f"kf_{uuid.uuid4().hex[:6]}"
    output_pattern = str(Path(tmpdir) / f"{prefix}_%03d.jpg")

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"fps=1/{VIDEO_KEYFRAME_INTERVAL},scale=512:-1",
                "-q:v", "5",
                output_pattern,
            ],
            capture_output=True, timeout=30, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.warning(f"Keyframe extraction failed for {video_path}: {e}")
        return []

    frames = []
    for f in sorted(Path(tmpdir).glob(f"{prefix}_*.jpg")):
        idx = len(frames)
        frames.append({"path": str(f), "timestamp": idx * VIDEO_KEYFRAME_INTERVAL})

    return frames


def _make_photo_clip(photo_path: str, output_path: str, duration: int = PHOTO_DURATION):
    """Convert a photo to a video clip with Ken Burns zoom effect."""
    # Zooms from 100% to 110% over the duration, centered
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", photo_path,
            "-t", str(duration),
            "-vf", (
                f"scale={OUTPUT_WIDTH * 2}:{OUTPUT_HEIGHT * 2}:force_original_aspect_ratio=increase,"
                f"crop={OUTPUT_WIDTH * 2}:{OUTPUT_HEIGHT * 2},"
                f"zoompan=z='min(zoom+0.0015,1.1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={duration * OUTPUT_FPS}:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:fps={OUTPUT_FPS}"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path,
        ],
        capture_output=True, timeout=30, check=True,
    )


def _make_video_clip(video_path: str, output_path: str, max_duration: int = VIDEO_CLIP_MAX, start_time: float = 0.0):
    """Trim and normalize a video clip to standard resolution."""
    duration = _probe_duration(video_path)
    if duration > 0 and start_time > 0:
        start_time = min(start_time, max(0, duration - max_duration))
    remaining = (duration - start_time) if duration > 0 else max_duration
    trim_to = min(remaining, max_duration)

    seek_args = ["-ss", f"{start_time:.2f}"] if start_time > 0 else []

    subprocess.run(
        [
            "ffmpeg", "-y",
            *seek_args,
            "-i", video_path,
            "-t", str(trim_to),
            "-vf", (
                f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-r", str(OUTPUT_FPS),
            "-pix_fmt", "yuv420p",
            "-an",
            output_path,
        ],
        capture_output=True, timeout=60, check=True,
    )


def _add_text_overlay(input_path: str, output_path: str, event_name: str, event_date: str):
    """Add event name + date text overlay to the final video."""
    # Escape special chars for FFmpeg drawtext
    safe_name = event_name.replace("'", "'\\''").replace(":", "\\:")
    safe_date = event_date.replace("'", "'\\''").replace(":", "\\:")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", (
                f"drawtext=text='{safe_name}'"
                f":fontsize=42:fontcolor=white:borderw=3:bordercolor=black"
                f":x=(w-text_w)/2:y=h-80"
                f":enable='between(t,0,4)',"
                f"drawtext=text='{safe_date}'"
                f":fontsize=28:fontcolor=white@0.8:borderw=2:bordercolor=black"
                f":x=(w-text_w)/2:y=h-40"
                f":enable='between(t,0,4)'"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            output_path,
        ],
        capture_output=True, timeout=120, check=True,
    )


def _ensure_face_model() -> str | None:
    """Download FaceLandmarker model if not cached. Returns path or None."""
    if _FACE_LANDMARKER_PATH.exists() and _FACE_LANDMARKER_PATH.stat().st_size > 0:
        return str(_FACE_LANDMARKER_PATH)
    try:
        import urllib.request
        logger.info("Downloading FaceLandmarker model...")
        urllib.request.urlretrieve(_FACE_LANDMARKER_URL, str(_FACE_LANDMARKER_PATH))
        logger.info(f"FaceLandmarker model downloaded ({_FACE_LANDMARKER_PATH.stat().st_size // 1024}KB)")
        return str(_FACE_LANDMARKER_PATH)
    except Exception as e:
        logger.warning(f"Failed to download FaceLandmarker model: {e}")
        return None


def _get_smile_score(blendshapes: list) -> float:
    """Extract smile score (0.0-1.0) from FaceLandmarker blendshapes."""
    smile_left = 0.0
    smile_right = 0.0
    for shape in blendshapes:
        if shape.category_name == "mouthSmileLeft":
            smile_left = shape.score
        elif shape.category_name == "mouthSmileRight":
            smile_right = shape.score
    return (smile_left + smile_right) / 2.0


def _score_with_mediapipe(image_paths: list[str]) -> dict[str, dict]:
    """Score images using MediaPipe FaceLandmarker for face count and smile detection.

    Returns dict: path -> {face_count, smile_avg, mp_score (0-10)}.
    """
    if not MEDIAPIPE_AVAILABLE:
        return {}

    model_path = _ensure_face_model()
    if not model_path:
        return {}

    results = {}
    base_options = _mp.tasks.BaseOptions(model_asset_path=model_path)
    options = _mp.tasks.vision.FaceLandmarkerOptions(
        base_options=base_options,
        num_faces=MP_MAX_FACES,
        output_face_blendshapes=True,
        min_face_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
    )

    with _mp.tasks.vision.FaceLandmarker.create_from_options(options) as landmarker:
        for path in image_paths:
            try:
                image = _mp.Image.create_from_file(path)
                result = landmarker.detect(image)

                if not result.face_landmarks:
                    results[path] = {"face_count": 0, "smile_avg": 0.0, "mp_score": 3.0}
                    continue

                face_count = len(result.face_landmarks)
                smiles = []
                if result.face_blendshapes:
                    smiles = [_get_smile_score(shapes) for shapes in result.face_blendshapes]

                smile_avg = sum(smiles) / len(smiles) if smiles else 0.0

                face_component = min(8.0, 2.0 + min(face_count, 4) * 1.5)
                smile_component = smile_avg * 10.0
                mp_score = (face_component * 0.4) + (smile_component * 0.6)

                results[path] = {
                    "face_count": face_count,
                    "smile_avg": round(smile_avg, 3),
                    "mp_score": round(mp_score, 2),
                }
            except Exception as e:
                logger.warning(f"MediaPipe scoring failed for {path}: {e}")
                results[path] = {"face_count": 0, "smile_avg": 0.0, "mp_score": 3.0}

    return results


def _merge_scores(openai_score: float | None, mp_score: float | None) -> float:
    """Merge OpenAI and MediaPipe scores. Both on 0-10 scale."""
    if openai_score is not None and mp_score is not None:
        return (openai_score * 0.6) + (mp_score * 0.4)
    if openai_score is not None:
        return openai_score
    if mp_score is not None:
        return mp_score
    return 5.0


def _score_media_batch(image_paths: list[str], image_labels: list[str]) -> list[MediaScore] | None:
    """Score a batch of images using OpenAI Vision API with structured output."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)

    content = [
        {
            "type": "text",
            "text": (
                "You are scoring event/party media for an automated highlight reel. "
                f"There are {len(image_paths)} images below, numbered 0 to {len(image_paths) - 1}. "
                "For each image, rate on a scale of 1-10:\n"
                "- energy: How much excitement, action, or energy is in the scene\n"
                "- composition: Visual quality, framing, clarity (blurry/dark = low)\n"
                "- people: How many people are visible and how prominent they are\n"
                "- emotion: Fun factor, smiles, celebration, memorable moments\n"
                "Give a brief 5-word description of each image.\n\n"
                "Image labels:\n" +
                "\n".join(f"  Image {i}: {label}" for i, label in enumerate(image_labels))
            ),
        },
    ]

    for path in image_paths:
        b64 = _encode_image_base64(path)
        if b64 is None:
            continue
        ext = Path(path).suffix.lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{b64}",
                "detail": AI_DETAIL_LEVEL,
            },
        })

    try:
        completion = client.chat.completions.parse(
            model=AI_SCORING_MODEL,
            messages=[{"role": "user", "content": content}],
            response_format=ScoringResponse,
            max_tokens=2000,
            temperature=0.2,
        )
        message = completion.choices[0].message
        if message.parsed:
            return message.parsed.scores
        logger.warning(f"AI scoring refused: {message.refusal}")
        return None
    except Exception as e:
        logger.warning(f"AI scoring API call failed: {e}")
        return None


def _score_all_media(
    photos: list[dict], videos: list[dict], tmpdir: str,
) -> tuple[list[dict], list[dict]]:
    """Score all photos and video keyframes using MediaPipe + OpenAI Vision.

    Scoring layers (best to worst):
    1. OpenAI Vision + MediaPipe: 60/40 composite
    2. MediaPipe only: face/smile scoring (free)
    3. Neither: default 5.0

    Attaches _ai_score, _ai_description, _face_count, _smile_avg to each item.
    Videos also get _best_start (float) for the best segment timestamp.
    """
    score_items = []  # (type, parent_index, path, label, keyframe_timestamp)

    for i, photo in enumerate(photos):
        path = photo.get("_path")
        if path and Path(path).exists():
            score_items.append(("photo", i, path, f"Photo {i+1}", None))

    for i, video in enumerate(videos):
        path = video.get("_path")
        if not path or not Path(path).exists():
            continue
        keyframes = _extract_video_keyframes(path, tmpdir)
        for kf in keyframes:
            score_items.append(("video", i, kf["path"], f"Video {i+1} @ {kf['timestamp']}s", kf["timestamp"]))

    if not score_items:
        return photos, videos

    all_image_paths = [item[2] for item in score_items]

    # MediaPipe scoring (local, free)
    mp_scores = {}
    if MEDIAPIPE_AVAILABLE:
        try:
            mp_scores = _score_with_mediapipe(all_image_paths)
            faces_found = sum(1 for v in mp_scores.values() if v["face_count"] > 0)
            logger.info(f"MediaPipe scored {len(mp_scores)} images (faces in {faces_found})")
        except Exception as e:
            logger.warning(f"MediaPipe scoring failed: {e}")

    # OpenAI Vision scoring (cloud API)
    settings = get_settings()
    has_openai = bool(settings.openai_api_key)
    all_openai_scores = {}  # (type, parent_index, timestamp) -> MediaScore

    if has_openai:
        for batch_start in range(0, len(score_items), AI_BATCH_SIZE):
            batch = score_items[batch_start:batch_start + AI_BATCH_SIZE]
            paths = [item[2] for item in batch]
            labels = [item[3] for item in batch]

            batch_scores = _score_media_batch(paths, labels)
            if batch_scores:
                for score in batch_scores:
                    idx = score.image_index
                    if 0 <= idx < len(batch):
                        item = batch[idx]
                        all_openai_scores[(item[0], item[1], item[4])] = score

    # Merge scores and apply to photos
    for i, photo in enumerate(photos):
        key = ("photo", i, None)
        path = photo.get("_path", "")

        openai_score = None
        if key in all_openai_scores:
            s = all_openai_scores[key]
            openai_score = (s.energy + s.composition + s.people + s.emotion) / 4.0
            photo["_ai_description"] = s.description

        mp_data = mp_scores.get(path, {})
        photo["_ai_score"] = _merge_scores(openai_score, mp_data.get("mp_score"))
        photo["_face_count"] = mp_data.get("face_count", 0)
        photo["_smile_avg"] = mp_data.get("smile_avg", 0.0)

    # Merge scores and apply to videos — find best keyframe per video
    for i, video in enumerate(videos):
        video_kf_items = [
            (item[2], item[4])  # (path, timestamp)
            for item in score_items
            if item[0] == "video" and item[1] == i
        ]

        best_score = 0.0
        best_ts = 0.0
        best_desc = ""

        for kf_path, kf_ts in video_kf_items:
            oa_key = ("video", i, kf_ts)
            oa_score = None
            oa_desc = ""
            if oa_key in all_openai_scores:
                s = all_openai_scores[oa_key]
                oa_score = (s.energy + s.composition + s.people + s.emotion) / 4.0
                oa_desc = s.description

            mp_data = mp_scores.get(kf_path, {})
            merged = _merge_scores(oa_score, mp_data.get("mp_score"))

            if merged > best_score:
                best_score = merged
                best_ts = kf_ts
                best_desc = oa_desc

        if best_score > 0:
            video["_ai_score"] = best_score
            video["_best_start"] = max(0, best_ts - 2)
            video["_ai_description"] = best_desc
        else:
            video["_ai_score"] = 5.0
            video["_best_start"] = 0.0

    return photos, videos


def _select_best_photos_ai(photos: list[dict], max_count: int = MAX_PHOTOS) -> list[dict]:
    """Select photos using AI scores with temporal spread."""
    uploads_dir = Path(get_settings().uploads_dir)

    valid = []
    for p in photos:
        filepath = uploads_dir / p["filename"]
        if not filepath.exists():
            continue
        valid.append({**p, "_path": str(filepath), "_filesize": filepath.stat().st_size})

    if not valid:
        return []

    valid.sort(key=lambda x: (x.get("_ai_score", 5.0), x["_filesize"]), reverse=True)

    if len(valid) <= max_count:
        return valid

    # Temporal bucketing — ensure coverage across the event timeline
    n_buckets = min(max_count, len(valid))
    bucket_size = len(valid) / n_buckets
    selected = []
    used_buckets = set()

    for photo in valid:
        if len(selected) >= max_count:
            break
        original_idx = next((i for i, p in enumerate(photos) if p.get("id") == photo.get("id")), 0)
        bucket = min(int(original_idx / bucket_size), n_buckets - 1)

        if bucket not in used_buckets or len(used_buckets) >= n_buckets:
            selected.append(photo)
            used_buckets.add(bucket)

    return selected[:max_count]


def _select_videos_ai(videos: list[dict], max_count: int = MAX_VIDEOS) -> list[dict]:
    """Select videos using AI scores."""
    uploads_dir = Path(get_settings().uploads_dir)

    valid = []
    for v in videos:
        filepath = uploads_dir / v["filename"]
        if not filepath.exists():
            continue
        valid.append({**v, "_path": str(filepath)})

    valid.sort(key=lambda x: x.get("_ai_score", 5.0), reverse=True)
    return valid[:max_count]


def _order_clips_narrative(clip_pairs: list[tuple[str, dict]]) -> list[str]:
    """Reorder clips for narrative arc: calm → build → peak energy → wind down."""
    if len(clip_pairs) <= 3:
        return [path for path, _ in clip_pairs]

    clip_pairs.sort(key=lambda x: x[1].get("_ai_score", 5.0))

    n = len(clip_pairs)
    result = [None] * n
    mid_start = n // 3
    mid_end = 2 * n // 3

    # Highest energy in the middle third
    high_energy = clip_pairs[-(mid_end - mid_start):]
    for i, (path, _) in enumerate(high_energy):
        result[mid_start + i] = path

    # Fill start and end with remaining
    remaining = [path for path, _ in clip_pairs if path not in result]
    fill_positions = [i for i in range(n) if result[i] is None]
    for i, pos in enumerate(fill_positions):
        if i < len(remaining):
            result[pos] = remaining[i]

    return [r for r in result if r is not None]


def generate_highlight_video(event_id: int) -> dict:
    """
    Generate a highlight recap video for an event from attendee uploads.

    Blocking function — run in a background thread.
    Returns dict with success status and video URL.
    """
    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    # Load event + media from DB
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"success": False, "error": "Event not found"}

        all_media = (
            db.query(EventPhoto)
            .filter(EventPhoto.event_id == event_id)
            .order_by(EventPhoto.created_at.asc())
            .all()
        )

        if not all_media:
            return {"success": False, "error": "No media uploaded for this event"}

        event_name = event.name
        event_date = event.event_date
    finally:
        db.close()

    # Separate photos and videos
    photos = []
    videos = []
    for m in all_media:
        filename = m.photo_url.replace("/uploads/", "", 1)
        entry = {
            "id": m.id,
            "filename": filename,
            "uploaded_by": m.uploaded_by_name or "Anonymous",
        }
        if (m.media_type or "photo") == "video":
            videos.append(entry)
        else:
            photos.append(entry)

    # Determine if AI scoring is available
    use_ai = bool(settings.openai_api_key) or MEDIAPIPE_AVAILABLE

    # Work in a temp directory
    with tempfile.TemporaryDirectory(prefix="highlight_") as tmpdir:
        tmpdir = Path(tmpdir)

        if use_ai:
            logger.info(f"Using AI scoring for event {event_id}")
            for p in photos:
                fp = uploads_dir / p["filename"]
                if fp.exists():
                    p["_path"] = str(fp)
            for v in videos:
                fp = uploads_dir / v["filename"]
                if fp.exists():
                    v["_path"] = str(fp)
            try:
                photos, videos = _score_all_media(photos, videos, str(tmpdir))
            except Exception as e:
                logger.warning(f"AI scoring failed, falling back to file-size selection: {e}")
                use_ai = False

        if use_ai:
            selected_photos = _select_best_photos_ai(photos)
            selected_videos = _select_videos_ai(videos)
        else:
            selected_photos = _select_best_photos(photos)
            selected_videos = _select_videos(videos)

        total_clips = len(selected_photos) + len(selected_videos)
        if total_clips == 0:
            return {"success": False, "error": "No valid media files found on disk"}

        logger.info(
            f"Generating highlight for event {event_id}: "
            f"{len(selected_photos)} photos, {len(selected_videos)} videos"
            f"{' (AI scored)' if use_ai else ''}"
        )

        clip_paths = []
        clip_pairs = []  # (clip_path, media_dict) for narrative ordering
        clip_index = 0

        # Convert photos to clips
        for photo in selected_photos:
            clip_path = str(tmpdir / f"clip_{clip_index:03d}.mp4")
            try:
                _make_photo_clip(photo["_path"], clip_path)
                clip_paths.append(clip_path)
                clip_pairs.append((clip_path, photo))
                clip_index += 1
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to process photo {photo['filename']}: {e.stderr[:200] if e.stderr else e}")
            except Exception as e:
                logger.warning(f"Failed to process photo {photo['filename']}: {e}")

        # Trim video clips
        for video in selected_videos:
            clip_path = str(tmpdir / f"clip_{clip_index:03d}.mp4")
            try:
                start = video.get("_best_start", 0.0) if use_ai else 0.0
                _make_video_clip(video["_path"], clip_path, start_time=start)
                clip_paths.append(clip_path)
                clip_pairs.append((clip_path, video))
                clip_index += 1
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to process video {video['filename']}: {e.stderr[:200] if e.stderr else e}")
            except Exception as e:
                logger.warning(f"Failed to process video {video['filename']}: {e}")

        # Narrative reordering (AI only)
        if use_ai and len(clip_paths) > 3:
            clip_paths = _order_clips_narrative(clip_pairs)

        if not clip_paths:
            return {"success": False, "error": "All media files failed to process"}

        # Concatenate clips with crossfade transitions
        if len(clip_paths) == 1:
            concat_output = clip_paths[0]
        else:
            concat_output = str(tmpdir / "concat.mp4")
            _concatenate_with_crossfade(clip_paths, concat_output, tmpdir)

        # Add text overlay
        final_output_name = f"highlight_ev{event_id}_{uuid.uuid4().hex[:8]}.mp4"
        final_output = uploads_dir / final_output_name

        try:
            _add_text_overlay(concat_output, str(final_output), event_name, event_date)
        except subprocess.CalledProcessError:
            # If text overlay fails, just copy the concat output
            logger.warning("Text overlay failed, using video without overlay")
            import shutil
            shutil.copy2(concat_output, str(final_output))

    if not final_output.exists() or final_output.stat().st_size == 0:
        return {"success": False, "error": "FFmpeg produced no output"}

    mp4_url = f"/uploads/{final_output_name}"
    size_mb = round(final_output.stat().st_size / (1024 * 1024), 1)

    logger.info(f"Highlight video complete for event {event_id}: {final_output_name} ({size_mb} MB)")

    # Save URL to event.post_event_video_url
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if event:
            # Clean up old highlight if it exists
            old_url = event.post_event_video_url
            if old_url and old_url.startswith("/uploads/highlight_"):
                old_file = uploads_dir / old_url.replace("/uploads/", "", 1)
                if old_file.exists():
                    old_file.unlink()

            event.post_event_video_url = mp4_url
            db.commit()
    finally:
        db.close()

    return {
        "success": True,
        "mp4_url": mp4_url,
        "size_mb": size_mb,
        "clips_used": len(clip_paths),
        "photos": len(selected_photos),
        "videos": len(selected_videos),
        "ai_scored": use_ai,
        "scoring_methods": [
            *(["openai"] if bool(settings.openai_api_key) else []),
            *(["mediapipe"] if MEDIAPIPE_AVAILABLE else []),
        ],
    }


def _concatenate_with_crossfade(clip_paths: list[str], output_path: str, tmpdir: Path):
    """Concatenate clips with crossfade transitions using FFmpeg xfade filter.

    For many clips, xfade filter chains get complex, so we use a two-pass
    approach: concat pairs with crossfade, then concat the results.
    For simplicity with large numbers of clips, we fall back to simple
    concat (no transitions) if there are more than 15 clips.
    """
    if len(clip_paths) > 15:
        # Simple concat for many clips (avoids filter complexity)
        concat_file = tmpdir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for cp in clip_paths:
                f.write(f"file '{cp}'\n")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-an",
                output_path,
            ],
            capture_output=True, timeout=300, check=True,
        )
        return

    # Build xfade filter chain for crossfade transitions
    # Each xfade needs: offset = (clip_duration * index) - (crossfade * index)
    # For uniform clips this simplifies significantly
    n = len(clip_paths)

    # Get durations
    durations = []
    for cp in clip_paths:
        d = _probe_duration(cp)
        durations.append(d if d > 0 else PHOTO_DURATION)

    # Build inputs
    inputs = []
    for cp in clip_paths:
        inputs.extend(["-i", cp])

    # Build xfade filter chain
    filter_parts = []
    offset = 0.0
    prev_label = "[0:v]"

    for i in range(1, n):
        offset += durations[i - 1] - CROSSFADE_DURATION
        if offset < 0:
            offset = 0
        out_label = f"[v{i}]" if i < n - 1 else "[vout]"
        filter_parts.append(
            f"{prev_label}[{i}:v]xfade=transition=fade:duration={CROSSFADE_DURATION}:offset={offset:.3f}{out_label}"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)
    except subprocess.CalledProcessError as e:
        logger.warning(f"xfade concat failed, falling back to simple concat: {e.stderr[:300] if e.stderr else e}")
        # Fallback: simple concat
        concat_file = tmpdir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for cp in clip_paths:
                f.write(f"file '{cp}'\n")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-an",
                output_path,
            ],
            capture_output=True, timeout=300, check=True,
        )


async def trigger_highlight_generation_async(event_id: int) -> dict:
    """Async wrapper that runs the blocking generation in a thread pool executor."""
    import asyncio

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        generate_highlight_video,
        event_id,
    )

    if result.get("success"):
        try:
            from app.routers.mcp import sse_manager

            await sse_manager.broadcast("highlight_video_ready", {
                "event_id": event_id,
                "mp4_url": result["mp4_url"],
                "size_mb": result.get("size_mb"),
                "clips_used": result.get("clips_used"),
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast SSE for highlight video: {e}")

    return result
