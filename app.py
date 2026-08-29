import streamlit as st
import sqlite3
import math
import random
import urllib.parse
import os
import pandas as pd
import folium
import qrcode
import io
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from fpdf import FPDF

st.set_page_config(
    page_title="Bharat All-in-One Hyperlocal Platform",
    page_icon="🛍️",
    layout="wide"
)

DB_NAME = "hyperlocal_market.db"
PLATFORM_UPI_ID = "adminplatform@upi"

# -----------------------------------------------------------
# 1. DATABASE SETUP & COMPLETE SCHEMA MIGRATION
# -----------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Vendors Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '919876543210',
            upi_id TEXT DEFAULT 'merchant@upi',
            city TEXT NOT NULL,
            address TEXT,
            gstin TEXT DEFAULT 'NON-GST',
            rera_id TEXT DEFAULT 'N/A',
            is_kyc_verified INTEGER DEFAULT 1,
            is_sponsored INTEGER DEFAULT 0,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            rating REAL DEFAULT 4.8,
            wallet_balance REAL DEFAULT 150.0,
            free_delivery_above_500 INTEGER DEFAULT 1,
            base_1km REAL DEFAULT 20.0,
            base_2km REAL DEFAULT 30.0,
            per_km_extra REAL DEFAULT 10.0
        )
    ''')

    vendor_cols = [col[1] for col in c.execute("PRAGMA table_info(vendors)").fetchall()]
    if "rera_id" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN rera_id TEXT DEFAULT 'N/A'")
    if "is_kyc_verified" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN is_kyc_verified INTEGER DEFAULT 1")
    if "is_sponsored" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN is_sponsored INTEGER DEFAULT 0")
    if "gstin" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN gstin TEXT DEFAULT 'NON-GST'")
    if "wallet_balance" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN wallet_balance REAL DEFAULT 150.0")

    # 2. Products Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            brand TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            is_high_value INTEGER DEFAULT 0,
            advance_booking_amount REAL DEFAULT 0.0,
            video_url TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            description TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id)
        )
    ''')

    # 3. Orders Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            vendor_id INTEGER,
            rider_id INTEGER DEFAULT 0,
            delivery_otp TEXT DEFAULT '1234',
            items_summary TEXT DEFAULT '',
            item_price REAL DEFAULT 0.0,
            amount_paid_now REAL DEFAULT 0.0,
            discount_amount REAL DEFAULT 0.0,
            delivery_fee REAL DEFAULT 0.0,
            grand_total REAL DEFAULT 0.0,
            platform_commission_1pct REAL DEFAULT 0.0,
            platform_gst_18pct REAL DEFAULT 0.0,
            vendor_net_payout REAL DEFAULT 0.0,
            distance_km REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Order Placed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Wallet Recharges & Withdrawals History Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            txn_type TEXT,
            amount REAL,
            txn_ref TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Default Demo Store (ममता स्टोर)
    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO vendors (name, phone, upi_id, city, address, gstin, rera_id, is_kyc_verified, is_sponsored, lat, lon, rating, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
            VALUES 
            ('Mamta General & Cloth Store', '919876543210', 'mamtastore@okaxis', 'Nagpur', 'Main Market', '27ABCDE1234F1Z5', 'N/A', 1, 1, 21.1458, 79.0882, 4.9, 150.0, 1, 20.0, 30.0, 10.0)
        ''')
        c.execute('''
            INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, video_url, image_url, description)
            VALUES 
            (1, 'Cotton King', 'Pure Cotton Shirt', 'Fashion', 1000.0, 0, 0.0, '', 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60', 'Pure breathable formal shirt'),
            (1, 'Tata Tea', 'Tata Tea Premium 250g', 'Grocery', 50.0, 0, 0.0, '', 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=500&auto=format&fit=crop&q=60', 'Fresh daily morning tea')
        ''')

    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------
# 2. LOGIC FUNCTIONS
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

def generate_upi_qr(upi_id, payee_name, amount, note):
    upi_url = f"upi://pay?pa={upi_id}&pn={urllib.parse.quote(payee_name)}&am={amount:.2f}&cu=INR&tn={urllib.parse.quote(note)}"
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# -----------------------------------------------------------
# 3. NAVIGATION
# -----------------------------------------------------------
st.sidebar.title("🇮🇳 Bharat Platform")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Marketplace",
    "🏪 Vendor Terminal & Orders",
    "💳 Vendor Wallet & Refund/Withdrawal",
    "📦 Add Product / Listing",
    "🏬 Register New Store (Free)",
    "📊 Platform Earnings Ledger"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER MARKETPLACE
# -----------------------------------------------------------
if menu == "🛍️ Customer Marketplace":
    st.subheader("📍 Nearby Stores (Direct Store UPI Payment)")
    
    live_loc = get_geolocation()
    detected_lat = 21.1458
    detected_lon = 79.0882
    if live_loc and 'coords' in live_loc:
        detected_lat = live_loc['coords']['latitude']
        detected_lon = live_loc['coords']['longitude']

    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1:
        cust_name = st.text_input("Customer Name", value="Rahul Sharma")
    with c2:
        cust_phone = st.text_input("Customer Phone", value="919876500000")
    with c3:
        cust_lat = st.number_input("Latitude", value=float(detected_lat), format="%.4f")
    with c4:
        cust_lon = st.number_input("Longitude", value=float(detected_lon), format="%.4f")

    st.markdown("---")
    
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT p.id, p.brand, p.title, p.category, p.price, p.image_url, p.description,
               v.id as vendor_id, v.name as vendor_name, v.phone as vendor_phone, v.upi_id,
               v.wallet_balance as vendor_wallet, v.lat, v.lon
        FROM products p
        JOIN vendors v ON p.vendor_id = v.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        dist = calculate_distance(cust_lat, cust_lon, row["lat"], row["lon"])
        results.append({
            "p_id": row["id"],
            "brand": row["brand"],
            "title": row["title"],
            "category": row["category"],
            "price": row["price"],
            "image_url": row["image_url"] if row["image_url"] else "https://via.placeholder.com/300x200?text=Product+Image",
            "desc": row["description"],
            "v_id": row["vendor_id"],
            "v_name": row["vendor_name"],
            "v_phone": str(row["vendor_phone"]),
            "v_upi": row["upi_id"],
            "v_wallet": row["vendor_wallet"],
            "distance": dist
        })

    if results:
        cols = st.columns(2)
        for idx, item in enumerate(results):
            with cols[idx % 2]:
                with st.container(border=True):
                    img_col, info_col = st.columns([1, 2])
                    with img_col:
                        st.image(item["image_url"], use_container_width=True)
                    with info_col:
                        st.markdown(f"### {item['brand']} - {item['title']}")
                        st.markdown(f"Price: :green[**Rs {item['price']:,.2f}**]")
                        st.caption(f"🏬 **Store:** {item['v_name']} (Direct UPI: `{item['v_upi']}`)")

                    commission_required = round(item["price"] * 0.01, 2)
                    
                    # Store active only if wallet balance > 0
                    if item["v_wallet"] < commission_required:
                        st.error(f"⚠️ {item['v_name']} is currently Offline (Recharge required by shopkeeper).")
                    else:
                        if st.button(f"⚡ Buy & Pay Store Directly (Rs {item['price']:,.2f})", key=f"btn_{item['p_id']}"):
                            item_total = item["price"]
                            cut_1pct = commission_required
                            gen_otp = str(random.randint(1000, 9999))

                            conn_o = sqlite3.connect(DB_NAME)
                            cur = conn_o.cursor()
                            cur.execute('''
                                INSERT INTO orders (customer_name, customer_phone, vendor_id, delivery_otp, items_summary, item_price, amount_paid_now, delivery_fee, grand_total, platform_commission_1pct, vendor_net_payout, distance_km, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, 'Order Placed')
                            ''', (cust_name, cust_phone, item["v_id"], gen_otp, f"{item['brand']} - {item['title']}", item_total, item_total, item_total, cut_1pct, item_total, item["distance"]))
                            
                            # ⚡ सिर्फ बिक्री होने पर ही 1% कमीशन वेंडर के वॉलेट से कटेगा
                            cur.execute('UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?', (cut_1pct, item["v_id"]))
                            conn_o.commit()
                            order_id = cur.lastrowid
                            conn_o.close()

                            st.session_state.current_bill = {
                                "order_id": order_id,
                                "cust": cust_name,
                                "item": f"{item['brand']} - {item['title']}",
                                "shop": item["v_name"],
                                "shop_phone": item["v_phone"],
                                "shop_upi": item["v_upi"],
                                "total": item_total,
                                "cut": cut_1pct
                            }

    # Invoice & Direct Merchant QR
    if "current_bill" in st.session_state:
        b = st.session_state.current_bill
        st.markdown("---")
        st.success(f"🎉 Order #{b['order_id']} Created! Pay 100% Directly to Store:")
        
        q1, q2 = st.columns([1, 1])
        with q1:
            st.markdown(f"### 📱 Scan to Pay Direct to {b['shop']}")
            qr_bytes = generate_upi_qr(b["shop_upi"], b["shop"], b["total"], f"Order_{b['order_id']}")
            st.image(qr_bytes, width=220)
            st.write(f"**Direct Payee UPI:** `{b['shop_upi']}` | **Total Amount:** :green[**Rs {b['total']:,.2f}**]")
            
        with q2:
            st.markdown("### 🧾 Invoice & Commission Settlement")
            st.write(f"**Customer:** {b['cust']}")
            st.write(f"**Item:** {b['item']}")
            st.markdown(f"### **Total Paid to Shop:** :green[Rs {b['total']:,.2f}]")
            st.info(f"✅ 1% Platform Fee (Rs {b['cut']:,.2f}) auto-debited from {b['shop']}'s Wallet on this transaction.")

# -----------------------------------------------------------
# TAB 2: VENDOR TERMINAL & ORDERS
# -----------------------------------------------------------
elif menu == "🏪 Vendor Terminal & Orders":
    st.subheader("🔔 Store Orders & 1% Commission Audit")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    if not vendors_df.empty:
        selected_vid = st.selectbox(
            "Select Shop Terminal",
            vendors_df["id"].tolist(),
            format_func=lambda x: f"{vendors_df[vendors_df['id'] == x]['name'].values[0]} (Wallet: Rs {vendors_df[vendors_df['id'] == x]['wallet_balance'].values[0]:,.2f})"
        )

        conn = sqlite3.connect(DB_NAME)
        v_orders = pd.read_sql_query(
            "SELECT * FROM orders WHERE vendor_id = ? ORDER BY created_at DESC", 
            conn, params=(selected_vid,)
        )
        conn.close()

        if not v_orders.empty:
            for _, ord_row in v_orders.iterrows():
                with st.container(border=True):
                    col_o1, col_o2 = st.columns([2, 2])
                    with col_o1:
                        st.markdown(f"**Order #{ord_row['id']}** | Customer: `{ord_row['customer_name']}`")
                        st.write(f"Direct Store Received: :green[**Rs {ord_row['grand_total']:,.2f}**]")
                    with col_o2:
                        st.write(f"1% Platform Fee Deducted: :red[**-Rs {ord_row['platform_commission_1pct']:,.2f}**]")
                        st.caption("Deducted from your In-App Wallet balance on successful sale.")
        else:
            st.info("No orders received yet.")

# -----------------------------------------------------------
# TAB 3: VENDOR WALLET & REFUND / WITHDRAWAL
# -----------------------------------------------------------
elif menu == "💳 Vendor Wallet & Refund/Withdrawal":
    st.subheader("💳 Store Personal Wallet & Refund Manager")
    st.caption("यह आपका निजी वॉलेट है। जब तक माल नहीं बिकता, आपका पैसा 100% सुरक्षित रहता है। आप कभी भी बचा हुआ बैलेंस वापस ले सकते हैं।")

    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    if not vendors_df.empty:
        v_select = st.selectbox(
            "Select Store Account",
            vendors_df["id"].tolist(),
            format_func=lambda x: f"{vendors_df[vendors_df['id'] == x]['name'].values[0]}"
        )
        curr_vendor = vendors_df[vendors_df["id"] == v_select].iloc[0]

        w1, w2 = st.columns([1, 1])
        with w1:
            with st.container(border=True):
                st.markdown("### 💰 Your In-App Wallet Balance")
                st.metric("Safe Unused Balance", f"Rs {curr_vendor['wallet_balance']:,.2f}")
                
                if curr_vendor['wallet_balance'] < 10.0:
                    st.error("🚨 Low Balance! Store is Offline.")
                else:
                    st.success("🟢 Store is ACTIVE (Ready to receive customer orders).")

                st.write(f"Store: **{curr_vendor['name']}**")
                st.write(f"Direct Payment UPI: `{curr_vendor['upi_id']}`")

                # ⚡ 1-Click Withdraw/Refund Remaining Unused Balance
                st.markdown("---")
                st.markdown("#### 🔄 Withdraw / Refund Remaining Balance")
                st.caption("अगर आपको प्लेटफॉर्म छोड़ना है, तो बचा हुआ पूरा पैसा आपके UPI पर वापस मिल जाएगा:")
                
                if curr_vendor['wallet_balance'] > 0:
                    if st.button("💸 Withdraw Full Remaining Balance"):
                        refund_amt = curr_vendor['wallet_balance']
                        conn_wd = sqlite3.connect(DB_NAME)
                        conn_wd.execute("UPDATE vendors SET wallet_balance = 0.0 WHERE id = ?", (v_select,))
                        conn_wd.execute("INSERT INTO wallet_logs (vendor_id, txn_type, amount, txn_ref) VALUES (?, 'WITHDRAWAL/REFUND', ?, ?)", 
                                        (v_select, refund_amt, f"Refund to {curr_vendor['upi_id']}"))
                        conn_wd.commit()
                        conn_wd.close()
                        st.success(f"🎉 Rs {refund_amt:,.2f} refund initiated to `{curr_vendor['upi_id']}`! Wallet is now Rs 0.00.")
                        st.rerun()
                else:
                    st.info("No balance available to withdraw.")

        with w2:
            with st.container(border=True):
                st.markdown("### ⚡ Top-Up In-App Wallet")
                st.write("Advance deposit to keep store active:")
                
                topup_amt = st.radio("Select Top-Up Amount", [100.0, 150.0, 200.0, 500.0], index=1, horizontal=True)
                
                p_qr = generate_upi_qr(PLATFORM_UPI_ID, "Bharat Platform Admin", topup_amt, f"Wallet_Store_{curr_vendor['id']}")
                st.image(p_qr, width=170)
                st.caption(f"Platform UPI: `{PLATFORM_UPI_ID}` | Amount: **Rs {topup_amt:.0f}**")
                
                txn_ref_in = st.text_input("Enter 12-Digit UPI Ref / UTR No.", placeholder="e.g. 423456789012")
                
                if st.button("✅ Add Balance to My Wallet"):
                    if txn_ref_in:
                        conn_tu = sqlite3.connect(DB_NAME)
                        conn_tu.execute("UPDATE vendors SET wallet_balance = wallet_balance + ? WHERE id = ?", (topup_amt, v_select))
                        conn_tu.execute("INSERT INTO wallet_logs (vendor_id, txn_type, amount, txn_ref) VALUES (?, 'TOP-UP', ?, ?)", (v_select, topup_amt, txn_ref_in))
                        conn_tu.commit()
                        conn_tu.close()
                        st.success(f"🎉 Rs {topup_amt:,.2f} added to {curr_vendor['name']}'s wallet!")
                        st.rerun()
                    else:
                        st.error("Please enter UTR Number after payment.")

        st.markdown("---")
        st.write("### 📜 Wallet History (Top-Ups & Refunds):")
        conn_l = sqlite3.connect(DB_NAME)
        logs_df = pd.read_sql_query("SELECT * FROM wallet_logs WHERE vendor_id = ? ORDER BY created_at DESC", conn_l, params=(v_select,))
        conn_l.close()
        if not logs_df.empty:
            st.dataframe(logs_df, use_container_width=True)
        else:
            st.info("No wallet transactions recorded yet.")

# -----------------------------------------------------------
# TAB 4: ADD PRODUCT / LISTING
# -----------------------------------------------------------
elif menu == "📦 Add Product / Listing":
    st.subheader("📦 Add New Product to Store")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    with st.form("prod_form"):
        s_id = st.selectbox(
            "Select Store", vendors_df["id"].tolist(),
            format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0]
        )
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            b_name = st.text_input("Brand / Item Group", placeholder="e.g. Mamta Cloth, Tata")
            p_name = st.text_input("Product Name", placeholder="e.g. Cotton Shirt, Tea 250g")
            p_cat = st.selectbox("Category", ["Fashion", "Grocery", "Daily Essentials", "Electronics"])
        with c_p2:
            p_val = st.number_input("Selling Price (Rs)", min_value=10.0, max_value=500000.0, value=1000.0, step=50.0)
            img_link = st.text_input("Product Image URL", placeholder="https://example.com/item.jpg")
            p_desc = st.text_area("Product Details")

        if st.form_submit_button("🚀 Publish Product"):
            if b_name and p_name:
                conn_i = sqlite3.connect(DB_NAME)
                conn_i.execute('''
                    INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, video_url, image_url, description)
                    VALUES (?, ?, ?, ?, ?, 0, 0.0, '', ?, ?)
                ''', (s_id, b_name, p_name, p_cat, p_val, img_link, p_desc))
                conn_i.commit()
                conn_i.close()
                st.success(f"✅ '{b_name} - {p_name}' published successfully!")
                st.rerun()

# -----------------------------------------------------------
# TAB 5: REGISTER NEW STORE (100% FREE LIFETIME LISTING)
# -----------------------------------------------------------
elif menu == "🏬 Register New Store (Free)":
    st.subheader("🏬 Free Merchant Onboarding")

    with st.form("shop_form"):
        s_c1, s_c2 = st.columns(2)
        with s_c1:
            name = st.text_input("Store Name", placeholder="e.g. Mamta General & Cloth Store")
            phone = st.text_input("WhatsApp Phone (with 91)", value="919876543210")
            upi = st.text_input("Store Direct UPI ID (for Customer Payments)", placeholder="e.g. mamtastore@okaxis / 9876543210@paytm")
            city = st.text_input("City", value="Nagpur")
            address = st.text_input("Store Full Address")
        with s_c2:
            lat = st.number_input("GPS Latitude", value=21.1450, format="%.4f")
            lon = st.number_input("GPS Longitude", value=79.0800, format="%.4f")
            b1 = st.number_input("1 KM Delivery Fee (Rs)", value=20.0)
            b2 = st.number_input("2 KM Delivery Fee (Rs)", value=30.0)
            pe = st.number_input("Extra KM Fee (Rs)", value=10.0)

        if st.form_submit_button("✅ Register Store (Free)"):
            if name and upi:
                conn_r = sqlite3.connect(DB_NAME)
                conn_r.execute('''
                    INSERT INTO vendors (name, phone, upi_id, gstin, rera_id, is_kyc_verified, is_sponsored, city, address, lat, lon, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
                    VALUES (?, ?, ?, 'NON-GST', 'N/A', 1, 0, ?, ?, ?, ?, 0.0, 1, ?, ?, ?)
                ''', (name, phone, upi, city, address, lat, lon, b1, b2, pe))
                conn_r.commit()
                conn_r.close()
                st.success(f"🎉 Store '{name}' registered successfully with Rs 0.00 balance! Recharge wallet to activate.")
            else:
                st.error("Store Name and Direct UPI ID are compulsory.")

# -----------------------------------------------------------
# TAB 6: PLATFORM EARNINGS LEDGER
# -----------------------------------------------------------
else:
    st.subheader("📊 Platform 1% Pure Commission Revenue")
    conn = sqlite3.connect(DB_NAME)
    orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    conn.close()

    total_gross = orders_df["item_price"].sum() if not orders_df.empty else 0.0
    total_comm = orders_df["platform_commission_1pct"].sum() if not orders_df.empty else 0.0

    m1, m2 = st.columns(2)
    m1.metric("Total Platform GMV", f"Rs {total_gross:,.2f}")
    m2.metric("Total 1% Pure Commission Earned", f"Rs {total_comm:,.2f}", delta="Auto-Debited on Sales")

    st.markdown("---")
    st.write("### 📜 Real-Time Sales & Commission Deductions:")
    if not orders_df.empty:
        st.dataframe(orders_df[[
            "id", "customer_name", "items_summary", "item_price", "grand_total",
            "platform_commission_1pct", "status", "created_at"
        ]], use_container_width=True)
    else:
        st.info("No orders placed yet.")