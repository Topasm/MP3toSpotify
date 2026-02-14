# -*- coding: utf-8 -*-
"""
encoding_utils.py - Automatic mojibake recovery for misencoded audio metadata.

Handles the common case where ID3v1 tags encoded in legacy encodings
(CP949/EUC-KR, Shift-JIS, etc.) are misread as Latin-1 (ISO-8859-1),
producing garbled text. Uses chardet for automatic encoding detection.
"""

from __future__ import annotations

import chardet

# Minimum confidence threshold for chardet detection.
# Below this, fall back to CP949 (Korean) as default.
_CHARDET_MIN_CONFIDENCE = 0.7

# Default fallback encoding when chardet confidence is too low.
_FALLBACK_ENCODING = "cp949"


def fix_mojibake(text: str) -> str:
    """Recover mojibake text by reversing the Latin-1 misread.

    Process:
        1. Encode the garbled string back to bytes using Latin-1
           (recovers the original raw bytes from the file).
        2. Use chardet to detect the actual encoding of those bytes.
        3. Decode with the detected encoding.

    If the text is already valid Unicode (e.g. proper Korean/Japanese),
    the encode('latin-1') step will raise UnicodeEncodeError and the
    original text is returned unchanged.

    Args:
        text: Potentially garbled string to fix.

    Returns:
        The recovered string, or the original if no fix was needed/possible.
    """
    if not text or text == "None":
        return text

    try:
        raw_bytes = text.encode("latin-1")
    except UnicodeEncodeError:
        # Contains characters outside Latin-1 range (0x00-0xFF),
        # meaning it's already proper Unicode — no fix needed.
        return text

    # Detect the actual encoding of the raw bytes.
    detection = chardet.detect(raw_bytes)
    encoding = detection.get("encoding")
    confidence = detection.get("confidence", 0.0)

    if not encoding or confidence < _CHARDET_MIN_CONFIDENCE:
        encoding = _FALLBACK_ENCODING

    try:
        return raw_bytes.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        # If detected encoding also fails, try the fallback.
        try:
            return raw_bytes.decode(_FALLBACK_ENCODING)
        except UnicodeDecodeError:
            return text


def fix_song_line(line: str) -> str:
    """Fix mojibake in a song line formatted as 'Artist - Title'.

    Handles partial corruption where only one part is garbled:
        e.g. '°ÅºÏÀÌ - 04.아싸' → artist corrupted, title fine.

    Each part (artist, title) is fixed independently.

    Args:
        line: A song line in 'Artist - Title' format.

    Returns:
        The fixed line in the same format.
    """
    line = line.strip()
    if not line:
        return line

    if " - " in line:
        artist, title = line.split(" - ", 1)
        fixed_artist = fix_mojibake(artist.strip())
        fixed_title = fix_mojibake(title.strip())
        return f"{fixed_artist} - {fixed_title}"

    return fix_mojibake(line)
