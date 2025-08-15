import re
import logging
from typing import List
from uk_postcodes_parsing.postcode_utils import is_valid_outcode

logger = logging.getLogger(__name__)


FIXABLE_REGEX = re.compile(
    r"^\s*[a-z01]{1,2}[0-9oi][a-z\d]?\s*[0-9oi][a-z01]{2}\s*$", re.I
)


def fix(s: str) -> str:
    """Attempts to fix a given postcode

    Args:
        s (str): The postcode to fix
    Returns:
        str: The fixed postcode
    """
    if not FIXABLE_REGEX.match(s):
        return s
    s = s.upper().strip().replace(r"\s+", "")
    inward = s[-3:].strip()
    outward = s[:-3].strip()
    return f"{coerce_outcode(outward)} {coerce_incode(inward)}"


def to_letter(char: str) -> str:
    """
    Convert a number to a letter if possible. For example,
        "0" => "O"
        "1" => "I"

    Args:
        c (str): The number to convert
    Returns:
        str: The letter
    """
    return {
        "0": "O",
        "1": "I",
    }.get(char, char)


def to_number(char: str) -> str:
    """
    Convert a letter to a number if possible. For example,
        "O" => "0"
        "I" => "1"

    Args:
        c (str): The letter to convert
    Returns:
        str: The number
    """
    return {
        "O": "0",
        "I": "1",
    }.get(char, char)


def coerce(pattern: str, string: str) -> str:
    """
    Coerce a given string into a pattern. For e.g.
        pattern: "LN" => signifies a letter followed by a number
        input: "01" => changes to "O1". Where the first 0 should be a letter so it
            is coverted from 0 to O. The Second 1 is already correct so no change.

    Args:
        pattern (str): The pattern to coerce the string into
        string (str): The string to coerce

    Returns:
        str: The coerced string (with the pattern applied to it)
    """
    return "".join(
        to_number(c) if target == "N" else to_letter(c) if target == "L" else c
        for c, target in zip(string, pattern)
    )


def fix_with_options(s: str) -> List[str]:
    """Attempts to fix a given postcode, covering all options.

    Args:
        s (str): The postcode to fix
    Returns:
        str: The fixed postcode
    """
    if not FIXABLE_REGEX.match(s):
        return s
    s = s.upper().strip().replace(r"\s+", "")
    inward = s[-3:].strip()
    outward = s[:-3].strip()
    outcode_options = coerce_outcode_with_options(outward)
    return [
        f"{coerce_outcode(option)} {coerce_incode(inward)}"
        for option in outcode_options
    ]


def coerce_outcode_with_options(i: str) -> List[str]:
    """Coerce outcode, but cover all possibilities"""
    if len(i) == 2:
        return [coerce("LN", i)]
    elif len(i) == 3:
        outcodes = []
        if is_valid_outcode(outcode := coerce("LNL", i)):
            outcodes.append(outcode)
        if is_valid_outcode(outcode := coerce("LNN", i)):
            outcodes.append(outcode)
        if is_valid_outcode(outcode := coerce("LLN", i)):
            outcodes.append(outcode)
        return list(set(outcodes))
    elif len(i) == 4:
        outcodes = []
        if is_valid_outcode(outcode := coerce("LLNL", i)):
            outcodes.append(outcode)
        if is_valid_outcode(outcode := coerce("LLNN", i)):
            outcodes.append(outcode)
        return list(set(outcodes))
    else:
        return [i]


def coerce_outcode(i: str) -> str:
    """Coerce outcode"""
    if len(i) == 2:
        return coerce("LN", i)
    elif len(i) == 3:
        return coerce("L??", i)
    elif len(i) == 4:
        return coerce("LLN?", i)
    else:
        return i


def coerce_incode(i: str) -> str:
    """Coerce incode"""
    return coerce("NLL", i)
