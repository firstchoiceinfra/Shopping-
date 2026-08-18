import streamlit as st
import sqlite3
import math
import pandas as pd

# Page setup
st.set_page_config(
    page_title="Bharat All-in-One Hyperlocal Platform",
    page_icon="🛍️",
    layout="wide"
)

# -----------------------------------------------------------
# 1. DATABASE INITIALIZATION (SQLite Persistent DB)
# -----------------------------------------------------------
DB_NAME = "hyperlocal_market.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Vendors Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            free_delivery_above_500 INTEGER DEFAULT 1,
            base_1km REAL DEFAULT 20.0,
            base_2km REAL DEFAULT 30.0,
            per_km_extra REAL DEFAULT 10.0
        )
    ''')

    # Products Table (Supports Rs 50 to Rs 5 Lakhs+)
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

    # Orders & 1% Split Table
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
    
    # Seed default shops and items if empty
    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO vendors (name, city, lat, lon, free_delivery_above_500, base_1km, base_2km, per_km_extra)
            VALUES 
            ('Nagpur Central Mart', 'Nagpur', 21.1458, 79.0882, 1, 20.0, 30.0, 10.0),
            ('Dharampeth Auto & Electronic World', 'Nagpur', 21.1400, 79.0600, 0, 20.0, 30.0, 10.0)
        ''')
        
        c.execute('''
            INSERT INTO products (vendor_id, brand, title, category, price, description)
            VALUES 
            (1, 'Tata Tea', 'Tata Tea Premium 250g', 'Grocery', 50.0, 'Fresh aromatic daily tea leaves'),
            (1, 'Fortune', 'Fortune Sunflower Oil 5L', 'Grocery', 680.0, 'Pure refined cooking oil'),
            (2, 'Apple', 'iPhone 15 Pro Max 1TB', 'Electronics', 179900.0, 'Original sealed pack with 1-year warranty'),
            (2, 'Mahindra / Dealership', 'Vehicle Booking Advance', 'Automobile', 50000.0, 'Instant showroom delivery booking token')
        ''')
    
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------
# 2. LOGIC: DISTANCE & DELIVERY CHARGE ENGINE
# -----------------------------------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculates road distance approximation in KM"""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def get_delivery_fee(distance_km, item_price, free_allowed, base_1km, base_2km, per_km_extra):
    """
    Rules:
    - <= 1 KM: Rs 20
    - <= 2 KM: Rs 30
    - > 2 KM: Rs 30 + Rs 10 per extra km
    - If Cart >= Rs 500 & Vendor allows: FREE Delivery (Rs 0)
    """
    if item_price >= 500 and free_allowed == 1:
        return 0.0, "FREE Delivery (Order Above ₹500 Shop Policy)"
    
    if distance_km <= 1.0:
        return float(base_1km), f"₹{base_1km:.0f} Base Delivery (Within 1 KM)"
    elif distance_km <= 2.0:
        return float(base_2km), f"₹{base_2km:.0f} Delivery (Within 2 KM)"
    else:
        extra_km = distance_km - 2.0
        fee = base_2km + (extra_km * per_km_extra)
        return round(fee, 2), f"₹{base_2km:.0f} + Extra Distance (Total {distance_km} KM)"

# -----------------------------------------------------------
# 3. USER INTERFACE & NAVIGATION
# -----------------------------------------------------------
st.title("🇮🇳 Bharat All-in-One Hyperlocal Marketplace")
st.caption("₹50 ki Chai se ₹5 Lakh tak ka koi bhi saman | Nearest Shop Discovery | Automated 1% Platform Split")

menu = st.sidebar.radio("Select Portal", [
    "🛍️ Customer Marketplace", 
    "🏪 Vendor / Shopkeeper Dashboard", 
    "📊 Platform Admin & Earnings"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER MARKETPLACE
# -----------------------------------------------------------
if menu == "🛍️ Customer Marketplace":
    st.subheader("📍 Your Live Location & Local Market")
    
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    with col_c1:
        cust_name = st.text_input("Customer Name", value="Rahul Sharma")
    with col_c2:
        cust_lat = st.number_input("Your Latitude (GPS)", value=21.1465, format="%.4f")
    with col_c3:
        cust_lon = st.number_input("Your Longitude (GPS)", value=79.0820, format="%.4f")

    st.markdown("---")
    search_query = st.text_input("🔍 Search any item (e.g. Chai, iPhone, Oil, Booking, Sugar):", "")

    # Fetch products and vendor coordinates from SQLite
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT p.id, p.brand, p.title, p.category, p.price, p.description,
               v.id, v.name, v.lat, v.lon, v.free_delivery_above_500, v.base_1km, v.base_2km, v.per_km_extra
        FROM products p
        JOIN vendors v ON p.vendor_id = v.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        # Search Filter
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
            "v_name": row["name"],
            "distance": dist,
            "delivery_fee": fee,
            "fee_desc": fee_desc
        })

    # Sort nearest vendor shop first
    results.sort(key=lambda x: x["distance"])

    st.write(f"Showing **{len(results)}** available products near you:")

    if results:
        cols = st.columns(2)
        for idx, item in enumerate(results):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### {item['brand']} - {item['title']}")
                    st.markdown(f"**Category:** `{item['category']}` | **Price:** :green[**₹{item['price']:,.2f}**]")
                    st.write(f"📝 {item['desc']}")
                    st.info(f"🏬 **Shop:** {item['v_name']} ({item['distance']} KM away)")
                    
                    del_display = "FREE" if item['delivery_fee'] == 0 else f"₹{item['delivery_fee']:,.2f}"
                    st.write(f"🚚 **Delivery:** `{del_display}` ({item['fee_desc']})")

                    if st.button(f"🛒 Buy Now (₹{item['price']:,.2f})", key=f"buy_{item['p_id']}"):
                        # Process Order
                        item_total = item["price"]
                        del_fee = item["delivery_fee"]
                        grand_total = item_total + del_fee
                        cut_1pct = round(item_total * 0.01, 2)
                        vendor_cut = round(grand_total - cut_1pct, 2)

                        # Insert into DB
                        c_conn = sqlite3.connect(DB_NAME)
                        cur = c_conn.cursor()
                        cur.execute('''
                            INSERT INTO orders (customer_name, vendor_id, product_id, item_price, delivery_fee, grand_total, platform_commission_1pct, vendor_net_payout, distance_km)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (cust_name, item["v_id"], item["p_id"], item_total, del_fee, grand_total, cut_1pct, vendor_cut, item["distance"]))
                        c_conn.commit()
                        order_id = cur.lastrowid
                        c_conn.close()

                        st.session_state.last_order = {
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

    # Invoice and Commission Split Block
    if "last_order" in st.session_state:
        ord_info = st.session_state.last_order
        st.markdown("---")
        st.success(f"✅ Order #{ord_info['order_id']} Placed Successfully!")
        
        inv1, inv2 = st.columns(2)
        with inv1:
            st.markdown("### 🧾 Customer Digital Invoice")
            st.write(f"**Customer:** {ord_info['cust']}")
            st.write(f"**Shop Name:** {ord_info['shop']}")
            st.write(f"**Item:** {ord_info['item']}")
            st.write(f"**Product Price:** ₹{ord_info['price']:,.2f}")
            st.write(f"**Delivery Charge:** ₹{ord_info['fee']:,.2f}")
            st.markdown(f"### **Total Amount Paid:** :green[₹{ord_info['total']:,.2f}]")
        
        with inv2:
            st.markdown("### ⚡ Automated 1% Platform Split")
            st.metric("1% Platform Income", f"₹{ord_info['cut']:,.2f}", delta="Your Commission")
            st.metric("Vendor Settle Payout", f"₹{ord_info['payout']:,.2f}", delta="Transferred to Shop")
            st.caption("Yeh paisa instant webhook / escrow payment splitter se transfer hota hai.")

# -----------------------------------------------------------
# TAB 2: VENDOR DASHBOARD
# -----------------------------------------------------------
elif menu == "🏪 Vendor / Shopkeeper Dashboard":
    st.subheader("🏪 Shopkeeper & Listing Panel")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    v_tab1, v_tab2 = st.tabs(["➕ Add New Product (₹50 to ₹5 Lakh+)", "⚙️ Delivery Policy & Store Settings"])

    with v_tab1:
        with st.form("add_product_form"):
            selected_shop = st.selectbox(
                "Select Your Store", 
                vendors_df["id"].tolist(), 
                format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0]
            )
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                brand = st.text_input("Brand Name", placeholder="e.g. Samsung, Amul, Mahindra, Local")
                title = st.text_input("Product Title", placeholder="e.g. 100g Butter, 4K TV, 1000 Sqft Plot")
                category = st.selectbox("Category", ["Grocery", "Electronics", "Automobile", "Real Estate", "Daily Essentials", "Clothing"])
            with col_b2:
                price = st.number_input("Selling Price (₹50 to ₹5,00,000+)", min_value=50.0, max_value=10000000.0, value=500.0, step=50.0)
                description = st.text_area("Full Description & Specs")

            submit_btn = st.form_submit_button("🚀 Publish Product (Free Listing)")

            if submit_btn:
                if brand and title:
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT INTO products (vendor_id, brand, title, category, price, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (selected_shop, brand, title, category, price, description))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ '{brand} - {title}' has been listed at ₹{price:,.2f}!")
                    st.rerun()
                else:
                    st.error("Please fill in Brand and Title.")

    with v_tab2:
        st.write("### Dukandar Delivery Settings")
        for _, v in vendors_df.iterrows():
            with st.expander(f"📍 {v['name']} ({v['city']})"):
                is_free = st.toggle(
                    "Free Delivery above ₹500 Enabled", 
                    value=bool(v["free_delivery_above_500"]), 
                    key=f"toggle_{v['id']}"
                )
                if st.button("Save Policy", key=f"save_btn_{v['id']}"):
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("UPDATE vendors SET free_delivery_above_500 = ? WHERE id = ?", (1 if is_free else 0, v["id"]))
                    conn.commit()
                    conn.close()
                    st.success("Delivery policy updated successfully!")
                    st.rerun()

# -----------------------------------------------------------
# TAB 3: ADMIN & COMMISSION METRICS
# -----------------------------------------------------------
else:
    st.subheader("📊 Platform Revenue & PAN-India Metrics")
    conn = sqlite3.connect(DB_NAME)
    orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    conn.close()

    total_turnover = orders_df["item_price"].sum() if not orders_df.empty else 0.0
    total_platform_cut = orders_df["platform_commission_1pct"].sum() if not orders_df.empty else 0.0
    total_orders = len(orders_df)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Order Volume", f"₹{total_turnover:,.2f}")
    m2.metric("Your 1% Pure Platform Profit", f"₹{total_platform_cut:,.2f}", delta="1% Commission")
    m3.metric("Total Orders Processed", total_orders)

    st.markdown("---")
    st.write("### 📜 Real-time Transactions & Payout Ledger")
    if not orders_df.empty:
        st.dataframe(orders_df[[
            "id", "customer_name", "item_price", "delivery_fee", 
            "grand_total", "platform_commission_1pct", "vendor_net_payout", "created_at"
        ]], use_container_width=True)
    else:
        st.info("No orders placed yet. Place an order from the Customer Marketplace!")
