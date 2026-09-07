# ============================================================
# FILE: src/shayari_video.py
# ============================================================
#
# HINGLISH SHAYARI SHORT VIDEO GENERATOR
#
# DESIGN:
#   - User background ONLY
#   - No card
#   - No paper overlay
#   - No external image
#   - No UI
#   - Static typography
#   - Reference-inspired serif typography
#   - Reference-inspired spacing
#   - User music only
#
# OUTPUT:
#   1080 x 1920
#   9:16
#   H.264 + AAC
#
# ============================================================

import os
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_audioclips,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"

MUSIC_DIR = ASSETS_DIR / "music"

FONTS_DIR = ASSETS_DIR / "fonts"

OUTPUT_DIR = BASE_DIR / "output"


# ============================================================
# VIDEO CONFIG
# ============================================================

WIDTH = 1080
HEIGHT = 1920

FPS = 30

DEFAULT_DURATION = int(
    os.getenv(
        "SHAYARI_DURATION",
        "15"
    )
)


# ============================================================
# DESIGN CONFIG
# ============================================================

# Main body font size.
#
# Reference video at 720x1280 uses a large serif font.
# 1080x1920 scale is approximately 1.5x.
#
BODY_FONT_SIZE = int(
    os.getenv(
        "SHAYARI_FONT_SIZE",
        "46"
    )
)

# Smaller branding text.
BRAND_FONT_SIZE = int(
    os.getenv(
        "BRAND_FONT_SIZE",
        "30"
    )
)

# Footer.
FOOTER_FONT_SIZE = int(
    os.getenv(
        "FOOTER_FONT_SIZE",
        "22"
    )
)

# Text area.
LEFT_MARGIN = int(
    os.getenv(
        "TEXT_LEFT_MARGIN",
        "135"
    )
)

RIGHT_MARGIN = int(
    os.getenv(
        "TEXT_RIGHT_MARGIN",
        "135"
    )
)

TEXT_MAX_WIDTH = (
    WIDTH
    - LEFT_MARGIN
    - RIGHT_MARGIN
)


# ============================================================
# TEXT POSITION
# ============================================================

# Reference composition has the brand in the upper section
# and the poetry below it.
#
# Since there is NO card anymore, the text is positioned
# relative to the entire user's background.

BRAND_Y = int(
    os.getenv(
        "BRAND_Y",
        "330"
    )
)

POETRY_Y = int(
    os.getenv(
        "POETRY_Y",
        "650"
    )
)


# ============================================================
# COLORS
# ============================================================

# Classic reference-style dark text.
#
# We intentionally keep the text almost black rather than
# pure black so it feels slightly softer.

TEXT_COLOR = (
    18,
    18,
    18,
    255
)

BRAND_COLOR = (
    25,
    25,
    25,
    255
)

FOOTER_COLOR = (
    35,
    35,
    35,
    210
)


# ============================================================
# TEXT SHADOW
# ============================================================

# Very subtle shadow.
#
# This is NOT a background overlay/card.
# It only helps black typography remain readable over photos.

SHADOW_COLOR = (
    255,
    255,
    255,
    95
)

SHADOW_OFFSET = 2

SHADOW_BLUR = 1


# ============================================================
# BACKGROUND FILTER
# ============================================================

# Reference videos have a soft, muted, slightly warm
# photographic appearance.
#
# This filter is intentionally subtle.
#
# It does NOT create a paper/card layer.
#
FILTER_ENABLED = (
    os.getenv(
        "REFERENCE_FILTER",
        "true"
    ).lower()
    == "true"
)


# ============================================================
# FONT DISCOVERY
# ============================================================

def find_font(
    preferred_names: List[str],
    fallback_names: List[str],
) -> str:

    candidates = []

    for name in preferred_names:
        candidates.extend([
            FONTS_DIR / name,
            BASE_DIR / name,
        ])

    # Windows fonts
    windows_fonts = Path(
        os.environ.get(
            "WINDIR",
            "C:/Windows"
        )
    ) / "Fonts"

    candidates.extend([
        windows_fonts / "times.ttf",
        windows_fonts / "timesnewroman.ttf",
        windows_fonts / "georgia.ttf",
        windows_fonts / "baskerville.ttf",
        windows_fonts / "cambria.ttf",
        windows_fonts / "arial.ttf",
    ])

    # Linux / GitHub Actions fonts
    candidates.extend([
        Path(
            "/usr/share/fonts/truetype/"
            "liberation2/LiberationSerif-Regular.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/"
            "liberation2/LiberationSerif-Italic.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSerif.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSerif-Italic.ttf"
        ),
    ])

    # Explicit fallback names
    for name in fallback_names:
        candidates.append(
            FONTS_DIR / name
        )

    for candidate in candidates:

        try:

            if candidate.exists():
                return str(candidate)

        except Exception:
            pass

    raise FileNotFoundError(
        "No suitable serif font found. "
        "Please put a .ttf font inside assets/fonts/."
    )


def get_body_font() -> str:

    return find_font(
        preferred_names=[
            "body.ttf",
            "TimesNewRoman.ttf",
            "times.ttf",
            "Georgia.ttf",
        ],
        fallback_names=[
            "arial.ttf",
        ]
    )


def get_brand_font() -> str:

    return find_font(
        preferred_names=[
            "brand.ttf",
            "TimesNewRomanItalic.ttf",
            "timesi.ttf",
            "GeorgiaItalic.ttf",
        ],
        fallback_names=[
            "ariali.ttf",
        ]
    )


# ============================================================
# BACKGROUND DISCOVERY
# ============================================================

def find_background() -> Path:

    preferred = [

        ASSETS_DIR / "background.jpg",

        ASSETS_DIR / "background.jpeg",

        ASSETS_DIR / "background.png",

        ASSETS_DIR / "background.webp",

        ASSETS_DIR / "background.mp4",

        ASSETS_DIR / "background.mov",

        ASSETS_DIR / "background.mkv",
    ]

    for path in preferred:

        if path.exists():
            return path

    # Generic fallback.
    extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".mp4",
        ".mov",
        ".mkv",
    ]

    for path in ASSETS_DIR.iterdir():

        if (
            path.is_file()
            and path.suffix.lower()
            in extensions
        ):
            return path

    raise FileNotFoundError(
        "No background found.\n"
        "Put your background here:\n"
        "assets/background.jpg"
    )


# ============================================================
# MUSIC DISCOVERY
# ============================================================

def find_music() -> Path:

    preferred = [

        MUSIC_DIR / "bg_music.mp3",

        MUSIC_DIR / "background.mp3",

        MUSIC_DIR / "music.mp3",

        MUSIC_DIR / "bg_music.wav",

        MUSIC_DIR / "background.wav",
    ]

    for path in preferred:

        if path.exists():
            return path

    extensions = [
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".ogg",
    ]

    if MUSIC_DIR.exists():

        for path in MUSIC_DIR.iterdir():

            if (
                path.is_file()
                and path.suffix.lower()
                in extensions
            ):
                return path

    raise FileNotFoundError(
        "No music found.\n"
        "Put your music here:\n"
        "assets/music/bg_music.mp3"
    )


# ============================================================
# IMAGE CROP
# ============================================================

def crop_to_vertical(
    image: Image.Image,
    target_width: int = WIDTH,
    target_height: int = HEIGHT,
) -> Image.Image:

    image = image.convert("RGB")

    src_w, src_h = image.size

    target_ratio = (
        target_width
        / target_height
    )

    src_ratio = (
        src_w
        / src_h
    )

    # --------------------------------------------------------
    # Landscape / wide image
    # --------------------------------------------------------

    if src_ratio > target_ratio:

        new_height = src_h

        new_width = int(
            src_h
            * target_ratio
        )

        left = (
            src_w
            - new_width
        ) // 2

        top = 0

    # --------------------------------------------------------
    # Portrait image
    # --------------------------------------------------------

    else:

        new_width = src_w

        new_height = int(
            src_w
            / target_ratio
        )

        left = 0

        top = (
            src_h
            - new_height
        ) // 2

    image = image.crop(
        (
            left,
            top,
            left + new_width,
            top + new_height
        )
    )

    image = image.resize(
        (
            target_width,
            target_height
        ),
        Image.Resampling.LANCZOS
    )

    return image


# ============================================================
# REFERENCE-STYLE FILTER
# ============================================================

def apply_reference_filter(
    image: Image.Image
) -> Image.Image:

    if not FILTER_ENABLED:
        return image

    image = image.convert("RGB")

    # --------------------------------------------------------
    # Slightly lower saturation.
    # --------------------------------------------------------

    image = ImageEnhance.Color(
        image
    ).enhance(
        0.82
    )

    # --------------------------------------------------------
    # Slight contrast increase.
    # --------------------------------------------------------

    image = ImageEnhance.Contrast(
        image
    ).enhance(
        1.05
    )

    # --------------------------------------------------------
    # Slight brightness reduction.
    # --------------------------------------------------------

    image = ImageEnhance.Brightness(
        image
    ).enhance(
        0.94
    )

    # --------------------------------------------------------
    # Very subtle warm tone.
    # --------------------------------------------------------

    arr = np.asarray(
        image
    ).astype(
        np.float32
    )

    # Warm the image slightly.
    arr[:, :, 0] *= 1.025
    arr[:, :, 1] *= 1.000
    arr[:, :, 2] *= 0.970

    arr = np.clip(
        arr,
        0,
        255
    ).astype(
        np.uint8
    )

    image = Image.fromarray(
        arr,
        "RGB"
    )

    # --------------------------------------------------------
    # Subtle cinematic vignette.
    #
    # This is a filter on the user's background,
    # NOT an overlay card.
    # --------------------------------------------------------

    w, h = image.size

    yy, xx = np.mgrid[
        0:h,
        0:w
    ]

    cx = w / 2
    cy = h / 2

    dx = (
        xx - cx
    ) / cx

    dy = (
        yy - cy
    ) / cy

    distance = np.sqrt(
        dx * dx
        + dy * dy
    )

    vignette = np.clip(
        1.0
        - 0.10
        * np.maximum(
            distance - 0.45,
            0
        ),
        0.84,
        1.0
    )

    arr = np.asarray(
        image
    ).astype(
        np.float32
    )

    arr *= vignette[:, :, None]

    arr = np.clip(
        arr,
        0,
        255
    ).astype(
        np.uint8
    )

    return Image.fromarray(
        arr,
        "RGB"
    )


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> List[str]:

    words = text.split()

    if not words:
        return [""]

    lines = []

    current = words[0]

    for word in words[1:]:

        candidate = (
            current
            + " "
            + word
        )

        bbox = draw.textbbox(
            (0, 0),
            candidate,
            font=font
        )

        width = (
            bbox[2]
            - bbox[0]
        )

        if width <= max_width:

            current = candidate

        else:

            lines.append(
                current
            )

            current = word

    lines.append(
        current
    )

    return lines


# ============================================================
# MEASURE TEXT
# ============================================================

def get_text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
) -> Tuple[int, int]:

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    return (
        bbox[2] - bbox[0],
        bbox[3] - bbox[1]
    )


# ============================================================
# DRAW TEXT WITH SHADOW
# ============================================================

def draw_text_with_shadow(
    layer: Image.Image,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill,
    anchor=None,
):

    shadow_layer = Image.new(
        "RGBA",
        layer.size,
        (0, 0, 0, 0)
    )

    shadow_draw = ImageDraw.Draw(
        shadow_layer
    )

    x, y = position

    shadow_draw.text(
        (
            x + SHADOW_OFFSET,
            y + SHADOW_OFFSET
        ),
        text,
        font=font,
        fill=SHADOW_COLOR,
        anchor=anchor
    )

    if SHADOW_BLUR > 0:

        shadow_layer = shadow_layer.filter(
            ImageFilter.GaussianBlur(
                SHADOW_BLUR
            )
        )

    layer.alpha_composite(
        shadow_layer
    )

    draw = ImageDraw.Draw(
        layer
    )

    draw.text(
        position,
        text,
        font=font,
        fill=fill,
        anchor=anchor
    )


# ============================================================
# BRAND
# ============================================================

def draw_brand(
    layer: Image.Image,
    brand_text: str = "Mehfil-e-Shayariii",
):

    font_path = get_brand_font()

    font = ImageFont.truetype(
        font_path,
        BRAND_FONT_SIZE
    )

    draw = ImageDraw.Draw(
        layer
    )

    # --------------------------------------------------------
    # Reference-inspired centered branding.
    #
    # No circle/logo/card is generated.
    # This is ONLY text.
    # --------------------------------------------------------

    bbox = draw.textbbox(
        (0, 0),
        brand_text,
        font=font
    )

    text_width = (
        bbox[2]
        - bbox[0]
    )

    x = (
        WIDTH
        - text_width
    ) // 2

    draw_text_with_shadow(
        layer=layer,
        position=(
            x,
            BRAND_Y
        ),
        text=brand_text,
        font=font,
        fill=BRAND_COLOR
    )


# ============================================================
# POETRY LAYOUT
# ============================================================

def prepare_poetry_lines(
    lines: List[str]
) -> List[str]:

    prepared = []

    for line in lines:

        if line is None:
            prepared.append("")
            continue

        line = str(
            line
        ).strip()

        prepared.append(
            line
        )

    # Remove blank lines at beginning/end.
    while (
        prepared
        and not prepared[0]
    ):
        prepared.pop(0)

    while (
        prepared
        and not prepared[-1]
    ):
        prepared.pop()

    return prepared


# ============================================================
# DRAW SHAYARI
# ============================================================

def draw_shayari(
    layer: Image.Image,
    lines: List[str],
):

    lines = prepare_poetry_lines(
        lines
    )

    body_font_path = get_body_font()

    font = ImageFont.truetype(
        body_font_path,
        BODY_FONT_SIZE
    )

    draw = ImageDraw.Draw(
        layer
    )

    # --------------------------------------------------------
    # Reference typography metrics.
    # --------------------------------------------------------

    sample_height = get_text_size(
        draw,
        "Ag",
        font
    )[1]

    line_spacing = int(
        sample_height * 0.36
    )

    # Extra vertical space between poetry blocks.
    block_spacing = int(
        sample_height * 1.05
    )

    current_y = POETRY_Y

    for index, raw_line in enumerate(lines):

        # ----------------------------------------------------
        # Blank line = intentional poetry block spacing.
        # ----------------------------------------------------

        if not raw_line:

            current_y += (
                block_spacing
            )

            continue

        # ----------------------------------------------------
        # Wrap only if the generated line is too long.
        # ----------------------------------------------------

        wrapped = wrap_text_to_width(
            draw,
            raw_line,
            font,
            TEXT_MAX_WIDTH
        )

        for wrapped_line in wrapped:

            # ------------------------------------------------
            # Reference style is left-aligned within the
            # text area.
            # ------------------------------------------------

            x = LEFT_MARGIN

            draw_text_with_shadow(
                layer=layer,
                position=(
                    x,
                    current_y
                ),
                text=wrapped_line,
                font=font,
                fill=TEXT_COLOR
            )

            current_y += (
                sample_height
                + line_spacing
            )

        # ----------------------------------------------------
        # Safety: never allow text to run off-screen.
        # ----------------------------------------------------

        if current_y > HEIGHT - 250:

            break


# ============================================================
# FOOTER
# ============================================================

def draw_footer(
    layer: Image.Image,
    footer_text: str = "HINGLISH SHAYARI",
):

    font_path = get_body_font()

    font = ImageFont.truetype(
        font_path,
        FOOTER_FONT_SIZE
    )

    draw = ImageDraw.Draw(
        layer
    )

    bbox = draw.textbbox(
        (0, 0),
        footer_text,
        font=font
    )

    text_width = (
        bbox[2]
        - bbox[0]
    )

    x = (
        WIDTH
        - text_width
    ) // 2

    y = HEIGHT - 110

    draw.text(
        (
            x,
            y
        ),
        footer_text,
        font=font,
        fill=FOOTER_COLOR
    )


# ============================================================
# RENDER IMAGE
# ============================================================

def render_image_background(
    background_path: Path,
    lines: List[str],
    brand: str = "Mehfil-e-Shayariii",
) -> Image.Image:

    print(
        f"🖼️ Loading background: {background_path}"
    )

    image = Image.open(
        background_path
    ).convert(
        "RGB"
    )

    print(
        f"Original background size: {image.size}"
    )

    # --------------------------------------------------------
    # Crop to exact 9:16.
    # --------------------------------------------------------

    image = crop_to_vertical(
        image,
        WIDTH,
        HEIGHT
    )

    # --------------------------------------------------------
    # Apply reference-inspired filter.
    # --------------------------------------------------------

    image = apply_reference_filter(
        image
    )

    # --------------------------------------------------------
    # Transparent text layer ONLY.
    #
    # IMPORTANT:
    # There is NO rectangle/card/page.
    # --------------------------------------------------------

    layer = Image.new(
        "RGBA",
        (
            WIDTH,
            HEIGHT
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    # --------------------------------------------------------
    # Brand
    # --------------------------------------------------------

    draw_brand(
        layer,
        brand
    )

    # --------------------------------------------------------
    # Shayari
    # --------------------------------------------------------

    draw_shayari(
        layer,
        lines
    )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    draw_footer(
        layer
    )

    # --------------------------------------------------------
    # Composite text over user's image.
    #
    # This is the ONLY compositing operation.
    # --------------------------------------------------------

    result = Image.alpha_composite(
        image.convert("RGBA"),
        layer
    )

    return result.convert(
        "RGB"
    )


# ============================================================
# IMAGE VIDEO
# ============================================================

def create_image_video(
    background_path: Path,
    lines: List[str],
    duration: int,
) -> ImageClip:

    image = render_image_background(
        background_path,
        lines
    )

    clip = (
        ImageClip(
            np.array(image)
        )
        .set_duration(
            duration
        )
        .set_fps(
            FPS
        )
    )

    return clip


# ============================================================
# VIDEO BACKGROUND
# ============================================================

def prepare_video_background(
    background_path: Path,
    duration: int,
) -> VideoFileClip:

    source = VideoFileClip(
        str(background_path),
        audio=False
    )

    # --------------------------------------------------------
    # Loop if shorter than requested duration.
    # --------------------------------------------------------

    if source.duration < duration:

        repeat_count = int(
            math.ceil(
                duration
                / source.duration
            )
        )

        clips = [
            source
            for _ in range(
                repeat_count
            )
        ]

        from moviepy.editor import concatenate_videoclips

        video = concatenate_videoclips(
            clips,
            method="compose"
        )

        video = video.subclip(
            0,
            duration
        )

    else:

        video = source.subclip(
            0,
            duration
        )

    # --------------------------------------------------------
    # Resize/crop to 9:16.
    # --------------------------------------------------------

    source_w = video.w
    source_h = video.h

    target_ratio = (
        WIDTH
        / HEIGHT
    )

    source_ratio = (
        source_w
        / source_h
    )

    if source_ratio > target_ratio:

        # Landscape.
        new_h = HEIGHT

        new_w = int(
            source_w
            * HEIGHT
            / source_h
        )

        video = video.resize(
            height=HEIGHT
        )

        x1 = (
            new_w
            - WIDTH
        ) // 2

        video = video.crop(
            x1=x1,
            y1=0,
            x2=x1 + WIDTH,
            y2=HEIGHT
        )

    else:

        # Portrait.
        new_w = WIDTH

        new_h = int(
            source_h
            * WIDTH
            / source_w
        )

        video = video.resize(
            width=WIDTH
        )

        y1 = (
            new_h
            - HEIGHT
        ) // 2

        video = video.crop(
            x1=0,
            y1=y1,
            x2=WIDTH,
            y2=y1 + HEIGHT
        )

    return video


# ============================================================
# TEXT OVERLAY FOR VIDEO BACKGROUND
# ============================================================

def make_text_frame(
    lines: List[str]
) -> np.ndarray:

    layer = Image.new(
        "RGBA",
        (
            WIDTH,
            HEIGHT
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    draw_brand(
        layer,
        "Mehfil-e-Shayariii"
    )

    draw_shayari(
        layer,
        lines
    )

    draw_footer(
        layer
    )

    return np.array(
        layer
    )


# ============================================================
# VIDEO BACKGROUND RENDER
# ============================================================

def create_video_background(
    background_path: Path,
    lines: List[str],
    duration: int,
):

    video = prepare_video_background(
        background_path,
        duration
    )

    # --------------------------------------------------------
    # Text is rendered as a transparent layer.
    #
    # IMPORTANT:
    # No card.
    # No page.
    # No image.
    # --------------------------------------------------------

    text_frame = make_text_frame(
        lines
    )

    text_clip = (
        ImageClip(
            text_frame,
            transparent=True
        )
        .set_duration(
            duration
        )
        .set_fps(
            FPS
        )
    )

    final = CompositeVideoClip(
        [
            video,
            text_clip
        ],
        size=(
            WIDTH,
            HEIGHT
        )
    )

    return final


# ============================================================
# MUSIC
# ============================================================

def add_music(
    video,
    music_path: Path,
    duration: int,
):

    print(
        f"🎵 Loading music: {music_path}"
    )

    music = AudioFileClip(
        str(music_path)
    )

    # --------------------------------------------------------
    # Loop music if shorter than video.
    # --------------------------------------------------------

    if music.duration < duration:

        loops = int(
            math.ceil(
                duration
                / music.duration
            )
        )

        clips = []

        for _ in range(
            loops
        ):

            clips.append(
                AudioFileClip(
                    str(music_path)
                )
            )

        music = concatenate_audioclips(
            clips
        )

    # --------------------------------------------------------
    # Trim.
    # --------------------------------------------------------

    music = music.subclip(
        0,
        duration
    )

    # --------------------------------------------------------
    # Keep user's music audible.
    #
    # No TTS exists in this project.
    # --------------------------------------------------------

    music = music.volumex(
        float(
            os.getenv(
                "MUSIC_VOLUME",
                "0.40"
            )
        )
    )

    video = video.set_audio(
        music
    )

    return video


# ============================================================
# CREATE VIDEO
# ============================================================

def create_video(
    lines: List[str],
    output_path: str,
    duration: int = DEFAULT_DURATION,
) -> str:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    background_path = find_background()

    music_path = find_music()

    print()
    print("=" * 60)
    print("HINDI / HINGLISH SHAYARI VIDEO")
    print("=" * 60)

    print(
        f"Background: {background_path}"
    )

    print(
        f"Music: {music_path}"
    )

    print(
        f"Resolution: {WIDTH}x{HEIGHT}"
    )

    print(
        f"Duration: {duration}s"
    )

    print(
        "Design: USER BACKGROUND + STATIC TEXT ONLY"
    )

    # --------------------------------------------------------
    # Generate background video.
    # --------------------------------------------------------

    extension = (
        background_path
        .suffix
        .lower()
    )

    video_extensions = {
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".webm",
    }

    if extension in video_extensions:

        video = create_video_background(
            background_path,
            lines,
            duration
        )

    else:

        video = create_image_video(
            background_path,
            lines,
            duration
        )

    # --------------------------------------------------------
    # Add user's music.
    # --------------------------------------------------------

    video = add_music(
        video,
        music_path,
        duration
    )

    # --------------------------------------------------------
    # Write MP4.
    # --------------------------------------------------------

    print()
    print(
        "🎬 Rendering final MP4..."
    )

    video.write_videofile(
        str(output_path),

        fps=FPS,

        codec="libx264",

        audio_codec="aac",

        audio_bitrate="192k",

        preset="medium",

        bitrate="6000k",

        threads=4,

        ffmpeg_params=[
            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",
        ],

        temp_audiofile=str(
            OUTPUT_DIR
            / "temp_audio.m4a"
        ),

        remove_temp=True,
    )

    # --------------------------------------------------------
    # Close resources.
    # --------------------------------------------------------

    try:
        video.close()
    except Exception:
        pass

    print()
    print("=" * 60)
    print("✅ VIDEO CREATED")
    print("=" * 60)

    print(
        output_path
    )

    return str(
        output_path
    )


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

def generate_video(
    lines: List[str],
    output_path: str,
    duration: int = DEFAULT_DURATION,
) -> str:

    return create_video(
        lines=lines,
        output_path=output_path,
        duration=duration
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_lines = [
        "Jo dil se chaha,",
        "woh kabhi mera hua hi nahi,",
        "",
        "aur jise bhoolna chaha,",
        "uski yaadein kabhi gayi hi nahi.",
    ]

    output = (
        OUTPUT_DIR
        / "test_shayari.mp4"
    )

    create_video(
        lines=test_lines,
        output_path=str(
            output
        ),
        duration=15
    )
