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
import json
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from fpdf import FPDF
from PIL import Image

try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

st.set_page_config(page_title="Bharat Premium Hyperlocal", page_icon="👑", layout="wide")

# ==========================================
# 💎 PREMIUM LUXURY UI/UX & MULTI-COLOR TITLES
# ==========================================
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(145deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}
[data-testid="stSidebar"] h1 {
    color: #FFD700 !important; 
    font-family: 'Georgia', serif !important;
    letter-spacing: 1.2px;
    text-shadow: 0px 2px 8px rgba(255, 215, 0, 0.4);
}
div[role="radiogroup"] > label p { color: #F8FAFC !important; font-weight: 500; font-size: 15px; margin: 0; }
div[role="radiogroup"] > label {
    background: rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 12px 15px;
    margin-bottom: 10px; border: 1px solid rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}
div[role="radiogroup"] > label:hover {
    background: linear-gradient(90deg, rgba(212, 175, 55, 0.2) 0%, rgba(212, 175, 55, 0.05) 100%);
    border-left: 4px solid #D4AF37; transform: translateX(5px); box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
div[role="radiogroup"] > label span[data-baseweb="radio"] { display: none !important; }
.stApp { background: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, sans-serif; }
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px !important; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04) !important;
    border: 1px solid rgba(229, 184, 11, 0.3) !important; background: #ffffff !important;
    transition: transform 0.3s ease, box-shadow 0.3s ease; padding: 12px;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-5px); box-shadow: 0 12px 32px rgba(229, 184, 11, 0.15) !important;
    border: 1px solid rgba(229, 184, 11, 0.8) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
    color: #ffffff !important; border-radius: 30px !important; border: none !important;
    font-weight: 600 !important; box-shadow: 0 4px 15px rgba(30, 60, 114, 0.3) !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover { transform: scale(1.02); }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #D4AF37 0%, #AA7C11 100%) !important; color: #111 !important; }
.premium-title {
    background: linear-gradient(90deg, #FF1493, #FF8C00, #FFD700, #00BFFF);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 2.8rem; font-weight: 900; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding-bottom: 15px; letter-spacing: 1px; text-shadow: 2px 2px 5px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)
# ==========================================

DB_NAME = "hyperlocal_market.db"
PLATFORM_UPI_ID = "adminplatform@upi"

def init_db():
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT DEFAULT '919876543210', upi_id TEXT DEFAULT 'merchant@upi',
        city TEXT NOT NULL, address TEXT, gstin TEXT DEFAULT 'NON-GST', rera_id TEXT DEFAULT 'N/A', is_kyc_verified INTEGER DEFAULT 1,
        is_sponsored INTEGER DEFAULT 0, lat REAL NOT NULL, lon REAL NOT NULL, rating REAL DEFAULT 4.8, wallet_balance REAL DEFAULT 150.0,
        free_delivery_above_500 INTEGER DEFAULT 1, base_1km REAL DEFAULT 20.0, base_2km REAL DEFAULT 30.0, per_km_extra REAL DEFAULT 10.0
    )''')
    vendor_cols = [col[1] for col in c.execute("PRAGMA table_info(vendors)").fetchall()]
    if "wallet_balance" not in vendor_cols: c.execute("ALTER TABLE vendors ADD COLUMN wallet_balance REAL DEFAULT 150.0")

    c.execute("CREATE TABLE IF NOT EXISTS riders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL, city TEXT NOT NULL, vehicle_number TEXT, wallet_balance REAL DEFAULT 0.0, status TEXT DEFAULT 'Active')")
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id INTEGER NOT NULL, brand TEXT NOT NULL, title TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL, is_high_value INTEGER DEFAULT 0, advance_booking_amount REAL DEFAULT 0.0, video_url TEXT DEFAULT '', image_url TEXT DEFAULT '', description TEXT, FOREIGN KEY (vendor_id) REFERENCES vendors (id))")
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, customer_phone TEXT, delivery_address TEXT, vendor_id INTEGER,
        rider_id INTEGER DEFAULT 0, delivery_otp TEXT DEFAULT '1234', items_summary TEXT DEFAULT '', item_price REAL DEFAULT 0.0,
        delivery_fee REAL DEFAULT 0.0, grand_total REAL DEFAULT 0.0, platform_commission_1pct REAL DEFAULT 0.0, distance_km REAL DEFAULT 0.0,
        delivery_mode TEXT DEFAULT 'Delivery', payment_status TEXT DEFAULT 'Pending (UPI on Delivery)', status TEXT DEFAULT 'Order Placed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    order_cols = [col[1] for col in c.execute("PRAGMA table_info(orders)").fetchall()]
    if "delivery_address" not in order_cols: c.execute("ALTER TABLE orders ADD COLUMN delivery_address TEXT DEFAULT 'GPS Location'")
    if "payment_status" not in order_cols: c.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'Pending (UPI on Delivery)'")
    if "delivery_mode" not in order_cols: c.execute("ALTER TABLE orders ADD COLUMN delivery_mode TEXT DEFAULT 'Delivery'")

    c.execute("CREATE TABLE IF NOT EXISTS wallet_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id INTEGER, txn_type TEXT, amount REAL, txn_ref TEXT, status TEXT DEFAULT 'Completed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS site_visits (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, vendor_id INTEGER, customer_name TEXT, customer_phone TEXT, visit_date TEXT, visit_time TEXT, status TEXT DEFAULT 'Confirmed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, sender_name TEXT, message_text TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS coupons (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, discount_pct REAL DEFAULT 10.0, min_order_value REAL DEFAULT 200.0, is_active INTEGER DEFAULT 1)")

    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO vendors (name, upi_id, city, lat, lon) VALUES ('Mamta Store', 'mamtastore@upi', 'Nagpur', 21.1458, 79.0882)")
        c.execute("INSERT INTO products (vendor_id, brand, title, category, price, image_url) VALUES (1, 'Cotton King', 'Premium Shirt', 'Fashion', 1000.0, 'https://via.placeholder.com/200')")
        c.execute("INSERT INTO riders (name, phone, city, wallet_balance) VALUES ('Amit Rider', '919876540001', 'Nagpur', 5000.0)")
    conn.commit(); conn.close()

init_db()
if "cart" not in st.session_state: st.session_state.cart = []
if "scanned_data" not in st.session_state: st.session_state.scanned_data = {"brand": "", "title": "", "price": 0.0, "desc": ""}

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0; d_lat, d_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(d_lat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(d_lon/2)**2)
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 2)

def get_delivery_fee(distance_km, item_price, free_allowed, base_1km, base_2km, per_km_extra):
    if item_price >= 500 and free_allowed == 1: return 0.0, "FREE"
    if distance_km <= 1.0: return float(base_1km), f"Rs {base_1km:.0f}"
    elif distance_km <= 2.0: return float(base_2km), f"Rs {base_2km:.0f}"
    else: return round(base_2km + ((distance_km - 2.0) * per_km_extra), 2), f"Rs {base_2km:.0f} + Extra"

def generate_upi_qr(upi_id, payee_name, amount, note):
    upi_url = f"upi://pay?pa={upi_id}&pn={urllib.parse.quote(payee_name)}&am={amount:.2f}&cu=INR&tn={urllib.parse.quote(note)}"
    qr = qrcode.QRCode(box_size=6, border=2); qr.add_data(upi_url); qr.make(fit=True)
    buf = io.BytesIO(); qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return buf.getvalue()

def generate_standee_pdf(vendor):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "BHARAT DIGITAL NETWORK", ln=True, align="C"); pdf.set_font("Helvetica", "B", 14); pdf.cell(0, 10, f"OFFICIAL STORE: {vendor['name']}", ln=True, align="C")
    pdf.line(10, 45, 200, 45); pdf.ln(12)
    pdf.image(io.BytesIO(generate_upi_qr(vendor["upi_id"], vendor["name"], 0.0, "Store Purchase")), x=65, y=55, w=80)
    return pdf.output()

def generate_pdf_invoice(b):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "OFFICIAL INVOICE", ln=True, align="C"); pdf.set_font("Helvetica", "", 10); pdf.line(10, 28, 200, 28); pdf.ln(8)
    pdf.cell(100, 7, f"Order ID: #{b['order_id']}"); pdf.cell(90, 7, f"Customer: {b['cust']}", ln=True); pdf.cell(100, 7, f"Store: {b['shop']}"); pdf.ln(4)
    pdf.cell(120, 7, "Description"); pdf.cell(70, 7, "Amount", ln=True, align="R"); pdf.cell(120, 7, f"{b['item']}"); pdf.cell(70, 7, f"Rs {b['price']:,.2f}", ln=True, align="R")
    pdf.cell(120, 7, "Delivery Charges"); pdf.cell(70, 7, f"Rs {b['fee']:,.2f}", ln=True, align="R"); pdf.line(10, 85, 200, 85); pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12); pdf.cell(120, 9, "Total to Pay:"); pdf.cell(70, 9, f"Rs {b['total']:,.2f}", ln=True, align="R")
    return pdf.output()

st.sidebar.title("👑 Bharat Premium")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Marketplace", "🛒 Cart & Checkout", "📅 Scheduled Site Visits", "🚚 Track My Orders & Chat",
    "🏪 Vendor Terminal", "🛵 Rider Terminal (UPI)", "🪧 Vendor QR Standee", "💳 Vendor Wallet & Refund",
    "📦 Add Product / Property", "🏬 Register New Store", "📊 Admin Ledger"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER MARKETPLACE
# -----------------------------------------------------------
if menu == "🛍️ Customer Marketplace":
    st.markdown("<div class='premium-title'>🛍️ Discover Premium Products</div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("#### 📍 Find Stores Near Your Location")
        col_m1, col_m2 = st.columns(2)
        with col_m1: detected_lat = st.number_input("Your Latitude", value=21.1458, format="%.4f")
        with col_m2: detected_lon = st.number_input("Your Longitude", value=79.0882, format="%.4f")
    st.markdown("---")
    
    f1, f2 = st.columns([3, 1])
    with f1: search_query = st.text_input("🔍 Search any product, brand or property...", placeholder="e.g. Cotton Shirt, Plot, Rice")
    with f2: cat_filter = st.selectbox("Category", ["All Categories", "Real Estate", "Grocery", "Electronics", "Automobile", "Fashion"])

    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT p.*, v.id as v_id, v.name as v_name, v.upi_id, v.wallet_balance, v.lat as v_lat, v.lon as v_lon, v.free_delivery_above_500, v.base_1km, v.base_2km, v.per_km_extra FROM products p JOIN vendors v ON p.vendor_id = v.id', conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        if search_query and search_query.lower() not in row["title"].lower() and search_query.lower() not in row["brand"].lower(): continue
        if cat_filter != "All Categories" and row["category"] != cat_filter: continue
        dist = calculate_distance(detected_lat, detected_lon, row["v_lat"], row["v_lon"])
        fee, fee_desc = get_delivery_fee(dist, row["price"], row["free_delivery_above_500"], row["base_1km"], row["base_2km"], row["per_km_extra"])
        results.append({
            "p_id": row["id"], "brand": row["brand"], "title": row["title"], "price": row["price"], "is_high_val": row["is_high_value"],
            "advance_token": row["advance_booking_amount"], "image_url": row["image_url"], "v_id": row["v_id"], "v_name": row["v_name"],
            "v_upi": row["upi_id"], "v_wallet": row["wallet_balance"], "distance": dist, "delivery_fee": fee, "fee_desc": fee_desc,
        })
    results.sort(key=lambda x: x["distance"])

    if results:
        cols = st.columns(3) 
        for idx, item in enumerate(results):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.image(item["image_url"], use_container_width=True)
                    st.markdown(f"### {item['title']}")
                    st.caption(f"🏪 **{item['v_name']}** | 📍 {item['distance']} KM")
                    if item["is_high_val"] == 1:
                        st.markdown(f"Value: :blue[**Rs {item['price']:,.2f}**]")
                        st.markdown(f"Booking Token: :green[**Rs {item['advance_token']:,.2f}**]")
                    else:
                        st.markdown(f"Price: :green[**Rs {item['price']:,.2f}**]")

                    commission_required = round((item["advance_token"] if item["is_high_val"]==1 else item["price"]) * 0.01, 2)
                    if item["v_wallet"] < commission_required: st.error("⚠️ Store Currently Offline")
                    else:
                        if st.button("➕ Add to Cart", key=f"cart_{item['p_id']}", use_container_width=True):
                            st.session_state.cart.append(item)
                            st.toast("Item added to your Cart! Head to Checkout.", icon="🛍️")
    else: st.info("No products found nearby. Try changing your search or location.")

# -----------------------------------------------------------
# TAB 2: CART & CHECKOUT
# -----------------------------------------------------------
elif menu == "🛒 Cart & Checkout":
    st.markdown("<div class='premium-title'>🛒 Your Secure Checkout</div>", unsafe_allow_html=True)
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        with st.container(border=True):
            st.markdown("### 📦 Cart Items")
            st.dataframe(cart_df[["brand", "title", "price", "v_name", "distance"]], use_container_width=True)
            if st.button("🗑️ Clear Entire Cart", key="clear_cart"): st.session_state.cart = []; st.rerun()

        unique_vendors = cart_df["v_id"].nunique()
        if unique_vendors > 1: st.error("⚠️ Cart contains items from multiple stores. Order from one store at a time.")
        else:
            sample_item = st.session_state.cart[0]
            items_total = cart_df["price"].sum() if sample_item["is_high_val"]==0 else cart_df["advance_token"].sum()
            
            c_col1, c_col2 = st.columns([1, 1])
            with c_col1:
                with st.container(border=True):
                    st.markdown("### 🚚 Delivery Details")
                    cust_name = st.text_input("Full Name", "Rahul Sharma")
                    cust_phone = st.text_input("WhatsApp Number", "919876500000")
                    cust_address_text = st.text_area("Complete Delivery Address", "Flat 102, New Amar Nagar, Nagpur")
                    
                    if sample_item["is_high_val"] == 0:
                        del_pref = st.radio("Fulfillment Mode:", ["🚚 Home Delivery", "🚶 Self-Pickup from Store (Free)"], horizontal=True)
                        final_mode = "Pickup" if "Pickup" in del_pref else "Delivery"
                        fee = get_delivery_fee(sample_item["distance"], items_total, 1, 20.0, 30.0, 10.0)[0]
                        final_fee = 0.0 if final_mode == "Pickup" else fee
                    else:
                        final_mode = "Site Visit / Token Booking"; final_fee = 0.0

            with c_col2:
                with st.container(border=True):
                    st.markdown("### 🧾 Bill Summary")
                    st.write(f"Items Subtotal: **Rs {items_total:,.2f}**")
                    st.write(f"Delivery Fee: **Rs {final_fee:,.2f}**")
                    final_total = items_total + final_fee
                    st.markdown(f"### Grand Total: :green[**Rs {final_total:,.2f}**]")
                    st.caption("Payment Method: **UPI on Delivery** (Pay directly to store via QR code)")

                    cut_1pct = round(items_total * 0.01, 2)
                    loc_confirm = st.checkbox("📍 I confirm my address and order details are correct.")
                    
                    if loc_confirm:
                        if st.button("🚀 Place Order Now", type="primary", use_container_width=True):
                            items_summary = ", ".join([f"{x['title']}" for x in st.session_state.cart])
                            gen_otp = str(random.randint(1000, 9999))
                            
                            conn_co = sqlite3.connect(DB_NAME)
                            conn_co.execute('''INSERT INTO orders (customer_name, customer_phone, delivery_address, vendor_id, delivery_otp, items_summary, item_price, delivery_fee, grand_total, platform_commission_1pct, distance_km, delivery_mode, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Order Placed')''', 
                                (cust_name, cust_phone, cust_address_text, sample_item["v_id"], gen_otp, items_summary, items_total, final_fee, final_total, cut_1pct, sample_item["distance"], final_mode))
                            conn_co.execute('UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?', (cut_1pct, sample_item["v_id"]))
                            conn_co.commit(); order_id = conn_co.execute("SELECT last_insert_rowid()").fetchone()[0]; conn_co.close()
                            
                            st.session_state.cart = []
                            st.success(f"🎉 Order #{order_id} Placed Successfully!")
                            st.info(f"Your secret OTP is **{gen_otp}**. Please give this to the rider/store after making the UPI payment.")
                            st.balloons()
                    else: st.warning("Please tick the confirmation checkbox to place your order.")
    else: st.info("🛒 Your cart is completely empty.")

# -----------------------------------------------------------
# TAB 3: SCHEDULED SITE VISITS
# -----------------------------------------------------------
elif menu == "📅 Scheduled Site Visits":
    st.markdown("<div class='premium-title'>📅 Site Visits & Consultations</div>", unsafe_allow_html=True)
    conn_v = sqlite3.connect(DB_NAME)
    sv_df = pd.read_sql_query('SELECT sv.id, sv.customer_name, sv.customer_phone, sv.visit_date, sv.visit_time, sv.status, p.brand, p.title, v.name as firm_name FROM site_visits sv JOIN products p ON sv.product_id = p.id JOIN vendors v ON sv.vendor_id = v.id ORDER BY sv.created_at DESC', conn_v)
    conn_v.close()
    if not sv_df.empty: st.dataframe(sv_df, use_container_width=True)
    else: st.info("No site visits scheduled yet.")

# -----------------------------------------------------------
# TAB 4: TRACK MY ORDERS & CHAT
# -----------------------------------------------------------
elif menu == "🚚 Track My Orders & Chat":
    st.markdown("<div class='premium-title'>🚚 Track Orders & Direct Chat</div>", unsafe_allow_html=True)
    t_phone = st.text_input("Enter your Registered WhatsApp Phone Number:", value="919876500000")
    conn = sqlite3.connect(DB_NAME)
    my_orders = pd.read_sql_query('SELECT o.*, v.name as shop_name, v.phone as shop_phone FROM orders o JOIN vendors v ON o.vendor_id = v.id WHERE o.customer_phone = ? ORDER BY o.created_at DESC', conn, params=(t_phone,))
    
    if not my_orders.empty:
        for _, o_row in my_orders.iterrows():
            with st.container(border=True):
                c_t1, c_t2 = st.columns([3, 2])
                with c_t1:
                    st.markdown(f"### Order #{o_row['id']} - {o_row['items_summary']}")
                    st.write(f"🏬 **Store:** {o_row['shop_name']} | 📍 Distance: `{o_row['distance_km']} KM`")
                    st.write(f"**Amount:** :green[**Rs {o_row['grand_total']:,.2f}**] | Payment: `{o_row['payment_status']}`")
                    st.warning(f"🔒 **Your Delivery OTP:** `{o_row['delivery_otp']}`")
                    
                    status = o_row['status']
                    if status == "Order Placed": st.warning("🟡 Status: **Order Placed (Waiting for Store Dispatch)**")
                    elif status == "Accepted by Rider": st.info("🚴 Status: **Rider Accepted Order - Pick up in progress**")
                    elif status == "Dispatched": st.info("🔵 Status: **Out for Delivery** 🚚")
                    elif status == "Delivered": 
                        st.success("🟢 Status: **Delivered Successfully** ✅")
                        with st.expander("⭐ Leave a Review for this Store"):
                            with st.form(f"rev_form_{o_row['id']}"):
                                star_val = st.slider("Star Rating (1 to 5)", 1, 5, 5)
                                rev_txt = st.text_input("Feedback", placeholder="Great product!")
                                if st.form_submit_button("Submit Rating"):
                                    conn.execute("INSERT INTO reviews (vendor_id, customer_name, rating, review_text) VALUES (?, ?, ?, ?)", (o_row['vendor_id'], "Rahul Sharma", star_val, rev_txt))
                                    conn.commit(); st.success("Rating saved!")

                with c_t2:
                    st.markdown("#### 💬 Live In-App Chat")
                    msgs = pd.read_sql_query("SELECT * FROM messages WHERE order_id = ? ORDER BY sent_at ASC", conn, params=(o_row['id'],))
                    if not msgs.empty:
                        for _, m_row in msgs.iterrows(): st.write(f"**{m_row['sender_name']}:** {m_row['message_text']}")
                    
                    with st.form(f"chat_form_{o_row['id']}"):
                        msg_input = st.text_input("Type message / instructions...", key=f"msg_in_{o_row['id']}")
                        if st.form_submit_button("Send") and msg_input:
                            conn.execute("INSERT INTO messages (order_id, sender_name, message_text) VALUES (?, ?, ?)", (o_row['id'], "Customer", msg_input))
                            conn.commit(); st.rerun()
    else: st.info("No orders found for this phone number.")
    conn.close()

# -----------------------------------------------------------
# TAB 5: VENDOR TERMINAL
# -----------------------------------------------------------
elif menu == "🏪 Vendor Terminal":
    st.markdown("<div class='premium-title'>🔔 Store Fulfillment Dashboard</div>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    
    if not vendors_df.empty:
        selected_vid = st.selectbox("Select Shop Terminal", vendors_df["id"].tolist(), format_func=lambda x: f"{vendors_df[vendors_df['id'] == x]['name'].values[0]} (Wallet: Rs {vendors_df[vendors_df['id'] == x]['wallet_balance'].values[0]:,.2f})")
        v_orders = pd.read_sql_query("SELECT * FROM orders WHERE vendor_id = ? ORDER BY created_at DESC LIMIT 10", conn, params=(selected_vid,))
        
        if not v_orders.empty:
            for _, ord_row in v_orders.iterrows():
                with st.container(border=True):
                    col_o1, col_o2, col_o3 = st.columns([2, 2, 2])
                    with col_o1:
                        st.markdown(f"**Order #{ord_row['id']}** | Customer: `{ord_row['customer_name']}`")
                        st.write(f"Address: `{ord_row['delivery_address']}`")
                        st.write(f"Collect via UPI: :green[**Rs {ord_row['grand_total']:,.2f}**]")
                    with col_o2:
                        st.write(f"Mode: **{ord_row['delivery_mode']}**")
                        st.write(f"Status: `{ord_row['status']}`")
                        if "Paid" in ord_row['payment_status']: st.success(f"✅ {ord_row['payment_status']}")
                        else: st.warning(f"⏳ {ord_row['payment_status']}")
                    with col_o3:
                        if ord_row["status"] == "Order Placed":
                            if ord_row['delivery_mode'] == "Pickup":
                                if st.button("✅ Confirm Picked Up & Paid", key=f"pu_{ord_row['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ord_row['id'],)); conn.commit(); st.rerun()
                            elif ord_row['delivery_mode'] == "Delivery":
                                if st.button("Self-Dispatch (Own Boy)", key=f"sd_{ord_row['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ord_row['id'],)); conn.commit(); st.rerun()
                                if ord_row['grand_total'] <= 5000:
                                    if st.button("🛵 Request Platform Rider", type="primary", key=f"rr_{ord_row['id']}"):
                                        conn.execute("UPDATE orders SET status = 'Rider Requested' WHERE id = ?", (ord_row['id'],)); conn.commit(); st.rerun()
                                else: st.error("⚠️ Order > Rs 5000. Use Self-Dispatch.")
                        elif ord_row["status"] == "Dispatched" and ord_row['rider_id'] == 0:
                            if st.button("✅ Mark Delivered & Paid", key=f"md_{ord_row['id']}"):
                                conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ord_row['id'],)); conn.commit(); st.rerun()

                        msgs = pd.read_sql_query("SELECT message_text FROM messages WHERE order_id = ? AND sender_name = 'System'", conn, params=(ord_row['id'],))
                        for _, m in msgs.iterrows(): st.info(m['message_text'])
        else: st.info("No orders received yet for this store.")
    conn.close()

# -----------------------------------------------------------
# TAB 6: RIDER TERMINAL
# -----------------------------------------------------------
elif menu == "🛵 Rider Terminal (UPI)":
    st.markdown("<div class='premium-title'>🛵 Delivery Partner Dashboard</div>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    riders_df = pd.read_sql_query("SELECT * FROM riders WHERE status = 'Active'", conn)
    
    if riders_df.empty: st.warning("No active riders.")
    else:
        selected_rider_id = st.selectbox("Select Rider Profile", riders_df["id"].tolist(), format_func=lambda x: riders_df[riders_df['id'] == x]['name'].values[0])
        curr_rider = riders_df[riders_df["id"] == selected_rider_id].iloc[0]
        st.metric("Rider Security Deposit", f"Rs {curr_rider['wallet_balance']:,.2f}")
        
        r_orders = pd.read_sql_query("SELECT o.*, v.name as shop_name, v.address as shop_address, v.upi_id as shop_upi FROM orders o JOIN vendors v ON o.vendor_id = v.id WHERE o.status = 'Rider Requested' OR (o.status IN ('Accepted by Rider', 'Dispatched') AND o.rider_id = ?) ORDER BY o.created_at DESC", conn, params=(selected_rider_id,))
        if not r_orders.empty:
            for _, ro in r_orders.iterrows():
                with st.container(border=True):
                    col_r1, col_r2 = st.columns([3, 2])
                    with col_r1:
                        st.write(f"**Order #{ro['id']}** | Pickup: **{ro['shop_name']}**")
                        st.write(f"📍 Drop: `{ro['delivery_address']}`")
                    with col_r2:
                        if ro["status"] == "Rider Requested":
                            if curr_rider['wallet_balance'] < 5000: st.error("⚠️ Rs 5000 Security required.")
                            elif st.button("🚴 Accept Delivery", key=f"acc_{ro['id']}"):
                                conn.execute("UPDATE orders SET status = 'Accepted by Rider', rider_id = ? WHERE id = ?", (selected_rider_id, ro['id'])); conn.commit(); st.rerun()
                        elif ro["status"] == "Accepted by Rider":
                            if st.button("🚚 Picked Up", key=f"disp_r_{ro['id']}"):
                                conn.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ro['id'],)); conn.commit(); st.rerun()
                        elif ro["status"] == "Dispatched":
                            st.warning(f"Scan & Pay **Rs {ro['grand_total']:,.2f}** directly to **{ro['shop_name']}**:")
                            st.image(generate_upi_qr(ro['shop_upi'], ro['shop_name'], ro['grand_total'], f"Order_{ro['id']}"), width=150)
                            otp_in = st.text_input("Customer OTP", key=f"otp_{ro['id']}")
                            if st.button("✅ Verify & Complete", key=f"comp_{ro['id']}"):
                                if otp_in == str(ro['delivery_otp']):
                                    conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ro['id'],))
                                    conn.execute("INSERT INTO messages (order_id, sender_name, message_text) VALUES (?, 'System', ?)", (ro['id'], f"✅ Rs {ro['grand_total']:,.2f} Collected by Rider."))
                                    conn.commit(); st.success("Completed!"); st.rerun()
                                else: st.error("❌ Invalid OTP!")
    conn.close()

# -----------------------------------------------------------
# TAB 7: VENDOR QR STANDEE
# -----------------------------------------------------------
elif menu == "🪧 Vendor QR Standee":
    st.markdown("<div class='premium-title'>🪧 Download Official QR Standee</div>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()
    if not vendors_df.empty:
        selected_vid = st.selectbox("Select Shop", vendors_df["id"].tolist(), format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0])
        curr_v = vendors_df[vendors_df["id"] == selected_vid].iloc[0]
        st.info(f"Generating Standee for **{curr_v['name']}**")
        standee_pdf_bytes = generate_standee_pdf(curr_v)
        st.download_button("🖨️ Download PDF Counter Standee", data=bytes(standee_pdf_bytes), file_name=f"Standee_{curr_v['name'].replace(' ', '_')}.pdf", mime="application/pdf")

# -----------------------------------------------------------
# TAB 8: VENDOR WALLET & REFUND
# -----------------------------------------------------------
elif menu == "💳 Vendor Wallet & Refund":
    st.markdown("<div class='premium-title'>💳 Store Wallet & Refund Manager</div>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()
    if not vendors_df.empty:
        v_select = st.selectbox("Select Store Account", vendors_df["id"].tolist(), format_func=lambda x: f"{vendors_df[vendors_df['id'] == x]['name'].values[0]}")
        curr_vendor = vendors_df[vendors_df["id"] == v_select].iloc[0]

        w1, w2 = st.columns([1, 1])
        with w1:
            with st.container(border=True):
                st.markdown("### 💰 Your In-App Wallet Balance")
                st.metric("Safe Unused Balance", f"Rs {curr_vendor['wallet_balance']:,.2f}")
                if curr_vendor['wallet_balance'] < 10.0: st.error("🚨 Low Balance! Store Offline.")
                else: st.success("🟢 Store is ACTIVE.")

                st.markdown("---")
                st.markdown("#### 🔄 Withdraw Remaining Balance")
                withdraw_request = curr_vendor['wallet_balance']
                processing_fee = max(round(withdraw_request * 0.02, 2), 3.0)
                
                if withdraw_request > processing_fee:
                    refund_amt = withdraw_request - processing_fee
                    st.write(f"Withdrawal Processing Fee (2%): :red[**- Rs {processing_fee:,.2f}**]")
                    if st.button("💸 Request Balance Withdrawal"):
                        conn_wd = sqlite3.connect(DB_NAME)
                        conn_wd.execute("UPDATE vendors SET wallet_balance = 0.0 WHERE id = ?", (v_select,))
                        conn_wd.execute("INSERT INTO wallet_logs (vendor_id, txn_type, amount, txn_ref, status) VALUES (?, 'WITHDRAWAL_REQUEST', ?, ?, 'Pending Admin Approval')", 
                                        (v_select, refund_amt, f"Refund to UPI: {curr_vendor['upi_id']} (Rs {processing_fee} Fee Deducted)"))
                        conn_wd.commit(); conn_wd.close(); st.success(f"🎉 रिक्वेस्ट भेज दी गई है!"); st.rerun()
                elif withdraw_request > 0: st.error(f"⚠️ Balance too low to cover Rs {processing_fee:,.2f} fee.")

        with w2:
            with st.container(border=True):
                st.markdown("### ⚡ Top-Up In-App Wallet")
                topup_amt = st.radio("Select Top-Up Amount", [100.0, 150.0, 200.0, 500.0], index=1, horizontal=True)
                p_qr = generate_upi_qr(PLATFORM_UPI_ID, "Bharat Platform Admin", topup_amt, f"Wallet_Store_{curr_vendor['id']}")
                st.image(p_qr, width=170)
                
                txn_ref_in = st.text_input("Enter 12-Digit UPI Ref / UTR No.")
                if st.button("✅ Add Balance to My Wallet") and txn_ref_in:
                    conn_tu = sqlite3.connect(DB_NAME)
                    conn_tu.execute("UPDATE vendors SET wallet_balance = wallet_balance + ? WHERE id = ?", (topup_amt, v_select))
                    conn_tu.execute("INSERT INTO wallet_logs (vendor_id, txn_type, amount, txn_ref, status) VALUES (?, 'TOP-UP', ?, ?, 'Completed')", (v_select, topup_amt, txn_ref_in))
                    conn_tu.commit(); conn_tu.close(); st.success(f"🎉 Rs {topup_amt:,.2f} added!"); st.rerun()

        st.markdown("---")
        st.write("### 📜 Wallet History")
        conn_l = sqlite3.connect(DB_NAME)
        logs_df = pd.read_sql_query("SELECT * FROM wallet_logs WHERE vendor_id = ? ORDER BY created_at DESC", conn_l, params=(v_select,))
        conn_l.close()
        if not logs_df.empty: st.dataframe(logs_df, use_container_width=True)

# -----------------------------------------------------------
# TAB 9: ADD PRODUCT / PROPERTY LISTING (WITH AI CAMERA SCANNER)
# -----------------------------------------------------------
elif menu == "📦 Add Product / Property":
    st.markdown("<div class='premium-title'>📦 Smart AI Product Listing</div>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    t1, t2 = st.tabs(["📸 AI Camera Scanner", "⚙️ Store Settings"])
    
    with t1:
        st.info("💡 **Tip:** प्रोडक्ट के डब्बे या MRP लेबल की फोटो खींचें, Google Gemini AI अपने आप MRP, ब्रांड और नाम पढ़कर फॉर्म भर देगा!")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            api_key = st.text_input("🔑 Enter Free Google Gemini API Key", type="password", help="AI Scanner चलाने के लिए Gemini API Key डालें")
            if not api_key: st.caption("👉 Google AI Studio से फ्री API key जनरेट करें।")
            
        scanned_image = st.camera_input("📸 Scan Product Box / Label")

        if scanned_image is not None and api_key:
            if st.button("✨ Extract Details using AI", use_container_width=True, type="primary"):
                with st.spinner("🧠 AI is analyzing MRP, Brand and Product Name..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        img = Image.open(scanned_image)
                        
                        prompt = """
                        Extract the following product details from the image in strict JSON format:
                        {
                            "brand": "Brand Name",
                            "title": "Product Title/Name",
                            "price": <numeric value of MRP or Price, numbers only>,
                            "desc": "Short description, ingredients, or key features"
                        }
                        Return ONLY valid JSON.
                        """
                        response = model.generate_content([prompt, img], generation_config={"response_mime_type": "application/json"})
                        data = json.loads(response.text)
                        
                        st.session_state.scanned_data["brand"] = data.get("brand", "")
                        st.session_state.scanned_data["title"] = data.get("title", "")
                        st.session_state.scanned_data["price"] = float(data.get("price", 0.0))
                        st.session_state.scanned_data["desc"] = data.get("desc", "")
                        
                        st.success("✅ AI Scan Complete! Details Auto-filled below. Please verify and publish.")
                    except Exception as e:
                        st.error(f"Scan Error: Please check API Key or Image clarity. Details: {e}")

        # --- The Product Form (Values linked to Session State) ---
        st.markdown("### 📝 Edit & Publish Listing")
        with st.form("prod_form"):
            s_id = st.selectbox("Select Store", vendors_df["id"].tolist(), format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0])
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                b_name = st.text_input("Brand / Company Name", value=st.session_state.scanned_data["brand"])
                p_name = st.text_input("Product Title", value=st.session_state.scanned_data["title"])
                p_cat = st.selectbox("Category", ["Grocery", "Electronics", "Fashion", "Real Estate", "Automobile"])
                is_high = st.checkbox("High-Value Property/Vehicle?", value=False)
            with c_p2:
                # Use AI Extracted MRP/Price
                p_val = st.number_input("Full Selling Price / MRP (Rs)", min_value=1.0, value=max(1.0, float(st.session_state.scanned_data["price"])), step=10.0)
                adv_val = st.number_input("Advance Token (if High-Value)", min_value=0.0, value=11000.0 if is_high else 0.0)
                img_link = st.text_input("Cover Image URL", placeholder="https://via.placeholder.com/200")
                p_desc = st.text_area("Full Description", value=st.session_state.scanned_data["desc"])

            if st.form_submit_button("🚀 Publish Listing"):
                if b_name and p_name:
                    conn_i = sqlite3.connect(DB_NAME)
                    conn_i.execute('''INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, image_url, description)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (s_id, b_name, p_name, p_cat, p_val, 1 if is_high else 0, adv_val, img_link, p_desc))
                    conn_i.commit(); conn_i.close()
                    # Reset scanned data
                    st.session_state.scanned_data = {"brand": "", "title": "", "price": 0.0, "desc": ""}
                    st.success("✅ Listed successfully!"); st.rerun()

    with t2:
        for _, v in vendors_df.iterrows():
            with st.expander(f"📍 {v['name']} ({v['city']})"):
                toggle_free = st.toggle("Offer FREE Delivery above Rs 500", value=bool(v["free_delivery_above_500"]), key=f"f_{v['id']}")
                toggle_spon = st.toggle("Enable Sponsored Top Badge", value=bool(v["is_sponsored"]), key=f"sp_{v['id']}")
                if st.button("Save Settings", key=f"s_{v['id']}"):
                    conn_s = sqlite3.connect(DB_NAME)
                    conn_s.execute("UPDATE vendors SET free_delivery_above_500 = ?, is_sponsored = ? WHERE id = ?", (1 if toggle_free else 0, 1 if toggle_spon else 0, v["id"]))
                    conn_s.commit(); conn_s.close(); st.success("Updated!"); st.rerun()

# -----------------------------------------------------------
# TAB 10: REGISTER NEW STORE
# -----------------------------------------------------------
elif menu == "🏬 Register New Store":
    st.markdown("<div class='premium-title'>🏬 Enterprise & Rider Onboarding</div>", unsafe_allow_html=True)
    ob_tab1, ob_tab2 = st.tabs(["🏪 Register Shop", "🛵 Register Rider"])
    
    with ob_tab1:
        with st.form("shop_form"):
            s_c1, s_c2 = st.columns(2)
            with s_c1:
                name = st.text_input("Store Name")
                phone = st.text_input("WhatsApp Phone")
                upi = st.text_input("Store UPI ID for Payments")
                city = st.text_input("City")
            with s_c2:
                lat = st.number_input("GPS Latitude", value=21.1450, format="%.4f")
                lon = st.number_input("GPS Longitude", value=79.0800, format="%.4f")
                b1 = st.number_input("1 KM Fee (Rs)", value=20.0)
                b2 = st.number_input("2 KM Fee (Rs)", value=30.0)
                pe = st.number_input("Extra KM Fee (Rs)", value=10.0)

            if st.form_submit_button("✅ Register Store") and name and upi:
                conn_r = sqlite3.connect(DB_NAME)
                conn_r.execute('''INSERT INTO vendors (name, phone, upi_id, city, lat, lon, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
                                  VALUES (?, ?, ?, ?, ?, ?, 0.0, 1, ?, ?, ?)''', (name, phone, upi, city, lat, lon, b1, b2, pe))
                conn_r.commit(); conn_r.close(); st.success(f"🎉 Store '{name}' registered!")

    with ob_tab2:
        with st.form("rider_reg_form"):
            r_name = st.text_input("Rider Name"); r_phone = st.text_input("WhatsApp Phone")
            r_city = st.text_input("City"); r_veh = st.text_input("Vehicle Number")
            if st.form_submit_button("🛵 Register Rider") and r_name and r_phone:
                try:
                    conn_rd = sqlite3.connect(DB_NAME)
                    conn_rd.execute("INSERT INTO riders (name, phone, city, vehicle_number, wallet_balance, status) VALUES (?, ?, ?, ?, 0.0, 'Pending')", (r_name, r_phone, r_city, r_veh))
                    conn_rd.commit(); conn_rd.close(); st.success(f"🎉 {r_name} registered! Deposit Rs 5,000 via Admin.")
                except Exception: st.error("Phone number already registered.")

# -----------------------------------------------------------
# TAB 11: PLATFORM EARNINGS LEDGER
# -----------------------------------------------------------
else:
    st.markdown("<div class='premium-title'>📊 Platform Earnings Ledger</div>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    pending_withdrawals = pd.read_sql_query("SELECT * FROM wallet_logs WHERE status = 'Pending Admin Approval'", conn)
    conn.close()

    total_comm = orders_df["platform_commission_1pct"].sum() if not orders_df.empty else 0.0

    m1, m2 = st.columns(2)
    m1.metric("Total 1% Pure Commission Earned", f"Rs {total_comm:,.2f}", delta="Auto-Debited on Sales")
    m2.metric("Pending Withdrawal Requests", len(pending_withdrawals))
    st.markdown("---")
    
    an1, an2 = st.columns(2)
    with an1:
        st.write("### 📜 Commission Deductions:")
        if not orders_df.empty: st.dataframe(orders_df[["id", "customer_name", "grand_total", "platform_commission_1pct", "created_at"]], use_container_width=True)
        else: st.info("No orders placed yet.")

    with an2:
        st.write("### ⚡ Pending Vendor Withdrawals")
        if not pending_withdrawals.empty:
            for _, w_row in pending_withdrawals.iterrows():
                with st.container(border=True):
                    st.write(f"**Vendor ID #{w_row['vendor_id']}** requested **Rs {w_row['amount']:,.2f}**")
                    st.info(f"Details: `{w_row['txn_ref']}`")
                    if st.button("✅ Mark Paid (Approve)", key=f"approve_{w_row['id']}"):
                        conn_ap = sqlite3.connect(DB_NAME)
                        conn_ap.execute("UPDATE wallet_logs SET status = 'Refund Completed' WHERE id = ?", (w_row['id'],))
                        conn_ap.commit(); conn_ap.close(); st.success("Marked as Paid!"); st.rerun()
        else: st.success("No pending requests!")