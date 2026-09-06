# FILE: src/generator.py
# Hindi Motivation + Quotes Video Generator
# Compatible with GitHub Actions, per-slide audio sync,
# long-form videos, YouTube Shorts, thumbnails and background music.

import os
import json
import time
import random
import re
import requests

from io import BytesIO
from pathlib import Path

from google import genai
from gtts import gTTS
from gtts.tts import gTTSError

from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    CompositeAudioClip,
    concatenate_videoclips,
    vfx
)

from moviepy.config import change_settings

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter
)

from pydub import AudioSegment


# ============================================================
# CONFIGURATION
# ============================================================

ASSETS_PATH = Path("assets")

FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"

BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music/bg_music.mp3"

FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()

# Channel / creator name
YOUR_NAME = "Aksh Dev"

# Main niche
CHANNEL_NICHE = "Hindi Motivation"

# TTS language
TTS_LANGUAGE = "hi"

# Gemini model
GEMINI_MODEL = "gemini-3.6-flash"

# Number of slides
LONG_FORM_SLIDES_MIN = 7
LONG_FORM_SLIDES_MAX = 9

# TTS retry configuration
TTS_MAX_ATTEMPTS = 5
TTS_BACKOFF_SECONDS = 5
TTS_MIN_GAP_SECONDS = 2

_last_tts_request = 0.0


# ============================================================
# IMAGEMAGICK - GITHUB ACTIONS
# ============================================================

if os.name == "posix":
    change_settings({
        "IMAGEMAGICK_BINARY": "/usr/bin/convert"
    })


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():
    """Creates and returns Gemini client."""

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY environment variable is missing."
        )

    return genai.Client(api_key=api_key)


# ============================================================
# JSON CLEANER
# ============================================================

def clean_json_response(text):
    """Cleans Gemini response and extracts JSON safely."""

    if not text:
        raise ValueError("Gemini returned an empty response.")

    text = text.strip()

    # Remove markdown code fences
    text = text.replace("```json", "")
    text = text.replace("```JSON", "")
    text = text.replace("```", "")

    text = text.strip()

    # Try direct JSON first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        extracted = text[start:end + 1]

        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Gemini response was not valid JSON."
    )


# ============================================================
# PEXELS IMAGE SEARCH
# ============================================================

def get_pexels_image(query, video_type):
    """
    Searches Pexels for a motivational image.
    """

    pexels_api_key = os.getenv("PEXELS_API_KEY")

    if not pexels_api_key:
        print(
            "⚠️ PEXELS_API_KEY not found. "
            "Using fallback background."
        )
        return None

    if video_type == "long":
        orientation = "landscape"
    else:
        orientation = "portrait"

    # Motivation-focused search
    motivation_words = [
        "motivation",
        "success",
        "discipline",
        "determination",
        "hard work",
        "sunrise",
        "mountain",
        "lonely person",
        "success journey"
    ]

    clean_query = str(query).strip()

    # Pick one additional visual keyword
    extra = random.choice(motivation_words)

    search_query = (
        f"{clean_query} {extra} cinematic"
    )

    try:

        headers = {
            "Authorization": pexels_api_key
        }

        params = {
            "query": search_query,
            "per_page": 1,
            "orientation": orientation
        }

        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        photos = data.get("photos", [])

        if not photos:
            print(
                f"⚠️ No Pexels image found for: {search_query}"
            )
            return None

        image_url = (
            photos[0]["src"].get("large2x")
            or photos[0]["src"].get("large")
            or photos[0]["src"].get("original")
        )

        if not image_url:
            return None

        image_response = requests.get(
            image_url,
            timeout=15
        )

        image_response.raise_for_status()

        return Image.open(
            BytesIO(image_response.content)
        ).convert("RGBA")

    except requests.exceptions.RequestException as e:

        print(
            f"❌ Network error fetching Pexels image: {e}"
        )

    except Exception as e:

        print(
            f"❌ Error fetching Pexels image: {e}"
        )

    return None


# ============================================================
# TTS THROTTLE
# ============================================================

def _throttle_tts():

    global _last_tts_request

    elapsed = (
        time.monotonic()
        - _last_tts_request
    )

    if elapsed < TTS_MIN_GAP_SECONDS:

        time.sleep(
            TTS_MIN_GAP_SECONDS - elapsed
        )

    _last_tts_request = time.monotonic()


# ============================================================
# TEXT TO SPEECH
# ============================================================

def text_to_speech(text, output_path):
    """
    Converts Hindi text into Hindi speech.
    """

    print("🎤 Generating Hindi voice-over...")

    output_path = Path(output_path)

    temp_mp3_path = (
        output_path.parent
        / f"{output_path.stem}_temp.mp3"
    )

    wav_path = output_path.with_suffix(".wav")

    for attempt in range(
        1,
        TTS_MAX_ATTEMPTS + 1
    ):

        try:

            _throttle_tts()

            tts = gTTS(
                text=text,
                lang=TTS_LANGUAGE,
                slow=False
            )

            tts.save(
                str(temp_mp3_path)
            )

            if (
                not temp_mp3_path.exists()
                or temp_mp3_path.stat().st_size < 1024
            ):

                raise gTTSError(
                    "gTTS produced an empty audio file."
                )

            audio = AudioSegment.from_mp3(
                str(temp_mp3_path)
            )

            audio.export(
                str(wav_path),
                format="wav",
                codec="pcm_s16le"
            )

            if temp_mp3_path.exists():
                temp_mp3_path.unlink()

            print(
                "✅ Hindi voice generated successfully."
            )

            return wav_path

        except Exception as e:

            if temp_mp3_path.exists():
                temp_mp3_path.unlink()

            if attempt == TTS_MAX_ATTEMPTS:

                print(
                    "❌ Hindi TTS failed after "
                    f"{TTS_MAX_ATTEMPTS} attempts: {e}"
                )

                raise

            delay = (
                TTS_BACKOFF_SECONDS
                * (2 ** (attempt - 1))
                + random.uniform(0, 2)
            )

            print(
                f"⚠️ TTS attempt "
                f"{attempt}/{TTS_MAX_ATTEMPTS} failed."
            )

            print(
                f"   Retrying in {delay:.1f} seconds..."
            )

            time.sleep(delay)


# ============================================================
# MOTIVATION CURRICULUM
# ============================================================

def generate_curriculum(previous_titles=None):
    """
    Generates a series plan for Hindi motivational videos.
    """

    print(
        "🤖 Generating Hindi motivation content plan..."
    )

    client = get_gemini_client()

    history = ""

    if previous_titles:

        formatted = "\n".join(
            [
                f"{i + 1}. {title}"
                for i, title in enumerate(
                    previous_titles
                )
            ]
        )

        history = f"""
Previously generated videos:

{formatted}

IMPORTANT:
Do not repeat these topics, titles,
quotes or concepts.

Create fresh topics that feel different.
"""

    prompt = f"""
You are an expert Hindi motivational YouTube
content strategist.

Create a YouTube content series for:

CHANNEL NICHE:
Hindi Motivation

LANGUAGE:
Natural Hindi

AUDIENCE:
Indian viewers interested in motivation,
discipline, success, confidence,
self improvement and life lessons.

{history}

The videos must NOT be about:
- programming
- AI tutorials
- software development
- technology education
- coding

The niche is ONLY Hindi motivation.

Generate 20 fresh video ideas.

Topics can include:

- मेहनत
- सफलता
- अनुशासन
- आत्मविश्वास
- समय
- लक्ष्य
- असफलता
- हार के बाद वापसी
- जिंदगी
- अकेलेपन से ताकत
- सपने
- संघर्ष
- consistency
- self respect
- positive thinking
- focus
- patience
- career motivation
- student motivation
- morning motivation
- रात में सोचने वालों के लिए motivation

Titles should be emotionally powerful,
natural Hindi and clickable.

Avoid fake claims.

Do not copy famous quotes word-for-word.

Every title should feel like a real
Hindi motivational YouTube video.

Return ONLY valid JSON.

Required structure:

{{
  "lessons": [
    {{
      "chapter": 1,
      "part": 1,
      "title": "Hindi title",
      "status": "pending",
      "youtube_id": null
    }}
  ]
}}

Exactly 20 lesson objects.
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        curriculum = clean_json_response(
            response.text
        )

        print(
            "✅ Hindi motivation curriculum generated."
        )

        return curriculum

    except Exception as e:

        print(
            "❌ Failed to generate curriculum:"
            f" {e}"
        )

        raise


# ============================================================
# LESSON CONTENT
# ============================================================

def generate_lesson_content(lesson_title):
    """
    Generates Hindi motivational video content,
    Shorts content, SEO metadata and thumbnail text.
    """

    print(
        f"🤖 Generating Hindi motivation video:"
        f" '{lesson_title}'..."
    )

    client = get_gemini_client()

    prompt = f"""
You are a professional Hindi motivational
YouTube scriptwriter and SEO strategist.

VIDEO TOPIC:
{lesson_title}

CHANNEL NICHE:
Hindi Motivation

LANGUAGE:
Hindi

TARGET AUDIENCE:
Indian viewers.

IMPORTANT:

This is NOT an AI, programming or developer channel.

Do NOT use:
- AI
- Artificial Intelligence
- Developer
- Programming
- Coding
- Agents
- Software
- Technology

unless the topic genuinely requires it.

The video should feel emotional,
human, cinematic and motivational.

Do NOT copy famous copyrighted quotes.

Create original motivational lines.

The first slide must have a VERY STRONG HOOK.

The viewer should immediately feel:
"ये वीडियो मुझे पूरा देखना चाहिए।"

--------------------------------------------------
LONG FORM VIDEO
--------------------------------------------------

Create 7 to 9 slides.

Each slide needs:

"title"
"content"
"visual_query"

CONTENT RULES:

- Natural Hindi
- Easy to understand
- Short sentences
- Emotional storytelling
- No unnecessary English
- No robotic wording
- No repetitive points
- Strong progression
- Final slide should give a memorable takeaway

--------------------------------------------------
SHORT
--------------------------------------------------

Create a short motivational script.

It should be approximately
20 to 45 seconds when spoken.

Include:

"hook"
"script"
"ending"

The hook must be powerful.

Example style:

"अगर आज तुम्हें लग रहा है कि तुम हार गए हो,
तो ये बात याद रखना..."

Do NOT copy this exact example.

--------------------------------------------------
YOUTUBE SEO
--------------------------------------------------

Generate:

"title"

"description"

"tags"

"keywords"

"hashtags"

SEO MUST be based on actual search intent
for Hindi motivation viewers.

Think deeply about what Indian users might
actually search on YouTube.

Good examples of keyword intent:

hindi motivation
motivational quotes in hindi
life motivation hindi
success motivation hindi
motivational speech hindi
self improvement hindi
student motivation hindi
morning motivation hindi
discipline motivation hindi
hard work motivation hindi

But choose tags that are actually relevant
to THIS VIDEO.

Do NOT simply take random words from the title.

Do NOT generate generic irrelevant tags such as:

AI
Agents
Developer
Future
Programming
Systems
Tutorial
Artificial Intelligence

unless genuinely relevant.

Use a mixture of:

1. Main keyword
2. Related search keyword
3. Long-tail keyword
4. Hindi search phrase
5. Audience intent
6. Topic-specific keyword

Keep tags natural.

Generate approximately 10-18 useful tags.

--------------------------------------------------
THUMBNAIL
--------------------------------------------------

Generate:

"thumbnail_text"

Thumbnail text must be:

- 2 to 6 words
- Hindi
- emotionally strong
- readable
- curiosity driven
- NOT the full video title

Examples of style:

"हार मत मानना"

"बस एक बार और"

"तुम कर सकते हो"

"वक्त बदल जाएगा"

Do not copy these exact examples.

--------------------------------------------------
DESCRIPTION
--------------------------------------------------

Description should:

- Start with a strong hook
- Explain the video's value
- Naturally include relevant keywords
- Encourage viewers to watch till the end
- Avoid keyword stuffing
- Include relevant hashtags at the end

--------------------------------------------------

Return ONLY valid JSON.

Required JSON structure:

{{
  "long_form_slides": [
    {{
      "title": "Hindi slide title",
      "content": "Hindi spoken content",
      "visual_query": "cinematic motivational visual"
    }}
  ],

  "short_form_highlight": {{
    "hook": "Hindi hook",
    "script": "Hindi short script",
    "ending": "Hindi ending"
  }},

  "youtube": {{
    "title": "SEO optimized Hindi YouTube title",
    "description": "SEO optimized Hindi description",
    "tags": [
      "relevant tag 1",
      "relevant tag 2"
    ],
    "keywords": [
      "keyword 1",
      "keyword 2"
    ],
    "hashtags": [
      "#HindiMotivation",
      "#Motivation"
    ]
  }},

  "thumbnail_text": "2 to 6 word Hindi thumbnail text"
}}
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        content = clean_json_response(
            response.text
        )

        print(
            "✅ Hindi motivational content generated."
        )

        return content

    except Exception as e:

        print(
            "❌ Failed to generate lesson content:"
            f" {e}"
        )

        raise


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(draw, text, font, max_width):

    words = str(text).split()

    lines = []

    current_line = ""

    for word in words:

        test_line = (
            f"{current_line} {word}"
        ).strip()

        bbox = draw.textbbox(
            (0, 0),
            test_line,
            font=font
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        if text_width <= max_width:

            current_line = test_line

        else:

            if current_line:
                lines.append(
                    current_line
                )

            current_line = word

    if current_line:
        lines.append(
            current_line
        )

    return lines


# ============================================================
# VISUAL GENERATOR
# ============================================================

def generate_visuals(
    output_dir,
    video_type,
    slide_content=None,
    thumbnail_title=None,
    slide_number=0,
    total_slides=0
):
    """
    Generates cinematic motivational slides
    and high-contrast thumbnails.
    """

    output_dir.mkdir(
        exist_ok=True,
        parents=True
    )

    is_thumbnail = (
        thumbnail_title is not None
    )

    # --------------------------------------------------------
    # DIMENSIONS
    # --------------------------------------------------------

    if video_type == "long":

        width = 1920
        height = 1080

    else:

        width = 1080
        height = 1920

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if is_thumbnail:

        title = str(
            thumbnail_title or ""
        )

    else:

        title = str(
            slide_content.get(
                "title",
                ""
            )
        )

    # --------------------------------------------------------
    # BACKGROUND
    # --------------------------------------------------------

    bg_image = get_pexels_image(
        title,
        video_type
    )

    if not bg_image:

        bg_image = Image.new(
            "RGBA",
            (width, height),
            color=(12, 17, 29, 255)
        )

    # Resize
    bg_image = bg_image.resize(
        (width, height)
    )

    # Cinematic blur
    bg_image = bg_image.filter(
        ImageFilter.GaussianBlur(3)
    )

    # Dark overlay
    darken_layer = Image.new(
        "RGBA",
        bg_image.size,
        (0, 0, 0, 155)
    )

    final_bg = Image.alpha_composite(
        bg_image,
        darken_layer
    ).convert("RGB")

    # --------------------------------------------------------
    # DRAW
    # --------------------------------------------------------

    draw = ImageDraw.Draw(
        final_bg
    )

    # --------------------------------------------------------
    # FONTS
    # --------------------------------------------------------

    try:

        if is_thumbnail:

            title_font = ImageFont.truetype(
                str(FONT_FILE),
                105
            )

        elif video_type == "long":

            title_font = ImageFont.truetype(
                str(FONT_FILE),
                76
            )

        else:

            title_font = ImageFont.truetype(
                str(FONT_FILE),
                78
            )

        content_font = ImageFont.truetype(
            str(FONT_FILE),
            48 if video_type == "long" else 58
        )

        footer_font = ImageFont.truetype(
            str(FONT_FILE),
            26
        )

    except IOError:

        print(
            "⚠️ Font not found. "
            "Using default font."
        )

        title_font = (
            FALLBACK_THUMBNAIL_FONT
        )

        content_font = (
            FALLBACK_THUMBNAIL_FONT
        )

        footer_font = (
            FALLBACK_THUMBNAIL_FONT
        )

    # ========================================================
    # THUMBNAIL
    # ========================================================

    if is_thumbnail:

        # Strong dark gradient-like overlays
        overlay = Image.new(
            "RGBA",
            (width, height),
            (0, 0, 0, 80)
        )

        final_bg = Image.alpha_composite(
            final_bg.convert("RGBA"),
            overlay
        ).convert("RGB")

        draw = ImageDraw.Draw(
            final_bg
        )

        # Thumbnail text wrapping
        lines = wrap_text(
            draw,
            title,
            title_font,
            width * 0.82
        )

        line_height = 125

        total_height = (
            len(lines)
            * line_height
        )

        start_y = (
            height - total_height
        ) / 2

        for line in lines:

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=title_font,
                stroke_width=4
            )

            text_width = (
                bbox[2] - bbox[0]
            )

            x = (
                width - text_width
            ) / 2

            # Heavy black outline
            draw.text(
                (x, start_y),
                line,
                font=title_font,
                fill=(255, 255, 255),
                stroke_width=5,
                stroke_fill=(0, 0, 0)
            )

            start_y += line_height

        # Small channel branding
        brand_text = (
            f"{CHANNEL_NICHE} • {YOUR_NAME}"
        )

        brand_bbox = draw.textbbox(
            (0, 0),
            brand_text,
            font=footer_font
        )

        brand_x = 35

        brand_y = (
            height
            - (
                brand_bbox[3]
                - brand_bbox[1]
            )
            - 30
        )

        draw.text(
            (brand_x, brand_y),
            brand_text,
            font=footer_font,
            fill=(220, 220, 220)
        )

    # ========================================================
    # NORMAL SLIDE
    # ========================================================

    else:

        header_height = int(
            height * 0.18
        )

        # Header background
        draw.rectangle(
            [
                0,
                0,
                width,
                header_height
            ],
            fill=(15, 25, 40)
        )

        # Title wrapping
        title_lines = wrap_text(
            draw,
            title,
            title_font,
            width * 0.88
        )

        line_height = 85

        total_title_height = (
            len(title_lines)
            * line_height
        )

        y_text = (
            header_height
            - total_title_height
        ) / 2

        for line in title_lines:

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=title_font
            )

            text_width = (
                bbox[2] - bbox[0]
            )

            x = (
                width - text_width
            ) / 2

            draw.text(
                (x, y_text),
                line,
                font=title_font,
                fill=(255, 255, 255)
            )

            y_text += line_height

        # ----------------------------------------------------
        # CONTENT
        # ----------------------------------------------------

        content = str(
            slide_content.get(
                "content",
                ""
            )
        )

        content_lines = wrap_text(
            draw,
            content,
            content_font,
            width * 0.82
        )

        line_height = 68

        total_content_height = (
            len(content_lines)
            * line_height
        )

        # Keep content centered
        y_content = max(
            header_height + 80,
            (
                height
                - total_content_height
            ) / 2
        )

        for line in content_lines:

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=content_font
            )

            text_width = (
                bbox[2] - bbox[0]
            )

            x = (
                width - text_width
            ) / 2

            draw.text(
                (x, y_content),
                line,
                font=content_font,
                fill=(235, 235, 235)
            )

            y_content += line_height

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        footer_height = int(
            height * 0.065
        )

        draw.rectangle(
            [
                0,
                height - footer_height,
                width,
                height
            ],
            fill=(15, 25, 40)
        )

        footer_text = (
            f"{CHANNEL_NICHE} • {YOUR_NAME}"
        )

        draw.text(
            (
                35,
                height
                - footer_height
                + 15
            ),
            footer_text,
            font=footer_font,
            fill=(180, 180, 180)
        )

        if total_slides > 0:

            slide_text = (
                f"{slide_number} / {total_slides}"
            )

            bbox = draw.textbbox(
                (0, 0),
                slide_text,
                font=footer_font
            )

            text_width = (
                bbox[2] - bbox[0]
            )

            draw.text(
                (
                    width
                    - text_width
                    - 35,
                    height
                    - footer_height
                    + 15
                ),
                slide_text,
                font=footer_font,
                fill=(180, 180, 180)
            )

    # ========================================================
    # SAVE
    # ========================================================

    if is_thumbnail:

        file_prefix = "thumbnail"

    else:

        file_prefix = (
            f"slide_{slide_number:02d}"
        )

    path = (
        output_dir
        / f"{file_prefix}.png"
    )

    final_bg.save(
        path,
        quality=95
    )

    print(
        f"🖼️ Created visual: {path}"
    )

    return str(path)


# ============================================================
# VIDEO CREATOR
# ============================================================

def create_video(
    slide_paths,
    audio_paths,
    output_path,
    video_type
):
    """
    Creates final video from slides + Hindi voice.
    Adds background music automatically.
    """

    print(
        f"🎬 Creating {video_type} video..."
    )

    try:

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if (
            not slide_paths
            or not audio_paths
            or len(slide_paths)
            != len(audio_paths)
        ):

            raise ValueError(
                "Mismatch between slides and audio clips."
            )

        # ----------------------------------------------------
        # CREATE IMAGE CLIPS
        # ----------------------------------------------------

        image_clips = []

        for i, (
            img_path,
            audio_path
        ) in enumerate(
            zip(
                slide_paths,
                audio_paths
            )
        ):

            print(
                f"🎞️ Processing slide "
                f"{i + 1}/{len(slide_paths)}..."
            )

            audio_clip = AudioFileClip(
                str(audio_path)
            )

            # Small padding after speech
            duration = (
                audio_clip.duration
                + 0.35
            )

            img_clip = (
                ImageClip(img_path)
                .set_duration(duration)
                .set_audio(audio_clip)
                .fadein(0.35)
                .fadeout(0.35)
            )

            image_clips.append(
                img_clip
            )

        # ----------------------------------------------------
        # CONCATENATE
        # ----------------------------------------------------

        final_video = concatenate_videoclips(
            image_clips,
            method="compose"
        )

        # ----------------------------------------------------
        # BACKGROUND MUSIC
        # ----------------------------------------------------

        if BACKGROUND_MUSIC_PATH.exists():

            print(
                "🎵 Adding background music..."
            )

            bg_music = AudioFileClip(
                str(BACKGROUND_MUSIC_PATH)
            )

            # Keep music quiet under voice
            bg_music = (
                bg_music
                .volumex(0.07)
            )

            # Loop music
            if (
                bg_music.duration
                < final_video.duration
            ):

                bg_music = bg_music.fx(
                    vfx.loop,
                    duration=final_video.duration
                )

            else:

                bg_music = bg_music.subclip(
                    0,
                    final_video.duration
                )

            # ------------------------------------------------
            # AUDIO MIX
            # ------------------------------------------------

            if final_video.audio:

                voice_audio = (
                    final_video.audio
                    .volumex(1.15)
                )

                composite_audio = (
                    CompositeAudioClip(
                        [
                            voice_audio,
                            bg_music
                        ]
                    )
                )

                final_video = (
                    final_video
                    .set_audio(
                        composite_audio
                    )
                )

            else:

                final_video = (
                    final_video
                    .set_audio(bg_music)
                )

        else:

            print(
                "⚠️ Background music not found:"
                f" {BACKGROUND_MUSIC_PATH}"
            )

            print(
                "   Video will be generated "
                "with voice only."
            )

        # ----------------------------------------------------
        # EXPORT
        # ----------------------------------------------------

        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
            preset="medium",
            threads=4
        )

        print(
            f"✅ {video_type.capitalize()} "
            "video created successfully!"
        )

        # ----------------------------------------------------
        # CLEANUP
        # ----------------------------------------------------

        try:

            final_video.close()

        except Exception:

            pass

        for clip in image_clips:

            try:
                clip.close()

            except Exception:
                pass

    except Exception as e:

        print(
            "❌ ERROR during video creation:"
            f" {e}"
        )

        raise
