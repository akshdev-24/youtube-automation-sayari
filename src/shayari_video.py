# ============================================================
# FILE: src/shayari_video.py
# HINGLISH SHAYARI STATIC SHORT VIDEO GENERATOR
# ============================================================

from pathlib import Path
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)


# ============================================================
# CONFIG
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = ROOT_DIR / "assets"
MUSIC_DIR = ASSETS_DIR / "music"

WIDTH = 1080
HEIGHT = 1920

DEFAULT_DURATION = int(
    os.getenv("SHAYARI_DURATION", "15")
)

FPS = 30


# ============================================================
# BACKGROUND SEARCH
# ============================================================

def find_background():
    """
    Find user-provided background.

    Priority:
        background.jpg
        background.jpeg
        background.png
        background.webp
        background.mp4
        background.mov
        fallback.jpg
    """

    image_files = [
        "background.jpg",
        "background.jpeg",
        "background.png",
        "background.webp",
        "bg.jpg",
        "bg.jpeg",
        "bg.png",
    ]

    video_files = [
        "background.mp4",
        "background.mov",
        "background.webm",
        "bg.mp4",
        "bg.mov",
    ]

    for filename in image_files:
        path = ASSETS_DIR / filename

        if path.exists():
            return path

    for filename in video_files:
        path = ASSETS_DIR / filename

        if path.exists():
            return path

    fallback = ASSETS_DIR / "fallback.jpg"

    if fallback.exists():
        return fallback

    raise FileNotFoundError(
        "No background found.\n"
        "Put your background at:\n"
        "assets/background.jpg"
    )


# ============================================================
# MUSIC SEARCH
# ============================================================

def find_music():
    """
    Find background music inside assets/music.
    """

    if not MUSIC_DIR.exists():
        return None

    extensions = [
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".ogg",
    ]

    for file in sorted(
        MUSIC_DIR.iterdir()
    ):

        if file.is_file() and file.suffix.lower() in extensions:
            return file

    return None


# ============================================================
# CROP IMAGE TO 9:16
# ============================================================

def crop_to_vertical(
    image: Image.Image,
    width=WIDTH,
    height=HEIGHT,
):
    """
    Crop image to exact 1080x1920 aspect ratio.
    """

    image = image.convert("RGB")

    target_ratio = width / height
    image_ratio = image.width / image.height

    if image_ratio > target_ratio:

        # Image too wide.
        new_width = int(
            image.height * target_ratio
        )

        left = (
            image.width - new_width
        ) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_width,
                image.height,
            )
        )

    else:

        # Image too tall.
        new_height = int(
            image.width / target_ratio
        )

        top = (
            image.height - new_height
        ) // 2

        image = image.crop(
            (
                0,
                top,
                image.width,
                top + new_height,
            )
        )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )


# ============================================================
# FONT
# ============================================================

def find_font(
    bold=False,
    size=60,
):
    """
    Find a usable font from assets/fonts.
    """

    font_dir = ASSETS_DIR / "fonts"

    candidates = []

    if bold:

        candidates = [
            font_dir / "arialbd.ttf",
            font_dir / "arial.ttf",
        ]

    else:

        candidates = [
            font_dir / "arial.ttf",
            font_dir / "ariali.ttf",
        ]

    for path in candidates:

        if path.exists():

            return ImageFont.truetype(
                str(path),
                size,
            )

    # Linux/GitHub Actions fallback.
    linux_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in linux_fonts:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size,
            )

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_shayari(
    text,
    font,
    max_width,
    draw,
):
    """
    Wrap Shayari based on actual pixel width.
    """

    output_lines = []

    for original_line in text.splitlines():

        line = original_line.strip()

        if not line:
            output_lines.append("")
            continue

        words = line.split()

        current = ""

        for word in words:

            test = (
                word
                if not current
                else current + " " + word
            )

            bbox = draw.textbbox(
                (0, 0),
                test,
                font=font,
            )

            text_width = (
                bbox[2] - bbox[0]
            )

            if text_width <= max_width:

                current = test

            else:

                if current:
                    output_lines.append(
                        current
                    )

                current = word

        if current:
            output_lines.append(
                current
            )

    return output_lines


# ============================================================
# CREATE STATIC CARD
# ============================================================

def create_shayari_card(
    shayari: str,
):
    """
    Create the static cream Shayari card.

    No animation.
    """

    # --------------------------------------------------------
    # Transparent overlay
    # --------------------------------------------------------

    card = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        card
    )

    # --------------------------------------------------------
    # Card dimensions
    # --------------------------------------------------------

    card_left = 70
    card_right = WIDTH - 70

    card_top = 170
    card_bottom = HEIGHT - 170

    card_width = (
        card_right - card_left
    )

    card_height = (
        card_bottom - card_top
    )

    radius = 42

    # --------------------------------------------------------
    # Shadow
    # --------------------------------------------------------

    shadow = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    shadow_draw = ImageDraw.Draw(
        shadow
    )

    shadow_draw.rounded_rectangle(
        (
            card_left + 12,
            card_top + 18,
            card_right + 12,
            card_bottom + 18,
        ),
        radius=radius,
        fill=(0, 0, 0, 150),
    )

    shadow = shadow.filter(
        ImageFilter.GaussianBlur(18)
    )

    card.alpha_composite(
        shadow
    )

    draw = ImageDraw.Draw(
        card
    )

    # --------------------------------------------------------
    # Main cream card
    # --------------------------------------------------------

    draw.rounded_rectangle(
        (
            card_left,
            card_top,
            card_right,
            card_bottom,
        ),
        radius=radius,
        fill=(242, 235, 220, 255),
    )

    # --------------------------------------------------------
    # Top brand
    # --------------------------------------------------------

    brand_font = find_font(
        bold=True,
        size=34,
    )

    small_font = find_font(
        bold=False,
        size=25,
    )

    brand = "MEHFIL-E-SHAYARI"

    brand_bbox = draw.textbbox(
        (0, 0),
        brand,
        font=brand_font,
    )

    brand_width = (
        brand_bbox[2]
        - brand_bbox[0]
    )

    brand_x = (
        WIDTH - brand_width
    ) // 2

    draw.text(
        (
            brand_x,
            card_top + 70,
        ),
        brand,
        font=brand_font,
        fill=(45, 40, 35, 255),
    )

    # Small divider.
    divider_y = card_top + 125

    draw.line(
        (
            WIDTH // 2 - 50,
            divider_y,
            WIDTH // 2 + 50,
            divider_y,
        ),
        fill=(100, 90, 75, 180),
        width=2,
    )

    # --------------------------------------------------------
    # Shayari font
    # --------------------------------------------------------

    shayari_font_size = 58

    shayari_font = find_font(
        bold=False,
        size=shayari_font_size,
    )

    max_text_width = card_width - 130

    lines = wrap_shayari(
        shayari,
        shayari_font,
        max_text_width,
        draw,
    )

    # --------------------------------------------------------
    # Calculate total text height
    # --------------------------------------------------------

    line_spacing = 24

    measured_lines = []

    for line in lines:

        if not line:
            measured_lines.append(
                (0, 0)
            )
            continue

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=shayari_font,
        )

        measured_lines.append(
            (
                bbox[2] - bbox[0],
                bbox[3] - bbox[1],
            )
        )

    total_height = 0

    for _, line_height in measured_lines:

        total_height += (
            line_height
            + line_spacing
        )

    # --------------------------------------------------------
    # Keep text inside card.
    # --------------------------------------------------------

    available_height = (
        card_height - 330
    )

    while (
        total_height > available_height
        and shayari_font_size > 38
    ):

        shayari_font_size -= 2

        shayari_font = find_font(
            bold=False,
            size=shayari_font_size,
        )

        lines = wrap_shayari(
            shayari,
            shayari_font,
            max_text_width,
            draw,
        )

        measured_lines = []

        for line in lines:

            if not line:
                measured_lines.append(
                    (0, 0)
                )
                continue

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=shayari_font,
            )

            measured_lines.append(
                (
                    bbox[2] - bbox[0],
                    bbox[3] - bbox[1],
                )
            )

        total_height = sum(
            height + line_spacing
            for _, height in measured_lines
        )

    # --------------------------------------------------------
    # Center Shayari vertically.
    # --------------------------------------------------------

    text_start_y = (
        card_top
        + (card_height - total_height) // 2
        + 20
    )

    current_y = text_start_y

    for index, line in enumerate(lines):

        if not line:
            current_y += 20
            continue

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=shayari_font,
        )

        line_width = (
            bbox[2] - bbox[0]
        )

        line_height = (
            bbox[3] - bbox[1]
        )

        x = (
            WIDTH - line_width
        ) // 2

        draw.text(
            (
                x,
                current_y,
            ),
            line,
            font=shayari_font,
            fill=(35, 32, 29, 255),
        )

        current_y += (
            line_height
            + line_spacing
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    footer = "HINGLISH SHAYARI"

    footer_bbox = draw.textbbox(
        (0, 0),
        footer,
        font=small_font,
    )

    footer_width = (
        footer_bbox[2]
        - footer_bbox[0]
    )

    footer_x = (
        WIDTH - footer_width
    ) // 2

    draw.text(
        (
            footer_x,
            card_bottom - 80,
        ),
        footer,
        font=small_font,
        fill=(95, 85, 72, 230),
    )

    return card


# ============================================================
# PREPARE IMAGE BACKGROUND
# ============================================================

def prepare_image_background(
    path: Path,
):
    """
    Load and prepare static image background.
    """

    image = Image.open(
        path
    ).convert("RGB")

    image = crop_to_vertical(
        image
    )

    temp_path = (
        ROOT_DIR
        / "output"
        / "_background_temp.jpg"
    )

    temp_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image.save(
        temp_path,
        quality=95,
    )

    return temp_path


# ============================================================
# PREPARE VIDEO BACKGROUND
# ============================================================

def prepare_video_background(
    path: Path,
    duration: float,
):
    """
    Load video background and crop it to 9:16.
    """

    clip = VideoFileClip(
        str(path)
    )

    # If source is shorter than desired duration,
    # loop it.
    if clip.duration < duration:

        loops = int(
            duration / clip.duration
        ) + 1

        clips = [
            clip
            for _ in range(loops)
        ]

        clip = concatenate_videoclips(
            clips
        )

    clip = clip.subclip(
        0,
        min(
            duration,
            clip.duration,
        ),
    )

    # --------------------------------------------------------
    # Resize while maintaining aspect ratio.
    # --------------------------------------------------------

    source_ratio = (
        clip.w / clip.h
    )

    target_ratio = (
        WIDTH / HEIGHT
    )

    if source_ratio > target_ratio:

        # Source too wide.
        clip = clip.resize(
            height=HEIGHT
        )

        x1 = (
            clip.w - WIDTH
        ) / 2

        clip = clip.crop(
            x1=x1,
            x2=x1 + WIDTH,
        )

    else:

        # Source too tall.
        clip = clip.resize(
            width=WIDTH
        )

        y1 = (
            clip.h - HEIGHT
        ) / 2

        clip = clip.crop(
            y1=y1,
            y2=y1 + HEIGHT,
        )

    return clip


# ============================================================
# MUSIC
# ============================================================

def add_music(
    video_clip,
    music_path,
    duration,
):
    """
    Add background music and loop if necessary.
    """

    if music_path is None:

        print(
            "⚠️ No music found."
        )

        return video_clip

    print(
        f"🎵 Music: {music_path.name}"
    )

    music = AudioFileClip(
        str(music_path)
    )

    # --------------------------------------------------------
    # Loop music if shorter than video.
    # --------------------------------------------------------

    if music.duration < duration:

        loops = int(
            duration / music.duration
        ) + 1

        audio_clips = []

        for _ in range(loops):

            audio_clips.append(
                AudioFileClip(
                    str(music_path)
                )
            )

        from moviepy.audio.AudioClip import concatenate_audioclips

        music = concatenate_audioclips(
            audio_clips
        )

    music = music.subclip(
        0,
        min(
            duration,
            music.duration,
        ),
    )

    # Background music should not overpower the video.
    music = music.volumex(
        0.35
    )

    return video_clip.set_audio(
        music
    )


# ============================================================
# CREATE VIDEO
# ============================================================

def create_video(
    shayari: str,
    output_path: Path,
    duration: int = DEFAULT_DURATION,
):
    """
    Main video creation function.

    Output:
        1080x1920 MP4
    """

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "🎬 Preparing video..."
    )

    # --------------------------------------------------------
    # Find assets
    # --------------------------------------------------------

    background_path = find_background()

    music_path = find_music()

    print(
        f"🖼️ Background: {background_path}"
    )

    if music_path:
        print(
            f"🎵 Music: {music_path}"
        )

    # --------------------------------------------------------
    # Background
    # --------------------------------------------------------

    if background_path.suffix.lower() in [
        ".mp4",
        ".mov",
        ".webm",
    ]:

        background_clip = (
            prepare_video_background(
                background_path,
                duration,
            )
        )

    else:

        background_image = (
            prepare_image_background(
                background_path
            )
        )

        background_clip = (
            ImageClip(
                str(background_image)
            )
            .set_duration(
                duration
            )
        )

    # --------------------------------------------------------
    # Create static Shayari card.
    # --------------------------------------------------------

    print(
        "📝 Creating static Shayari card..."
    )

    card_image = create_shayari_card(
        shayari
    )

    card_path = (
        output_path.parent
        / "_shayari_card.png"
    )

    card_image.save(
        card_path
    )

    card_clip = (
        ImageClip(
            str(card_path)
        )
        .set_duration(
            duration
        )
    )

    # --------------------------------------------------------
    # Composite
    # --------------------------------------------------------

    final_video = CompositeVideoClip(
        [
            background_clip,
            card_clip,
        ],
        size=(
            WIDTH,
            HEIGHT,
        ),
    ).set_duration(
        duration
    )

    # --------------------------------------------------------
    # Add music
    # --------------------------------------------------------

    final_video = add_music(
        final_video,
        music_path,
        duration,
    )

    # --------------------------------------------------------
    # Render
    # --------------------------------------------------------

    print(
        "🎞️ Rendering 1080x1920 video..."
    )

    final_video.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        ffmpeg_params=[
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
        ],
        logger="bar",
    )

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    try:
        final_video.close()

    except Exception:
        pass

    try:
        background_clip.close()

    except Exception:
        pass

    print(
        f"✅ Video created: {output_path}"
    )

    return output_path


# ============================================================
# ALIAS
# ============================================================

def generate_video(
    shayari: str,
    output_path: Path,
    duration: int = DEFAULT_DURATION,
):
    """
    Alias for compatibility.
    """

    return create_video(
        shayari=shayari,
        output_path=output_path,
        duration=duration,
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_text = (
        "Kuch log dil mein bas jaate hain,\n"
        "Phir chahe kitni bhi door chale jaayein,\n"
        "Unki yaadein paas hi rehti hain."
    )

    output = (
        ROOT_DIR
        / "output"
        / "test_shayari.mp4"
    )

    create_video(
        shayari=test_text,
        output_path=output,
        duration=15,
    )
