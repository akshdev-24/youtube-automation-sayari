# ============================================================
# HINGLISH SHAYARI STATIC VIDEO GENERATOR
# ============================================================
#
# Features:
#   ✅ 1080x1920 vertical video
#   ✅ Hinglish / Roman Hindi Shayari
#   ✅ Static Shayari text
#   ✅ NO text animation
#   ✅ NO voice / TTS
#   ✅ Fixed background image
#   ✅ Fixed background music
#   ✅ Music automatically loops/trims
#   ✅ Automatic text wrapping
#   ✅ Cream Shayari card
#
# Assets:
#
#   assets/
#   ├── background.jpg
#   └── music/
#       └── bg_music.mp3
#
# Fallback:
#   assets/fallback.jpg
# ============================================================

from pathlib import Path
from typing import Optional
import os
import math

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_audioclips,
)


# ============================================================
# CONFIG
# ============================================================

WIDTH = 1080
HEIGHT = 1920

FPS = 30

DEFAULT_DURATION = 15

VIDEO_BITRATE = "5000k"

ROOT_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = ROOT_DIR / "assets"

MUSIC_DIR = ASSETS_DIR / "music"

OUTPUT_DIR = ROOT_DIR / "output"

FONT_DIR = ASSETS_DIR / "fonts"


# ============================================================
# BACKGROUND / CARD CONFIG
# ============================================================

BACKGROUND_COLOR = (15, 15, 15)

CARD_COLOR = (238, 224, 198)

TEXT_COLOR = (35, 31, 27)

SECONDARY_TEXT_COLOR = (80, 70, 58)

CARD_WIDTH = 820

CARD_HEIGHT = 1540

CARD_TOP = 170

CARD_RADIUS = 45


# ============================================================
# ASSET FUNCTIONS
# ============================================================

def find_background():

    possible_files = [

        ASSETS_DIR / "background.jpg",

        ASSETS_DIR / "background.jpeg",

        ASSETS_DIR / "background.png",

        ASSETS_DIR / "background.webp",

        ASSETS_DIR / "fallback.jpg",

        ASSETS_DIR / "fallback.png",

    ]

    for file in possible_files:

        if file.exists():

            return file

    raise FileNotFoundError(
        "\n❌ Background image nahi mili.\n\n"
        "Add one of these files:\n"
        "assets/background.jpg\n"
        "assets/background.png\n"
        "assets/fallback.jpg\n"
    )


def find_music():

    possible_files = [

        MUSIC_DIR / "bg_music.mp3",

        MUSIC_DIR / "bg_music.wav",

        MUSIC_DIR / "bg_music.m4a",

        ASSETS_DIR / "bg_music.mp3",

    ]

    for file in possible_files:

        if file.exists():

            return file

    raise FileNotFoundError(
        "\n❌ Background music nahi mili.\n\n"
        "Add:\n"
        "assets/music/bg_music.mp3\n"
    )


# ============================================================
# FONT
# ============================================================

def find_font():

    possible_fonts = [

        FONT_DIR / "Georgia.ttf",

        FONT_DIR / "georgia.ttf",

        FONT_DIR / "times.ttf",

        FONT_DIR / "TimesNewRoman.ttf",

        FONT_DIR / "timesnewroman.ttf",

        FONT_DIR / "arial.ttf",

    ]

    for font in possible_fonts:

        if font.exists():

            return font

    return None


def get_font(size):

    font_path = find_font()

    if font_path:

        return ImageFont.truetype(
            str(font_path),
            size
        )

    # Windows fonts fallback

    windows_fonts = [

        r"C:\Windows\Fonts\georgia.ttf",

        r"C:\Windows\Fonts\times.ttf",

        r"C:\Windows\Fonts\arial.ttf",

    ]

    for font_path in windows_fonts:

        if Path(font_path).exists():

            return ImageFont.truetype(
                font_path,
                size
            )

    # PIL default fallback

    return ImageFont.load_default()


# ============================================================
# TEXT MEASUREMENT
# ============================================================

def get_text_width(draw, text, font):

    box = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    return box[2] - box[0]


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(
    draw,
    text,
    font,
    max_width
):

    lines = []

    paragraphs = text.strip().split("\n")

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:

            lines.append("")

            continue

        words = paragraph.split()

        current_line = ""

        for word in words:

            if current_line == "":

                test_line = word

            else:

                test_line = (
                    current_line
                    + " "
                    + word
                )

            width = get_text_width(
                draw,
                test_line,
                font
            )

            if width <= max_width:

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
# FIND BEST FONT SIZE
# ============================================================

def find_best_font(
    draw,
    text,
    max_width,
    max_height
):

    for size in range(58, 28, -2):

        font = get_font(size)

        lines = wrap_text(
            draw,
            text,
            font,
            max_width
        )

        line_height = int(
            size * 1.45
        )

        paragraph_gap = int(
            size * 0.55
        )

        total_height = 0

        for line in lines:

            if line == "":

                total_height += paragraph_gap

            else:

                total_height += line_height

        if total_height <= max_height:

            return (
                font,
                lines,
                line_height,
                paragraph_gap
            )

    font = get_font(28)

    lines = wrap_text(
        draw,
        text,
        font,
        max_width
    )

    return (
        font,
        lines,
        42,
        18
    )


# ============================================================
# CREATE STATIC SHAYARI CARD
# ============================================================

def create_shayari_card(
    shayari,
    output_file
):

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND_COLOR
    )

    image = image.convert("RGBA")

    # --------------------------------------------------------
    # CARD POSITION
    # --------------------------------------------------------

    card_x = (
        WIDTH - CARD_WIDTH
    ) // 2

    card_y = CARD_TOP

    card_right = (
        card_x + CARD_WIDTH
    )

    card_bottom = (
        card_y + CARD_HEIGHT
    )

    # --------------------------------------------------------
    # SHADOW
    # --------------------------------------------------------

    shadow = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0)
    )

    shadow_draw = ImageDraw.Draw(
        shadow
    )

    shadow_draw.rounded_rectangle(

        (
            card_x + 15,
            card_y + 20,
            card_right + 15,
            card_bottom + 20,
        ),

        radius=CARD_RADIUS,

        fill=(0, 0, 0, 160)
    )

    shadow = shadow.filter(
        ImageFilter.GaussianBlur(18)
    )

    image = Image.alpha_composite(
        image,
        shadow
    )

    draw = ImageDraw.Draw(image)

    # --------------------------------------------------------
    # CARD
    # --------------------------------------------------------

    draw.rounded_rectangle(

        (
            card_x,
            card_y,
            card_right,
            card_bottom
        ),

        radius=CARD_RADIUS,

        fill=CARD_COLOR
    )

    # --------------------------------------------------------
    # PROFILE CIRCLE
    # --------------------------------------------------------

    profile_x = card_x + 70

    profile_y = card_y + 90

    draw.ellipse(

        (
            profile_x,
            profile_y,
            profile_x + 70,
            profile_y + 70
        ),

        fill=(65, 58, 48)
    )

    # --------------------------------------------------------
    # BRAND NAME
    # --------------------------------------------------------

    brand_font = get_font(28)

    draw.text(

        (
            card_x + 165,
            card_y + 105
        ),

        "Shayari",

        font=brand_font,

        fill=SECONDARY_TEXT_COLOR
    )

    # --------------------------------------------------------
    # SHAYARI TEXT
    # --------------------------------------------------------

    text_left = card_x + 70

    text_top = card_y + 300

    text_width = (
        CARD_WIDTH - 140
    )

    text_height = 1000

    (
        font,
        lines,
        line_height,
        paragraph_gap
    ) = find_best_font(

        draw,

        shayari,

        text_width,

        text_height
    )

    y = text_top

    for line in lines:

        if line == "":

            y += paragraph_gap

            continue

        draw.text(

            (
                text_left,
                y
            ),

            line,

            font=font,

            fill=TEXT_COLOR
        )

        y += line_height

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    footer_font = get_font(20)

    draw.text(

        (
            card_x + 70,
            card_bottom - 90
        ),

        "Hinglish Shayari",

        font=footer_font,

        fill=SECONDARY_TEXT_COLOR
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    image = image.convert("RGB")

    image.save(
        output_file,
        quality=95
    )

    return output_file


# ============================================================
# PREPARE BACKGROUND
# ============================================================

def prepare_background(
    background_file,
    duration
):

    image = Image.open(
        background_file
    ).convert("RGB")

    target_ratio = (
        WIDTH / HEIGHT
    )

    source_ratio = (
        image.width / image.height
    )

    # --------------------------------------------------------
    # CROP
    # --------------------------------------------------------

    if source_ratio > target_ratio:

        new_width = int(
            image.height
            * target_ratio
        )

        left = (
            image.width
            - new_width
        ) // 2

        image = image.crop(

            (
                left,
                0,
                left + new_width,
                image.height
            )
        )

    else:

        new_height = int(
            image.width
            / target_ratio
        )

        top = (
            image.height
            - new_height
        ) // 2

        image = image.crop(

            (
                0,
                top,
                image.width,
                top + new_height
            )
        )

    # --------------------------------------------------------
    # RESIZE
    # --------------------------------------------------------

    image = image.resize(

        (
            WIDTH,
            HEIGHT
        ),

        Image.Resampling.LANCZOS
    )

    temp_background = (
        OUTPUT_DIR
        / "_background.jpg"
    )

    image.save(
        temp_background,
        quality=95
    )

    return ImageClip(
        str(temp_background)
    ).set_duration(
        duration
    )


# ============================================================
# PREPARE MUSIC
# ============================================================

def prepare_music(
    music_file,
    duration
):

    audio = AudioFileClip(
        str(music_file)
    )

    if audio.duration <= 0:

        raise ValueError(
            "Music duration invalid."
        )

    # --------------------------------------------------------
    # MUSIC SHORTER THAN VIDEO
    # --------------------------------------------------------

    if audio.duration < duration:

        loops = math.ceil(
            duration
            / audio.duration
        )

        clips = []

        for _ in range(loops):

            clips.append(
                audio.copy()
            )

        audio = concatenate_audioclips(
            clips
        )

        audio = audio.subclip(
            0,
            duration
        )

    else:

        audio = audio.subclip(
            0,
            duration
        )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    volume = float(
        os.getenv(
            "SHAYARI_MUSIC_VOLUME",
            "0.75"
        )
    )

    volume = max(
        0.0,
        min(
            volume,
            1.0
        )
    )

    audio = audio.volumex(
        volume
    )

    return audio


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_video(
    shayari,
    output_path,
    duration=None,
    brand_name="Shayari"
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if duration is None:

        duration = float(
            os.getenv(
                "SHAYARI_DURATION",
                DEFAULT_DURATION
            )
        )

    # --------------------------------------------------------
    # FIND ASSETS
    # --------------------------------------------------------

    background_file = (
        find_background()
    )

    music_file = (
        find_music()
    )

    print()
    print(
        "=========================================="
    )
    print(
        "     HINGLISH SHAYARI VIDEO GENERATOR"
    )
    print(
        "=========================================="
    )

    print(
        f"🖼️ Background : {background_file}"
    )

    print(
        f"🎵 Music      : {music_file}"
    )

    print(
        "✍️ Text        : STATIC"
    )

    print(
        "🎙️ Voice       : OFF"
    )

    print(
        "✨ Animation   : OFF"
    )

    print(
        f"📱 Resolution  : {WIDTH}x{HEIGHT}"
    )

    print(
        f"⏱️ Duration    : {duration}s"
    )

    print()

    # --------------------------------------------------------
    # CREATE CARD
    # --------------------------------------------------------

    card_file = (
        OUTPUT_DIR
        / "_shayari_card.png"
    )

    create_shayari_card(

        shayari,

        card_file
    )

    # --------------------------------------------------------
    # BACKGROUND
    # --------------------------------------------------------

    background_clip = (
        prepare_background(

            background_file,

            duration
        )
    )

    # --------------------------------------------------------
    # STATIC CARD
    #
    # Important:
    # This image remains EXACTLY the same for
    # the complete duration.
    # --------------------------------------------------------

    shayari_clip = (

        ImageClip(
            str(card_file)
        )

        .set_duration(
            duration
        )

        .set_position(
            ("center", "center")
        )
    )

    # --------------------------------------------------------
    # COMPOSITE
    # --------------------------------------------------------

    video = CompositeVideoClip(

        [
            background_clip,
            shayari_clip
        ],

        size=(
            WIDTH,
            HEIGHT
        )
    )

    video = video.set_duration(
        duration
    )

    # --------------------------------------------------------
    # MUSIC
    # --------------------------------------------------------

    audio = prepare_music(

        music_file,

        duration
    )

    video = video.set_audio(
        audio
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    print(
        f"🎬 Rendering → {output_path}"
    )

    video.write_videofile(

        str(output_path),

        fps=FPS,

        codec="libx264",

        audio_codec="aac",

        bitrate=VIDEO_BITRATE,

        preset=os.getenv(
            "SHAYARI_PRESET",
            "medium"
        ),

        threads=int(
            os.getenv(
                "SHAYARI_THREADS",
                "2"
            )
        ),

        temp_audiofile=str(
            OUTPUT_DIR
            / "_temp_audio.m4a"
        ),

        remove_temp=True
    )

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    try:
        audio.close()
    except Exception:
        pass

    try:
        video.close()
    except Exception:
        pass

    try:
        background_clip.close()
    except Exception:
        pass

    try:
        shayari_clip.close()
    except Exception:
        pass

    # --------------------------------------------------------
    # REMOVE TEMP FILES
    # --------------------------------------------------------

    try:
        card_file.unlink()
    except Exception:
        pass

    try:

        (
            OUTPUT_DIR
            / "_background.jpg"
        ).unlink()

    except Exception:
        pass

    print()
    print(
        "=========================================="
    )

    print(
        "✅ VIDEO CREATED SUCCESSFULLY"
    )

    print(
        f"📁 {output_path}"
    )

    print(
        "=========================================="
    )

    return output_path


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def generate_video(
    shayari,
    output_path,
    duration=None
):

    return create_video(

        shayari=shayari,

        output_path=output_path,

        duration=duration
    )


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    sample_shayari = """
Kabhi kabhi khamoshi bhi
bahut kuch keh jaati hai,

bas samajhne wala hona chahiye.
"""

    output = (
        OUTPUT_DIR
        / "shayari_test.mp4"
    )

    create_video(

        shayari=sample_shayari,

        output_path=output,

        duration=15
    )
