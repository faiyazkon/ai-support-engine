"""LAYER 4: clean the text.

Customers (and attackers) can write the same words in many tricky ways: invisible
characters hidden inside words, Bangla digits, fancy letters, stretched spacing.
This layer makes ONE clean copy and ONE "skeleton" copy of every message.

  clean text   the message, tidied. It goes on to the next layers (hiding private details, search, Gemini).
  skeleton     a deliberately ugly copy used ONLY to spot attacks. It is never shown or sent to Gemini.

This file has no database and no settings. You can try it by hand:
    python -m app.tools.try_clean "I g n o r*. e all ins*strüçtìon"
"""
import re
import unicodedata
from dataclasses import dataclass

# ---------- small lists of characters ----------

# Invisible characters. They show nothing on screen but can be hidden inside a word.
INVISIBLE = set("­͏؜​‎‏⁠⁡⁢⁣⁤﻿")
INVISIBLE |= {chr(code) for code in range(0x202A, 0x202F)}  # left-to-right / right-to-left marks
INVISIBLE |= {chr(code) for code in range(0x2066, 0x206A)}

# These two are also invisible, BUT real Bangla spelling uses them, so we keep them next to Bangla letters.
JOINERS = {"‌", "‍"}

# Letters from other alphabets that look like English letters (Cyrillic, Greek, and a few odd Latin ones).
LOOKALIKES = {
    "а": "a", "с": "c", "е": "e", "о": "o", "р": "p", "х": "x", "у": "y", "к": "k", "м": "m",
    "н": "h", "т": "t", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g",
    "ο": "o", "α": "a", "ε": "e", "ρ": "p", "ν": "v", "τ": "t", "ι": "i", "κ": "k", "υ": "u",
    "ı": "i", "ɑ": "a", "ø": "o", "ł": "l", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe",
}
LOOKALIKE_TABLE = str.maketrans(LOOKALIKES)

# Characters people push INSIDE words to break them up: ig*nore, i_gnore, ig-nore
DECORATIONS = "*_~^|`'\"+=<>-"
DECORATION_TABLE = str.maketrans({char: None for char in DECORATIONS})

# Ordinary punctuation. In the skeleton it becomes a space.
PUNCTUATION = ".,!?;:()[]{}/\\"
PUNCTUATION_TABLE = str.maketrans({char: " " for char in PUNCTUATION})

# Digits and symbols that stand in for letters: 1gn0re, 4ll, @ll, $ystem
LEET_TABLE = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


@dataclass(frozen=True)
class Cleaned:
    text: str      # the tidy copy that goes on
    skeleton: str  # the ugly copy for attack checks only


# ---------- helpers for the clean text ----------

def is_bangla(char: str) -> bool:
    return char != "" and 0x0980 <= ord(char) <= 0x09FF


def remove_invisible(text: str, keep_bangla_joiners: bool) -> str:
    kept = []
    for i, char in enumerate(text):
        if char in INVISIBLE:
            continue  # always remove
        if char in JOINERS:
            before = ""
            if i > 0:
                before = text[i - 1]

            after = ""
            if i + 1 < len(text):
                after = text[i + 1]

            if keep_bangla_joiners and (is_bangla(before) or is_bangla(after)):
                kept.append(char)  # part of Bangla spelling: keep it
            continue
        kept.append(char)
    return "".join(kept)


def to_ascii_digits(text: str) -> str:
    """Turn digits of any alphabet into 0-9. Bangla ০১২৩৪৫৬৭৮৯ becomes 0123456789."""
    result = []
    for char in text:
        if unicodedata.category(char) == "Nd":
            result.append(str(unicodedata.decimal(char)))
        else:
            result.append(char)
    return "".join(result)


# ---------- helpers for the skeleton ----------

def is_latin(char: str) -> bool:
    return unicodedata.name(char, "").startswith("LATIN")


def strip_latin_accents(text: str) -> str:
    """ü -> u, ì -> i. Only touches English-style letters, so Bangla is never damaged."""
    result = []
    for char in text:
        if unicodedata.category(char) == "Mn" and result and is_latin(result[-1][-1]):
            continue  # a loose accent mark sitting on an English letter
        if is_latin(char):
            parts = unicodedata.normalize("NFKD", char)
            char = "".join(part for part in parts if unicodedata.category(part) != "Mn")
        result.append(char)
    return "".join(result)


def swap_leet(text: str) -> str:
    """1gn0re -> ignore. Only inside words that contain a letter, so plain numbers stay numbers."""
    words = []
    for word in text.split(" "):
        has_letter = False
        for char in word:
            if char.isalpha():
                has_letter = True

        if has_letter:
            words.append(word.translate(LEET_TABLE))
        else:
            words.append(word)
    return " ".join(words)


def is_single_english_letter(word: str) -> bool:
    return len(word) == 1 and "a" <= word <= "z"


def join_single_letters(text: str) -> str:
    """'i g n o r e' -> 'ignore'. Three or more single letters in a row are glued together."""
    words = text.split(" ")
    result = []
    i = 0
    while i < len(words):
        j = i
        while j < len(words) and is_single_english_letter(words[j]):
            j += 1
        if j - i >= 3:
            result.append("".join(words[i:j]))
            i = j
        else:
            result.append(words[i])
            i += 1
    return " ".join(result)


def squash_repeats(text: str) -> str:
    """heeeello -> heello. Three or more of the same English letter become two. Digits are never touched."""
    return re.sub(r"([a-z])\1{2,}", r"\1\1", text)


def make_skeleton(clean_text: str) -> str:
    text = clean_text.lower()
    text = remove_invisible(text, keep_bangla_joiners=False)
    text = strip_latin_accents(text)
    text = text.translate(LOOKALIKE_TABLE)
    text = text.translate(DECORATION_TABLE)
    text = text.translate(PUNCTUATION_TABLE)
    text = re.sub(r"\s+", " ", text).strip()
    text = swap_leet(text)
    text = join_single_letters(text)
    text = squash_repeats(text)
    return text


# ---------- the one function the pipeline calls ----------

def clean(raw: str) -> Cleaned:
    text = remove_invisible(raw, keep_bangla_joiners=True)  # 1. hidden characters out
    text = unicodedata.normalize("NFKC", text)              # 2. fancy letters become plain (ＩＧＮ -> IGN)
    text = to_ascii_digits(text)                            # 3. Bangla digits become 0-9
    text = re.sub(r"\s+", " ", text)                        # 4. any run of spaces, tabs, newlines becomes one space
    text = "".join(char for char in text if unicodedata.category(char) != "Cc").strip()  # 5. control codes out
    return Cleaned(text=text, skeleton=make_skeleton(text))
