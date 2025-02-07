"""
postcode_utils.py: Utilities for working with postcodes.
"""

import re
from typing import Union


# Tests for district
DISTRICT_SPLIT_REGEX = re.compile(r"^([a-z]{1,2}\d)([a-z])$", re.I)

# Tests for the unit section of a postcode
UNIT_REGEX = re.compile(r"[a-z]{2}$", re.I)

# Tests for the inward code section of a postcode
INCODE_REGEX = re.compile(r"\d[a-z]{2}$", re.I)

# Tests for the outward code section of a postcode
OUTCODE_REGEX = re.compile(r"^[a-z]{1,2}\d[a-z\d]?$", re.I)

# Tests for a valid postcode
POSTCODE_REGEX = re.compile(r"^[a-z]{1,2}\d[a-z\d]?\s*\d[a-z]{2}$", re.I)

# Tests for the area section of a postcode
AREA_REGEX = re.compile(r"^[a-z]{1,2}", re.I)


def sanitize(string: str) -> str:
    """Sanitizes a string by removing whitespace and converting to uppercase.
    Args:
        s (str): The string to sanitize
    Returns:
        str: The sanitized string
    """
    return string.replace(" ", "").upper()


def is_valid(postcode: str) -> bool:
    """
    Checks if a postcode is valid using the `POSTCODE_REGEX`.
    Args:
        postcode (str): The postcode to check

    Returns:
        bool: True if the postcode is valid, False otherwise
    """
    return re.match(POSTCODE_REGEX, postcode) is not None


def is_valid_outcode(outcode: str) -> bool:
    """
    Checks if a string representing an outcode is valid using the `OUTCODE_REGEX`.
    Args:
        outcode (str): The postcode to check
    Returns:
        bool: True if the postcode is valid, False otherwise
    """
    return re.match(OUTCODE_REGEX, outcode) is not None


def to_normalised(postcode: str) -> Union[str, None]:
    """
    Normalises a postcode by removing whitespace, converting to uppercase, and formatting.
    Args:
        postcode (str): The postcode to normalise
    Returns:
        str: The normalised postcode
    """
    outcode = to_outcode(postcode)
    if outcode is None:
        return None
    incode = to_incode(postcode)
    return None if incode is None else f"{outcode} {incode}"


def to_outcode(postcode: str) -> Union[str, None]:
    """Extract the outcode from a postcode string.
    Args:
        postcode (str): The postcode to extract the outcode from
    Returns:
        str: The outcode
    """
    if not is_valid(postcode):
        return None
    return re.sub(INCODE_REGEX, "", sanitize(postcode))


def to_incode(postcode: str) -> Union[str, None]:
    """Extract the incode from a postcode string.
    Args:
        postcode (str): The postcode to extract the incode from
    Returns:
        str: The incode
    """
    if not is_valid(postcode):
        return None
    incode = re.findall(INCODE_REGEX, sanitize(postcode))
    return incode[0] if incode else None


def to_area(postcode: str) -> Union[str, None]:
    """Extract the area from a postcode string.
    Args:
        postcode (str): The postcode to extract the area from
    Returns:
        str: The area
    """
    if not is_valid(postcode):
        return None
    area = re.findall(AREA_REGEX, sanitize(postcode))
    return area[0] if area else None


def to_sector(postcode: str) -> Union[str, None]:
    """Extract the sector from a postcode string.
    Args:
        postcode (str): The postcode to extract the sector from
    Returns:
        str: The sector
    """
    outcode = to_outcode(postcode)
    if outcode is None:
        return None
    incode = to_incode(postcode)
    return None if incode is None else f"{outcode} {incode[0]}"


def to_unit(postcode: str) -> Union[str, None]:
    """Extract the unit from a postcode string.
    Args:
        postcode (str): The postcode to extract the unit from
    Returns:
        str: The unit
    """
    if not is_valid(postcode):
        return None
    unit = re.findall(UNIT_REGEX, sanitize(postcode))
    return unit[0] if unit else None


def to_district(postcode: str) -> Union[str, None]:
    """Extract the district from a postcode string.
    Args:
        postcode (str): The postcode to extract the district from
    Returns:
        str: The district
    """
    outcode = to_outcode(postcode)
    if outcode is None:
        return None
    district = re.match(DISTRICT_SPLIT_REGEX, outcode)
    return district[1] if district else outcode


def to_sub_district(postcode: str) -> Union[str, None]:
    """Extract the sub-district from a postcode string.
    Args:
        postcode (str): The postcode to extract the sub-district from
    Returns:
        str: The sub-district
    """
    outcode = to_outcode(postcode)
    if outcode is None:
        return None
    split = re.match(DISTRICT_SPLIT_REGEX, outcode)
    return None if split is None else outcode
