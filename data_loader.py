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
        "https://raw.githubusercontent.com/mowaffak-alraiyes/refugee-resources/main/resources/healthcare.txt",
        "resources/healthcare.txt"
    ],
    "Education": [
        "https://raw.githubusercontent.com/mowaffak-alraiyes/refugee-resources/main/resources/education.txt", 
        "resources/education.txt"
    ],
    "Resettlement / Legal / Shelter": [
        "https://raw.githubusercontent.com/mowaffak-alraiyes/refugee-resources/main/resources/ResettlementLegalShelterBasicNeeds.txt",
        "resources/ResettlementLegalShelterBasicNeeds.txt"
    ]
}

# Compile regex patterns once for performance
ZIP_PATTERN = re.compile(r'\b(60\d{3})\b')
PHONE_PATTERN = re.compile(r'(\d{3}[-.]?\d{3}[-.]?\d{4})')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
WEBSITE_PATTERN = re.compile(r'https?://[^\s<>"\']+')

# Service patterns for normalization with comprehensive subcategories
SERVICE_PATTERNS = {
    # Healthcare subcategories
    "dental": re.compile(r'\b(dental|dentist|oral|teeth|tooth|dental care|exams|cleanings|x.?rays|extractions)\b', re.I),
    "pediatric": re.compile(r'\b(pediatric|pediatrician|child|children|kids|baby|infant|adolescent|adolescent medicine|youth.?focused)\b', re.I),
    "mental_health": re.compile(r'\b(mental|therapy|therapist|counseling|counselor|psychology|psychiatric|psychiatry|behavioral health|behavioral)\b', re.I),
    "primary_care": re.compile(r'\b(primary care|family medicine|family|general|internal medicine|internal|adult|physician|doctor)\b', re.I),
    "womens_health": re.compile(r'\b(women\'?s health|obstetrics|gynecology|ob/gyn|ob-gyn|ob gyn|prenatal|midwifery|prenatal/ob)\b', re.I),
    "urgent_care": re.compile(r'\b(urgent|emergency|walk.?in|same.?day|24/7|24 hours)\b', re.I),
    "hiv_sti": re.compile(r'\b(hiv|sti|std|sexually transmitted|hiv/st?i)\b', re.I),
    "nutrition": re.compile(r'\b(nutrition|nutritional|dietitian|diet)\b', re.I),
    "mobile_screening": re.compile(r'\b(mobile|screening|screenings|glucose|blood pressure|immunization|vaccination|vaccine)\b', re.I),
    "specialty": re.compile(r'\b(surgery|podiatry|surgical|specialty)\b', re.I),
    
    # Education subcategories
    "esl": re.compile(r'\b(esl|english|english language|language training|language classes|english classes|language learning)\b', re.I),
    "citizenship": re.compile(r'\b(citizenship|citizenship preparation|citizenship classes|citizenship exam|citizenship instruction|civics)\b', re.I),
    "ged": re.compile(r'\b(ged|high.?school|diploma|adult education|adult basic education)\b', re.I),
    "literacy": re.compile(r'\b(literacy|literate|reading|adult literacy|basic literacy|family literacy)\b', re.I),
    "youth_tutoring": re.compile(r'\b(youth|after.?school|tutoring|homework help|after.?school tutoring|mentoring|youth programs)\b', re.I),
    "computer_literacy": re.compile(r'\b(computer|digital literacy|computer skills|computer classes|digital|technology)\b', re.I),
    "workforce": re.compile(r'\b(workforce|job training|employment|career|vocational|job readiness|job placement|workforce readiness|workforce development)\b', re.I),
    "financial_literacy": re.compile(r'\b(financial literacy|financial|money management|budgeting)\b', re.I),
    
    # Resettlement/Legal/Shelter subcategories
    "legal": re.compile(r'\b(legal|lawyer|attorney|immigration|asylum|daca|d?a?c?a|family reunification|court|advocacy|legal services|legal assistance)\b', re.I),
    "refugee_resettlement": re.compile(r'\b(refugee resettlement|resettlement|case management|welcoming center)\b', re.I),
    "shelter": re.compile(r'\b(shelter|housing|homeless|emergency housing|emergency shelter|domestic violence shelter|temporary housing)\b', re.I),
    "employment_assistance": re.compile(r'\b(employment|job|job placement|job readiness|job training|job coaching|career|vocational)\b', re.I),
    "benefits": re.compile(r'\b(benefits|snap|food stamps|medicaid|cash assistance|public benefits|enrollment|insurance enrollment)\b', re.I),
    "food": re.compile(r'\b(food|food pantry|pantry|food bank|food distribution|free meals|meals)\b', re.I),
    "crisis": re.compile(r'\b(crisis|hotline|24.?hour|emergency|abuse|neglect)\b', re.I),
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
    """Normalize and categorize services with subcategories."""
    if not services_text:
        return []
    
    services = []
    services_lower = services_text.lower()
    
    # Check all patterns and collect matching subcategories
    for service_type, pattern in SERVICE_PATTERNS.items():
        if pattern.search(services_lower):
            services.append(service_type)
    
    return list(set(services))  # Remove duplicates

def get_availability_badges(services_text: str, name: str = "", address: str = "") -> List[str]:
    """Extract availability badges (Free, Medicaid, Walk-in, etc.) from resource description."""
    badges = []
    if not services_text:
        return badges
    
    text_lower = (services_text + " " + name + " " + address).lower()
    
    # Free services
    if re.search(r'\b(free|no cost|no-cost|complimentary|pro bono|tuition-free)\b', text_lower, re.I):
        badges.append("Free")
    
    # Low cost / Affordable
    if re.search(r'\b(low cost|low-cost|affordable|sliding scale|income-based)\b', text_lower, re.I):
        badges.append("Low Cost")
    
    # Medicaid acceptance
    if re.search(r'\b(medicaid|medicare|insurance|accepts medicaid|medicaid accepted)\b', text_lower, re.I):
        badges.append("Accepts Medicaid")
    
    # Walk-in / No appointment
    if re.search(r'\b(walk.?in|walk in|no appointment|drop.?in|same.?day)\b', text_lower, re.I):
        badges.append("Walk-in")
    
    # Interpreter available
    if re.search(r'\b(interpreter|translation|bilingual|language services|multilingual)\b', text_lower, re.I):
        badges.append("Interpreter Available")
    
    # 24/7 / Emergency
    if re.search(r'\b(24/7|24 hours|always open|emergency|round.?the.?clock)\b', text_lower, re.I):
        badges.append("24/7 Available")
    
    # Appointment required
    if re.search(r'\b(appointment required|call ahead|schedule|booking)\b', text_lower, re.I):
        badges.append("Appointment Required")
    
    return list(set(badges))  # Remove duplicates

def get_subcategories(services_text: str, category: str) -> List[str]:
    """Extract subcategories based on category and services description."""
    if not services_text:
        return []
    
    subcategories = []
    services_lower = services_text.lower()
    
    if category == "Healthcare":
        if re.search(r'\b(family medicine|primary care|internal medicine|general)\b', services_lower, re.I):
            subcategories.append("Primary Care")
        if re.search(r'\b(dental|dentist|oral)\b', services_lower, re.I):
            subcategories.append("Dental")
        if re.search(r'\b(pediatric|children|kids|adolescent|youth)\b', services_lower, re.I):
            subcategories.append("Pediatrics")
        if re.search(r'\b(women|obstetrics|gynecology|ob/gyn|prenatal|midwifery)\b', services_lower, re.I):
            subcategories.append("Women's Health")
        if re.search(r'\b(mental|therapy|counseling|psychiatric|behavioral)\b', services_lower, re.I):
            subcategories.append("Mental Health")
        if re.search(r'\b(mobile|screening|immunization|vaccination)\b', services_lower, re.I):
            subcategories.append("Mobile/Screening Services")
        if re.search(r'\b(hiv|sti|std)\b', services_lower, re.I):
            subcategories.append("HIV/STI Services")
        if re.search(r'\b(nutrition)\b', services_lower, re.I):
            subcategories.append("Nutrition")
        if re.search(r'\b(urgent|emergency|24/7|24 hours)\b', services_lower, re.I):
            subcategories.append("Urgent Care")
        if re.search(r'\b(surgery|podiatry|specialty)\b', services_lower, re.I):
            subcategories.append("Specialty Care")
    
    elif category == "Education":
        if re.search(r'\b(esl|english language|english classes)\b', services_lower, re.I):
            subcategories.append("ESL Classes")
        if re.search(r'\b(citizenship|civics)\b', services_lower, re.I):
            subcategories.append("Citizenship Preparation")
        if re.search(r'\b(ged|high school|diploma|adult education)\b', services_lower, re.I):
            subcategories.append("GED Preparation")
        if re.search(r'\b(literacy|reading)\b', services_lower, re.I):
            subcategories.append("Adult Literacy")
        if re.search(r'\b(youth|after.?school|tutoring|homework help)\b', services_lower, re.I):
            subcategories.append("Youth Tutoring")
        if re.search(r'\b(computer|digital|technology)\b', services_lower, re.I):
            subcategories.append("Computer Literacy")
        if re.search(r'\b(workforce|job training|employment|career|vocational)\b', services_lower, re.I):
            subcategories.append("Workforce Development")
        if re.search(r'\b(financial literacy|financial)\b', services_lower, re.I):
            subcategories.append("Financial Literacy")
    
    elif category == "Resettlement / Legal / Shelter":
        if re.search(r'\b(refugee resettlement|resettlement|case management)\b', services_lower, re.I):
            subcategories.append("Refugee Resettlement")
        if re.search(r'\b(legal|lawyer|attorney|immigration|asylum|daca)\b', services_lower, re.I):
            subcategories.append("Legal Services")
        if re.search(r'\b(shelter|housing|homeless|emergency housing)\b', services_lower, re.I):
            subcategories.append("Emergency Shelter/Housing")
        if re.search(r'\b(employment|job|job placement|job training)\b', services_lower, re.I):
            subcategories.append("Employment Assistance")
        if re.search(r'\b(benefits|snap|medicaid|cash assistance|public benefits)\b', services_lower, re.I):
            subcategories.append("Public Benefits")
        if re.search(r'\b(food|food pantry|food bank|free meals)\b', services_lower, re.I):
            subcategories.append("Food Assistance")
        if re.search(r'\b(domestic violence|abuse|crisis)\b', services_lower, re.I):
            subcategories.append("Crisis Services")
    
    return list(set(subcategories))  # Remove duplicates

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

def parse_blocks(text: str, category: str = "") -> List[Dict[str, Any]]:
    """Parse text blocks into structured records."""
    items = []
    
    # Split by numbered items (format: "1. Name" or "NN. Name")
    # Also handle double newlines as separators
    # First, normalize: split by double newlines OR by numbered item patterns
    text_clean = text.strip()
    
    # Try splitting by numbered items first (more reliable)
    blocks = re.split(r'(?:\n\s*\n+|\n)(?=\d+\.\s)', text_clean)
    
    # If that doesn't work well, fall back to double newlines
    if len(blocks) < 2:
        blocks = re.split(r'\n\s*\n+', text_clean)
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) < 2:
            continue
        
        # Extract name (usually first line, may have "NN. " prefix)
        first_line = lines[0].strip()
        name = re.sub(r'^\d+\.\s*', '', first_line).strip()
        
        # Try to extract item ID from first line if present
        id_match = re.match(r'^(\d+)\.\s', first_line)
        item_id = id_match.group(1) if id_match else f"item_{len(items) + 1}"
        
        # Initialize record
        record = {
            "id": item_id,
            "name": name,
            "address": "",
            "phone": "",
            "phone_digits": "",
            "website": "",
            "zip_code": "",
            "services": [],
            "services_text": "",  # Store original services text
            "subcategories": [],  # Store subcategories
            "availability_badges": [],  # Store availability badges
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
                record["services_text"] = services_text
                record["services"] = normalize_services(services_text)
                # Extract subcategories based on category
                if category:
                    record["subcategories"] = get_subcategories(services_text, category)
                # Extract availability badges
                record["availability_badges"] = get_availability_badges(services_text, record["name"], record["address"])
            
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
                # Handle address with or without emoji
                addr_text = re.sub(r'^(address|📍|location):\s*', '', line, flags=re.I).strip()
                # Also check if line starts with 📍 without colon
                if not addr_text and line.strip().startswith('📍'):
                    addr_text = re.sub(r'^📍\s*', '', line).strip()
                record["address"] = addr_text
                record["zip_code"] = normalize_zip(addr_text)
            
            else:
                # Check if line starts with 📍 emoji (address indicator)
                if line.strip().startswith('📍'):
                    addr_text = re.sub(r'^📍\s*', '', line).strip()
                    record["address"] = addr_text
                    record["zip_code"] = normalize_zip(addr_text)
                # Assume it's address if no keyword found and looks like an address
                elif not record["address"] and len(line) > 10 and ('chicago' in line_lower or 'il' in line_lower or re.search(r'\b(60\d{3})\b', line)):
                    record["address"] = line
                    record["zip_code"] = normalize_zip(line)
        
        # Precompute search blob for fast searching (include subcategories and services text)
        search_fields = [
            record["name"],
            record["address"],
            record["services_text"],  # Include full services text for better semantic matching
            " ".join(record["services"]),
            " ".join(record["subcategories"]),  # Include subcategories
            " ".join(record["languages"]),
            record["hours_text"]
        ]
        record["search_blob"] = " ".join([f for f in search_fields if f]).lower()
        
        items.append(record)
    
    return items

# ===========================
# Cached Data Loading
# ===========================

@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes - always check GitHub for updates
def load_category_data(category: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Load and cache category data with normalization.
    Always fetches from GitHub .txt files as source of truth.
    
    Args:
        category: Category name
        force_refresh: If True, force refresh from GitHub even if JSON exists
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    category_key = category.lower().replace(" / ", "_").replace(" ", "_")
    json_path = data_dir / f"{category_key}.json"
    
    # Always fetch from GitHub first (source of truth)
    sources = DATA_SOURCES.get(category, [])
    
    # Prioritize GitHub URLs
    github_urls = [s for s in sources if s.startswith("http")]
    local_files = [s for s in sources if not s.startswith("http")]
    
    # Try GitHub first, then local fallback
    raw_text = None
    for source in github_urls + local_files:
        try:
            raw_text = fetch_text_from_sources([source])
            if raw_text:
                break
        except:
            continue
    
    if not raw_text:
        # If GitHub fetch fails, try to load from existing JSON
        if json_path.exists() and not force_refresh:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cached JSON: {e}")
        return []
    
    # Parse and normalize from .txt file (source of truth)
    items = parse_blocks(raw_text, category)
    
    # Always save/update JSON from fresh .txt data (GitHub is source of truth)
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"✅ Updated {json_path} from GitHub .txt file ({len(items)} items)")
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


