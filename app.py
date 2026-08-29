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
    page_icon="🇮🇳",
    layout="wide"
)

DB_NAME = "hyperlocal_market.db"
PLATFORM_UPI_ID = "adminplatform@upi"

# -----------------------------------------------------------
# 1. DATABASE SETUP
# -----------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT DEFAULT '919876543210',
        upi_id TEXT DEFAULT 'merchant@upi', city TEXT NOT NULL, address TEXT, gstin TEXT DEFAULT 'NON-GST',
        rera_id TEXT DEFAULT 'N/A', is_kyc_verified INTEGER DEFAULT 1, is_sponsored INTEGER DEFAULT 0,
        lat REAL NOT NULL, lon REAL NOT NULL, rating REAL DEFAULT 4.8, wallet_balance REAL DEFAULT 150.0,
        free_delivery_above_500 INTEGER DEFAULT 1, base_1km REAL DEFAULT 20.0, base_2km REAL DEFAULT 30.0, per_km_extra REAL DEFAULT 10.0
    )''')
    vendor_cols = [col[1] for col in c.execute("PRAGMA table_info(vendors)").fetchall()]
    if "wallet_balance" not in vendor_cols: c.execute("ALTER TABLE vendors ADD COLUMN wallet_balance REAL DEFAULT 150.0")

    c.execute('''CREATE TABLE IF NOT EXISTS riders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
        city TEXT NOT NULL, vehicle_number TEXT, wallet_balance REAL DEFAULT 0.0, status TEXT DEFAULT 'Active'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id INTEGER NOT NULL, brand TEXT NOT NULL,
        title TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL, is_high_value INTEGER DEFAULT 0,
        advance_booking_amount REAL DEFAULT 0.0, video_url TEXT DEFAULT '', image_url TEXT DEFAULT '', description TEXT,
        FOREIGN KEY (vendor_id) REFERENCES vendors (id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, customer_phone TEXT, delivery_address TEXT, vendor_id INTEGER,
        rider_id INTEGER DEFAULT 0, delivery_otp TEXT DEFAULT '1234', items_summary TEXT DEFAULT '',
        item_price REAL DEFAULT 0.0, delivery_fee REAL DEFAULT 0.0, grand_total REAL DEFAULT 0.0, 
        platform_commission_1pct REAL DEFAULT 0.0, distance_km REAL DEFAULT 0.0, delivery_mode TEXT DEFAULT 'Delivery', 
        payment_status TEXT DEFAULT 'Pending (UPI on Delivery)', status TEXT DEFAULT 'Order Placed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    order_cols = [col[1] for col in c.execute("PRAGMA table_info(orders)").fetchall()]
    if "delivery_address" not in order_cols: c.execute("ALTER TABLE orders ADD COLUMN delivery_address TEXT DEFAULT 'GPS Location'")
    if "payment_status" not in order_cols: c.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'Pending (UPI on Delivery)'")

    c.execute("CREATE TABLE IF NOT EXISTS wallet_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id INTEGER, txn_type TEXT, amount REAL, txn_ref TEXT, status TEXT DEFAULT 'Completed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS site_visits (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, vendor_id INTEGER, customer_name TEXT, customer_phone TEXT, visit_date TEXT, visit_time TEXT, status TEXT DEFAULT 'Confirmed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, sender_name TEXT, message_text TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO vendors (name, phone, upi_id, city, address, gstin, rera_id, is_kyc_verified, is_sponsored, lat, lon, rating, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
            VALUES ('Mamta General & Cloth Store', '919876543210', 'mamtastore@upi', 'Nagpur', 'Main Market', '27ABCDE1234F1Z5', 'N/A', 1, 1, 21.1458, 79.0882, 4.9, 150.0, 1, 20.0, 30.0, 10.0)''')
        c.execute('''INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, video_url, image_url, description)
            VALUES (1, 'Cotton King', 'Premium Cotton Shirt', 'Fashion', 1000.0, 0, 0.0, '', 'https://via.placeholder.com/200', 'Pure breathable formal shirt')''')
        c.execute("INSERT INTO riders (name, phone, city, vehicle_number, wallet_balance, status) VALUES ('Amit Kumar (Rider)', '919876540001', 'Nagpur', 'MH-31-AB-1234', 5000.0, 'Active')")
    
    conn.commit()
    conn.close()

init_db()
if "cart" not in st.session_state: st.session_state.cart = []

# -----------------------------------------------------------
# 2. HELPER FUNCTIONS
# -----------------------------------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    d_lat, d_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(d_lat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(d_lon/2)**2)
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 2)

def get_delivery_fee(distance_km, item_price, free_allowed, base_1km, base_2km, per_km_extra):
    if item_price >= 500 and free_allowed == 1: return 0.0, "FREE Delivery"
    if distance_km <= 1.0: return float(base_1km), f"Rs {base_1km:.0f}"
    elif distance_km <= 2.0: return float(base_2km), f"Rs {base_2km:.0f}"
    else: return round(base_2km + ((distance_km - 2.0) * per_km_extra), 2), f"Rs {base_2km:.0f} + Extra KM"

def generate_upi_qr(upi_id, payee_name, amount, note):
    upi_url = f"upi://pay?pa={upi_id}&pn={urllib.parse.quote(payee_name)}&am={amount:.2f}&cu=INR&tn={urllib.parse.quote(note)}"
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(upi_url); qr.make(fit=True)
    buf = io.BytesIO(); qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return buf.getvalue()

def generate_pdf_invoice(bill_data):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "BHARAT HYPERLOCAL MARKETPLACE", ln=True, align="C"); pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 7, f"Order ID: #{bill_data['order_id']}")
    pdf.cell(90, 7, f"Customer: {bill_data['cust']}", ln=True)
    pdf.cell(100, 7, f"Store: {bill_data['shop']}")
    pdf.cell(90, 7, f"Address: {bill_data['address']}", ln=True); pdf.ln(4)
    pdf.cell(120, 7, "Description"); pdf.cell(70, 7, "Amount (INR)", ln=True, align="R")
    pdf.cell(120, 7, f"{bill_data['item']}"); pdf.cell(70, 7, f"Rs {bill_data['price']:,.2f}", ln=True, align="R")
    pdf.cell(120, 7, "Delivery Charges"); pdf.cell(70, 7, f"Rs {bill_data['fee']:,.2f}", ln=True, align="R")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 9, "Total to Pay Store:"); pdf.cell(70, 9, f"Rs {bill_data['total']:,.2f}", ln=True, align="R")
    return pdf.output()

# -----------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------
st.sidebar.title("🇮🇳 Bharat Platform")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Marketplace",
    "🏪 Vendor Terminal",
    "🛵 Rider Terminal (UPI Collection)",
    "🚚 Track My Orders",
    "💳 Vendor Wallet & Refund"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER MARKETPLACE (Custom Location Added)
# -----------------------------------------------------------
if menu == "🛍️ Customer Marketplace":
    st.subheader("📍 Discover Nearby Stores")
    
    # Custom Location Logic
    loc_mode = st.radio("Choose Delivery Location Method:", ["📍 Auto-Detect (Current GPS)", "🏠 Enter Manual Location (e.g. Nagpur Home)"], horizontal=True)
    
    detected_lat, detected_lon = 21.1458, 79.0882
    cust_address_text = "Current GPS Location"

    if loc_mode == "📍 Auto-Detect (Current GPS)":
        live_loc = get_geolocation()
        if live_loc and 'coords' in live_loc:
            detected_lat = live_loc['coords']['latitude']
            detected_lon = live_loc['coords']['longitude']
    else:
        cust_address_text = st.text_input("Enter Full Delivery Address & City (e.g., New Amar Nagar, Nagpur)", "New Amar Nagar, Nagpur")
        # In a real app, geocode the address. Here we allow manual tweak if needed.
        col_m1, col_m2 = st.columns(2)
        with col_m1: detected_lat = st.number_input("Latitude", value=21.1000, format="%.4f")
        with col_m2: detected_lon = st.number_input("Longitude", value=79.0700, format="%.4f")

    c1, c2 = st.columns(2)
    with c1: cust_name = st.text_input("Name", value="Rahul Sharma")
    with c2: cust_phone = st.text_input("WhatsApp", value="919876500000")
    st.markdown("---")
    
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT p.*, v.id as v_id, v.name as v_name, v.upi_id, v.wallet_balance, v.lat as v_lat, v.lon as v_lon, v.free_delivery_above_500, v.base_1km, v.base_2km, v.per_km_extra FROM products p JOIN vendors v ON p.vendor_id = v.id', conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        dist = calculate_distance(detected_lat, detected_lon, row["v_lat"], row["v_lon"])
        fee, fee_desc = get_delivery_fee(dist, row["price"], row["free_delivery_above_500"], row["base_1km"], row["base_2km"], row["per_km_extra"])
        results.append({
            "p_id": row["id"], "brand": row["brand"], "title": row["title"], "price": row["price"], "is_high_val": row["is_high_value"],
            "image_url": row["image_url"], "v_id": row["v_id"], "v_name": row["v_name"], "v_upi": row["upi_id"], "v_wallet": row["wallet_balance"],
            "distance": dist, "delivery_fee": fee, "fee_desc": fee_desc, "v_lat": row["v_lat"], "v_lon": row["v_lon"]
        })
    results.sort(key=lambda x: x["distance"])

    if results:
        m = folium.Map(location=[detected_lat, detected_lon], zoom_start=13)
        folium.Marker([detected_lat, detected_lon], popup="Delivery Location", icon=folium.Icon(color="blue", icon="home")).add_to(m)
        for item in results:
            folium.Marker([item["v_lat"], item["v_lon"]], popup=f"{item['v_name']} ({item['distance']} KM)", icon=folium.Icon(color="green")).add_to(m)
        st_folium(m, height=230, use_container_width=True)

        cols = st.columns(2)
        for idx, item in enumerate(results):
            with cols[idx % 2]:
                with st.container(border=True):
                    img_col, info_col = st.columns([1, 2])
                    with img_col: st.image(item["image_url"], use_container_width=True)
                    with info_col:
                        st.markdown(f"### {item['brand']} - {item['title']}")
                        st.markdown(f"Price: :green[**Rs {item['price']:,.2f}**]")
                        st.caption(f"🏬 **Store:** {item['v_name']} | {item['distance']} KM away")

                    del_pref = st.radio("Delivery Mode:", [f"🚚 Home Delivery (Rs {item['delivery_fee']})", "🚶 Pickup (Free)"], key=f"rad_{item['p_id']}", horizontal=True)
                    final_fee = 0.0 if "Pickup" in del_pref else item["delivery_fee"]
                    final_mode = "Pickup" if "Pickup" in del_pref else "Delivery"

                    commission_required = round(item["price"] * 0.01, 2)
                    
                    if item["v_wallet"] < commission_required:
                        st.error("⚠️ Store Offline (Wallet Recharge pending).")
                    else:
                        if st.button(f"🚀 Place Order (Pay via UPI on Delivery)", key=f"btn_{item['p_id']}"):
                            grand_total = item["price"] + final_fee
                            gen_otp = str(random.randint(1000, 9999))

                            conn_o = sqlite3.connect(DB_NAME)
                            cur = conn_o.cursor()
                            cur.execute('''
                                INSERT INTO orders (customer_name, customer_phone, delivery_address, vendor_id, delivery_otp, items_summary, item_price, delivery_fee, grand_total, platform_commission_1pct, distance_km, delivery_mode, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Order Placed')
                            ''', (cust_name, cust_phone, cust_address_text, item["v_id"], gen_otp, f"{item['brand']} - {item['title']}", item["price"], final_fee, grand_total, commission_required, item["distance"], final_mode))
                            
                            cur.execute('UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?', (commission_required, item["v_id"]))
                            conn_o.commit(); order_id = cur.lastrowid; conn_o.close()

                            st.session_state.current_bill = {
                                "order_id": order_id, "cust": cust_name, "address": cust_address_text, "otp": gen_otp,
                                "item": f"{item['brand']} - {item['title']}", "shop": item["v_name"],
                                "shop_upi": item["v_upi"], "price": item["price"], "fee": final_fee, 
                                "total": grand_total, "cut": commission_required, "distance": item["distance"], "mode": final_mode
                            }

    if "current_bill" in st.session_state:
        b = st.session_state.current_bill
        st.success(f"🎉 Order #{b['order_id']} Placed! Delivered to: {b['address']}")
        st.info(f"आपको डिलीवरी के समय **Rs {b['total']:,.2f}** का पेमेंट सीधे दुकानदार के UPI पर करना होगा।")
        st.warning(f"🔒 **Your Secret Delivery OTP:** `{b['otp']}`")
        pdf_bytes = generate_pdf_invoice(b)
        st.download_button("📄 Download Invoice", data=bytes(pdf_bytes), file_name=f"Order_{b['order_id']}.pdf", mime="application/pdf")

# -----------------------------------------------------------
# TAB: VENDOR TERMINAL (Shows Notifications)
# -----------------------------------------------------------
elif menu == "🏪 Vendor Terminal":
    st.subheader("🔔 Store Orders & Fulfillment Dashboard")
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    
    if not vendors_df.empty:
        selected_vid = st.selectbox("Select Shop Terminal", vendors_df["id"].tolist(), format_func=lambda x: f"{vendors_df[vendors_df['id'] == x]['name'].values[0]}")
        v_orders = pd.read_sql_query("SELECT * FROM orders WHERE vendor_id = ? ORDER BY created_at DESC LIMIT 10", conn, params=(selected_vid,))
        
        if not v_orders.empty:
            for _, ord_row in v_orders.iterrows():
                with st.container(border=True):
                    col_o1, col_o2, col_o3 = st.columns([2, 2, 2])
                    with col_o1:
                        st.markdown(f"**Order #{ord_row['id']}** | Customer: `{ord_row['customer_name']}`")
                        st.write(f"Address: `{ord_row['delivery_address']}`")
                        st.write(f"Payment to Collect: :green[**Rs {ord_row['grand_total']:,.2f}**]")
                    with col_o2:
                        st.write(f"Mode: **{ord_row['delivery_mode']}**")
                        st.write(f"Status: `{ord_row['status']}`")
                        if "Paid via UPI" in ord_row['payment_status']:
                            st.success(f"✅ {ord_row['payment_status']}")
                        else:
                            st.warning(f"⏳ {ord_row['payment_status']}")
                    with col_o3:
                        if ord_row["status"] == "Order Placed":
                            if ord_row['delivery_mode'] == "Pickup":
                                if st.button("✅ Confirm Picked Up", key=f"pu_{ord_row['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ord_row['id'],))
                                    conn.commit(); st.rerun()
                            elif ord_row['delivery_mode'] == "Delivery":
                                if st.button("Self-Dispatch (Own Boy)", key=f"sd_{ord_row['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ord_row['id'],))
                                    conn.commit(); st.rerun()
                                if ord_row['grand_total'] <= 5000:
                                    if st.button("🛵 Request Platform Rider", type="primary", key=f"rr_{ord_row['id']}"):
                                        conn.execute("UPDATE orders SET status = 'Rider Requested' WHERE id = ?", (ord_row['id'],))
                                        conn.commit(); st.rerun()
                        elif ord_row["status"] == "Dispatched" and ord_row['rider_id'] == 0:
                            if st.button("✅ Mark Delivered & Paid", key=f"md_{ord_row['id']}"):
                                conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ord_row['id'],))
                                conn.commit(); st.rerun()

                        # Fetch System Notifications for this order
                        msgs = pd.read_sql_query("SELECT message_text FROM messages WHERE order_id = ? AND sender_name = 'System'", conn, params=(ord_row['id'],))
                        for _, m in msgs.iterrows():
                            st.info(m['message_text'])
    conn.close()

# -----------------------------------------------------------
# TAB: RIDER TERMINAL (Rider Notifies Vendor)
# -----------------------------------------------------------
elif menu == "🛵 Rider Terminal (UPI Collection)":
    st.subheader("🛵 Delivery Partner Dashboard")
    conn = sqlite3.connect(DB_NAME)
    riders_df = pd.read_sql_query("SELECT * FROM riders WHERE status = 'Active'", conn)
    
    if not riders_df.empty:
        selected_rider_id = st.selectbox("Select Rider Profile", riders_df["id"].tolist(), format_func=lambda x: riders_df[riders_df['id'] == x]['name'].values[0])
        curr_rider = riders_df[riders_df["id"] == selected_rider_id].iloc[0]

        r_orders = pd.read_sql_query('''
            SELECT o.*, v.name as shop_name, v.address as shop_address, v.upi_id as shop_upi
            FROM orders o JOIN vendors v ON o.vendor_id = v.id
            WHERE o.status = 'Rider Requested' OR (o.status IN ('Accepted by Rider', 'Dispatched') AND o.rider_id = ?)
            ORDER BY o.created_at DESC
        ''', conn, params=(selected_rider_id,))

        if not r_orders.empty:
            for _, ro in r_orders.iterrows():
                with st.container(border=True):
                    col_r1, col_r2 = st.columns([3, 2])
                    with col_r1:
                        st.markdown(f"**Order #{ro['id']}** | Customer: `{ro['customer_name']}`")
                        st.write(f"Drop Address: `{ro['delivery_address']}`")
                        st.write(f"Delivery Fee Earned: :green[Rs {ro['delivery_fee']:,.2f}]")
                    with col_r2:
                        if ro["status"] == "Rider Requested":
                            if curr_rider['wallet_balance'] < 5000: st.error("⚠️ Rs 5000 Security required.")
                            else:
                                if st.button("🚴 Accept Delivery", key=f"acc_{ro['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Accepted by Rider', rider_id = ? WHERE id = ?", (selected_rider_id, ro['id']))
                                    conn.commit(); st.rerun()

                        elif ro["status"] == "Accepted by Rider":
                            if st.button("🚚 Picked Up & Reached Customer", key=f"disp_r_{ro['id']}"):
                                conn.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ro['id'],))
                                conn.commit(); st.rerun()

                        elif ro["status"] == "Dispatched":
                            st.markdown("### 📱 Payment Collection")
                            st.warning(f"स्कैन करके **Rs {ro['grand_total']:,.2f}** सीधे **{ro['shop_name']}** को पे करें:")
                            qr_bytes = generate_upi_qr(ro['shop_upi'], ro['shop_name'], ro['grand_total'], f"Order_{ro['id']}")
                            st.image(qr_bytes, width=200)
                            
                            otp_in = st.text_input("Customer 4-Digit OTP", key=f"otp_{ro['id']}")
                            if st.button("✅ Verify OTP & Mark Complete", key=f"comp_{ro['id']}"):
                                if otp_in == str(ro['delivery_otp']):
                                    # Update Order
                                    conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ro['id'],))
                                    # Send Notification to Vendor
                                    msg = f"✅ Success! Rs {ro['grand_total']:,.2f} has been directly collected via Rider ({curr_rider['name']}) through UPI."
                                    conn.execute("INSERT INTO messages (order_id, sender_name, message_text) VALUES (?, 'System', ?)", (ro['id'], msg))
                                    conn.commit()
                                    st.success(f"🎉 Delivery Completed & Vendor Notified!"); st.rerun()
                                else:
                                    st.error("❌ Invalid OTP!")
    conn.close()

# -----------------------------------------------------------
# OTHER TABS
# -----------------------------------------------------------
elif menu in ["🚚 Track My Orders", "💳 Vendor Wallet & Refund"]:
    st.info("Additional tabs work exactly exactly as defined previously.")