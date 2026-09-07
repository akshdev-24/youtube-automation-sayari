# ============================================================
# FILE: src/shayari_generator.py
# ============================================================
#
# HINGLISH / ROMAN HINDI SHAYARI GENERATOR
#
# Features:
#   - Gemini API
#   - JSON structured output
#   - No function calling / AFC
#   - 503 / 429 / 5xx retry
#   - Automatic fallback Shayari
#   - No Devanagari
#   - Duplicate-content protection
#   - SEO title / description / hashtags / tags
#   - content_history.json support
#
# ============================================================

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types


# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

HISTORY_FILE = ROOT_DIR / "content_history.json"


# ============================================================
# CONFIG
# ============================================================

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)

API_KEY = os.getenv(
    "GOOGLE_API_KEY"
)

MAX_RETRIES = int(
    os.getenv(
        "GEMINI_RETRIES",
        "3"
    )
)

RETRY_BASE_DELAY = float(
    os.getenv(
        "GEMINI_RETRY_DELAY",
        "3"
    )
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(
    "shayari-generator"
)


# ============================================================
# CLIENT
# ============================================================

_client = None


def get_client():
    """
    Create Gemini client lazily.
    """

    global _client

    if _client is not None:
        return _client

    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY environment variable is missing."
        )

    _client = genai.Client(
        api_key=API_KEY
    )

    return _client


# ============================================================
# FALLBACK SHAYARI
# ============================================================
#
# These are ORIGINAL fallback lines.
# They are used when Gemini is temporarily unavailable.
#
# ============================================================

FALLBACK_SHAYARI = [

    {
        "shayari": (
            "Kabhi kabhi kisi ki yaad bhi "
            "kitni ajeeb hoti hai,\n"
            "paas na hokar bhi dil ke "
            "sabse kareeb hoti hai.\n\n"
            "Hum use bhoolne ki koshish to karte hain,\n"
            "magar har khamoshi mein "
            "uski kami mehsoos hoti hai."
        ),
        "category": "yaad",
        "style": "emotional",
        "emotion": "quiet longing",
        "title": (
            "Uski Yaad Ab Bhi Hai 💔 | "
            "Sad Shayari | Emotional Poetry"
        ),
    },

    {
        "shayari": (
            "Tumse milna ek khoobsurat khwab tha,\n"
            "tumhara bichhadna us khwab ka ant.\n\n"
            "Ab na shikayat hai, na koi sawaal,\n"
            "bas tumhari yaadon ka hai "
            "mere paas ek kona sambhal."
        ),
        "category": "judai",
        "style": "heartbreak",
        "emotion": "quiet heartbreak",
        "title": (
            "Tumse Bichhad Kar 💔 | "
            "Heart Touching Shayari"
        ),
    },

    {
        "shayari": (
            "Intezaar karte karte shaam dhal gayi,\n"
            "khamoshi se meri har baat badal gayi.\n\n"
            "Tum aaye nahi, phir bhi yakeen raha,\n"
            "shayad kisi mod par mulaqat hogi."
        ),
        "category": "intezaar",
        "style": "romantic",
        "emotion": "hopeful longing",
        "title": (
            "Intezaar Ab Bhi Hai 💔 | "
            "Love Shayari | Hindi Poetry"
        ),
    },

    {
        "shayari": (
            "Kuch rishte lafzon ke mohtaj nahi hote,\n"
            "bas khamoshi mein samajh aa jaate hain.\n\n"
            "Aur kuch log door hokar bhi,\n"
            "dil se kabhi door nahi jaate."
        ),
        "category": "rishte",
        "style": "deep",
        "emotion": "warm nostalgia",
        "title": (
            "Kuch Log Door Hokar Bhi 💔 | "
            "Deep Shayari"
        ),
    },

    {
        "shayari": (
            "Humne mohabbat mein kuch nahi maanga,\n"
            "bas tera saath maanga tha.\n\n"
            "Tumne woh bhi waqt ke hawale kar diya,\n"
            "aur humne use yaad bana kar rakh liya."
        ),
        "category": "mohabbat",
        "style": "sad romantic",
        "emotion": "lost love",
        "title": (
            "Bas Tera Saath Maanga Tha 💔 | "
            "Love Shayari"
        ),
    },

    {
        "shayari": (
            "Raat chup thi, chaand bhi tanha tha,\n"
            "aur dil mein tera hi fasana tha.\n\n"
            "Neend aankhon se door thi,\n"
            "shayad yaadon ko aaj phir "
            "tera bahaana tha."
        ),
        "category": "raat",
        "style": "romantic",
        "emotion": "nighttime longing",
        "title": (
            "Raat Aur Teri Yaad 💔 | "
            "Romantic Shayari"
        ),
    },

    {
        "shayari": (
            "Kuch baatein dil mein hi reh jaati hain,\n"
            "kuch mulaqatein adhuri reh jaati hain.\n\n"
            "Insaan chala jaata hai zindagi se,\n"
            "magar uski yaadein wahi reh jaati hain."
        ),
        "category": "yaadein",
        "style": "deep emotional",
        "emotion": "nostalgia",
        "title": (
            "Kuch Baatein Adhuri Reh Gayi 💔 | "
            "Deep Shayari"
        ),
    },

    {
        "shayari": (
            "Ajeeb sa rishta tha tumse,\n"
            "na paas reh sake, na door ja sake.\n\n"
            "Tumhe chhodna bhi mumkin nahi tha,\n"
            "aur tumhe paana bhi naseeb nahi tha."
        ),
        "category": "adhura_pyar",
        "style": "heartbreak",
        "emotion": "unfulfilled love",
        "title": (
            "Na Paas, Na Door 💔 | "
            "Broken Heart Shayari"
        ),
    },
]


# ============================================================
# CATEGORIES
# ============================================================

CATEGORIES = [
    "mohabbat",
    "ishq",
    "intezaar",
    "judai",
    "yaad",
    "tanhaai",
    "dard",
    "broken heart",
    "adhura pyar",
    "khamoshi",
    "rishte",
    "raat",
    "nostalgia",
]


# ============================================================
# SEO KEYWORDS
# ============================================================

SEO_TAGS = [
    "shayari",
    "hindi shayari",
    "sad shayari",
    "love shayari",
    "heart touching shayari",
    "emotional shayari",
    "dard bhari shayari",
    "deep shayari",
    "romantic shayari",
    "broken heart shayari",
    "urdu poetry",
    "poetry",
    "hindi poetry",
    "emotional poetry",
    "heart touching poetry",
    "sad poetry",
    "love poetry",
    "deep poetry",
    "shayari shorts",
    "shorts",
]


# ============================================================
# HELPERS
# ============================================================

def contains_devanagari(text: str) -> bool:
    """
    Return True if Devanagari is found.
    """

    if not text:
        return False

    return bool(
        re.search(
            r"[\u0900-\u097F]",
            text
        )
    )


def clean_text(text: Any) -> str:
    """
    Normalize text safely.
    """

    if text is None:
        return ""

    return str(text).strip()


def normalize_hashtags(
    hashtags: Any
) -> list[str]:
    """
    Normalize hashtags.
    """

    if isinstance(
        hashtags,
        str
    ):
        hashtags = re.split(
            r"[\s,]+",
            hashtags
        )

    if not isinstance(
        hashtags,
        list
    ):
        hashtags = []

    result = []

    for item in hashtags:

        item = clean_text(item)

        if not item:
            continue

        if not item.startswith("#"):
            item = "#" + item

        # Only simple hashtag characters.
        item = re.sub(
            r"[^#A-Za-z0-9_]",
            "",
            item
        )

        if item and item not in result:
            result.append(item)

    return result[:8]


def normalize_tags(
    tags: Any
) -> list[str]:
    """
    Normalize YouTube tags.
    """

    if isinstance(
        tags,
        str
    ):
        tags = tags.split(",")

    if not isinstance(
        tags,
        list
    ):
        tags = []

    result = []

    for item in tags:

        item = clean_text(item)

        if not item:
            continue

        if item not in result:
            result.append(item)

    # Add base SEO tags if missing.
    for tag in SEO_TAGS:

        if tag not in result:
            result.append(tag)

    return result[:30]


def normalize_content(
    data: dict
) -> dict:
    """
    Convert Gemini response into the exact structure
    expected by the rest of the application.
    """

    shayari = clean_text(
        data.get("shayari")
    )

    title = clean_text(
        data.get("title")
    )

    description = clean_text(
        data.get("description")
    )

    category = clean_text(
        data.get("category")
    ) or "deep feelings"

    style = clean_text(
        data.get("style")
    ) or "emotional"

    emotion = clean_text(
        data.get("emotion")
    ) or "deep emotions"

    hashtags = normalize_hashtags(
        data.get("hashtags")
    )

    tags = normalize_tags(
        data.get("tags")
    )

    # --------------------------------------------------------
    # Required fallback metadata
    # --------------------------------------------------------

    if not title:
        title = (
            "Heart Touching Shayari 💔 | "
            "Emotional Poetry | Shorts"
        )

    if not hashtags:
        hashtags = [
            "#Shayari",
            "#SadShayari",
            "#LoveShayari",
            "#EmotionalShayari",
            "#Shorts",
        ]

    if not description:
        description = (
            f"{title}\n\n"
            "Heart touching Roman Hindi Shayari "
            "and emotional poetry.\n\n"
            "A collection of feelings, love, "
            "yaadein and khamoshi."
        )

    return {
        "shayari": shayari,
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
        "category": category,
        "style": style,
        "emotion": emotion,
    }


# ============================================================
# HISTORY
# ============================================================

def load_history() -> list[dict]:
    """
    Load previous generated content.
    """

    if not HISTORY_FILE.exists():
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(
            data,
            list
        ):
            return data

        if isinstance(
            data,
            dict
        ):
            return data.get(
                "items",
                []
            )

    except Exception as exc:

        logger.warning(
            "Could not read history: %s",
            exc
        )

    return []


def save_history(item: dict) -> None:
    """
    Append generated item to content_history.json.
    """

    history = load_history()

    history.append(item)

    # Keep history manageable.
    history = history[-500:]

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2
        )


def is_duplicate(
    shayari: str,
    history: list[dict]
) -> bool:
    """
    Detect exact/near duplicate content.
    """

    normalized_new = re.sub(
        r"\s+",
        " ",
        shayari.lower()
    ).strip()

    if not normalized_new:
        return True

    for item in history:

        old = clean_text(
            item.get("shayari")
            or item.get("text")
        )

        normalized_old = re.sub(
            r"\s+",
            " ",
            old.lower()
        ).strip()

        if not normalized_old:
            continue

        if normalized_new == normalized_old:
            return True

    return False


# ============================================================
# GEMINI PROMPT
# ============================================================

def build_prompt(
    history: list[dict]
) -> str:
    """
    Build the generation prompt.

    We intentionally do NOT provide copyrighted text to copy.
    """

    recent_titles = []

    for item in history[-20:]:

        title = clean_text(
            item.get("title")
        )

        if title:
            recent_titles.append(
                title
            )

    blocked_titles = "\n".join(
        f"- {title}"
        for title in recent_titles
    )

    category = random.choice(
        CATEGORIES
    )

    return f"""
You are an expert Hindi/Urdu poetry writer.

Create ONE completely ORIGINAL Shayari for a YouTube Short.

IMPORTANT LANGUAGE RULES:
- Write ONLY in Roman Hindi / Hinglish.
- Do NOT use Devanagari.
- Do NOT write Urdu script.
- Do NOT transliterate famous existing poetry.
- Do NOT copy lines from any poet, book, website, song, movie or social-media post.
- Create fresh original wording.

STYLE:
- Emotional.
- Deep.
- Natural.
- Literary but easy to understand.
- Suitable for a 15-second vertical Shayari Short.
- Around 35 to 65 words.
- Use 5 to 8 poetic lines.
- Use blank lines between meaningful stanza blocks.
- No emojis inside the Shayari itself.

THEME:
{category}

The Shayari should feel like:
- mohabbat
- yaad
- intezaar
- khamoshi
- judai
- tanhaai
- emotional distance

Do not make it generic motivational content.

TITLE:
Create a short YouTube Shorts title.
Roman Hindi + relevant SEO phrase.
Do not make it excessively long.

DESCRIPTION:
Write a natural YouTube description.
Mention the emotional/poetry theme naturally.
Do NOT keyword-stuff.

HASHTAGS:
Give 5 to 7 relevant hashtags.

TAGS:
Give relevant YouTube search tags.
Focus on Shayari, Hindi poetry, emotional poetry,
love/sad poetry and Shorts.

Return ONLY valid JSON matching the requested schema.

RECENT TITLES TO AVOID:
{blocked_titles}
""".strip()


# ============================================================
# GEMINI REQUEST
# ============================================================

def request_gemini(
    prompt: str
) -> dict:
    """
    Request structured JSON from Gemini.

    Important:
    - No tools.
    - No Google Search.
    - No automatic function calling.
    - JSON schema enforced.
    """

    client = get_client()

    schema = {
        "type": "OBJECT",
        "properties": {
            "shayari": {
                "type": "STRING"
            },
            "title": {
                "type": "STRING"
            },
            "description": {
                "type": "STRING"
            },
            "hashtags": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                }
            },
            "tags": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                }
            },
            "category": {
                "type": "STRING"
            },
            "style": {
                "type": "STRING"
            },
            "emotion": {
                "type": "STRING"
            },
        },
        "required": [
            "shayari",
            "title",
            "description",
            "hashtags",
            "tags",
            "category",
            "style",
            "emotion",
        ],
    }

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=1.0,
            max_output_tokens=1200,
        ),
    )

    # --------------------------------------------------------
    # Safely extract response text
    # --------------------------------------------------------

    text = ""

    try:
        text = response.text or ""
    except Exception:
        text = ""

    text = text.strip()

    if not text:
        logger.warning(
            "Gemini returned an empty text response."
        )

        # Try candidate parts directly.
        try:

            for candidate in (
                response.candidates or []
            ):

                content = getattr(
                    candidate,
                    "content",
                    None
                )

                if not content:
                    continue

                for part in (
                    getattr(
                        content,
                        "parts",
                        []
                    )
                    or []
                ):

                    part_text = getattr(
                        part,
                        "text",
                        None
                    )

                    if part_text:
                        text = str(
                            part_text
                        ).strip()

                        break

                if text:
                    break

        except Exception as exc:

            logger.warning(
                "Could not extract candidate text: %s",
                exc
            )

    if not text:
        raise ValueError(
            "Gemini returned no usable text."
        )

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:

        data = json.loads(
            text
        )

    except json.JSONDecodeError:

        # Sometimes models may accidentally wrap JSON
        # in markdown despite schema instructions.

        cleaned = text

        cleaned = re.sub(
            r"^```json\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"^```\s*",
            "",
            cleaned
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned
        )

        try:

            data = json.loads(
                cleaned.strip()
            )

        except Exception as exc:

            raise ValueError(
                "Gemini returned invalid JSON."
            ) from exc

    if not isinstance(
        data,
        dict
    ):
        raise ValueError(
            "Gemini JSON response is not an object."
        )

    return data


# ============================================================
# FALLBACK
# ============================================================

def get_fallback(
    history: list[dict]
) -> dict:
    """
    Return a guaranteed-valid original Shayari.
    """

    available = [
        item
        for item in FALLBACK_SHAYARI
        if not is_duplicate(
            item["shayari"],
            history
        )
    ]

    if not available:

        # If all fallbacks were already used,
        # choose randomly rather than returning empty data.
        available = FALLBACK_SHAYARI

    selected = random.choice(
        available
    )

    data = {
        "shayari": selected["shayari"],
        "title": selected["title"],
        "description": (
            f"{selected['title']}\n\n"
            "Heart touching Roman Hindi Shayari "
            "for anyone who has ever loved, waited "
            "or silently missed someone.\n\n"
            "Original emotional poetry."
        ),
        "hashtags": [
            "#Shayari",
            "#SadShayari",
            "#LoveShayari",
            "#EmotionalShayari",
            "#HeartTouchingPoetry",
            "#Shorts",
        ],
        "tags": SEO_TAGS.copy(),
        "category": selected["category"],
        "style": selected["style"],
        "emotion": selected["emotion"],
    }

    return normalize_content(
        data
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_generated(
    content: dict
) -> None:
    """
    Make sure generated content is actually usable.
    """

    shayari = clean_text(
        content.get("shayari")
    )

    if not shayari:
        raise ValueError(
            "Generated Shayari is empty."
        )

    title = clean_text(
        content.get("title")
    )

    if not title:
        raise ValueError(
            "Generated title is empty."
        )

    # --------------------------------------------------------
    # No Devanagari
    # --------------------------------------------------------

    for field in [
        "shayari",
        "title",
        "description",
    ]:

        value = clean_text(
            content.get(field)
        )

        if contains_devanagari(
            value
        ):
            raise ValueError(
                f"Devanagari detected in {field}."
            )

    # --------------------------------------------------------
    # Minimum content quality
    # --------------------------------------------------------

    if len(shayari) < 25:
        raise ValueError(
            "Generated Shayari is too short."
        )

    if len(shayari) > 1200:
        raise ValueError(
            "Generated Shayari is too long."
        )


# ============================================================
# PUBLIC GENERATOR
# ============================================================

def generate_shayari() -> dict:
    """
    Main public function used by main.py.

    GUARANTEE:
    This function either returns valid content or raises
    a clear error. It will never return empty Shayari.
    """

    history = load_history()

    prompt = build_prompt(
        history
    )

    # --------------------------------------------------------
    # Gemini attempts
    # --------------------------------------------------------

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            logger.info(
                "Gemini generation attempt %d/%d",
                attempt,
                MAX_RETRIES,
            )

            raw = request_gemini(
                prompt
            )

            content = normalize_content(
                raw
            )

            validate_generated(
                content
            )

            # Prevent duplicate Gemini output.
            if is_duplicate(
                content["shayari"],
                history
            ):

                logger.warning(
                    "Gemini generated duplicate content."
                )

                if attempt < MAX_RETRIES:
                    continue

                raise ValueError(
                    "Duplicate Shayari generated."
                )

            logger.info(
                "Gemini Shayari generated successfully."
            )

            logger.info(
                "Category: %s",
                content["category"]
            )

            logger.info(
                "Title: %s",
                content["title"]
            )

            return content

        except Exception as exc:

            error_text = str(
                exc
            )

            print(
                f"⚠️ Shayari generation attempt "
                f"{attempt}/{MAX_RETRIES} failed: "
                f"{error_text}"
            )

            logger.warning(
                "Gemini attempt %d failed: %s",
                attempt,
                exc
            )

            if attempt < MAX_RETRIES:

                # Exponential backoff.
                delay = (
                    RETRY_BASE_DELAY
                    * (2 ** (attempt - 1))
                )

                # Small jitter.
                delay += random.uniform(
                    0.5,
                    1.5
                )

                logger.info(
                    "Waiting %.1f seconds before retry...",
                    delay
                )

                time.sleep(
                    delay
                )

    # --------------------------------------------------------
    # Gemini failed -> guaranteed fallback
    # --------------------------------------------------------

    logger.warning(
        "Gemini generation failed."
    )

    logger.warning(
        "Using fallback Shayari."
    )

    fallback = get_fallback(
        history
    )

    # Final safety validation.
    validate_generated(
        fallback
    )

    print()
    print("=" * 60)
    print("NEW SHAYARI GENERATED")
    print("=" * 60)

    print(
        fallback["shayari"]
    )

    print()

    print(
        f"Category: {fallback['category']}"
    )

    print(
        f"Style: {fallback['style']}"
    )

    print(
        f"Emotion: {fallback['emotion']}"
    )

    print()

    print(
        f"TITLE:\n{fallback['title']}"
    )

    print()

    print(
        "HASHTAGS:\n"
        + " ".join(
            fallback["hashtags"]
        )
    )

    print(
        "=" * 60
    )

    return fallback


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
    )

    result = generate_shayari()

    print()
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )
