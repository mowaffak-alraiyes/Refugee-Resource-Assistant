#!/usr/bin/env python3
"""
Chicago neighborhood to ZIP code mapping.
Allows users to search by neighborhood name instead of just ZIP codes.
"""

from typing import List, Tuple

NEIGHBORHOOD_TO_ZIPS = {
    # North Side
    "rogers park": ["60626", "60645"],
    "uptown": ["60613", "60640", "60657"],
    "lincoln square": ["60625", "60640"],
    "lakeview": ["60613", "60614", "60657"],
    "lincoln park": ["60614", "60657"],
    "old town": ["60610", "60614"],
    "gold coast": ["60610", "60611"],
    "river north": ["60610", "60611", "60654"],
    "loop": ["60601", "60602", "60603", "60604"],
    "south loop": ["60605", "60616"],
    
    # West Side
    "humboldt park": ["60622", "60647"],
    "west town": ["60622", "60647"],
    "wicker park": ["60622"],
    "bucktown": ["60622"],
    "ukrainian village": ["60622"],
    "logan square": ["60647"],
    "avondale": ["60618", "60641"],
    "irving park": ["60618", "60641"],
    "portage park": ["60630", "60634", "60641"],
    "austin": ["60644", "60651"],
    "garfield park": ["60624", "60644"],
    "lawndale": ["60623", "60624"],
    "little village": ["60623", "60608"],
    "pilsen": ["60608", "60616"],
    
    # South Side
    "bridgeport": ["60608", "60616"],
    "chinatown": ["60616"],
    "bronzeville": ["60615", "60653"],
    "hyde park": ["60615", "60637"],
    "kenwood": ["60615", "60637"],
    "woodlawn": ["60615", "60637"],
    "englewood": ["60621", "60636"],
    "auburn gresham": ["60620", "60628"],
    "chatham": ["60619", "60620"],
    "south shore": ["60649"],
    "calumet heights": ["60617", "60619"],
    "pullman": ["60628"],
    "roseland": ["60628"],
    "west pullman": ["60628", "60643"],
    "morgan park": ["60643"],
    "beverly": ["60643"],
    "ashburn": ["60652"],
    "archer heights": ["60632", "60638"],
    "brighton park": ["60632", "60629"],
    "mckinley park": ["60609", "60632"],
    "back of the yards": ["60609", "60632"],
    "new city": ["60609", "60632"],
    "gage park": ["60629", "60632"],
    "west lawn": ["60629"],
    "garfield ridge": ["60638"],
    "clearing": ["60638"],
    "west elsd": ["60638"],
    
    # Common variations
    "rogers park": ["60626", "60645"],
    "lincoln square": ["60625", "60640"],
    "wicker park": ["60622"],
    "logan square": ["60647"],
    "little village": ["60623", "60608"],
    "hyde park": ["60615", "60637"],
}

def get_zips_for_neighborhood(neighborhood: str) -> List[str]:
    """Get ZIP codes for a neighborhood name (case-insensitive)."""
    neighborhood_lower = neighborhood.lower().strip()
    
    # Direct match
    if neighborhood_lower in NEIGHBORHOOD_TO_ZIPS:
        return NEIGHBORHOOD_TO_ZIPS[neighborhood_lower]
    
    # Fuzzy match - check if neighborhood name contains any key
    for key, zips in NEIGHBORHOOD_TO_ZIPS.items():
        if key in neighborhood_lower or neighborhood_lower in key:
            return zips
    
    return []

def expand_neighborhood_query(query: str) -> Tuple[str, List[str]]:
    """
    Expand query to include ZIP codes if neighborhood is mentioned.
    Returns (cleaned_query, list_of_zips)
    """
    query_lower = query.lower()
    found_zips = []
    cleaned_query = query
    
    # Check each neighborhood
    for neighborhood, zips in NEIGHBORHOOD_TO_ZIPS.items():
        if neighborhood in query_lower:
            found_zips.extend(zips)
            # Remove neighborhood name from query (optional - can keep both)
            # cleaned_query = cleaned_query.replace(neighborhood, "").strip()
    
    # Remove duplicates
    found_zips = list(set(found_zips))
    
    return cleaned_query, found_zips

def get_all_neighborhoods() -> List[str]:
    """Get list of all available neighborhood names."""
    return sorted(list(NEIGHBORHOOD_TO_ZIPS.keys()))

