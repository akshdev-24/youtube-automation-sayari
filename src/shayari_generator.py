# ============================================================
# FILE: src/shayari_generator.py
# HINGLISH / ROMAN HINDI SHAYARI GENERATOR
# ============================================================
#
# Generates:
#   ✅ Original Roman/Hinglish Shayari
#   ✅ YouTube title
#   ✅ Description
#   ✅ Hashtags
#   ✅ SEO tags
#   ✅ Category
#
# Does NOT generate:
#   ❌ Devanagari Hindi
#   ❌ Voice script
#   ❌ TTS
#   ❌ Famous/copied Shayari
# ============================================================

import json
import os
import random
import re
from pathlib import Path

from google import genai
from google.genai import types


# ============================================================
# CONFIG
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

HISTORY_FILE = ROOT_DIR / "content_history.json"

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

MAX_HISTORY = 200


# ============================================================
# SHAYARI CATEGORIES
# ============================================================

CATEGORIES = [
    "sad love",
    "heartbreak",
    "one sided love",
    "deep feelings",
    "zindagi",
    "dosti",
    "attitude",
    "khamoshi",
    "yaadein",
    "alone",
    "missing someone",
    "unspoken love",
]


# ============================================================
# DEVANAGARI DETECTOR
# ============================================================

DEVANAGARI_PATTERN = re.compile(
    r"[\u0900-\u097F]"
)


def contains_devanagari(text: str) -> bool:
    """Return True if text contains Devanagari characters."""

    return bool(
        DEVANAGARI_PATTERN.search(
            text or ""
        )
    )


# ============================================================
# LOAD HISTORY
# ============================================================

def load_history():
    """Load previously generated content."""

    if not HISTORY_FILE.exists():
        return []

    try:

        data = json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, list):
            return []

        return data

    except Exception as exc:

        print(
            f"⚠️ Could not read history: {exc}"
        )

        return []


# ============================================================
# SAVE HISTORY
# ============================================================

def save_history(content: dict):
    """Save generated Shayari to history."""

    history = load_history()

    entry = {
        "shayari": content.get(
            "shayari",
            ""
        ).strip(),

        "title": content.get(
            "title",
            ""
        ).strip(),

        "category": content.get(
            "category",
            ""
        ).strip(),
    }

    history.append(entry)

    history = history[-MAX_HISTORY:]

    HISTORY_FILE.write_text(
        json.dumps(
            history,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text: str) -> str:
    """Normalize whitespace without changing Hinglish spelling."""

    text = str(text or "")

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # Remove excessive spaces.
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# CLEAN SHAYARI
# ============================================================

def clean_shayari(text: str) -> str:
    """Clean Gemini output while preserving line structure."""

    text = normalize_text(text)

    # Remove accidental markdown code fences.
    text = re.sub(
        r"^```(?:text|txt)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    # Remove common labels Gemini may add.
    text = re.sub(
        r"^(shayari|poem|text)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove leading numbering.
    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        line = re.sub(
            r"^\d+[\.\)\-:]\s*",
            "",
            line
        )

        # Remove bullets.
        line = re.sub(
            r"^[•●▪️\-]\s*",
            "",
            line
        )

        lines.append(line)

    return "\n".join(lines).strip()


# ============================================================
# CLEAN TITLE
# ============================================================

def clean_title(title: str) -> str:
    """Clean and limit YouTube title."""

    title = normalize_text(title)

    title = title.replace(
        "\n",
        " "
    )

    title = title.strip(
        "\"'` "
    )

    # Remove accidental title label.
    title = re.sub(
        r"^title\s*:\s*",
        "",
        title,
        flags=re.IGNORECASE
    )

    if len(title) > 100:
        title = title[:97].rstrip() + "..."

    return title


# ============================================================
# CLEAN HASHTAGS
# ============================================================

def clean_hashtags(hashtags):
    """Normalize hashtag list."""

    if not isinstance(
        hashtags,
        list
    ):
        return []

    cleaned = []

    for hashtag in hashtags:

        hashtag = str(
            hashtag
        ).strip()

        hashtag = hashtag.replace(
            " ",
            ""
        )

        if not hashtag:
            continue

        if not hashtag.startswith("#"):
            hashtag = "#" + hashtag

        # Hashtags should not contain Devanagari.
        if contains_devanagari(
            hashtag
        ):
            continue

        if hashtag.lower() not in [
            x.lower()
            for x in cleaned
        ]:
            cleaned.append(
                hashtag
            )

    # Always include Shorts.
    if not any(
        x.lower() == "#shorts"
        for x in cleaned
    ):
        cleaned.append(
            "#Shorts"
        )

    return cleaned[:15]


# ============================================================
# CLEAN TAGS
# ============================================================

def clean_tags(tags):
    """Normalize YouTube SEO tags."""

    if not isinstance(
        tags,
        list
    ):
        return []

    cleaned = []

    for tag in tags:

        tag = normalize_text(
            tag
        )

        tag = tag.replace(
            "\n",
            " "
        )

        tag = tag.strip(
            "\"'` "
        )

        if not tag:
            continue

        if contains_devanagari(
            tag
        ):
            continue

        if tag.lower() not in [
            x.lower()
            for x in cleaned
        ]:
            cleaned.append(
                tag
            )

    return cleaned[:30]


# ============================================================
# FALLBACK CONTENT
# ============================================================

def fallback_content(category: str):
    """
    Emergency fallback if Gemini fails.

    These are generic original lines and should only be used
    when AI generation is unavailable.
    """

    fallback_pool = [

        [
            "Kuch log paas hokar bhi apne nahi hote,",
            "Aur kuch door rehkar bhi dil ke kareeb hote hain.",
        ],

        [
            "Waqt badla to sabke chehre badal gaye,",
            "Hum wahi rahe, bas rishte sambhal gaye.",
        ],

        [
            "Khamoshi bhi bahut kuch keh jaati hai,",
            "Bas samajhne wala koi chahiye.",
        ],

        [
            "Yaadein kabhi purani nahi hoti,",
            "Bas unhe yaad karne ki aadat badal jaati hai.",
        ],

        [
            "Jise dil se chaha tha,",
            "Usi ne humein khamoshi sikha di.",
        ],

    ]

    lines = random.choice(
        fallback_pool
    )

    shayari = "\n".join(
        lines
    )

    return {
        "shayari": shayari,

        "title": "Kuch Baatein Dil Mein Reh Jaati Hain",

        "description": (
            "Kuch ehsaas lafzon mein kehna mushkil hota hai. "
            "Agar ye lines dil ko chhoo gayi ho to share zaroor karein.\n\n"
            "#Shorts #Shayari #HinglishShayari #LoveShayari"
        ),

        "hashtags": [
            "#Shorts",
            "#Shayari",
            "#HinglishShayari",
            "#LoveShayari",
            "#SadShayari",
        ],

        "tags": [
            "shayari",
            "hinglish shayari",
            "roman hindi shayari",
            "love shayari",
            "sad shayari",
            "heart touching shayari",
            "hindi shayari",
            "shayari shorts",
            "shorts",
        ],

        "category": category,
    }


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt(
    category: str,
    history: list
) -> str:

    recent_shayari = []

    for item in history[-30:]:

        if isinstance(
            item,
            dict
        ):

            text = item.get(
                "shayari",
                ""
            )

            if text:
                recent_shayari.append(
                    text
                )

    history_text = "\n---\n".join(
        recent_shayari
    )

    if not history_text:
        history_text = "No previous Shayari available."

    return f"""
You are an expert Indian short-form poetry writer.

Create ONE completely original Shayari for a YouTube Short.

CATEGORY:
{category}

IMPORTANT LANGUAGE RULE:
Write ONLY in Roman Hindi / Hinglish.

Use English alphabet only.

DO NOT use:
- Devanagari Hindi
- Urdu script
- Hindi Unicode characters
- Sanskrit script
- Transliteration mixed with Devanagari

Example of acceptable style:
"Uski yaadon ka silsila aaj bhi wahi hai,
Bas hum badal gaye, yaadein nahi."

The Shayari should feel natural for Indian social media.

STYLE:
- emotional
- simple
- relatable
- poetic
- cinematic
- easy to read
- modern
- human sounding
- suitable for a 15 second Short

LENGTH:
4 to 8 short lines.

IMPORTANT:
- Do not make every line extremely long.
- Avoid complicated vocabulary.
- Avoid excessive emojis.
- Do not put emojis inside the Shayari.
- Do not copy famous Shayari.
- Do not imitate a living poet.
- Do not mention that you are AI.
- Do not add explanations.
- Do not add quotation marks around the Shayari.

The following are previous Shayaris.
Do NOT repeat them or create something substantially similar:

{history_text}

Return ONLY valid JSON.

Required JSON structure:

{{
  "shayari": "4 to 8 lines separated by newline",
  "title": "short YouTube title",
  "description": "YouTube description",
  "hashtags": [
    "#Shorts",
    "#Shayari"
  ],
  "tags": [
    "shayari",
    "hinglish shayari"
  ],
  "category": "{category}"
}}

TITLE:
- Roman Hindi / Hinglish only
- Maximum 100 characters
- Emotional and clickable
- No misleading clickbait

DESCRIPTION:
- Roman Hindi / Hinglish only
- 2 to 4 short sentences
- Natural
- Include relevant hashtags

HASHTAGS:
Generate 5 to 12 relevant hashtags.

TAGS:
Generate 8 to 20 YouTube SEO tags.

Again:
ONLY Roman/Hinglish.
NO Devanagari.
ONLY JSON.
"""


# ============================================================
# VALIDATE RESPONSE
# ============================================================

def validate_response(data: dict):
    """Validate Gemini response."""

    if not isinstance(
        data,
        dict
    ):
        raise ValueError(
            "Gemini response is not a JSON object."
        )

    required = [
        "shayari",
        "title",
        "description",
        "hashtags",
        "tags",
        "category",
    ]

    for key in required:

        if key not in data:
            raise ValueError(
                f"Missing field: {key}"
            )

    shayari = clean_shayari(
        data["shayari"]
    )

    title = clean_title(
        data["title"]
    )

    description = normalize_text(
        data["description"]
    )

    # ---------------------------------------------
    # Roman/Hinglish check
    # ---------------------------------------------

    combined_text = (
        shayari
        + "\n"
        + title
        + "\n"
        + description
    )

    if contains_devanagari(
        combined_text
    ):
        raise ValueError(
            "Gemini returned Devanagari text."
        )

    # ---------------------------------------------
    # Minimum quality
    # ---------------------------------------------

    lines = [
        line.strip()
        for line in shayari.splitlines()
        if line.strip()
    ]

    if len(lines) < 2:
        raise ValueError(
            "Shayari has too few lines."
        )

    if len(shayari) < 30:
        raise ValueError(
            "Shayari is too short."
        )

    # ---------------------------------------------
    # Clean fields
    # ---------------------------------------------

    data["shayari"] = shayari
    data["title"] = title
    data["description"] = description

    data["hashtags"] = clean_hashtags(
        data["hashtags"]
    )

    data["tags"] = clean_tags(
        data["tags"]
    )

    data["category"] = normalize_text(
        data["category"]
    )

    # Ensure Shorts hashtag.
    if not any(
        x.lower() == "#shorts"
        for x in data["hashtags"]
    ):
        data["hashtags"].insert(
            0,
            "#Shorts"
        )

    return data


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
# GENERATE SHAYARI
# ============================================================

def generate_shayari():
    """
    Generate one original Hinglish Shayari.

    Automatically retries invalid AI output.
    """

    client = get_client()

    history = load_history()

    category = random.choice(
        CATEGORIES
    )

    prompt = build_prompt(
        category=category,
        history=history,
    )

    print(
        f"🎭 Category: {category}"
    )

    max_attempts = 3

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            print(
                f"🤖 Gemini generation "
                f"attempt {attempt}/{max_attempts}..."
            )

            response = client.models.generate_content(

                model=MODEL,

                contents=prompt,

                config=types.GenerateContentConfig(

                    temperature=1.0,

                    response_mime_type="application/json",

                    max_output_tokens=1500,
                ),
            )

            raw_text = (
                response.text
                if response
                else ""
            )

            if not raw_text:
                raise ValueError(
                    "Gemini returned empty response."
                )

            # -------------------------------------
            # Parse JSON
            # -------------------------------------

            raw_text = raw_text.strip()

            # Remove accidental code fences.
            raw_text = re.sub(
                r"^```json\s*",
                "",
                raw_text,
                flags=re.IGNORECASE
            )

            raw_text = re.sub(
                r"\s*```$",
                "",
                raw_text
            )

            data = json.loads(
                raw_text
            )

            # -------------------------------------
            # Validate
            # -------------------------------------

            data = validate_response(
                data
            )

            # -------------------------------------
            # Duplicate check
            # -------------------------------------

            normalized_new = re.sub(
                r"\s+",
                " ",
                data["shayari"].lower()
            ).strip()

            duplicate = False

            for item in history:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                old = re.sub(
                    r"\s+",
                    " ",
                    str(
                        item.get(
                            "shayari",
                            ""
                        )
                    ).lower()
                ).strip()

                if normalized_new == old:
                    duplicate = True
                    break

            if duplicate:

                print(
                    "⚠️ Duplicate Shayari detected."
                )

                # Add extra instruction for next attempt.
                prompt += """

IMPORTANT:
The previous generated result was a duplicate.
Create something completely different in imagery,
wording, emotion and sentence structure.
"""

                continue

            print(
                "✅ Original Hinglish Shayari generated."
            )

            return data

        except json.JSONDecodeError as exc:

            print(
                f"⚠️ Invalid JSON from Gemini: {exc}"
            )

        except Exception as exc:

            print(
                f"⚠️ Generation attempt failed: {exc}"
            )

        # Add stronger instruction before retry.
        prompt += """

RETRY INSTRUCTION:
Return ONLY valid JSON.
Use ONLY Roman/Hinglish English alphabet.
Do not use Devanagari.
Make the Shayari different from previous attempts.
"""

    # --------------------------------------------------------
    # Gemini completely failed
    # --------------------------------------------------------

    print(
        "⚠️ Gemini generation failed."
    )

    print(
        "🔄 Using emergency fallback Shayari."
    )

    return fallback_content(
        category
    )


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("💔 HINGLISH SHAYARI GENERATOR TEST")
    print("=" * 70)

    result = generate_shayari()

    print("\n📝 SHAYARI")
    print("-" * 70)
    print(result["shayari"])

    print("\n🎬 TITLE")
    print("-" * 70)
    print(result["title"])

    print("\n📄 DESCRIPTION")
    print("-" * 70)
    print(result["description"])

    print("\n🏷️ HASHTAGS")
    print("-" * 70)
    print(" ".join(result["hashtags"]))

    print("\n🔖 TAGS")
    print("-" * 70)
    print(", ".join(result["tags"]))

    print("\n📂 CATEGORY")
    print("-" * 70)
    print(result["category"])

    print("=" * 70)
