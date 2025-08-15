"""
ukpostcode.py: main module for parsing UK postcodes from text.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Union, List, Optional

from uk_postcodes_parsing.postcode_utils import (
    is_valid,
    to_normalised,
    to_outcode,
    to_incode,
    to_area,
    to_sector,
    to_unit,
    to_district,
    to_sub_district,
)
from uk_postcodes_parsing.fix import fix, fix_with_options

logger = logging.getLogger(__name__)

# Test for a valid postcode embedded in text
POSTCODE_CORPUS_REGEX = re.compile(r"[a-z]{1,2}\d[a-z\d]?\s*\d[a-z]{2}", re.I)
FIXABLE_POSTCODE_CORPUS_REGEX = re.compile(
    r"[a-z01]{1,2}[0-9oi][a-z\d]?\s*[0-9oi][a-z01]{2}", re.I
)

SPECIAL_CASE_POSTCODES = ("GIR", "NPT", "BX", "BF")


@dataclass(order=True)
class Postcode:
    """Class to hold the parsed postcode.
    Constructor arguments:
        original (str): The raw (original) string of the postcode.
        postcode (str): The postcode as a string.
        incode (str): The inward code (the first 3 characters) of the postcode.
        outcode (str): The outward code (the last 4 characters) of the postcode.
        area (str): The area of the postcode.
        district (str): The district of the postcode.
        sub_district (str): The sub-district of the postcode.
        sector (str): The sector of the postcode.
        unit (str): The unit of the postcode.

    Additional attributes:
        is_in_ons_postcode_directory (bool): Whether the postcode was successfully verified against
            [ONS Postcode Directory](https://geoportal.statistics.gov.uk/datasets/489c152010a3425f80a71dc3663f73e1/about).
        fix_distance (int): The number of characters that the postcode string was corrected by the
            `fix` function during parsing.
    """

    # Calculate post initialization
    is_in_ons_postcode_directory: bool = field(init=False)
    fix_distance: int = field(init=False)
    # raw text
    original: str
    # The rest of the fields are parsed from the postcode using regex
    postcode: str
    incode: str
    outcode: str
    area: str
    district: str
    sub_district: Union[str, None]
    sector: str
    unit: str

    def __post_init__(self):
        """calculate class attributes after initialization.
        - `is_in_ons_postcode_directory` (bool)
        - `fix_distance` (int): the "edit distance" between the raw postcode and final postcode
        """
        # Convert raw (original) string in postcode format
        original = self.original.upper().strip().replace(r"\s+", "")
        inward = original[-3:].strip()
        outward = original[:-3].strip()
        formatted = f"{outward} {inward}"

        fix_distance = sum(c1 != c2 for c1, c2 in zip(formatted, self.postcode)) * -1

        self.fix_distance = fix_distance
        self.is_in_ons_postcode_directory = is_in_ons_postcode_directory(self.postcode)

    def __eq__(self, other):
        """Ignore is_in_ons_postcode_directory and fix_distance."""
        return (
            self.original == other.original
            and self.postcode == other.postcode
            and self.incode == other.incode
            and self.outcode == other.outcode
            and self.area == other.area
            and self.district == other.district
            and self.sub_district == other.sub_district
            and self.sector == other.sector
            and self.unit == other.unit
        )


def _parse(postcode: str) -> dict:
    """Internal function to parse postcode string using `uk_postcodes_parsing.postcode_utils`

    Args:
        postcode (str): Postcode to parse. E.g. "EC1R 1UB".
    Returns:
        dict: Parsed postcode.
    """
    if not is_valid(postcode):
        return None
    return {
        "postcode": to_normalised(postcode),
        "incode": to_incode(postcode),
        "outcode": to_outcode(postcode),
        "area": to_area(postcode),
        "district": to_district(postcode),
        "sub_district": to_sub_district(postcode),
        "sector": to_sector(postcode),
        "unit": to_unit(postcode),
    }


def parse_all_options(postcode) -> List[Postcode]:
    """Parse possible postcodes

    Args:
        postcode (str): Postcode to parse. E.g. "EC1R 1UB".
        attempt_fix (bool): Attempt to fix postcodes. Defaults to True.
    Returns:
        Postcode: Parsed postcode.
    """
    if postcode.strip().upper().startswith(SPECIAL_CASE_POSTCODES):  # Edge case logging
        logger.debug("Found special case postcode: %s", postcode)
    if is_valid(postcode):
        return [Postcode(**_parse(postcode), original=postcode)]
    else:
        fixed_list = fix_with_options(postcode)
        return [
            Postcode(**_parse(fixed_postcode), original=postcode)
            for fixed_postcode in fixed_list
        ]


def parse(postcode: str, attempt_fix: bool = True) -> Optional[Postcode]:
    """Parse a postcode

    Args:
        postcode (str): Postcode to parse. E.g. "EC1R 1UB".
        attempt_fix (bool): Attempt to fix postcodes. Defaults to True.
    Returns:
        Postcode: Parsed postcode.
    """
    if not postcode:
        return None
    if postcode.strip().upper().startswith(SPECIAL_CASE_POSTCODES):  # Edge case logging
        logger.debug("Found special case postcode: %s", postcode)
    if is_valid(postcode):
        return Postcode(**_parse(postcode), original=postcode)
    if attempt_fix:
        fixed = fix(postcode)
        if is_valid(fixed):
            logger.debug("Postcode Fixed: '%s' => '%s'", postcode, fixed)
            return Postcode(**_parse(fixed), original=postcode)
        logger.warning("Unable to fix postcode: %s", postcode)
    logger.warning("Failed to parse postcode: %s", postcode)
    return None


def parse_from_corpus(
    text: str, attempt_fix=False, try_all_fix_options=False
) -> List[Postcode]:
    """Parse postcodes from a text corpus

    Args:
        text (str): Text corpus. E.g. "The postcode could be EC1R 1UB or EC1R IUB"
        attempt_fix (bool): Attempt to fix postcodes. Defaults to False.
        try_all_fix_options (bool): If postcode is invalid and attempt_fix=True, this option
            tries all possibilites to correct mistakes. Note this can create postcodes out of
            invaid text in edge cases.
    Returns:
        List[Postcode]: List of parsed postcodes.

    """
    if try_all_fix_options and not attempt_fix:
        raise ValueError("attempt_fix must be true if try_all_fix_options is True")

    if attempt_fix:
        postcodes = re.findall(FIXABLE_POSTCODE_CORPUS_REGEX, text)
        if try_all_fix_options:
            postcodes = [parse_all_options(postcode) for postcode in postcodes]
            postcodes = [item for sublist in postcodes for item in sublist]  # Flatten
        else:
            postcodes = [parse(postcode, attempt_fix=True) for postcode in postcodes]
            postcodes = [postcode for postcode in postcodes if postcode is not None]
        return postcodes
    else:
        postcodes = re.findall(POSTCODE_CORPUS_REGEX, text)
        postcodes = [parse(postcode, attempt_fix=False) for postcode in postcodes]
        postcodes = [postcode for postcode in postcodes if postcode is not None]
        return postcodes


def is_in_ons_postcode_directory(postcode: str) -> bool:
    """Check if the postcode is valid with ons directory

    Args:
        postcode (str): The postcode to check

    Returns:
        bool: True if the postcode is valid, False otherwise
    """
    try:
        # Extract outcode and incode - these functions handle normalization
        outcode = to_outcode(postcode)
        incode = to_incode(postcode)

        if not outcode or not incode:
            return False

        # Try to import the outcode module dynamically
        try:
            import importlib

            module_name = f"uk_postcodes_parsing.outcodes.{outcode.lower()}"
            module = importlib.import_module(module_name)
            incodes = getattr(module, "INCODES", set())
            return incode in incodes
        except (ImportError, AttributeError):
            # If outcode file doesn't exist, postcode is invalid
            return False

    except Exception as e:
        logger.debug(f"Error checking postcode in outcodes: {e}")
        return False
