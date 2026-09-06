import os
import re
import sys
import json
import datetime
import time
import traceback
from pathlib import Path

from src.generator import (
    generate_curriculum,
    generate_lesson_content,
    text_to_speech,
    generate_visuals,
    create_video,
    YOUR_NAME,
)

from src.uploader import upload_to_youtube


# ============================================================
# CONFIGURATION
# ============================================================

CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")

# One lesson = 1 long video + 1 Short
LESSONS_PER_RUN = 1


# ============================================================
# CONTENT PLAN
# ============================================================

def get_content_plan():
    """
    Load existing content plan.

    If content_plan.json doesn't exist or is invalid,
    generate a fresh Hindi Motivation curriculum.
    """

    if not CONTENT_PLAN_FILE.exists():
        print("📄 content_plan.json not found.")
        print("🤖 Generating new Hindi Motivation content plan...")

        new_plan = generate_curriculum()

        with open(CONTENT_PLAN_FILE, "w", encoding="utf-8") as f:
            json.dump(
                new_plan,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(f"✅ New curriculum saved to {CONTENT_PLAN_FILE}")

        return new_plan

    try:
        with open(CONTENT_PLAN_FILE, "r", encoding="utf-8") as f:
            plan = json.load(f)

        if (
            not plan.get("lessons")
            or not isinstance(plan["lessons"], list)
        ):
            raise ValueError(
                "Invalid or empty lesson plan detected."
            )

        return plan

    except Exception as e:

        print(
            f"❌ ERROR loading content plan: {e}"
        )

        print(
            "🔄 Regenerating content plan..."
        )

        new_plan = generate_curriculum()

        with open(CONTENT_PLAN_FILE, "w", encoding="utf-8") as f:
            json.dump(
                new_plan,
                f,
                indent=2,
                ensure_ascii=False
            )

        return new_plan


def update_content_plan(plan):
    """
    Save updated content plan.
    """

    with open(
        CONTENT_PLAN_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            plan,
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value, fallback=""):
    """
    Safely convert a value into clean text.
    """

    if value is None:
        return fallback

    return str(value).strip()


def clean_hashtags(value):
    """
    Convert hashtags into a clean string.
    """

    if isinstance(value, list):

        result = []

        for tag in value:

            tag = clean_text(tag)

            if not tag:
                continue

            if not tag.startswith("#"):
                tag = "#" + tag

            result.append(tag)

        return " ".join(result)

    value = clean_text(value)

    if not value:
        return ""

    return value


def clean_tags(value):
    """
    Keep tags clean and YouTube-friendly.

    Supports:
    - list
    - tuple
    - comma separated string
    """

    if isinstance(value, (list, tuple)):

        tags = value

    elif isinstance(value, str):

        tags = value.split(",")

    else:

        tags = []

    cleaned = []

    seen = set()

    for tag in tags:

        tag = clean_text(tag)

        if not tag:
            continue

        tag = tag.replace("#", "").strip()

        if not tag:
            continue

        key = tag.lower()

        if key in seen:
            continue

        seen.add(key)

        cleaned.append(tag)

    return cleaned


# ============================================================
# LESSON PRODUCTION
# ============================================================

def produce_lesson_videos(lesson):

    lesson_title = clean_text(
        lesson.get("title"),
        "आज खुद पर विश्वास करो"
    )

    chapter = clean_text(
        lesson.get("chapter"),
        "1"
    )

    part = clean_text(
        lesson.get("part"),
        "1"
    )

    print("\n" + "=" * 70)
    print(f"▶️ Starting Lesson: {lesson_title}")
    print(f"📚 Chapter: {chapter}")
    print(f"📌 Part: {part}")
    print("=" * 70)

    # --------------------------------------------------------
    # UNIQUE ID
    # --------------------------------------------------------

    chapter_safe = re.sub(
        r"[^\w]+",
        "_",
        chapter
    ).strip("_")

    part_safe = re.sub(
        r"[^\w]+",
        "_",
        part
    ).strip("_")

    title_safe = re.sub(
        r"[^\w]+",
        "_",
        lesson_title
    ).strip("_")[:50]

    unique_id = (
        f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        f"_{chapter_safe}"
        f"_{part_safe}"
        f"_{title_safe}"
    )

    # --------------------------------------------------------
    # GENERATE AI CONTENT
    # --------------------------------------------------------

    print("\n🤖 Generating Hindi Motivation content...")

    lesson_content = generate_lesson_content(
        lesson_title
    )

    if not lesson_content:
        raise ValueError(
            "Gemini returned empty lesson content."
        )

    # --------------------------------------------------------
    # YOUTUBE METADATA
    # --------------------------------------------------------

    youtube_data = lesson_content.get(
        "youtube",
        {}
    )

    if not isinstance(youtube_data, dict):
        youtube_data = {}

    youtube_title = clean_text(
        youtube_data.get("title"),
        lesson_title
    )

    youtube_description = clean_text(
        youtube_data.get("description"),
        ""
    )

    youtube_tags = clean_tags(
        youtube_data.get("tags", [])
    )

    youtube_hashtags = clean_hashtags(
        youtube_data.get("hashtags", [])
    )

    thumbnail_text = clean_text(
        youtube_data.get("thumbnail_text"),
        lesson_title
    )

    # --------------------------------------------------------
    # FALLBACK TAGS
    # --------------------------------------------------------

    if not youtube_tags:

        youtube_tags = [
            "hindi motivation",
            "motivational video hindi",
            "hindi motivational video",
            "motivation in hindi",
            "success motivation",
            "life motivation",
            "self improvement hindi",
            "motivational quotes hindi",
            "positive thinking hindi",
            "success quotes hindi",
        ]

    # --------------------------------------------------------
    # FALLBACK HASHTAGS
    # --------------------------------------------------------

    if not youtube_hashtags:

        youtube_hashtags = (
            "#HindiMotivation "
            "#Motivation "
            "#MotivationalQuotes "
            "#Success "
            "#SelfImprovement"
        )

    print("\n📊 Generated YouTube Metadata")
    print("----------------------------------------")
    print(f"TITLE: {youtube_title}")
    print(f"TAGS: {youtube_tags}")
    print(f"HASHTAGS: {youtube_hashtags}")
    print(f"THUMBNAIL: {thumbnail_text}")
    print("----------------------------------------")

    # ========================================================
    # LONG FORM VIDEO
    # ========================================================

    print("\n🎬 Producing LONG-FORM video...")

    long_slides = lesson_content.get(
        "long_form_slides",
        []
    )

    if not isinstance(long_slides, list):
        long_slides = []

    if not long_slides:

        raise ValueError(
            "No long_form_slides generated."
        )

    # --------------------------------------------------------
    # INTRO
    # --------------------------------------------------------

    intro_slide = {
        "title": youtube_title,
        "content": (
            "Hindi Motivation • "
            f"Chapter {chapter} • Part {part}"
        )
    }

    # --------------------------------------------------------
    # OUTRO
    # --------------------------------------------------------

    outro_slide = {
        "title": "खुद पर विश्वास रखो ❤️",
        "content": (
            f"{YOUR_NAME} के साथ रोज़ motivation के लिए "
            "चैनल को Subscribe करें!\n\n"
            f"{youtube_hashtags}"
        )
    }

    all_slides = (
        [intro_slide]
        + long_slides
        + [outro_slide]
    )

    # --------------------------------------------------------
    # SLIDE VOICE
    # --------------------------------------------------------

    slide_scripts = []

    intro_script = (
        f"नमस्ते दोस्तों। "
        f"आज की इस Hindi Motivation video में "
        f"हम बात करेंगे — {youtube_title} के बारे में। "
        "अगर आप अपनी जिंदगी में आगे बढ़ना चाहते हैं, "
        "तो इस वीडियो को अंत तक जरूर सुनिए।"
    )

    slide_scripts.append(
        intro_script
    )

    for slide in long_slides:

        content = clean_text(
            slide.get("content"),
            ""
        )

        if content:
            slide_scripts.append(content)

    outro_script = (
        "अगर इस वीडियो ने आपको थोड़ी भी motivation दी है, "
        "तो वीडियो को Like करें, "
        "चैनल को Subscribe करें "
        "और इसे अपने किसी दोस्त के साथ जरूर शेयर करें। "
        "याद रखिए — शुरुआत छोटी हो सकती है, "
        "लेकिन आपका सपना बड़ा होना चाहिए।"
    )

    slide_scripts.append(
        outro_script
    )

    # --------------------------------------------------------
    # CREATE AUDIO
    # --------------------------------------------------------

    slide_audio_paths = []

    for i, script in enumerate(
        slide_scripts
    ):

        audio_path = (
            OUTPUT_DIR
            / f"audio_long_{unique_id}_{i+1}.mp3"
        )

        print(
            f"🎙️ Creating Hindi voice {i+1}/{len(slide_scripts)}..."
        )

        wav_path = text_to_speech(
            script,
            audio_path
        )

        slide_audio_paths.append(
            wav_path
        )

    print(
        f"🎧 Total long-form audio files: "
        f"{len(slide_audio_paths)}"
    )

    # --------------------------------------------------------
    # CREATE VISUALS
    # --------------------------------------------------------

    slide_dir = (
        OUTPUT_DIR
        / f"slides_long_{unique_id}"
    )

    slide_paths = []

    for i, slide in enumerate(
        all_slides
    ):

        path = generate_visuals(
            output_dir=slide_dir,
            video_type="long",
            slide_content=slide,
            slide_number=i + 1,
            total_slides=len(all_slides)
        )

        slide_paths.append(path)

    # --------------------------------------------------------
    # CREATE LONG VIDEO
    # --------------------------------------------------------

    long_video_path = (
        OUTPUT_DIR
        / f"long_video_{unique_id}.mp4"
    )

    print(
        f"🎥 Creating long video: "
        f"{long_video_path}"
    )

    create_video(
        slide_paths,
        slide_audio_paths,
        long_video_path,
        "long"
    )

    if not long_video_path.exists():

        raise FileNotFoundError(
            "Long video was not created."
        )

    # --------------------------------------------------------
    # LONG THUMBNAIL
    # --------------------------------------------------------

    print("🖼️ Creating long-form thumbnail...")

    long_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type="long",
        thumbnail_title=thumbnail_text
    )

    if not long_thumb_path or not Path(
        long_thumb_path
    ).exists():

        raise FileNotFoundError(
            "Long-form thumbnail was not created."
        )

    # ========================================================
    # SHORT VIDEO
    # ========================================================

    print("\n" + "-" * 70)
    print("📱 Producing SHORT video...")
    print("-" * 70)

    short_highlight = clean_text(
        lesson_content.get(
            "short_form_highlight"
        ),
        ""
    )

    if not short_highlight:

        short_highlight = (
            "अगर जिंदगी बदलनी है, "
            "तो सबसे पहले खुद पर विश्वास करना सीखो।"
        )

    # --------------------------------------------------------
    # SHORT SCRIPT
    # --------------------------------------------------------

    short_script = (
        "रुकिए! "
        "अगर आप अपनी जिंदगी में कुछ बड़ा करना चाहते हैं, "
        "तो यह बात हमेशा याद रखिए।\n\n"
        f"{short_highlight}\n\n"
        "ऐसी ही powerful motivation के लिए "
        "चैनल को Subscribe करें।"
    )

    short_audio_mp3_path = (
        OUTPUT_DIR
        / f"short_audio_{unique_id}.mp3"
    )

    print("🎙️ Creating Hindi Short voice...")

    short_audio_path = text_to_speech(
        short_script,
        short_audio_mp3_path
    )

    # --------------------------------------------------------
    # SHORT VISUAL
    # --------------------------------------------------------

    short_slide_dir = (
        OUTPUT_DIR
        / f"slides_short_{unique_id}"
    )

    short_slide_content = {

        "title": "आज की बात याद रखना 🔥",

        "content": (
            f"{short_highlight}\n\n"
            f"{youtube_hashtags}"
        )
    }

    short_slide_path = generate_visuals(
        output_dir=short_slide_dir,
        video_type="short",
        slide_content=short_slide_content,
        slide_number=1,
        total_slides=1
    )

    # --------------------------------------------------------
    # CREATE SHORT VIDEO
    # --------------------------------------------------------

    short_video_path = (
        OUTPUT_DIR
        / f"short_video_{unique_id}.mp4"
    )

    print(
        f"🎥 Creating Short: "
        f"{short_video_path}"
    )

    create_video(
        [short_slide_path],
        [short_audio_path],
        short_video_path,
        "short"
    )

    if not short_video_path.exists():

        raise FileNotFoundError(
            "Short video was not created."
        )

    # --------------------------------------------------------
    # SHORT THUMBNAIL
    # --------------------------------------------------------

    print("🖼️ Creating Short thumbnail...")

    short_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type="short",
        thumbnail_title=thumbnail_text
    )

    # ========================================================
    # UPLOAD LONG VIDEO
    # ========================================================

    print("\n" + "=" * 70)
    print("📤 UPLOADING LONG VIDEO TO YOUTUBE")
    print("=" * 70)

    long_video_id = upload_to_youtube(

        video_path=long_video_path,

        title=youtube_title,

        description=youtube_description,

        tags=youtube_tags,

        thumbnail_path=long_thumb_path
    )

    if not long_video_id:

        print(
            "❌ Long video upload failed."
        )

        return None

    print(
        f"✅ Long video uploaded!"
    )

    print(
        f"🔗 https://www.youtube.com/watch?v={long_video_id}"
    )

    # ========================================================
    # WAIT BEFORE SHORT UPLOAD
    # ========================================================

    print(
        "\n⏳ Waiting 30 seconds before uploading Short..."
    )

    time.sleep(30)

    # ========================================================
    # SHORT METADATA
    # ========================================================

    short_title = clean_text(
        lesson_content.get(
            "short_title"
        ),
        ""
    )

    if not short_title:

        short_title = (
            short_highlight[:80].strip()
        )

    if not short_title:

        short_title = "आज की सबसे जरूरी बात"

    if not short_title.lower().endswith(
        "#shorts"
    ):

        short_title = (
            f"{short_title} #Shorts"
        )

    short_description = (
        f"{short_highlight}\n\n"
        f"पूरा वीडियो देखें:\n"
        f"https://www.youtube.com/watch?v={long_video_id}\n\n"
        f"{youtube_hashtags}"
    )

    short_tags = clean_tags(
        lesson_content.get(
            "short_tags",
            []
        )
    )

    if not short_tags:

        short_tags = [
            "hindi shorts",
            "motivation shorts",
            "motivational shorts",
            "hindi motivation",
            "motivational quotes",
            "success motivation",
            "life motivation",
            "shorts",
        ]

    # ========================================================
    # UPLOAD SHORT
    # ========================================================

    print("\n" + "=" * 70)
    print("📱 UPLOADING SHORT TO YOUTUBE")
    print("=" * 70)

    short_video_id = upload_to_youtube(

        video_path=short_video_path,

        title=short_title.strip(),

        description=short_description,

        tags=short_tags,

        thumbnail_path=short_thumb_path
    )

    if short_video_id:

        print(
            "✅ Short uploaded successfully!"
        )

        print(
            f"🔗 https://www.youtube.com/shorts/"
            f"{short_video_id}"
        )

    else:

        print(
            "⚠️ Short upload failed."
        )

    return long_video_id


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "=" * 70)
    print("🚀 HINDI MOTIVATION YOUTUBE AUTOMATION")
    print("=" * 70)

    print(
        f"📁 Current working directory: "
        f"{os.getcwd()}"
    )

    print(
        f"📁 Output directory: "
        f"{OUTPUT_DIR.resolve()}"
    )

    try:

        # ----------------------------------------------------
        # CREATE OUTPUT DIRECTORY
        # ----------------------------------------------------

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            f"📁 Output folder ready: "
            f"{OUTPUT_DIR.exists()}"
        )

        # ----------------------------------------------------
        # LOAD CONTENT PLAN
        # ----------------------------------------------------

        plan = get_content_plan()

        pending = [
            (i, lesson)
            for i, lesson in enumerate(
                plan["lessons"]
            )
            if lesson.get("status") == "pending"
        ]

        # ----------------------------------------------------
        # IF PLAN FINISHED
        # ----------------------------------------------------

        if not pending:

            print(
                "\n🎉 All current lessons completed!"
            )

            previous_titles = [
                lesson.get("title", "")
                for lesson in plan["lessons"]
            ]

            print(
                "🤖 Generating a fresh Hindi Motivation plan..."
            )

            new_plan = generate_curriculum(
                previous_titles=previous_titles
            )

            update_content_plan(
                new_plan
            )

            plan = new_plan

            pending = [
                (i, lesson)
                for i, lesson in enumerate(
                    plan["lessons"]
                )
                if lesson.get("status") == "pending"
            ]

            if not pending:

                print(
                    "⚠️ New curriculum has no pending lessons."
                )

                return

        # ----------------------------------------------------
        # PROCESS LESSONS
        # ----------------------------------------------------

        failed_lessons = []

        selected_lessons = pending[
            :LESSONS_PER_RUN
        ]

        print(
            f"\n📚 Lessons selected this run: "
            f"{len(selected_lessons)}"
        )

        for lesson_index, lesson in selected_lessons:

            try:

                video_id = produce_lesson_videos(
                    lesson
                )

                if video_id:

                    # ----------------------------------------
                    # MARK COMPLETE
                    # ----------------------------------------

                    for original_lesson in plan["lessons"]:

                        if (
                            clean_text(
                                original_lesson.get("title")
                            ).lower()
                            ==
                            clean_text(
                                lesson.get("title")
                            ).lower()
                        ):

                            original_lesson[
                                "status"
                            ] = "complete"

                            original_lesson[
                                "youtube_id"
                            ] = video_id

                            original_lesson[
                                "completed_at"
                            ] = (
                                datetime.datetime.utcnow()
                                .isoformat()
                                + "Z"
                            )

                            break

                    print(
                        f"✅ Completed lesson: "
                        f"{lesson.get('title')}"
                    )

                else:

                    print(
                        f"❌ Upload failed: "
                        f"{lesson.get('title')}"
                    )

                    failed_lessons.append(
                        lesson.get("title")
                    )

            except Exception as e:

                print(
                    f"\n❌ FAILED: "
                    f"{lesson.get('title')}"
                )

                print(
                    f"Error: {e}"
                )

                traceback.print_exc()

                failed_lessons.append(
                    lesson.get("title")
                )

            finally:

                # --------------------------------------------
                # ALWAYS SAVE CONTENT PLAN
                # --------------------------------------------

                update_content_plan(
                    plan
                )

                print(
                    "💾 Content plan saved."
                )

        # ----------------------------------------------------
        # FAILURE REPORT
        # ----------------------------------------------------

        if failed_lessons:

            print(
                "\n" + "=" * 70
            )

            print(
                "❌ PIPELINE FAILED"
            )

            print(
                f"Failed lessons: "
                f"{len(failed_lessons)}"
            )

            for title in failed_lessons:

                print(
                    f"   • {title}"
                )

            print(
                "=" * 70
            )

            sys.exit(1)

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        print(
            "\n" + "=" * 70
        )

        print(
            "🎉 AUTOMATION RUN COMPLETED SUCCESSFULLY"
        )

        print(
            "=" * 70
        )

    except Exception as e:

        print(
            "\n❌ CRITICAL ERROR IN MAIN()"
        )

        traceback.print_exc()

        sys.exit(1)

    # ========================================================
    # CLEANUP
    # ========================================================

    try:

        print(
            "\n🧹 Cleaning temporary WAV files..."
        )

        for file in OUTPUT_DIR.glob(
            "*.wav"
        ):

            try:

                file.unlink()

                print(
                    f"🗑️ Deleted: {file.name}"
                )

            except Exception as e:

                print(
                    f"⚠️ Could not delete "
                    f"{file.name}: {e}"
                )

    except Exception as e:

        print(
            f"⚠️ Cleanup error: {e}"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
