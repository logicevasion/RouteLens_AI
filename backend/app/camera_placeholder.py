"""Deterministic comparison against the supplied Vancouver outage graphic."""

from base64 import b64decode

from PIL import Image

OFFLINE_SHA256 = "4107c7a44d6fd293742bb52ddf468241911a89a2a18a206d6670ba62666a4db2"

# Derived from tests/fixtures/IMG-20261103-WA0002.jpg. The central crop
# captures the text pattern and gives the plain blue margin less weight.
_THUMBNAIL_SIZE = (48, 32)
_TEXT_BOX = (11, 8, 37, 22)
_BACKGROUND_RGB = (0, 101, 157)
_TEXT_TEMPLATE = b64decode(
    "S0lNTUxLSU1NSUxMTE1MSUpKS0xMTUxMSU14jllLU1heTUtiVFBSTk9gXF5XUFFMUFVf"
    "TmZ9cZGBh4tJXotXk3ick597ooWHfUBnhpJUYHNviYJ7l1BbhG6fknd+mnSPgpeTR2Z9"
    "l15RVU9OU1heTkxfW05WT09gXk1WUlFPUFVeTkxMS0lJR0RISURGSUhJSUZHSUhJTUhJ"
    "TUlNTkpninaCcmx5hXJ1dX5iZGuFa2dQbGtPTk1NS1uEhI+RnJ+Sh3+jnJOciamGjUmG"
    "fUVPTU1NUmRshGRVdEtpfGZveHdtbGiAdlpaS09NS0lMSUVGTU5ETUVITEZEQkdFSEhK"
    "S0dLSE1dYlJWa2tITWlWbFRGZV9pX2deUlpUaV9oToGJfm+Lg2V8gZGdZm6Nip56qo+H"
    "gIlyjJJNfoGChGZoV22GgmVUYIGWj3KObY5sf3qHiE5TVFBXTVBJSllNTkxIV1RZVkpQ"
    "Tk9NWVVbTg=="
)


def matches_offline_placeholder(sha256: str, image: Image.Image) -> bool:
    """Match a decoded frame, with tolerance for JPEG recompression and resizing."""
    if sha256 == OFFLINE_SHA256:
        return True
    corners = image.resize((5, 5), Image.Resampling.BOX).convert("RGB")
    for point in ((0, 0), (4, 0), (0, 4), (4, 4)):
        if any(
            abs(actual - expected) > 12
            for actual, expected in zip(corners.getpixel(point), _BACKGROUND_RGB)
        ):
            return False
    thumbnail = image.convert("L").resize(_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    text = thumbnail.crop(_TEXT_BOX).tobytes()
    mean_difference = sum(abs(a - b) for a, b in zip(text, _TEXT_TEMPLATE)) / len(text)
    return mean_difference <= 4
