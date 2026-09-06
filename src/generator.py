# ============================================================
# FILE: src/generator.py
# ============================================================
#
# HINDI MOTIVATION YOUTUBE AUTOMATION
#
# Features:
#   Gemini API
#   Gemini 503/429/5xx retry
#   Edge TTS Hindi neural voice
#   VTT timing support + fallback
#   Animated kinetic typography
#   Speech-synced text
#   Long-form videos
#   YouTube Shorts
#   Pexels visuals
#   Cinematic background
#   Background music
#   Professional thumbnails
#   Hindi / Devanagari font detection
#   MoviePy NumPy frame fix
#   SAFE MOVIEPY AUDIO HANDLING
#   GitHub Actions compatible
#
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
import numpy as np

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


# ============================================================
# GEMINI
# ============================================================

GEMINI_MODEL = "gemini-3.6-flash"

GEMINI_RETRIES = 6

GEMINI_INITIAL_BACKOFF = 5

GEMINI_MAX_BACKOFF = 60


# ============================================================
# EDGE TTS
# ============================================================

TTS_LANGUAGE = "hi"

TTS_VOICE = "hi-IN-MadhurNeural"

TTS_RETRIES = 5

TTS_BACKOFF = 5


# ============================================================
# VIDEO
# ============================================================

LONG_WIDTH = 1920
LONG_HEIGHT = 1080

SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920

FPS = 24


# ============================================================
# TEXT
# ============================================================

WORDS_PER_HIGHLIGHT = 3

TEXT_ANIMATION_IN = 0.22


# ============================================================
# AUDIO
# ============================================================

BACKGROUND_MUSIC_VOLUME = 0.065


# ============================================================
# SEO
# ============================================================

MAX_TAGS = 25


# ============================================================
# FONT
# ============================================================

def find_hindi_font():

    candidates = [

        ASSETS_PATH /
        "fonts" /
        "NotoSansDevanagari-Regular.ttf",

        ASSETS_PATH /
        "fonts" /
        "NotoSansDevanagari-Medium.ttf",

        ASSETS_PATH /
        "fonts" /
        "NotoSansDevanagari-Bold.ttf",

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

        Path(
            "/usr/share/fonts/opentype/noto/"
            "NotoSansDevanagari-Medium.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/noto/"
            "NotoSansDevanagari-Bold.ttf"
        ),

        Path(
            "/usr/share/fonts/opentype/noto/"
            "NotoSansDevanagari-Bold.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/"
            "lohit-devanagari/"
            "Lohit-Devanagari.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),

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
# GEMINI ERROR DETECTION
# ============================================================

def is_retryable_gemini_error(error):

    error_text = str(
        error
    ).upper()

    status_code = getattr(
        error,
        "status_code",
        None
    )

    retryable_status_codes = {
        429,
        500,
        502,
        503,
        504,
    }

    if status_code in retryable_status_codes:

        return True

    retryable_messages = [

        "429",
        "500",
        "502",
        "503",
        "504",

        "UNAVAILABLE",

        "RESOURCE_EXHAUSTED",

        "INTERNAL",

        "BAD_GATEWAY",

        "DEADLINE_EXCEEDED",

        "SERVICE UNAVAILABLE",

        "HIGH DEMAND",

        "TEMPORARILY UNAVAILABLE",

        "OVERLOADED",
    ]

    return any(
        message in error_text
        for message in retryable_messages
    )


# ============================================================
# SAFE GEMINI GENERATION
# ============================================================

def generate_gemini_content(prompt):

    client = get_gemini_client()

    last_error = None

    for attempt in range(
        1,
        GEMINI_RETRIES + 1
    ):

        try:

            print(
                "\n🤖 ====================================="
            )

            print(
                f"🤖 Gemini attempt "
                f"{attempt}/"
                f"{GEMINI_RETRIES}"
            )

            print(
                f"🤖 Model: {GEMINI_MODEL}"
            )

            print(
                "🤖 ====================================="
            )

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

            if response is None:

                raise RuntimeError(
                    "Gemini returned None response."
                )

            response_text = getattr(
                response,
                "text",
                None
            )

            if not response_text:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            print(
                "✅ Gemini response received."
            )

            return response

        except Exception as error:

            last_error = error

            print(
                "\n⚠️ ====================================="
            )

            print(
                "⚠️ Gemini request failed"
            )

            print(
                f"⚠️ Error: {error}"
            )

            print(
                "⚠️ ====================================="
            )

            if not is_retryable_gemini_error(
                error
            ):

                print(
                    "❌ Non-retryable Gemini error."
                )

                raise

            if attempt >= GEMINI_RETRIES:

                print(
                    "❌ Gemini failed after "
                    f"{GEMINI_RETRIES} attempts."
                )

                break

            backoff = min(
                GEMINI_INITIAL_BACKOFF *
                (
                    2 ** (
                        attempt - 1
                    )
                ),
                GEMINI_MAX_BACKOFF
            )

            jitter = random.uniform(
                0,
                3
            )

            wait_time = (
                backoff +
                jitter
            )

            print(
                "⏳ Gemini is temporarily "
                "unavailable."
            )

            print(
                f"🔄 Retrying in "
                f"{wait_time:.1f} seconds..."
            )

            time.sleep(
                wait_time
            )

    raise RuntimeError(
        "Gemini API remained unavailable "
        f"after {GEMINI_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


# ============================================================
# JSON CLEANER
# ============================================================

def clean_json_response(text):

    if not text:

        raise ValueError(
            "Gemini returned empty response."
        )

    text = str(
        text
    ).strip()

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

    start = text.find("{")

    end = text.rfind("}")

    if start >= 0 and end >= 0:

        text = text[
            start:end + 1
        ]

    return json.loads(text)


# ============================================================
# PEXELS
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

    orientation = (
        "portrait"
        if video_type == "short"
        else "landscape"
    )

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
            or
            src.get("large")
            or
            src.get("original")
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
        (
            width,
            height
        ),
        (
            10,
            10,
            16
        )
    )

    draw = ImageDraw.Draw(
        image
    )

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

        image = create_fallback_background(
            width,
            height
        )

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

    image = image.filter(
        ImageFilter.GaussianBlur(
            radius=1.4
        )
    )

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

    return image.convert("RGB")


# ============================================================
# CURRICULUM
# ============================================================

def generate_curriculum(
    previous_titles=None
):

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

    response = generate_gemini_content(
        prompt
    )

    return clean_json_response(
        response.text
    )


# ============================================================
# LESSON CONTENT
# ============================================================

def generate_lesson_content(
    lesson_title
):

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

    response = generate_gemini_content(
        prompt
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

            for path in [
                mp3_path,
                vtt_path,
                timing_path,
                output_path,
            ]:

                if path.exists():

                    try:
                        path.unlink()
                    except Exception:
                        pass

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
                    result.stderr or
                    "edge-tts command failed."
                )

            if not mp3_path.exists():

                raise FileNotFoundError(
                    "Edge TTS MP3 was not created."
                )

            audio = AudioSegment.from_mp3(
                mp3_path
            )

            audio.export(
                output_path,
                format="wav"
            )

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
        ).strip()

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
# GENERATE VISUALS
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

        image = prepare_background(
            "long",
            "motivational success person"
        )

        draw = ImageDraw.Draw(
            image
        )

        title_font = get_font(78)

        brand_font = get_font(32)

        text = str(
            thumbnail_title
        ).strip()

        if len(text) > 80:

            text = (
                text[:77] +
                "..."
            )

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
                (
                    width -
                    brand_width
                ) // 2,
                650
            ),
            brand,
            font=brand_font,
            fill="white",
            stroke_width=3,
            stroke_fill="black"
        )

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
            f"🖼️ Thumbnail created: {path}"
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

    visual_query = str(
        slide_content.get(
            "visual_query",
            "motivation"
        )
    ).strip()

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

    if video_type == "short":

        title_font = get_font(58)

        title_y = 100

    else:

        title_font = get_font(58)

        title_y = 55

    title_lines = wrap_text(
        draw,
        title,
        title_font,
        int(width * 0.82)
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

    footer_font = get_font(26)

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
            (
                width -
                footer_width
            ) // 2,
            height - 65
        ),
        footer,
        font=footer_font,
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    if (
        slide_number
        and
        total_slides
    ):

        number_font = get_font(24)

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
        f"🖼️ Slide created: {path}"
    )

    return path


# ============================================================
# VTT TIME
# ============================================================

def vtt_time_to_seconds(value):

    value = value.strip()

    parts = value.split(":")

    try:

        if len(parts) == 3:

            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])

        elif len(parts) == 2:

            hours = 0
            minutes = float(parts[0])
            seconds = float(parts[1])

        else:

            return 0.0

        return (
            hours * 3600 +
            minutes * 60 +
            seconds
        )

    except Exception:

        return 0.0


# ============================================================
# PARSE VTT
# ============================================================

def parse_vtt(vtt_path):

    path = Path(vtt_path)

    if not path.exists():

        return []

    try:

        text = path.read_text(
            encoding="utf-8"
        )

    except Exception:

        return []

    text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    pattern = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}\.\d{3}"
        r"|\d{1,2}:\d{2}\.\d{3})"
        r"\s*-->\s*"
        r"(\d{1,2}:\d{2}:\d{2}\.\d{3}"
        r"|\d{1,2}:\d{2}\.\d{3})"
        r"[^\n]*\n"
        r"(.*?)(?=\n\s*\n|\Z)",
        re.DOTALL
    )

    results = []

    for match in pattern.finditer(text):

        start_text = match.group(1)

        end_text = match.group(2)

        caption = match.group(3).strip()

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

    duration = max(
        0.1,
        float(duration)
    )

    chunks = []

    for i in range(
        0,
        len(words),
        WORDS_PER_HIGHLIGHT
    ):

        chunk_words = words[
            i:
            i + WORDS_PER_HIGHLIGHT
        ]

        chunks.append(
            " ".join(chunk_words)
        )

    total_words = len(words)

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

        end = min(
            duration,
            current +
            chunk_duration
        )

        timings.append(
            {
                "start": current,
                "end": end,
                "text": chunk
            }
        )

        current = end

    if timings:

        timings[-1]["end"] = duration

    return timings


# ============================================================
# TEXT TIMINGS
# ============================================================

def get_text_timings(
    script,
    audio_path
):

    try:

        audio = AudioSegment.from_file(
            audio_path
        )

        duration = (
            len(audio) /
            1000.0
        )

    except Exception as e:

        print(
            f"⚠️ Could not read audio "
            f"duration: {e}"
        )

        duration = 1.0

    timing_candidates = [

        Path(audio_path).with_suffix(
            ".timing.vtt"
        ),

        Path(audio_path).with_suffix(
            ".vtt"
        ),
    ]

    timings = []

    for timing_path in timing_candidates:

        if timing_path.exists():

            timings = parse_vtt(
                timing_path
            )

            if timings:

                print(
                    f"✅ VTT timing loaded: "
                    f"{timing_path}"
                )

                break

    if not timings:

        print(
            "⚠️ VTT timing unavailable."
        )

        print(
            "🔄 Using estimated speech timing."
        )

        timings = create_fallback_timings(
            script,
            duration
        )

    cleaned = []

    for item in timings:

        text = re.sub(
            r"\s+",
            " ",
            item.get("text", "")
        ).strip()

        if not text:

            continue

        start = max(
            0.0,
            float(
                item.get(
                    "start",
                    0
                )
            )
        )

        end = min(
            duration,
            float(
                item.get(
                    "end",
                    duration
                )
            )
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

        print(
            "⚠️ Timing parser produced "
            "no chunks."
        )

        cleaned = create_fallback_timings(
            script,
            duration
        )

    print(
        f"📝 Final timing chunks: "
        f"{len(cleaned)}"
    )

    return cleaned


# ============================================================
# CURRENT TIMING
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

    previous = None

    for item in timings:

        if item["start"] <= current_time:

            previous = item

        else:

            break

    return previous


# ============================================================
# ANIMATED FRAME
# ============================================================

def make_animated_frame(
    base_image,
    timings,
    current_time,
    video_type
):

    frame = base_image.copy()

    width, height = frame.size

    draw = ImageDraw.Draw(frame)

    if video_type == "short":

        text_font = get_font(68)

        max_width = int(
            width * 0.82
        )

        text_center_y = int(
            height * 0.46
        )

        line_height = 84

    else:

        text_font = get_font(64)

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

        return frame.convert("RGB")

    text = current.get(
        "text",
        ""
    )

    if not text:

        return frame.convert("RGB")

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

    eased = (
        1 -
        (
            1 -
            progress
        ) ** 3
    )

    scale = (
        0.88 +
        0.12 * eased
    )

    alpha = int(
        255 * eased
    )

    movement = int(
        20 *
        (
            1 -
            eased
        )
    )

    lines = wrap_text(
        draw,
        text,
        text_font,
        max_width
    )

    if not lines:

        return frame.convert("RGB")

    total_height = (
        len(lines) *
        line_height
    )

    start_y = (
        text_center_y -
        total_height // 2 +
        movement
    )

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

        padding_x = 28
        padding_y = 14

        rect = (
            x - padding_x,
            y - padding_y,
            x + text_width + padding_x,
            y + line_height - 8
        )

        overlay_draw.rounded_rectangle(
            rect,
            radius=18,
            fill=(
                0,
                0,
                0,
                int(175 * eased)
            )
        )

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

    if abs(
        scale - 1.0
    ) > 0.001:

        new_width = max(
            1,
            int(width * scale)
        )

        new_height = max(
            1,
            int(height * scale)
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

    frame = Image.alpha_composite(
        frame.convert("RGBA"),
        overlay
    )

    return frame.convert("RGB")


# ============================================================
# NUMPY FRAME
# ============================================================

def pil_to_numpy_frame(image):

    if not isinstance(
        image,
        Image.Image
    ):

        image = Image.fromarray(
            np.asarray(image)
        )

    image = image.convert("RGB")

    array = np.asarray(
        image,
        dtype=np.uint8
    )

    if array.ndim != 3:

        raise ValueError(
            f"Invalid video frame shape: "
            f"{array.shape}"
        )

    if array.shape[2] != 3:

        raise ValueError(
            "Video frame must have "
            f"3 channels, got: "
            f"{array.shape}"
        )

    return array


# ============================================================
# SAFE AUDIO VALIDATION
# ============================================================

def validate_audio_file(
    audio_path
):

    path = Path(audio_path)

    if not path.exists():

        raise FileNotFoundError(
            f"Audio file not found: {path}"
        )

    if path.stat().st_size < 1024:

        raise RuntimeError(
            f"Audio file is too small or invalid: "
            f"{path}"
        )

    try:

        audio = AudioFileClip(
            str(path)
        )

        duration = float(
            audio.duration or 0
        )

        if duration <= 0:

            audio.close()

            raise RuntimeError(
                f"Audio duration is invalid: "
                f"{path}"
            )

        audio.close()

        return duration

    except Exception as e:

        raise RuntimeError(
            f"Could not validate audio "
            f"{path}: {e}"
        )


# ============================================================
# SAFE BACKGROUND MUSIC
# ============================================================

def create_background_music(
    music_path,
    target_duration
):

    """
    Create background music safely.

    IMPORTANT:
    The source AudioFileClip stays open until
    the final video rendering is finished.

    We DO NOT close the source music reader early.
    """

    if not Path(
        music_path
    ).exists():

        print(
            f"ℹ️ Background music not found: "
            f"{music_path}"
        )

        return None, None

    try:

        print(
            "🎵 Loading background music..."
        )

        source_music = AudioFileClip(
            str(music_path)
        )

        source_duration = float(
            source_music.duration or 0
        )

        if source_duration <= 0:

            source_music.close()

            print(
                "⚠️ Background music has "
                "invalid duration."
            )

            return None, None

        target_duration = float(
            target_duration
        )

        parts = []

        remaining = target_duration

        while remaining > 0:

            segment_duration = min(
                source_duration,
                remaining
            )

            part = (
                source_music
                .subclip(
                    0,
                    segment_duration
                )
                .volumex(
                    BACKGROUND_MUSIC_VOLUME
                )
            )

            parts.append(
                part
            )

            remaining -= (
                segment_duration
            )

        if not parts:

            source_music.close()

            return None, None

        if len(parts) == 1:

            music = parts[0]

        else:

            music = concatenate_audioclips(
                parts
            )

        print(
            f"✅ Background music prepared "
            f"for {target_duration:.2f}s"
        )

        # Return BOTH music and source.
        # Source MUST stay open during render.
        return music, source_music

    except Exception as e:

        print(
            f"⚠️ Background music failed: "
            f"{e}"
        )

        return None, None


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

    if not slide_paths:

        raise ValueError(
            "No slide paths supplied."
        )

    if not audio_paths:

        raise ValueError(
            "No audio paths supplied."
        )

    if len(slide_paths) != len(audio_paths):

        raise ValueError(
            "Slide/audio count mismatch."
        )

    if slide_scripts is None:

        slide_scripts = [
            ""
            for _ in slide_paths
        ]

    if len(slide_scripts) != len(slide_paths):

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

    music = None

    music_source = None

    music_parts = []

    final_video = None

    mixed_audio = None

    # ========================================================
    # PROCESS SLIDES
    # ========================================================

    try:

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

            # ------------------------------------------------
            # Validate audio BEFORE MoviePy
            # ------------------------------------------------

            validate_audio_file(
                audio_path
            )

            # ------------------------------------------------
            # Load voice audio
            # ------------------------------------------------

            audio = AudioFileClip(
                str(audio_path)
            )

            if audio.duration is None:

                audio.close()

                raise RuntimeError(
                    f"Audio duration unavailable: "
                    f"{audio_path}"
                )

            audio_duration = float(
                audio.duration
            )

            if audio_duration <= 0:

                audio.close()

                raise RuntimeError(
                    f"Audio duration invalid: "
                    f"{audio_path}"
                )

            duration = (
                audio_duration +
                0.45
            )

            print(
                f"🔊 Audio duration: "
                f"{audio_duration:.2f}s"
            )

            # ------------------------------------------------
            # Image
            # ------------------------------------------------

            base_image = Image.open(
                slide_path
            ).convert("RGB")

            expected_size = (

                (
                    SHORT_WIDTH,
                    SHORT_HEIGHT
                )

                if video_type == "short"

                else

                (
                    LONG_WIDTH,
                    LONG_HEIGHT
                )
            )

            if (
                base_image.size
                !=
                expected_size
            ):

                base_image = base_image.resize(
                    expected_size,
                    Image.Resampling.LANCZOS
                )

            # ------------------------------------------------
            # Timing
            # ------------------------------------------------

            timings = get_text_timings(
                script,
                audio_path
            )

            print(
                f"📝 Text timing chunks: "
                f"{len(timings)}"
            )

            # ------------------------------------------------
            # Frame function
            # ------------------------------------------------

            def make_frame(
                t,
                base=base_image.copy(),
                timing_data=timings,
                vt=video_type,
                audio_len=audio_duration
            ):

                if t >= audio_len:

                    local_time = max(
                        0.0,
                        audio_len - 0.05
                    )

                else:

                    local_time = max(
                        0.0,
                        float(t)
                    )

                pil_frame = make_animated_frame(
                    base,
                    timing_data,
                    local_time,
                    vt
                )

                return pil_to_numpy_frame(
                    pil_frame
                )

            # ------------------------------------------------
            # Video clip
            # ------------------------------------------------

            clip = VideoClip(
                make_frame=make_frame,
                duration=duration
            )

            clip = clip.set_audio(
                audio
            )

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

            # IMPORTANT:
            # Keep this AudioFileClip open until
            # rendering has completely finished.
            voice_audio_clips.append(
                audio
            )

        # ====================================================
        # JOIN SLIDES
        # ====================================================

        print(
            "\n🔗 Joining animated slides..."
        )

        final_video = concatenate_videoclips(
            clips,
            method="compose"
        )

        print(
            f"⏱️ Final video duration: "
            f"{final_video.duration:.2f}s"
        )

        # ====================================================
        # BACKGROUND MUSIC
        # ====================================================

        audio_layers = list(
            voice_audio_clips
        )

        music, music_source = (
            create_background_music(
                MUSIC_PATH,
                final_video.duration
            )
        )

        if music is not None:

            audio_layers.append(
                music
            )

        # ====================================================
        # FINAL AUDIO
        # ====================================================

        print(
            "🎚️ Mixing voice + background music..."
        )

        if not audio_layers:

            raise RuntimeError(
                "No valid audio layers available."
            )

        mixed_audio = CompositeAudioClip(
            audio_layers
        )

        # Force exact final duration.
        mixed_audio = mixed_audio.set_duration(
            final_video.duration
        )

        final_video = final_video.set_audio(
            mixed_audio
        )

        # ====================================================
        # RENDER
        # ====================================================

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

        # ====================================================
        # VERIFY OUTPUT
        # ====================================================

        if not output_path.exists():

            raise RuntimeError(
                "MoviePy finished but MP4 "
                "was not created."
            )

        output_size = (
            output_path.stat().st_size
        )

        if output_size < 10000:

            raise RuntimeError(
                "Generated MP4 appears invalid "
                f"or too small: {output_size} bytes"
            )

        print(
            f"📦 MP4 size: "
            f"{output_size / 1024 / 1024:.2f} MB"
        )

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

    finally:

        # ====================================================
        # CLEANUP
        #
        # VERY IMPORTANT:
        # Cleanup happens AFTER write_videofile().
        # Never close source audio before rendering.
        # ====================================================

        print(
            "\n🧹 Cleaning MoviePy resources..."
        )

        if final_video is not None:

            try:

                final_video.close()

            except Exception:

                pass

        if mixed_audio is not None:

            try:

                mixed_audio.close()

            except Exception:

                pass

        if music is not None:

            try:

                music.close()

            except Exception:

                pass

        for part in music_parts:

            try:

                part.close()

            except Exception:

                pass

        if music_source is not None:

            try:

                music_source.close()

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

        print(
            "🧹 MoviePy cleanup completed."
        )


# ============================================================
# END
# ============================================================
