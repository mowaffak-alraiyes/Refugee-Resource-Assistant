#!/usr/bin/env python3
"""
Data loading and caching module for community resources.
Handles parsing, normalization, and caching of resource data.
"""

import json
import re
import functools
from pathlib import Path
from typing import List, Dict, Any, Optional
import streamlit as st

# ===========================
# Constants
# ===========================

# Data sources configuration
DATA_SOURCES = {
    "Healthcare": [
        "https://raw.githubusercontent.com/your-repo/main/resources/healthcare.txt",
        "resources/healthcare.txt"
    ],
    "Education": [
        "https://raw.githubusercontent.com/your-repo/main/resources/education.txt", 
        "resources/education.txt"
    ],
    "Resettlement / Legal / Shelter": [
        "https://raw.githubusercontent.com/your-repo/main/resources/ResettlementLegalShelterBasicNeeds.txt",
        "resources/ResettlementLegalShelterBasicNeeds.txt"
    ]
}

# Compile regex patterns once for performance
ZIP_PATTERN = re.compile(r'\b(60\d{3})\b')
PHONE_PATTERN = re.compile(r'(\d{3}[-.]?\d{3}[-.]?\d{4})')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
WEBSITE_PATTERN = re.compile(r'https?://[^\s<>"\']+')

# Service patterns for normalization
SERVICE_PATTERNS = {
    "dental": re.compile(r'\b(dental|dentist|oral|teeth|tooth)\b', re.I),
    "pediatric": re.compile(r'\b(pediatric|pediatrician|child|children|kids|baby|infant)\b', re.I),
    "mental_health": re.compile(r'\b(mental|therapy|therapist|counseling|counselor|psychology|psychiatric)\b', re.I),
    "primary_care": re.compile(r'\b(primary|family|general|internal|medicine|doctor|physician)\b', re.I),
    "urgent_care": re.compile(r'\b(urgent|emergency|walk.?in|same.?day)\b', re.I),
    "esl": re.compile(r'\b(esl|english|language|learning|class|course|tutoring)\b', re.I),
    "ged": re.compile(r'\b(ged|high.?school|diploma|education|adult.?education)\b', re.I),
    "legal": re.compile(r'\b(legal|lawyer|attorney|immigration|court|advocacy)\b', re.I),
    "shelter": re.compile(r'\b(shelter|housing|homeless|emergency.?housing)\b', re.I),
}

# Language patterns for normalization
LANGUAGE_PATTERNS = {
    "spanish": re.compile(r'\b(spanish|español|española)\b', re.I),
    "arabic": re.compile(r'\b(arabic|عربي|arab)\b', re.I),
    "french": re.compile(r'\b(french|français|française)\b', re.I),
    "polish": re.compile(r'\b(polish|polski)\b', re.I),
    "mandarin": re.compile(r'\b(mandarin|chinese|中文|普通话)\b', re.I),
    "urdu": re.compile(r'\b(urdu|اردو)\b', re.I),
    "hindi": re.compile(r'\b(hindi|हिन्दी)\b', re.I),
}

# Day patterns for hours parsing
DAY_PATTERNS = {
    "monday": re.compile(r'\b(mon|monday)\b', re.I),
    "tuesday": re.compile(r'\b(tue|tues|tuesday)\b', re.I),
    "wednesday": re.compile(r'\b(wed|wednesday)\b', re.I),
    "thursday": re.compile(r'\b(thu|thur|thursday)\b', re.I),
    "friday": re.compile(r'\b(fri|friday)\b', re.I),
    "saturday": re.compile(r'\b(sat|saturday)\b', re.I),
    "sunday": re.compile(r'\b(sun|sunday)\b', re.I),
}

# ===========================
# Utility Functions
# ===========================

def fetch_text_from_sources(sources: List[str]) -> Optional[str]:
    """Try each source in order and return the first non-empty text."""
    import requests
    
    for source in sources:
        try:
            if source.startswith('http'):
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    text = response.text.strip()
                    if text:
                        return text
            else:
                # Local file
                path = Path(source)
                if path.exists():
                    text = path.read_text(encoding='utf-8').strip()
                    if text:
                        return text
        except Exception as e:
            print(f"Failed to fetch from {source}: {e}")
            continue
    return None

def normalize_phone(phone_text: str) -> Dict[str, str]:
    """Extract and normalize phone number."""
    if not phone_text:
        return {"phone": "", "phone_digits": ""}
    
    # Find phone number
    phone_match = PHONE_PATTERN.search(phone_text)
    if phone_match:
        phone = phone_match.group(1)
        # Normalize to digits only
        phone_digits = re.sub(r'\D', '', phone)
        return {"phone": phone, "phone_digits": phone_digits}
    
    return {"phone": phone_text.strip(), "phone_digits": ""}

def normalize_website(website_text: str) -> str:
    """Extract and normalize website URL."""
    if not website_text:
        return ""
    
    # Find website URL
    website_match = WEBSITE_PATTERN.search(website_text)
    if website_match:
        return website_match.group(0)
    
    return website_text.strip()

def normalize_zip(address_text: str) -> str:
    """Extract ZIP code from address."""
    if not address_text:
        return ""
    
    zip_match = ZIP_PATTERN.search(address_text)
    if zip_match:
        return zip_match.group(1)
    
    return ""

def normalize_services(services_text: str) -> List[str]:
    """Normalize and categorize services."""
    if not services_text:
        return []
    
    services = []
    services_lower = services_text.lower()
    
    for service_type, pattern in SERVICE_PATTERNS.items():
        if pattern.search(services_lower):
            services.append(service_type)
    
    return list(set(services))  # Remove duplicates

def normalize_languages(languages_text: str) -> List[str]:
    """Normalize and categorize languages."""
    if not languages_text:
        return []
    
    languages = []
    languages_lower = languages_text.lower()
    
    for lang_type, pattern in LANGUAGE_PATTERNS.items():
        if pattern.search(languages_lower):
            languages.append(lang_type)
    
    return list(set(languages))  # Remove duplicates

def parse_hours(hours_text: str) -> Dict[str, List[tuple]]:
    """Parse hours text into structured format."""
    if not hours_text:
        return {}
    
    hours_dict = {}
    hours_lower = hours_text.lower()
    
    # Simple time pattern
    time_pattern = re.compile(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?')
    
    for day, pattern in DAY_PATTERNS.items():
        if pattern.search(hours_lower):
            # Extract time ranges for this day
            day_text = pattern.search(hours_lower)
            if day_text:
                start_pos = day_text.end()
                # Look for time patterns after the day
                remaining = hours_lower[start_pos:start_pos+50]  # Look ahead 50 chars
                times = time_pattern.findall(remaining)
                
                if times:
                    # Convert to time objects (simplified)
                    time_ranges = []
                    for i in range(0, len(times), 2):
                        if i+1 < len(times):
                            start_time = times[i]
                            end_time = times[i+1]
                            # Convert to time tuples (hour, minute)
                            start_hour = int(start_time[0])
                            start_min = int(start_time[1]) if start_time[1] else 0
                            end_hour = int(end_time[0])
                            end_min = int(end_time[1]) if end_time[1] else 0
                            
                            time_ranges.append(((start_hour, start_min), (end_hour, end_min)))
                    
                    hours_dict[day] = time_ranges
    
    return hours_dict

def parse_blocks(text: str) -> List[Dict[str, Any]]:
    """Parse text blocks into structured records."""
    items = []
    
    # Split by double newlines or specific patterns
    blocks = re.split(r'\n\s*\n', text)
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) < 2:
            continue
        
        # Extract name (usually first line)
        name = lines[0].strip()
        
        # Initialize record
        record = {
            "id": f"item_{len(items) + 1}",
            "name": name,
            "address": "",
            "phone": "",
            "phone_digits": "",
            "website": "",
            "zip_code": "",
            "services": [],
            "languages": [],
            "hours": {},
            "hours_text": "",
            "search_blob": "",  # Precomputed for fast search
        }
        
        # Parse other fields
        for line in lines[1:]:
            line_lower = line.lower()
            
            if any(keyword in line_lower for keyword in ['services:', '🏥', '🛟', '🛠️']):
                services_text = re.sub(r'^(services?|🏥|🛟|🛠️):\s*', '', line, flags=re.I).strip()
                record["services"] = normalize_services(services_text)
            
            elif any(keyword in line_lower for keyword in ['phone:', '📞']):
                phone_text = re.sub(r'^(phone|📞):\s*', '', line, flags=re.I).strip()
                phone_data = normalize_phone(phone_text)
                record["phone"] = phone_data["phone"]
                record["phone_digits"] = phone_data["phone_digits"]
            
            elif any(keyword in line_lower for keyword in ['hours:', '⏰']):
                hours_text = re.sub(r'^(hours?|⏰):\s*', '', line, flags=re.I).strip()
                record["hours"] = parse_hours(hours_text)
                record["hours_text"] = hours_text
            
            elif any(keyword in line_lower for keyword in ['languages:', '🌐', 'language:']):
                lang_text = re.sub(r'^(languages?|🌐|language):\s*', '', line, flags=re.I).strip()
                record["languages"] = normalize_languages(lang_text)
            
            elif any(keyword in line_lower for keyword in ['website:', '🌐', 'web:']):
                web_text = re.sub(r'^(website|🌐|web):\s*', '', line, flags=re.I).strip()
                record["website"] = normalize_website(web_text)
            
            elif any(keyword in line_lower for keyword in ['address:', '📍', 'location:']):
                addr_text = re.sub(r'^(address|📍|location):\s*', '', line, flags=re.I).strip()
                record["address"] = addr_text
                record["zip_code"] = normalize_zip(addr_text)
            
            else:
                # Assume it's address if no keyword found
                if not record["address"] and len(line) > 10:
                    record["address"] = line
                    record["zip_code"] = normalize_zip(line)
        
        # Precompute search blob for fast searching
        search_fields = [
            record["name"],
            record["address"],
            " ".join(record["services"]),
            " ".join(record["languages"]),
            record["hours_text"]
        ]
        record["search_blob"] = " ".join(search_fields).lower()
        
        items.append(record)
    
    return items

# ===========================
# Cached Data Loading
# ===========================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_category_data(category: str) -> List[Dict[str, Any]]:
    """Load and cache category data with normalization."""
    
    # Check if normalized JSON exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    category_key = category.lower().replace(" / ", "_").replace(" ", "_")
    json_path = data_dir / f"{category_key}.json"
    
    # Return cached JSON if it exists and is recent
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cached JSON: {e}")
    
    # Parse from text sources
    sources = DATA_SOURCES.get(category, [])
    raw_text = fetch_text_from_sources(sources)
    
    if not raw_text:
        return []
    
    # Parse and normalize
    items = parse_blocks(raw_text)
    
    # Save normalized data to JSON
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving normalized JSON: {e}")
    
    return items

@st.cache_resource
def get_compiled_patterns():
    """Return compiled regex patterns for caching."""
    return {
        "zip": ZIP_PATTERN,
        "phone": PHONE_PATTERN,
        "email": EMAIL_PATTERN,
        "website": WEBSITE_PATTERN,
        "services": SERVICE_PATTERNS,
        "languages": LANGUAGE_PATTERNS,
        "days": DAY_PATTERNS,
    }

# ===========================
# Public API
# ===========================

def get_dataset(category: str) -> tuple[List[Dict[str, Any]], str]:
    """Get dataset for a category. Returns (items, raw_text)."""
    
    # Load normalized data
    items = load_category_data(category)
    
    # Get raw text for display purposes
    sources = DATA_SOURCES.get(category, [])
    raw_text = fetch_text_from_sources(sources) or ""
    
    return items, raw_text

def refresh_category_cache(category: str) -> None:
    """Force refresh of category cache."""
    category_key = category.lower().replace(" / ", "_").replace(" ", "_")
    json_path = Path("data") / f"{category_key}.json"
    
    if json_path.exists():
        json_path.unlink()
    
    # Clear Streamlit cache
    load_category_data.clear()
    
    # Reload data
    load_category_data(category)


