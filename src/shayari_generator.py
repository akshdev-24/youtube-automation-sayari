# ============================================================
# FILE: src/shayari_generator.py
# ============================================================
#
# HINGLISH / ROMAN HINDI SHAYARI GENERATOR
#
# Features:
#   - Gemini generated original Shayari
#   - Roman Hindi / Hinglish only
#   - No Devanagari
#   - Literary-quality prompting
#   - Strong emotional hooks
#   - Natural poetry line breaks
#   - Poetry block spacing
#   - SEO title
#   - SEO description
#   - SEO hashtags
#   - YouTube tags
#   - Duplicate prevention
#   - Content history
#   - Fallback Shayari
#
# ============================================================

import os
import re
import json
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Any

from google import genai
from google.genai import types


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

HISTORY_FILE = BASE_DIR / "content_history.json"

API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

MAX_HISTORY = 200


# ============================================================
# CONTENT CATEGORIES
# ============================================================

CATEGORIES = [
    "sad love",
    "heartbreak",
    "one sided love",
    "bewafa",
    "judai",
    "yaadein",
    "khamoshi",
    "mohabbat",
    "intezaar",
    "dard",
    "tanhai",
    "zindagi",
    "attitude",
    "deep feelings",
    "missing someone",
    "unspoken love",
]


# ============================================================
# LITERARY REFERENCES
# ============================================================
#
# These are style/reference directions.
#
# We do NOT ask the model to reproduce copyrighted poems.
# Instead we ask for original writing with qualities such as:
#
#   - classical imagery
#   - emotional depth
#   - conversational pain
#   - philosophical undertone
#   - metaphor
#
# ============================================================

LITERARY_DIRECTIONS = {
    "ghazal_classical": [
        "classical Urdu ghazal atmosphere",
        "subtle metaphors",
        "ishq, hijr, intezaar and firaaq",
        "elegant and restrained language",
        "philosophical emotional depth",
    ],

    "modern_sad": [
        "modern melancholic poetry",
        "quiet emotional pain",
        "simple but memorable imagery",
        "loneliness and emotional distance",
        "short powerful statements",
    ],

    "life_philosophy": [
        "philosophical observation about life",
        "human contradictions",
        "simple words with deeper meaning",
        "realistic emotional insight",
        "thought-provoking ending",
    ],

    "romantic": [
        "soft romantic imagery",
        "intimate emotions",
        "subtle longing",
        "memory and presence",
        "emotion without excessive sweetness",
    ],

    "deep_heartbreak": [
        "quiet heartbreak",
        "unsaid feelings",
        "emotional distance",
        "loss without melodrama",
        "a strong final line",
    ],
}


# ============================================================
# FALLBACK SHAYARI
# ============================================================

FALLBACK_SHAYARI = [
    {
        "category": "heartbreak",
        "style": "deep_heartbreak",
        "lines": [
            "Tumse bichhad kar bhi",
            "tumse hi milta raha main,",
            "",
            "log kehte rahe waqt badal deta hai sabko,",
            "shayad unhone kisi ko",
            "dil se chaha hi nahi."
        ],
    },
    {
        "category": "one sided love",
        "style": "romantic",
        "lines": [
            "Uske paas rehne ki",
            "khwahish bhi ajeeb thi,",
            "",
            "woh mera kabhi tha hi nahi,",
            "phir bhi uske khone ka",
            "dard bahut tha."
        ],
    },
    {
        "category": "khamoshi",
        "style": "deep_heartbreak",
        "lines": [
            "Kuch baatein lafzon se",
            "kahan kahi jaati hain,",
            "",
            "aankhon mein ruk jaati hain,",
            "aur umr bhar",
            "khamosh rehti hain."
        ],
    },
    {
        "category": "yaadein",
        "style": "modern_sad",
        "lines": [
            "Yaadein bhi ajeeb hoti hain,",
            "jab chahein tab nahi aati,",
            "",
            "aur jab aa jaati hain,",
            "phir kisi aur cheez ko",
            "rehne nahi deti."
        ],
    },
    {
        "category": "zindagi",
        "style": "life_philosophy",
        "lines": [
            "Zindagi ne ek baat",
            "bahut der se samjhayi,",
            "",
            "jo waqt ke saath badal jaaye,",
            "use apna kehna",
            "zaroori nahi hota."
        ],
    },
]


# ============================================================
# BASIC HELPERS
# ============================================================

def contains_devanagari(text: str) -> bool:
    """
    Detect Hindi/Devanagari Unicode characters.
    """

    if not text:
        return False

    return bool(
        re.search(r"[\u0900-\u097F]", text)
    )


def clean_text(text: str) -> str:
    """
    Basic cleanup.
    """

    if not text:
        return ""

    text = str(text)

    # Remove markdown
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\*", "", text)
    text = re.sub(r"`", "", text)

    # Normalize excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_lines(lines: List[str]) -> List[str]:
    """
    Clean generated poetry lines while preserving
    intentional blank lines.
    """

    result = []

    for line in lines:

        if line is None:
            continue

        line = str(line).strip()

        if not line:
            result.append("")
            continue

        # Remove accidental bullets
        line = re.sub(
            r"^[\-\*\•\·]+\s*",
            "",
            line
        )

        result.append(line)

    # Remove leading/trailing blank lines
    while result and not result[0]:
        result.pop(0)

    while result and not result[-1]:
        result.pop()

    return result


def make_fingerprint(lines: List[str]) -> str:
    """
    Create duplicate fingerprint.
    """

    text = " ".join(
        line.strip().lower()
        for line in lines
        if line.strip()
    )

    text = re.sub(
        r"[^a-z0-9 ]+",
        "",
        text
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================
# HISTORY
# ============================================================

def load_history() -> List[Dict[str, Any]]:
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
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def save_history(item: Dict[str, Any]) -> None:
    """
    Save generated content to history.
    """

    history = load_history()

    history.append(item)

    history = history[-MAX_HISTORY:]

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


def is_duplicate(
    lines: List[str],
    history: List[Dict[str, Any]]
) -> bool:

    fingerprint = make_fingerprint(lines)

    for item in history:

        if item.get("fingerprint") == fingerprint:
            return True

    return False


# ============================================================
# STYLE SELECTION
# ============================================================

def choose_style(category: str) -> str:

    if category in [
        "heartbreak",
        "bewafa",
        "judai",
        "dard",
        "tanhai",
        "missing someone",
    ]:
        return random.choice([
            "deep_heartbreak",
            "modern_sad",
            "ghazal_classical",
        ])

    if category in [
        "mohabbat",
        "one sided love",
        "intezaar",
        "unspoken love",
    ]:
        return random.choice([
            "romantic",
            "ghazal_classical",
            "deep_heartbreak",
        ])

    if category == "zindagi":
        return "life_philosophy"

    if category == "khamoshi":
        return random.choice([
            "deep_heartbreak",
            "modern_sad",
            "ghazal_classical",
        ])

    return random.choice(
        list(LITERARY_DIRECTIONS.keys())
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_client():

    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY environment variable is missing."
        )

    return genai.Client(
        api_key=API_KEY
    )


# ============================================================
# PROMPT
# ============================================================

def build_prompt(
    category: str,
    style: str,
    history: List[Dict[str, Any]]
) -> str:

    direction = "\n".join(
        f"- {x}"
        for x in LITERARY_DIRECTIONS[style]
    )

    previous = []

    for item in history[-25:]:

        lines = item.get("lines", [])

        if lines:

            previous.append(
                " / ".join(
                    line
                    for line in lines
                    if line.strip()
                )
            )

    previous_text = "\n".join(
        f"- {x}"
        for x in previous
    )

    return f"""
You are an experienced Hindi-Urdu poetry writer creating
original short-form Shayari for a premium poetry Shorts channel.

TASK:
Create ONE original Shayari for the category:

{category}

LITERARY DIRECTION:
{direction}

IMPORTANT:

1. Write ONLY in Roman Hindi / Hinglish.
2. NEVER use Devanagari.
3. Do not translate English sentences into Hindi.
4. Natural Hindi/Urdu words written using Latin alphabet are preferred.
5. Use emotionally mature language.
6. Avoid generic AI motivational quotes.
7. Avoid childish rhymes.
8. Avoid overused social-media clichés.
9. Do not use excessive emojis.
10. Do not imitate a living poet's exact wording.
11. Do not reproduce any known/copyrighted poem.
12. Create completely ORIGINAL wording.
13. The result should feel like serious Hindi-Urdu poetry.
14. Prefer metaphor, emotional tension and understated pain.
15. The final line should leave an emotional aftertaste.
16. No explanation outside the requested JSON.

REFERENCE TRADITION:

The writing can draw inspiration from the broad literary
traditions associated with classical Urdu/Hindi poetry,
including themes found in works associated with:

- Mirza Ghalib
- Mir Taqi Mir
- Dushyant Kumar
- Gulzar
- Firaq Gorakhpuri
- Jaun Elia
- Parveen Shakir
- Khwaja Haider Ali Aatish
- Nida Fazli

But DO NOT copy their poems, ghazals or recognizable lines.

LENGTH:

4 to 8 poetic lines.

FORMAT:

Use intentional blank lines between emotional blocks.

Example formatting:

[
  "Pehli line,",
  "doosri line,",
  "",
  "teesri line,",
  "chauthi line.",
  "",
  "aakhri gehri line."
]

The blank strings are intentional visual spacing.

Do NOT put every sentence on one line.

Do NOT make every line extremely short.

The poetry should look beautiful when rendered as
large static typography on a vertical 9:16 video.

PREVIOUS CONTENT:

The following content has already been used.
Do NOT create anything substantially similar:

{previous_text}

Return ONLY valid JSON:

{{
  "category": "{category}",
  "style": "{style}",
  "lines": [
    "line 1",
    "line 2",
    "",
    "line 3",
    "line 4"
  ],
  "theme": "short theme description",
  "emotion": "primary emotion",
  "title_hook": "short emotional hook"
}}
"""


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_raw(
    category: str,
    style: str,
    history: List[Dict[str, Any]]
) -> Dict[str, Any]:

    client = get_client()

    prompt = build_prompt(
        category,
        style,
        history
    )

    response = client.models.generate_content(

        model=MODEL,

        contents=prompt,

        config=types.GenerateContentConfig(

            temperature=1.0,

            response_mime_type="application/json",

            max_output_tokens=1800,
        )
    )

    text = response.text

    if not text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    # Remove accidental markdown JSON fences
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError(
            "Gemini response is not a JSON object."
        )

    return data


# ============================================================
# VALIDATION
# ============================================================

def validate_shayari(
    data: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(data, dict):
        raise ValueError(
            "Invalid Shayari object."
        )

    lines = data.get("lines")

    if not isinstance(lines, list):
        raise ValueError(
            "Shayari lines are missing."
        )

    lines = normalize_lines(lines)

    non_empty = [
        line
        for line in lines
        if line.strip()
    ]

    if len(non_empty) < 4:
        raise ValueError(
            "Shayari must contain at least 4 lines."
        )

    if len(non_empty) > 8:
        raise ValueError(
            "Shayari must contain no more than 8 lines."
        )

    combined = "\n".join(lines)

    if contains_devanagari(combined):
        raise ValueError(
            "Devanagari detected. Roman Hindi required."
        )

    # Reject obvious markdown
    if "```" in combined:
        raise ValueError(
            "Markdown detected."
        )

    # Reject accidental list formatting
    for line in non_empty:

        if re.match(
            r"^\d+[\.\)]\s",
            line
        ):
            raise ValueError(
                "Numbered list detected."
            )

    # Avoid excessive emojis
    emoji_count = len(
        re.findall(
            r"[^\x00-\x7F]",
            combined
        )
    )

    if emoji_count > 3:
        raise ValueError(
            "Too many non-ASCII characters."
        )

    data["lines"] = lines

    data["category"] = clean_text(
        data.get(
            "category",
            "shayari"
        )
    )

    data["style"] = clean_text(
        data.get(
            "style",
            "modern_sad"
        )
    )

    data["theme"] = clean_text(
        data.get(
            "theme",
            ""
        )
    )

    data["emotion"] = clean_text(
        data.get(
            "emotion",
            ""
        )
    )

    data["title_hook"] = clean_text(
        data.get(
            "title_hook",
            ""
        )
    )

    return data


# ============================================================
# SEO KEYWORD POOL
# ============================================================

BASE_KEYWORDS = [
    "shayari",
    "hindi shayari",
    "hindishayari",
    "shayari status",
    "hindi poetry",
    "urdu poetry",
    "poetry",
]


CATEGORY_KEYWORDS = {

    "sad love": [
        "sad love shayari",
        "love shayari",
        "sad shayari",
        "heart touching shayari",
        "emotional shayari",
    ],

    "heartbreak": [
        "heartbreak shayari",
        "broken heart shayari",
        "dard bhari shayari",
        "sad shayari",
        "heart touching poetry",
    ],

    "one sided love": [
        "one sided love shayari",
        "one sided love",
        "sad love shayari",
        "mohabbat shayari",
        "heart touching shayari",
    ],

    "bewafa": [
        "bewafa shayari",
        "bewafai shayari",
        "dard bhari shayari",
        "sad love shayari",
        "heartbreak shayari",
    ],

    "judai": [
        "judai shayari",
        "dard e judai",
        "sad shayari",
        "dard bhari shayari",
        "heart touching poetry",
    ],

    "yaadein": [
        "yaadein shayari",
        "yaadon ki shayari",
        "sad shayari",
        "emotional poetry",
        "heart touching shayari",
    ],

    "khamoshi": [
        "khamoshi shayari",
        "silent love shayari",
        "deep shayari",
        "emotional shayari",
        "heart touching poetry",
    ],

    "mohabbat": [
        "mohabbat shayari",
        "love shayari",
        "romantic shayari",
        "ishq shayari",
        "heart touching shayari",
    ],

    "intezaar": [
        "intezaar shayari",
        "waiting for someone shayari",
        "mohabbat shayari",
        "sad love shayari",
        "heart touching poetry",
    ],

    "dard": [
        "dard shayari",
        "dard bhari shayari",
        "sad shayari",
        "emotional shayari",
        "heart touching poetry",
    ],

    "tanhai": [
        "tanhai shayari",
        "alone shayari",
        "sad shayari",
        "lonely poetry",
        "dard bhari shayari",
    ],

    "zindagi": [
        "zindagi shayari",
        "life shayari",
        "zindagi quotes",
        "deep shayari",
        "hindi poetry",
    ],

    "attitude": [
        "attitude shayari",
        "attitude status",
        "royal attitude shayari",
        "hindi attitude shayari",
        "shayari status",
    ],

    "deep feelings": [
        "deep shayari",
        "deep feelings shayari",
        "emotional shayari",
        "heart touching poetry",
        "hindi poetry",
    ],

    "missing someone": [
        "miss you shayari",
        "missing someone shayari",
        "sad love shayari",
        "yaadein shayari",
        "heart touching shayari",
    ],

    "unspoken love": [
        "unspoken love shayari",
        "silent love shayari",
        "one sided love",
        "mohabbat shayari",
        "heart touching poetry",
    ],
}


# ============================================================
# SEO GENERATOR
# ============================================================

def build_seo(
    data: Dict[str, Any]
) -> Dict[str, Any]:

    category = data.get(
        "category",
        "sad love"
    ).lower()

    hook = data.get(
        "title_hook",
        ""
    ).strip()

    if not hook:

        first_lines = [
            line
            for line in data["lines"]
            if line.strip()
        ]

        hook = (
            first_lines[0]
            if first_lines
            else "Dil Ki Baat"
        )

    # Keep title reasonably short.
    hook = hook[:65].strip()

    keyword_pool = list(
        dict.fromkeys(
            BASE_KEYWORDS
            + CATEGORY_KEYWORDS.get(
                category,
                []
            )
        )
    )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title_templates = [

        "{hook} 💔 | Dard Bhari Shayari | Heart Touching Poetry",

        "{hook} 💔 | {category_title} | Hindi Shayari",

        "{hook} | Heart Touching Shayari 💔 | Hindi Poetry",

        "{hook} 💔 | Sad Shayari | Emotional Poetry",

    ]

    category_title = category.title()

    template = random.choice(
        title_templates
    )

    title = template.format(
        hook=hook,
        category_title=category_title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    ).strip()

    # YouTube title length safety
    title = title[:100].rstrip()

    # --------------------------------------------------------
    # HASHTAGS
    # --------------------------------------------------------

    hashtag_map = {

        "sad love": [
            "#Shayari",
            "#SadShayari",
            "#LoveShayari",
            "#HeartTouchingShayari",
            "#Shorts",
        ],

        "heartbreak": [
            "#Shayari",
            "#DardBhariShayari",
            "#Heartbreak",
            "#SadShayari",
            "#Shorts",
        ],

        "one sided love": [
            "#Shayari",
            "#OneSidedLove",
            "#LoveShayari",
            "#SadShayari",
            "#Shorts",
        ],

        "bewafa": [
            "#Shayari",
            "#BewafaShayari",
            "#SadShayari",
            "#DardBhariShayari",
            "#Shorts",
        ],

        "judai": [
            "#Shayari",
            "#JudaiShayari",
            "#SadShayari",
            "#HeartTouchingShayari",
            "#Shorts",
        ],

        "yaadein": [
            "#Shayari",
            "#Yaadein",
            "#SadShayari",
            "#EmotionalShayari",
            "#Shorts",
        ],

        "khamoshi": [
            "#Shayari",
            "#Khamoshi",
            "#DeepShayari",
            "#HeartTouchingPoetry",
            "#Shorts",
        ],

        "mohabbat": [
            "#Shayari",
            "#Mohabbat",
            "#LoveShayari",
            "#Ishq",
            "#Shorts",
        ],

        "intezaar": [
            "#Shayari",
            "#Intezaar",
            "#LoveShayari",
            "#SadShayari",
            "#Shorts",
        ],

        "dard": [
            "#Shayari",
            "#DardBhariShayari",
            "#SadShayari",
            "#EmotionalShayari",
            "#Shorts",
        ],

        "tanhai": [
            "#Shayari",
            "#Tanhai",
            "#AloneShayari",
            "#SadShayari",
            "#Shorts",
        ],

        "zindagi": [
            "#Shayari",
            "#ZindagiShayari",
            "#LifeShayari",
            "#HindiPoetry",
            "#Shorts",
        ],

        "attitude": [
            "#Shayari",
            "#AttitudeShayari",
            "#AttitudeStatus",
            "#HindiShayari",
            "#Shorts",
        ],

        "deep feelings": [
            "#Shayari",
            "#DeepShayari",
            "#EmotionalShayari",
            "#HeartTouchingPoetry",
            "#Shorts",
        ],

        "missing someone": [
            "#Shayari",
            "#MissYou",
            "#SadShayari",
            "#LoveShayari",
            "#Shorts",
        ],

        "unspoken love": [
            "#Shayari",
            "#UnspokenLove",
            "#OneSidedLove",
            "#LoveShayari",
            "#Shorts",
        ],
    }

    hashtags = hashtag_map.get(
        category,
        [
            "#Shayari",
            "#HindiShayari",
            "#Poetry",
            "#HeartTouching",
            "#Shorts",
        ]
    )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    poetry_preview = "\n".join(
        line
        for line in data["lines"]
        if line.strip()
    )

    description = f"""
{poetry_preview}

A collection of heartfelt Hindi-Urdu poetry written in Roman Hindi,
for those who understand the silence behind words.

Agar aapko Shayari, Hindi Shayari, Sad Shayari, Love Shayari,
Dard Bhari Shayari, Heart Touching Poetry, Emotional Shayari,
Urdu Poetry aur deep feelings wali poetry pasand hai,
toh ye Shayari aapke liye hai.

Kabhi mohabbat lafzon mein nahi hoti,
kabhi dard awaaz nahi karta,
aur kabhi khamoshi sab kuch keh jaati hai.

Apne ehsaas comments mein zaroor likhna.

Follow / Subscribe for more:
• Hindi Shayari
• Sad Shayari
• Love Shayari
• Heart Touching Poetry
• Dard Bhari Shayari
• Emotional Poetry
• Urdu Poetry

{ " ".join(hashtags) }
""".strip()

    # --------------------------------------------------------
    # TAGS
    # --------------------------------------------------------

    tags = list(
        dict.fromkeys(
            keyword_pool
            + [
                "heart touching",
                "heart touching poetry",
                "emotional poetry",
                "dard bhari poetry",
                "best shayari",
                "shayari video",
                "shayari shorts",
                "youtube shorts",
                "shorts",
                "viral shayari",
                "trending shayari",
                "roman hindi shayari",
                "hinglish shayari",
                "urdu shayari",
            ]
        )
    )

    # YouTube tag field safety
    clean_tags = []

    for tag in tags:

        tag = tag.strip()

        if tag and tag not in clean_tags:
            clean_tags.append(tag)

    # --------------------------------------------------------
    # RETURN SEO
    # --------------------------------------------------------

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": clean_tags,
    }


# ============================================================
# FALLBACK
# ============================================================

def get_fallback() -> Dict[str, Any]:

    item = random.choice(
        FALLBACK_SHAYARI
    )

    data = {
        "category": item["category"],
        "style": item["style"],
        "lines": item["lines"],
        "theme": item["category"],
        "emotion": "deep emotion",
        "title_hook": (
            item["lines"][0]
            if item["lines"]
            else "Dil Ki Baat"
        ),
    }

    data = validate_shayari(
        data
    )

    seo = build_seo(
        data
    )

    data["seo"] = seo

    return data


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_shayari() -> Dict[str, Any]:

    history = load_history()

    category = random.choice(
        CATEGORIES
    )

    style = choose_style(
        category
    )

    # --------------------------------------------------------
    # Try Gemini multiple times
    # --------------------------------------------------------

    for attempt in range(3):

        try:

            data = generate_raw(
                category=category,
                style=style,
                history=history
            )

            data = validate_shayari(
                data
            )

            if is_duplicate(
                data["lines"],
                history
            ):
                print(
                    "⚠️ Duplicate Shayari detected. Retrying..."
                )
                continue

            seo = build_seo(
                data
            )

            data["seo"] = seo

            fingerprint = make_fingerprint(
                data["lines"]
            )

            data["fingerprint"] = fingerprint

            print()
            print("=" * 60)
            print("NEW SHAYARI GENERATED")
            print("=" * 60)

            print(
                "\n".join(
                    data["lines"]
                )
            )

            print()
            print("Category:", data["category"])
            print("Style:", data["style"])
            print("Emotion:", data["emotion"])

            print()
            print("TITLE:")
            print(data["seo"]["title"])

            print()
            print("HASHTAGS:")
            print(
                " ".join(
                    data["seo"]["hashtags"]
                )
            )

            return data

        except Exception as e:

            print(
                f"⚠️ Shayari generation attempt "
                f"{attempt + 1}/3 failed: {e}"
            )

    # --------------------------------------------------------
    # Gemini failed → fallback
    # --------------------------------------------------------

    print(
        "⚠️ Gemini generation failed."
    )

    print(
        "Using fallback Shayari."
    )

    return get_fallback()


# ============================================================
# SAVE GENERATED CONTENT
# ============================================================

def generate_and_save() -> Dict[str, Any]:

    data = generate_shayari()

    save_history({
        "fingerprint": data.get(
            "fingerprint",
            make_fingerprint(
                data["lines"]
            )
        ),

        "lines": data["lines"],

        "category": data.get(
            "category",
            ""
        ),

        "style": data.get(
            "style",
            ""
        ),

        "title": data["seo"]["title"],

        "created_at": (
            __import__("datetime")
            .datetime.utcnow()
            .isoformat()
            + "Z"
        ),
    })

    return data


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Starting Hinglish Shayari Generator..."
    )

    result = generate_and_save()

    print()
    print("=" * 60)
    print("FINAL JSON")
    print("=" * 60)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )
