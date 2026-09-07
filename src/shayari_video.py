# ============================================================
# FILE: src/shayari_video.py
# ============================================================
#
# HINGLISH SHAYARI SHORTS VIDEO GENERATOR
#
# FINAL SETTINGS:
#
#   Resolution : 1080 x 1920
#   Aspect     : 9:16
#   Duration   : RANDOM 5 / 6 / 7 seconds
#   Font       : Times New Roman Regular
#   Text       : Static
#   Voice      : NONE
#   Animation  : NONE
#   Background : User asset only
#   Music      : User asset only
#
# NO:
#   ❌ Cream card
#   ❌ Paper background
#   ❌ Logo
#   ❌ Handle
#   ❌ Footer
#   ❌ TTS
#   ❌ Kinetic typography
#   ❌ Text animation
#
# ============================================================

from __future__ import annotations

import os
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter


# ============================================================
# CONFIG
# ============================================================

WIDTH = 1080
HEIGHT = 1920

FPS = 30

MIN_DURATION = 5
MAX_DURATION = 7

# Allowed final durations ONLY.
ALLOWED_DURATIONS = [5, 6, 7]

# Times New Roman Regular is the required font.
FONT_SIZE = 62

# Line spacing
LINE_SPACING = 24

# Space between poetry stanzas
STANZA_GAP = 55

# Text color requested from reference style.
TEXT_COLOR = (0, 0, 0, 255)

# Maximum width available for text.
TEXT_MAX_WIDTH = 860

# Vertical position.
#
# 0.42 means the main poetry area starts around 42%
# of the screen height.
TEXT_TOP_RATIO = 0.40

# Background processing
BACKGROUND_BRIGHTNESS = 1.02
BACKGROUND_CONTRAST = 1.05
BACKGROUND_SATURATION = 0.92
BACKGROUND_SHARPNESS = 1.02


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

ASSETS_DIR = ROOT / "assets"

MUSIC_DIR = ASSETS_DIR / "music"

OUTPUT_DIR = ROOT / "output"


# ============================================================
# SUPPORTED FILE TYPES
# ============================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
}


# ============================================================
# FIND BACKGROUND
# ============================================================

def find_background() -> Path:
    """
    Find user's background.

    Priority:
        background.*
        bg.*
        then first image/video asset
    """

    if not ASSETS_DIR.exists():
        raise FileNotFoundError(
            f"Assets directory not found: {ASSETS_DIR}"
        )

    priority_names = [
        "background",
        "bg",
        "background_image",
        "background_video",
        "shayari_background",
    ]

    files = [
        p
        for p in ASSETS_DIR.iterdir()
        if p.is_file()
    ]

    # First search exact priority names.
    for name in priority_names:

        for path in files:

            if path.stem.lower() == name.lower():

                if (
                    path.suffix.lower()
                    in IMAGE_EXTENSIONS
                    or
                    path.suffix.lower()
                    in VIDEO_EXTENSIONS
                ):
                    return path

    # Then image files
    images = [
        p
        for p in files
        if p.suffix.lower()
        in IMAGE_EXTENSIONS
    ]

    if images:
        return sorted(images)[0]

    # Then videos
    videos = [
        p
        for p in files
        if p.suffix.lower()
        in VIDEO_EXTENSIONS
    ]

    if videos:
        return sorted(videos)[0]

    raise FileNotFoundError(
        "No background image/video found in assets/."
    )


# ============================================================
# FIND MUSIC
# ============================================================

def find_music() -> Path | None:
    """
    Find user-provided background music.

    Searches:
        assets/music/
    """

    if not MUSIC_DIR.exists():
        return None

    supported_audio = {
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".ogg",
        ".flac",
    }

    files = [
        p
        for p in MUSIC_DIR.iterdir()
        if (
            p.is_file()
            and p.suffix.lower()
            in supported_audio
        )
    ]

    if not files:
        return None

    # Prefer bg_music if available.
    for path in files:

        if path.stem.lower() in {
            "bg_music",
            "background_music",
            "music",
            "bg",
        }:
            return path

    return sorted(files)[0]


# ============================================================
# FIND TIMES NEW ROMAN REGULAR
# ============================================================

def find_times_new_roman_regular() -> str:
    """
    Find Times New Roman Regular.

    IMPORTANT:
    We intentionally search ONLY for regular Times New Roman
    first. Bold/Italic fonts are never intentionally selected.
    """

    candidates = []

    windows_fonts = os.environ.get(
        "WINDIR"
    )

    if windows_fonts:

        font_dir = (
            Path(windows_fonts)
            / "Fonts"
        )

        candidates.extend(
            [
                font_dir / "times.ttf",
                font_dir / "Times New Roman.ttf",
                font_dir / "timesnr.ttf",
            ]
        )

    # Common Linux font locations
    candidates.extend(
        [
            Path(
                "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf"
            ),
            Path(
                "/usr/share/fonts/truetype/msttcorefonts/times.ttf"
            ),
            Path(
                "/usr/share/fonts/truetype/msttcorefonts/timesnr.ttf"
            ),
        ]
    )

    # Project-local font.
    #
    # If you put:
    #
    # assets/fonts/times.ttf
    #
    # it will be preferred.
    local_candidates = [
        ASSETS_DIR
        / "fonts"
        / "times.ttf",

        ASSETS_DIR
        / "fonts"
        / "times_new_roman.ttf",

        ASSETS_DIR
        / "fonts"
        / "Times New Roman.ttf",

        ASSETS_DIR
        / "fonts"
        / "TimesNewRoman.ttf",
    ]

    # Project-local Times New Roman gets priority.
    candidates = (
        local_candidates
        + candidates
    )

    for path in candidates:

        if path.exists():

            return str(path)

    # Search recursively for likely regular Times font.
    font_dirs = []

    if windows_fonts:
        font_dirs.append(
            Path(windows_fonts) / "Fonts"
        )

    font_dirs.append(
        ASSETS_DIR / "fonts"
    )

    for directory in font_dirs:

        if not directory.exists():
            continue

        try:

            for path in directory.rglob(
                "*.ttf"
            ):

                name = path.name.lower()

                # Avoid bold/italic variants.
                if (
                    "bold" in name
                    or "italic" in name
                    or "oblique" in name
                ):
                    continue

                if (
                    "times" in name
                    and (
                        "new" in name
                        or "roman" in name
                        or "times" in name
                    )
                ):
                    return str(path)

        except Exception:
            pass

    # Linux fallback.
    linux_candidates = [
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]

    for path in linux_candidates:

        if Path(path).exists():
            print(
                "[WARNING] Times New Roman Regular "
                "not found. Using serif fallback:"
            )
            print(path)

            return path

    raise FileNotFoundError(
        "Times New Roman Regular font not found."
    )


# ============================================================
# FONT
# ============================================================

def load_font(
    size: int = FONT_SIZE,
) -> ImageFont.FreeTypeFont:

    font_path = find_times_new_roman_regular()

    print(
        "[FONT]",
        font_path,
    )

    return ImageFont.truetype(
        font_path,
        size=size,
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(
    text: str,
) -> str:
    """
    Clean Shayari before rendering.
    """

    if not text:
        return ""

    text = str(text)

    # Remove markdown
    text = text.replace(
        "```",
        "",
    )

    # Remove accidental hashtags
    text = re.sub(
        r"#\w+",
        "",
        text,
    )

    # Remove common labels
    text = re.sub(
        r"^\s*(shayari|poetry|poem)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    lines = []

    for line in text.split("\n"):

        line = line.strip()

        if not line:
            lines.append("")
            continue

        line = re.sub(
            r"\s+",
            " ",
            line,
        )

        lines.append(line)

    # Maximum 2 consecutive blank lines
    cleaned = []

    blank_count = 0

    for line in lines:

        if line == "":

            blank_count += 1

            if blank_count <= 2:
                cleaned.append("")

        else:

            blank_count = 0
            cleaned.append(line)

    return "\n".join(
        cleaned
    ).strip()


# ============================================================
# BACKGROUND FILTER
# ============================================================

def process_background(
    image: Image.Image,
) -> Image.Image:
    """
    Apply a subtle cinematic correction.

    No artificial card/page is added.
    """

    image = image.convert(
        "RGB"
    )

    image = ImageEnhance.Brightness(
        image
    ).enhance(
        BACKGROUND_BRIGHTNESS
    )

    image = ImageEnhance.Contrast(
        image
    ).enhance(
        BACKGROUND_CONTRAST
    )

    image = ImageEnhance.Color(
        image
    ).enhance(
        BACKGROUND_SATURATION
    )

    image = ImageEnhance.Sharpness(
        image
    ).enhance(
        BACKGROUND_SHARPNESS
    )

    return image


# ============================================================
# COVER / CROP IMAGE
# ============================================================

def resize_cover(
    image: Image.Image,
    width: int = WIDTH,
    height: int = HEIGHT,
) -> Image.Image:
    """
    Resize image to fill 1080x1920 without distortion.

    Center crop is used.
    """

    image = image.convert(
        "RGB"
    )

    src_w, src_h = image.size

    target_ratio = (
        width / height
    )

    src_ratio = (
        src_w / src_h
    )

    if src_ratio > target_ratio:

        # Image too wide
        new_h = height

        new_w = int(
            src_w
            * (
                height / src_h
            )
        )

    else:

        # Image too tall
        new_w = width

        new_h = int(
            src_h
            * (
                width / src_w
            )
        )

    image = image.resize(
        (
            new_w,
            new_h,
        ),
        Image.Resampling.LANCZOS,
    )

    left = (
        new_w - width
    ) // 2

    top = (
        new_h - height
    ) // 2

    image = image.crop(
        (
            left,
            top,
            left + width,
            top + height,
        )
    )

    return image


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """
    Wrap a single line based on actual pixel width.
    """

    words = text.split()

    if not words:
        return [""]

    lines = []

    current = words[0]

    for word in words[1:]:

        test = (
            current
            + " "
            + word
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font,
        )

        width = (
            bbox[2]
            - bbox[0]
        )

        if width <= max_width:

            current = test

        else:

            lines.append(
                current
            )

            current = word

    lines.append(
        current
    )

    return lines


def prepare_text_lines(
    text: str,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
) -> list[tuple[str, int]]:
    """
    Prepare wrapped lines.

    Returns:
        (line_text, extra_gap_after)
    """

    text = clean_text(
        text
    )

    result = []

    for raw_line in text.split("\n"):

        if not raw_line:

            result.append(
                (
                    "",
                    STANZA_GAP,
                )
            )

            continue

        wrapped = wrap_line(
            draw,
            raw_line,
            font,
            TEXT_MAX_WIDTH,
        )

        for index, line in enumerate(
            wrapped
        ):

            result.append(
                (
                    line,
                    0,
                )
            )

    return result


# ============================================================
# TEXT LAYER
# ============================================================

def create_text_layer(
    text: str,
) -> Image.Image:
    """
    Create transparent RGBA text layer.

    IMPORTANT:
    The background is NOT placed on this layer.

    This prevents a video background from freezing.
    """

    layer = Image.new(
        "RGBA",
        (
            WIDTH,
            HEIGHT,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    draw = ImageDraw.Draw(
        layer
    )

    font = load_font(
        FONT_SIZE
    )

    lines = prepare_text_lines(
        text,
        draw,
        font,
    )

    # Determine total text height.
    line_height = (
        font.getbbox("Ag")[3]
        - font.getbbox("Ag")[1]
    )

    total_height = 0

    for line, gap in lines:

        if line:

            total_height += (
                line_height
                + LINE_SPACING
            )

        total_height += gap

    # Prevent text from going off-screen.
    max_text_height = int(
        HEIGHT * 0.52
    )

    if total_height > max_text_height:

        # Dynamically reduce font size.
        adjusted_size = FONT_SIZE

        while (
            total_height > max_text_height
            and adjusted_size > 42
        ):

            adjusted_size -= 2

            font = load_font(
                adjusted_size
            )

            lines = prepare_text_lines(
                text,
                draw,
                font,
            )

            line_height = (
                font.getbbox("Ag")[3]
                - font.getbbox("Ag")[1]
            )

            total_height = 0

            for line, gap in lines:

                if line:

                    total_height += (
                        line_height
                        + LINE_SPACING
                    )

                total_height += gap

    # Vertical center around requested area.
    top_y = int(
        HEIGHT * TEXT_TOP_RATIO
    )

    # Slightly center the complete block.
    if total_height < max_text_height:

        top_y -= int(
            (
                max_text_height
                - total_height
            )
            * 0.15
        )

    y = max(
        80,
        top_y,
    )

    for line, gap in lines:

        if not line:

            y += gap
            continue

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font,
        )

        text_width = (
            bbox[2]
            - bbox[0]
        )

        x = (
            WIDTH
            - text_width
        ) // 2

        # Pure black Times New Roman Regular.
        draw.text(
            (
                x,
                y,
            ),
            line,
            font=font,
            fill=TEXT_COLOR,
        )

        y += (
            line_height
            + LINE_SPACING
        )

    return layer


# ============================================================
# CREATE IMAGE FRAME
# ============================================================

def create_image_frame(
    background_path: Path,
    text_layer: Image.Image,
) -> Image.Image:
    """
    Create final image frame.
    """

    background = Image.open(
        background_path
    ).convert(
        "RGB"
    )

    background = resize_cover(
        background,
        WIDTH,
        HEIGHT,
    )

    background = process_background(
        background
    )

    frame = background.convert(
        "RGBA"
    )

    frame.alpha_composite(
        text_layer
    )

    return frame.convert(
        "RGB"
    )


# ============================================================
# FFMPEG COMMAND
# ============================================================

def run_ffmpeg(
    command: list[str],
) -> None:
    """
    Run FFmpeg and raise useful error.
    """

    print(
        "\n[FFMPEG]"
    )

    print(
        " ".join(
            str(x)
            for x in command
        )
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        print(
            result.stderr
        )

        raise RuntimeError(
            "FFmpeg failed."
        )


# ============================================================
# IMAGE VIDEO GENERATION
# ============================================================

def render_image_background(
    background_path: Path,
    text_layer: Image.Image,
    output_path: Path,
    duration: int,
) -> None:
    """
    Render static image background.
    """

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="shayari_"
        )
    )

    try:

        frame_path = (
            temp_dir
            / "frame.png"
        )

        frame = create_image_frame(
            background_path,
            text_layer,
        )

        frame.save(
            frame_path,
            "PNG",
        )

        command = [
            "ffmpeg",
            "-y",

            "-loop",
            "1",

            "-i",
            str(frame_path),

            "-t",
            str(duration),

            "-r",
            str(FPS),

            "-vf",
            (
                f"scale={WIDTH}:{HEIGHT}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={WIDTH}:{HEIGHT}:"
                "(ow-iw)/2:(oh-ih)/2"
            ),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            str(output_path),
        ]

        run_ffmpeg(
            command
        )

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


# ============================================================
# VIDEO BACKGROUND GENERATION
# ============================================================

def render_video_background(
    background_path: Path,
    text_layer: Image.Image,
    output_path: Path,
    duration: int,
) -> None:
    """
    Render video background.

    IMPORTANT:
    Text is generated as a transparent PNG and overlaid
    with FFmpeg.

    This keeps the actual background video moving.
    """

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="shayari_video_"
        )
    )

    try:

        text_path = (
            temp_dir
            / "text_overlay.png"
        )

        text_layer.save(
            text_path,
            "PNG",
        )

        command = [
            "ffmpeg",
            "-y",

            "-stream_loop",
            "-1",

            "-i",
            str(background_path),

            "-loop",
            "1",

            "-i",
            str(text_path),

            "-t",
            str(duration),

            "-filter_complex",
            (
                f"[0:v]"
                f"scale={WIDTH}:{HEIGHT}:"
                "force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{HEIGHT},"
                "eq="
                f"brightness=0.005:"
                f"contrast={BACKGROUND_CONTRAST}:"
                f"saturation={BACKGROUND_SATURATION}"
                "[bg];"

                "[1:v]"
                f"format=rgba"
                "[txt];"

                "[bg][txt]"
                "overlay=0:0:"
                "format=yuv420p"
                "[outv]"
            ),

            "-map",
            "[outv]",

            "-an",

            "-r",
            str(FPS),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            str(output_path),
        ]

        run_ffmpeg(
            command
        )

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


# ============================================================
# ADD MUSIC
# ============================================================

def add_music(
    video_path: Path,
    music_path: Path,
    output_path: Path,
    duration: int,
) -> None:
    """
    Add user-provided music.

    Music is looped if shorter than video.
    Music is trimmed if longer.
    """

    command = [
        "ffmpeg",
        "-y",

        "-i",
        str(video_path),

        "-stream_loop",
        "-1",

        "-i",
        str(music_path),

        "-t",
        str(duration),

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "copy",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "48000",

        "-ac",
        "2",

        "-shortest",

        "-movflags",
        "+faststart",

        str(output_path),
    ]

    run_ffmpeg(
        command
    )


# ============================================================
# VERIFY VIDEO
# ============================================================

def verify_video(
    output_path: Path,
    expected_duration: int,
) -> None:
    """
    Verify generated MP4.
    """

    command = [
        "ffprobe",
        "-v",
        "error",

        "-show_entries",
        "format=duration",

        "-show_entries",
        "stream=width,height",

        "-of",
        "default=noprint_wrappers=1",

        str(output_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            "ffprobe failed while checking video."
        )

    output = result.stdout

    print(
        "\n[VIDEO VERIFY]"
    )

    print(
        output
    )

    if (
        "width=1080" not in output
        or "height=1920" not in output
    ):

        raise RuntimeError(
            "Video is not 1080x1920."
        )


# ============================================================
# FINAL VIDEO CREATOR
# ============================================================

def create_video(
    text: str,
    output_path: str,
    duration: int | None = None,
) -> dict:
    """
    Main video creation function.

    Parameters:
        text:
            Shayari text.

        output_path:
            Final MP4 path.

        duration:
            Optional.

            If omitted:
                random 5/6/7 sec.

            If provided:
                it MUST be 5, 6 or 7.

    Returns:
        {
            "path": "...",
            "duration": 5,
            "background": "...",
            "music": "..."
        }
    """

    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------

    if duration is None:

        duration = random.choice(
            ALLOWED_DURATIONS
        )

    else:

        duration = int(
            duration
        )

        if duration not in ALLOWED_DURATIONS:

            raise ValueError(
                "Duration must be exactly "
                "5, 6 or 7 seconds."
            )

    print(
        "\n" + "=" * 60
    )

    print(
        "CREATING SHAYARI SHORT"
    )

    print(
        "=" * 60
    )

    print(
        f"[DURATION] {duration} seconds"
    )

    print(
        "[RESOLUTION] 1080x1920"
    )

    print(
        "[FONT] Times New Roman Regular"
    )

    # --------------------------------------------------------
    # Paths
    # --------------------------------------------------------

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    background = find_background()

    music = find_music()

    print(
        f"[BACKGROUND] {background}"
    )

    if music:

        print(
            f"[MUSIC] {music}"
        )

    else:

        print(
            "[MUSIC] No music found."
        )

    # --------------------------------------------------------
    # Text layer
    # --------------------------------------------------------

    text_layer = create_text_layer(
        text
    )

    # --------------------------------------------------------
    # Temporary video without audio
    # --------------------------------------------------------

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="shayari_final_"
        )
    )

    silent_video = (
        temp_dir
        / "silent.mp4"
    )

    final_video = (
        temp_dir
        / "final.mp4"
    )

    try:

        # ----------------------------------------------------
        # Background
        # ----------------------------------------------------

        if (
            background.suffix.lower()
            in IMAGE_EXTENSIONS
        ):

            render_image_background(
                background,
                text_layer,
                silent_video,
                duration,
            )

        elif (
            background.suffix.lower()
            in VIDEO_EXTENSIONS
        ):

            render_video_background(
                background,
                text_layer,
                silent_video,
                duration,
            )

        else:

            raise ValueError(
                f"Unsupported background format: "
                f"{background.suffix}"
            )

        # ----------------------------------------------------
        # Music
        # ----------------------------------------------------

        if music:

            add_music(
                silent_video,
                music,
                final_video,
                duration,
            )

        else:

            shutil.copy2(
                silent_video,
                final_video,
            )

        # ----------------------------------------------------
        # Copy final output
        # ----------------------------------------------------

        shutil.copy2(
            final_video,
            output_path,
        )

        # ----------------------------------------------------
        # Verify
        # ----------------------------------------------------

        verify_video(
            output_path,
            duration,
        )

        print(
            "\n[SUCCESS]"
        )

        print(
            f"Video: {output_path}"
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

        return {
            "path": str(
                output_path
            ),
            "duration": duration,
            "background": str(
                background
            ),
            "music": (
                str(music)
                if music
                else None
            ),
        }

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

def generate_video(
    text: str,
    output_path: str,
    duration: int | None = None,
):
    """
    Compatibility alias.
    """

    return create_video(
        text,
        output_path,
        duration,
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_output = (
        OUTPUT_DIR
        / "test_shayari.mp4"
    )

    test_text = (
        "Jo dil ke kareeb tha,\n"
        "wahi aaj sabse door hai.\n"
        "\n"
        "Kuch rishte khatam nahi hote,\n"
        "bas khamosh ho jaate hain."
    )

    result = create_video(
        text=test_text,
        output_path=str(
            test_output
        ),
        duration=None,
    )

    print(
        "\nTEST RESULT:"
    )

    print(
        result
    )
