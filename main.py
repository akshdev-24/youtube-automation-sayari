# ============================================================
# FILE: main.py
# ============================================================
#
# HINGLISH SHAYARI YOUTUBE SHORTS AUTOMATION
#
# PIPELINE:
#
# Gemini
#    ↓
# Shayari
#    ↓
# SEO title
#    ↓
# Queries
#    ↓
# Hashtags
#    ↓
# Tags
#    ↓
# Video
#    ↓
# YouTube UNLISTED
#
# ============================================================

from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# PROJECT PATH
# ============================================================

ROOT_DIR = Path(
    __file__
).resolve().parent

OUTPUT_DIR = (
    ROOT_DIR / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "shayari-automation"
)


# ============================================================
# IMPORT GENERATOR MODULE
# ============================================================

import src.shayari_generator as shayari_generator

from src.shayari_video import (
    create_video,
)

from src.uploader import (
    upload_short_to_youtube,
)


# ============================================================
# CONFIG
# ============================================================

VIDEO_DURATION = int(
    os.getenv(
        "SHAYARI_DURATION",
        "15",
    )
)

YOUTUBE_UPLOAD = (
    os.getenv(
        "YOUTUBE_UPLOAD",
        "true",
    ).lower()
    == "true"
)

PIPELINE_RETRIES = int(
    os.getenv(
        "PIPELINE_RETRIES",
        "3",
    )
)

RETRY_DELAY = int(
    os.getenv(
        "RETRY_DELAY",
        "15",
    )
)


# ============================================================
# GEMINI MODELS
# ============================================================

def get_gemini_models() -> list[str]:

    raw = os.getenv(
        "GEMINI_MODELS",
        "",
    ).strip()

    if raw:

        models = [
            item.strip()
            for item in raw.split(",")
            if item.strip()
        ]

    else:

        models = [
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
        ]

    # Remove duplicates while
    # preserving order.
    unique = []

    for model in models:

        if model not in unique:
            unique.append(model)

    return unique


GEMINI_MODELS = (
    get_gemini_models()
)


# ============================================================
# SWITCH MODEL
# ============================================================

def switch_gemini_model(
    model: str,
) -> None:

    os.environ[
        "GEMINI_MODEL"
    ] = model

    shayari_generator.MODEL = (
        model
    )

    logger.info(
        f"Gemini model selected: {model}"
    )


# ============================================================
# QUOTA ERROR
# ============================================================

def is_quota_error(
    exc: Exception,
) -> bool:

    text = str(
        exc
    ).lower()

    indicators = [
        "429",
        "resource_exhausted",
        "quota",
        "rate limit",
        "too many requests",
        "generaterequestsperday",
    ]

    return any(
        indicator in text
        for indicator in indicators
    )


# ============================================================
# GENERATE CONTENT
# ============================================================

def generate_content() -> dict:

    logger.info(
        "Starting Shayari content generation..."
    )

    last_error = None

    for model in GEMINI_MODELS:

        switch_gemini_model(
            model
        )

        try:

            result = (
                shayari_generator
                .generate_shayari()
            )

            if not result:
                raise RuntimeError(
                    "Generator returned empty result."
                )

            shayari = str(
                result.get(
                    "shayari",
                    "",
                )
            ).strip()

            title = str(
                result.get(
                    "title",
                    "",
                )
            ).strip()

            description = str(
                result.get(
                    "description",
                    "",
                )
            ).strip()

            if not shayari:

                raise RuntimeError(
                    "Generated Shayari is empty."
                )

            if not title:

                raise RuntimeError(
                    "Generated title is empty."
                )

            if not description:

                raise RuntimeError(
                    "Generated description is empty."
                )

            # Final Roman-Hindi safety check.
            if re.search(
                r"[\u0900-\u097F]",
                shayari,
            ):

                raise RuntimeError(
                    "Generated Shayari contains Devanagari."
                )

            result[
                "_gemini_model"
            ] = model

            logger.info(
                "Content generation successful."
            )

            return result

        except Exception as exc:

            last_error = exc

            logger.error(
                f"Model {model} failed: {exc}"
            )

            if is_quota_error(
                exc
            ):

                logger.warning(
                    f"Quota/rate limit on {model}. "
                    "Trying next model..."
                )

                continue

            # Other errors:
            # try next configured model too.
            continue

    # ========================================================
    # ALL GEMINI MODELS FAILED
    # ========================================================

    logger.warning(
        "All configured Gemini models failed."
    )

    logger.warning(
        "Using local fallback content."
    )

    result = (
        shayari_generator
        .local_fallback(
            shayari_generator.load_history()
        )
    )

    result[
        "_gemini_model"
    ] = "local_fallback"

    if last_error:

        result[
            "_last_gemini_error"
        ] = str(last_error)

    return result


# ============================================================
# SAFE FILENAME
# ============================================================

def safe_filename(
    text: str,
) -> str:

    text = str(
        text or "shayari"
    )

    text = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        text,
    )

    text = re.sub(
        r"_+",
        "_",
        text,
    )

    return text.strip(
        "_"
    )[:70] or "shayari"


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    data: dict,
    path: Path,
) -> None:

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ============================================================
# GENERATE VIDEO
# ============================================================

def generate_video_file(
    content: dict,
) -> Path:

    title = content[
        "title"
    ]

    filename = (
        safe_filename(title)
        + "_short.mp4"
    )

    output_path = (
        OUTPUT_DIR
        / filename
    )

    logger.info(
        f"Generating video: {output_path}"
    )

    # IMPORTANT:
    # Positional arguments intentionally used.
    # This keeps compatibility with the existing
    # create_video(text, output_path, duration)
    # function.
    result = create_video(
        content[
            "shayari"
        ],
        str(output_path),
        VIDEO_DURATION,
    )

    result_path = Path(
        result
    )

    if not result_path.exists():

        raise RuntimeError(
            "Video generator reported success "
            "but output file does not exist."
        )

    return result_path


# ============================================================
# SAVE METADATA
# ============================================================

def save_metadata(
    content: dict,
    video_path: Path,
) -> Path:

    metadata_path = (
        video_path.with_suffix(
            ".json"
        )
    )

    metadata = {
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "video": {
            "filename": video_path.name,
            "duration": VIDEO_DURATION,
            "width": 1080,
            "height": 1920,
            "aspect_ratio": "9:16",
        },

        "content": {
            "shayari": content.get(
                "shayari",
                "",
            ),

            "title": content.get(
                "title",
                "",
            ),

            "description": content.get(
                "description",
                "",
            ),

            "queries": content.get(
                "queries",
                [],
            ),

            "hashtags": content.get(
                "hashtags",
                [],
            ),

            "tags": content.get(
                "tags",
                [],
            ),
        },

        "generation": {
            "source": content.get(
                "_source",
                "",
            ),

            "gemini_model": content.get(
                "_gemini_model",
                content.get(
                    "_model",
                    "",
                ),
            ),
        },

        "youtube": {
            "upload_enabled": YOUTUBE_UPLOAD,
            "privacy_status": "unlisted",
        },
    }

    save_json(
        metadata,
        metadata_path,
    )

    logger.info(
        f"Metadata saved: {metadata_path}"
    )

    return metadata_path


# ============================================================
# SAVE HISTORY
# ============================================================

def save_content_history(
    content: dict,
    video_path: Path,
) -> None:

    history_item = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "video": video_path.name,

        "shayari": content.get(
            "shayari",
            "",
        ),

        "title": content.get(
            "title",
            "",
        ),

        "description": content.get(
            "description",
            "",
        ),

        "queries": content.get(
            "queries",
            [],
        ),

        "hashtags": content.get(
            "hashtags",
            [],
        ),

        "tags": content.get(
            "tags",
            [],
        ),

        "source": content.get(
            "_source",
            "",
        ),

        "gemini_model": content.get(
            "_gemini_model",
            content.get(
                "_model",
                "",
            ),
        ),
    }

    # The generator already handles
    # history. Do not duplicate the same
    # content there.
    #
    # We only record if the generator's
    # history doesn't already contain it.

    history = (
        shayari_generator
        .load_history()
    )

    current_shayari = (
        content.get(
            "shayari",
            "",
        ).strip()
    )

    already_exists = any(
        str(
            item.get(
                "shayari",
                "",
            )
        ).strip()
        == current_shayari
        for item in history
    )

    if not already_exists:

        shayari_generator.save_history(
            history_item
        )


# ============================================================
# YOUTUBE UPLOAD
# ============================================================

def upload_to_youtube(
    content: dict,
    video_path: Path,
) -> dict | None:

    if not YOUTUBE_UPLOAD:

        logger.info(
            "YOUTUBE_UPLOAD=false. "
            "Skipping upload."
        )

        return None

    title = content.get(
        "title",
        "Heart Touching Shayari",
    )

    description = content.get(
        "description",
        "",
    )

    tags = content.get(
        "tags",
        [],
    )

    # --------------------------------------------------------
    # FINAL SAFETY:
    # Never allow this pipeline to publish public.
    # --------------------------------------------------------

    logger.info(
        "YouTube privacy: UNLISTED"
    )

    try:

        result = upload_short_to_youtube(
            str(video_path),
            title,
            description,
            tags=tags,
        )

    except TypeError:

        # Compatibility fallback if uploader
        # has an older function signature.
        result = upload_short_to_youtube(
            str(video_path),
            title,
            description,
            tags,
        )

    if not result:

        raise RuntimeError(
            "YouTube uploader returned empty result."
        )

    privacy = str(
        result.get(
            "privacy_status",
            result.get(
                "privacyStatus",
                "",
            ),
        )
    ).lower()

    # If uploader provides privacy status,
    # verify it.
    if privacy and privacy != "unlisted":

        raise RuntimeError(
            "SAFETY STOP: YouTube upload did not "
            f"return unlisted status. Got: {privacy}"
        )

    logger.info(
        "YouTube upload completed."
    )

    return result


# ============================================================
# ONE COMPLETE PIPELINE
# ============================================================

def run_pipeline() -> dict:

    logger.info("")
    logger.info(
        "=" * 70
    )
    logger.info(
        "HINGLISH SHAYARI SHORTS AUTOMATION"
    )
    logger.info(
        "=" * 70
    )

    logger.info(
        f"Duration: {VIDEO_DURATION}s"
    )

    logger.info(
        "Resolution: 1080x1920"
    )

    logger.info(
        "Aspect ratio: 9:16"
    )

    logger.info(
        "TTS: DISABLED"
    )

    logger.info(
        "Text animation: DISABLED"
    )

    logger.info(
        "Extra card/UI: DISABLED"
    )

    logger.info(
        f"YouTube upload: {YOUTUBE_UPLOAD}"
    )

    logger.info(
        "YouTube privacy: UNLISTED"
    )

    # --------------------------------------------------------
    # 1. CONTENT
    # --------------------------------------------------------

    content = generate_content()

    logger.info("")
    logger.info(
        "GENERATED SHAYARI:"
    )
    logger.info(
        content["shayari"]
    )

    logger.info("")
    logger.info(
        f"TITLE: {content['title']}"
    )

    logger.info("")
    logger.info(
        "QUERIES:"
    )

    for query in content.get(
        "queries",
        [],
    ):

        logger.info(
            f"  - {query}"
        )

    logger.info("")
    logger.info(
        "HASHTAGS:"
    )

    logger.info(
        " ".join(
            content.get(
                "hashtags",
                [],
            )
        )
    )

    logger.info("")
    logger.info(
        "TAGS:"
    )

    logger.info(
        ", ".join(
            content.get(
                "tags",
                [],
            )
        )
    )

    # --------------------------------------------------------
    # 2. VIDEO
    # --------------------------------------------------------

    video_path = (
        generate_video_file(
            content
        )
    )

    # --------------------------------------------------------
    # 3. METADATA
    # --------------------------------------------------------

    metadata_path = (
        save_metadata(
            content,
            video_path,
        )
    )

    # --------------------------------------------------------
    # 4. HISTORY
    # --------------------------------------------------------

    save_content_history(
        content,
        video_path,
    )

    # --------------------------------------------------------
    # 5. YOUTUBE
    # --------------------------------------------------------

    upload_result = (
        upload_to_youtube(
            content,
            video_path,
        )
    )

    # --------------------------------------------------------
    # 6. RESULT
    # --------------------------------------------------------

    result = {
        "success": True,

        "video": str(
            video_path
        ),

        "metadata": str(
            metadata_path
        ),

        "title": content[
            "title"
        ],

        "shayari": content[
            "shayari"
        ],

        "queries": content.get(
            "queries",
            [],
        ),

        "hashtags": content.get(
            "hashtags",
            [],
        ),

        "tags": content.get(
            "tags",
            [],
        ),

        "gemini_model": content.get(
            "_gemini_model",
            "",
        ),

        "youtube": upload_result,
    }

    logger.info("")
    logger.info(
        "=" * 70
    )
    logger.info(
        "PIPELINE COMPLETED SUCCESSFULLY"
    )
    logger.info(
        "=" * 70
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    last_error = None

    for attempt in range(
        1,
        PIPELINE_RETRIES + 1,
    ):

        logger.info(
            f"Pipeline attempt "
            f"{attempt}/{PIPELINE_RETRIES}"
        )

        try:

            result = run_pipeline()

            result_path = (
                OUTPUT_DIR
                / "latest_result.json"
            )

            save_json(
                result,
                result_path,
            )

            print("")
            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                )
            )

            return 0

        except Exception as exc:

            last_error = exc

            logger.exception(
                "Pipeline failed."
            )

            if attempt >= PIPELINE_RETRIES:

                break

            delay = (
                RETRY_DELAY
                * attempt
            )

            delay += random.uniform(
                1,
                5,
            )

            logger.info(
                f"Retrying entire pipeline "
                f"in {delay:.1f}s..."
            )

            time.sleep(
                delay
            )

    logger.error(
        ""
    )

    logger.error(
        "=" * 70
    )

    logger.error(
        "PIPELINE FAILED"
    )

    logger.error(
        "=" * 70
    )

    if last_error:

        logger.error(
            str(last_error)
        )

    return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )
