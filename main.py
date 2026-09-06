# ============================================================
# FILE: main.py
# HINGLISH SHAYARI SHORTS AUTOMATION
# ============================================================
#
# FLOW:
#   1. Generate original Hinglish Shayari using Gemini
#   2. Generate title / description / hashtags / tags
#   3. Create 1080x1920 static Shayari video
#   4. Save metadata + history
#   5. Upload to YouTube Shorts
#
# NO:
#   ❌ TTS
#   ❌ Voice
#   ❌ Text animation
#   ❌ Devanagari Hindi
#
# YES:
#   ✅ Roman Hindi / Hinglish
#   ✅ Static Shayari
#   ✅ Background image/video
#   ✅ Background music
#   ✅ YouTube Shorts
# ============================================================

import json
import os
import sys
import time
from pathlib import Path

from src.shayari_generator import generate_shayari, save_history
from src.shayari_video import create_video
from src.uploader import upload_short_to_youtube


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT_DIR / "output"
HISTORY_FILE = ROOT_DIR / "content_history.json"


# ------------------------------------------------------------
# ENV CONFIG
# ------------------------------------------------------------

YOUTUBE_UPLOAD = os.getenv("YOUTUBE_UPLOAD", "true").lower() == "true"

# Video duration in seconds
VIDEO_DURATION = int(os.getenv("SHAYARI_DURATION", "15"))

# Retry count for the complete pipeline
PIPELINE_RETRIES = int(os.getenv("PIPELINE_RETRIES", "2"))


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------

def log(message: str):
    """Simple timestamped logger."""

    now = time.strftime("%H:%M:%S")

    print(f"[{now}] {message}")


# ------------------------------------------------------------
# DIRECTORY SETUP
# ------------------------------------------------------------

def prepare_directories():
    """Create required directories."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log(f"📁 Output directory: {OUTPUT_DIR}")


# ------------------------------------------------------------
# PRINT CONTENT
# ------------------------------------------------------------

def print_content(content: dict):
    """Print generated content in a readable format."""

    print("\n")
    print("=" * 70)
    print("📝 GENERATED SHAYARI")
    print("=" * 70)

    print(content.get("shayari", "").strip())

    print("\n" + "-" * 70)

    print(f"🎬 TITLE:")
    print(content.get("title", ""))

    print("\n📄 DESCRIPTION:")
    print(content.get("description", ""))

    print("\n🏷️ HASHTAGS:")
    print(" ".join(content.get("hashtags", [])))

    print("\n🔖 TAGS:")
    print(", ".join(content.get("tags", [])))

    print("\n📂 CATEGORY:")
    print(content.get("category", ""))

    print("=" * 70)


# ------------------------------------------------------------
# SAVE METADATA
# ------------------------------------------------------------

def save_metadata(content: dict, video_path: Path) -> Path:
    """Save generated content metadata beside the video."""

    metadata = {
        "shayari": content.get("shayari", ""),
        "title": content.get("title", ""),
        "description": content.get("description", ""),
        "hashtags": content.get("hashtags", []),
        "tags": content.get("tags", []),
        "category": content.get("category", ""),
        "video": str(video_path),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": "youtube_shorts",
    }

    metadata_path = video_path.with_suffix(".json")

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    log(f"💾 Metadata saved: {metadata_path}")

    return metadata_path


# ------------------------------------------------------------
# VALIDATE CONTENT
# ------------------------------------------------------------

def validate_content(content: dict):
    """Basic safety/quality validation before creating video."""

    if not isinstance(content, dict):
        raise ValueError("Gemini returned invalid content.")

    shayari = content.get("shayari", "").strip()

    if not shayari:
        raise ValueError("Generated Shayari is empty.")

    title = content.get("title", "").strip()

    if not title:
        raise ValueError("Generated title is empty.")

    # Reject Devanagari Hindi.
    for char in shayari:
        if "\u0900" <= char <= "\u097F":
            raise ValueError(
                "Generated Shayari contains Devanagari Hindi. "
                "Only Roman/Hinglish text is allowed."
            )

    # Keep title within YouTube limit.
    if len(title) > 100:
        content["title"] = title[:97] + "..."

    # Make sure hashtags exist.
    if not isinstance(content.get("hashtags"), list):
        content["hashtags"] = []

    if not isinstance(content.get("tags"), list):
        content["tags"] = []

    # Ensure Shorts hashtag.
    hashtags = content["hashtags"]

    if "#Shorts" not in hashtags and "#shorts" not in hashtags:
        hashtags.append("#Shorts")

    return content


# ------------------------------------------------------------
# GENERATE VIDEO
# ------------------------------------------------------------

def build_video(content: dict, run_id: str) -> Path:
    """Generate the final 1080x1920 Shorts video."""

    video_path = OUTPUT_DIR / f"shayari_{run_id}.mp4"

    log("🎬 Creating Shorts video...")
    log(f"📐 Resolution: 1080x1920")
    log(f"⏱️ Duration: {VIDEO_DURATION}s")
    log("🎙️ Voice: OFF")
    log("✨ Text animation: OFF")
    log("🎵 Background music: ON")

    create_video(
        shayari=content["shayari"],
        output_path=video_path,
        duration=VIDEO_DURATION,
    )

    if not video_path.exists():
        raise RuntimeError("Video generation failed.")

    if video_path.stat().st_size < 10_000:
        raise RuntimeError("Generated video file is suspiciously small.")

    log(f"✅ Video created: {video_path}")

    return video_path


# ------------------------------------------------------------
# YOUTUBE UPLOAD
# ------------------------------------------------------------

def upload_youtube(content: dict, video_path: Path):
    """Upload generated video to YouTube Shorts."""

    if not YOUTUBE_UPLOAD:
        log("ℹ️ YOUTUBE_UPLOAD=false")
        log("⏭️ YouTube upload skipped.")

        return None

    log("📤 Uploading to YouTube...")

    video_id = upload_short_to_youtube(
        video_path=video_path,
        title=content["title"],
        description=content["description"],
        tags=content.get("tags", []),
        thumbnail_path=None,
    )

    if video_id:
        log("✅ YouTube upload successful!")
        log(f"🔗 Video ID: {video_id}")
        log(f"📺 https://www.youtube.com/shorts/{video_id}")

    return video_id


# ------------------------------------------------------------
# SINGLE PIPELINE RUN
# ------------------------------------------------------------

def run_pipeline():
    """Run the complete Shayari automation pipeline."""

    prepare_directories()

    run_id = time.strftime("%Y%m%d_%H%M%S")

    log("=" * 70)
    log("💔 HINGLISH SHAYARI SHORTS FACTORY")
    log("=" * 70)

    # --------------------------------------------------------
    # STEP 1 — Generate Shayari
    # --------------------------------------------------------

    log("🤖 Generating original Hinglish Shayari...")

    content = generate_shayari()

    content = validate_content(content)

    print_content(content)

    # --------------------------------------------------------
    # STEP 2 — Create video
    # --------------------------------------------------------

    video_path = build_video(
        content=content,
        run_id=run_id,
    )

    # --------------------------------------------------------
    # STEP 3 — Save metadata
    # --------------------------------------------------------

    save_metadata(
        content=content,
        video_path=video_path,
    )

    # --------------------------------------------------------
    # STEP 4 — Save history
    # --------------------------------------------------------

    try:
        save_history(content)
        log("📚 Content history updated.")
    except Exception as exc:
        # History failure should not destroy an already-created video.
        log(f"⚠️ Could not update history: {exc}")

    # --------------------------------------------------------
    # STEP 5 — YouTube
    # --------------------------------------------------------

    video_id = None

    try:
        video_id = upload_youtube(
            content=content,
            video_path=video_path,
        )

    except Exception as exc:

        # Upload failure should not delete the generated video.
        log("❌ YouTube upload failed.")
        log(f"   Error: {exc}")
        log("💾 Generated video has been preserved.")

        if YOUTUBE_UPLOAD:
            raise

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("✅ PIPELINE COMPLETE")
    print("=" * 70)

    print(f"🎬 Video: {video_path}")

    if video_id:
        print(f"📺 YouTube: https://www.youtube.com/shorts/{video_id}")
    else:
        print("📺 YouTube: Upload skipped / not completed")

    print("=" * 70)

    return video_path


# ------------------------------------------------------------
# RETRY WRAPPER
# ------------------------------------------------------------

def run_with_retry():
    """Run pipeline with limited retries."""

    last_error = None

    for attempt in range(1, PIPELINE_RETRIES + 2):

        try:

            log(
                f"🚀 Pipeline attempt "
                f"{attempt}/{PIPELINE_RETRIES + 1}"
            )

            return run_pipeline()

        except KeyboardInterrupt:

            log("🛑 Process stopped by user.")
            return None

        except Exception as exc:

            last_error = exc

            log(
                f"❌ Attempt {attempt} failed: {exc}"
            )

            if attempt >= PIPELINE_RETRIES + 1:
                break

            wait_seconds = min(
                30 * attempt,
                120,
            )

            log(
                f"⏳ Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError(
        f"Pipeline failed after retries: {last_error}"
    )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    try:

        run_with_retry()

        return 0

    except KeyboardInterrupt:

        print("\n🛑 Stopped.")

        return 130

    except Exception as exc:

        print("\n")
        print("=" * 70)
        print("❌ PIPELINE FAILED")
        print("=" * 70)
        print(str(exc))
        print("=" * 70)

        return 1


if __name__ == "__main__":
    sys.exit(main())
