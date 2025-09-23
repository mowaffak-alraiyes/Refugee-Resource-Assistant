#!/usr/bin/env python3
"""
Enhanced UI components with click-to-call, directions, and better mobile support.
"""

import streamlit as st
import urllib.parse
from typing import Dict, Any, List
import search

# ===========================
# Card Components
# ===========================

def render_enhanced_card(index: int, item: Dict[str, Any], category: str) -> None:
    """Render an enhanced resource card with micro-actions."""
    
    with st.container():
        st.markdown(f"### {index}. {item.get('name', 'Unknown')}")
        
        # Main content
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Address with click-to-map
            if item.get("address"):
                map_url = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(item['address'])}"
                st.markdown(f"📍 **Where to find them:** [{item['address']}]({map_url})")
            
            # Phone with click-to-call
            if item.get("phone"):
                phone_digits = item.get("phone_digits", "")
                if phone_digits:
                    st.markdown(f"📞 **Call them:** [{item['phone']}](tel:{phone_digits})")
                else:
                    st.markdown(f"📞 **Call them:** {item['phone']}")
            
            # Website with new tab
            if item.get("website"):
                st.markdown(f"🌐 **Check them out online:** [{item['website']}]({item['website']})")
            
            # Services
            if item.get("services"):
                services_text = ", ".join(item["services"])
                st.markdown(f"🛠️ **Services:** {services_text}")
            
            # Languages
            if item.get("languages"):
                languages_text = ", ".join(item["languages"])
                st.markdown(f"🗣️ **Languages:** {languages_text}")
            
            # Hours with open now indicator
            if item.get("hours_text"):
                hours_text = item["hours_text"]
                if search.is_open_now(item):
                    st.markdown(f"⏰ **When they're open:** {hours_text} 🟢 **OPEN NOW**")
                else:
                    next_open = search.get_next_open_time(item)
                    if next_open:
                        st.markdown(f"⏰ **When they're open:** {hours_text} (Next: {next_open})")
                    else:
                        st.markdown(f"⏰ **When they're open:** {hours_text}")
        
        with col2:
            # Micro-actions
            st.markdown("**Quick Actions:**")
            
            # Call button
            if item.get("phone_digits"):
                if st.button("📞 Call", key=f"call_{category}_{item['id']}", help="Click to call"):
                    st.markdown(f"[Call {item['phone']}](tel:{item['phone_digits']})")
            
            # Directions button
            if item.get("address"):
                if st.button("🗺️ Directions", key=f"dir_{category}_{item['id']}", help="Get directions"):
                    map_url = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(item['address'])}"
                    st.markdown(f"[Get Directions]({map_url})")
            
            # Website button
            if item.get("website"):
                if st.button("🌐 Website", key=f"web_{category}_{item['id']}", help="Visit website"):
                    st.markdown(f"[Visit Website]({item['website']})")
            
            # Pin/Unpin button
            pinned_now = is_pinned(category, item["id"])
            label = "📌 Unpin" if pinned_now else "📌 Pin"
            if st.button(label, key=f"pin_{category}_{item['id']}", help="Pin/unpin this resource"):
                toggle_pin(category, item)
                st.rerun()
            
            # Copy buttons
            if st.button("📋 Copy Address", key=f"copy_addr_{category}_{item['id']}", help="Copy address"):
                st.code(item.get("address", ""))
            
            if item.get("phone"):
                if st.button("📋 Copy Phone", key=f"copy_phone_{category}_{item['id']}", help="Copy phone number"):
                    st.code(item.get("phone", ""))
        
        st.divider()

# ===========================
# Pin Management
# ===========================

def is_pinned(category: str, item_id: str) -> bool:
    """Check if an item is pinned."""
    pinned = st.session_state.get("pinned", [])
    return any(p["id"] == item_id and p["category"] == category for p in pinned)

def toggle_pin(category: str, item: Dict[str, Any]) -> None:
    """Toggle pin status of an item."""
    pinned = st.session_state.get("pinned", [])
    
    # Check if already pinned
    for i, p in enumerate(pinned):
        if p["id"] == item["id"] and p["category"] == category:
            # Unpin
            pinned.pop(i)
            st.session_state["pinned"] = pinned
            return
    
    # Pin
    pinned.append({
        "id": item["id"],
        "category": category,
        "name": item.get("name", "Unknown"),
        "address": item.get("address", ""),
        "phone": item.get("phone", ""),
        "website": item.get("website", ""),
        "services": item.get("services", []),
        "languages": item.get("languages", []),
    })
    st.session_state["pinned"] = pinned

def render_pinned_sidebar() -> None:
    """Render pinned items in sidebar."""
    pinned = st.session_state.get("pinned", [])
    
    if not pinned:
        st.info("No pinned resources yet. Pin resources you want to save!")
        return
    
    st.subheader("📌 Pinned Resources")
    
    for i, item in enumerate(pinned):
        with st.expander(f"{item['name']} ({item['category']})"):
            st.markdown(f"**Address:** {item['address']}")
            if item['phone']:
                st.markdown(f"**Phone:** {item['phone']}")
            if item['website']:
                st.markdown(f"**Website:** {item['website']}")
            
            # Quick actions for pinned items
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Remove", key=f"remove_pin_{i}"):
                    pinned.pop(i)
                    st.session_state["pinned"] = pinned
                    st.rerun()
            
            with col2:
                if st.button("📋 Copy", key=f"copy_pin_{i}"):
                    copy_text = f"{item['name']}\n{item['address']}"
                    if item['phone']:
                        copy_text += f"\n{item['phone']}"
                    st.code(copy_text)
    
    # Export pinned items
    if st.button("📤 Export Pins"):
        export_pins()

def export_pins() -> None:
    """Export pinned items to CSV/JSON."""
    pinned = st.session_state.get("pinned", [])
    
    if not pinned:
        st.warning("No pinned items to export!")
        return
    
    # CSV format
    csv_data = "Name,Category,Address,Phone,Website,Services,Languages\n"
    for item in pinned:
        services = "; ".join(item.get("services", []))
        languages = "; ".join(item.get("languages", []))
        csv_data += f'"{item["name"]}","{item["category"]}","{item["address"]}","{item["phone"]}","{item["website"]}","{services}","{languages}"\n'
    
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name="pinned_resources.csv",
        mime="text/csv"
    )
    
    # JSON format
    import json
    json_data = json.dumps(pinned, indent=2)
    st.download_button(
        label="📥 Download JSON",
        data=json_data,
        file_name="pinned_resources.json",
        mime="application/json"
    )

# ===========================
# Enhanced Filters
# ===========================

def render_enhanced_filters(category: str, items: List[Dict[str, Any]]) -> tuple:
    """Render enhanced filter controls."""
    
    # Extract unique values from items
    all_zips = sorted(set(item.get("zip_code", "") for item in items if item.get("zip_code")))
    all_langs = sorted(set(lang for item in items for lang in item.get("languages", [])))
    all_services = sorted(set(service for item in items for service in item.get("services", [])))
    
    # Get available days from hours data
    all_days = set()
    for item in items:
        hours = item.get("hours", {})
        all_days.update(hours.keys())
    all_days = sorted(all_days)
    
    # Filter options
    zip_options = ["All"] + all_zips
    lang_options = ["All"] + all_langs
    service_options = ["All"] + all_services
    day_options = ["All"] + all_days
    
    # Render filters
    st.subheader("🔍 Filters")
    
    col1, col2 = st.columns(2)
    with col1:
        zip_filter = st.selectbox("ZIP Code:", zip_options, key=f"zip_{category}")
        lang_filter = st.selectbox("Language:", lang_options, key=f"lang_{category}")
    
    with col2:
        service_filter = st.selectbox("Service:", service_options, key=f"service_{category}")
        day_filter = st.selectbox("Day:", day_options, key=f"day_{category}")
    
    # Smart filter info
    detected_filters = []
    if st.session_state.get(f"detected_zip_{category}"):
        detected_filters.append(f"ZIP {st.session_state[f'detected_zip_{category}']}")
    if st.session_state.get(f"detected_service_{category}"):
        detected_filters.append(f"service {st.session_state[f'detected_service_{category}']}")
    if st.session_state.get(f"detected_day_{category}"):
        detected_filters.append(f"day {st.session_state[f'detected_day_{category}']}")
    
    if detected_filters:
        st.info(f"🔍 **Smart filtering:** Auto-detected {', '.join(detected_filters)}")
    
    return zip_filter, lang_filter, service_filter, day_filter

# ===========================
# QR Code Section
# ===========================

def render_qr_section() -> None:
    """Render QR code section in sidebar."""
    st.subheader("📱 Quick Access")
    
    # Get app URL
    try:
        app_public_url = st.secrets.get("APP_PUBLIC_URL", None)
        qr_url = app_public_url if app_public_url else "http://192.168.1.186:8502"
    except:
        qr_url = "http://192.168.1.186:8502"
    
    # Generate QR code
    try:
        import qrcode
        import io
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        st.image(img_bytes, caption="Scan to access app")
        
        # Download button
        st.download_button(
            label="📥 Download QR Code",
            data=img_bytes.getvalue(),
            file_name="app_qr_code.png",
            mime="image/png"
        )
        
        if app_public_url:
            st.success("🌐 Public URL configured")
        else:
            st.info("🏠 Local network URL")
            
    except Exception as e:
        st.error(f"QR code generation failed: {e}")

# ===========================
# Mobile-Friendly Components
# ===========================

def render_mobile_friendly_category_selector() -> None:
    """Render mobile-friendly category selector."""
    st.markdown("""
    <style>
    /* Mobile-friendly radio buttons */
    div[role="radiogroup"] > div {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        justify-content: center;
    }
    
    div[role="radiogroup"] label {
        border: 2px solid var(--primary-color, #4f46e5);
        padding: 0.75rem 1.25rem;
        border-radius: 25px;
        cursor: pointer;
        font-weight: 600;
        user-select: none;
        min-width: 120px;
        text-align: center;
        transition: all 0.2s ease;
    }
    
    div[role="radiogroup"] label:hover {
        background-color: var(--primary-color, #4f46e5);
        color: white;
    }
    
    div[role="radiogroup"] label[data-checked="true"] {
        background: var(--primary-color, #4f46e5);
        color: white !important;
    }
    
    /* Mobile-friendly buttons */
    .mobile-btn button {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        min-height: 44px; /* iOS recommended touch target */
    }
    
    /* Responsive cards */
    .resource-card {
        margin-bottom: 1rem;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background: white;
    }
    
    @media (max-width: 768px) {
        .resource-card {
            margin: 0.5rem 0;
            padding: 0.75rem;
        }
        
        div[role="radiogroup"] label {
            min-width: 100px;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def render_pagination_controls(total_results: int, shown_count: int) -> bool:
    """Render pagination controls. Returns True if user wants more results."""
    if total_results <= shown_count:
        return False
    
    remaining = total_results - shown_count
    st.info(f"Showing {shown_count} of {total_results} results. {remaining} more available.")
    
    if st.button("📄 Show More Results", key="show_more"):
        return True
    
    return False
