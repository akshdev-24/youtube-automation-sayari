# FILE: src/uploader.py
# ============================================================
# HINDI MOTIVATION YOUTUBE AUTOMATION UPLOADER
# ============================================================
#
# Features:
# - YouTube OAuth2 authentication
# - GitHub Actions compatible
# - Automatic token refresh
# - Hindi title support
# - Hindi description support
# - SEO tag cleaning
# - YouTube 500-character tag limit
# - Long video upload
# - YouTube Shorts upload
# - Custom thumbnail upload
# - PNG / JPG / JPEG MIME detection
# - Thumbnail validation
# - Upload progress
# - Robust error handling
#
# ============================================================

import os
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


# ============================================================
# CONFIGURATION
# ============================================================

CLIENT_SECRETS_FILE = Path("client_secrets.json")
CREDENTIALS_FILE = Path("credentials.json")

# ------------------------------------------------------------
# YouTube OAuth scope
# ------------------------------------------------------------

YOUTUBE_UPLOAD_SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload"
]

# ------------------------------------------------------------
# YouTube category
#
# 22 = People & Blogs
# Suitable for:
# - Motivation
# - Lifestyle
# - Personal development
# ------------------------------------------------------------

YOUTUBE_CATEGORY_ID = "22"

# ------------------------------------------------------------
# Upload privacy
#
# public / private / unlisted
# ------------------------------------------------------------

YOUTUBE_PRIVACY_STATUS = "public"

# ------------------------------------------------------------
# Retry configuration
# ------------------------------------------------------------

UPLOAD_RETRIES = 3
RETRY_DELAY_SECONDS = 10

# ------------------------------------------------------------
# YouTube title maximum
# ------------------------------------------------------------

MAX_TITLE_LENGTH = 100

# ------------------------------------------------------------
# YouTube tags maximum total characters
#
# YouTube allows approximately 500 characters.
# Keep a safe margin.
# ------------------------------------------------------------

MAX_TAG_CHARACTERS = 480


# ============================================================
# AUTHENTICATION
# ============================================================

def get_authenticated_service():
    """
    Authenticate with YouTube.

    GitHub Actions:
        Uses credentials.json restored from
        CREDENTIALS_B64 secret.

    Existing refresh token:
        Automatically refreshes expired credentials.

    First-time local authentication:
        Opens OAuth browser flow.
    """

    print("\n" + "=" * 60)
    print("🔐 YOUTUBE AUTHENTICATION")
    print("=" * 60)

    credentials = None

    # ========================================================
    # LOAD EXISTING CREDENTIALS
    # ========================================================

    if CREDENTIALS_FILE.exists():

        print(
            f"🔑 Found credentials file: "
            f"{CREDENTIALS_FILE}"
        )

        try:

            credentials = (
                Credentials.from_authorized_user_file(
                    str(CREDENTIALS_FILE),
                    YOUTUBE_UPLOAD_SCOPE
                )
            )

            print(
                "✅ Existing YouTube credentials loaded."
            )

        except Exception as e:

            print(
                "⚠️ Could not load existing credentials:"
            )

            print(
                f"   {e}"
            )

            credentials = None

    else:

        print(
            "⚠️ credentials.json not found."
        )

    # ========================================================
    # VALID CREDENTIALS
    # ========================================================

    if credentials and credentials.valid:

        print(
            "✅ YouTube credentials are valid."
        )

    # ========================================================
    # REFRESH EXPIRED CREDENTIALS
    # ========================================================

    elif (
        credentials
        and credentials.expired
        and credentials.refresh_token
    ):

        print(
            "🔄 YouTube access token expired."
        )

        print(
            "🔄 Refreshing access token..."
        )

        try:

            credentials.refresh(
                Request()
            )

            print(
                "✅ Access token refreshed successfully."
            )

        except Exception as e:

            print(
                "❌ Token refresh failed."
            )

            print(
                f"   Error: {e}"
            )

            raise RuntimeError(
                "YouTube authentication refresh failed."
            )

    # ========================================================
    # FIRST-TIME AUTHENTICATION
    # ========================================================

    else:

        print(
            "🔐 No valid YouTube credentials found."
        )

        print(
            "🌐 Starting OAuth authentication..."
        )

        if not CLIENT_SECRETS_FILE.exists():

            raise FileNotFoundError(
                "CRITICAL ERROR: "
                f"{CLIENT_SECRETS_FILE} not found.\n"
                "Make sure CLIENT_SECRET_B64 is configured "
                "correctly in GitHub Secrets."
            )

        try:

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

            print(
                "✅ OAuth authentication completed."
            )

        except Exception as e:

            print(
                "❌ OAuth authentication failed."
            )

            print(
                f"   Error: {e}"
            )

            raise

    # ========================================================
    # SAVE UPDATED CREDENTIALS
    # ========================================================

    try:

        with open(
            CREDENTIALS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                credentials.to_json()
            )

        print(
            f"💾 Credentials saved to:"
            f" {CREDENTIALS_FILE}"
        )

    except Exception as e:

        print(
            "⚠️ Could not save credentials:"
        )

        print(
            f"   {e}"
        )

    # ========================================================
    # BUILD YOUTUBE API SERVICE
    # ========================================================

    try:

        youtube = build(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False
        )

        print(
            "✅ YouTube API service initialized."
        )

    except Exception as e:

        print(
            "❌ Could not initialize YouTube API."
        )

        print(
            f"   Error: {e}"
        )

        raise

    return youtube


# ============================================================
# TAG NORMALIZER
# ============================================================

def normalize_tags(tags):
    """
    Normalize YouTube tags.

    Accepts:
        list
        tuple
        string

    Example:

        [
            "hindi motivation",
            "#motivation",
            "Hindi Motivation"
        ]

    Returns:
        Clean unique list.
    """

    if not tags:

        return []

    # --------------------------------------------------------
    # LIST / TUPLE
    # --------------------------------------------------------

    if isinstance(
        tags,
        (list, tuple)
    ):

        raw_tags = list(tags)

    # --------------------------------------------------------
    # STRING
    # --------------------------------------------------------

    elif isinstance(
        tags,
        str
    ):

        raw_tags = tags.split(",")

    # --------------------------------------------------------
    # OTHER
    # --------------------------------------------------------

    else:

        raw_tags = [
            str(tags)
        ]

    cleaned_tags = []

    seen = set()

    # ========================================================
    # CLEAN EACH TAG
    # ========================================================

    for tag in raw_tags:

        tag = str(
            tag
        ).strip()

        # Remove hashtag
        tag = tag.lstrip(
            "#"
        ).strip()

        # Remove unnecessary whitespace
        tag = " ".join(
            tag.split()
        )

        # Skip empty
        if not tag:

            continue

        # Prevent very long individual tags
        if len(tag) > 100:

            tag = tag[:100].strip()

        normalized_key = tag.lower()

        # Duplicate protection
        if normalized_key in seen:

            continue

        seen.add(
            normalized_key
        )

        cleaned_tags.append(
            tag
        )

    # ========================================================
    # YOUTUBE TOTAL TAG LIMIT
    # ========================================================

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
            > MAX_TAG_CHARACTERS
        ):

            break

        final_tags.append(
            tag
        )

        total_length += (
            additional_length
        )

    return final_tags


# ============================================================
# DESCRIPTION CLEANER
# ============================================================

def clean_description(description):
    """
    Clean YouTube description while
    preserving Hindi Unicode.
    """

    if not description:

        return ""

    description = str(
        description
    ).strip()

    # Normalize Windows line endings
    description = description.replace(
        "\r\n",
        "\n"
    )

    description = description.replace(
        "\r",
        "\n"
    )

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
    Clean YouTube title.
    """

    if not title:

        return (
            "Hindi Motivation | "
            "जिंदगी बदलने वाली बातें"
        )

    title = str(
        title
    ).strip()

    # Normalize whitespace
    title = " ".join(
        title.split()
    )

    # YouTube title limit
    if len(title) > MAX_TITLE_LENGTH:

        title = (
            title[
                :MAX_TITLE_LENGTH - 3
            ].rstrip()
            + "..."
        )

    return title


# ============================================================
# THUMBNAIL VALIDATION
# ============================================================

def validate_thumbnail(thumbnail_path):
    """
    Validate custom thumbnail.

    Supported:
        PNG
        JPG
        JPEG
    """

    if not thumbnail_path:

        return False

    path = Path(
        thumbnail_path
    )

    # --------------------------------------------------------
    # Exists?
    # --------------------------------------------------------

    if not path.exists():

        print(
            f"⚠️ Thumbnail not found:"
            f" {path}"
        )

        return False

    # --------------------------------------------------------
    # Is file?
    # --------------------------------------------------------

    if not path.is_file():

        print(
            f"⚠️ Thumbnail path is not a file:"
            f" {path}"
        )

        return False

    # --------------------------------------------------------
    # File size
    # --------------------------------------------------------

    file_size = path.stat().st_size

    if file_size < 1024:

        print(
            "⚠️ Thumbnail file is too small:"
            f" {file_size} bytes"
        )

        return False

    # --------------------------------------------------------
    # Extension
    # --------------------------------------------------------

    supported_extensions = {
        ".jpg",
        ".jpeg",
        ".png"
    }

    extension = (
        path.suffix.lower()
    )

    if extension not in supported_extensions:

        print(
            "⚠️ Unsupported thumbnail format:"
            f" {extension}"
        )

        return False

    # --------------------------------------------------------
    # Size warning
    # --------------------------------------------------------

    size_mb = (
        file_size
        / (1024 * 1024)
    )

    print(
        f"🖼️ Thumbnail:"
        f" {path.name}"
    )

    print(
        f"📦 Thumbnail size:"
        f" {size_mb:.2f} MB"
    )

    if size_mb > 2:

        print(
            "⚠️ WARNING:"
            " Thumbnail is larger than 2 MB."
        )

        print(
            "   YouTube may reject the thumbnail."
        )

    return True


# ============================================================
# THUMBNAIL MIME TYPE
# ============================================================

def get_thumbnail_mime_type(thumbnail_path):
    """
    Return correct MIME type based on extension.
    """

    extension = (
        Path(thumbnail_path)
        .suffix
        .lower()
    )

    mime_types = {

        ".jpg":
            "image/jpeg",

        ".jpeg":
            "image/jpeg",

        ".png":
            "image/png"
    }

    return mime_types.get(
        extension,
        "application/octet-stream"
    )


# ============================================================
# UPLOAD THUMBNAIL
# ============================================================

def upload_thumbnail(
    youtube,
    video_id,
    thumbnail_path
):
    """
    Upload custom thumbnail to YouTube.
    """

    print("\n" + "-" * 60)
    print("🖼️ CUSTOM THUMBNAIL UPLOAD")
    print("-" * 60)

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not validate_thumbnail(
        thumbnail_path
    ):

        print(
            "⚠️ Thumbnail upload skipped."
        )

        return False

    thumbnail_path = Path(
        thumbnail_path
    )

    # --------------------------------------------------------
    # MIME
    # --------------------------------------------------------

    mime_type = (
        get_thumbnail_mime_type(
            thumbnail_path
        )
    )

    print(
        f"📄 Format:"
        f" {thumbnail_path.suffix.lower()}"
    )

    print(
        f"📦 MIME:"
        f" {mime_type}"
    )

    # ========================================================
    # UPLOAD
    # ========================================================

    for attempt in range(
        1,
        UPLOAD_RETRIES + 1
    ):

        try:

            print(
                f"📤 Thumbnail upload attempt "
                f"{attempt}/{UPLOAD_RETRIES}"
            )

            thumbnail_media = (
                MediaFileUpload(
                    str(thumbnail_path),
                    mimetype=mime_type,
                    resumable=False
                )
            )

            youtube.thumbnails().set(
                videoId=video_id,
                media_body=thumbnail_media
            ).execute()

            print(
                "✅ Custom thumbnail uploaded!"
            )

            return True

        except HttpError as e:

            print(
                "❌ YouTube thumbnail API error:"
            )

            print(
                f"   {e}"
            )

            if attempt < UPLOAD_RETRIES:

                print(
                    f"🔄 Retrying in "
                    f"{RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )

        except Exception as e:

            print(
                "❌ Thumbnail upload failed:"
            )

            print(
                f"   {e}"
            )

            if attempt < UPLOAD_RETRIES:

                print(
                    f"🔄 Retrying in "
                    f"{RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )

    print(
        "❌ Thumbnail upload failed after "
        f"{UPLOAD_RETRIES} attempts."
    )

    return False


# ============================================================
# VIDEO VALIDATION
# ============================================================

def validate_video(video_path):
    """
    Validate video before upload.
    """

    path = Path(
        video_path
    )

    # --------------------------------------------------------
    # Exists
    # --------------------------------------------------------

    if not path.exists():

        raise FileNotFoundError(
            f"Video file not found:"
            f" {path}"
        )

    # --------------------------------------------------------
    # File
    # --------------------------------------------------------

    if not path.is_file():

        raise ValueError(
            f"Video path is not a file:"
            f" {path}"
        )

    # --------------------------------------------------------
    # Size
    # --------------------------------------------------------

    file_size = path.stat().st_size

    if file_size < 1024:

        raise ValueError(
            "Video file appears to be empty."
        )

    # --------------------------------------------------------
    # Extension
    # --------------------------------------------------------

    if path.suffix.lower() != ".mp4":

        print(
            "⚠️ Warning:"
            f" Video extension is {path.suffix}"
        )

    size_mb = (
        file_size
        / (1024 * 1024)
    )

    print(
        f"🎬 Video:"
        f" {path.name}"
    )

    print(
        f"📦 Video size:"
        f" {size_mb:.2f} MB"
    )

    return True


# ============================================================
# VIDEO UPLOAD
# ============================================================

def upload_video_file(
    youtube,
    video_path,
    title,
    description,
    tags
):
    """
    Upload video file to YouTube.

    Returns:
        video_id
    """

    video_path = Path(
        video_path
    )

    # ========================================================
    # REQUEST BODY
    # ========================================================

    request_body = {

        "snippet": {

            "title":
                title,

            "description":
                description,

            "tags":
                tags,

            "categoryId":
                YOUTUBE_CATEGORY_ID
        },

        "status": {

            "privacyStatus":
                YOUTUBE_PRIVACY_STATUS,

            "selfDeclaredMadeForKids":
                False
        }
    }

    # ========================================================
    # MEDIA
    # ========================================================

    print(
        "\n📦 Preparing video upload..."
    )

    media = MediaFileUpload(

        str(video_path),

        chunksize=-1,

        resumable=True,

        mimetype="video/mp4"
    )

    # ========================================================
    # API REQUEST
    # ========================================================

    request = youtube.videos().insert(

        part="snippet,status",

        body=request_body,

        media_body=media
    )

    response = None

    # ========================================================
    # UPLOAD LOOP
    # ========================================================

    while response is None:

        status, response = (
            request.next_chunk()
        )

        if status:

            progress = int(
                status.progress()
                * 100
            )

            print(
                f"📤 Upload progress:"
                f" {progress}%"
            )

    # ========================================================
    # VIDEO ID
    # ========================================================

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload completed but "
            "no video ID was returned."
        )

    return video_id


# ============================================================
# MAIN UPLOAD FUNCTION
# ============================================================

def upload_to_youtube(
    video_path,
    title,
    description,
    tags,
    thumbnail_path=None
):
    """
    Upload video to YouTube.

    Supports:
        - Hindi titles
        - Hindi descriptions
        - SEO tags
        - Custom thumbnails
        - GitHub Actions
        - OAuth token refresh

    Returns:
        YouTube video ID
    """

    print("\n" + "=" * 70)
    print("🚀 STARTING YOUTUBE UPLOAD")
    print("=" * 70)

    # ========================================================
    # VALIDATE VIDEO
    # ========================================================

    video_path = Path(
        video_path
    )

    validate_video(
        video_path
    )

    # ========================================================
    # CLEAN METADATA
    # ========================================================

    title = clean_title(
        title
    )

    description = clean_description(
        description
    )

    clean_tags = normalize_tags(
        tags
    )

    # ========================================================
    # LOG METADATA
    # ========================================================

    print("\n📝 YOUTUBE METADATA")
    print("-" * 60)

    print(
        f"TITLE:\n{title}"
    )

    print(
        f"\nTAGS:\n{clean_tags}"
    )

    print(
        f"\nTOTAL TAGS:"
        f" {len(clean_tags)}"
    )

    print(
        f"\nDESCRIPTION LENGTH:"
        f" {len(description)} characters"
    )

    if thumbnail_path:

        print(
            f"\nTHUMBNAIL:"
            f" {thumbnail_path}"
        )

    # ========================================================
    # AUTHENTICATE
    # ========================================================

    youtube = (
        get_authenticated_service()
    )

    # ========================================================
    # UPLOAD WITH RETRIES
    # ========================================================

    video_id = None

    for attempt in range(
        1,
        UPLOAD_RETRIES + 1
    ):

        try:

            print("\n" + "-" * 60)

            print(
                f"📤 VIDEO UPLOAD"
                f" — Attempt {attempt}/"
                f"{UPLOAD_RETRIES}"
            )

            print("-" * 60)

            video_id = upload_video_file(

                youtube=youtube,

                video_path=video_path,

                title=title,

                description=description,

                tags=clean_tags
            )

            break

        except HttpError as e:

            print(
                "\n❌ YouTube API upload error:"
            )

            print(
                f"{e}"
            )

            if attempt < UPLOAD_RETRIES:

                print(
                    f"\n🔄 Retrying in "
                    f"{RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )

            else:

                raise

        except Exception as e:

            print(
                "\n❌ Video upload failed:"
            )

            print(
                f"{e}"
            )

            if attempt < UPLOAD_RETRIES:

                print(
                    f"\n🔄 Retrying in "
                    f"{RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )

            else:

                raise

    # ========================================================
    # VERIFY VIDEO ID
    # ========================================================

    if not video_id:

        raise RuntimeError(
            "YouTube upload failed: "
            "No video ID returned."
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    print("\n" + "=" * 70)
    print("🎉 VIDEO UPLOAD SUCCESSFUL")
    print("=" * 70)

    print(
        f"🆔 Video ID:"
        f" {video_id}"
    )

    print(
        f"🔗 https://www.youtube.com/watch?v={video_id}"
    )

    # ========================================================
    # THUMBNAIL
    # ========================================================

    if thumbnail_path:

        print(
            "\n🖼️ Uploading custom thumbnail..."
        )

        thumbnail_success = (
            upload_thumbnail(
                youtube=youtube,
                video_id=video_id,
                thumbnail_path=thumbnail_path
            )
        )

        if thumbnail_success:

            print(
                "✅ Thumbnail successfully attached "
                "to video."
            )

        else:

            print(
                "⚠️ Video uploaded but thumbnail "
                "could not be attached."
            )

    else:

        print(
            "\n⚠️ No thumbnail path supplied."
        )

    print("\n" + "=" * 70)

    return video_id


# ============================================================
# OPTIONAL SHORTS HELPER
# ============================================================

def upload_short_to_youtube(
    video_path,
    title,
    description,
    tags,
    thumbnail_path=None
):
    """
    Dedicated helper for YouTube Shorts.

    The actual Shorts classification is primarily
    determined by the video's vertical format and
    Shorts-compatible metadata.

    Automatically ensures #Shorts is present
    in the title.
    """

    title = clean_title(
        title
    )

    # --------------------------------------------------------
    # Add #Shorts
    # --------------------------------------------------------

    if "#shorts" not in title.lower():

        # Make room for #Shorts
        suffix = " #Shorts"

        max_base_length = (
            MAX_TITLE_LENGTH
            - len(suffix)
        )

        title = (
            title[
                :max_base_length
            ].rstrip()
            + suffix
        )

    # --------------------------------------------------------
    # Add Shorts hashtag to description
    # --------------------------------------------------------

    description = clean_description(
        description
    )

    if "#shorts" not in description.lower():

        if description:

            description += (
                "\n\n#Shorts"
            )

        else:

            description = "#Shorts"

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    return upload_to_youtube(

        video_path=video_path,

        title=title,

        description=description,

        tags=tags,

        thumbnail_path=thumbnail_path
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "📺 YouTube uploader module loaded."
    )

    print(
        "This file is normally called "
        "from main.py."
    )
