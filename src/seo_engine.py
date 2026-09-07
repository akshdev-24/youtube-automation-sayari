# ============================================================
# FILE: src/seo_engine.py
# ============================================================
#
# YOUTUBE SEO ENGINE
#
# Purpose:
#   Generate:
#     - SEO title
#     - SEO description
#     - search queries
#     - YouTube tags
#     - hashtags
#
# Inspired by the useful SEO concepts of:
# Youtube-SEO-Tag-Generator
#
# Features:
#   ✅ Smart keyword extraction
#   ✅ Roman Hindi / Hinglish support
#   ✅ Google/YouTube autocomplete suggestions
#   ✅ Deterministic fallback if autocomplete fails
#   ✅ YouTube tag 500-character guard
#   ✅ Hashtag generation
#   ✅ Duplicate removal
#   ✅ No irrelevant keyword stuffing
#
# ============================================================

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from typing import Iterable


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

MAX_TAG_CHARS = 500
MAX_TITLE_CHARS = 100
MAX_DESCRIPTION_CHARS = 5000

AUTOCOMPLETE_TIMEOUT = 5

MAX_SUGGESTIONS_PER_QUERY = 8
MAX_FINAL_TAGS = 40
MAX_HASHTAGS = 15


# ------------------------------------------------------------
# STOP WORDS
# ------------------------------------------------------------

STOP_WORDS = {
    "a",
    "ab",
    "agar",
    "aur",
    "bas",
    "bhi",
    "bohot",
    "chahta",
    "chahti",
    "ek",
    "fir",
    "hai",
    "hain",
    "har",
    "ho",
    "hoga",
    "hogi",
    "hum",
    "humne",
    "in",
    "is",
    "itna",
    "ka",
    "kab",
    "kabhi",
    "kar",
    "karta",
    "karti",
    "ke",
    "ki",
    "ko",
    "kuch",
    "main",
    "mera",
    "meri",
    "mere",
    "mujhe",
    "na",
    "ne",
    "nahi",
    "nahin",
    "par",
    "phir",
    "se",
    "sirf",
    "tha",
    "thi",
    "to",
    "tum",
    "tumhe",
    "ya",
    "ye",
    "yeh",
}


# ------------------------------------------------------------
# DEFAULT SHAYARI SEO TERMS
# ------------------------------------------------------------

BASE_KEYWORDS = [
    "shayari",
    "hindi shayari",
    "hinglish shayari",
    "roman hindi shayari",
    "heart touching shayari",
    "emotional shayari",
    "dard bhari shayari",
    "sad shayari",
    "love shayari",
    "deep shayari",
    "poetry",
    "hindi poetry",
    "short shayari",
    "shayari shorts",
]


# ------------------------------------------------------------
# NORMALIZATION
# ------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Clean text while preserving Roman Hindi.
    """

    if not text:
        return ""

    text = str(text)

    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)

    # Normalize punctuation
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")

    # Keep letters/numbers/basic punctuation.
    text = re.sub(r"[^a-zA-Z0-9\s'\-]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_keyword(keyword: str) -> str:
    """
    Normalize one keyword/tag.
    """

    keyword = normalize_text(keyword)

    keyword = keyword.lower().strip()

    # Remove repeated spaces
    keyword = re.sub(r"\s+", " ", keyword)

    # Remove leading/trailing punctuation
    keyword = keyword.strip(" -,'\"")

    return keyword


# ------------------------------------------------------------
# UNIQUE HELPERS
# ------------------------------------------------------------

def unique_preserve_order(items: Iterable[str]) -> list[str]:
    """
    Remove duplicates without changing order.
    """

    result = []
    seen = set()

    for item in items:
        item = normalize_keyword(item)

        if not item:
            continue

        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result


# ------------------------------------------------------------
# KEYWORD EXTRACTION
# ------------------------------------------------------------

def extract_keywords(text: str, max_keywords: int = 12) -> list[str]:
    """
    Extract useful keyword seeds from title/shayari.

    Example:

        "Kabhi Kabhi Kisi Ko Khona Padta Hai"

    becomes approximately:

        [
            "kabhi",
            "kisi",
            "khona",
            "padta"
        ]

    Stop words are removed.
    """

    text = normalize_text(text).lower()

    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", text)

    keywords = []

    for word in words:

        word = word.strip("-'")

        if not word:
            continue

        if word in STOP_WORDS:
            continue

        if len(word) < 3:
            continue

        keywords.append(word)

    return unique_preserve_order(keywords)[:max_keywords]


# ------------------------------------------------------------
# PHRASE EXTRACTION
# ------------------------------------------------------------

def extract_phrases(text: str, max_phrases: int = 10) -> list[str]:
    """
    Extract 2-4 word phrases from title.

    These are useful as long-tail SEO seeds.
    """

    text = normalize_text(text).lower()

    words = [
        w
        for w in re.findall(r"[a-zA-Z][a-zA-Z0-9'-]+", text)
        if w not in STOP_WORDS
    ]

    phrases = []

    for size in (2, 3, 4):

        for i in range(len(words) - size + 1):

            phrase_words = words[i:i + size]

            if not phrase_words:
                continue

            phrase = " ".join(phrase_words)

            if len(phrase) < 5:
                continue

            phrases.append(phrase)

    return unique_preserve_order(phrases)[:max_phrases]


# ------------------------------------------------------------
# GOOGLE / YOUTUBE AUTOCOMPLETE
# ------------------------------------------------------------

def youtube_autocomplete(query: str) -> list[str]:
    """
    Get YouTube autocomplete suggestions.

    This is intentionally best-effort.

    If Google/YouTube autocomplete is unavailable,
    the SEO engine continues using deterministic keywords.
    """

    query = normalize_keyword(query)

    if not query:
        return []

    encoded = urllib.parse.quote(query)

    url = (
        "https://suggestqueries.google.com/complete/search"
        f"?client=youtube&ds=yt&q={encoded}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/120 Safari/537.36"
            )
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=AUTOCOMPLETE_TIMEOUT,
        ) as response:

            raw = response.read().decode(
                "utf-8",
                errors="ignore",
            )

        # Response normally looks like:
        #
        # ["query",[["suggestion",...], ...]]
        #
        # We deliberately avoid depending on a complex JSON
        # structure because autocomplete endpoints can change.

        suggestions = re.findall(
            r'\["([^"]+)"',
            raw,
        )

        cleaned = []

        for suggestion in suggestions:

            suggestion = normalize_keyword(suggestion)

            if not suggestion:
                continue

            if suggestion == query:
                continue

            cleaned.append(suggestion)

        return unique_preserve_order(
            cleaned
        )[:MAX_SUGGESTIONS_PER_QUERY]

    except Exception:
        return []


# ------------------------------------------------------------
# BUILD SEO SEEDS
# ------------------------------------------------------------

def build_seed_keywords(
    title: str,
    shayari: str,
    extra_keywords: Iterable[str] | None = None,
) -> list[str]:
    """
    Build initial SEO keyword seeds.
    """

    seeds = []

    # Title phrases are strongest
    seeds.extend(
        extract_phrases(
            title,
            max_phrases=10,
        )
    )

    # Title individual keywords
    seeds.extend(
        extract_keywords(
            title,
            max_keywords=12,
        )
    )

    # Shayari keywords
    seeds.extend(
        extract_keywords(
            shayari,
            max_keywords=8,
        )
    )

    # Extra known niche terms
    seeds.extend(BASE_KEYWORDS)

    if extra_keywords:
        seeds.extend(extra_keywords)

    return unique_preserve_order(seeds)


# ------------------------------------------------------------
# AUTOCOMPLETE EXPANSION
# ------------------------------------------------------------

def expand_with_autocomplete(
    seeds: list[str],
    max_seed_queries: int = 8,
) -> list[str]:
    """
    Expand SEO seeds through YouTube autocomplete.

    Only a limited number of queries are sent so that a
    GitHub Actions run does not make unnecessary requests.
    """

    results = []

    for seed in seeds[:max_seed_queries]:

        suggestions = youtube_autocomplete(seed)

        results.extend(suggestions)

    return unique_preserve_order(results)


# ------------------------------------------------------------
# HASHTAGS
# ------------------------------------------------------------

def hashtagify(keyword: str) -> str:
    """
    Convert keyword to a clean hashtag.

    Example:

        "heart touching shayari"

    ->

        "#HeartTouchingShayari"
    """

    keyword = normalize_keyword(keyword)

    if not keyword:
        return ""

    words = re.findall(
        r"[a-zA-Z0-9]+",
        keyword,
    )

    if not words:
        return ""

    tag = "".join(
        word[:1].upper() + word[1:]
        for word in words
    )

    return f"#{tag}"


def generate_hashtags(
    title: str,
    keywords: Iterable[str],
    max_hashtags: int = MAX_HASHTAGS,
) -> list[str]:
    """
    Generate relevant hashtags.

    Priority:
        1. title phrases
        2. SEO keywords
        3. niche hashtags
    """

    candidates = []

    candidates.extend(
        extract_phrases(
            title,
            max_phrases=8,
        )
    )

    candidates.extend(keywords)

    candidates.extend(
        [
            "shayari shorts",
            "hindi shayari",
            "hinglish shayari",
            "sad shayari",
            "love shayari",
            "heart touching shayari",
            "emotional shayari",
            "dard bhari shayari",
            "hindi poetry",
            "urdu poetry",
        ]
    )

    result = []

    seen = set()

    for candidate in candidates:

        hashtag = hashtagify(candidate)

        if not hashtag:
            continue

        key = hashtag.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(hashtag)

        if len(result) >= max_hashtags:
            break

    return result


# ------------------------------------------------------------
# YOUTUBE TAG LENGTH CALCULATOR
# ------------------------------------------------------------

def youtube_tag_cost(tag: str) -> int:
    """
    Calculate approximate YouTube API tag cost.

    YouTube documentation specifies:
      - commas count
      - tags containing spaces have additional quote cost

    We keep a safety margin below 500 characters.
    """

    tag = normalize_keyword(tag)

    if not tag:
        return 0

    cost = len(tag)

    # Comma separator
    cost += 1

    # YouTube treats multi-word tags as quoted values.
    if " " in tag:
        cost += 2

    return cost


# ------------------------------------------------------------
# 500 CHARACTER TAG BUILDER
# ------------------------------------------------------------

def build_youtube_tags(
    candidates: Iterable[str],
    max_chars: int = MAX_TAG_CHARS,
    max_tags: int = MAX_FINAL_TAGS,
) -> list[str]:
    """
    Build a valid YouTube tag list.

    Hard safety limit:
        <= 500 characters

    We intentionally target ~470 chars instead of 500
    to leave a safety margin.
    """

    # Safety margin
    safe_limit = min(
        max_chars,
        470,
    )

    tags = []

    used = set()

    current_cost = 0

    for candidate in candidates:

        tag = normalize_keyword(candidate)

        if not tag:
            continue

        # Avoid hashtags inside tags
        tag = tag.lstrip("#")

        if not tag:
            continue

        if tag in used:
            continue

        cost = youtube_tag_cost(tag)

        if current_cost + cost > safe_limit:
            continue

        used.add(tag)

        tags.append(tag)

        current_cost += cost

        if len(tags) >= max_tags:
            break

    return tags


# ------------------------------------------------------------
# DESCRIPTION
# ------------------------------------------------------------

def build_description(
    title: str,
    shayari: str,
    queries: Iterable[str],
    hashtags: Iterable[str],
) -> str:
    """
    Build YouTube description.

    Important:
      - First lines contain the actual content.
      - Search queries are clearly separated.
      - Hashtags are kept at the bottom.
    """

    title = normalize_text(title)

    shayari = shayari.strip()

    queries = unique_preserve_order(
        queries
    )

    hashtags = list(
        dict.fromkeys(
            h.strip()
            for h in hashtags
            if h and h.strip()
        )
    )

    query_text = ", ".join(
        queries[:15]
    )

    hashtag_text = " ".join(
        hashtags[:MAX_HASHTAGS]
    )

    description = (
        f"{title}\n\n"
        f"{shayari}\n\n"
        "Your Queries:\n"
        f"{query_text}\n\n"
        "If these words touched your heart, "
        "save this Shayari and share it with someone "
        "who needs to hear it.\n\n"
        f"{hashtag_text}"
    )

    # YouTube description max is 5000 bytes.
    # We keep the generated description comfortably below it.
    description = description[:MAX_DESCRIPTION_CHARS]

    return description.strip()


# ------------------------------------------------------------
# TITLE
# ------------------------------------------------------------

def build_title(
    title: str,
    keywords: Iterable[str] | None = None,
) -> str:
    """
    Clean and constrain title to YouTube's 100-character limit.
    """

    title = normalize_text(title)

    if not title:
        title = "Heart Touching Shayari"

    # Remove accidental hashtag spam from title
    title = re.sub(
        r"(?:\s*#\w+)+\s*$",
        "",
        title,
    ).strip()

    # Keep title <= 100 chars
    if len(title) > MAX_TITLE_CHARS:
        title = title[:MAX_TITLE_CHARS].rstrip()

    return title


# ------------------------------------------------------------
# COMPLETE SEO PACKAGE
# ------------------------------------------------------------

def generate_seo(
    title: str,
    shayari: str,
    extra_keywords: Iterable[str] | None = None,
) -> dict:
    """
    Generate complete SEO metadata.

    Returns:

    {
        "title": ...,
        "description": ...,
        "queries": [...],
        "tags": [...],
        "hashtags": [...]
    }
    """

    title = build_title(
        title,
        extra_keywords,
    )

    seeds = build_seed_keywords(
        title=title,
        shayari=shayari,
        extra_keywords=extra_keywords,
    )

    # Expand a subset through YouTube autocomplete.
    autocomplete = expand_with_autocomplete(
        seeds,
        max_seed_queries=8,
    )

    # Combine strongest candidates first.
    all_keywords = unique_preserve_order(
        [
            *extract_phrases(title),
            *autocomplete,
            *seeds,
            *BASE_KEYWORDS,
        ]
    )

    # Search queries
    queries = unique_preserve_order(
        [
            *autocomplete,
            *extract_phrases(title),
            *seeds,
        ]
    )[:20]

    # Tags
    tags = build_youtube_tags(
        all_keywords,
        max_chars=MAX_TAG_CHARS,
        max_tags=MAX_FINAL_TAGS,
    )

    # Hashtags
    hashtags = generate_hashtags(
        title=title,
        keywords=all_keywords,
        max_hashtags=MAX_HASHTAGS,
    )

    # Description
    description = build_description(
        title=title,
        shayari=shayari,
        queries=queries,
        hashtags=hashtags,
    )

    return {
        "title": title,
        "description": description,
        "queries": queries,
        "tags": tags,
        "hashtags": hashtags,

        # Useful for debugging
        "tag_character_count": calculate_tag_length(tags),
        "seo_seeds": seeds,
        "autocomplete_keywords": autocomplete,
    }


# ------------------------------------------------------------
# TAG LENGTH
# ------------------------------------------------------------

def calculate_tag_length(tags: Iterable[str]) -> int:
    """
    Calculate total YouTube tag cost.
    """

    total = 0

    tags = list(tags)

    for index, tag in enumerate(tags):

        tag = normalize_keyword(tag)

        if not tag:
            continue

        total += len(tag)

        # comma separator
        if index < len(tags) - 1:
            total += 1

        # quote overhead for multi-word tags
        if " " in tag:
            total += 2

    return total


# ------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------

def validate_seo_package(seo: dict) -> tuple[bool, list[str]]:
    """
    Validate generated SEO metadata.
    """

    errors = []

    title = seo.get("title", "")
    description = seo.get("description", "")
    tags = seo.get("tags", [])
    hashtags = seo.get("hashtags", [])

    if not title:
        errors.append(
            "SEO title is empty."
        )

    if len(title) > MAX_TITLE_CHARS:
        errors.append(
            f"Title exceeds {MAX_TITLE_CHARS} characters."
        )

    if not description:
        errors.append(
            "Description is empty."
        )

    if len(description.encode("utf-8")) > MAX_DESCRIPTION_CHARS:
        errors.append(
            "Description exceeds 5000 bytes."
        )

    tag_length = calculate_tag_length(tags)

    if tag_length > MAX_TAG_CHARS:
        errors.append(
            f"Tags exceed YouTube limit: {tag_length}"
        )

    if len(hashtags) > MAX_HASHTAGS:
        errors.append(
            "Too many hashtags."
        )

    # Ensure hashtags actually look like hashtags
    for hashtag in hashtags:

        if not hashtag.startswith("#"):
            errors.append(
                f"Invalid hashtag: {hashtag}"
            )

    return (
        len(errors) == 0,
        errors,
    )


# ------------------------------------------------------------
# CLI TEST
# ------------------------------------------------------------

if __name__ == "__main__":

    test_title = (
        "Jo Mil Na Saka Uska Intezaar Kyun"
    )

    test_shayari = (
        "Jo dil ke kareeb tha,\n"
        "wahi aaj sabse door hai."
    )

    seo = generate_seo(
        title=test_title,
        shayari=test_shayari,
    )

    print("\n" + "=" * 60)
    print("SEO TEST")
    print("=" * 60)

    print("\nTITLE:")
    print(seo["title"])

    print("\nDESCRIPTION:")
    print(seo["description"])

    print("\nQUERIES:")
    for query in seo["queries"]:
        print("-", query)

    print("\nTAGS:")
    print(", ".join(seo["tags"]))

    print(
        "\nTAG CHARACTER COUNT:",
        seo["tag_character_count"],
    )

    print("\nHASHTAGS:")
    print(" ".join(seo["hashtags"]))

    valid, errors = validate_seo_package(
        seo
    )

    print("\nVALID:", valid)

    if errors:
        print("\nERRORS:")
        for error in errors:
            print("-", error)
