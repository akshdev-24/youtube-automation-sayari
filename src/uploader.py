# ============================================================
# FILE: src/uploader.py
# HINGLISH SHAYARI - YOUTUBE SHORTS UPLOADER
# ============================================================
#
# Features:
#   ✅ YouTube OAuth2
#   ✅ GitHub Actions compatible
#   ✅ Automatic token refresh
#   ✅ Hinglish / Roman Hindi metadata
#   ✅ YouTube Shorts upload
#   ✅ SEO tag cleaning
#   ✅ 500-character tag protection
#   ✅ Upload retry
#   ✅ Upload progress
#   ✅ Optional custom thumbnail
#   ✅ No voice/TTS related code
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
# PATH CONFIG
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

CLIENT_SECRETS_FILE = ROOT_DIR / "client_secrets.json"

CREDENTIALS_FILE = ROOT_DIR / "credentials.json"


# ============================================================
# YOUTUBE CONFIG
# ============================================================

YOUTUBE_UPLOAD_SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload"
]

# 22 = People & Blogs
YOUTUBE_CATEGORY_ID = os.getenv(
    "YOUTUBE_CATEGORY_ID",
    "22"
)

# public / private / unlisted
YOUTUBE_PRIVACY_STATUS = os.getenv(
    "YOUTUBE_PRIVACY_STATUS",
    "public"
)

MAX_TITLE_LENGTH = 100

MAX_TAG_CHARACTERS = 480

UPLOAD_RETRIES = int(
    os.getenv(
        "YOUTUBE_UPLOAD_RETRIES",
        "3"
    )
)

RETRY_DELAY_SECONDS = int(
    os.getenv(
        "YOUTUBE_RETRY_DELAY",
        "10"
    )
)


# ============================================================
# AUTHENTICATION
# ============================================================

def get_authenticated_service():

    print()
    print("=" * 70)
    print("🔐 YOUTUBE AUTHENTICATION")
    print("=" * 70)

    credentials = None

    # --------------------------------------------------------
    # LOAD EXISTING CREDENTIALS
    # --------------------------------------------------------

    if CREDENTIALS_FILE.exists():

        print(
            f"🔑 Loading:"
            f" {CREDENTIALS_FILE}"
        )

        try:

            credentials = (
                Credentials.from_authorized_user_file(
                    str(CREDENTIALS_FILE),
                    YOUTUBE_UPLOAD_SCOPE
                )
            )

            print(
                "✅ Credentials loaded."
            )

        except Exception as error:

            print(
                "⚠️ Could not load credentials."
            )

            print(
                f"   {error}"
            )

            credentials = None

    else:

        print(
            "⚠️ credentials.json not found."
        )

    # --------------------------------------------------------
    # VALID
    # --------------------------------------------------------

    if credentials and credentials.valid:

        print(
            "✅ YouTube credentials are valid."
        )

    # --------------------------------------------------------
    # REFRESH
    # --------------------------------------------------------

    elif (
        credentials
        and credentials.expired
        and credentials.refresh_token
    ):

        print(
            "🔄 Access token expired."
        )

        print(
            "🔄 Refreshing token..."
        )

        try:

            credentials.refresh(
                Request()
            )

            print(
                "✅ Token refreshed."
            )

        except Exception as error:

            print(
                "❌ Token refresh failed."
            )

            raise RuntimeError(
                f"YouTube token refresh failed: {error}"
            )

    # --------------------------------------------------------
    # FIRST TIME LOCAL AUTH
    # --------------------------------------------------------

    else:

        print(
            "🔐 No valid credentials."
        )

        if not CLIENT_SECRETS_FILE.exists():

            raise FileNotFoundError(
                "\n❌ client_secrets.json not found.\n\n"
                "For GitHub Actions make sure your workflow "
                "creates client_secrets.json from your "
                "CLIENT_SECRET_B64 secret.\n"
            )

        print(
            "🌐 Starting browser OAuth..."
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
                "✅ OAuth completed."
            )

        except Exception as error:

            print(
                "❌ OAuth failed."
            )

            raise RuntimeError(
                f"YouTube OAuth failed: {error}"
            )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        CREDENTIALS_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8"
        )

        print(
            f"💾 Credentials saved:"
            f" {CREDENTIALS_FILE}"
        )

    except Exception as error:

        print(
            "⚠️ Could not save credentials."
        )

        print(
            f"   {error}"
        )

    # --------------------------------------------------------
    # BUILD API
    # --------------------------------------------------------

    try:

        youtube = build(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False
        )

        print(
            "✅ YouTube API ready."
        )

        return youtube

    except Exception as error:

        raise RuntimeError(
            f"Could not initialize YouTube API: {error}"
        )


# ============================================================
# TAG CLEANER
# ============================================================

def normalize_tags(tags):

    if not tags:

        return []

    # --------------------------------------------------------
    # INPUT LIST
    # --------------------------------------------------------

    if isinstance(
        tags,
        (list, tuple)
    ):

        raw_tags = list(tags)

    # --------------------------------------------------------
    # INPUT STRING
    # --------------------------------------------------------

    elif isinstance(
        tags,
        str
    ):

        raw_tags = tags.split(",")

    else:

        raw_tags = [
            str(tags)
        ]

    cleaned = []

    seen = set()

    total_length = 0

    for tag in raw_tags:

        tag = str(
            tag
        ).strip()

        # Remove # from YouTube tags
        tag = tag.lstrip(
            "#"
        )

        # Normalize spaces
        tag = " ".join(
            tag.split()
        )

        if not tag:

            continue

        # Maximum individual tag
        tag = tag[:100].strip()

        key = tag.lower()

        # Duplicate
        if key in seen:

            continue

        seen.add(
            key
        )

        extra_length = (
            len(tag)
            + (
                1
                if cleaned
                else 0
            )
        )

        # YouTube total tag limit
        if (
            total_length
            + extra_length
            > MAX_TAG_CHARACTERS
        ):

            break

        cleaned.append(
            tag
        )

        total_length += (
            extra_length
        )

    return cleaned


# ============================================================
# TITLE CLEANER
# ============================================================

def clean_title(title):

    if not title:

        title = (
            "Hinglish Shayari"
        )

    title = str(
        title
    ).strip()

    # Normalize whitespace
    title = " ".join(
        title.split()
    )

    # Keep #Shorts
    if "#shorts" not in title.lower():

        suffix = " #Shorts"

        max_length = (
            MAX_TITLE_LENGTH
            - len(suffix)
        )

        title = (
            title[
                :max_length
            ]
            .rstrip()
            + suffix
        )

    # Final protection
    if len(title) > MAX_TITLE_LENGTH:

        title = (
            title[
                :MAX_TITLE_LENGTH - 3
            ]
            .rstrip()
            + "..."
        )

    return title


# ============================================================
# DESCRIPTION CLEANER
# ============================================================

def clean_description(
    description
):

    if not description:

        description = ""

    description = str(
        description
    ).strip()

    # Normalize line endings
    description = description.replace(
        "\r\n",
        "\n"
    )

    description = description.replace(
        "\r",
        "\n"
    )

    # Remove excessive blank lines
    while "\n\n\n" in description:

        description = description.replace(
            "\n\n\n",
            "\n\n"
        )

    # Ensure Shorts hashtag
    if "#shorts" not in description.lower():

        if description:

            description += (
                "\n\n#Shorts"
            )

        else:

            description = "#Shorts"

    return description


# ============================================================
# VIDEO VALIDATION
# ============================================================

def validate_video(
    video_path
):

    path = Path(
        video_path
    )

    # --------------------------------------------------------
    # EXISTENCE
    # --------------------------------------------------------

    if not path.exists():

        raise FileNotFoundError(
            f"Video not found:\n{path}"
        )

    # --------------------------------------------------------
    # FILE
    # --------------------------------------------------------

    if not path.is_file():

        raise ValueError(
            f"Video path is not a file:\n{path}"
        )

    # --------------------------------------------------------
    # SIZE
    # --------------------------------------------------------

    size = path.stat().st_size

    if size < 1024:

        raise ValueError(
            "Video file is empty or invalid."
        )

    # --------------------------------------------------------
    # FORMAT
    # --------------------------------------------------------

    if path.suffix.lower() != ".mp4":

        print(
            "⚠️ Warning:"
            " video is not .mp4"
        )

    size_mb = (
        size
        / (
            1024 * 1024
        )
    )

    print(
        f"🎬 Video:"
        f" {path.name}"
    )

    print(
        f"📦 Size:"
        f" {size_mb:.2f} MB"
    )

    return True


# ============================================================
# THUMBNAIL VALIDATION
# ============================================================

def validate_thumbnail(
    thumbnail_path
):

    if not thumbnail_path:

        return False

    path = Path(
        thumbnail_path
    )

    if not path.exists():

        print(
            f"⚠️ Thumbnail not found:"
            f" {path}"
        )

        return False

    if not path.is_file():

        print(
            "⚠️ Thumbnail path is not a file."
        )

        return False

    supported = {
        ".jpg",
        ".jpeg",
        ".png"
    }

    if path.suffix.lower() not in supported:

        print(
            f"⚠️ Unsupported thumbnail:"
            f" {path.suffix}"
        )

        return False

    if path.stat().st_size < 1024:

        print(
            "⚠️ Thumbnail is too small."
        )

        return False

    size_mb = (
        path.stat().st_size
        / (
            1024 * 1024
        )
    )

    print(
        f"🖼️ Thumbnail:"
        f" {path.name}"
    )

    print(
        f"📦 Size:"
        f" {size_mb:.2f} MB"
    )

    if size_mb > 2:

        print(
            "⚠️ Thumbnail is larger than 2 MB."
        )

    return True


# ============================================================
# THUMBNAIL MIME
# ============================================================

def get_thumbnail_mime_type(
    thumbnail_path
):

    extension = (
        Path(thumbnail_path)
        .suffix
        .lower()
    )

    if extension in {
        ".jpg",
        ".jpeg"
    }:

        return "image/jpeg"

    if extension == ".png":

        return "image/png"

    return "application/octet-stream"


# ============================================================
# UPLOAD THUMBNAIL
# ============================================================

def upload_thumbnail(
    youtube,
    video_id,
    thumbnail_path
):

    print()
    print(
        "🖼️ UPLOADING THUMBNAIL"
    )

    if not validate_thumbnail(
        thumbnail_path
    ):

        return False

    path = Path(
        thumbnail_path
    )

    mime_type = (
        get_thumbnail_mime_type(
            path
        )
    )

    for attempt in range(
        1,
        UPLOAD_RETRIES + 1
    ):

        try:

            media = MediaFileUpload(

                str(path),

                mimetype=mime_type,

                resumable=False
            )

            youtube.thumbnails().set(

                videoId=video_id,

                media_body=media

            ).execute()

            print(
                "✅ Thumbnail uploaded."
            )

            return True

        except HttpError as error:

            print(
                f"❌ Thumbnail API error:"
                f" {error}"
            )

        except Exception as error:

            print(
                f"❌ Thumbnail error:"
                f" {error}"
            )

        if attempt < UPLOAD_RETRIES:

            print(
                f"🔄 Retry in "
                f"{RETRY_DELAY_SECONDS}s..."
            )

            time.sleep(
                RETRY_DELAY_SECONDS
            )

    print(
        "⚠️ Thumbnail upload failed."
    )

    return False


# ============================================================
# UPLOAD VIDEO
# ============================================================

def upload_video_file(
    youtube,
    video_path,
    title,
    description,
    tags
):

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

    print()
    print(
        "📦 Preparing YouTube upload..."
    )

    media = MediaFileUpload(

        str(video_path),

        mimetype="video/mp4",

        chunksize=1024 * 1024,

        resumable=True
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
                status.progress()
                * 100
            )

            print(
                f"📤 Upload:"
                f" {progress}%"
            )

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube returned no video ID."
        )

    return video_id


# ============================================================
# MAIN YOUTUBE UPLOAD
# ============================================================

def upload_to_youtube(
    video_path,
    title,
    description="",
    tags=None,
    thumbnail_path=None
):

    print()
    print("=" * 70)
    print("🚀 YOUTUBE SHORTS UPLOAD")
    print("=" * 70)

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    validate_video(
        video_path
    )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    title = clean_title(
        title
    )

    description = clean_description(
        description
    )

    tags = normalize_tags(
        tags
    )

    print()
    print(
        "📝 TITLE:"
    )

    print(
        title
    )

    print()
    print(
        "🏷️ TAGS:"
    )

    print(
        ", ".join(tags)
    )

    print()
    print(
        f"🏷️ Tag characters:"
        f" {sum(len(x) for x in tags) + max(len(tags)-1, 0)}"
    )

    # --------------------------------------------------------
    # AUTH
    # --------------------------------------------------------

    youtube = (
        get_authenticated_service()
    )

    video_id = None

    # --------------------------------------------------------
    # UPLOAD RETRY
    # --------------------------------------------------------

    for attempt in range(
        1,
        UPLOAD_RETRIES + 1
    ):

        try:

            print()
            print(
                f"📤 Attempt "
                f"{attempt}/{UPLOAD_RETRIES}"
            )

            video_id = upload_video_file(

                youtube=youtube,

                video_path=video_path,

                title=title,

                description=description,

                tags=tags
            )

            print(
                "✅ Video uploaded."
            )

            break

        except HttpError as error:

            print()
            print(
                "❌ YouTube API error:"
            )

            print(
                error
            )

            if attempt == UPLOAD_RETRIES:

                raise

        except Exception as error:

            print()
            print(
                "❌ Upload error:"
            )

            print(
                error
            )

            if attempt == UPLOAD_RETRIES:

                raise

        if attempt < UPLOAD_RETRIES:

            print(
                f"🔄 Waiting "
                f"{RETRY_DELAY_SECONDS}s..."
            )

            time.sleep(
                RETRY_DELAY_SECONDS
            )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    if not video_id:

        raise RuntimeError(
            "YouTube upload failed."
        )

    video_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    print()
    print("=" * 70)
    print("🎉 YOUTUBE UPLOAD SUCCESS")
    print("=" * 70)

    print(
        f"🆔 Video ID:"
        f" {video_id}"
    )

    print(
        f"🔗 {video_url}"
    )

    # --------------------------------------------------------
    # THUMBNAIL
    # --------------------------------------------------------

    if thumbnail_path:

        upload_thumbnail(

            youtube=youtube,

            video_id=video_id,

            thumbnail_path=thumbnail_path
        )

    return video_id


# ============================================================
# SHORTS UPLOAD HELPER
# ============================================================

def upload_short_to_youtube(
    video_path,
    title,
    description="",
    tags=None,
    thumbnail_path=None
):

    return upload_to_youtube(

        video_path=video_path,

        title=title,

        description=description,

        tags=tags,

        thumbnail_path=thumbnail_path
    )


# ============================================================
# SIMPLE BACKWARD-COMPATIBLE FUNCTION
# ============================================================

def upload_video(
    video_path,
    title,
    description="",
    tags=None,
    thumbnail_path=None
):

    return upload_short_to_youtube(

        video_path=video_path,

        title=title,

        description=description,

        tags=tags,

        thumbnail_path=thumbnail_path
    )


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "📺 Hinglish Shayari YouTube uploader"
    )

    print(
        "Use upload_short_to_youtube() "
        "from your main pipeline."
    )
