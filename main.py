# ============================================================
# FILE: main.py
# HINGLISH / ROMAN HINDI SHAYARI SHORTS AUTOMATION
# ============================================================

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

from src.shayari_generator import (
    generate_shayari,
    save_history,
)

from src.shayari_video import create_video

from src.uploader import upload_short_to_youtube


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_FILE = BASE_DIR / "content_history.json"


# ============================================================
# SETTINGS
# ============================================================

VIDEO_DURATION = int(
    os.getenv("SHAYARI_DURATION", "15")
)

YOUTUBE_UPLOAD = (
    os.getenv("YOUTUBE_UPLOAD", "true").lower()
    == "true"
)

PIPELINE_RETRIES = int(
    os.getenv("PIPELINE_RETRIES", "3")
)

RETRY_DELAY = int(
    os.getenv("RETRY_DELAY", "15")
)


# ============================================================
# GEMINI MODEL SWAP
# ============================================================
#
# Models are tried in this order.
#
# If one model:
#   - gives 429
#   - quota exhausted
#   - invalid response
#   - temporary failure
#
# the generator can move to the next model.
#
# These can also be overridden from GitHub Actions.
#
# Example:
#
# GEMINI_MODELS="gemini-3.6-flash,gemini-3.7-flash,gemini-3.8-flash"
#
# ============================================================

DEFAULT_GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
]


def get_gemini_models():
    """
    Read Gemini model priority from environment.

    Example:
        GEMINI_MODELS=gemini-3.6-flash,gemini-3.7-flash
    """

    raw = os.getenv(
        "GEMINI_MODELS",
        ""
    ).strip()

    if not raw:
        return DEFAULT_GEMINI_MODELS.copy()

    models = []

    for model in raw.split(","):

        model = model.strip()

        if model and model not in models:
            models.append(model)

    if not models:
        return DEFAULT_GEMINI_MODELS.copy()

    return models


GEMINI_MODELS = get_gemini_models()


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

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def validate_roman_hindi(text):
    """
    Prevent accidental Devanagari/Urdu script.

    Shayari must remain Roman Hindi / Hinglish.
    """

    if not text:
        return False

    # Devanagari Unicode range
    for char in text:

        code = ord(char)

        if 0x0900 <= code <= 0x097F:
            return False

    # Arabic / Urdu range
    for char in text:

        code = ord(char)

        if 0x0600 <= code <= 0x06FF:
            return False

    return True


def safe_filename(text):
    """
    Convert title into a safe filename.
    """

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_- "
    )

    cleaned = "".join(
        c if c in allowed else "_"
        for c in text
    )

    cleaned = "_".join(
        cleaned.split()
    )

    return cleaned[:80] or "shayari_short"


# ============================================================
# GEMINI MODEL CONFIG
# ============================================================

def set_model_environment(model):
    """
    Tell shayari_generator which Gemini model to use.

    The generator reads GEMINI_MODEL.
    """

    os.environ["GEMINI_MODEL"] = model

    logger.info(
        "🔄 Gemini model selected: %s",
        model
    )


# ============================================================
# GENERATE SHAYARI
# ============================================================

def generate_content_with_model_swapping():
    """
    Try Gemini models one by one.

    Model 1 fails
        ↓
    Model 2
        ↓
    Model 3
        ↓
    fallback inside generator
    """

    last_error = None

    for index, model in enumerate(
        GEMINI_MODELS,
        start=1
    ):

        logger.info(
            "🤖 Gemini model %d/%d: %s",
            index,
            len(GEMINI_MODELS),
            model
        )

        set_model_environment(model)

        try:

            content = generate_shayari()

            if not content:
                raise RuntimeError(
                    "Gemini returned empty content."
                )

            if not isinstance(content, dict):
                raise RuntimeError(
                    "Gemini response is not a dictionary."
                )

            shayari = str(
                content.get("shayari", "")
            ).strip()

            if not shayari:
                raise RuntimeError(
                    "Generated Shayari is empty."
                )

            if not validate_roman_hindi(shayari):
                raise RuntimeError(
                    "Generated text contains "
                    "Devanagari/Urdu characters."
                )

            logger.info(
                "✅ Shayari generated successfully "
                "using %s",
                model
            )

            content["_gemini_model"] = model

            return content

        except Exception as exc:

            last_error = exc

            error_text = str(exc)

            logger.warning(
                "⚠️ Model %s failed: %s",
                model,
                error_text
            )

            quota_error = (
                "429" in error_text
                or "RESOURCE_EXHAUSTED"
                in error_text
                or "quota"
                in error_text.lower()
                or "rate limit"
                in error_text.lower()
            )

            if quota_error:

                logger.warning(
                    "🚫 Quota/rate limit detected "
                    "for %s.",
                    model
                )

            if index < len(GEMINI_MODELS):

                logger.info(
                    "➡️ Switching Gemini model: "
                    "%s → %s",
                    model,
                    GEMINI_MODELS[index]
                )

                time.sleep(2)

    # ========================================================
    # ALL MODELS FAILED
    # ========================================================

    logger.error(
        "❌ All Gemini models failed."
    )

    if last_error:
        logger.error(
            "Last Gemini error: %s",
            last_error
        )

    logger.info(
        "🛟 Asking generator for fallback Shayari..."
    )

    # Final fallback call.
    #
    # The generator itself contains a local
    # original Shayari fallback pool.
    #
    set_model_environment(
        GEMINI_MODELS[-1]
    )

    fallback_content = generate_shayari()

    if not fallback_content:
        raise RuntimeError(
            "Gemini and local fallback both failed."
        )

    fallback_content[
        "_gemini_model"
    ] = "LOCAL_FALLBACK"

    return fallback_content


# ============================================================
# SAVE METADATA
# ============================================================

def save_metadata(
    content,
    video_path
):

    metadata = {
        "created_at": utc_now(),

        "title": content.get(
            "title",
            "Dard Bhari Shayari 💔"
        ),

        "description": content.get(
            "description",
            ""
        ),

        "hashtags": content.get(
            "hashtags",
            []
        ),

        "tags": content.get(
            "tags",
            []
        ),

        "shayari": content.get(
            "shayari",
            ""
        ),

        "video": str(
            video_path
        ),

        "gemini_model": content.get(
            "_gemini_model",
            "unknown"
        ),
    }

    metadata_path = (
        Path(video_path)
        .with_suffix(".json")
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(
        "📝 Metadata saved: %s",
        metadata_path
    )

    return metadata_path


# ============================================================
# SAVE HISTORY SAFELY
# ============================================================

def update_history(content):

    try:

        save_history(
            content
        )

        logger.info(
            "📚 Content history updated."
        )

    except TypeError:

        # Compatibility with generators
        # expecting different signatures.

        try:

            history = []

            if HISTORY_FILE.exists():

                with open(
                    HISTORY_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)

                    if isinstance(
                        data,
                        list
                    ):
                        history = data

            history.append(
                {
                    "created_at": utc_now(),
                    "title": content.get(
                        "title",
                        ""
                    ),
                    "shayari": content.get(
                        "shayari",
                        ""
                    ),
                }
            )

            history = history[-100:]

            with open(
                HISTORY_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    history,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            logger.info(
                "📚 History saved using "
                "compatibility mode."
            )

        except Exception as exc:

            logger.warning(
                "⚠️ Could not save history: %s",
                exc
            )

    except Exception as exc:

        logger.warning(
            "⚠️ History update failed: %s",
            exc
        )


# ============================================================
# CREATE VIDEO
# ============================================================

def generate_video_file(
    content,
    attempt
):

    title = content.get(
        "title",
        "Dard Bhari Shayari"
    )

    filename = (
        f"{safe_filename(title)}"
        f"_{int(time.time())}"
        f"_{attempt}.mp4"
    )

    output_path = (
        OUTPUT_DIR / filename
    )

    logger.info(
        "🎬 Creating video..."
    )

    logger.info(
        "📐 Target: 1080x1920"
    )

    logger.info(
        "⏱️ Duration: %s seconds",
        VIDEO_DURATION
    )

    # IMPORTANT:
    #
    # Positional arguments are intentional.
    #
    # This avoids:
    #
    # create_video() got an unexpected
    # keyword argument 'shayari'
    #
    result = create_video(
        content["shayari"],
        str(output_path),
        VIDEO_DURATION,
    )

    # Some implementations return
    # the output path.
    #
    # Others return None after creating it.

    if result:

        result_path = Path(
            str(result)
        )

        if result_path.exists():

            output_path = result_path

    if not output_path.exists():

        raise RuntimeError(
            "Video generation returned successfully "
            "but output MP4 was not found."
        )

    size_mb = (
        output_path.stat().st_size
        / (1024 * 1024)
    )

    if size_mb < 0.1:

        raise RuntimeError(
            "Generated video is suspiciously small."
        )

    logger.info(
        "✅ Video created: %s",
        output_path
    )

    logger.info(
        "📦 Video size: %.2f MB",
        size_mb
    )

    return output_path


# ============================================================
# YOUTUBE UPLOAD
# ============================================================

def upload_video(
    content,
    video_path
):

    if not YOUTUBE_UPLOAD:

        logger.info(
            "⏭️ YouTube upload disabled."
        )

        return None

    title = content.get(
        "title",
        "Dard Bhari Shayari 💔"
    )

    description = content.get(
        "description",
        ""
    )

    tags = content.get(
        "tags",
        []
    )

    logger.info(
        "📤 Uploading to YouTube..."
    )

    logger.info(
        "🔒 Privacy: UNLISTED"
    )

    result = upload_short_to_youtube(
        video_path=str(
            video_path
        ),
        title=title,
        description=description,
        tags=tags,
        thumbnail_path=None,
    )

    if not result:

        raise RuntimeError(
            "YouTube uploader returned empty result."
        )

    privacy = str(
        result.get(
            "privacy_status",
            ""
        )
    ).lower()

    if privacy and privacy != "unlisted":

        raise RuntimeError(
            "SAFETY CHECK FAILED: "
            f"YouTube privacy is '{privacy}', "
            "not 'unlisted'."
        )

    logger.info(
        "✅ YouTube upload successful."
    )

    logger.info(
        "🔒 Uploaded as UNLISTED."
    )

    if result.get("video_id"):

        logger.info(
            "🆔 Video ID: %s",
            result["video_id"]
        )

    if result.get("shorts_url"):

        logger.info(
            "🔗 Shorts URL: %s",
            result["shorts_url"]
        )

    return result


# ============================================================
# COMPLETE PIPELINE
# ============================================================

def run_pipeline():

    logger.info(
        "=" * 60
    )

    logger.info(
        "🚀 HINGLISH SHAYARI AUTOMATION STARTED"
    )

    logger.info(
        "=" * 60
    )

    logger.info(
        "🤖 Gemini model priority:"
    )

    for number, model in enumerate(
        GEMINI_MODELS,
        start=1
    ):

        logger.info(
            "   %d. %s",
            number,
            model
        )

    logger.info(
        "🎥 Duration: %ss",
        VIDEO_DURATION
    )

    logger.info(
        "📤 YouTube upload: %s",
        YOUTUBE_UPLOAD
    )

    logger.info(
        "🔒 YouTube privacy: UNLISTED"
    )

    last_error = None

    for attempt in range(
        1,
        PIPELINE_RETRIES + 1
    ):

        logger.info(
            ""
        )

        logger.info(
            "🔁 PIPELINE ATTEMPT %d/%d",
            attempt,
            PIPELINE_RETRIES
        )

        try:

            # ------------------------------------------------
            # 1. Generate Shayari
            # ------------------------------------------------

            content = (
                generate_content_with_model_swapping()
            )

            logger.info(
                "✍️ Shayari:"
            )

            logger.info(
                "%s",
                content["shayari"]
            )

            logger.info(
                "🏷️ Title: %s",
                content.get(
                    "title",
                    ""
                )
            )

            logger.info(
                "🤖 Model: %s",
                content.get(
                    "_gemini_model",
                    "unknown"
                )
            )

            # ------------------------------------------------
            # 2. Validate Roman Hindi
            # ------------------------------------------------

            if not validate_roman_hindi(
                content["shayari"]
            ):

                raise RuntimeError(
                    "Shayari contains unsupported script."
                )

            # ------------------------------------------------
            # 3. Create Video
            # ------------------------------------------------

            video_path = generate_video_file(
                content,
                attempt
            )

            # ------------------------------------------------
            # 4. Save Metadata
            # ------------------------------------------------

            metadata_path = save_metadata(
                content,
                video_path
            )

            # ------------------------------------------------
            # 5. Save History
            # ------------------------------------------------

            update_history(
                content
            )

            # ------------------------------------------------
            # 6. Upload YouTube
            # ------------------------------------------------

            upload_result = upload_video(
                content,
                video_path
            )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            logger.info(
                ""
            )

            logger.info(
                "=" * 60
            )

            logger.info(
                "🎉 PIPELINE COMPLETED SUCCESSFULLY"
            )

            logger.info(
                "=" * 60
            )

            logger.info(
                "🎬 Video: %s",
                video_path
            )

            logger.info(
                "📝 Metadata: %s",
                metadata_path
            )

            if upload_result:

                logger.info(
                    "📺 YouTube: %s",
                    upload_result.get(
                        "shorts_url",
                        upload_result.get(
                            "url",
                            "uploaded"
                        )
                    )
                )

            return {
                "success": True,
                "video_path": str(
                    video_path
                ),
                "metadata_path": str(
                    metadata_path
                ),
                "upload": upload_result,
            }

        except Exception as exc:

            last_error = exc

            logger.exception(
                "❌ Pipeline attempt %d failed.",
                attempt
            )

            if attempt >= PIPELINE_RETRIES:

                break

            logger.info(
                "⏳ Waiting %s seconds "
                "before next pipeline attempt...",
                RETRY_DELAY
            )

            time.sleep(
                RETRY_DELAY
            )

    # ========================================================
    # COMPLETE FAILURE
    # ========================================================

    logger.error(
        ""
    )

    logger.error(
        "=" * 60
    )

    logger.error(
        "💥 PIPELINE FAILED"
    )

    logger.error(
        "=" * 60
    )

    if last_error:

        logger.error(
            "Last error: %s",
            last_error
        )

    return {
        "success": False,
        "error": str(
            last_error
        ) if last_error else "Unknown error",
    }


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        result = run_pipeline()

        if result.get("success"):

            return 0

        return 1

    except KeyboardInterrupt:

        logger.warning(
            "🛑 Process interrupted by user."
        )

        return 130

    except Exception as exc:

        logger.exception(
            "💥 Fatal error: %s",
            exc
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )
