# ============================================================
# FILE: src/generator.py
# ============================================================
#
# HINDI MOTIVATION YOUTUBE AUTOMATION
#
# Features:
#   ✅ Gemini content generation
#   ✅ Hindi motivational curriculum
#   ✅ Natural Hindi Neural Voice
#   ✅ Edge TTS
#   ✅ Hindi / Devanagari font detection
#   ✅ Voice timing / VTT timing
#   ✅ Animated kinetic typography
#   ✅ Speech-synced text highlighting
#   ✅ Word/chunk based text animation
#   ✅ Long-form videos
#   ✅ YouTube Shorts
#   ✅ Pexels background visuals
#   ✅ Cinematic dark background
#   ✅ Background music
#   ✅ Professional thumbnails
#   ✅ GitHub Actions compatible
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import os
import json
import time
import random
import re
import subprocess
import shutil
from pathlib import Path
from io import BytesIO

import requests

from google import genai

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    concatenate_videoclips,
    concatenate_audioclips,
    VideoClip,
    vfx,
)

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
)

from pydub import AudioSegment


# ============================================================
# CONFIGURATION
# ============================================================

ASSETS_PATH = Path("assets")

MUSIC_PATH = (
    ASSETS_PATH /
    "music" /
    "bg_music.mp3"
)

YOUR_NAME = "Aksh Dev"

CHANNEL_NICHE = "Hindi Motivation"

# ------------------------------------------------------------
# Gemini
# ------------------------------------------------------------

GEMINI_MODEL = "gemini-3.6-flash"

# ------------------------------------------------------------
# Edge TTS
# ------------------------------------------------------------

TTS_LANGUAGE = "hi"

# Natural Indian Hindi male voice
TTS_VOICE = "hi-IN-MadhurNeural"

# Female alternative:
# hi-IN-SwaraNeural

TTS_RETRIES = 5
TTS_BACKOFF = 5

# ------------------------------------------------------------
# Video
# ------------------------------------------------------------

LONG_WIDTH = 1920
LONG_HEIGHT = 1080

SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920

FPS = 24

# ------------------------------------------------------------
# Text animation
# ------------------------------------------------------------

WORDS_PER_HIGHLIGHT = 3

TEXT_ANIMATION_IN = 0.22

# ------------------------------------------------------------
# Audio
# ------------------------------------------------------------

BACKGROUND_MUSIC_VOLUME = 0.065

# ------------------------------------------------------------
# SEO
# ------------------------------------------------------------

MAX_TAGS = 25


# ============================================================
# FONT DETECTION
# ============================================================

def find_hindi_font():
    """
    Find a proper Hindi / Devanagari font.

    Priority:
        1. Project font
        2. Noto Sans Devanagari
        3. System Noto
        4. DejaVu
        5. Arial fallback
    """

    candidates = [

        # Project fonts
        ASSETS_PATH /
        "fonts" /
        "NotoSansDevanagari-Regular.ttf",

        ASSETS_PATH /
        "fonts" /
        "NotoSansDevanagari-Medium.ttf",

        ASSETS_PATH /
        "fonts" /
        "NotoSansDevanagari-Bold.ttf",

        # Ubuntu / GitHub Actions
        Path(
            "/usr/share/fonts/truetype/noto/"
            "NotoSansDevanagari-Regular.ttf"
        ),

        Path(
            "/usr/share/fonts/opentype/noto/"
            "NotoSansDevanagari-Regular.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/noto/"
            "NotoSansDevanagari-Medium.ttf"
        ),

        # DejaVu fallback
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),

        # Existing project fallback
        ASSETS_PATH /
        "fonts" /
        "arial.ttf",
    ]

    for font_path in candidates:

        if font_path.exists():

            print(
                f"🔤 Hindi font selected: "
                f"{font_path}"
            )

            return font_path

    print(
        "⚠️ No Hindi font found. "
        "Using PIL default font."
    )

    return None


FONT_FILE = find_hindi_font()


# ============================================================
# FONT LOADER
# ============================================================

def get_font(size, bold=False):

    if FONT_FILE:

        try:

            return ImageFont.truetype(
                str(FONT_FILE),
                size
            )

        except Exception as e:

            print(
                f"⚠️ Font loading error: {e}"
            )

    return ImageFont.load_default()


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():

    api_key = os.getenv(
        "GOOGLE_API_KEY"
    )

    if not api_key:

        raise EnvironmentError(
            "GOOGLE_API_KEY is missing."
        )

    return genai.Client(
        api_key=api_key
    )


# ============================================================
# JSON CLEANER
# ============================================================

def clean_json_response(text):

    if not text:

        raise ValueError(
            "Gemini returned empty response."
        )

    text = str(text).strip()

    # Remove markdown fences
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end >= 0:

        text = text[
            start:end + 1
        ]

    return json.loads(text)


# ============================================================
# PEXELS IMAGE SEARCH
# ============================================================

def get_pexels_image(
    query,
    video_type="long"
):

    api_key = os.getenv(
        "PEXELS_API_KEY"
    )

    if not api_key:

        print(
            "⚠️ PEXELS_API_KEY missing."
        )

        return None

    if video_type == "short":

        orientation = "portrait"

    else:

        orientation = "landscape"

    motivation_keywords = [

        "motivation",

        "success",

        "discipline",

        "focus",

        "confidence",

        "determination",

        "achievement",

        "journey",

        "dream",

        "hard work",

        "courage",

    ]

    keyword = random.choice(
        motivation_keywords
    )

    search_query = (
        f"{query} {keyword}"
    )

    url = (
        "https://api.pexels.com/v1/search"
    )

    headers = {
        "Authorization": api_key
    }

    params = {

        "query": search_query,

        "orientation": orientation,

        "per_page": 15,
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        photos = data.get(
            "photos",
            []
        )

        if not photos:

            print(
                "⚠️ No Pexels image found."
            )

            return None

        photo = random.choice(
            photos
        )

        src = photo.get(
            "src",
            {}
        )

        image_url = (
            src.get("large2x")
            or src.get("large")
            or src.get("original")
        )

        if not image_url:

            return None

        image_response = requests.get(
            image_url,
            timeout=30
        )

        image_response.raise_for_status()

        return Image.open(
            BytesIO(
                image_response.content
            )
        ).convert("RGB")

    except Exception as e:

        print(
            f"⚠️ Pexels error: {e}"
        )

        return None


# ============================================================
# FALLBACK BACKGROUND
# ============================================================

def create_fallback_background(
    width,
    height
):

    image = Image.new(
        "RGB",
        (width, height),
        (10, 10, 16)
    )

    draw = ImageDraw.Draw(
        image
    )

    # Subtle gradient
    for y in range(height):

        ratio = (
            y /
            max(
                1,
                height - 1
            )
        )

        value = int(
            10 +
            ratio * 22
        )

        draw.line(
            (
                0,
                y,
                width,
                y
            ),
            fill=(
                value,
                value,
                min(
                    45,
                    value + 12
                )
            )
        )

    return image


# ============================================================
# PREPARE BACKGROUND
# ============================================================

def prepare_background(
    video_type,
    visual_query
):

    if video_type == "short":

        width = SHORT_WIDTH
        height = SHORT_HEIGHT

    else:

        width = LONG_WIDTH
        height = LONG_HEIGHT

    image = get_pexels_image(
        visual_query or "motivation",
        video_type
    )

    if image is None:

        image = (
            create_fallback_background(
                width,
                height
            )
        )

    # --------------------------------------------------------
    # Cover crop
    # --------------------------------------------------------

    source_ratio = (
        image.width /
        image.height
    )

    target_ratio = (
        width /
        height
    )

    if source_ratio > target_ratio:

        new_height = height

        new_width = int(
            height *
            source_ratio
        )

    else:

        new_width = width

        new_height = int(
            width /
            source_ratio
        )

    image = image.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )

    left = (
        new_width -
        width
    ) // 2

    top = (
        new_height -
        height
    ) // 2

    image = image.crop(
        (
            left,
            top,
            left + width,
            top + height
        )
    )

    # --------------------------------------------------------
    # Cinematic blur
    # --------------------------------------------------------

    image = image.filter(
        ImageFilter.GaussianBlur(
            radius=1.4
        )
    )

    # --------------------------------------------------------
    # Dark cinematic overlay
    # --------------------------------------------------------

    overlay = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (
            0,
            0,
            0,
            125
        )
    )

    image = Image.alpha_composite(
        image.convert("RGBA"),
        overlay
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# CURRICULUM GENERATION
# ============================================================

def generate_curriculum(
    previous_titles=None
):

    client = get_gemini_client()

    previous_titles = (
        previous_titles or []
    )

    previous_text = "\n".join(
        previous_titles[:100]
    )

    prompt = f"""
You are a professional Hindi motivational
YouTube content strategist.

Create exactly 20 fresh Hindi Motivation
video topics.

Audience:
Indian Hindi-speaking audience.

Topics can include:

- self confidence
- discipline
- consistency
- failure
- success
- hard work
- focus
- mindset
- courage
- time management
- habits
- self improvement
- overcoming fear
- persistence
- goals
- patience
- mental strength
- positive thinking

Avoid:

- AI
- Artificial Intelligence
- programming
- coding
- software
- developer
- agents
- technology tutorials
- computer tutorials

Do not repeat these previous titles:

{previous_text}

Titles should be emotionally interesting
and suitable for YouTube.

Return ONLY valid JSON:

{{
  "lessons": [
    {{
      "title": "...",
      "chapter": "1",
      "part": "1",
      "status": "pending"
    }}
  ]
}}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    return clean_json_response(
        response.text
    )


# ============================================================
# LESSON CONTENT GENERATION
# ============================================================

def generate_lesson_content(
    lesson_title
):

    client = get_gemini_client()

    prompt = f"""
You are an expert Hindi motivational
YouTube scriptwriter.

Create a powerful motivational video about:

"{lesson_title}"

The audience is Indian Hindi-speaking viewers.

The script must sound like a REAL HUMAN
motivational speaker.

STYLE:

- emotional
- natural spoken Hindi
- powerful
- conversational
- simple Hindi
- relatable
- practical
- inspiring
- no robotic AI language

Do NOT use:

- programming
- AI
- artificial intelligence
- developer terminology
- technical language
- generic filler

==================================================
LONG VIDEO
==================================================

Create 7-9 sections.

Each section:

title:
A short powerful Hindi title.

content:
45-80 words of natural spoken Hindi.

visual_query:
An English Pexels search query.

The content must flow naturally from
one section to the next.

==================================================
SHORT
==================================================

Create:

short_form_highlight:
35-60 powerful Hindi words.

short_title:
Clickable Hindi title.

short_tags:
Relevant YouTube search-intent tags.

==================================================
YOUTUBE SEO
==================================================

Generate:

title:
Clickable Hindi YouTube title.

description:
Natural Hindi YouTube description.

tags:
Relevant search-intent tags only.

hashtags:
5-8 relevant hashtags.

thumbnail_text:
2-6 powerful words.

DO NOT generate irrelevant tags like:

AI
AI:
Agents
Artificial Intelligence
Autonomous
Developer
Future
Intelligent
Next
Programming
Systems
The
Tutorial
What's
and
for
of

Return ONLY valid JSON.

Format:

{{
  "long_form_slides": [
    {{
      "title": "...",
      "content": "...",
      "visual_query": "..."
    }}
  ],

  "short_form_highlight": "...",

  "short_title": "...",

  "short_tags": [],

  "youtube": {{
    "title": "...",
    "description": "...",
    "tags": [],
    "hashtags": [],
    "thumbnail_text": "..."
  }}
}}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    return clean_json_response(
        response.text
    )


# ============================================================
# EDGE TTS
# ============================================================

def text_to_speech(
    text,
    output_path
):
    """
    Generate natural Hindi neural speech.

    Uses Edge TTS.

    Creates:

        .mp3
        .wav
        .timing.vtt
    """

    text = str(
        text or ""
    ).strip()

    if not text:

        raise ValueError(
            "TTS text is empty."
        )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Always use mp3 as Edge output
    mp3_path = output_path.with_suffix(
        ".mp3"
    )

    vtt_path = output_path.with_suffix(
        ".vtt"
    )

    timing_path = output_path.with_suffix(
        ".timing.vtt"
    )

    print(
        f"🎙️ Voice: {TTS_VOICE}"
    )

    for attempt in range(
        1,
        TTS_RETRIES + 1
    ):

        try:

            if mp3_path.exists():

                mp3_path.unlink()

            if vtt_path.exists():

                vtt_path.unlink()

            command = [

                "edge-tts",

                "--voice",
                TTS_VOICE,

                "--text",
                text,

                "--write-media",
                str(mp3_path),

                "--write-subtitles",
                str(vtt_path),
            ]

            print(
                f"🎤 TTS attempt "
                f"{attempt}/"
                f"{TTS_RETRIES}"
            )

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=180
            )

            if result.returncode != 0:

                raise RuntimeError(
                    result.stderr
                    or
                    "edge-tts command failed."
                )

            if not mp3_path.exists():

                raise FileNotFoundError(
                    "Edge TTS MP3 was not created."
                )

            # ------------------------------------------------
            # Convert MP3 to WAV
            # ------------------------------------------------

            audio = AudioSegment.from_mp3(
                mp3_path
            )

            audio.export(
                output_path,
                format="wav"
            )

            # ------------------------------------------------
            # Preserve VTT timing
            # ------------------------------------------------

            if vtt_path.exists():

                shutil.copy2(
                    vtt_path,
                    timing_path
                )

            print(
                f"✅ Hindi neural voice created: "
                f"{output_path}"
            )

            return output_path

        except Exception as e:

            print(
                f"⚠️ TTS error: {e}"
            )

            if attempt < TTS_RETRIES:

                wait_time = (
                    TTS_BACKOFF *
                    attempt
                )

                print(
                    f"⏳ Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(
                    wait_time
                )

    raise RuntimeError(
        "Hindi neural TTS failed after "
        f"{TTS_RETRIES} attempts."
    )


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(
    draw,
    text,
    font,
    max_width
):

    words = str(
        text or ""
    ).split()

    lines = []

    current = ""

    for word in words:

        test = (
            f"{current} {word}"
            .strip()
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        width = (
            bbox[2] -
            bbox[0]
        )

        if width <= max_width:

            current = test

        else:

            if current:

                lines.append(
                    current
                )

            current = word

    if current:

        lines.append(
            current
        )

    return lines


# ============================================================
# GENERATE VISUAL
# ============================================================

def generate_visuals(
    output_dir,
    video_type,
    slide_content=None,
    slide_number=None,
    total_slides=None,
    thumbnail_title=None
):

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # THUMBNAIL
    # ========================================================

    if thumbnail_title is not None:

        width = 1280
        height = 720

        # Use random motivational background
        image = prepare_background(
            "long",
            "motivational success person"
        )

        draw = ImageDraw.Draw(
            image
        )

        title_font = get_font(
            78
        )

        brand_font = get_font(
            32
        )

        text = str(
            thumbnail_title
        ).strip()

        # Limit thumbnail text
        if len(text) > 80:

            text = text[:77] + "..."

        lines = wrap_text(
            draw,
            text,
            title_font,
            1050
        )

        line_height = 95

        total_height = (
            len(lines) *
            line_height
        )

        y = (
            height -
            total_height
        ) // 2 - 20

        for line in lines:

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=title_font
            )

            text_width = (
                bbox[2] -
                bbox[0]
            )

            x = (
                width -
                text_width
            ) // 2

            # Black outline
            draw.text(
                (
                    x,
                    y
                ),
                line,
                font=title_font,
                fill="white",
                stroke_width=9,
                stroke_fill="black"
            )

            y += line_height

        # ----------------------------------------------------
        # Branding
        # ----------------------------------------------------

        brand = (
            f"{YOUR_NAME} • "
            f"{CHANNEL_NICHE}"
        )

        bbox = draw.textbbox(
            (0, 0),
            brand,
            font=brand_font
        )

        brand_width = (
            bbox[2] -
            bbox[0]
        )

        draw.text(
            (
                (width - brand_width) // 2,
                650
            ),
            brand,
            font=brand_font,
            fill="white",
            stroke_width=3,
            stroke_fill="black"
        )

        # ----------------------------------------------------
        # JPEG thumbnail
        # ----------------------------------------------------

        path = (
            output_dir /
            "thumbnail.jpg"
        )

        image.save(
            path,
            "JPEG",
            quality=90,
            optimize=True
        )

        print(
            f"🖼️ Thumbnail created: "
            f"{path}"
        )

        return path

    # ========================================================
    # NORMAL SLIDE
    # ========================================================

    slide_content = (
        slide_content or {}
    )

    title = str(
        slide_content.get(
            "title",
            ""
        )
    ).strip()

    content = str(
        slide_content.get(
            "content",
            ""
        )).strip()

    visual_query = str(
        slide_content.get(
            "visual_query",
            "motivation"
        )).strip()

    if video_type == "short":

        width = SHORT_WIDTH
        height = SHORT_HEIGHT

    else:

        width = LONG_WIDTH
        height = LONG_HEIGHT

    image = prepare_background(
        video_type,
        visual_query
    )

    draw = ImageDraw.Draw(
        image
    )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if video_type == "short":

        title_font = get_font(
            58
        )

        title_y = 100

    else:

        title_font = get_font(
            58
        )

        title_y = 55

    title_lines = wrap_text(
        draw,
        title,
        title_font,
        int(
            width * 0.82
        )
    )

    y = title_y

    for line in title_lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=title_font
        )

        text_width = (
            bbox[2] -
            bbox[0]
        )

        x = (
            width -
            text_width
        ) // 2

        draw.text(
            (
                x,
                y
            ),
            line,
            font=title_font,
            fill="white",
            stroke_width=4,
            stroke_fill="black"
        )

        y += 72

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    footer_font = get_font(
        26
    )

    footer = (
        f"{YOUR_NAME} • "
        f"{CHANNEL_NICHE}"
    )

    bbox = draw.textbbox(
        (0, 0),
        footer,
        font=footer_font
    )

    footer_width = (
        bbox[2] -
        bbox[0]
    )

    draw.text(
        (
            (width - footer_width) // 2,
            height - 65
        ),
        footer,
        font=footer_font,
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    # --------------------------------------------------------
    # SLIDE NUMBER
    # --------------------------------------------------------

    if (
        slide_number
        and
        total_slides
    ):

        number_font = get_font(
            24
        )

        number_text = (
            f"{slide_number}/"
            f"{total_slides}"
        )

        draw.text(
            (
                35,
                30
            ),
            number_text,
            font=number_font,
            fill="white",
            stroke_width=2,
            stroke_fill="black"
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    if slide_number is None:

        slide_number = 1

    path = (
        output_dir /
        f"slide_{slide_number:02d}.png"
    )

    image.save(
        path,
        "PNG"
    )

    print(
        f"🖼️ Slide created: "
        f"{path}"
    )

    return path


# ============================================================
# VTT TIME PARSER
# ============================================================

def vtt_time_to_seconds(
    value
):

    value = value.strip()

    parts = value.split(":")

    if len(parts) == 3:

        hours = float(
            parts[0]
        )

        minutes = float(
            parts[1]
        )

        seconds = float(
            parts[2]
        )

    elif len(parts) == 2:

        hours = 0

        minutes = float(
            parts[0]
        )

        seconds = float(
            parts[1]
        )

    else:

        return 0.0

    return (
        hours * 3600
        +
        minutes * 60
        +
        seconds
    )


# ============================================================
# PARSE VTT
# ============================================================

def parse_vtt(
    vtt_path
):

    path = Path(
        vtt_path
    )

    if not path.exists():

        return []

    try:

        text = path.read_text(
            encoding="utf-8"
        )

    except Exception:

        return []

    pattern = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}\.\d{3}"
        r"|\d{1,2}:\d{2}\.\d{3})"
        r"\s+-->\s+"
        r"(\d{1,2}:\d{2}:\d{2}\.\d{3}"
        r"|\d{1,2}:\d{2}\.\d{3})"
        r"\s*\n"
        r"(.+?)(?=\n\n|\Z)",
        re.DOTALL
    )

    results = []

    for match in pattern.finditer(
        text
    ):

        start_text = match.group(
            1
        )

        end_text = match.group(
            2
        )

        caption = match.group(
            3
        ).strip()

        caption = re.sub(
            r"<[^>]+>",
            "",
            caption
        )

        caption = re.sub(
            r"\s+",
            " ",
            caption
        ).strip()

        if not caption:

            continue

        start = vtt_time_to_seconds(
            start_text
        )

        end = vtt_time_to_seconds(
            end_text
        )

        if end <= start:

            continue

        results.append(
            {
                "start": start,
                "end": end,
                "text": caption
            }
        )

    return results


# ============================================================
# FALLBACK TIMINGS
# ============================================================

def create_fallback_timings(
    text,
    duration
):

    words = str(
        text or ""
    ).split()

    if not words:

        return []

    chunks = []

    for i in range(
        0,
        len(words),
        WORDS_PER_HIGHLIGHT
    ):

        chunk = " ".join(
            words[
                i:i +
                WORDS_PER_HIGHLIGHT
            ]
        )

        chunks.append(
            chunk
        )

    total_words = max(
        1,
        len(words)
    )

    timings = []

    current = 0.0

    for chunk in chunks:

        count = len(
            chunk.split()
        )

        chunk_duration = (
            duration *
            count /
            total_words
        )

        timings.append(
            {
                "start": current,
                "end": (
                    current +
                    chunk_duration
                ),
                "text": chunk
            }
        )

        current += chunk_duration

    return timings


# ============================================================
# GET TEXT TIMINGS
# ============================================================

def get_text_timings(
    script,
    audio_path
):

    audio = AudioSegment.from_file(
        audio_path
    )

    duration = (
        len(audio) /
        1000.0
    )

    timing_path = Path(
        audio_path
    ).with_suffix(
        ".timing.vtt"
    )

    timings = parse_vtt(
        timing_path
    )

    if not timings:

        print(
            "⚠️ VTT timing unavailable."
        )

        print(
            "🔄 Using estimated speech timing."
        )

        return create_fallback_timings(
            script,
            duration
        )

    cleaned = []

    for item in timings:

        text = re.sub(
            r"\s+",
            " ",
            item["text"]
        ).strip()

        if not text:

            continue

        start = max(
            0,
            item["start"]
        )

        end = min(
            duration,
            item["end"]
        )

        if end <= start:

            continue

        cleaned.append(
            {
                "start": start,
                "end": end,
                "text": text
            }
        )

    if not cleaned:

        return create_fallback_timings(
            script,
            duration
        )

    return cleaned


# ============================================================
# CURRENT TEXT CHUNK
# ============================================================

def get_current_timing(
    timings,
    current_time
):

    if not timings:

        return None

    for item in timings:

        if (
            item["start"]
            <= current_time
            <= item["end"]
        ):

            return item

    return None


# ============================================================
# ANIMATED TEXT FRAME
# ============================================================

def make_animated_frame(
    base_image,
    timings,
    current_time,
    video_type
):

    frame = base_image.copy()

    width, height = frame.size

    draw = ImageDraw.Draw(
        frame
    )

    # --------------------------------------------------------
    # Position / font
    # --------------------------------------------------------

    if video_type == "short":

        text_font = get_font(
            68
        )

        max_width = int(
            width * 0.82
        )

        text_center_y = int(
            height * 0.46
        )

        line_height = 84

    else:

        text_font = get_font(
            64
        )

        max_width = int(
            width * 0.78
        )

        text_center_y = int(
            height * 0.47
        )

        line_height = 78

    current = get_current_timing(
        timings,
        current_time
    )

    if current is None:

        return frame

    text = current["text"]

    # --------------------------------------------------------
    # Animation progress
    # --------------------------------------------------------

    local_time = (
        current_time -
        current["start"]
    )

    progress = min(
        1.0,
        max(
            0.0,
            local_time /
            TEXT_ANIMATION_IN
        )
    )

    # Cubic ease out
    eased = (
        1 -
        (1 - progress) ** 3
    )

    # Scale
    scale = (
        0.88 +
        0.12 * eased
    )

    # Opacity
    alpha = int(
        255 * eased
    )

    # Slight vertical movement
    movement = int(
        20 *
        (1 - eased)
    )

    # --------------------------------------------------------
    # Text lines
    # --------------------------------------------------------

    lines = wrap_text(
        draw,
        text,
        text_font,
        max_width
    )

    total_height = (
        len(lines) *
        line_height
    )

    start_y = (
        text_center_y -
        total_height // 2
        +
        movement
    )

    # --------------------------------------------------------
    # Transparent overlay
    # --------------------------------------------------------

    overlay = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    overlay_draw = ImageDraw.Draw(
        overlay
    )

    y = start_y

    for line in lines:

        bbox = overlay_draw.textbbox(
            (0, 0),
            line,
            font=text_font
        )

        text_width = (
            bbox[2] -
            bbox[0]
        )

        x = (
            width -
            text_width
        ) // 2

        # ----------------------------------------------------
        # Highlight box
        # ----------------------------------------------------

        padding_x = 28
        padding_y = 14

        rect = (
            x - padding_x,
            y - padding_y,
            x + text_width +
            padding_x,
            y +
            line_height -
            8
        )

        overlay_draw.rounded_rectangle(
            rect,
            radius=18,
            fill=(
                0,
                0,
                0,
                int(
                    175 *
                    eased
                )
            )
        )

        # ----------------------------------------------------
        # Text
        # ----------------------------------------------------

        overlay_draw.text(
            (
                x,
                y
            ),
            line,
            font=text_font,
            fill=(
                255,
                220,
                80,
                alpha
            ),
            stroke_width=4,
            stroke_fill=(
                0,
                0,
                0,
                alpha
            )
        )

        y += line_height

    # --------------------------------------------------------
    # Scale animation
    # --------------------------------------------------------

    if abs(
        scale - 1.0
    ) > 0.001:

        new_width = int(
            width *
            scale
        )

        new_height = int(
            height *
            scale
        )

        scaled = overlay.resize(
            (
                new_width,
                new_height
            ),
            Image.Resampling.LANCZOS
        )

        centered = Image.new(
            "RGBA",
            (
                width,
                height
            ),
            (
                0,
                0,
                0,
                0
            )
        )

        centered.alpha_composite(
            scaled,
            (
                (
                    width -
                    new_width
                ) // 2,
                (
                    height -
                    new_height
                ) // 2
            )
        )

        overlay = centered

    # --------------------------------------------------------
    # Composite
    # --------------------------------------------------------

    frame = Image.alpha_composite(
        frame.convert("RGBA"),
        overlay
    )

    return frame.convert(
        "RGB"
    )


# ============================================================
# CREATE VIDEO
# ============================================================

def create_video(
    slide_paths,
    audio_paths,
    output_path,
    video_type,
    slide_scripts=None
):
    """
    Create final video.

    slide_scripts:
        Spoken script for each slide.

    Text timing is generated from Edge TTS VTT
    whenever available.
    """

    if not slide_paths:

        raise ValueError(
            "No slide paths supplied."
        )

    if not audio_paths:

        raise ValueError(
            "No audio paths supplied."
        )

    if len(slide_paths) != len(
        audio_paths
    ):

        raise ValueError(
            "Slide/audio count mismatch."
        )

    if slide_scripts is None:

        slide_scripts = [
            ""
            for _ in slide_paths
        ]

    if len(slide_scripts) != len(
        slide_paths
    ):

        raise ValueError(
            "Slide/script count mismatch."
        )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        "\n🎬 ====================================="
    )

    print(
        "🎬 Creating animated motivational video"
    )

    print(
        "🎬 ====================================="
    )

    clips = []

    voice_audio_clips = []

    # ========================================================
    # PROCESS EACH SLIDE
    # ========================================================

    for index, (
        slide_path,
        audio_path,
        script
    ) in enumerate(
        zip(
            slide_paths,
            audio_paths,
            slide_scripts
        )
    ):

        print(
            f"\n🎞️ Slide "
            f"{index + 1}/"
            f"{len(slide_paths)}"
        )

        # ----------------------------------------------------
        # Audio
        # ----------------------------------------------------

        audio = AudioFileClip(
            str(audio_path)
        )

        audio_duration = (
            audio.duration
        )

        # Small breathing room
        duration = (
            audio_duration +
            0.45
        )

        # ----------------------------------------------------
        # Image
        # ----------------------------------------------------

        base_image = Image.open(
            slide_path
        ).convert(
            "RGB"
        )

        # ----------------------------------------------------
        # Text timings
        # ----------------------------------------------------

        timings = get_text_timings(
            script,
            audio_path
        )

        print(
            f"📝 Text timing chunks: "
            f"{len(timings)}"
        )

        # ----------------------------------------------------
        # Frame function
        # ----------------------------------------------------

        def make_frame(
            t,
            base=base_image.copy(),
            timing_data=timings,
            vt=video_type
        ):

            if t >= audio_duration:

                local_time = max(
                    0,
                    audio_duration -
                    0.05
                )

            else:

                local_time = t

            return make_animated_frame(
                base,
                timing_data,
                local_time,
                vt
            )

        # ----------------------------------------------------
        # MoviePy VideoClip
        # ----------------------------------------------------

        clip = VideoClip(
            make_frame=make_frame,
            duration=duration
        )

        clip = clip.set_audio(
            audio
        )

        # ----------------------------------------------------
        # Fade
        # ----------------------------------------------------

        clip = clip.fx(
            vfx.fadein,
            0.20
        )

        clip = clip.fx(
            vfx.fadeout,
            0.20
        )

        clips.append(
            clip
        )

        voice_audio_clips.append(
            audio
        )

    # ========================================================
    # JOIN SLIDES
    # ========================================================

    print(
        "\n🔗 Joining animated slides..."
    )

    final_video = concatenate_videoclips(
        clips,
        method="compose"
    )

    # ========================================================
    # BACKGROUND MUSIC
    # ========================================================

    audio_layers = list(
        voice_audio_clips
    )

    music = None
    music_parts = []

    if MUSIC_PATH.exists():

        try:

            print(
                "🎵 Adding background music..."
            )

            original_music = (
                AudioFileClip(
                    str(MUSIC_PATH)
                )
            )

            remaining = (
                final_video.duration
            )

            current = 0

            while remaining > 0:

                segment_duration = min(
                    original_music.duration,
                    remaining
                )

                segment = (
                    original_music
                    .subclip(
                        0,
                        segment_duration
                    )
                    .volumex(
                        BACKGROUND_MUSIC_VOLUME
                    )
                )

                music_parts.append(
                    segment
                )

                remaining -= (
                    segment.duration
                )

                current += (
                    segment.duration
                )

            if music_parts:

                if len(music_parts) == 1:

                    music = music_parts[0]

                else:

                    music = (
                        concatenate_audioclips(
                            music_parts
                        )
                    )

                audio_layers.append(
                    music
                )

        except Exception as e:

            print(
                f"⚠️ Background music "
                f"failed: {e}"
            )

    else:

        print(
            f"ℹ️ Background music not found: "
            f"{MUSIC_PATH}"
        )

    # ========================================================
    # FINAL AUDIO
    # ========================================================

    print(
        "🎚️ Mixing voice + background music..."
    )

    mixed_audio = CompositeAudioClip(
        audio_layers
    )

    final_video = final_video.set_audio(
        mixed_audio
    )

    # ========================================================
    # RENDER
    # ========================================================

    print(
        "\n💾 Rendering MP4..."
    )

    print(
        f"📁 Output: {output_path}"
    )

    final_video.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="5000k",
        threads=2,
        logger="bar"
    )

    # ========================================================
    # CLEANUP
    # ========================================================

    print(
        "\n🧹 Cleaning MoviePy resources..."
    )

    try:

        final_video.close()

    except Exception:

        pass

    for clip in clips:

        try:

            clip.close()

        except Exception:

            pass

    for audio in voice_audio_clips:

        try:

            audio.close()

        except Exception:

            pass

    if music:

        try:

            music.close()

        except Exception:

            pass

    for part in music_parts:

        try:

            part.close()

        except Exception:

            pass

    print(
        "\n✅ ====================================="
    )

    print(
        f"✅ VIDEO CREATED: {output_path}"
    )

    print(
        "✅ ====================================="
    )

    return output_path


# ============================================================
# END
# ============================================================
