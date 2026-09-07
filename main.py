# ============================================================
# FILE: main.py
# HINGLISH / ROMAN HINDI SHAYARI SHORTS AUTOMATION
# ============================================================
#
# Pipeline:
#   1. Generate Shayari + SEO metadata
#   2. Create 1080x1920 Shorts video
#   3. Save metadata
#   4. Save content history
#   5. Upload to YouTube as UNLISTED
#
# No TTS
# No voice
# No Devanagari
# No extra overlay/card/page
# User background + user music only
# ============================================================

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from src.shayari_generator import generate_shayari, save_history
from src.shayari_video import create_video
from src.uploader import upload_short_to_youtube


# ============================================================
# CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_FILE = ROOT_DIR / "content_history.json"

# ------------------------------------------------------------
# Video
# ------------------------------------------------------------

VIDEO_DURATION = int(
    os.getenv("SHAYARI_DURATION", "15")
)

# ------------------------------------------------------------
# YouTube
# ------------------------------------------------------------

YOUTUBE_UPLOAD = (
    os.getenv("YOUTUBE_UPLOAD", "true").lower()
    == "true"
)

# Safety: videos are ALWAYS uploaded as unlisted.
YOUTUBE_PRIVACY = "unlisted"

# YouTube category:
# 22 = People & Blogs
YOUTUBE_CATEGORY_ID = os.getenv(
    "YOUTUBE_CATEGORY_ID",
    "22"
)

# ------------------------------------------------------------
# Retry configuration
# ------------------------------------------------------------

PIPELINE_RETRIES = int(
    os.getenv("PIPELINE_RETRIES", "3")
)

RETRY_DELAY = int(
    os.getenv("RETRY_DELAY", "10")
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("shayari-automation")


# ============================================================
# HELPERS
# ============================================================

def now_utc():
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def safe_filename(text: str, max_length: int = 80) -> str:
    """
    Convert text into a safe filename.
    """

    if not text:
        return "shayari"

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "-_ "
    )

    cleaned = "".join(
        char if char in allowed else ""
        for char in text
    )

    cleaned = "_".join(cleaned.split())

    if not cleaned:
        cleaned = "shayari"

    return cleaned[:max_length]


def validate_roman_hindi(text: str) -> bool:
    """
    Reject Devanagari characters.

    The project intentionally uses Roman Hindi / Hinglish.
    """

    if not text:
        return False

    for char in text:
        if "\u0900" <= char <= "\u097F":
            return False

    return True


def validate_content(content: dict) -> None:
    """
    Validate generated Shayari content before video creation.
    """

    if not isinstance(content, dict):
        raise ValueError(
            "Generator did not return a valid dictionary."
        )

    required_fields = [
        "title",
        "shayari",
        "description",
        "hashtags",
        "tags",
    ]

    for field in required_fields:
        if field not in content:
            raise ValueError(
                f"Missing required content field: {field}"
            )

    shayari = str(content["shayari"]).strip()

    if not shayari:
        raise ValueError(
            "Generated Shayari is empty."
        )

    # Absolutely no Devanagari.
    for field in [
        "title",
        "shayari",
        "description",
    ]:
        value = str(content.get(field, ""))

        if not validate_roman_hindi(value):
            raise ValueError(
                f"Devanagari detected in field: {field}"
            )


def normalize_metadata(content: dict) -> dict:
    """
    Normalize generated metadata so the uploader receives
    predictable values.
    """

    title = str(
        content.get("title", "Heart Touching Shayari")
    ).strip()

    description = str(
        content.get("description", "")
    ).strip()

    shayari = str(
        content.get("shayari", "")
    ).strip()

    hashtags = content.get("hashtags", [])
    tags = content.get("tags", [])

    if isinstance(hashtags, str):
        hashtags = [
            item.strip()
            for item in hashtags.split()
            if item.strip()
        ]

    if isinstance(tags, str):
        tags = [
            item.strip()
            for item in tags.split(",")
            if item.strip()
        ]

    # Ensure hashtag formatting.
    formatted_hashtags = []

    for hashtag in hashtags:
        hashtag = str(hashtag).strip()

        if not hashtag:
            continue

        if not hashtag.startswith("#"):
            hashtag = "#" + hashtag

        formatted_hashtags.append(hashtag)

    # Remove duplicate hashtags.
    formatted_hashtags = list(
        dict.fromkeys(formatted_hashtags)
    )

    # Keep a clean, useful hashtag count.
    formatted_hashtags = formatted_hashtags[:8]

    # Remove duplicate tags.
    cleaned_tags = []

    for tag in tags:
        tag = str(tag).strip()

        if tag:
            cleaned_tags.append(tag)

    cleaned_tags = list(
        dict.fromkeys(cleaned_tags)
    )

    content["title"] = title
    content["description"] = description
    content["shayari"] = shayari
    content["hashtags"] = formatted_hashtags
    content["tags"] = cleaned_tags

    return content


def build_description(content: dict) -> str:
    """
    Build final YouTube description.

    First lines contain the most important information.
    """

    description = str(
        content.get("description", "")
    ).strip()

    hashtags = content.get("hashtags", [])

    hashtag_text = " ".join(
        str(tag).strip()
        for tag in hashtags
        if str(tag).strip()
    )

    parts = []

    if description:
        parts.append(description)

    if hashtag_text:
        parts.append("")
        parts.append(hashtag_text)

    return "\n".join(parts).strip()


def save_metadata(
    content: dict,
    video_path: Path,
    video_id: str | None = None,
) -> Path:
    """
    Save generated metadata alongside the video.
    """

    metadata = {
        "generated_at": now_utc(),
        "title": content.get("title"),
        "shayari": content.get("shayari"),
        "description": content.get("description"),
        "hashtags": content.get("hashtags", []),
        "tags": content.get("tags", []),
        "category": content.get("category"),
        "video_file": str(video_path),
        "video_id": video_id,
        "youtube_privacy": YOUTUBE_PRIVACY,
    }

    metadata_path = video_path.with_suffix(".json")

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(
        "Metadata saved: %s",
        metadata_path,
    )

    return metadata_path


def find_latest_video() -> Path | None:
    """
    Find the most recently generated MP4.
    """

    videos = list(
        OUTPUT_DIR.glob("*.mp4")
    )

    if not videos:
        return None

    return max(
        videos,
        key=lambda path: path.stat().st_mtime,
    )


# ============================================================
# GENERATE CONTENT
# ============================================================

def generate_content() -> dict:
    """
    Generate fresh Roman Hindi Shayari + SEO metadata.
    """

    logger.info(
        "Generating fresh Shayari..."
    )

    content = generate_shayari()

    content = normalize_metadata(content)

    validate_content(content)

    logger.info(
        "Generated title: %s",
        content["title"],
    )

    logger.info(
        "Shayari length: %d characters",
        len(content["shayari"]),
    )

    return content


# ============================================================
# CREATE VIDEO
# ============================================================

def generate_video_file(
    content: dict,
) -> Path:
    """
    Create the actual 1080x1920 Shorts video.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"{timestamp}_"
        f"{safe_filename(content['title'])}.mp4"
    )

    output_path = OUTPUT_DIR / filename

    logger.info(
        "Creating video: %s",
        output_path,
    )

    result = create_video(
        shayari=content["shayari"],
        output_path=str(output_path),
        duration=VIDEO_DURATION,
    )

    # Support either:
    # - create_video returning a path
    # - create_video returning None while writing output_path

    if result:
        result_path = Path(str(result))

        if result_path.exists():
            output_path = result_path

    if not output_path.exists():
        raise FileNotFoundError(
            "Video generation completed but output "
            f"file was not found: {output_path}"
        )

    file_size_mb = (
        output_path.stat().st_size
        / (1024 * 1024)
    )

    if file_size_mb < 0.1:
        raise ValueError(
            "Generated video file is suspiciously small."
        )

    logger.info(
        "Video created successfully: %.2f MB",
        file_size_mb,
    )

    return output_path


# ============================================================
# YOUTUBE UPLOAD
# ============================================================

def upload_video(
    content: dict,
    video_path: Path,
) -> dict | None:
    """
    Upload video to YouTube as UNLISTED.

    The uploader itself also contains a privacy safety check.
    """

    if not YOUTUBE_UPLOAD:
        logger.info(
            "YOUTUBE_UPLOAD=false -> "
            "Skipping YouTube upload."
        )
        return None

    description = build_description(
        content
    )

    logger.info(
        "Uploading to YouTube..."
    )

    logger.info(
        "Privacy status: %s",
        YOUTUBE_PRIVACY.upper(),
    )

    result = upload_short_to_youtube(
        video_path=str(video_path),
        title=content["title"],
        description=description,
        tags=content.get("tags", []),
        thumbnail_path=None,
    )

    if not result:
        raise RuntimeError(
            "YouTube uploader returned no result."
        )

    # Extra safety validation.
    returned_privacy = str(
        result.get(
            "privacy_status",
            YOUTUBE_PRIVACY,
        )
    ).lower()

    if returned_privacy != "unlisted":
        raise RuntimeError(
            "SAFETY ERROR: YouTube upload did not "
            f"return UNLISTED status. Got: "
            f"{returned_privacy}"
        )

    logger.info(
        "YouTube upload successful."
    )

    logger.info(
        "Video ID: %s",
        result.get("video_id"),
    )

    logger.info(
        "Privacy: UNLISTED"
    )

    if result.get("url"):
        logger.info(
            "URL: %s",
            result["url"],
        )

    return result


# ============================================================
# HISTORY
# ============================================================

def record_history(
    content: dict,
    video_path: Path,
    upload_result: dict | None = None,
) -> None:
    """
    Save generation/upload information to content history.
    """

    history_item = {
        "generated_at": now_utc(),
        "title": content.get("title"),
        "shayari": content.get("shayari"),
        "category": content.get("category"),
        "video_file": str(video_path),
        "youtube": {
            "uploaded": bool(upload_result),
            "video_id": (
                upload_result.get("video_id")
                if upload_result
                else None
            ),
            "privacy_status": (
                upload_result.get(
                    "privacy_status"
                )
                if upload_result
                else None
            ),
            "url": (
                upload_result.get("url")
                if upload_result
                else None
            ),
        },
    }

    save_history(history_item)

    logger.info(
        "Content history updated."
    )


# ============================================================
# SINGLE PIPELINE RUN
# ============================================================

def run_pipeline() -> dict:
    """
    Run one complete automation cycle.
    """

    logger.info("=" * 65)
    logger.info(
        "HINGLISH SHAYARI SHORTS AUTOMATION"
    )
    logger.info("=" * 65)

    logger.info(
        "Video duration: %s seconds",
        VIDEO_DURATION,
    )

    logger.info(
        "YouTube upload: %s",
        YOUTUBE_UPLOAD,
    )

    logger.info(
        "YouTube privacy: UNLISTED"
    )

    # --------------------------------------------------------
    # STEP 1 — Generate Shayari
    # --------------------------------------------------------

    content = generate_content()

    # --------------------------------------------------------
    # STEP 2 — Create video
    # --------------------------------------------------------

    video_path = generate_video_file(
        content
    )

    # --------------------------------------------------------
    # STEP 3 — Save metadata before upload
    # --------------------------------------------------------

    save_metadata(
        content=content,
        video_path=video_path,
    )

    # --------------------------------------------------------
    # STEP 4 — Upload YouTube
    # --------------------------------------------------------

    upload_result = upload_video(
        content=content,
        video_path=video_path,
    )

    # --------------------------------------------------------
    # STEP 5 — Save final metadata with video ID
    # --------------------------------------------------------

    save_metadata(
        content=content,
        video_path=video_path,
        video_id=(
            upload_result.get("video_id")
            if upload_result
            else None
        ),
    )

    # --------------------------------------------------------
    # STEP 6 — History
    # --------------------------------------------------------

    record_history(
        content=content,
        video_path=video_path,
        upload_result=upload_result,
    )

    logger.info("=" * 65)
    logger.info(
        "PIPELINE COMPLETED SUCCESSFULLY"
    )
    logger.info("=" * 65)

    return {
        "content": content,
        "video_path": str(video_path),
        "upload": upload_result,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    """
    Application entry point.
    """

    last_error = None

    for attempt in range(
        1,
        PIPELINE_RETRIES + 1,
    ):
        try:
            logger.info(
                "Pipeline attempt %d/%d",
                attempt,
                PIPELINE_RETRIES,
            )

            result = run_pipeline()

            # ------------------------------------------------
            # Final summary
            # ------------------------------------------------

            print()
            print("=" * 65)
            print("SUCCESS")
            print("=" * 65)

            print(
                f"Title: {result['content']['title']}"
            )

            print(
                f"Video: {result['video_path']}"
            )

            upload = result.get("upload")

            if upload:
                print(
                    f"YouTube ID: "
                    f"{upload.get('video_id')}"
                )

                print(
                    "YouTube Privacy: UNLISTED"
                )

                if upload.get("url"):
                    print(
                        f"YouTube URL: "
                        f"{upload['url']}"
                    )

            else:
                print(
                    "YouTube upload: SKIPPED"
                )

            print("=" * 65)

            return 0

        except KeyboardInterrupt:
            logger.warning(
                "Pipeline interrupted by user."
            )
            return 130

        except Exception as exc:
            last_error = exc

            logger.error(
                "Pipeline attempt %d failed: %s",
                attempt,
                exc,
            )

            logger.debug(
                traceback.format_exc()
            )

            if attempt < PIPELINE_RETRIES:
                logger.info(
                    "Retrying in %d seconds...",
                    RETRY_DELAY,
                )

                time.sleep(RETRY_DELAY)

    # --------------------------------------------------------
    # All retries failed
    # --------------------------------------------------------

    logger.error(
        "All %d pipeline attempts failed.",
        PIPELINE_RETRIES,
    )

    if last_error:
        logger.error(
            "Final error: %s",
            last_error,
        )

    return 1


# ============================================================
# SCRIPT ENTRY
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
