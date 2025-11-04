#!/usr/bin/env python3
"""
Map and geocoding utilities for resource visualization.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import requests
import time
import math

# Chicago center coordinates (for distance calculation)
CHICAGO_CENTER = (41.8781, -87.6298)

# ===========================
# Geocoding
# ===========================

@st.cache_data(ttl=86400)  # Cache for 24 hours
def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Geocode an address to lat/lon using Nominatim (free, no API key needed).
    Returns (latitude, longitude) or None if geocoding fails.
    """
    if not address:
        return None
    
    try:
        # Use Nominatim (OpenStreetMap) - free, no API key required
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        headers = {
            "User-Agent": "CommunityResourcesApp/1.0"  # Required by Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return (lat, lon)
        
        # Rate limiting - be respectful
        time.sleep(0.2)  # Nominatim allows 1 request per second
        
    except Exception as e:
        print(f"Geocoding error for '{address}': {e}")
    
    return None

def batch_geocode_addresses(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Geocode multiple addresses and add lat/lon to items.
    Respects rate limits and caches results.
    """
    for item in items:
        address = item.get("address", "")
        if address and not item.get("latitude"):  # Only geocode if not already done
            coords = geocode_address(address)
            if coords:
                item["latitude"] = coords[0]
                item["longitude"] = coords[1]
            else:
                # Set to Chicago center as fallback if geocoding fails
                item["latitude"] = 41.8781
                item["longitude"] = -87.6298
    
    return items

# ===========================
# Map Rendering
# ===========================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.
    Returns distance in miles.
    """
    # Radius of Earth in miles
    R = 3959.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return distance

def sort_by_distance(items: List[Dict[str, Any]], user_location: Optional[Tuple[float, float]] = None) -> List[Dict[str, Any]]:
    """
    Sort items by distance from user location (or Chicago center if not provided).
    """
    if not items:
        return items
    
    # Use Chicago center as default if no user location
    if user_location is None:
        user_location = CHICAGO_CENTER
    
    user_lat, user_lon = user_location
    
    # Calculate distance for each item
    items_with_distance = []
    for item in items:
        lat = item.get("latitude")
        lon = item.get("longitude")
        
        if lat and lon:
            distance = calculate_distance(user_lat, user_lon, lat, lon)
            item["distance_miles"] = distance
            items_with_distance.append(item)
        else:
            # Items without coordinates go to the end
            item["distance_miles"] = float('inf')
            items_with_distance.append(item)
    
    # Sort by distance
    items_with_distance.sort(key=lambda x: x.get("distance_miles", float('inf')))
    
    return items_with_distance

def render_map_view(items: List[Dict[str, Any]], category: str = "", user_location: Optional[Tuple[float, float]] = None, sort_by_dist: bool = False) -> None:
    """
    Render an interactive map view of resources using Streamlit's built-in map.
    
    Args:
        items: List of resource items
        category: Resource category
        user_location: Optional (lat, lon) tuple for distance sorting
        sort_by_dist: Whether to sort results by distance
    """
    if not items:
        st.warning("No resources to display on map.")
        return
    
    # Geocode addresses (with caching)
    items_with_coords = batch_geocode_addresses(items)
    
    # Sort by distance if requested
    if sort_by_dist:
        items_with_coords = sort_by_distance(items_with_coords, user_location)
        st.info("📍 Results sorted by distance (nearest first)")
    
    # Prepare data for map
    map_data = []
    for item in items_with_coords:
        lat = item.get("latitude")
        lon = item.get("longitude")
        
        if lat and lon:
            # Create map marker data
            marker_data = {
                "name": item.get("name", "Unknown"),
                "address": item.get("address", ""),
                "phone": item.get("phone", ""),
                "lat": lat,
                "lon": lon,
            }
            map_data.append(marker_data)
    
    if not map_data:
        st.warning("Could not geocode addresses for map display.")
        return
    
    # Convert to DataFrame for st.map()
    df = pd.DataFrame(map_data)
    
    # Calculate map center (average of all coordinates)
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()
    
    # Display map with markers
    st.map(
        df,
        latitude="lat",
        longitude="lon",
        zoom=11,  # Zoom level for Chicago
        use_container_width=True
    )
    
    # Show list below map
    st.markdown("---")
    st.subheader("📍 Locations on Map")
    
    for i, item in enumerate(items_with_coords[:20], 1):  # Limit to 20 for performance
        lat = item.get("latitude")
        lon = item.get("longitude")
        
        if lat and lon:
            name = item.get("name", "Unknown")
            address = item.get("address", "")
            phone = item.get("phone", "")
            distance = item.get("distance_miles")
            
            # Google Maps link
            map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            
            col1, col2 = st.columns([3, 1])
            with col1:
                distance_text = ""
                if distance is not None and distance != float('inf'):
                    distance_text = f" • {distance:.1f} mi away"
                st.markdown(f"**{i}. {name}**{distance_text}")
                st.markdown(f"📍 {address}")
                if phone:
                    st.markdown(f"📞 {phone}")
            with col2:
                st.link_button("🗺️ View", map_url)

# render_map_toggle moved to app_optimized.py for better integration

