# FILE: src/uploader.py
# Hindi Motivation YouTube Automation Uploader
#
# Handles:
# - YouTube OAuth2 authentication
# - Video upload
# - Hindi SEO title
# - Hindi description
# - Relevant YouTube tags
# - Correct YouTube category
# - Custom thumbnail upload
# - Robust tag handling
# - GitHub Actions compatibility

import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ============================================================
# CONFIGURATION
# ============================================================

CLIENT_SECRETS_FILE = Path("client_secrets.json")
CREDENTIALS_FILE = Path("credentials.json")

YOUTUBE_UPLOAD_SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload"
]

# YouTube category:
# 22 = People & Blogs
# Suitable for motivational/lifestyle content.
YOUTUBE_CATEGORY_ID = "22"

# Public videos
YOUTUBE_PRIVACY_STATUS = "public"


# ============================================================
# AUTHENTICATION
# ============================================================

def get_authenticated_service():
    """
    Authenticate with YouTube using OAuth2.

    Local:
        First run opens browser for authorization.

    GitHub Actions:
        Existing credentials.json is refreshed automatically.
    """

    credentials = None

    # --------------------------------------------------------
    # Existing credentials
    # --------------------------------------------------------

    if CREDENTIALS_FILE.exists():

        print(
            "🔐 Found existing YouTube credentials."
        )

        credentials = (
            Credentials.from_authorized_user_file(
                str(CREDENTIALS_FILE),
                YOUTUBE_UPLOAD_SCOPE
            )
        )

    # --------------------------------------------------------
    # Check credentials
    # --------------------------------------------------------

    if not credentials or not credentials.valid:

        # ----------------------------------------------------
        # Refresh existing credentials
        # ----------------------------------------------------

        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):

            print(
                "🔄 Refreshing expired YouTube credentials..."
            )

            credentials.refresh(
                Request()
            )

        # ----------------------------------------------------
        # First-time authentication
        # ----------------------------------------------------

        else:

            print(
                "🔐 No valid YouTube credentials found."
            )

            print(
                "🌐 Starting OAuth authentication..."
            )

            if not CLIENT_SECRETS_FILE.exists():

                raise FileNotFoundError(
                    f"CRITICAL ERROR: "
                    f"{CLIENT_SECRETS_FILE} not found."
                )

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    str(CLIENT_SECRETS_FILE),
                    scopes=YOUTUBE_UPLOAD_SCOPE
                )
            )

            credentials = flow.run_local_server(
                port=0
            )

        # ----------------------------------------------------
        # Save credentials
        # ----------------------------------------------------

        with open(
            CREDENTIALS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                credentials.to_json()
            )

        print(
            f"✅ Credentials saved to "
            f"{CREDENTIALS_FILE}"
        )

    # --------------------------------------------------------
    # Build YouTube API service
    # --------------------------------------------------------

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials
    )

    print(
        "✅ YouTube API authentication successful."
    )

    return youtube


# ============================================================
# TAG NORMALIZER
# ============================================================

def normalize_tags(tags):
    """
    Accepts:
        - list
        - tuple
        - comma-separated string

    Returns:
        clean list of YouTube tags.
    """

    if not tags:
        return []

    # --------------------------------------------------------
    # List / tuple
    # --------------------------------------------------------

    if isinstance(tags, (list, tuple)):

        raw_tags = list(tags)

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    elif isinstance(tags, str):

        raw_tags = tags.split(",")

    else:

        raw_tags = [str(tags)]

    cleaned_tags = []

    for tag in raw_tags:

        tag = str(tag).strip()

        # Remove accidental # from tags
        tag = tag.lstrip("#").strip()

        # Skip empty tags
        if not tag:
            continue

        # Remove duplicate tags
        if tag.lower() in [
            existing.lower()
            for existing in cleaned_tags
        ]:
            continue

        cleaned_tags.append(tag)

    # --------------------------------------------------------
    # YouTube allows tags up to 500 characters total.
    # Keep a safe margin.
    # --------------------------------------------------------

    final_tags = []

    total_length = 0

    for tag in cleaned_tags:

        additional_length = (
            len(tag)
            + (1 if final_tags else 0)
        )

        if (
            total_length
            + additional_length
            > 480
        ):
            break

        final_tags.append(tag)

        total_length += additional_length

    return final_tags


# ============================================================
# DESCRIPTION CLEANER
# ============================================================

def clean_description(description):
    """
    Cleans generated description without
    destroying Hindi text or hashtags.
    """

    if not description:
        return ""

    description = str(
        description
    ).strip()

    # Prevent excessive blank lines
    while "\n\n\n" in description:

        description = description.replace(
            "\n\n\n",
            "\n\n"
        )

    return description


# ============================================================
# TITLE CLEANER
# ============================================================

def clean_title(title):
    """
    Cleans YouTube title.
    """

    if not title:

        return "Hindi Motivation | जिंदगी बदलने वाली बातें"

    title = str(
        title
    ).strip()

    # YouTube title limit
    if len(title) > 100:

        title = title[:97] + "..."

    return title


# ============================================================
# THUMBNAIL VALIDATION
# ============================================================

def validate_thumbnail(thumbnail_path):
    """
    Checks whether thumbnail exists and is usable.
    """

    if not thumbnail_path:

        return False

    path = Path(
        thumbnail_path
    )

    if not path.exists():

        print(
            f"⚠️ Thumbnail not found: {path}"
        )

        return False

    if path.stat().st_size < 1024:

        print(
            f"⚠️ Thumbnail file is too small: {path}"
        )

        return False

    supported_extensions = {
        ".jpg",
        ".jpeg",
        ".png"
    }

    if path.suffix.lower() not in supported_extensions:

        print(
            "⚠️ Unsupported thumbnail format:"
            f" {path.suffix}"
        )

        return False

    return True


# ============================================================
# UPLOAD THUMBNAIL
# ============================================================

def upload_thumbnail(
    youtube,
    video_id,
    thumbnail_path
):
    """
    Uploads custom thumbnail to YouTube.
    """

    if not validate_thumbnail(
        thumbnail_path
    ):

        print(
            "⚠️ Thumbnail upload skipped."
        )

        return False

    try:

        print(
            f"🖼️ Uploading thumbnail:"
            f" {thumbnail_path}"
        )

        thumbnail_media = MediaFileUpload(
            str(thumbnail_path),
            mimetype="image/png",
            resumable=False
        )

        youtube.thumbnails().set(
            videoId=video_id,
            media_body=thumbnail_media
        ).execute()

        print(
            "✅ Custom thumbnail uploaded!"
        )

        return True

    except Exception as e:

        print(
            "❌ Thumbnail upload failed:"
            f" {e}"
        )

        return False


# ============================================================
# UPLOAD VIDEO
# ============================================================

def upload_to_youtube(
    video_path,
    title,
    description,
    tags,
    thumbnail_path=None
):
    """
    Uploads a video to YouTube.

    Supports:
    - Hindi titles
    - Hindi descriptions
    - SEO tags
    - custom thumbnail
    """

    print("=" * 60)

    print(
        "🚀 Starting YouTube upload..."
    )

    print(
        f"🎬 Video: {video_path}"
    )

    # --------------------------------------------------------
    # Validate video
    # --------------------------------------------------------

    video_path = Path(
        video_path
    )

    if not video_path.exists():

        raise FileNotFoundError(
            f"Video file not found: "
            f"{video_path}"
        )

    if video_path.stat().st_size < 1024:

        raise ValueError(
            "Video file appears to be empty."
        )

    # --------------------------------------------------------
    # Authenticate
    # --------------------------------------------------------

    youtube = get_authenticated_service()

    # --------------------------------------------------------
    # Clean metadata
    # --------------------------------------------------------

    title = clean_title(
        title
    )

    description = clean_description(
        description
    )

    clean_tags = normalize_tags(
        tags
    )

    print(
        f"📝 Title: {title}"
    )

    print(
        f"🏷️ Tags: {clean_tags}"
    )

    # --------------------------------------------------------
    # Request body
    # --------------------------------------------------------

    request_body = {

        "snippet": {

            "title": title,

            "description": description,

            "tags": clean_tags,

            # People & Blogs
            "categoryId": YOUTUBE_CATEGORY_ID
        },

        "status": {

            "privacyStatus":
                YOUTUBE_PRIVACY_STATUS,

            "selfDeclaredMadeForKids":
                False
        }
    }

    # --------------------------------------------------------
    # Media upload
    # --------------------------------------------------------

    print(
        "📤 Uploading video to YouTube..."
    )

    media = MediaFileUpload(
        str(video_path),
        chunksize=-1,
        resumable=True,
        mimetype="video/mp4"
    )

    request = youtube.videos().insert(

        part="snippet,status",

        body=request_body,

        media_body=media
    )

    response = None

    while response is None:

        status, response = (
            request.next_chunk()
        )

        if status:

            progress = int(
                status.progress() * 100
            )

            print(
                f"📤 Upload progress: "
                f"{progress}%"
            )

    # --------------------------------------------------------
    # Video ID
    # --------------------------------------------------------

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload completed but "
            "no video ID was returned."
        )

    print(
        "✅ Video uploaded successfully!"
    )

    print(
        f"🆔 Video ID: {video_id}"
    )

    print(
        f"🔗 https://www.youtube.com/watch?v={video_id}"
    )

    # --------------------------------------------------------
    # Thumbnail
    # --------------------------------------------------------

    if thumbnail_path:

        upload_thumbnail(
            youtube,
            video_id,
            thumbnail_path
        )

    else:

        print(
            "⚠️ No thumbnail path supplied."
        )

    print("=" * 60)

    return video_id
