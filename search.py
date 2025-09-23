#!/usr/bin/env python3
"""
Enhanced search module with fuzzy matching and "open now" detection.
"""

import re
from datetime import datetime, time
from typing import List, Dict, Any, Tuple, Optional
import streamlit as st
from rapidfuzz import fuzz
import pytz

# ===========================
# Search Configuration
# ===========================

# Base synonyms for keyword expansion
BASE_SYNONYMS = {
    "health": ["health", "healthcare", "medical", "clinic", "hospital", "doctor", "physician"],
    "dental": ["dental", "dentist", "oral", "teeth", "tooth", "dental care"],
    "pediatric": ["pediatric", "pediatrician", "child", "children", "kids", "baby", "infant"],
    "mental": ["mental", "therapy", "therapist", "counseling", "counselor", "psychology", "psychiatric"],
    "primary": ["primary", "family", "general", "internal", "medicine", "doctor", "physician"],
    "urgent": ["urgent", "emergency", "walk-in", "same-day", "walk in"],
    "education": ["education", "school", "learning", "class", "course", "training"],
    "esl": ["esl", "english", "language", "learning", "class", "course", "tutoring"],
    "ged": ["ged", "high school", "diploma", "education", "adult education"],
    "legal": ["legal", "lawyer", "attorney", "immigration", "court", "advocacy"],
    "shelter": ["shelter", "housing", "homeless", "emergency housing"],
    "free": ["free", "no cost", "no-cost", "complimentary", "pro bono"],
    "low cost": ["low cost", "low-cost", "affordable", "sliding scale"],
    "medicaid": ["medicaid", "medicare", "insurance", "coverage"],
}

# ===========================
# Time and Availability Functions
# ===========================

def is_open_now(record: Dict[str, Any], timezone: str = "America/Chicago") -> bool:
    """Check if a service is currently open."""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        current_day = now.strftime("%A").lower()
        current_time = now.time()
        
        hours = record.get("hours", {})
        if current_day not in hours:
            return False
        
        time_ranges = hours[current_day]
        for start_time, end_time in time_ranges:
            # Convert tuple to time object
            start = time(start_time[0], start_time[1])
            end = time(end_time[0], end_time[1])
            
            if start <= current_time <= end:
                return True
        
        return False
    except Exception:
        return False

def get_next_open_time(record: Dict[str, Any], timezone: str = "America/Chicago") -> Optional[str]:
    """Get the next time a service will be open."""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        # Check next 7 days
        for i in range(7):
            check_date = now + pytz.timedelta(days=i)
            day_name = check_date.strftime("%A").lower()
            
            hours = record.get("hours", {})
            if day_name in hours:
                time_ranges = hours[day_name]
                if time_ranges:
                    start_time, _ = time_ranges[0]
                    next_open = datetime.combine(check_date.date(), time(start_time[0], start_time[1]))
                    
                    if i == 0 and next_open <= now:
                        continue  # Already passed today
                    
                    return next_open.strftime("%A %I:%M %p")
        
        return None
    except Exception:
        return None

# ===========================
# Search Functions
# ===========================

@st.cache_resource
def get_search_patterns():
    """Get compiled regex patterns for search."""
    return {
        "zip": re.compile(r'\b(60\d{3})\b'),
        "service": re.compile(r'\b(dental|pediatric|mental|primary|urgent|esl|ged|legal|shelter)\b', re.I),
        "day": re.compile(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b', re.I),
        "time": re.compile(r'\b(now|today|open|available)\b', re.I),
    }

def extract_key_terms(query: str) -> Dict[str, str]:
    """Extract key terms from query using synonyms and patterns."""
    query_lower = query.lower()
    patterns = get_search_patterns()
    
    extracted = {}
    
    # Extract ZIP code
    zip_match = patterns["zip"].search(query)
    if zip_match:
        extracted["zip"] = zip_match.group(1)
    
    # Extract service type
    service_match = patterns["service"].search(query)
    if service_match:
        extracted["service"] = service_match.group(1).lower()
    
    # Extract day
    day_match = patterns["day"].search(query)
    if day_match:
        day = day_match.group(1).lower()
        # Normalize day names
        day_map = {
            "mon": "monday", "tue": "tuesday", "wed": "wednesday",
            "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"
        }
        extracted["day"] = day_map.get(day, day)
    
    # Extract time preference
    time_match = patterns["time"].search(query)
    if time_match:
        extracted["time"] = time_match.group(1).lower()
    
    return extracted

def expand_query_terms(query: str) -> List[str]:
    """Expand query with synonyms for better matching."""
    query_lower = query.lower()
    expanded_terms = [query_lower]
    
    for base_term, synonyms in BASE_SYNONYMS.items():
        if base_term in query_lower:
            for synonym in synonyms:
                if synonym not in query_lower:
                    expanded_query = query_lower.replace(base_term, synonym)
                    expanded_terms.append(expanded_query)
    
    return expanded_terms

def fuzzy_score(record: Dict[str, Any], query: str) -> float:
    """Calculate fuzzy match score for a record."""
    search_blob = record.get("search_blob", "")
    if not search_blob:
        return 0.0
    
    # Use token sort ratio for better fuzzy matching
    score = fuzz.token_sort_ratio(search_blob, query.lower())
    return score / 100.0  # Normalize to 0-1

def must_have_patterns(query: str, category: str) -> List[re.Pattern]:
    """Get must-have patterns based on query and category."""
    patterns = []
    query_lower = query.lower()
    
    # Category-specific patterns
    if category == "Healthcare":
        if "dental" in query_lower:
            patterns.append(re.compile(r'\b(dental|dentist|oral)\b', re.I))
        elif "pediatric" in query_lower:
            patterns.append(re.compile(r'\b(pediatric|child|children|kids)\b', re.I))
        elif "mental" in query_lower:
            patterns.append(re.compile(r'\b(mental|therapy|therapist|counseling)\b', re.I))
    
    elif category == "Education":
        if "esl" in query_lower:
            patterns.append(re.compile(r'\b(esl|english|language)\b', re.I))
        elif "ged" in query_lower:
            patterns.append(re.compile(r'\b(ged|high.?school|diploma)\b', re.I))
    
    elif category == "Resettlement / Legal / Shelter":
        if "legal" in query_lower:
            patterns.append(re.compile(r'\b(legal|lawyer|attorney|immigration)\b', re.I))
        elif "shelter" in query_lower:
            patterns.append(re.compile(r'\b(shelter|housing|homeless)\b', re.I))
    
    return patterns

def rank_items(
    items: List[Dict[str, Any]], 
    query: str, 
    category: str,
    zip_filter: str = "All",
    lang_filter: str = "All", 
    service_filter: str = "All",
    day_filter: str = "All"
) -> List[Tuple[float, Dict[str, Any]]]:
    """Enhanced ranking with fuzzy matching and filters."""
    
    if not items or not query.strip():
        return []
    
    # Extract key terms from query
    key_terms = extract_key_terms(query)
    
    # Get must-have patterns
    must_have = must_have_patterns(query, category)
    
    # Expand query terms
    expanded_queries = expand_query_terms(query)
    
    scored_items = []
    
    for item in items:
        score = 0.0
        
        # Apply filters
        if zip_filter != "All" and item.get("zip_code") != zip_filter:
            continue
        
        if lang_filter != "All":
            languages = item.get("languages", [])
            if lang_filter not in languages:
                continue
        
        if service_filter != "All":
            services = item.get("services", [])
            if service_filter not in services:
                continue
        
        if day_filter != "All":
            hours = item.get("hours", {})
            if day_filter not in hours:
                continue
        
        # Check must-have patterns
        search_text = item.get("search_blob", "")
        if must_have:
            if not any(pattern.search(search_text) for pattern in must_have):
                continue
        
        # Base fuzzy score
        max_fuzzy_score = 0.0
        for expanded_query in expanded_queries:
            fuzzy_score_val = fuzzy_score(item, expanded_query)
            max_fuzzy_score = max(max_fuzzy_score, fuzzy_score_val)
        
        score += max_fuzzy_score * 0.6  # 60% weight for fuzzy matching
        
        # Bonus for exact matches
        query_lower = query.lower()
        if query_lower in search_text:
            score += 0.3
        
        # Bonus for name matches
        name = item.get("name", "").lower()
        if query_lower in name:
            score += 0.2
        
        # Bonus for service matches
        services = item.get("services", [])
        for service in services:
            if service in query_lower:
                score += 0.1
        
        # Bonus for "open now"
        if key_terms.get("time") in ["now", "today", "open"]:
            if is_open_now(item):
                score += 0.4
        
        # Bonus for ZIP match
        if key_terms.get("zip"):
            if item.get("zip_code") == key_terms["zip"]:
                score += 0.3
        
        # Bonus for day match
        if key_terms.get("day"):
            hours = item.get("hours", {})
            if key_terms["day"] in hours:
                score += 0.2
        
        scored_items.append((score, item))
    
    # Sort by score (highest first)
    scored_items.sort(key=lambda x: x[0], reverse=True)
    
    # Filter out very low scores
    return [(score, item) for score, item in scored_items if score > 0.1]

# ===========================
# Utility Functions
# ===========================

def detect_zip_from_query(query: str) -> Optional[str]:
    """Detect ZIP code from query."""
    patterns = get_search_patterns()
    zip_match = patterns["zip"].search(query)
    return zip_match.group(1) if zip_match else None

def detect_service_from_query(query: str, category: str) -> Optional[str]:
    """Detect service type from query."""
    key_terms = extract_key_terms(query)
    return key_terms.get("service")

def detect_day_from_query(query: str) -> Optional[str]:
    """Detect day from query."""
    key_terms = extract_key_terms(query)
    return key_terms.get("day")

def clean_query_of_zip(query: str) -> str:
    """Remove ZIP code from query."""
    patterns = get_search_patterns()
    return patterns["zip"].sub("", query).strip()

def clean_query_of_service_and_day(query: str, detected_service: str = None, detected_day: str = None) -> str:
    """Remove detected service and day terms from query."""
    cleaned = query
    
    if detected_service:
        cleaned = re.sub(rf'\b{re.escape(detected_service)}\b', '', cleaned, flags=re.I)
    
    if detected_day:
        cleaned = re.sub(rf'\b{re.escape(detected_day)}\b', '', cleaned, flags=re.I)
    
    return cleaned.strip()
