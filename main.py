# ============================================================
# FILE: main.py
# ============================================================
#
# HINGLISH / ROMAN HINDI SHAYARI YOUTUBE SHORTS AUTOMATION
#
# FINAL PIPELINE:
#
#   Gemini
#      ↓
#   Original Roman Hindi Shayari
#      ↓
#   SEO ENGINE
#      ├── Title
#      ├── Description
#      ├── Search Queries
#      ├── YouTube Tags
#      └── Hashtags
#      ↓
#   5–7 sec Video
#      ↓
#   Times New Roman Regular
#      ↓
#   User Background
#      ↓
#   User Music
#      ↓
#   YouTube
#      ↓
#   Entertainment Category
#      ↓
#   UNLISTED
#
# ============================================================

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

import src.shayari_generator as shayari_generator

from src.shayari_video import create_video
from src.uploader import upload_short_to_youtube


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(
    __file__
).resolve().parent

OUTPUT_DIR = ROOT / "output"

HISTORY_FILE = ROOT / "content_history.json"

METADATA_DIR = OUTPUT_DIR / "metadata"


# ============================================================
# ENVIRONMENT CONFIG
# ============================================================

# ------------------------------------------------------------
# VIDEO
# ------------------------------------------------------------

VIDEO_MIN_DURATION = 5
VIDEO_MAX_DURATION = 7


# ------------------------------------------------------------
# YOUTUBE
# ------------------------------------------------------------

YOUTUBE_UPLOAD = (
    os.getenv(
        "YOUTUBE_UPLOAD",
        "true",
    ).lower()
    == "true"
)

# Entertainment category
YOUTUBE_CATEGORY_ID = os.getenv(
    "YOUTUBE_CATEGORY_ID",
    "24",
)


# ------------------------------------------------------------
# GEMINI MODELS
# ------------------------------------------------------------

DEFAULT_GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
]


def get_gemini_models() -> list[str]:
    """
    Read comma-separated Gemini models from environment.
    """

    raw = os.getenv(
        "GEMINI_MODELS",
        "",
    ).strip()

    if not raw:

        return DEFAULT_GEMINI_MODELS.copy()

    models = [
        item.strip()
        for item in raw.split(",")
        if item.strip()
    ]

    return models or DEFAULT_GEMINI_MODELS.copy()


GEMINI_MODELS = get_gemini_models()


# ------------------------------------------------------------
# RETRIES
# ------------------------------------------------------------

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
# HELPERS
# ============================================================

def switch_gemini_model(
    model: str,
) -> None:
    """
    Switch the active Gemini model.

    shayari_generator.py reads the global MODEL variable,
    so we update both the environment and module variable.
    """

    os.environ[
        "GEMINI_MODEL"
    ] = model

    shayari_generator.MODEL = model

    print(
        f"[GEMINI] Using model: {model}"
    )


def is_quota_error(
    error: Exception,
) -> bool:
    """
    Detect Gemini quota/rate-limit errors.
    """

    text = str(
        error
    ).lower()

    indicators = [
        "429",
        "resource_exhausted",
        "quota",
        "rate limit",
        "ratelimit",
        "too many requests",
        "generate requests per day",
    ]

    return any(
        indicator in text
        for indicator in indicators
    )


def choose_video_duration() -> int:
    """
    Pick ONLY 5, 6 or 7 seconds.

    No other duration is allowed.
    """

    duration = random.choice(
        [5, 6, 7]
    )

    print(
        f"[VIDEO] Selected duration: {duration}s"
    )

    return duration


# ============================================================
# CONTENT GENERATION
# ============================================================

def generate_content() -> dict:
    """
    Generate Shayari and complete SEO package.

    Returns:

        title
        shayari
        description
        queries
        tags
        hashtags
        seo
        _source
        _gemini_model
    """

    last_error = None

    # --------------------------------------------------------
    # Try all configured Gemini models
    # --------------------------------------------------------

    for model_index, model in enumerate(
        GEMINI_MODELS
    ):

        switch_gemini_model(
            model
        )

        try:

            print(
                "\n"
                + "=" * 60
            )

            print(
                f"[CONTENT] Generating with {model}"
            )

            print(
                "=" * 60
            )

            content = (
                shayari_generator.generate_shayari()
            )

            # ------------------------------------------------
            # Safety validation
            # ------------------------------------------------

            shayari = str(
                content.get(
                    "shayari",
                    "",
                )
            ).strip()

            title = str(
                content.get(
                    "title",
                    "",
                )
            ).strip()

            if not shayari:

                raise ValueError(
                    "Generated Shayari is empty."
                )

            if not title:

                raise ValueError(
                    "Generated title is empty."
                )

            if not shayari_generator.is_roman_hindi(
                shayari
            ):

                raise ValueError(
                    "Generated Shayari is not Roman Hindi."
                )

            # ------------------------------------------------
            # SEO validation
            # ------------------------------------------------

            required_fields = [
                "description",
                "queries",
                "tags",
                "hashtags",
            ]

            for field in required_fields:

                if field not in content:

                    raise ValueError(
                        f"SEO field missing: {field}"
                    )

            tags = content.get(
                "tags",
                [],
            )

            hashtags = content.get(
                "hashtags",
                [],
            )

            queries = content.get(
                "queries",
                [],
            )

            if not isinstance(
                tags,
                list,
            ):
                raise ValueError(
                    "SEO tags must be a list."
                )

            if not isinstance(
                hashtags,
                list,
            ):
                raise ValueError(
                    "SEO hashtags must be a list."
                )

            if not isinstance(
                queries,
                list,
            ):
                raise ValueError(
                    "SEO queries must be a list."
                )

            # ------------------------------------------------
            # 500-character YouTube tag safety
            # ------------------------------------------------

            seo_data = content.get(
                "seo",
                {},
            )

            tag_count = int(
                seo_data.get(
                    "tag_character_count",
                    0,
                )
            )

            if tag_count > 500:

                raise ValueError(
                    f"YouTube tags exceed 500 characters: "
                    f"{tag_count}"
                )

            # ------------------------------------------------
            # Final model information
            # ------------------------------------------------

            content[
                "_gemini_model"
            ] = model

            print(
                "\n[CONTENT SUCCESS]"
            )

            print(
                f"Title: {title}"
            )

            print(
                f"Source: "
                f"{content.get('_source', 'unknown')}"
            )

            print(
                f"Queries: {len(queries)}"
            )

            print(
                f"Tags: {len(tags)}"
            )

            print(
                f"Hashtags: {len(hashtags)}"
            )

            print(
                f"Tag characters: {tag_count}"
            )

            return content

        except Exception as exc:

            last_error = exc

            print(
                f"\n[CONTENT ERROR] {exc}"
            )

            # ------------------------------------------------
            # Quota error
            # ------------------------------------------------

            if is_quota_error(
                exc
            ):

                print(
                    "[GEMINI] Quota/rate limit detected."
                )

                if (
                    model_index
                    < len(GEMINI_MODELS) - 1
                ):

                    next_model = GEMINI_MODELS[
                        model_index + 1
                    ]

                    print(
                        f"[GEMINI] Switching to: "
                        f"{next_model}"
                    )

                    continue

                print(
                    "[GEMINI] All configured models "
                    "exhausted."
                )

                break

            # ------------------------------------------------
            # Other errors
            # ------------------------------------------------

            if (
                model_index
                < len(GEMINI_MODELS) - 1
            ):

                print(
                    "[GEMINI] Trying next model..."
                )

                continue

    # ========================================================
    # FINAL LOCAL FALLBACK
    # ========================================================

    print(
        "\n[CONTENT] Using local fallback."
    )

    history = (
        shayari_generator.load_history()
    )

    fallback = (
        shayari_generator.get_fallback(
            history
        )
    )

    fallback = (
        shayari_generator.add_seo(
            fallback
        )
    )

    fallback[
        "_source"
    ] = "local_fallback"

    fallback[
        "_gemini_model"
    ] = "local_fallback"

    if last_error:

        print(
            f"[CONTENT] Last Gemini error: "
            f"{last_error}"
        )

    return fallback


# ============================================================
# SAVE METADATA
# ============================================================

def save_metadata(
    content: dict,
    video_result: dict,
) -> Path:
    """
    Save complete metadata JSON.

    This makes it easy to inspect exactly what was generated
    before/after YouTube upload.
    """

    METADATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata = {
        "title": content.get(
            "title",
            "",
        ),

        "shayari": content.get(
            "shayari",
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

        "tags": content.get(
            "tags",
            [],
        ),

        "hashtags": content.get(
            "hashtags",
            [],
        ),

        "seo": content.get(
            "seo",
            {},
        ),

        "video": video_result,

        "youtube": {
            "category_id": YOUTUBE_CATEGORY_ID,
            "category": "Entertainment",
            "privacy_status": "unlisted",
        },

        "source": content.get(
            "_source",
            "",
        ),

        "gemini_model": content.get(
            "_gemini_model",
            "",
        ),

        "created_at": int(
            time.time()
        ),
    }

    timestamp = int(
        time.time()
    )

    metadata_path = (
        METADATA_DIR
        / f"metadata_{timestamp}.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"[METADATA] Saved: {metadata_path}"
    )

    return metadata_path


# ============================================================
# SAVE CONTENT HISTORY
# ============================================================

def save_content_history(
    content: dict,
) -> None:
    """
    Save generated Shayari history.

    Used to reduce duplicate poetry.
    """

    shayari_generator.save_history(
        content
    )

    print(
        f"[HISTORY] Updated: {HISTORY_FILE}"
    )


# ============================================================
# VIDEO GENERATION
# ============================================================

def generate_video_file(
    content: dict,
) -> tuple[Path, dict]:
    """
    Generate final 5–7 second video.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    duration = choose_video_duration()

    timestamp = int(
        time.time()
    )

    output_path = (
        OUTPUT_DIR
        / f"shayari_short_{timestamp}.mp4"
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "VIDEO GENERATION"
    )

    print(
        "=" * 60
    )

    print(
        f"Duration: {duration}s"
    )

    print(
        "Resolution: 1080x1920"
    )

    print(
        "Font: Times New Roman Regular"
    )

    print(
        "Text: Static"
    )

    print(
        "Voice: None"
    )

    print(
        "Animation: None"
    )

    result = create_video(
        content["shayari"],
        str(output_path),
        duration,
    )

    if not output_path.exists():

        raise RuntimeError(
            "Video generation reported success "
            "but MP4 does not exist."
        )

    if output_path.stat().st_size < 10_000:

        raise RuntimeError(
            "Generated MP4 is suspiciously small."
        )

    # --------------------------------------------------------
    # Force final duration validation
    # --------------------------------------------------------

    actual_duration = int(
        result.get(
            "duration",
            duration,
        )
    )

    if actual_duration not in {
        5,
        6,
        7,
    }:

        raise RuntimeError(
            f"Invalid video duration: "
            f"{actual_duration}s"
        )

    print(
        f"\n[VIDEO SUCCESS] {output_path}"
    )

    return (
        output_path,
        result,
    )


# ============================================================
# YOUTUBE UPLOAD
# ============================================================

def upload_to_youtube(
    content: dict,
    video_path: Path,
) -> dict:
    """
    Upload using generated SEO metadata.

    IMPORTANT:
        Category = Entertainment (24)
        Privacy = UNLISTED
    """

    if not YOUTUBE_UPLOAD:

        print(
            "\n[YOUTUBE] Upload disabled."
        )

        return {
            "uploaded": False,
            "reason": "YOUTUBE_UPLOAD=false",
        }

    title = content[
        "title"
    ]

    description = content[
        "description"
    ]

    tags = content[
        "tags"
    ]

    # --------------------------------------------------------
    # Explicit Entertainment category
    # --------------------------------------------------------

    os.environ[
        "YOUTUBE_CATEGORY_ID"
    ] = YOUTUBE_CATEGORY_ID

    # --------------------------------------------------------
    # Explicit unlisted protection
    # --------------------------------------------------------

    os.environ[
        "YOUTUBE_PRIVACY_STATUS"
    ] = "unlisted"

    print(
        "\n"
        + "=" * 60
    )

    print(
        "YOUTUBE UPLOAD"
    )

    print(
        "=" * 60
    )

    print(
        f"Title: {title}"
    )

    print(
        "Category: Entertainment"
    )

    print(
        "Category ID: 24"
    )

    print(
        "Privacy: UNLISTED"
    )

    print(
        f"Tags: {len(tags)}"
    )

    print(
        f"Description: "
        f"{len(description)} characters"
    )

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    result = upload_short_to_youtube(
        str(video_path),
        title,
        description,
        tags=tags,
        thumbnail_path=None,
    )

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    privacy_status = str(
        result.get(
            "privacy_status",
            "",
        )
    ).lower()

    if privacy_status:

        if privacy_status != "unlisted":

            raise RuntimeError(
                "SAFETY STOP: YouTube upload did not "
                f"return UNLISTED status. "
                f"Received: {privacy_status}"
            )

    print(
        "\n[YOUTUBE SUCCESS]"
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return result


# ============================================================
# PRINT FINAL SUMMARY
# ============================================================

def print_final_summary(
    content: dict,
    video_path: Path,
    video_result: dict,
    upload_result: dict | None,
) -> None:

    print(
        "\n"
        + "=" * 70
    )

    print(
        "FINAL SHAYARI SHORT SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"\nTITLE:\n{content['title']}"
    )

    print(
        f"\nSHAYARI:\n{content['shayari']}"
    )

    print(
        "\nVIDEO:"
    )

    print(
        f"Path       : {video_path}"
    )

    print(
        f"Duration   : "
        f"{video_result.get('duration')} sec"
    )

    print(
        "Resolution : 1080x1920"
    )

    print(
        "Font       : Times New Roman Regular"
    )

    print(
        "Animation  : None"
    )

    print(
        "Voice      : None"
    )

    print(
        "\nYOUTUBE:"
    )

    print(
        "Category   : Entertainment"
    )

    print(
        "Category ID: 24"
    )

    print(
        "Privacy    : UNLISTED"
    )

    print(
        "\nSEO:"
    )

    print(
        f"Queries    : "
        f"{len(content.get('queries', []))}"
    )

    print(
        f"Tags       : "
        f"{len(content.get('tags', []))}"
    )

    print(
        f"Hashtags   : "
        f"{len(content.get('hashtags', []))}"
    )

    print(
        f"Tag chars  : "
        f"{content.get('seo', {}).get('tag_character_count', 0)}"
    )

    if upload_result:

        print(
            "\nUPLOAD RESULT:"
        )

        print(
            json.dumps(
                upload_result,
                ensure_ascii=False,
                indent=2,
            )
        )

    print(
        "\n"
        + "=" * 70
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline() -> None:
    """
    Complete automation pipeline.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\n"
        + "#" * 70
    )

    print(
        "# HINGLISH SHAYARI SHORTS AUTOMATION"
    )

    print(
        "#" * 70
    )

    print(
        "\nFINAL CONFIG:"
    )

    print(
        "Video        : 5–7 seconds"
    )

    print(
        "Resolution   : 1080x1920"
    )

    print(
        "Font         : Times New Roman Regular"
    )

    print(
        "Category     : Entertainment (24)"
    )

    print(
        "Privacy      : UNLISTED"
    )

    print(
        "Voice        : NONE"
    )

    print(
        "Animation    : NONE"
    )

    # --------------------------------------------------------
    # Whole-pipeline retries
    # --------------------------------------------------------

    last_error = None

    for attempt in range(
        1,
        PIPELINE_RETRIES + 1,
    ):

        print(
            "\n"
            + "-" * 70
        )

        print(
            f"PIPELINE ATTEMPT "
            f"{attempt}/{PIPELINE_RETRIES}"
        )

        print(
            "-" * 70
        )

        try:

            # ------------------------------------------------
            # 1. Generate content + SEO
            # ------------------------------------------------

            content = (
                generate_content()
            )

            # ------------------------------------------------
            # 2. Generate video
            # ------------------------------------------------

            video_path, video_result = (
                generate_video_file(
                    content
                )
            )

            # ------------------------------------------------
            # 3. Save metadata
            # ------------------------------------------------

            save_metadata(
                content,
                video_result,
            )

            # ------------------------------------------------
            # 4. Save history
            # ------------------------------------------------

            save_content_history(
                content
            )

            # ------------------------------------------------
            # 5. Upload
            # ------------------------------------------------

            upload_result = (
                upload_to_youtube(
                    content,
                    video_path,
                )
            )

            # ------------------------------------------------
            # 6. Final summary
            # ------------------------------------------------

            print_final_summary(
                content,
                video_path,
                video_result,
                upload_result,
            )

            print(
                "\n[SUCCESS] Automation completed."
            )

            return

        except Exception as exc:

            last_error = exc

            print(
                "\n"
                + "!" * 70
            )

            print(
                f"[PIPELINE ERROR] {exc}"
            )

            print(
                "!" * 70
            )

            if attempt < PIPELINE_RETRIES:

                print(
                    f"\nRetrying in "
                    f"{RETRY_DELAY} seconds..."
                )

                time.sleep(
                    RETRY_DELAY
                )

    # --------------------------------------------------------
    # All attempts failed
    # --------------------------------------------------------

    raise RuntimeError(
        "Automation failed after "
        f"{PIPELINE_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_pipeline()
