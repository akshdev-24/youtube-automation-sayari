# ============================================================
# HINDI MOTIVATION YOUTUBE AUTOMATION
# ============================================================
#
# Main pipeline:
#
# 1. Load content_plan.json
# 2. Generate fresh curriculum when required
# 3. Select pending lesson
# 4. Generate Hindi motivation content
# 5. Generate long-form video
# 6. Generate long-form thumbnail
# 7. Generate YouTube SEO metadata
# 8. Upload long video
# 9. Generate Short
# 10. Generate Short thumbnail
# 11. Upload Short
# 12. Mark lesson complete
# 13. Save content_plan.json
#
# Designed for GitHub Actions execution.
#
# ============================================================

import os
import re
import sys
import json
import time
import shutil
import datetime
import traceback
from pathlib import Path


# ============================================================
# GENERATOR IMPORTS
# ============================================================

from src.generator import (
    generate_curriculum,
    generate_lesson_content,
    text_to_speech,
    generate_visuals,
    create_video,
    YOUR_NAME,
)


# ============================================================
# YOUTUBE UPLOADER
# ============================================================

from src.uploader import (
    upload_to_youtube,
    upload_short_to_youtube,
)


# ============================================================
# CONFIGURATION
# ============================================================

CONTENT_PLAN_FILE = Path(
    "content_plan.json"
)

OUTPUT_DIR = Path(
    "output"
)

LESSONS_PER_RUN = 1

CHANNEL_NICHE = (
    "Hindi Motivation"
)

DEFAULT_AUTHOR = (
    "Aksh Dev"
)

# ------------------------------------------------------------
# Short upload delay
# ------------------------------------------------------------

SHORT_UPLOAD_DELAY = 30

# ------------------------------------------------------------
# Number of previous titles supplied to Gemini
# when generating a new curriculum.
# ------------------------------------------------------------

PREVIOUS_TITLE_LIMIT = 50


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(
    value,
    fallback=""
):
    """
    Safely convert a value into
    clean Unicode text.
    """

    if value is None:
        return fallback

    try:
        value = str(value).strip()
    except Exception:
        return fallback

    return value


# ============================================================
# HASHTAG CLEANER
# ============================================================

def clean_hashtags(value):
    """
    Convert hashtags into a clean string.

    Supports:
        list
        tuple
        string
    """

    if isinstance(
        value,
        (list, tuple)
    ):

        result = []

        seen = set()

        for tag in value:

            tag = clean_text(
                tag
            )

            if not tag:
                continue

            tag = tag.replace(
                "#",
                ""
            ).strip()

            if not tag:
                continue

            key = tag.lower()

            if key in seen:
                continue

            seen.add(key)

            result.append(
                "#" + tag
            )

        return " ".join(
            result
        )

    value = clean_text(
        value
    )

    if not value:
        return ""

    # --------------------------------------------------------
    # Normalize space
    # --------------------------------------------------------

    value = " ".join(
        value.split()
    )

    return value


# ============================================================
# TAG CLEANER
# ============================================================

def clean_tags(value):
    """
    Clean SEO tags.

    Supports:
        list
        tuple
        comma-separated string
    """

    if isinstance(
        value,
        (list, tuple)
    ):

        tags = value

    elif isinstance(
        value,
        str
    ):

        tags = value.split(",")

    else:

        tags = []

    cleaned = []

    seen = set()

    for tag in tags:

        tag = clean_text(
            tag
        )

        if not tag:
            continue

        # Remove #
        tag = tag.replace(
            "#",
            ""
        ).strip()

        if not tag:
            continue

        # Normalize spaces
        tag = " ".join(
            tag.split()
        )

        key = tag.lower()

        if key in seen:
            continue

        seen.add(
            key
        )

        cleaned.append(
            tag
        )

    return cleaned


# ============================================================
# DEFAULT SEO TAGS
# ============================================================

def get_default_tags():
    """
    Fallback SEO tags for Hindi Motivation.
    """

    return [

        "hindi motivation",

        "hindi motivational video",

        "motivational video hindi",

        "motivation in hindi",

        "success motivation",

        "life motivation",

        "self improvement hindi",

        "motivational quotes hindi",

        "success quotes hindi",

        "positive thinking hindi",

        "life changing motivation",

        "powerful motivation hindi",

        "inspirational video hindi",

        "zindagi badalne wali baatein",

        "success tips hindi",

        "mindset motivation hindi",

        "discipline motivation hindi",

        "confidence motivation hindi",

        "hard work motivation hindi",

        "never give up motivation",

    ]


# ============================================================
# DEFAULT HASHTAGS
# ============================================================

def get_default_hashtags():

    return (
        "#HindiMotivation "
        "#Motivation "
        "#MotivationalQuotes "
        "#Success "
        "#SelfImprovement "
        "#HindiMotivationVideo"
    )


# ============================================================
# DEFAULT DESCRIPTION
# ============================================================

def build_default_description(
    lesson_title
):

    return (
        f"{lesson_title}\n\n"
        "इस वीडियो में हम बात करेंगे "
        "motivation, success, mindset और "
        "self improvement से जुड़ी जरूरी बातों के बारे में।\n\n"
        "अगर आप अपनी जिंदगी में आगे बढ़ना चाहते हैं "
        "और अपने goals को achieve करना चाहते हैं, "
        "तो इस वीडियो को पूरा जरूर देखें।\n\n"
        "ऐसी ही Hindi Motivation videos के लिए "
        "चैनल को Subscribe करें।\n\n"
        f"{get_default_hashtags()}\n\n"
        "#HindiMotivation #Success #Motivation"
    )


# ============================================================
# CONTENT PLAN LOAD
# ============================================================

def get_content_plan():

    print(
        "\n📄 Loading content plan..."
    )

    # ========================================================
    # FILE DOES NOT EXIST
    # ========================================================

    if not CONTENT_PLAN_FILE.exists():

        print(
            "📄 content_plan.json not found."
        )

        print(
            "🤖 Generating fresh Hindi "
            "Motivation curriculum..."
        )

        new_plan = generate_curriculum()

        if not new_plan:

            raise ValueError(
                "generate_curriculum() returned empty plan."
            )

        with open(
            CONTENT_PLAN_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                new_plan,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(
            "✅ New curriculum saved."
        )

        return new_plan

    # ========================================================
    # LOAD EXISTING FILE
    # ========================================================

    try:

        with open(
            CONTENT_PLAN_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            plan = json.load(
                f
            )

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if not isinstance(
            plan,
            dict
        ):

            raise ValueError(
                "Content plan must be a JSON object."
            )

        if (
            not plan.get("lessons")
            or not isinstance(
                plan["lessons"],
                list
            )
        ):

            raise ValueError(
                "Invalid or empty lessons list."
            )

        print(
            f"✅ Loaded "
            f"{len(plan['lessons'])} lessons."
        )

        return plan

    except Exception as e:

        print(
            "❌ Error loading content plan:"
        )

        print(
            f"   {e}"
        )

        print(
            "🔄 Regenerating curriculum..."
        )

        new_plan = generate_curriculum()

        if not new_plan:

            raise ValueError(
                "Failed to regenerate curriculum."
            )

        with open(
            CONTENT_PLAN_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                new_plan,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(
            "✅ New curriculum generated."
        )

        return new_plan


# ============================================================
# SAVE CONTENT PLAN
# ============================================================

def update_content_plan(
    plan
):

    try:

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

        print(
            "💾 content_plan.json saved."
        )

    except Exception as e:

        print(
            "❌ Could not save content plan:"
        )

        print(
            f"   {e}"
        )

        raise


# ============================================================
# GET PENDING LESSONS
# ============================================================

def get_pending_lessons(
    plan
):

    lessons = plan.get(
        "lessons",
        []
    )

    pending = []

    for index, lesson in enumerate(
        lessons
    ):

        if not isinstance(
            lesson,
            dict
        ):
            continue

        status = clean_text(
            lesson.get(
                "status"
            ),
            "pending"
        ).lower()

        if status == "pending":

            pending.append(
                (
                    index,
                    lesson
                )
            )

    return pending


# ============================================================
# GENERATE NEW CURRICULUM
# ============================================================

def generate_fresh_plan(
    old_plan
):

    print(
        "\n" + "=" * 70
    )

    print(
        "🤖 GENERATING FRESH "
        "HINDI MOTIVATION CURRICULUM"
    )

    print(
        "=" * 70
    )

    previous_titles = []

    for lesson in old_plan.get(
        "lessons",
        []
    ):

        if not isinstance(
            lesson,
            dict
        ):
            continue

        title = clean_text(
            lesson.get(
                "title"
            )
        )

        if title:

            previous_titles.append(
                title
            )

    previous_titles = (
        previous_titles[
            -PREVIOUS_TITLE_LIMIT:
        ]
    )

    print(
        f"📚 Previous titles supplied:"
        f" {len(previous_titles)}"
    )

    try:

        new_plan = generate_curriculum(
            previous_titles=previous_titles
        )

    except TypeError:

        # Backward compatibility in case
        # generator.py does not accept
        # previous_titles.
        print(
            "⚠️ Generator does not accept "
            "previous_titles."
        )

        print(
            "🔄 Calling generate_curriculum() "
            "without previous titles..."
        )

        new_plan = generate_curriculum()

    if not new_plan:

        raise ValueError(
            "Fresh curriculum generation failed."
        )

    if not isinstance(
        new_plan,
        dict
    ):

        raise ValueError(
            "Generated curriculum is not a dictionary."
        )

    lessons = new_plan.get(
        "lessons"
    )

    if not isinstance(
        lessons,
        list
    ):

        raise ValueError(
            "Generated curriculum has no valid lessons."
        )

    # --------------------------------------------------------
    # Make sure every lesson is pending
    # --------------------------------------------------------

    for lesson in lessons:

        if isinstance(
            lesson,
            dict
        ):

            lesson["status"] = "pending"

    update_content_plan(
        new_plan
    )

    print(
        f"✅ Fresh curriculum contains "
        f"{len(lessons)} lessons."
    )

    return new_plan


# ============================================================
# CREATE UNIQUE RUN ID
# ============================================================

def create_unique_id(
    lesson_title,
    chapter,
    part
):

    timestamp = (
        datetime.datetime.now(
            datetime.timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    chapter_safe = re.sub(
        r"[^\w]+",
        "_",
        clean_text(
            chapter,
            "1"
        ),
        flags=re.UNICODE
    ).strip("_")

    part_safe = re.sub(
        r"[^\w]+",
        "_",
        clean_text(
            part,
            "1"
        ),
        flags=re.UNICODE
    ).strip("_")

    title_safe = re.sub(
        r"[^\w]+",
        "_",
        clean_text(
            lesson_title,
            "motivation"
        ),
        flags=re.UNICODE
    ).strip("_")

    title_safe = (
        title_safe[:60]
        or "motivation"
    )

    return (
        f"{timestamp}_"
        f"{chapter_safe or '1'}_"
        f"{part_safe or '1'}_"
        f"{title_safe}"
    )


# ============================================================
# PREPARE YOUTUBE METADATA
# ============================================================

def prepare_youtube_metadata(
    lesson_title,
    lesson_content
):

    youtube_data = (
        lesson_content.get(
            "youtube",
            {}
        )
    )

    if not isinstance(
        youtube_data,
        dict
    ):

        youtube_data = {}

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    youtube_title = clean_text(
        youtube_data.get(
            "title"
        ),
        lesson_title
    )

    if not youtube_title:

        youtube_title = (
            lesson_title
            or
            "Hindi Motivation | "
            "जिंदगी बदलने वाली बातें"
        )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    youtube_description = clean_text(
        youtube_data.get(
            "description"
        ),
        ""
    )

    if not youtube_description:

        youtube_description = (
            build_default_description(
                youtube_title
            )
        )

    # --------------------------------------------------------
    # TAGS
    # --------------------------------------------------------

    youtube_tags = clean_tags(
        youtube_data.get(
            "tags",
            []
        )
    )

    if not youtube_tags:

        youtube_tags = (
            get_default_tags()
        )

    # --------------------------------------------------------
    # HASHTAGS
    # --------------------------------------------------------

    youtube_hashtags = clean_hashtags(
        youtube_data.get(
            "hashtags",
            []
        )
    )

    if not youtube_hashtags:

        youtube_hashtags = (
            get_default_hashtags()
        )

    # --------------------------------------------------------
    # THUMBNAIL
    # --------------------------------------------------------

    thumbnail_text = clean_text(
        youtube_data.get(
            "thumbnail_text"
        ),
        youtube_title
    )

    # --------------------------------------------------------
    # SHORT TITLE
    # --------------------------------------------------------

    short_title = clean_text(
        lesson_content.get(
            "short_title"
        ),
        ""
    )

    # --------------------------------------------------------
    # SHORT TAGS
    # --------------------------------------------------------

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

            "self improvement",

            "shorts",

        ]

    return {
        "title": youtube_title,
        "description": youtube_description,
        "tags": youtube_tags,
        "hashtags": youtube_hashtags,
        "thumbnail_text": thumbnail_text,
        "short_title": short_title,
        "short_tags": short_tags,
    }


# ============================================================
# PRODUCE ONE LESSON
# ============================================================

def produce_lesson_videos(
    lesson
):

    # ========================================================
    # BASIC INFORMATION
    # ========================================================

    lesson_title = clean_text(
        lesson.get(
            "title"
        ),
        "आज खुद पर विश्वास करो"
    )

    chapter = clean_text(
        lesson.get(
            "chapter"
        ),
        "1"
    )

    part = clean_text(
        lesson.get(
            "part"
        ),
        "1"
    )

    print(
        "\n" + "=" * 70
    )

    print(
        f"▶️ LESSON:"
        f" {lesson_title}"
    )

    print(
        f"📚 Chapter:"
        f" {chapter}"
    )

    print(
        f"📌 Part:"
        f" {part}"
    )

    print(
        "=" * 70
    )

    # ========================================================
    # UNIQUE ID
    # ========================================================

    unique_id = create_unique_id(
        lesson_title,
        chapter,
        part
    )

    print(
        f"🆔 Run ID:"
        f" {unique_id}"
    )

    # ========================================================
    # GENERATE CONTENT
    # ========================================================

    print(
        "\n🤖 Generating Hindi Motivation content..."
    )

    lesson_content = (
        generate_lesson_content(
            lesson_title
        )
    )

    if not lesson_content:

        raise ValueError(
            "Gemini returned empty lesson content."
        )

    if not isinstance(
        lesson_content,
        dict
    ):

        raise ValueError(
            "Gemini lesson content is not a dictionary."
        )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = (
        prepare_youtube_metadata(
            lesson_title,
            lesson_content
        )
    )

    youtube_title = metadata[
        "title"
    ]

    youtube_description = metadata[
        "description"
    ]

    youtube_tags = metadata[
        "tags"
    ]

    youtube_hashtags = metadata[
        "hashtags"
    ]

    thumbnail_text = metadata[
        "thumbnail_text"
    ]

    short_title = metadata[
        "short_title"
    ]

    short_tags = metadata[
        "short_tags"
    ]

    # ========================================================
    # DISPLAY METADATA
    # ========================================================

    print(
        "\n📊 GENERATED YOUTUBE METADATA"
    )

    print(
        "-" * 70
    )

    print(
        f"TITLE:\n{youtube_title}"
    )

    print(
        f"\nTAGS:\n{youtube_tags}"
    )

    print(
        f"\nHASHTAGS:\n{youtube_hashtags}"
    )

    print(
        f"\nTHUMBNAIL TEXT:\n{thumbnail_text}"
    )

    print(
        "-" * 70
    )

    # ========================================================
    # LONG FORM
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "🎬 PRODUCING LONG-FORM VIDEO"
    )

    print(
        "=" * 70
    )

    long_slides = (
        lesson_content.get(
            "long_form_slides",
            []
        )
    )

    if not isinstance(
        long_slides,
        list
    ):

        long_slides = []

    if not long_slides:

        raise ValueError(
            "No long_form_slides generated."
        )

    # ========================================================
    # INTRO SLIDE
    # ========================================================

    intro_slide = {

        "title":
            youtube_title,

        "content":
            (
                "Hindi Motivation • "
                f"Chapter {chapter} • "
                f"Part {part}"
            )
    }

    # ========================================================
    # OUTRO SLIDE
    # ========================================================

    outro_slide = {

        "title":
            "खुद पर विश्वास रखो ❤️",

        "content":
            (
                f"{YOUR_NAME} के साथ रोज़ "
                "motivation के लिए "
                "चैनल को Subscribe करें!"
            )
    }

    all_slides = (
        [intro_slide]
        + long_slides
        + [outro_slide]
    )

    # ========================================================
    # LONG SLIDE SCRIPTS
    # ========================================================

    slide_scripts = []

    # --------------------------------------------------------
    # INTRO SCRIPT
    # --------------------------------------------------------

    intro_script = (
        "नमस्ते दोस्तों। "
        "आज की इस Hindi Motivation video में "
        f"हम बात करेंगे — {youtube_title} "
        "के बारे में। "
        "अगर आप अपनी जिंदगी में आगे बढ़ना चाहते हैं, "
        "तो इस वीडियो को अंत तक जरूर सुनिए।"
    )

    slide_scripts.append(
        intro_script
    )

    # --------------------------------------------------------
    # GENERATED SLIDES
    # --------------------------------------------------------

    for slide in long_slides:

        if not isinstance(
            slide,
            dict
        ):

            slide_scripts.append(
                "इस बात को अपनी जिंदगी में जरूर अपनाइए।"
            )

            continue

        content = clean_text(
            slide.get(
                "content"
            ),
            ""
        )

        if not content:

            content = (
                "इस बात को समझना "
                "आपकी जिंदगी में एक "
                "बड़ा बदलाव ला सकता है।"
            )

        slide_scripts.append(
            content
        )

    # --------------------------------------------------------
    # OUTRO SCRIPT
    # --------------------------------------------------------

    outro_script = (
        "अगर इस वीडियो ने आपको "
        "थोड़ी भी motivation दी है, "
        "तो वीडियो को Like करें, "
        "चैनल को Subscribe करें "
        "और इसे अपने किसी दोस्त के साथ "
        "जरूर शेयर करें। "
        "याद रखिए — शुरुआत छोटी हो सकती है, "
        "लेकिन आपका सपना बड़ा होना चाहिए।"
    )

    slide_scripts.append(
        outro_script
    )

    # ========================================================
    # LONG AUDIO
    # ========================================================

    slide_audio_paths = []

    print(
        "\n🎙️ Generating natural Hindi voice..."
    )

    for i, script in enumerate(
        slide_scripts
    ):

        audio_path = (
            OUTPUT_DIR
            / f"audio_long_{unique_id}_{i + 1}.mp3"
        )

        print(
            f"🎙️ Voice "
            f"{i + 1}/{len(slide_scripts)}"
        )

        wav_path = text_to_speech(
            script,
            audio_path
        )

        if not wav_path:

            raise RuntimeError(
                f"TTS failed for slide {i + 1}."
            )

        wav_path = Path(
            wav_path
        )

        if not wav_path.exists():

            raise FileNotFoundError(
                f"TTS output not found:"
                f" {wav_path}"
            )

        slide_audio_paths.append(
            wav_path
        )

    print(
        f"✅ Generated "
        f"{len(slide_audio_paths)} "
        "voice tracks."
    )

    # ========================================================
    # LONG VISUALS
    # ========================================================

    print(
        "\n🖼️ Generating long-form visuals..."
    )

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

            total_slides=len(
                all_slides
            )
        )

        if not path:

            raise RuntimeError(
                f"Visual generation failed "
                f"for slide {i + 1}."
            )

        path = Path(
            path
        )

        if not path.exists():

            raise FileNotFoundError(
                f"Slide image not found:"
                f" {path}"
            )

        slide_paths.append(
            path
        )

    print(
        f"✅ Generated "
        f"{len(slide_paths)} slide visuals."
    )

    # ========================================================
    # CREATE LONG VIDEO
    # ========================================================

    long_video_path = (
        OUTPUT_DIR
        / f"long_video_{unique_id}.mp4"
    )

    print(
        "\n🎥 Creating long-form MP4..."
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

    if long_video_path.stat().st_size < 1024:

        raise ValueError(
            "Long video file is too small."
        )

    print(
        f"✅ Long video created:"
        f" {long_video_path}"
    )

    # ========================================================
    # LONG THUMBNAIL
    # ========================================================

    print(
        "\n🖼️ Creating long-form thumbnail..."
    )

    long_thumb_path = (
        generate_visuals(

            output_dir=OUTPUT_DIR,

            video_type="long",

            thumbnail_title=thumbnail_text
        )
    )

    if not long_thumb_path:

        raise FileNotFoundError(
            "Long-form thumbnail was not created."
        )

    long_thumb_path = Path(
        long_thumb_path
    )

    if not long_thumb_path.exists():

        raise FileNotFoundError(
            f"Long thumbnail not found:"
            f" {long_thumb_path}"
        )

    print(
        f"✅ Long thumbnail:"
        f" {long_thumb_path}"
    )

    # ========================================================
    # SHORT FORM
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "📱 PRODUCING YOUTUBE SHORT"
    )

    print(
        "=" * 70
    )

    # ========================================================
    # SHORT HIGHLIGHT
    # ========================================================

    short_highlight = clean_text(
        lesson_content.get(
            "short_form_highlight"
        ),
        ""
    )

    # --------------------------------------------------------
    # Some Gemini responses may return
    # an object instead of a string.
    # --------------------------------------------------------

    if isinstance(
        lesson_content.get(
            "short_form_highlight"
        ),
        dict
    ):

        short_data = (
            lesson_content.get(
                "short_form_highlight"
            )
        )

        short_highlight = clean_text(
            short_data.get(
                "script"
            )
            or
            short_data.get(
                "hook"
            ),
            ""
        )

    if not short_highlight:

        short_highlight = (
            "अगर जिंदगी बदलनी है, "
            "तो सबसे पहले खुद पर "
            "विश्वास करना सीखो।"
        )

    # ========================================================
    # SHORT SCRIPT
    # ========================================================

    short_script = (
        "रुकिए! "
        "अगर आप अपनी जिंदगी में "
        "कुछ बड़ा करना चाहते हैं, "
        "तो यह बात हमेशा याद रखिए।\n\n"
        f"{short_highlight}\n\n"
        "ऐसी ही powerful motivation के लिए "
        "चैनल को Subscribe करें।"
    )

    # ========================================================
    # SHORT AUDIO
    # ========================================================

    short_audio_mp3_path = (
        OUTPUT_DIR
        / f"short_audio_{unique_id}.mp3"
    )

    print(
        "🎙️ Generating Short Hindi voice..."
    )

    short_audio_path = text_to_speech(
        short_script,
        short_audio_mp3_path
    )

    if not short_audio_path:

        raise RuntimeError(
            "Short TTS generation failed."
        )

    short_audio_path = Path(
        short_audio_path
    )

    if not short_audio_path.exists():

        raise FileNotFoundError(
            f"Short audio not found:"
            f" {short_audio_path}"
        )

    # ========================================================
    # SHORT VISUAL
    # ========================================================

    short_slide_dir = (
        OUTPUT_DIR
        / f"slides_short_{unique_id}"
    )

    short_slide_content = {

        "title":
            "आज की बात याद रखना 🔥",

        "content":
            short_highlight
    }

    short_slide_path = (
        generate_visuals(

            output_dir=short_slide_dir,

            video_type="short",

            slide_content=short_slide_content,

            slide_number=1,

            total_slides=1
        )
    )

    if not short_slide_path:

        raise RuntimeError(
            "Short visual generation failed."
        )

    short_slide_path = Path(
        short_slide_path
    )

    if not short_slide_path.exists():

        raise FileNotFoundError(
            f"Short slide not found:"
            f" {short_slide_path}"
        )

    # ========================================================
    # CREATE SHORT VIDEO
    # ========================================================

    short_video_path = (
        OUTPUT_DIR
        / f"short_video_{unique_id}.mp4"
    )

    print(
        "\n🎥 Creating YouTube Short..."
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

    if short_video_path.stat().st_size < 1024:

        raise ValueError(
            "Short video file is too small."
        )

    print(
        f"✅ Short created:"
        f" {short_video_path}"
    )

    # ========================================================
    # SHORT THUMBNAIL
    # ========================================================

    print(
        "\n🖼️ Creating Short thumbnail..."
    )

    short_thumb_path = (
        generate_visuals(

            output_dir=OUTPUT_DIR,

            video_type="short",

            thumbnail_title=thumbnail_text
        )
    )

    if short_thumb_path:

        short_thumb_path = Path(
            short_thumb_path
        )

        if short_thumb_path.exists():

            print(
                f"✅ Short thumbnail:"
                f" {short_thumb_path}"
            )

        else:

            print(
                "⚠️ Short thumbnail path "
                "returned but file does not exist."
            )

            short_thumb_path = None

    # ========================================================
    # UPLOAD LONG VIDEO
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "📤 UPLOADING LONG VIDEO TO YOUTUBE"
    )

    print(
        "=" * 70
    )

    long_video_id = (
        upload_to_youtube(

            video_path=long_video_path,

            title=youtube_title,

            description=youtube_description,

            tags=youtube_tags,

            thumbnail_path=long_thumb_path
        )
    )

    if not long_video_id:

        raise RuntimeError(
            "Long video upload failed."
        )

    print(
        "\n🎉 LONG VIDEO UPLOADED!"
    )

    print(
        f"🆔 Video ID:"
        f" {long_video_id}"
    )

    print(
        "🔗 "
        f"https://www.youtube.com/watch?v="
        f"{long_video_id}"
    )

    # ========================================================
    # WAIT
    # ========================================================

    print(
        f"\n⏳ Waiting "
        f"{SHORT_UPLOAD_DELAY} seconds "
        "before Short upload..."
    )

    time.sleep(
        SHORT_UPLOAD_DELAY
    )

    # ========================================================
    # SHORT TITLE
    # ========================================================

    if not short_title:

        short_title = (
            short_highlight[:75]
            .strip()
        )

    if not short_title:

        short_title = (
            "आज की सबसे जरूरी बात"
        )

    # Remove accidental newlines
    short_title = " ".join(
        short_title.split()
    )

    # ========================================================
    # SHORT DESCRIPTION
    # ========================================================

    short_description = (
        f"{short_highlight}\n\n"
        "पूरा वीडियो देखें:\n"
        f"https://www.youtube.com/watch?v="
        f"{long_video_id}\n\n"
        f"{youtube_hashtags}\n\n"
        "#Shorts"
    )

    # ========================================================
    # UPLOAD SHORT
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "📱 UPLOADING SHORT TO YOUTUBE"
    )

    print(
        "=" * 70
    )

    short_video_id = (
        upload_short_to_youtube(

            video_path=short_video_path,

            title=short_title,

            description=short_description,

            tags=short_tags,

            thumbnail_path=short_thumb_path
        )
    )

    # ========================================================
    # SHORT RESULT
    # ========================================================

    if short_video_id:

        print(
            "\n🎉 SHORT UPLOADED SUCCESSFULLY!"
        )

        print(
            f"🆔 Short ID:"
            f" {short_video_id}"
        )

        print(
            "🔗 "
            f"https://www.youtube.com/shorts/"
            f"{short_video_id}"
        )

    else:

        print(
            "\n⚠️ Short upload failed."
        )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "long_video_id":
            long_video_id,

        "short_video_id":
            short_video_id,

        "long_video_path":
            str(long_video_path),

        "short_video_path":
            str(short_video_path),

        "long_thumbnail":
            str(long_thumb_path),

        "short_thumbnail":
            (
                str(short_thumb_path)
                if short_thumb_path
                else None
            )
    }


# ============================================================
# MARK LESSON COMPLETE
# ============================================================

def mark_lesson_complete(
    plan,
    lesson,
    result
):

    lesson_title = clean_text(
        lesson.get(
            "title"
        )
    ).lower()

    completed = False

    for original_lesson in plan.get(
        "lessons",
        []
    ):

        if not isinstance(
            original_lesson,
            dict
        ):
            continue

        original_title = clean_text(
            original_lesson.get(
                "title"
            )
        ).lower()

        if (
            original_title
            == lesson_title
        ):

            original_lesson[
                "status"
            ] = "complete"

            original_lesson[
                "youtube_id"
            ] = result.get(
                "long_video_id"
            )

            original_lesson[
                "long_video_id"
            ] = result.get(
                "long_video_id"
            )

            original_lesson[
                "short_video_id"
            ] = result.get(
                "short_video_id"
            )

            original_lesson[
                "completed_at"
            ] = (
                datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()
            )

            original_lesson[
                "youtube_url"
            ] = (
                "https://www.youtube.com/watch?v="
                + str(
                    result.get(
                        "long_video_id"
                    )
                )
            )

            if result.get(
                "short_video_id"
            ):

                original_lesson[
                    "short_url"
                ] = (
                    "https://www.youtube.com/shorts/"
                    + str(
                        result.get(
                            "short_video_id"
                        )
                    )
                )

            completed = True

            break

    if not completed:

        print(
            "⚠️ Could not find lesson "
            "inside content plan."
        )

        return False

    update_content_plan(
        plan
    )

    print(
        f"✅ Lesson marked complete:"
        f" {lesson.get('title')}"
    )

    return True


# ============================================================
# CLEAN TEMPORARY FILES
# ============================================================

def cleanup_temporary_files():

    print(
        "\n🧹 Cleaning temporary files..."
    )

    # --------------------------------------------------------
    # Temporary WAV files
    # --------------------------------------------------------

    wav_files = list(
        OUTPUT_DIR.glob(
            "*.wav"
        )
    )

    for file in wav_files:

        try:

            file.unlink()

            print(
                f"🗑️ Deleted:"
                f" {file.name}"
            )

        except Exception as e:

            print(
                f"⚠️ Could not delete "
                f"{file.name}: {e}"
            )

    # --------------------------------------------------------
    # Temporary timing JSON files
    #
    # Keep these if generator.py needs them
    # for animation, therefore DO NOT delete.
    # --------------------------------------------------------

    print(
        f"🧹 Removed "
        f"{len(wav_files)} temporary WAV files."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n" + "=" * 70
    )

    print(
        "🚀 HINDI MOTIVATION "
        "YOUTUBE AUTOMATION"
    )

    print(
        "=" * 70
    )

    print(
        f"👤 Creator:"
        f" {YOUR_NAME or DEFAULT_AUTHOR}"
    )

    print(
        f"🎯 Niche:"
        f" {CHANNEL_NICHE}"
    )

    print(
        f"📁 Working directory:"
        f" {os.getcwd()}"
    )

    print(
        f"📁 Output directory:"
        f" {OUTPUT_DIR.resolve()}"
    )

    print(
        f"⏰ Started:"
        f" {datetime.datetime.now().isoformat()}"
    )

    # ========================================================
    # PREPARE OUTPUT DIRECTORY
    # ========================================================

    try:

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            f"✅ Output folder ready:"
            f" {OUTPUT_DIR.exists()}"
        )

    except Exception as e:

        print(
            "❌ Could not create output directory."
        )

        print(
            f"   {e}"
        )

        raise

    # ========================================================
    # LOAD PLAN
    # ========================================================

    plan = get_content_plan()

    # ========================================================
    # FIND PENDING
    # ========================================================

    pending = get_pending_lessons(
        plan
    )

    # ========================================================
    # NO PENDING LESSONS
    # ========================================================

    if not pending:

        print(
            "\n🎉 All current lessons are complete!"
        )

        print(
            "🤖 Generating a fresh curriculum..."
        )

        plan = generate_fresh_plan(
            plan
        )

        pending = get_pending_lessons(
            plan
        )

        if not pending:

            raise RuntimeError(
                "Fresh curriculum has no pending lessons."
            )

    # ========================================================
    # SELECT LESSONS
    # ========================================================

    selected_lessons = (
        pending[
            :LESSONS_PER_RUN
        ]
    )

    print(
        "\n📚 Lessons selected:"
        f" {len(selected_lessons)}"
    )

    for index, lesson in selected_lessons:

        print(
            f"   {index + 1}. "
            f"{lesson.get('title')}"
        )

    # ========================================================
    # PROCESS LESSONS
    # ========================================================

    failed_lessons = []

    completed_count = 0

    for lesson_index, lesson in (
        selected_lessons
    ):

        print(
            "\n" + "=" * 70
        )

        print(
            f"▶️ PROCESSING LESSON "
            f"{lesson_index + 1}"
        )

        print(
            "=" * 70
        )

        try:

            # ------------------------------------------------
            # Produce
            # ------------------------------------------------

            result = (
                produce_lesson_videos(
                    lesson
                )
            )

            # ------------------------------------------------
            # Validate result
            # ------------------------------------------------

            if not result:

                raise RuntimeError(
                    "Video production returned no result."
                )

            if not result.get(
                "long_video_id"
            ):

                raise RuntimeError(
                    "Long video ID missing."
                )

            # ------------------------------------------------
            # Mark complete
            # ------------------------------------------------

            mark_lesson_complete(
                plan,
                lesson,
                result
            )

            completed_count += 1

            print(
                "\n✅ LESSON COMPLETED:"
                f" {lesson.get('title')}"
            )

        except Exception as e:

            print(
                "\n" + "=" * 70
            )

            print(
                "❌ LESSON FAILED"
            )

            print(
                "=" * 70
            )

            print(
                f"📚 Lesson:"
                f" {lesson.get('title')}"
            )

            print(
                f"❌ Error:"
                f" {e}"
            )

            traceback.print_exc()

            failed_lessons.append(
                lesson.get(
                    "title",
                    "Unknown lesson"
                )
            )

            # ------------------------------------------------
            # IMPORTANT:
            # Keep failed lesson pending.
            # ------------------------------------------------

            try:

                for original_lesson in (
                    plan.get(
                        "lessons",
                        []
                    )
                ):

                    if (
                        clean_text(
                            original_lesson.get(
                                "title"
                            )
                        ).lower()
                        ==
                        clean_text(
                            lesson.get(
                                "title"
                            )
                        ).lower()
                    ):

                        original_lesson[
                            "status"
                        ] = "pending"

                        original_lesson.pop(
                            "youtube_id",
                            None
                        )

                        break

                update_content_plan(
                    plan
                )

            except Exception as save_error:

                print(
                    "⚠️ Could not save "
                    "failed lesson status:"
                )

                print(
                    f"   {save_error}"
                )

        finally:

            # ------------------------------------------------
            # Save plan after every lesson
            # ------------------------------------------------

            try:

                update_content_plan(
                    plan
                )

            except Exception as e:

                print(
                    "⚠️ Content plan save failed:"
                    f" {e}"
                )

    # ========================================================
    # CLEANUP
    # ========================================================

    try:

        cleanup_temporary_files()

    except Exception as e:

        print(
            f"⚠️ Cleanup error:"
            f" {e}"
        )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "📊 AUTOMATION REPORT"
    )

    print(
        "=" * 70
    )

    print(
        f"✅ Completed:"
        f" {completed_count}"
    )

    print(
        f"❌ Failed:"
        f" {len(failed_lessons)}"
    )

    if failed_lessons:

        print(
            "\n❌ Failed lessons:"
        )

        for title in failed_lessons:

            print(
                f"   • {title}"
            )

    print(
        "\n⏰ Finished:"
        f" {datetime.datetime.now().isoformat()}"
    )

    # ========================================================
    # FAILURE
    # ========================================================

    if failed_lessons:

        print(
            "\n" + "=" * 70
        )

        print(
            "❌ AUTOMATION RUN FAILED"
        )

        print(
            "=" * 70
        )

        sys.exit(1)

    # ========================================================
    # SUCCESS
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "🎉 AUTOMATION RUN COMPLETED SUCCESSFULLY"
    )

    print(
        "=" * 70
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\n⚠️ Process interrupted."
        )

        sys.exit(130)

    except Exception as e:

        print(
            "\n" + "=" * 70
        )

        print(
            "❌ CRITICAL AUTOMATION ERROR"
        )

        print(
            "=" * 70
        )

        print(
            f"Error:"
            f" {e}"
        )

        traceback.print_exc()

        sys.exit(1)
