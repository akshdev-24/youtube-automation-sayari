# ============================================================
# FILE: src/shayari_generator.py
# ============================================================
#
# HINGLISH / ROMAN HINDI SHAYARI GENERATOR
#
# Pipeline:
#
#   Gemini
#      ↓
#   Original Roman Hindi Shayari
#      ↓
#   SEO Engine
#      ↓
#   Title
#   Description
#   Search Queries
#   YouTube Tags
#   Hashtags
#
# Rules:
#   ✅ Roman Hindi / Hinglish only
#   ✅ No Devanagari
#   ✅ No Urdu script
#   ✅ No TTS
#   ✅ Original wording
#   ✅ Duplicate protection
#   ✅ SEO engine integration
#   ✅ Gemini model can be switched by main.py
#
# ============================================================

from __future__ import annotations

import json
import os
import random
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .seo_engine import (
    generate_seo,
    validate_seo_package,
)


# ============================================================
# CONFIG
# ============================================================

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)

API_KEY_ENV = "GOOGLE_API_KEY"

HISTORY_FILE = Path(
    os.getenv(
        "CONTENT_HISTORY_FILE",
        "content_history.json",
    )
)

MAX_GENERATION_RETRIES = int(
    os.getenv(
        "GENERATION_RETRIES",
        "2",
    )
)

RETRY_DELAY = float(
    os.getenv(
        "GENERATION_RETRY_DELAY",
        "2",
    )
)


# ============================================================
# FALLBACK ORIGINAL SHAYARI
# ============================================================
#
# These are original fallback lines created for this project.
# They are NOT copied from published books or modern poets.
#
# ============================================================

FALLBACK_SHAYARI = [
    {
        "title": "Jo Door Ho Gaya",
        "shayari": (
            "Jo paas tha,\n"
            "woh yaad ban gaya,\n"
            "\n"
            "jo apna tha,\n"
            "woh kisi aur ka ho gaya."
        ),
    },
    {
        "title": "Khamoshi Bhi Bolti Hai",
        "shayari": (
            "Kabhi lafz kam pad jaate hain,\n"
            "jab dil bahut kuch kehna chahta hai,\n"
            "\n"
            "khamoshi tabhi samajh aati hai,\n"
            "jab koi dil se sunta hai."
        ),
    },
    {
        "title": "Intezaar",
        "shayari": (
            "Intezaar uska nahi tha,\n"
            "bas ek umeed thi,\n"
            "\n"
            "shayad kabhi woh samjhega,\n"
            "ki mohabbat kitni gehri thi."
        ),
    },
    {
        "title": "Yaadon Ka Shehar",
        "shayari": (
            "Log chale jaate hain,\n"
            "yaadein nahi jaati,\n"
            "\n"
            "kuch kahaniyan khatam hokar bhi,\n"
            "dil se nahi jaati."
        ),
    },
    {
        "title": "Adhoori Mohabbat",
        "shayari": (
            "Mohabbat poori hoti,\n"
            "toh kahani chhoti hoti,\n"
            "\n"
            "jo adhoori reh gayi,\n"
            "shayad wahi sabse gehri thi."
        ),
    },
]


# ============================================================
# GEMINI CLIENT
# ============================================================

_client = None


def get_client():
    """
    Create Gemini client lazily.
    """

    global _client

    if _client is not None:
        return _client

    api_key = os.getenv(API_KEY_ENV)

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY environment variable is missing."
        )

    _client = genai.Client(
        api_key=api_key,
    )

    return _client


# ============================================================
# HISTORY
# ============================================================

def load_history() -> list[dict[str, Any]]:
    """
    Load previously generated content.
    """

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

        return []

    except Exception:
        return []


def save_history(
    content: dict[str, Any],
) -> None:
    """
    Save generated content to history.
    """

    history = load_history()

    history.append(
        {
            "title": content.get(
                "title",
                "",
            ),
            "shayari": content.get(
                "shayari",
                "",
            ),
            "model": content.get(
                "_gemini_model",
                MODEL,
            ),
            "source": content.get(
                "_source",
                "gemini",
            ),
            "timestamp": int(
                time.time()
            ),
        }
    )

    # Keep file reasonably small.
    history = history[-200:]

    HISTORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

def normalize_for_comparison(
    text: str,
) -> str:
    """
    Normalize text for duplicate detection.
    """

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    text = re.sub(
        r"[^a-z0-9 ]",
        "",
        text,
    )

    return text.strip()


# ============================================================
# ROMAN HINDI VALIDATION
# ============================================================

def contains_devanagari(
    text: str,
) -> bool:
    """
    Detect Devanagari characters.
    """

    return bool(
        re.search(
            r"[\u0900-\u097F]",
            text,
        )
    )


def contains_urdu_script(
    text: str,
) -> bool:
    """
    Detect common Arabic/Persian/Urdu script ranges.
    """

    return bool(
        re.search(
            r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]",
            text,
        )
    )


def is_roman_hindi(
    text: str,
) -> bool:
    """
    Ensure generated poetry is Roman Hindi/Hinglish.

    We allow:
        a-z
        numbers
        spaces
        common punctuation
        apostrophes
        hyphens
    """

    if not text:
        return False

    if contains_devanagari(text):
        return False

    if contains_urdu_script(text):
        return False

    # Reject unusual Unicode letters.
    if re.search(
        r"[^\x00-\x7F]",
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
# CLEAN SHAYARI
# ============================================================

def clean_shayari(
    text: str,
) -> str:
    """
    Clean Gemini's poetry output.
    """

    if not text:
        return ""

    text = str(text)

    # Remove Markdown code fences
    text = re.sub(
        r"```(?:text|txt)?",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.replace(
        "```",
        "",
    )

    # Remove accidental labels
    text = re.sub(
        r"^\s*(shayari|poem|poetry)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Normalize line endings
    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    # Remove excessive spaces
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

    # Remove excessive blank lines
    cleaned = []

    blank_count = 0

    for line in lines:

        if not line:

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
# GEMINI PROMPT
# ============================================================

def build_prompt(
    previous_shayari: list[str],
) -> str:
    """
    Build generation prompt.

    We explicitly ask for original wording instead of
    reproducing copyrighted modern poetry.
    """

    recent_examples = ""

    if previous_shayari:

        recent = previous_shayari[-15:]

        recent_examples = (
            "\n\nDO NOT repeat or closely imitate these "
            "recently generated texts:\n"
            + "\n---\n".join(recent)
        )

    return f"""
You are writing short original Hindi/Hinglish poetry
for a YouTube Shorts channel.

IMPORTANT LANGUAGE RULE:
Write ONLY in Roman Hindi / Hinglish using the Latin alphabet.

DO NOT use:
- Devanagari
- Urdu script
- Arabic script
- Hindi Unicode characters

CONTENT RULES:
- Create completely original wording.
- Do not reproduce lines from published books.
- Do not imitate a specific living poet.
- Do not quote copyrighted poetry.
- Public-domain themes may be used, but write fresh wording.
- The poetry should feel natural, emotional and human.
- Avoid generic AI-sounding phrases.
- Do not use emojis inside the poetry.
- Do not add hashtags inside the poetry.
- Do not add a title inside the poetry.

STYLE:
- Emotional
- Deep
- Simple
- Natural Roman Hindi
- Suitable for a 5–7 second YouTube Short
- Easy to read on screen
- Strong emotional ending

LENGTH:
Create 4–6 short poetry lines.

FORMAT:
Use line breaks naturally.
You may use one blank line between two emotional parts.

TITLE:
Create a short searchable title related to the poetry.
The title should be natural, not keyword stuffed.

Return ONLY valid JSON.

JSON format:
{{
  "title": "short title",
  "shayari": "line one\\nline two\\n\\nline three\\nline four"
}}

{recent_examples}
""".strip()


# ============================================================
# GEMINI JSON SCHEMA
# ============================================================

GENERATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {
            "type": "STRING",
        },
        "shayari": {
            "type": "STRING",
        },
    },
    "required": [
        "title",
        "shayari",
    ],
}


# ============================================================
# RESPONSE PARSER
# ============================================================

def parse_gemini_response(
    response,
) -> dict[str, str]:
    """
    Parse structured Gemini response safely.
    """

    raw = getattr(
        response,
        "text",
        None,
    )

    if not raw:
        raise ValueError(
            "Gemini returned empty response."
        )

    raw = raw.strip()

    # Remove accidental markdown fences.
    raw = re.sub(
        r"^```json\s*",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    raw = re.sub(
        r"\s*```$",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    try:

        data = json.loads(raw)

    except json.JSONDecodeError as exc:

        # Sometimes a model may return extra text.
        # Try extracting the first JSON object.
        match = re.search(
            r"\{.*\}",
            raw,
            flags=re.DOTALL,
        )

        if not match:
            raise ValueError(
                f"Gemini returned invalid JSON: {raw[:500]}"
            ) from exc

        try:

            data = json.loads(
                match.group(0)
            )

        except Exception as second_exc:

            raise ValueError(
                f"Gemini returned invalid JSON: {raw[:500]}"
            ) from second_exc

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Gemini JSON response is not an object."
        )

    title = str(
        data.get(
            "title",
            "",
        )
    ).strip()

    shayari = clean_shayari(
        str(
            data.get(
                "shayari",
                "",
            )
        )
    )

    if not title:
        raise ValueError(
            "Gemini returned empty title."
        )

    if not shayari:
        raise ValueError(
            "Gemini returned empty shayari."
        )

    return {
        "title": title,
        "shayari": shayari,
    }


# ============================================================
# DUPLICATE CHECK
# ============================================================

def is_duplicate(
    shayari: str,
    history: list[dict[str, Any]],
) -> bool:
    """
    Check whether poetry already exists in history.
    """

    current = normalize_for_comparison(
        shayari
    )

    if not current:
        return True

    for item in history:

        old = normalize_for_comparison(
            str(
                item.get(
                    "shayari",
                    "",
                )
            )
        )

        if not old:
            continue

        if current == old:
            return True

        # Also reject extremely similar short content.
        current_words = set(
            current.split()
        )

        old_words = set(
            old.split()
        )

        if not current_words or not old_words:
            continue

        intersection = (
            len(
                current_words
                & old_words
            )
        )

        union = (
            len(
                current_words
                | old_words
            )
        )

        similarity = (
            intersection / union
            if union
            else 0
        )

        if similarity >= 0.85:
            return True

    return False


# ============================================================
# FALLBACK
# ============================================================

def get_fallback(
    history: list[dict[str, Any]],
) -> dict[str, str]:
    """
    Select a non-duplicate local fallback.
    """

    shuffled = FALLBACK_SHAYARI.copy()

    random.shuffle(
        shuffled
    )

    for item in shuffled:

        if not is_duplicate(
            item["shayari"],
            history,
        ):
            return {
                "title": item["title"],
                "shayari": item["shayari"],
            }

    # If all fallbacks have been used,
    # return a randomized fresh combination.
    item = random.choice(
        FALLBACK_SHAYARI
    )

    return {
        "title": item["title"],
        "shayari": item["shayari"],
    }


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_with_gemini(
    history: list[dict[str, Any]],
) -> dict[str, str]:
    """
    Generate one original Shayari using Gemini.
    """

    client = get_client()

    previous = [
        str(
            item.get(
                "shayari",
                "",
            )
        )
        for item in history
        if item.get("shayari")
    ]

    prompt = build_prompt(
        previous
    )

    last_error = None

    for attempt in range(
        1,
        MAX_GENERATION_RETRIES + 1,
    ):

        try:

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.9,
                    response_mime_type="application/json",
                    response_schema=GENERATION_SCHEMA,
                ),
            )

            result = parse_gemini_response(
                response
            )

            title = result["title"]
            shayari = result["shayari"]

            if not is_roman_hindi(
                title + "\n" + shayari
            ):
                raise ValueError(
                    "Generated content contains non-Roman script."
                )

            if is_duplicate(
                shayari,
                history,
            ):
                raise ValueError(
                    "Generated Shayari is a duplicate."
                )

            return {
                "title": title,
                "shayari": shayari,
            }

        except Exception as exc:

            last_error = exc

            error_text = str(
                exc
            ).lower()

            # Do not waste retries on quota errors.
            if (
                "429" in error_text
                or "resource_exhausted" in error_text
                or "quota" in error_text
                or "rate limit" in error_text
            ):
                raise

            if attempt < MAX_GENERATION_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )

    raise RuntimeError(
        f"Gemini generation failed: {last_error}"
    )


# ============================================================
# SEO INTEGRATION
# ============================================================

def add_seo(
    content: dict[str, Any],
) -> dict[str, Any]:
    """
    Send generated Shayari into SEO engine.
    """

    seo = generate_seo(
        title=content["title"],
        shayari=content["shayari"],
    )

    valid, errors = validate_seo_package(
        seo
    )

    if not valid:

        raise ValueError(
            "SEO validation failed: "
            + "; ".join(errors)
        )

    content["title"] = seo["title"]

    content["description"] = seo[
        "description"
    ]

    content["queries"] = seo[
        "queries"
    ]

    content["tags"] = seo[
        "tags"
    ]

    content["hashtags"] = seo[
        "hashtags"
    ]

    content["seo"] = {
        "tag_character_count": seo[
            "tag_character_count"
        ],
        "seed_keywords": seo[
            "seo_seeds"
        ],
        "autocomplete_keywords": seo[
            "autocomplete_keywords"
        ],
    }

    return content


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def generate_shayari() -> dict[str, Any]:
    """
    Main public generator.

    Returns:

    {
        "title": "...",
        "shayari": "...",
        "description": "...",
        "queries": [...],
        "tags": [...],
        "hashtags": [...],
        "seo": {...},
        "_source": "gemini",
        "_gemini_model": "..."
    }
    """

    history = load_history()

    # --------------------------------------------------------
    # Try Gemini
    # --------------------------------------------------------

    try:

        content = generate_with_gemini(
            history
        )

        source = "gemini"

    except Exception as exc:

        print(
            f"[WARNING] Gemini generation failed: {exc}"
        )

        print(
            "[INFO] Using local original Shayari fallback."
        )

        content = get_fallback(
            history
        )

        source = "local_fallback"

    # --------------------------------------------------------
    # Roman Hindi safety check
    # --------------------------------------------------------

    combined = (
        content["title"]
        + "\n"
        + content["shayari"]
    )

    if not is_roman_hindi(
        combined
    ):

        print(
            "[WARNING] Non-Roman content detected."
        )

        content = get_fallback(
            history
        )

        source = "local_fallback"

    # --------------------------------------------------------
    # SEO
    # --------------------------------------------------------

    content = add_seo(
        content
    )

    # --------------------------------------------------------
    # Final safety checks
    # --------------------------------------------------------

    if not is_roman_hindi(
        content["shayari"]
    ):
        raise ValueError(
            "Final Shayari is not Roman Hindi."
        )

    if len(
        content["tags"]
    ) == 0:

        raise ValueError(
            "SEO engine generated no tags."
        )

    if (
        content.get(
            "seo",
            {}
        ).get(
            "tag_character_count",
            9999,
        )
        > 500
    ):

        raise ValueError(
            "YouTube tags exceed 500 characters."
        )

    content["_source"] = source

    content["_gemini_model"] = (
        MODEL
        if source == "gemini"
        else "local_fallback"
    )

    return content


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "\nGenerating Shayari..."
    )

    result = generate_shayari()

    print(
        "\n" + "=" * 60
    )

    print(
        "TITLE:"
    )

    print(
        result["title"]
    )

    print(
        "\nSHAYARI:"
    )

    print(
        result["shayari"]
    )

    print(
        "\nDESCRIPTION:"
    )

    print(
        result["description"]
    )

    print(
        "\nQUERIES:"
    )

    for query in result["queries"]:
        print(
            "-",
            query,
        )

    print(
        "\nTAGS:"
    )

    print(
        ", ".join(
            result["tags"]
        )
    )

    print(
        "\nTAG CHARACTERS:"
    )

    print(
        result["seo"][
            "tag_character_count"
        ]
    )

    print(
        "\nHASHTAGS:"
    )

    print(
        " ".join(
            result["hashtags"]
        )
    )

    print(
        "\nSOURCE:"
    )

    print(
        result["_source"]
    )

    print(
        "\nMODEL:"
    )

    print(
        result["_gemini_model"]
    )

    print(
        "=" * 60
    )
