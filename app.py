import streamlit as st
import requests
import re
import qrcode
import io
import uuid
import database as db
from typing import List, Dict, Tuple

# ===========================
# Page & Styles
# ===========================
st.set_page_config(page_title="Community Resources Chat", layout="wide")

# Initialize database
db.initialize_database()

st.title("💬 Community Resources Chat")

# Radio -> big buttons that stay highlighted when chosen
st.markdown("""
<style>
/* Make segmented category control look like big pill buttons */
div[role="radiogroup"] > div{
  display:flex; gap:0.75rem; flex-wrap:wrap;
}
div[role="radiogroup"] label{
  border:2px solid var(--primary-color,#4f46e5);
  padding:0.6rem 1.0rem; border-radius:9999px;
  cursor:pointer; font-weight:600; user-select:none;
}
div[role="radiogroup"] label[data-checked="true"]{
  background:var(--primary-color,#4f46e5); color:white !important;
}

/* Make inline "Pin" buttons compact */
.small-btn button {
  padding: 0.25rem 0.5rem;
  font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# ===========================
# Constants
# ===========================
TOP_N = 3  # show first N; user can type "more" to fetch next batch

# URL Configuration for QR Code
LOCAL_URL = "http://192.168.1.186:8501"  # Fallback for testing on local network

def get_app_public_url():
    """Safely get the public URL from secrets, with fallback to None."""
    try:
        return st.secrets.get("APP_PUBLIC_URL", None)
    except:
        return None

# Common misspellings with suggested corrections
MISSPELLING_SUGGESTIONS = {
    # Healthcare misspellings
    "dentall": "dental",
    "dentel": "dental", 
    "dentle": "dental",
    "pediatrik": "pediatric",
    "pediatrik": "pediatric",
    "terapy": "therapy",
    "theraphy": "therapy",
    "klinik": "clinic",
    "clinik": "clinic",
    
    # Education misspellings
    "inglish": "english",
    "skool": "school",
    "klas": "class",
    
    # Legal/Shelter misspellings
    "leagal": "legal",
    "leagle": "legal",
    "imigration": "immigration",
    "asilum": "asylum",
    
    # Common word misspellings
    "halp": "help",
    "nead": "need",
    "faind": "find",
    "neer": "near",
    "cloes": "close",
}

DATA_SOURCES = {
    "Healthcare": [
        "https://raw.githubusercontent.com/mowaffak-alraiyes/refugee-resources/main/resources/healthcare.txt",
        "/mnt/data/Healthcare Resources.txt",
    ],
    "Education": [
        "https://raw.githubusercontent.com/mowaffak-alraiyes/refugee-resources/main/resources/education.txt",
        "/mnt/data/Education Resources.txt",
        "/mnt/data/Education Resources (1).txt",
    ],
    "Resettlement / Legal / Shelter": [
        "https://raw.githubusercontent.com/mowaffak-alraiyes/refugee-resources/main/resources/ResettlementLegalShelterBasicNeeds.txt",
        "/mnt/data/Resettlement Legal Shelter Needs.txt",
        "/mnt/data/Resettlement Legal Shelter Needs (1).txt",
    ],
}

BASE_SYNONYMS = {
    "common": {
        "bilingual": {"bilingual","spanish","mandarin","arabic","polish","urdu","cantonese","taiwanese","hindi","yoruba","kannada","tamil","french","swahili","tigrinya","ukrainian"},
        "hours": {"hours","open","closing","time","times","schedule"},
        "address": {"address","where","location"},
        "phone": {"phone","number","call","contact"},
        "website": {"website","site","link"},
    },
    "Healthcare": {
        "dental": {"dental","dentist","teeth","tooth","oral","mouth"},
        "pediatric": {"pediatric","pediatrics","children","child","kid","kids","adolescent","youth"},
        "women": {"women","woman","female","obgyn","ob/gyn","ob-gyn","ob gyn","prenatal","midwifery","obstetrics","gynecology"},
        "mental": {"behavioral","mental","counseling","counselor","therapy","therapist","psychiatry","psychiatric"},
        "primary": {"primary","family","internal medicine","family medicine","adult"},
        "immunization": {"immunization","immunizations","vaccination","vaccinations","shots","vaccine","vaccines"},
    },
    "Education": {
        "esl": {"esl","english","language","tutoring","classes","citizenship","ged","literacy","after-school","after school","youth"},
    },
    "Resettlement / Legal / Shelter": {
        "legal": {"legal","law","attorney","immigration","asylum","daca","family reunification"},
        "shelter": {"shelter","housing","emergency","homeless"},
        "benefits": {"benefits","snap","medicaid","cash assistance","311","food","pantry"},
        "resettlement": {"resettlement","case management","employment","job readiness","welcoming center"},
    },
}

# ===========================
# Utilities
# ===========================
def fetch_text_from_sources(sources: List[str]) -> str:
    last_err = None
    for src in sources:
        try:
            if src.startswith("http"):
                r = requests.get(src, timeout=20)
                r.raise_for_status()
                if r.text.strip():
                    return r.text
            else:
                with open(src, "r", encoding="utf-8") as f:
                    text = f.read()
                    if text.strip():
                        return text
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Failed to load dataset from any source. Last error: {last_err}")

def first_match(pat: str, text: str) -> str:
    m = re.search(pat, text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else ""

def parse_blocks(resource_text: str) -> List[Dict]:
    # Split each numbered block "NN. Name"
    blocks = re.split(r"\n(?=\d+\.\s)|\A(?=\d+\.\s)", resource_text.strip())
    out = []
    for blk in blocks:
        if not blk.strip():
            continue
        m = re.match(r"^\s*(\d+)\.\s+(.+)", blk.strip(), flags=re.MULTILINE)
        if m:
            item_id = m.group(1).strip()
            name = m.group(2).strip()
        else:
            first_line = blk.strip().splitlines()[0].strip()
            item_id = str(len(out) + 1)
            name = re.sub(r"^\s*\d+\.\s*", "", first_line)

        address   = first_match(r"📍\s*(.+)", blk)
        website   = first_match(r"🌐\s*(https?://\S+)", blk)
        languages = first_match(r"🗣\s*Languages:\s*(.+)", blk)
        # Multiple emoji fallbacks for Services
        services  = (first_match(r"(?:🏥|🛟|🛠️|🧰)\s*Services:\s*(.+)", blk) or 
                    first_match(r"Services:\s*(.+)", blk))
        # Multiple fallbacks for Hours
        hours     = (first_match(r"⏰\s*Hours:\s*(.+)", blk) or 
                    first_match(r"Hours:\s*(.+)", blk))
        # Multiple fallbacks for Phone
        phone     = (first_match(r"📞\s*(.+)", blk) or 
                    first_match(r"Phone:\s*(.+)", blk) or
                    first_match(r"📞\s*Phone:\s*(.+)", blk))
        # Search for zip in full block if address is missing
        zip_code  = first_match(r"\b(60\d{3})\b", address or blk)

        out.append({
            "id": item_id,
            "name": name,
            "address": address,
            "zip": zip_code,
            "website": website,
            "languages": languages,
            "services": services,
            "hours": hours,
            "phone": phone,
            "_search_blob": " ".join([name or "", address or "", languages or "", services or ""]).lower(),
        })
    return out

def detect_misspellings(query: str) -> List[Tuple[str, str]]:
    """Detect misspellings in the query and return (misspelled_word, suggested_correction) pairs."""
    if not query:
        return []
    
    suggestions = []
    words = query.lower().split()
    
    for word in words:
        if word in MISSPELLING_SUGGESTIONS:
            suggestions.append((word, MISSPELLING_SUGGESTIONS[word]))
    
    return suggestions

def detect_zip_from_query(query: str) -> str:
    """Auto-detect ZIP code from search query and return it if found."""
    # Look for 5-digit ZIP codes (60xxx format for Chicago area)
    zip_match = re.search(r'\b(60\d{3})\b', query)
    if zip_match:
        return zip_match.group(1)
    return None

def clean_query_of_zip(query: str) -> str:
    """Remove ZIP code from query text to avoid double-counting in search."""
    # Remove 5-digit ZIP codes from query
    cleaned = re.sub(r'\b(60\d{3})\b', '', query)
    # Clean up extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def detect_service_from_query(query: str, category: str) -> str:
    """Auto-detect service type from search query and return it if found."""
    query_lower = query.lower()
    
    # Healthcare services
    if category == "Healthcare":
        if any(word in query_lower for word in ["dental", "dentist", "teeth", "tooth", "oral"]):
            return "dental"
        elif any(word in query_lower for word in ["pediatric", "children", "child", "kid", "kids", "youth"]):
            return "pediatric"
        elif any(word in query_lower for word in ["mental", "counseling", "therapy", "psychiatry"]):
            return "mental health"
        elif any(word in query_lower for word in ["women", "obgyn", "prenatal", "midwifery"]):
            return "women's health"
        elif any(word in query_lower for word in ["immunization", "vaccination", "shots", "vaccine"]):
            return "immunization"
    
    # Education services
    elif category == "Education":
        if any(word in query_lower for word in ["esl", "english", "language", "tutoring", "classes"]):
            return "ESL"
        elif any(word in query_lower for word in ["ged", "citizenship", "literacy"]):
            return "GED/Citizenship"
        elif any(word in query_lower for word in ["after-school", "after school", "youth"]):
            return "Youth Programs"
    
    # Legal/Shelter services
    elif category == "Resettlement / Legal / Shelter":
        if any(word in query_lower for word in ["legal", "law", "attorney", "immigration", "asylum", "daca"]):
            return "Legal Services"
        elif any(word in query_lower for word in ["shelter", "housing", "emergency", "homeless"]):
            return "Shelter/Housing"
        elif any(word in query_lower for word in ["benefits", "snap", "medicaid", "cash assistance"]):
            return "Benefits Assistance"
        elif any(word in query_lower for word in ["resettlement", "case management", "employment", "job"]):
            return "Resettlement Services"
    
    return None

def detect_day_from_query(query: str) -> str:
    """Auto-detect day of week from search query and return it if found."""
    query_lower = query.lower()
    
    days = {
        "monday": "Monday", "mon": "Monday",
        "tuesday": "Tuesday", "tue": "Tuesday", "tues": "Tuesday",
        "wednesday": "Wednesday", "wed": "Wednesday",
        "thursday": "Thursday", "thu": "Thursday", "thurs": "Thursday",
        "friday": "Friday", "fri": "Friday",
        "saturday": "Saturday", "sat": "Saturday",
        "sunday": "Sunday", "sun": "Sunday"
    }
    
    for day_key, day_value in days.items():
        if day_key in query_lower:
            return day_value
    
    return None

def generate_qr_code(url: str) -> bytes:
    """Generate a QR code for the given URL and return as PNG bytes."""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"Failed to generate QR code: {e}")
        return None

def parse_day_ranges(hours_text: str) -> List[str]:
    """Parse day ranges like 'Mon-Thu' or 'Mon, Wed, Fri' and return list of individual days."""
    hours_lower = hours_text.lower()
    available_days = []
    
    # Day mapping for abbreviations
    day_map = {
        "mon": "Monday", "tue": "Tuesday", "tues": "Tuesday", "wed": "Wednesday",
        "thu": "Thursday", "thurs": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"
    }
    
    # Look for day ranges like "Mon-Thu" or "Mon - Thu"
    range_pattern = r'\b(mon|tue|tues|wed|thu|thurs|fri|sat|sun)\s*[-–]\s*(mon|tue|tues|wed|thu|thurs|fri|sat|sun)\b'
    range_matches = re.findall(range_pattern, hours_lower)
    
    for start_day, end_day in range_matches:
        start_idx = list(day_map.keys()).index(start_day)
        end_idx = list(day_map.keys()).index(end_day)
        
        # Handle wrapping around (e.g., Fri-Mon)
        if start_idx <= end_idx:
            day_range = list(day_map.keys())[start_idx:end_idx + 1]
        else:
            day_range = list(day_map.keys())[start_idx:] + list(day_map.keys())[:end_idx + 1]
        
        for day in day_range:
            available_days.append(day_map[day])
    
    # Look for individual days or comma-separated lists
    individual_pattern = r'\b(mon|tue|tues|wed|thu|thurs|fri|sat|sun)\b'
    individual_matches = re.findall(individual_pattern, hours_lower)
    
    for day in individual_matches:
        if day_map[day] not in available_days:  # Avoid duplicates
            available_days.append(day_map[day])
    
    # Look for full day names
    full_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for full_day in full_days:
        if full_day in hours_lower and full_day.capitalize() not in available_days:
            available_days.append(full_day.capitalize())
    
    return available_days

def is_day_available_in_dataset(day: str, items: List[Dict]) -> bool:
    """Check if a specific day is actually available in the dataset."""
    if not day or day == "All":
        return False
    
    day_lower = day.lower()
    for item in items:
        hours = item.get("hours", "")
        if hours:
            # Use the smart parsing to get all available days
            available_days = parse_day_ranges(hours)
            # Check if the requested day is in the available days
            if day in available_days:
                return True
    
    return False

def clean_query_of_service_and_day(query: str, detected_service: str = None, detected_day: str = None) -> str:
    """Remove detected service and day from query text to avoid double-counting in search."""
    cleaned = query
    
    if detected_service:
        # Remove service-related words
        service_words = detected_service.lower().split()
        for word in service_words:
            cleaned = re.sub(rf'\b{re.escape(word)}\b', '', cleaned, flags=re.IGNORECASE)
    
    if detected_day:
        # Remove day-related words
        day_words = detected_day.lower().split()
        for word in day_words:
            cleaned = re.sub(rf'\b{re.escape(word)}\b', '', cleaned, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def expand_terms(query: str, category: str) -> List[str]:
    q = (query or "").lower()
    words = set(re.findall(r"[a-zA-Z]+", q))
    expanded = set(words)

    cat_syns = {}
    cat_syns.update(BASE_SYNONYMS.get("common", {}))
    cat_syns.update(BASE_SYNONYMS.get(category, {}))
    for key, syns in cat_syns.items():
        if (key in words) or (words & syns):
            expanded |= syns
            expanded.add(key)
    return sorted(expanded)

def must_have_patterns(terms: List[str], category: str) -> List[re.Pattern]:
    """If user asked for a specific service, require it to appear in Services text."""
    pats = []
    t = set(terms)
    if category == "Healthcare":
        if {"dental","dentist","oral","tooth","teeth"} & t:
            pats.append(re.compile(r"\b(dental|dentist|oral)\b"))
        if {"pediatric","children","youth","adolescent","kid","kids"} & t:
            pats.append(re.compile(r"\b(pediatric|children|youth|adolescent)\b"))
    if category == "Resettlement / Legal / Shelter":
        if {"legal","immigration","asylum","daca"} & t:
            pats.append(re.compile(r"\b(legal|immigration|asylum|daca)\b"))
        if {"shelter","housing","homeless","emergency"} & t:
            pats.append(re.compile(r"\b(shelter|housing|emergency)\b"))
    if category == "Education":
        if {"esl","english","literacy","ged","citizenship"} & t:
            pats.append(re.compile(r"\b(esl|english|literacy|ged|citizenship)\b"))
    return pats

def rank_items(items: List[Dict], query: str, category: str, zip_filter: str, lang_filter: str, service_filter: str = "All", day_filter: str = "All") -> List[Tuple[int, Dict]]:
    terms = expand_terms(query, category)
    require = must_have_patterns(terms, category)

    ranked = []
    for c in items:
        # ZIP filter
        if zip_filter != "All" and c.get("zip") and c["zip"] != zip_filter:
            continue
        # Language filter
        if lang_filter != "All":
            langs = (c.get("languages") or "").lower()
            if lang_filter.lower() not in langs:
                continue
        # Service filter
        if service_filter != "All":
            services = (c.get("services") or "").lower()
            if service_filter.lower() not in services:
                continue
        # Day filter
        if day_filter != "All":
            hours = c.get("hours") or ""
            if hours:
                # Use smart parsing to get available days
                available_days = parse_day_ranges(hours)
                if day_filter not in available_days:
                    continue
            else:
                # No hours data, skip this item
                continue

        blob = c["_search_blob"]
        svc = (c.get("services") or "").lower()

        # If user asked for specific service(s), require them in Services
        if require and not all(p.search(svc) for p in require):
            continue

        # Base score + small bonuses
        score = sum(1 for t in terms if t in blob) if terms else 1
        if re.search(r"\b(dental|dentist|oral)\b", query, re.I) and re.search(r"\b(dental|dentist|oral)\b", svc):
            score += 2
        if re.search(r"\b(pediatric|children|youth|adolescent)\b", query, re.I) and re.search(r"\b(pediatric|children|youth|adolescent)\b", svc):
            score += 2
        if re.search(r"\b(legal|immigration|asylum|daca)\b", query, re.I) and re.search(r"\b(legal|immigration|asylum|daca)\b", svc):
            score += 2
        if re.search(r"\b(esl|english|literacy|ged|citizenship)\b", query, re.I) and re.search(r"\b(esl|english|literacy|ged|citizenship)\b", svc):
            score += 2
        if re.search(r"\b(shelter|housing|emergency)\b", query, re.I) and re.search(r"\b(shelter|housing|emergency)\b", svc):
            score += 2

        if score > 0:
            ranked.append((score, c))

    ranked.sort(key=lambda x: (-x[0], x[1]["name"]))
    return ranked

def is_pinned(cat_key: str, item_id: str) -> bool:
    return any(p["cat"] == cat_key and p["id"] == item_id for p in st.session_state["pinned"])

def toggle_pin(cat_key: str, item: Dict):
    """Toggle pin state for an item. Returns True if pinned, False if unpinned."""
    current_pinned = st.session_state.get("pinned", [])
    
    # Check if already pinned
    existing_index = None
    for i, p in enumerate(current_pinned):
        if p["cat"] == cat_key and p["id"] == item["id"]:
            existing_index = i
            break
    
    if existing_index is not None:
        # Unpin: remove from list
        current_pinned.pop(existing_index)
        st.session_state["pinned"] = current_pinned
        return False
    else:
        # Pin: add to list
        pin_data = {
            "cat": cat_key, 
            "id": item["id"], 
            "name": item["name"], 
            "website": item.get("website")
        }
        st.session_state["pinned"] = current_pinned + [pin_data]
        return True

def friendly_intro(category: str, query: str, zip_filter: str, lang_filter: str, service_filter: str = "All", day_filter: str = "All", detected_zip: str = None, detected_service: str = None, detected_day: str = None) -> str:
    # Warm, conversational intro that explains what we looked for and invites next step
    parts = [f"Great question! I looked for **{category}** resources matching **'{query.strip()}'**."]
    f = []
    
    # Show auto-detected ZIP first if it exists
    if detected_zip:
        f.append(f"ZIP **{detected_zip}** (auto-detected from your search)")
    elif zip_filter != "All":
        f.append(f"ZIP **{zip_filter}**")
    
    # Show auto-detected service if it exists
    if detected_service:
        f.append(f"service **{detected_service}** (auto-detected from your search)")
    elif service_filter != "All":
        f.append(f"service **{service_filter}**")
    
    # Show auto-detected day if it exists
    if detected_day:
        f.append(f"day **{detected_day}** (auto-detected from your search)")
    elif day_filter != "All":
        f.append(f"day **{day_filter}**")
    
    if lang_filter != "All": 
        f.append(f"language **{lang_filter}**")
    
    if f: 
        parts.append("I'm using these filters: " + ", ".join(f) + ".")
    
    parts.append("Here are a few good fits. Want more? Type **more**. If you'd like, tell me your ZIP, service, day, or language preference and I'll narrow it down.")
    return " ".join(parts)

def render_card(idx: int, item: Dict, cat_key: str):
    # Add friendly personality to the clinic display
    emoji = "🏥" if "health" in cat_key.lower() else "🎓" if "education" in cat_key.lower() else "🏠"
    st.markdown(f"### {emoji} **{idx}. {item['name']}**")
    
    # small inline pin toggle
    col1, col2 = st.columns([1, 9])
    with col1:
        pinned_now = is_pinned(cat_key, item["id"])
        btn_label = "📌 Unpin" if pinned_now else "📌 Pin"
        # Use a unique key that includes the current state to prevent conflicts
        if st.button(btn_label, key=f"pin_{cat_key}_{item['id']}_{idx}_{pinned_now}"):
            toggle_pin(cat_key, item)
            # Force a clean rerun after pin state change
            st.rerun()

    with col2:
        # print full details inline (no expander) with friendly language
        if item.get("address"):   st.markdown(f"**📍 Where to find them:** {item['address']}")
        if item.get("website"):   st.markdown(f"**🌐 Check them out online:** {item['website']}")
        if item.get("phone"):     st.markdown(f"**📞 Give them a call:** {item['phone']}")
        if item.get("languages"): st.markdown(f"**🗣 They speak:** {item['languages']}")
        if item.get("services"):  st.markdown(f"**🏥 What they offer:** {item['services']}")
        if item.get("hours"):     st.markdown(f"**⏰ When they're open:** {item['hours']}")

# ===========================
# Session State
# ===========================
st.session_state.setdefault("category", "Healthcare")
st.session_state.setdefault("datasets_cache", {})
st.session_state.setdefault("messages", [])  # [{"role":"user","text":...}, {"role":"assistant","text"/"render":...}]
st.session_state.setdefault("pinned", [])
st.session_state.setdefault("last_query_by_cat", {})
st.session_state.setdefault("shown_ids_by_cat", {})
st.session_state.setdefault("scroll_flag", False)
st.session_state.setdefault("misspelling_suggestion", None)
st.session_state.setdefault("waiting_for_misspelling_response", False)

# Initialize conversation ID for database logging
if "convo_id" not in st.session_state:
    st.session_state["convo_id"] = uuid.uuid4().hex[:12]

# ===========================
# Sidebar: Pins & Filters
# ===========================
with st.sidebar:
    st.markdown("### 📌 Pinned")
    if st.session_state["pinned"]:
        for i, p in enumerate(st.session_state["pinned"], 1):
            if p.get("website"):
                st.markdown(f"**{i}. {p['name']}**  \n{p['website']}")
            else:
                st.markdown(f"**{i}. {p['name']}**")
    else:
        st.caption("No items pinned yet.")

    st.markdown("---")
    st.subheader("📂 Filters")

# ===========================
# Category selector (radio-as-buttons that stays highlighted)
# ===========================
cat_choice = st.radio(
    "Choose a category to search:",
    ["Healthcare", "Education", "Resettlement / Legal / Shelter"],
    horizontal=True,
    index=["Healthcare", "Education", "Resettlement / Legal / Shelter"].index(st.session_state["category"]),
    key="category"
)

# ===========================
# Load dataset
# ===========================
def get_dataset(cat_key: str) -> Tuple[List[Dict], str]:
    if cat_key in st.session_state["datasets_cache"]:
        return st.session_state["datasets_cache"][cat_key]
    text = fetch_text_from_sources(DATA_SOURCES[cat_key])
    items = parse_blocks(text)
    st.session_state["datasets_cache"][cat_key] = (items, text)
    return items, text

try:
    items, raw_text = get_dataset(st.session_state["category"])
except Exception as e:
    st.error(f"⚠️ Could not load the **{st.session_state['category']}** dataset. Check the GitHub/raw path or local fallback.\n\n{e}")
    st.stop()

# Build filter options from the loaded dataset
all_zips = sorted(set(re.findall(r"\b60\d{3}\b", raw_text)))
lang_lines = re.findall(r"🗣\s*Languages:\s*(.+)", raw_text)
langs = set()
for line in lang_lines:
    for lang in re.split(r"[;,]", line):
        lang = lang.strip()
        if lang and not lang.lower().startswith("and"):
            langs.add(lang)
all_langs = sorted(langs)

# Build service filter options based on category
service_options = ["All"]
if cat_choice == "Healthcare":
    service_options.extend(["dental", "pediatric", "mental health", "women's health", "immunization", "primary care"])
elif cat_choice == "Education":
    service_options.extend(["ESL", "GED/Citizenship", "Youth Programs", "Tutoring", "Literacy"])
elif cat_choice == "Resettlement / Legal / Shelter":
    service_options.extend(["Legal Services", "Shelter/Housing", "Benefits Assistance", "Resettlement Services"])

# Build day of week filter options from actual hours data
day_options = ["All"]
available_days = set()

# Extract available days from hours data using smart parsing
for item in items:
    hours = item.get("hours", "")
    if hours:
        # Use the new smart parsing function
        days_found = parse_day_ranges(hours)
        for day in days_found:
            available_days.add(day)

# Add available days to options, sorted
day_options.extend(sorted(available_days))

# Tip about auto-detection features (now that day_options is defined)
if len(day_options) > 1:
    tip_text = "💡 **Pro tip:** You can include ZIP codes, services, or days in your search (e.g., 'dental 60629', 'ESL monday', 'legal help mon', 'clinic tue-thu') and I'll automatically filter!"
else:
    tip_text = "💡 **Pro tip:** You can include ZIP codes or services in your search (e.g., 'dental 60629', 'ESL programs', 'legal help') and I'll automatically filter!"

with st.sidebar:
    zip_filter = st.selectbox("Filter by ZIP:", ["All"] + all_zips, key=f"zip_{cat_choice}")
    lang_filter = st.selectbox("Filter by Language:", ["All"] + all_langs, key=f"lang_{cat_choice}")
    service_filter = st.selectbox("Filter by Service:", service_options, key=f"service_{cat_choice}")
    
    # Only show day filter if there are actual days found in the dataset
    if len(day_options) > 1:  # More than just "All"
        day_filter = st.selectbox("Filter by Day:", day_options, key=f"day_{cat_choice}")
    else:
        day_filter = "All"  # Default to "All" if no days found
    
    # Display the tip about auto-detection features
    st.info(tip_text)
    
    # QR Code section for easy app access
    st.markdown("---")
    st.subheader("📱 Quick Access")
    
    # Determine which URL to use for QR code
    app_public_url = get_app_public_url()
    qr_url = app_public_url if app_public_url else LOCAL_URL
    
    if app_public_url:
        st.success("🌐 Public URL configured - QR code links to public app")
    else:
        st.info("🏠 Local network URL - QR code for same Wi-Fi access")
    
    # Generate and display QR code
    qr_bytes = generate_qr_code(qr_url)
    if qr_bytes:
        # Display QR code as image
        st.image(qr_bytes, caption="Scan to open the app", width=200)
        
        # Download button for QR code
        st.download_button(
            label="📥 Download QR Code",
            data=qr_bytes,
            file_name="community-resources-app.png",
            mime="image/png"
        )
    else:
        st.error("Failed to generate QR code")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔁 Reset Chat", key="reset_chat"):
            st.session_state["messages"] = []
            st.session_state["pinned"] = []
            st.session_state["shown_ids_by_cat"] = {}
            st.session_state["last_query_by_cat"] = {}
            st.session_state["misspelling_suggestion"] = None
            st.session_state["waiting_for_misspelling_response"] = False
            # Clear datasets cache to force fresh fetch
            st.session_state["datasets_cache"] = {}
            # New API (no deprecation warning)
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.rerun()
    with c2:
        if st.button("⏬ Scroll to Latest", key="scroll_latest"):
            st.session_state["scroll_flag"] = True



# ===========================
# Response function definition
# ===========================
def respond_to_query(user_text: str, category: str):
    is_more = user_text.strip().lower() == "more"

    # 2) Decide query (user message already added outside this function)
    if is_more:
        query = st.session_state["last_query_by_cat"].get(category, "")
    else:
        query = user_text
        if category == "Healthcare":
            query = re.sub(r"\bclinic(s)?\b", "", query, flags=re.IGNORECASE)
        st.session_state["last_query_by_cat"][category] = query

    # 3) Auto-detect ZIP, service, and day from query and apply filtering
    detected_zip = None
    detected_service = None
    detected_day = None
    
    if not is_more:
        detected_zip = detect_zip_from_query(query)
        detected_service = detect_service_from_query(query, category)
        detected_day = detect_day_from_query(query)
        
        # Only use detected day if it's actually available in the dataset
        if detected_day and not is_day_available_in_dataset(detected_day, items):
            detected_day = None
        
        if detected_zip or detected_service or detected_day:
            # Clean the query to avoid double-counting
            query = clean_query_of_service_and_day(query, detected_service, detected_day)
            if detected_zip:
                query = clean_query_of_zip(query)
            st.session_state["last_query_by_cat"][category] = query
    
    # 4) Rank with current filters (auto-detected values take priority over sidebar)
    zf = detected_zip or st.session_state.get(f"zip_{category}", "All") or "All"
    lf = st.session_state.get(f"lang_{category}", "All") or "All"
    sf = detected_service or st.session_state.get(f"service_{category}", "All") or "All"
    df = detected_day or st.session_state.get(f"day_{category}", "All") or "All"
    
    ranked = rank_items(items, query, category, zf, lf, sf, df)

    # 4) Exclude already shown if 'more'
    shown_map = st.session_state["shown_ids_by_cat"]
    prev_ids = set(shown_map.get(category, []))
    fresh = [c for _, c in ranked if c["id"] not in prev_ids]
    to_show = fresh[:TOP_N]

    # 5) Assistant reply (friendly/proactive + cards)
    with st.chat_message("assistant"):
        if to_show:
            intro = friendly_intro(category, query, zf, lf, sf, df, detected_zip, detected_service, detected_day)
            st.markdown(intro)
            
            # Show confidence with result count
            if len(to_show) > 0:
                st.success(f"✨ I found **{len(to_show)}** great options for you!")
            
            # Show auto-detected filters info if applicable
            detected_filters = []
            if detected_zip:
                detected_filters.append(f"ZIP code **{detected_zip}**")
            if detected_service:
                detected_filters.append(f"service **{detected_service}**")
            if detected_day:
                detected_filters.append(f"day **{detected_day}**")
            
            if detected_filters:
                st.info(f"🔍 **Smart filtering:** I automatically detected {', '.join(detected_filters)} from your search and applied those filters!")
            
            ids = [c["id"] for c in to_show]
            shown_map[category] = list(prev_ids | set(ids))
            for i, c in enumerate(to_show, 1):
                render_card(i, c, category)

            # friendly nudge to refine
            st.info(
                "💡 **Pro tip:** Want to find something more specific? Try filtering by ZIP code, language, or service type (like dental, pediatrics, GED, legal)! "
                "Or just type **more** to see additional options. I'm confident these are great matches for you! 🎯"
            )
            
            # Proactive follow-up suggestions
            st.info(
                "Want to narrow it down further? Tell me your ZIP, preferred language, service type (e.g., dental, ESL, legal), or day of the week (e.g., monday, friday)."
            )

            # Persist assistant block
            st.session_state["messages"].append({
                "role": "assistant",
                "render": "cards",
                "category": category,
                "results": to_show,
                "text": intro
            })
            
            # Log assistant message to database
            def summarize_results(results):
                lines = []
                for r in results:
                    name = r.get("name") or "Unknown"
                    addr = r.get("address") or ""
                    phone = r.get("phone") or ""
                    lines.append(f"{name} | {addr} | {phone}")
                return "\n".join(lines[:10])
            
            reply_text = summarize_results(to_show)
            reply_json = {"category": category, "results": to_show}
            db.save_assistant_message(
                convo_id=st.session_state["convo_id"],
                reply_text=reply_text,
                reply_json=reply_json,
                category=category
            )
            
            # Auto-scroll to bottom after successful response
            st.session_state["scroll_flag"] = True
        else:
            if is_more:
                st.markdown(
                    "🎯 _That's all the additional matching items I found! But don't stop here - you can also check these trusted national resources: "
                    "[FindHelp.org](https://www.findhelp.org), "
                    "[211.org](https://www.211.org), or "
                    "[HRSA Health Center Locator](https://findahealthcenter.hrsa.gov/). "
                    "Feel free to ask me about other services or locations!_"
                )
                
                # Encourage trying different search terms
                st.markdown(
                    "**💡 Try searching for a different service type or location - I might have more options for you!**"
                )
            else:
                # Friendly fallback for general questions or non-dataset help
                st.markdown(
                    "😔 I couldn't find a match for that in this dataset, but don't worry! "
                    "I'm here to help you figure out what you need. "
                    "For official listings nearby, try these trusted resources: "
                    "[FindHelp.org](https://www.findhelp.org), "
                    "[211.org](https://www.211.org), or "
                    "[HRSA Health Center Locator](https://findahealthcenter.hrsa.gov/). "
                    "Feel free to ask me about other services or locations!"
                )
                
                # Add helpful follow-up for general questions
                st.markdown(
                    "**I can help you look up programs from our local lists. Tell me a service (e.g., dental, ESL, legal) and a ZIP or neighborhood. "
                    "For broader help, try the resources above.**"
                )
            st.session_state["messages"].append({
                "role": "assistant",
                "text": "No matches in dataset (see national resources above)."
            })
            
            # Log assistant message to database (no results case)
            reply_text = "No matches in dataset (see national resources above)."
            reply_json = {"category": category, "results": []}
            db.save_assistant_message(
                convo_id=st.session_state["convo_id"],
                reply_text=reply_text,
                reply_json=reply_json,
                category=category
            )
            
            # Auto-scroll to bottom after response (even if no results)
            st.session_state["scroll_flag"] = True

# ===========================
# Chat input (always visible)
# ===========================
prompt = st.chat_input(
    f"💬 What {st.session_state['category']} resources are you looking for? (e.g., 'dental 60629', 'ESL monday', 'legal help mon', 'clinic tue-thu')…"
)

# ===========================
# Re-render previous chat
# ===========================
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("render") == "cards":
            # assistant intro text (friendlier)
            if msg.get("text"):
                st.markdown(msg["text"])
            for i, item in enumerate(msg["results"], 1):
                render_card(i, item, msg["category"])
            st.caption("💡 Want to see more options? Just type **more**!")
        else:
            st.markdown(msg.get("text", ""))

# ===========================
# Show current user input immediately (if any)
# ===========================
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Add user message to session state for chat history
    st.session_state["messages"].append({"role": "user", "text": prompt})
    
    # Log user message to database
    db.save_user_message(
        convo_id=st.session_state["convo_id"],
        query_text=prompt,
        category=st.session_state["category"],
        user_label=None
    )
    
    # Check if we're waiting for a response to a misspelling suggestion
    if st.session_state.get("waiting_for_misspelling_response", False):
        # User is responding to a "Did you mean X?" question
        if prompt.lower() in ["yes", "y", "yeah", "sure", "ok", "okay"]:
            # User confirmed the suggestion
            suggestion = st.session_state.get("misspelling_suggestion")
            if suggestion:
                with st.chat_message("assistant"):
                    st.info(f"✅ Perfect! Let me search for **{suggestion}** for you.")
                # Clear the misspelling state
                st.session_state["misspelling_suggestion"] = None
                st.session_state["waiting_for_misspelling_response"] = False
                # Search with the corrected term
                respond_to_query(suggestion, st.session_state["category"])
        elif prompt.lower() in ["no", "n", "nope", "not really"]:
            # User rejected the suggestion
            with st.chat_message("assistant"):
                st.info("🤔 No worries at all! Let me help you find what you need. Could you tell me a bit more about what you're looking for? For example:")
                st.markdown("- What type of service do you need?")
                st.markdown("- Are you looking for something else?")
                st.markdown("- Any other details that might help me find the right resources?")
            # Clear the misspelling state
            st.session_state["misspelling_suggestion"] = None
            st.session_state["waiting_for_misspelling_response"] = False
        else:
            # User gave a different response, treat as new query
            st.session_state["misspelling_suggestion"] = None
            st.session_state["waiting_for_misspelling_response"] = False
            respond_to_query(prompt, st.session_state["category"])
    else:
        # Check for misspellings in new query
        misspelling_suggestions = detect_misspellings(prompt)
        
        if misspelling_suggestions:
            # Found misspellings, ask "Did you mean X?"
            misspelled_word, suggested_correction = misspelling_suggestions[0]  # Take first suggestion
            
            # Create the corrected query
            corrected_query = prompt.lower().replace(misspelled_word, suggested_correction)
            
            with st.chat_message("assistant"):
                st.info(f"🤔 Hey there! I think you might have meant **{suggested_correction}** instead of **{misspelled_word}**?")
                st.markdown(f"**If that's right, your search would be:** {corrected_query}")
                st.markdown("**Just let me know - is that what you were looking for? (yes/no)**")
            
            # Set state to wait for user response
            st.session_state["misspelling_suggestion"] = corrected_query
            st.session_state["waiting_for_misspelling_response"] = True
            
            # Add to chat history
            st.session_state["messages"].append({
                "role": "assistant",
                "text": f"Asked if user meant '{suggested_correction}' instead of '{misspelled_word}'"
            })
        else:
            # No misspellings, process normally
            respond_to_query(prompt, st.session_state["category"])
    
    # Auto-scroll to bottom after response
    st.session_state["scroll_flag"] = True
    # Add immediate spacing to trigger scroll
    st.write("\n" * 30)

# Auto-scroll to bottom after new content
if st.session_state.get("scroll_flag"):
    # Force scroll to bottom by adding substantial spacing
    # This pushes the viewport down to show the latest content
    st.write("\n" * 150)
    st.session_state["scroll_flag"] = False
