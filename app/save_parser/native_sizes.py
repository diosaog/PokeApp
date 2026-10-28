"""Exact native save sizes per game: pure data, importable on any platform.

The API (Linux container) checks byte sizes with these; it must not import the
Windows-only writer engine to do so.
"""

NATIVE_SIZES = {
    "X": 415232,
    "Y": 415232,
    "OR": 483328,
    "AS": 483328,
    "SN": 441856,
    "MN": 441856,
    "US": 445440,
    "UM": 445440,
}
