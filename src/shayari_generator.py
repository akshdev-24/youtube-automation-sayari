# ============================================================
# FILE: src/shayari_generator.py
# ============================================================
#
# GEMINI SHAYARI + YOUTUBE SEO METADATA GENERATOR
#
# OUTPUT:
#   shayari
#   title
#   description
#   queries
#   hashtags
#   tags
#   keywords
#
# LANGUAGE:
#   Roman Hindi / Hinglish
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
# CONFIG
# ============================================================

ROOT_DIR = Path(
    __file__
).resolve().parent.parent

HISTORY_FILE = (
    ROOT_DIR
    / "content_history.json"
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)

MAX_RETRIES = 2

RETRY_BASE_DELAY = 2


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(
    __name__
)


# ============================================================
# FALLBACK SHAYARI
# ============================================================
#
# Original fallback material.
# No copyrighted poem reproduction.
#
# ============================================================

FALLBACK_SHAYARI = [

    {
        "shayari": (
            "Kabhi kabhi kisi ko paana "
            "mohabbat nahi hoti...\n\n"
            "Uske bina bhi use chahte rehna,\n"
            "shayad isi ko sachhi mohabbat kehte hain."
        ),
        "theme": "deep love",
    },

    {
        "shayari": (
            "Humne khamoshi ko bhi "
            "apni zubaan bana liya,\n\n"
            "jo samajh sake woh apna,\n"
            "jo na samjhe use jaane diya."
        ),
        "theme": "deep emotional",
    },

    {
        "shayari": (
            "Kuch rishte naam ke mohtaaj nahi hote,\n\n"
            "dil se jude log kabhi "
            "anjaan nahi hote."
        ),
        "theme": "relationship",
    },

    {
        "shayari": (
            "Waqt badla toh sab badal gaye,\n\n"
            "bas ek yaad thi\n"
            "jo aaj bhi wahi reh gayi."
        ),
        "theme": "sad",
    },

    {
        "shayari": (
            "Tum paas nahi ho,\n"
            "phir bhi sabse kareeb lagte ho,\n\n"
            "shayad mohabbat isi ehsaas ka naam hai."
        ),
        "theme": "romantic",
    },

    {
        "shayari": (
            "Jise dil se chaha tha,\n"
            "use bhoolna aasaan nahi tha,\n\n"
            "isliye humne yaadon se dosti kar li."
        ),
        "theme": "heartbreak",
    },

    {
        "shayari": (
            "Har muskurahat ke peeche\n"
            "ek kahani hoti hai,\n\n"
            "har khamoshi mein\n"
            "kuch baat purani hoti hai."
        ),
        "theme": "emotional",
    },

]


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_client():

    api_key = os.getenv(
        "GOOGLE_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "GOOGLE_API_KEY environment variable is missing."
        )

    return genai.Client(
        api_key=api_key
    )


# ============================================================
# HISTORY
# ============================================================

def load_history() -> list[dict[str, Any]]:

    if not HISTORY_FILE.exists():
        return []

    try:

        data = json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(data, list):
            return data

        if isinstance(data, dict):

            return data.get(
                "items",
                []
            )

    except Exception as exc:

        logger.warning(
            f"Could not load history: {exc}"
        )

    return []


def save_history(
    item: dict[str, Any],
) -> None:

    history = load_history()

    history.append(item)

    # Keep history manageable.
    history = history[-500:]

    HISTORY_FILE.write_text(
        json.dumps(
            history,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(
    text: str,
) -> str:

    text = str(
        text or ""
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def is_roman_hindi(
    text: str,
) -> bool:

    if not text:
        return False

    # Reject Devanagari.
    if re.search(
        r"[\u0900-\u097F]",
        text,
    ):
        return False

    # Reject Arabic/Urdu script.
    if re.search(
        r"[\u0600-\u06FF]",
        text,
    ):
        return False

    # Must contain alphabetic content.
    if not re.search(
        r"[A-Za-z]",
        text,
    ):
        return False

    return True


# ============================================================
# DUPLICATE CHECK
# ============================================================

def is_duplicate(
    shayari: str,
    history: list[dict[str, Any]],
) -> bool:

    current = normalize_text(
        shayari
    )

    if not current:
        return True

    for item in history:

        previous = normalize_text(
            item.get(
                "shayari",
                ""
            )
        )

        if not previous:
            continue

        if current == previous:
            return True

        # Prevent near duplicate content.
        current_words = set(
            current.split()
        )

        previous_words = set(
            previous.split()
        )

        if not current_words:
            continue

        overlap = (
            len(
                current_words
                & previous_words
            )
            / len(current_words)
        )

        if overlap >= 0.82:
            return True

    return False


# ============================================================
# REMOVE BAD HASHTAG FORMATTING
# ============================================================

def clean_hashtags(
    hashtags: Any,
) -> list[str]:

    if isinstance(
        hashtags,
        str,
    ):

        hashtags = re.split(
            r"[\s,]+",
            hashtags,
        )

    if not isinstance(
        hashtags,
        list,
    ):

        return []

    result = []

    for item in hashtags:

        item = str(
            item
        ).strip()

        if not item:
            continue

        if not item.startswith("#"):
            item = "#" + item

        # Remove spaces from hashtag
        item = item.replace(
            " ",
            "",
        )

        if item not in result:
            result.append(item)

    return result[:12]


# ============================================================
# CLEAN TAGS
# ============================================================

def clean_tags(
    tags: Any,
) -> list[str]:

    if isinstance(
        tags,
        str,
    ):

        tags = re.split(
            r"[,|\n]+",
            tags,
        )

    if not isinstance(
        tags,
        list,
    ):

        return []

    result = []

    for tag in tags:

        tag = str(
            tag
        ).strip()

        if not tag:
            continue

        if tag not in result:
            result.append(tag)

    # YouTube API has a total tag-character
    # limit. Keep a safe amount.
    final = []

    total_chars = 0

    for tag in result:

        if total_chars + len(tag) + 1 > 450:

            break

        final.append(tag)

        total_chars += (
            len(tag) + 1
        )

    return final


# ============================================================
# CLEAN QUERIES
# ============================================================

def clean_queries(
    queries: Any,
) -> list[str]:

    if isinstance(
        queries,
        str,
    ):

        queries = re.split(
            r"[,|\n]+",
            queries,
        )

    if not isinstance(
        queries,
        list,
    ):

        return []

    result = []

    for query in queries:

        query = str(
            query
        ).strip()

        if not query:
            continue

        query = re.sub(
            r"^[-•*]\s*",
            "",
            query,
        )

        if query not in result:
            result.append(query)

    return result[:15]


# ============================================================
# DESCRIPTION BUILDER
# ============================================================

def build_description(
    title: str,
    shayari: str,
    queries: list[str],
    hashtags: list[str],
) -> str:

    query_text = "\n".join(
        queries
    )

    hashtag_text = " ".join(
        hashtags
    )

    description = f"""{title}

{shayari}

Agar ye shayari dil ko chhoo gayi ho,
to video ko like karein aur aisi hi
heart touching shayari ke liye channel ko subscribe karein.

Your queries:
{query_text}

{hashtag_text}
"""

    # YouTube description max 5000 chars.
    return description[:4900].strip()


# ============================================================
# GEMINI PROMPT
# ============================================================

def build_prompt(
    history: list[dict[str, Any]],
) -> str:

    recent = []

    for item in history[-20:]:

        previous = item.get(
            "shayari",
            "",
        )

        if previous:
            recent.append(
                previous
            )

    previous_text = "\n---\n".join(
        recent
    )

    return f"""
You are a professional Hindi/Hinglish Shayari content
writer and YouTube Shorts SEO editor.

Create ONE ORIGINAL Shayari Short package.

IMPORTANT LANGUAGE RULE:
- Write ONLY Roman Hindi / Hinglish using Latin alphabet.
- NEVER use Devanagari.
- NEVER use Urdu/Arabic script.
- Do not translate into English.
- The Shayari should feel natural when read by a Hindi speaker.
- Keep the emotional depth of Hindi/Urdu poetry but write it
  completely in Roman script.

IMPORTANT COPYRIGHT RULE:
- Create original wording.
- Do not reproduce a modern poet's published poem.
- Do not copy text from books, websites or other YouTube channels.
- You may use broad poetic themes such as love, heartbreak,
  loneliness, memories, betrayal, silence and hope.

STYLE:
- Deep
- Emotional
- Elegant
- Simple
- Heart touching
- Suitable for a 15-second YouTube Short
- Approximately 4 to 10 short lines.
- Use stanza breaks with blank lines.
- Do not make every line extremely long.
- Avoid generic motivational clichés.

VIDEO TEXT:
The Shayari field will be displayed directly over a background
image/video.

Therefore:
- No title inside the Shayari.
- No hashtags inside the Shayari.
- No emojis inside the Shayari.
- No "Shayari:" label.
- No @handle.
- No author name.
- No explanation.

YOUTUBE TITLE:
Create a natural, clickable Hindi/Hinglish title.
It may contain one relevant emoji.
Do not keyword-stuff.
Do not claim "viral", "100% viral", "guaranteed views", etc.

YOUTUBE DESCRIPTION:
The system will construct the final description.
Provide:
- relevant search queries
- relevant hashtags
- relevant YouTube tags

SEO:
Focus on actual search intent around:
- Shayari
- Hindi Shayari
- Heart Touching Shayari
- Dard Bhari Shayari
- Sad Shayari
- Love Shayari
- Emotional Shayari
- Romantic Shayari
- Broken Heart Shayari
- Deep Shayari
- Shayari Shorts

Do NOT put all keywords everywhere.
Keep them relevant to the generated Shayari.

RETURN ONLY VALID JSON.

JSON structure:

{{
  "shayari": "Roman Hindi Shayari here",
  "title": "YouTube title here",
  "queries": [
    "search query 1",
    "search query 2"
  ],
  "hashtags": [
    "#Shayari",
    "#HeartTouchingShayari"
  ],
  "tags": [
    "Shayari",
    "Heart Touching Shayari"
  ]
}}

Do not add markdown.
Do not add ```json.
Do not add explanations.

Recent generated Shayari to avoid repeating:
---
{previous_text}
---
"""


# ============================================================
# GEMINI REQUEST
# ============================================================

def call_gemini(
    client,
    prompt: str,
):

    response = client.models.generate_content(

        model=MODEL,

        contents=prompt,

        config=types.GenerateContentConfig(

            temperature=0.9,

            response_mime_type="application/json",

            response_schema={
                "type": "OBJECT",
                "properties": {
                    "shayari": {
                        "type": "STRING"
                    },
                    "title": {
                        "type": "STRING"
                    },
                    "queries": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                    },
                    "hashtags": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                    },
                    "tags": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                    },
                },
                "required": [
                    "shayari",
                    "title",
                    "queries",
                    "hashtags",
                    "tags",
                ],
            },
        ),
    )

    raw = response.text

    if not raw:
        raise ValueError(
            "Gemini returned empty response."
        )

    raw = raw.strip()

    # Handle accidental markdown fences.
    raw = re.sub(
        r"^```(?:json)?",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    raw = re.sub(
        r"```$",
        "",
        raw,
    )

    raw = raw.strip()

    return json.loads(
        raw
    )


# ============================================================
# VALIDATE RESULT
# ============================================================

def validate_result(
    data: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Gemini result is not an object."
        )

    shayari = str(
        data.get(
            "shayari",
            "",
        )
    ).strip()

    title = str(
        data.get(
            "title",
            "",
        )
    ).strip()

    if not shayari:
        raise ValueError(
            "Generated Shayari is empty."
        )

    if not is_roman_hindi(
        shayari
    ):

        raise ValueError(
            "Generated Shayari is not Roman Hindi."
        )

    if is_duplicate(
        shayari,
        history,
    ):

        raise ValueError(
            "Generated Shayari is duplicate."
        )

    if len(shayari) > 900:

        raise ValueError(
            "Shayari is too long."
        )

    if not title:

        title = (
            "Heart Touching Shayari 💔"
        )

    queries = clean_queries(
        data.get(
            "queries",
            [],
        )
    )

    hashtags = clean_hashtags(
        data.get(
            "hashtags",
            [],
        )
    )

    tags = clean_tags(
        data.get(
            "tags",
            [],
        )
    )

    # Guaranteed baseline relevant queries.
    baseline_queries = [
        "shayari",
        "heart touching shayari",
        "dard bhari shayari",
        "sad shayari",
        "love shayari",
        "emotional shayari",
        "hindi shayari",
        "shayari shorts",
    ]

    for query in baseline_queries:

        if query not in queries:
            queries.append(query)

    queries = queries[:15]

    # Guaranteed baseline hashtags.
    baseline_hashtags = [
        "#Shayari",
        "#HeartTouchingShayari",
        "#HindiShayari",
        "#ShayariShorts",
    ]

    for hashtag in baseline_hashtags:

        if hashtag not in hashtags:
            hashtags.append(
                hashtag
            )

    hashtags = hashtags[:12]

    # Guaranteed relevant tags.
    baseline_tags = [
        "Shayari",
        "Hindi Shayari",
        "Heart Touching Shayari",
        "Dard Bhari Shayari",
        "Sad Shayari",
        "Love Shayari",
        "Emotional Shayari",
        "Shayari Shorts",
    ]

    for tag in baseline_tags:

        if tag not in tags:
            tags.append(tag)

    tags = clean_tags(
        tags
    )

    description = build_description(
        title,
        shayari,
        queries,
        hashtags,
    )

    return {
        "shayari": shayari,
        "title": title[:100],
        "description": description,
        "queries": queries,
        "hashtags": hashtags,
        "tags": tags,
    }


# ============================================================
# LOCAL FALLBACK
# ============================================================

def local_fallback(
    history: list[dict[str, Any]],
) -> dict[str, Any]:

    candidates = FALLBACK_SHAYARI.copy()

    random.shuffle(
        candidates
    )

    selected = None

    for candidate in candidates:

        if not is_duplicate(
            candidate["shayari"],
            history,
        ):

            selected = candidate
            break

    if selected is None:

        selected = random.choice(
            FALLBACK_SHAYARI
        )

    shayari = selected[
        "shayari"
    ]

    title_map = {
        "deep love":
            "Mohabbat Ka Ek Alag Ehsaas ❤️",
        "deep emotional":
            "Kuch Khamoshiyan Bahut Kuch Kehti Hain 💔",
        "relationship":
            "Kuch Rishte Dil Se Jude Hote Hain ❤️",
        "sad":
            "Kuch Yaadein Kabhi Purani Nahi Hoti 💔",
        "romantic":
            "Tum Sabse Kareeb Lagte Ho ❤️",
        "heartbreak":
            "Yaadon Se Dosti Kar Li 💔",
        "emotional":
            "Har Khamoshi Mein Ek Kahani Hoti Hai 💔",
    }

    title = title_map.get(
        selected["theme"],
        "Heart Touching Shayari 💔",
    )

    queries = [
        "shayari",
        "heart touching shayari",
        "dard bhari shayari",
        "sad shayari",
        "love shayari",
        "emotional shayari",
        "hindi shayari",
        "shayari shorts",
        "deep shayari",
    ]

    hashtags = [
        "#Shayari",
        "#HeartTouchingShayari",
        "#DardBhariShayari",
        "#SadShayari",
        "#LoveShayari",
        "#HindiShayari",
        "#EmotionalShayari",
        "#ShayariShorts",
        "#Shorts",
    ]

    tags = [
        "Shayari",
        "Heart Touching Shayari",
        "Dard Bhari Shayari",
        "Sad Shayari",
        "Love Shayari",
        "Emotional Shayari",
        "Hindi Shayari",
        "Shayari Shorts",
        "Deep Shayari",
        "Broken Heart Shayari",
    ]

    description = build_description(
        title,
        shayari,
        queries,
        hashtags,
    )

    return {
        "shayari": shayari,
        "title": title,
        "description": description,
        "queries": queries,
        "hashtags": hashtags,
        "tags": clean_tags(tags),
        "_source": "local_fallback",
    }


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_shayari() -> dict[str, Any]:

    history = load_history()

    client = get_client()

    prompt = build_prompt(
        history
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            logger.info(
                f"Generating Shayari with {MODEL} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

            data = call_gemini(
                client,
                prompt,
            )

            result = validate_result(
                data,
                history,
            )

            result[
                "_source"
            ] = "gemini"

            result[
                "_model"
            ] = MODEL

            logger.info(
                "Gemini Shayari generated successfully."
            )

            return result

        except Exception as exc:

            error_text = str(
                exc
            )

            logger.warning(
                f"Gemini generation failed: "
                f"{error_text}"
            )

            # Do not waste quota by retrying
            # quota/rate-limit errors.
            quota_error = (
                "429" in error_text
                or
                "RESOURCE_EXHAUSTED"
                in error_text
                or
                "quota"
                in error_text.lower()
                or
                "rate limit"
                in error_text.lower()
            )

            if quota_error:

                logger.warning(
                    "Gemini quota/rate limit detected. "
                    "Stopping retries."
                )

                break

            if attempt < MAX_RETRIES:

                delay = (
                    RETRY_BASE_DELAY
                    * (2 ** (attempt - 1))
                )

                delay += random.uniform(
                    0.5,
                    1.5,
                )

                logger.info(
                    f"Retrying in {delay:.1f}s..."
                )

                time.sleep(
                    delay
                )

    logger.warning(
        "Using local Shayari fallback."
    )

    return local_fallback(
        history
    )


# ============================================================
# SAVE HISTORY
# ============================================================

def record_generated_content(
    result: dict[str, Any],
) -> None:

    item = {
        "shayari": result.get(
            "shayari",
            "",
        ),
        "title": result.get(
            "title",
            "",
        ),
        "queries": result.get(
            "queries",
            [],
        ),
        "hashtags": result.get(
            "hashtags",
            [],
        ),
        "tags": result.get(
            "tags",
            [],
        ),
        "source": result.get(
            "_source",
            "",
        ),
        "model": result.get(
            "_model",
            "",
        ),
        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        ),
    }

    save_history(
        item
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    result = generate_shayari()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )
