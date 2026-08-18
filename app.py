import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(
    page_title="Bharat Marketplace - Hyperlocal",
    page_icon="🛍️",
    layout="wide"
)

# -----------------------------------------------------------
# In-Memory Database (Session State for real-time demo)
# -----------------------------------------------------------
if "vendors" not in st.session_state:
    st.session_state.vendors = [
        {
            "id": 1,
            "name": "Nagpur Central Superstore",
            "lat": 21.1458,
            "lon": 79.0882,
            "city": "Nagpur",
            "free_delivery_above_500": True,
            "base_1km": 20,
            "base_2km": 30,
            "per_km_extra": 10
        },
        {
            "id": 2,
            "name": "Dharampeth Auto & Electronics Hub",
            "lat": 21.1400,
            "lon": 79.0600,
            "city": "Nagpur",
            "free_delivery_above_500": False,
            "base_1km": 20,
            "base_2km": 30,
            "per_km_extra": 10
        }
    ]

if "products" not in st.session_state:
    st.session_state.products = [
        {
            "id": 101,
            "vendor_id": 1,
            "brand": "Wagh Bakri",
            "title": "Premium Chai Patti (250g)",
            "category": "Grocery",
            "price": 50.0,
            "desc": "Fresh tea leaves for daily use"
        },
        {
            "id": 102,
            "vendor_id": 1,
            "brand": "Aashirvaad",
            "title": "Shudh Chakki Atta (10kg)",
            "category": "Grocery",
            "price": 420.0,
            "desc": "100% whole wheat flour"
        },
        {
            "id": 103,
            "vendor_id": 2,
            "brand": "Apple",
            "title": "iPhone 15 Pro Max (1TB)",
            "category": "Electronics",
            "price": 179900.0,
            "desc": "Brand new sealed pack with invoice"
        },
        {
            "id": 104,
            "vendor_id": 2,
            "brand": "Royal Enfield",
            "title": "Hunter 350 Dapper Edition",
            "category": "Automobile",
            "price": 175000.0,
            "desc": "Brand new motorcycle booking & fast delivery"
        }
    ]

# -----------------------------------------------------------
# Helper Functions: Distance & Delivery Logic
# -----------------------------------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine road-distance approximation in KM"""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def calculate_delivery_charge(distance_km, item_price, vendor):
    """
    Rules:
    - Distance <= 1 KM: Rs 20
    - Distance <= 2 KM: Rs 30
    - Distance > 2 KM: Rs 30 + Rs 10 per extra km
    - If Cart > 500 & Vendor agrees: FREE Delivery (Rs 0)
    """
    if item_price >= 500 and vendor["free_delivery_above_500"]:
        return 0.0, "FREE Delivery (Above ₹500 Policy)"

    if distance_km <= 1.0:
        return float(vendor["base_1km"]), "₹20 Base Delivery (Within 1 KM)"
    elif distance_km <= 2.0:
        return float(vendor["base_2km"]), "₹30 Delivery (Within 2 KM)"
    else:
        extra_km = distance_km - 2.0
        fee = vendor["base_2km"] + (extra_km * vendor["per_km_extra"])
        return round(fee, 2), f"₹30 + Extra Distance Fee (Total {distance_km} KM)"

# -----------------------------------------------------------
# UI - Header & Mode Switcher
# -----------------------------------------------------------
st.title("🇮🇳 Bharat All-in-One Hyperlocal Platform")
st.caption("₹50 ki Chai se lekar ₹5 Lakh tak ka koi bhi saman — Direct Local Shop se Nearest Delivery & 1% Automated Cut")

mode = st.sidebar.radio("Select Portal / Mode", ["🛍️ Customer Portal (Buy Items)", "🏪 Vendor / Seller Portal (List Items)"])

# ===========================================================
# 1. CUSTOMER PORTAL
# ===========================================================
if mode == "🛍️ Customer Portal (Buy Items)":
    st.subheader("📍 Customer Location & Nearby Market")

    col_loc1, col_loc2, col_loc3 = st.columns(3)
    with col_loc1:
        cust_name = st.text_input("Customer Name", value="Rahul Sharma")
    with col_loc2:
        cust_lat = st.number_input("Customer Latitude (GPS)", value=21.1465, format="%.4f")
    with col_loc3:
        cust_lon = st.number_input("Customer Longitude (GPS)", value=79.0820, format="%.4f")

    st.markdown("---")

    # Search Bar & Filter
    search_query = st.text_input("🔍 Search any product (e.g. Chai, iPhone, Bike, Atta):", value="")

    # Nearby Shop Sorting Algorithm
    matched_items = []
    for prod in st.session_state.products:
        # Search match
        if search_query:
            q = search_query.lower()
            if q not in prod["title"].lower() and q not in prod["brand"].lower() and q not in prod["category"].lower():
                continue

        vendor = next((v for v in st.session_state.vendors if v["id"] == prod["vendor_id"]), None)
        if not vendor:
            continue

        dist = calculate_distance(cust_lat, cust_lon, vendor["lat"], vendor["lon"])
        del_fee, del_reason = calculate_delivery_charge(dist, prod["price"], vendor)

        matched_items.append({
            "product": prod,
            "vendor": vendor,
            "distance": dist,
            "del_fee": del_fee,
            "del_reason": del_reason
        })

    # Sort nearest vendor shop first
    matched_items.sort(key=lambda x: x["distance"])

    st.write(f"Showing **{len(matched_items)}** items near your location (Sorted by nearest road distance):")

    # Display Products in Grid
    if matched_items:
        cols = st.columns(2)
        for i, item in enumerate(matched_items):
            prod = item["product"]
            vendor = item["vendor"]
            dist = item["distance"]
            fee = item["del_fee"]
            fee_text = "FREE" if fee == 0 else f"₹{fee}"

            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"### {prod['brand']} - {prod['title']}")
                    st.markdown(f"**Category:** `{prod['category']}` | **Price:** :green[**₹{prod['price']:,.2f}**]")
                    st.write(f"📝 {prod['desc']}")
                    st.info(f"🏬 **Shop:** {vendor['name']} ({dist} KM away)")
                    st.write(f"🚚 **Estimated Delivery:** `{fee_text}` ({item['del_reason']})")

                    # Order Placement Button
                    if st.button(f"🛒 Order Now - ₹{prod['price']:,.2f}", key=f"btn_{prod['id']}"):
                        st.session_state.current_order = {
                            "customer": cust_name,
                            "product": prod,
                            "vendor": vendor,
                            "distance": dist,
                            "delivery_fee": fee,
                            "delivery_reason": item["del_reason"]
                        }

    # Invoice & Split Calculation Display
    if "current_order" in st.session_state:
        order = st.session_state.current_order
        p = order["product"]
        v = order["vendor"]
        item_val = p["price"]
        del_val = order["delivery_fee"]
        total_bill = item_val + del_val

        # 1% Platform Split Computation
        platform_cut = round(item_val * 0.01, 2)
        vendor_net = round(total_bill - platform_cut, 2)

        st.markdown("---")
        st.success("🎉 Order Processed! Live Invoice & Automated 1% Split Generated:")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🧾 Customer Digital Bill")
            st.write(f"**Customer:** {order['customer']}")
            st.write(f"**Seller:** {v['name']}")
            st.write(f"**Item Purchased:** {p['brand']} {p['title']}")
            st.write(f"**Item Price:** ₹{item_val:,.2f}")
            st.write(f"**Delivery Charges:** {'FREE (₹0.00)' if del_val == 0 else f'₹{del_val:,.2f}'}")
            st.markdown(f"### **Grand Total Paid:** :green[₹{total_bill:,.2f}]")

        with c2:
            st.markdown("### ⚡ Automated Payment Split (Escrow/PG)")
            st.metric("1% Platform Profit (Your Cut)", f"₹{platform_cut:,.2f}", delta="Instant Platform Earn")
            st.metric("Vendor Net Payout (99% + Delivery)", f"₹{vendor_net:,.2f}")
            st.caption("Yeh paisa automated API ke jariye bina kisi manual check ke seedha split ho jata hai.")

# ===========================================================
# 2. VENDOR / SELLER PORTAL
# ===========================================================
else:
    st.subheader("🏪 Vendor / Seller Dashboard")
    st.write("Dukandar yahan ₹50 se ₹5,00,000 tak ka koi bhi saman rate, brand aur delivery policy ke sath publish kar sakte hain.")

    tab1, tab2 = st.tabs(["➕ Add / Publish New Product", "⚙️ Shop & Free Delivery Policy Settings"])

    with tab1:
        with st.form("vendor_add_form"):
            selected_vendor_id = st.selectbox(
                "Select Your Shop",
                options=[v["id"] for v in st.session_state.vendors],
                format_func=lambda x: next(v["name"] for v in st.session_state.vendors if v["id"] == x)
            )

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                p_brand = st.text_input("Brand Name", placeholder="e.g. Tata, Apple, Sony, Local Brand")
                p_title = st.text_input("Product Title", placeholder="e.g. 1kg Sugar, 50-inch Smart TV, Plot Booking")
                p_cat = st.selectbox("Category", ["Grocery", "Electronics", "Automobile", "Fashion", "Real Estate", "Daily Essentials"])
            with col_p2:
                p_price = st.number_input("Product Selling Price (₹50 to ₹5,00,000+)", min_value=50.0, max_value=10000000.0, value=500.0, step=50.0)
                p_desc = st.text_area("Product Details / Specifications", placeholder="Enter full specifications, warranty, or condition details")

            submit_product = st.form_submit_button("🚀 Publish Product on Network (Free Listing)")

            if submit_product:
                if p_brand and p_title:
                    new_item = {
                        "id": len(st.session_state.products) + 101,
                        "vendor_id": selected_vendor_id,
                        "brand": p_brand,
                        "title": p_title,
                        "category": p_cat,
                        "price": float(p_price),
                        "desc": p_desc
                    }
                    st.session_state.products.append(new_item)
                    st.success(f"✅ '{p_brand} - {p_title}' published successfully at ₹{p_price:,.2f}!")
                else:
                    st.error("Please provide both Brand Name and Product Title.")

    with tab2:
        st.write("### Dukandar ki Delivery Policy")
        for v in st.session_state.vendors:
            with st.expander(f"📍 {v['name']} (City: {v['city']})"):
                free_opt = st.toggle(
                    f"Enable FREE Delivery on orders above ₹500 (Dukandar ki Choice)",
                    value=v["free_delivery_above_500"],
                    key=f"free_toggle_{v['id']}"
                )
                v["free_delivery_above_500"] = free_opt

                st.write(f"- 1 KM Delivery Charge: **₹{v['base_1km']}**")
                st.write(f"- 2 KM Delivery Charge: **₹{v['base_2km']}**")
                st.write(f"- >2 KM Per Extra KM: **+₹{v['per_km_extra']}/KM**")
                st.info(f"Current Status: {'Free delivery offered above ₹500' if v['free_delivery_above_500'] else 'Standard distance delivery charges apply always'}")
