"""BGG URL parser for extracting game information."""

import re
from typing import Optional
from data_models import BoardGame


def parse_bgg_url(url: str) -> Optional[BoardGame]:
    """Parse a BoardGameGeek URL and extract game information.
    
    Supports formats:
    - https://boardgamegeek.com/boardgame/{id}/{slug}
    - https://boardgamegeek.com/boardgame/{id}
    - boardgamegeek.com/boardgame/{id}/{slug}
    - boardgame/{id}/{slug} (partial)
    
    Args:
        url: The BGG URL to parse
    
    Returns:
        BoardGame object with object_id set, or None if parsing fails
    """
    if not url:
        return None
    
    # Clean up the URL - remove whitespace
    url = url.strip()
    
    # Add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    # Pattern to match BGG URLs
    # Matches: boardgamegeek.com/boardgame/{id} with optional /{slug}
    pattern = r'boardgamegeek\.com/boardgame/(\d+)(?:/[^/]*)?(?:\?.*)?$'
    
    match = re.search(pattern, url)
    if not match:
        return None
    
    try:
        object_id = int(match.group(1))
        # Create minimal BoardGame object with just the ID
        # The name will be fetched later by the scraper
        return BoardGame(
            object_id=object_id,
            name="",  # Will be populated by scraper
            publishers=[]  # Will be populated by scraper
        )
    except ValueError:
        return None


def is_valid_bgg_url(url: str) -> bool:
    """Check if a URL is a valid BoardGameGeek URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if URL is valid BGG format, False otherwise
    """
    return parse_bgg_url(url) is not None