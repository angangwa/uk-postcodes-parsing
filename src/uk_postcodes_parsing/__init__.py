import logging

# Set up library logging with NullHandler to prevent warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Core parsing functionality (backward compatible)
from uk_postcodes_parsing.ukpostcode import (
    parse,
    parse_from_corpus,
    is_in_ons_postcode_directory,
    Postcode,
)

# New rich postcode lookup APIs
try:
    from uk_postcodes_parsing.postcode_database import (
        lookup_postcode,
        search_postcodes,
        find_nearest,
        get_area_postcodes,
        reverse_geocode,
        get_outcode_postcodes,
        PostcodeResult,
    )
except ImportError:
    # Database APIs not available if dependencies missing
    pass

# Database management
try:
    from uk_postcodes_parsing.database_manager import setup_database, get_database_info
except ImportError:
    pass

__version__ = "2.1.0"
