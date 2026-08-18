import streamlit as st
import sqlite3
import math
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

# Page Setup
st.set_page_config(
    page_title="Bharat Hyperlocal & High-Value Network",
    page_icon="🛍️",
    layout="wide"
)

DB_NAME = "hyperlocal_market.db"

# -----------------------------------------------------------
# 1. DATABASE SETUP
# -----------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Vendors Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            address TEXT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            free_delivery_above_500 INTEGER DEFAULT 1,
            base_1km REAL DEFAULT 20.0,
            base_2km REAL DEFAULT 30.0,
            per_km_extra REAL DEFAULT 10.0
        )
    ''')

    # Products Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            brand TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id)
        )
    ''')

    # Orders Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            vendor_id INTEGER,
            product_id INTEGER,
            item_price REAL,
            delivery_fee REAL,
            grand_total REAL,
            platform_commission_1pct REAL,
            vendor_net_payout REAL,
            distance_km REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed Default Data
    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO vendors (name, city, address, lat, lon, free_delivery_above_500, base_1km, base_2km, per_km_extra)
            VALUES 
            ('Nagpur Central Mart', 'Nagpur', 'Sitabuldi Main Market', 21.1458, 79.0882, 1, 20.0, 30.0, 10.0),
            ('Dharampeth Auto & Electronic World', 'Nagpur', 'West High Court Road', 21.1400, 79.0600, 0, 20.0, 30.0, 10.0)
        ''')
        c.execute('''
            INSERT INTO products (vendor_id, brand, title, category, price, description)
            VALUES 
            (1, 'Tata Tea', 'Tata Tea Premium 250g', 'Grocery', 50.0, 'Fresh daily morning tea'),
            (1, 'Fortune', 'Refined Sunflower Oil 5L', 'Grocery', 680.0, 'Pure cooking oil pack'),
            (2, 'Apple', 'iPhone 15 Pro Max 1TB', 'Electronics', 179900.0, 'Brand new sealed smartphone'),
            (2, 'Mahindra / Dealer', 'Commercial Vehicle Advance Token', 'Automobile', 50000.0, 'Express booking advance token')
        ''')
    
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------
# 2. DISTANCE & DELIVERY LOGIC
# -----------------------------------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def get_delivery_fee(distance_km, item_price, free_allowed, base_1km, base_2km, per_km_extra):
    if item_price >= 500 and free_allowed == 1:
        return 0.0, "FREE Delivery (Above ₹500 Policy)"
    if distance_km <= 1.0:
        return float(base_1km), f"₹{base_1km:.0f} (Within 1 KM)"
    elif distance_km <= 2.0:
        return float(base_2km), f"₹{base_2km:.0f} (Within 2 KM)"
    else:
        extra_km = distance_km - 2.0
        fee = base_2km + (extra_km * per_km_extra)
        return round(fee, 2), f"₹{base_2km:.0f} + Extra Distance ({distance_km} KM)"

# -----------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------
st.sidebar.title("🇮🇳 Bharat Hyperlocal")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Portal",
    "🏪 Vendor / Seller Panel",
    "🏬 Register New Shop",
    "📊 Platform Earnings & Ledger"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER PORTAL
# -----------------------------------------------------------
if menu == "🛍️ Customer Portal":
    st.subheader("📍 Customer Live Location & Hyperlocal Search")
    
    # Auto GPS detection
    live_loc = get_geolocation()
    detected_lat = 21.1458
    detected_lon = 79.0882
    if live_loc and 'coords' in live_loc:
        detected_lat = live_loc['coords']['latitude']
        detected_lon = live_loc['coords']['longitude']
        st.success(f"📍 GPS Location Auto-Detected: `{detected_lat:.4f}, {detected_lon:.4f}`")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        cust_name = st.text_input("Customer Name", value="Rahul Sharma")
    with c2:
        cust_lat = st.number_input("Customer Latitude", value=float(detected_lat), format="%.4f")
    with c3:
        cust_lon = st.number_input("Customer Longitude", value=float(detected_lon), format="%.4f")

    search_query = st.text_input("🔍 Search any product (e.g. Chai, iPhone, Oil, Sugar):", "")

    # Fetch inventory from DB
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT p.id, p.brand, p.title, p.category, p.price, p.description,
               v.id as vendor_id, v.name as vendor_name, v.lat, v.lon, v.free_delivery_above_500,
               v.base_1km, v.base_2km, v.per_km_extra
        FROM products p
        JOIN vendors v ON p.vendor_id = v.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        if search_query:
            q = search_query.lower()
            if q not in row["title"].lower() and q not in row["brand"].lower() and q not in row["category"].lower():
                continue

        dist = calculate_distance(cust_lat, cust_lon, row["lat"], row["lon"])
        fee, fee_desc = get_delivery_fee(
            dist, row["price"], row["free_delivery_above_500"],
            row["base_1km"], row["base_2km"], row["per_km_extra"]
        )

        results.append({
            "p_id": row["id"],
            "brand": row["brand"],
            "title": row["title"],
            "category": row["category"],
            "price": row["price"],
            "desc": row["description"],
            "v_id": row["vendor_id"],
            "v_name": row["vendor_name"],
            "v_lat": row["lat"],
            "v_lon": row["lon"],
            "distance": dist,
            "delivery_fee": fee,
            "fee_desc": fee_desc
        })

    # Nearest seller sorting
    results.sort(key=lambda x: x["distance"])

    st.write(f"Found **{len(results)}** items near your location (Nearest Shop First):")

    if results:
        # Live Map Display
        m = folium.Map(location=[cust_lat, cust_lon], zoom_start=13)
        folium.Marker([cust_lat, cust_lon], popup="Your Location (Customer)", icon=folium.Icon(color="blue", icon="user")).add_to(m)
        for item in results:
            folium.Marker(
                [item["v_lat"], item["v_lon"]],
                popup=f"{item['v_name']} ({item['distance']} KM)",
                icon=folium.Icon(color="green", icon="shopping-cart")
            ).add_to(m)
        
        st_folium(m, height=280, use_container_width=True)

        cols = st.columns(2)
        for idx, item in enumerate(results):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### {item['brand']} - {item['title']}")
                    st.markdown(f"**Category:** `{item['category']}` | **Price:** :green[**₹{item['price']:,.2f}**]")
                    st.write(f"📝 {item['desc']}")
                    st.info(f"🏬 **Shop:** {item['v_name']} ({item['distance']} KM away)")
                    
                    del_display = "FREE" if item['delivery_fee'] == 0 else f"₹{item['delivery_fee']:,.2f}"
                    st.write(f"🚚 **Delivery Charge:** `{del_display}` ({item['fee_desc']})")

                    if st.button(f"🛒 Order Now (₹{item['price']:,.2f})", key=f"btn_order_{item['p_id']}"):
                        item_total = item["price"]
                        del_fee = item["delivery_fee"]
                        grand_total = item_total + del_fee
                        cut_1pct = round(item_total * 0.01, 2)
                        vendor_cut = round(grand_total - cut_1pct, 2)

                        conn_o = sqlite3.connect(DB_NAME)
                        cur = conn_o.cursor()
                        cur.execute('''
                            INSERT INTO orders (customer_name, vendor_id, product_id, item_price, delivery_fee, grand_total, platform_commission_1pct, vendor_net_payout, distance_km)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (cust_name, item["v_id"], item["p_id"], item_total, del_fee, grand_total, cut_1pct, vendor_cut, item["distance"]))
                        conn_o.commit()
                        order_id = cur.lastrowid
                        conn_o.close()

                        st.session_state.current_bill = {
                            "order_id": order_id,
                            "cust": cust_name,
                            "item": f"{item['brand']} - {item['title']}",
                            "shop": item["v_name"],
                            "price": item_total,
                            "fee": del_fee,
                            "total": grand_total,
                            "cut": cut_1pct,
                            "payout": vendor_cut
                        }

    # Invoice and Split Box
    if "current_bill" in st.session_state:
        b = st.session_state.current_bill
        st.markdown("---")
        st.success(f"🎉 Order #{b['order_id']} Processed Successfully!")
        
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            st.markdown("### 🧾 Customer Digital Bill")
            st.write(f"**Customer:** {b['cust']}")
            st.write(f"**Store:** {b['shop']}")
            st.write(f"**Item:** {b['item']}")
            st.write(f"**Item Amount:** ₹{b['price']:,.2f}")
            st.write(f"**Delivery:** ₹{b['fee']:,.2f}")
            st.markdown(f"### **Total Paid:** :green[₹{b['total']:,.2f}]")
            
        with col_inv2:
            st.markdown("### ⚡ Automated Split Execution")
            st.metric("Platform Cut (1% Pure Profit)", f"₹{b['cut']:,.2f}", delta="Your SaaS Cut")
            st.metric("Vendor Net Settle (99% + Delivery)", f"₹{b['payout']:,.2f}")
            st.caption("Paisa Escrow API ke zariye automated transfer hota hai.")

# -----------------------------------------------------------
# TAB 2: VENDOR / SELLER PANEL
# -----------------------------------------------------------
elif menu == "🏪 Vendor / Seller Panel":
    st.subheader("🏪 Vendor Catalog & Policy Management")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    if vendors_df.empty:
        st.warning("Pehle 'Register New Shop' se dukan add karein.")
    else:
        v_tab1, v_tab2 = st.tabs(["➕ Add Product to Shop", "⚙️ Store Delivery Preferences"])
        
        with v_tab1:
            with st.form("product_upload_form"):
                shop_id = st.selectbox(
                    "Select Store",
                    vendors_df["id"].tolist(),
                    format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0]
                )
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    p_brand = st.text_input("Brand Name", placeholder="e.g. Parle, Sony, Royal Enfield")
                    p_title = st.text_input("Product Title", placeholder="e.g. 500g Biscuit, 65-inch OLED TV")
                    p_category = st.selectbox("Category", ["Grocery", "Electronics", "Automobile", "Real Estate", "Daily Essentials", "Fashion"])
                with col_p2:
                    p_price = st.number_input("Selling Price (₹50 to ₹5,00,000+)", min_value=50.0, max_value=10000000.0, value=500.0, step=50.0)
                    p_desc = st.text_area("Detailed Specs & Description")

                p_submit = st.form_submit_button("🚀 Publish Product (Free)")
                if p_submit:
                    if p_brand and p_title:
                        conn_p = sqlite3.connect(DB_NAME)
                        cur = conn_p.cursor()
                        cur.execute('''
                            INSERT INTO products (vendor_id, brand, title, category, price, description)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (shop_id, p_brand, p_title, p_category, p_price, p_desc))
                        conn_p.commit()
                        conn_p.close()
                        st.success(f"✅ '{p_brand} - {p_title}' published at ₹{p_price:,.2f}!")
                        st.rerun()

        with v_tab2:
            st.write("### Delivery Threshold Controls")
            for _, v in vendors_df.iterrows():
                with st.expander(f"📍 {v['name']} ({v['city']})"):
                    toggle_free = st.toggle(
                        "Offer FREE Delivery above ₹500 Orders",
                        value=bool(v["free_delivery_above_500"]),
                        key=f"pref_{v['id']}"
                    )
                    if st.button("Save Settings", key=f"btn_save_{v['id']}"):
                        conn_s = sqlite3.connect(DB_NAME)
                        cur = conn_s.cursor()
                        cur.execute("UPDATE vendors SET free_delivery_above_500 = ? WHERE id = ?", (1 if toggle_free else 0, v["id"]))
                        conn_s.commit()
                        conn_s.close()
                        st.success("Preferences updated!")
                        st.rerun()

# -----------------------------------------------------------
# TAB 3: REGISTER NEW SHOP (Self-Onboarding)
# -----------------------------------------------------------
elif menu == "🏬 Register New Shop":
    st.subheader("🏬 Self-Serve Store Onboarding (PAN-India)")
    st.caption("Kisi bhi gaon, kasbe ya shahar ka dukandar apni dukan yahan turant register kar sakta hai.")

    with st.form("new_shop_form"):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            shop_name = st.text_input("Shop / Enterprise Name", placeholder="e.g. Nagpur Traders")
            city = st.text_input("City / District", placeholder="e.g. Nagpur, Amravati, Pune")
            address = st.text_input("Full Address / Landmark")
        with col_s2:
            lat = st.number_input("Shop GPS Latitude", value=21.1450, format="%.4f")
            lon = st.number_input("Shop GPS Longitude", value=79.0800, format="%.4f")
            free_delivery = st.checkbox("Enable Free Delivery on orders above ₹500 by default", value=True)

        st.markdown("#### Delivery Pricing Rules")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            base_1 = st.number_input("Within 1 KM Fee (₹)", value=20.0)
        with col_d2:
            base_2 = st.number_input("Within 2 KM Fee (₹)", value=30.0)
        with col_d3:
            per_km = st.number_input("Per Extra KM after 2 KM (₹)", value=10.0)

        submit_shop = st.form_submit_button("✅ Register Shop Online")
        if submit_shop:
            if shop_name and city:
                conn_ns = sqlite3.connect(DB_NAME)
                cur = conn_ns.cursor()
                cur.execute('''
                    INSERT INTO vendors (name, city, address, lat, lon, free_delivery_above_500, base_1km, base_2km, per_km_extra)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (shop_name, city, address, lat, lon, 1 if free_delivery else 0, base_1, base_2, per_km))
                conn_ns.commit()
                conn_ns.close()
                st.success(f"🎉 Store '{shop_name}' registered successfully! Ab aap saman list kar sakte hain.")
            else:
                st.error("Dukan ka naam aur shahar zaroori hai.")

# -----------------------------------------------------------
# TAB 4: PLATFORM EARNINGS & LEDGER
# -----------------------------------------------------------
else:
    st.subheader("📊 Platform Revenue & 1% Automated Cut Ledger")
    conn = sqlite3.connect(DB_NAME)
    orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    conn.close()

    total_gross = orders_df["item_price"].sum() if not orders_df.empty else 0.0
    total_commission = orders_df["platform_commission_1pct"].sum() if not orders_df.empty else 0.0
    total_count = len(orders_df)

    m1, m2, m3 = st.columns(3)
    m1.metric("Gross Turnover (All Items)", f"₹{total_gross:,.2f}")
    m2.metric("Platform 1% Pure Profit", f"₹{total_commission:,.2f}", delta="Instant Software Revenue")
    m3.metric("Total Successful Orders", total_count)

    st.markdown("---")
    st.write("### 📜 Real-time Transactions & Settlement Log")
    if not orders_df.empty:
        st.dataframe(orders_df[[
            "id", "customer_name", "item_price", "delivery_fee",
            "grand_total", "platform_commission_1pct", "vendor_net_payout", "created_at"
        ]], use_container_width=True)
    else:
        st.info("Abhi tak koi order nahi hua hai. Customer Portal se order test karein.")
