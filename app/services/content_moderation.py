"""
Content Moderation Service using nsfwpy

Detects NSFW/offensive content in uploaded images using local ML model.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# Try to import nsfwpy - gracefully degrade if not installed
try:
    from nsfwpy import NSFWDetector
    NSFWPY_AVAILABLE = True
except ImportError:
    NSFWPY_AVAILABLE = False
    NSFWDetector = None

from app.config import get_settings

logger = logging.getLogger(__name__)


class ContentModerationResult:
    """Result of content moderation check."""

    def __init__(
        self,
        safe: bool,
        score: float,
        scores: Dict[str, float],
        status: str = "approved"
    ):
        self.safe = safe
        self.score = score  # Overall NSFW score (0-1)
        self.scores = scores  # Detailed scores: porn, sexy, hentai, neutral, drawings
        self.status = status  # approved, rejected, flagged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "safe": self.safe,
            "score": self.score,
            "scores": self.scores,
            "status": self.status,
        }


class ContentModerator:
    """
    Content moderation using nsfwpy (local ML model).

    Categories detected:
    - porn: Pornographic images, sexual acts
    - sexy: Sexually explicit but not pornography
    - hentai: Hentai and pornographic drawings
    - drawings: Safe for work drawings
    - neutral: Safe for work neutral images
    """

    def __init__(self):
        self.settings = get_settings()
        self.enabled = self.settings.content_moderation_enabled and NSFWPY_AVAILABLE
        self.threshold = self.settings.nsfw_threshold
        self.auto_approve = self.settings.auto_approve_safe
        self.detector: Optional[NSFWDetector] = None

        if self.enabled:
            try:
                self.detector = NSFWDetector()
                logger.info("Content moderation enabled using nsfwpy")
            except Exception as e:
                logger.warning(f"Failed to initialize NSFW detector: {e}. Moderation disabled.")
                self.enabled = False
        else:
            if not NSFWPY_AVAILABLE:
                logger.warning("nsfwpy not installed. Install with: pip install nsfwpy")
            elif not self.settings.content_moderation_enabled:
                logger.info("Content moderation disabled in settings")

    def check_image(self, image_path: str) -> ContentModerationResult:
        """
        Check if an image is safe for public display.

        Args:
            image_path: Path to the image file

        Returns:
            ContentModerationResult with safety status and scores
        """
        if not self.enabled:
            # Moderation disabled - auto-approve
            return ContentModerationResult(
                safe=True,
                score=0.0,
                scores={},
                status="approved"
            )

        if not self.detector:
            return ContentModerationResult(
                safe=True,
                score=0.0,
                scores={},
                status="approved"
            )

        try:
            # Check if file exists
            path = Path(image_path)
            if not path.exists():
                logger.warning(f"Image file not found: {image_path}")
                return ContentModerationResult(
                    safe=True,
                    score=0.0,
                    scores={},
                    status="approved"  # Fail open for missing files
                )

            # Run nsfwpy detection
            result = self.detector.predict(str(path))

            # nsfwpy returns: {filename: {porn: X, sexy: Y, hentai: Z, drawings: W, neutral: V}}
            # Extract the first (only) result
            if isinstance(result, dict) and result:
                scores = list(result.values())[0] if result else {}
            else:
                scores = {}

            if not scores:
                logger.warning(f"Unexpected nsfwpy result format: {result}")
                return ContentModerationResult(
                    safe=True,
                    score=0.0,
                    scores={},
                    status="approved"
                )

            # Calculate overall NSFW score
            # porn + sexy + hentai = NSFW
            # drawings + neutral = safe
            nsfw_score = (
                scores.get("porn", 0) +
                scores.get("sexy", 0) +
                scores.get("hentai", 0)
            )

            # Determine status
            if nsfw_score >= self.threshold:
                status = "rejected"
                safe = False
            elif nsfw_score >= self.threshold * 0.7:
                status = "flagged"  # Close to threshold - may need review
                safe = self.auto_approve
            else:
                status = "approved"
                safe = True

            logger.info(
                f"Content moderation: {image_path} - "
                f"NSFW score: {nsfw_score:.3f}, status: {status}"
            )

            return ContentModerationResult(
                safe=safe,
                score=nsfw_score,
                scores=scores,
                status=status
            )

        except Exception as e:
            logger.error(f"Content moderation error for {image_path}: {e}")
            # Fail open - don't block uploads on errors
            return ContentModerationResult(
                safe=True,
                score=0.0,
                scores={"error": str(e)},
                status="approved"
            )

    def moderate_event_photo(
        self,
        db,
        photo,
        image_path: str
    ) -> Dict[str, Any]:
        """
        Run moderation on an EventPhoto and update the record.

        Args:
            db: Database session
            photo: EventPhoto model instance
            image_path: Full path to the image file

        Returns:
            Dict with moderation result
        """
        result = self.check_image(image_path)

        # Update photo record
        photo.moderation_status = result.status
        photo.moderation_score = result.score
        photo.moderation_scores_json = json.dumps(result.scores)
        photo.moderated_at = datetime.now(timezone.utc)

        db.commit()

        return result.to_dict()


# Singleton instance
_moderator: Optional[ContentModerator] = None


def get_moderator() -> ContentModerator:
    """Get or create the singleton ContentModerator instance."""
    global _moderator
    if _moderator is None:
        _moderator = ContentModerator()
    return _moderator


def moderate_image_file(image_path: str) -> ContentModerationResult:
    """
    Convenience function to moderate an image file.

    Args:
        image_path: Path to the image file

    Returns:
        ContentModerationResult
    """
    moderator = get_moderator()
    return moderator.check_image(image_path)
