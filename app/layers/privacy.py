"""LAYER 5: hide private details.

Before anything leaves your machine, private details are replaced with stand-ins:

    "I am Rahim, call 01711223344"  ->  "I am [NAME_1], call [PHONE_1]"

The real values are kept in a small dictionary (the "mapping") that lives only in memory for the
length of one request. It is never saved to the database and never sent anywhere.
Layer 10 uses restore() to put the real values back into the reply.

What we hide, in this order:
  EMAIL    rahim@example.com
  ORDER    DE-12345 (our made-up order number format)
  PHONE    Bangladesh mobile numbers (01711223344, +8801711223344, 01711-223344) and +country-code numbers
  CARD     13 to 19 digits in a row (spaces or dashes allowed)
  NUMBER   any other run of 9 or more digits (ID card numbers, account numbers)
  NAME     the profile name the sender gave us, and each word of it

Honest limit: names are only found when they match the profile name exactly.
A name written in a different spelling or alphabet, or a name nobody told us, slips through.

This file has no database and no settings. You can try it by hand:
    python -m app.tools.try_hide "I am Rahim, call 01711223344"
"""
import re
import unicodedata
from dataclasses import dataclass

# Layer 4 already turned Bangla digits into 0-9, so these patterns only need to know 0-9.
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ORDER_PATTERN = re.compile(r"\bDE-?\d{4,10}\b", re.IGNORECASE)
BD_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?880[\s-]?|0)1[3-9](?:[\s-]?\d){8}(?!\d)")
INTERNATIONAL_PHONE_PATTERN = re.compile(r"(?<![\w+])\+\d(?:[\s-]?\d){8,13}(?!\d)")
CARD_PATTERN = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
LONG_NUMBER_PATTERN = re.compile(r"(?<!\d)\d{9,}(?!\d)")

# (kind, pattern). The order matters: the first pattern to claim a piece of text wins.
PATTERNS = [
    ("EMAIL", EMAIL_PATTERN),
    ("ORDER", ORDER_PATTERN),
    ("PHONE", BD_PHONE_PATTERN),
    ("PHONE", INTERNATIONAL_PHONE_PATTERN),
    ("CARD", CARD_PATTERN),
    ("NUMBER", LONG_NUMBER_PATTERN),
]

MIN_NAME_WORD_LENGTH = 3  # shorter words (like "Md" or "Mr") would hide too many ordinary words


@dataclass(frozen=True)
class Hidden:
    text: str       # the message with stand-ins. This is what goes on to the next layers.
    mapping: dict   # "[PHONE_1]" -> "01711223344". Stays in memory only.

    @property
    def count(self) -> int:
        return len(self.mapping)


class PlaceholderBook:
    """Hands out stand-ins and remembers which real value each one replaced."""

    def __init__(self):
        self.mapping = {}   # "[PHONE_1]" -> real value
        self.by_value = {}  # (kind, real value) -> "[PHONE_1]"
        self.counts = {}    # kind -> how many we have handed out

    def placeholder_for(self, kind: str, value: str) -> str:
        # The same value always gets the same stand-in, so "call 0171... or 0171..." stays consistent.
        key = (kind, value)
        if key in self.by_value:
            return self.by_value[key]

        number = self.counts.get(kind, 0) + 1
        self.counts[kind] = number
        placeholder = f"[{kind}_{number}]"

        self.by_value[key] = placeholder
        self.mapping[placeholder] = value
        return placeholder


def hide_with_pattern(text: str, kind: str, pattern, book: PlaceholderBook) -> str:
    pieces = []
    position = 0
    for match in pattern.finditer(text):
        pieces.append(text[position:match.start()])
        pieces.append(book.placeholder_for(kind, match.group()))
        position = match.end()
    pieces.append(text[position:])
    return "".join(pieces)


def is_part_of_word(char: str) -> bool:
    # Letters, accent/vowel marks (Bangla needs these) and digits all belong inside a word.
    category = unicodedata.category(char)
    return category[0] in ("L", "M", "N")


def hide_name(text: str, name: str, book: PlaceholderBook) -> str:
    """Hide one name, but only when it stands alone: 'Sam' is hidden, 'Samsung' is not."""
    pattern = re.compile(re.escape(name), re.IGNORECASE)
    pieces = []
    position = 0
    for match in pattern.finditer(text):
        before = ""
        if match.start() > 0:
            before = text[match.start() - 1]

        after = ""
        if match.end() < len(text):
            after = text[match.end()]

        if before != "" and is_part_of_word(before):
            continue
        if after != "" and is_part_of_word(after):
            continue

        pieces.append(text[position:match.start()])
        pieces.append(book.placeholder_for("NAME", match.group()))
        position = match.end()
    pieces.append(text[position:])
    return "".join(pieces)


def names_to_hide(profile_name: str | None) -> list:
    """The full profile name first, then each word of it. Longest first, so the full name wins."""
    if profile_name is None:
        return []

    full_name = " ".join(profile_name.split())
    if full_name == "":
        return []

    names = [full_name]
    for word in full_name.split(" "):
        if len(word) >= MIN_NAME_WORD_LENGTH and word not in names:
            names.append(word)

    names.sort(key=len, reverse=True)
    return names


# ---------- the two functions the pipeline calls ----------

def hide_private(text: str, profile_name: str | None = None) -> Hidden:
    book = PlaceholderBook()

    for kind, pattern in PATTERNS:
        text = hide_with_pattern(text, kind, pattern, book)

    for name in names_to_hide(profile_name):
        text = hide_name(text, name, book)

    return Hidden(text=text, mapping=book.mapping)


def restore(text: str, mapping: dict) -> str:
    """Put the real values back. Used on Gemini's reply (Layer 10)."""
    for placeholder, real_value in mapping.items():
        text = text.replace(placeholder, real_value)
    return text
