"""
Outcode-based postcode validation files.
Each file contains incodes for a specific outcode.
"""

import os
from pathlib import Path
from typing import Set, Optional

def get_outcode_incodes(outcode: str) -> Optional[Set[str]]:
    """Get set of incodes for a given outcode"""
    try:
        module_name = f"outcodes.{outcode.lower()}"
        module = __import__(module_name, fromlist=[outcode.lower()])
        return getattr(module, 'INCODES', set())
    except (ImportError, AttributeError):
        return None

def is_postcode_valid(outcode: str, incode: str) -> bool:
    """Check if a postcode (outcode + incode) is valid"""
    incodes = get_outcode_incodes(outcode)
    return incodes is not None and incode in incodes
