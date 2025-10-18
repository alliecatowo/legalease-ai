"""
Identifier utilities for generating short, URL-safe NanoIDs.

This module provides functions to generate NanoIDs for use as public-facing
identifiers in URLs and APIs while UUIDs remain the internal database primary key.
"""

from nanoid import generate
from typing import Optional

# Base62 alphabet (0-9, a-z, A-Z) - URL-safe and readable
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DEFAULT_SIZE = 12  # Shorter than the old 22-char, still extremely safe


def generate_gid(size: int = DEFAULT_SIZE, alphabet: str = BASE62_ALPHABET) -> str:
    """
    Generate a NanoID identifier.

    Default generates 12-character base62 ID which provides:
    - ~71 bits of entropy
    - 1% collision probability at ~1.4 billion IDs
    - 0.1% collision probability at ~450 million IDs

    Args:
        size: Length of the ID (default: 12)
        alphabet: Character set to use (default: base62 0-9a-zA-Z)

    Returns:
        Random NanoID string

    Example:
        >>> gid = generate_gid()
        >>> len(gid)
        12
        >>> gid = generate_gid(size=16)  # More entropy if needed
        >>> len(gid)
        16
    """
    return generate(alphabet, size)


def is_valid_gid(gid: str, expected_size: Optional[int] = None) -> bool:
    """
    Check if a string is a valid GID format.

    Args:
        gid: String to validate
        expected_size: Expected length (default: accepts 12-22 for migration)

    Returns:
        True if valid GID format, False otherwise
    """
    if not isinstance(gid, str):
        return False

    # Accept 12 (new standard), and 21-22 (old base62-UUID) for migration period
    if expected_size:
        valid_length = len(gid) == expected_size
    else:
        valid_length = len(gid) in (12, 21, 22)

    if not valid_length:
        return False

    # All characters must be in base62 alphabet
    return all(char in BASE62_ALPHABET for char in gid)


def validate_gid(gid: str) -> str:
    """
    Validate a GID and return it, raising descriptive errors.

    Args:
        gid: String to validate

    Returns:
        Validated GID string

    Raises:
        ValueError: With descriptive message if GID is invalid
    """
    if not is_valid_gid(gid):
        raise ValueError(
            f"Invalid GID format: '{gid}'. "
            f"GID must be a 12-22 character base62-encoded string"
        )
    return gid
