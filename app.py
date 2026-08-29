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
    page_title="Bharat Premium Hyperlocal Platform",
    page_icon="👑",
    layout="wide"
)

# ==========================================
# 💎 PREMIUM LUXURY CSS INJECTION
# ==========================================
st.markdown("""
<style>
/* 1. Sidebar Background (Single Luxury Dark Color) */
[data-testid="stSidebar"] {
    background-color: #0b0f19 !important;
}

/* Sidebar Title - Premium Gold */
[data-testid="stSidebar"] h1 {
    color: #E5B80B !important; 
    font-family: 'Georgia', serif !important;
    letter-spacing: 1.5px;
    text-shadow: 0px 2px 4px rgba(229, 184, 11, 0.3);
}

/* 2. Menu Text Multi-Color Logic */
div[role="radiogroup"] > label:nth-child(1) p { color: #FFD700 !important; font-weight: 600; font-size: 16px; } /* Gold */
div[role="radiogroup"] > label:nth-child(2) p { color: #00FA9A !important; font-weight: 600; font-size: 16px; } /* Spring Green */
div[role="radiogroup"] > label:nth-child(3) p { color: #FF69B4 !important; font-weight: 600; font-size: 16px; } /* Hot Pink */
div[role="radiogroup"] > label:nth-child(4) p { color: #00BFFF !important; font-weight: 600; font-size: 16px; } /* Sky Blue */
div[role="radiogroup"] > label:nth-child(5) p { color: #FF7F50 !important; font-weight: 600; font-size: 16px; } /* Coral */
div[role="radiogroup"] > label:nth-child(6) p { color: #DDA0DD !important; font-weight: 600; font-size: 16px; } /* Plum */
div[role="radiogroup"] > label:nth-child(7) p { color: #F0E68C !important; font-weight: 600; font-size: 16px; } /* Khaki */
div[role="radiogroup"] > label:nth-child(8) p { color: #20B2AA !important; font-weight: 600; font-size: 16px; } /* Sea Green */
div[role="radiogroup"] > label:nth-child(9) p { color: #FF6347 !important; font-weight: 600; font-size: 16px; } /* Tomato */
div[role="radiogroup"] > label:nth-child(10) p { color: #87CEFA !important; font-weight: 600; font-size: 16px; } /* Light Sky Blue */
div[role="radiogroup"] > label:nth-child(11) p { color: #FFE4B5 !important; font-weight: 600; font-size: 16px; } /* Moccasin */

/* Hide default radio circle for cleaner look */
div[role="radiogroup"] > label span[data-baseweb="radio"] {
    border-color: #E5B80B !important;
    background-color: transparent !important;
}
div[role="radiogroup"] > label span[data-baseweb="radio"] div {
    background-color: #E5B80B !important;
}

/* 3. Premium Main Page Background */
.stApp {
    background: linear-gradient(135deg, #f6f8fd 0%, #f1f6f9 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* 4. Luxury 3D Cards (Glassmorphism + Gold Accents) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06) !important;
    border: 1px solid rgba(229, 184, 11, 0.4) !important; /* Gold Border */
    background: rgba(255, 255, 255, 0.85) !important;
    backdrop-filter: blur(10px);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    padding: 10px;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 32px rgba(229, 184, 11, 0.15) !important; /* Gold Glow on hover */
    border: 1px solid rgba(229, 184, 11, 0.9) !important;
}

/* 5. Premium Gold/Blue Buttons */
.stButton > button {
    background: linear-gradient(135deg, #D4AF37 0%, #AA7C11 100%) !important;
    color: #ffffff !important;
    border-radius: 30px !important;
    border: none !important;
    font-weight: bold !important;
    letter-spacing: 1px;
    box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4) !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #AA7C11 0%, #D4AF37 100%) !important;
    box-shadow: 0 6px 20px rgba(212, 175, 55, 0.6) !important;
    transform: scale(1.03);
}

/* Primary Buttons (Dark Royal Blue) */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
    box-shadow: 0 4px 15px rgba(30, 60, 114, 0.4) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(30, 60, 114, 0.6) !important;
}

/* Elegant Headers */
h1, h2, h3 {
    font-family: 'Georgia', serif !important;
    color: #1a202c !important;
    text-shadow: 0px 1px 2px rgba(0,0,0,0.05);
}

/* Stylish Alerts */
.stAlert {
    border-radius: 12px !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
}
</style>
""", unsafe_allow_html=True)
# ==========================================


DB_NAME = "hyperlocal_market.db"
PLATFORM_UPI_ID = "adminplatform@upi"

# -----------------------------------------------------------
# 1. DATABASE SETUP
# -----------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Vendors
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT DEFAULT '919876543210',
        upi_id TEXT DEFAULT 'merchant@upi', city TEXT NOT NULL, address TEXT, gstin TEXT DEFAULT 'NON-GST',
        rera_id TEXT DEFAULT 'N/A', is_kyc_verified INTEGER DEFAULT 1, is_sponsored INTEGER DEFAULT 0,
        lat REAL NOT NULL, lon REAL NOT NULL, rating REAL DEFAULT 4.8, wallet_balance REAL DEFAULT 150.0,
        free_delivery_above_500 INTEGER DEFAULT 1, base_1km REAL DEFAULT 20.0, base_2km REAL DEFAULT 30.0, per_km_extra REAL DEFAULT 10.0
    )''')
    vendor_cols = [col[1] for col in c.execute("PRAGMA table_info(vendors)").fetchall()]
    if "wallet_balance" not in vendor_cols: c.execute("ALTER TABLE vendors ADD COLUMN wallet_balance REAL DEFAULT 150.0")

    # 2. Riders
    c.execute('''CREATE TABLE IF NOT EXISTS riders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
        city TEXT NOT NULL, vehicle_number TEXT, wallet_balance REAL DEFAULT 0.0, status TEXT DEFAULT 'Active'
    )''')

    # 3. Products
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id INTEGER NOT NULL, brand TEXT NOT NULL,
        title TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL, is_high_value INTEGER DEFAULT 0,
        advance_booking_amount REAL DEFAULT 0.0, video_url TEXT DEFAULT '', image_url TEXT DEFAULT '', description TEXT,
        FOREIGN KEY (vendor_id) REFERENCES vendors (id)
    )''')

    # 4. Orders
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

    # 5. Other Tables
    c.execute("CREATE TABLE IF NOT EXISTS wallet_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id INTEGER, txn_type TEXT, amount REAL, txn_ref TEXT, status TEXT DEFAULT 'Completed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS site_visits (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, vendor_id INTEGER, customer_name TEXT, customer_phone TEXT, visit_date TEXT, visit_time TEXT, status TEXT DEFAULT 'Confirmed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, sender_name TEXT, message_text TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS coupons (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, discount_pct REAL DEFAULT 10.0, min_order_value REAL DEFAULT 200.0, is_active INTEGER DEFAULT 1)")

    # Default Data Seed
    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO vendors (name, phone, upi_id, city, address, gstin, rera_id, is_kyc_verified, is_sponsored, lat, lon, rating, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
            VALUES ('Mamta General & Cloth Store', '919876543210', 'mamtastore@upi', 'Nagpur', 'Main Market', '27ABCDE1234F1Z5', 'N/A', 1, 1, 21.1458, 79.0882, 4.9, 150.0, 1, 20.0, 30.0, 10.0),
                   ('First Choice Infra & Deals Hub', '919876543211', 'firstchoice@upi', 'Nagpur', 'Wardha Road / Besa', '27WXYZ8910G2Z1', 'MAHARERA/P5050001234', 1, 1, 21.1000, 79.0700, 4.9, 500.0, 0, 20.0, 30.0, 10.0)''')
        c.execute('''INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, video_url, image_url, description)
            VALUES (1, 'Cotton King', 'Premium Cotton Shirt', 'Fashion', 1000.0, 0, 0.0, '', 'https://via.placeholder.com/200', 'Pure breathable formal shirt'),
                   (2, 'Sai Samruddhi City', 'Residential NA Plot 1200 Sq.Ft.', 'Real Estate', 1500000.0, 1, 21000.0, '', 'https://via.placeholder.com/200', 'NMRDA Sanctioned RL plot with cement road, water & electricity')''')
        c.execute("INSERT INTO riders (name, phone, city, vehicle_number, wallet_balance, status) VALUES ('Amit Kumar (Rider)', '919876540001', 'Nagpur', 'MH-31-AB-1234', 5000.0, 'Active')")
        c.execute("INSERT INTO coupons (code, discount_pct, min_order_value, is_active) VALUES ('BHARAT10', 10.0, 100.0, 1)")
    
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

def generate_standee_pdf(vendor):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "BHARAT DIGITAL NETWORK", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 14); pdf.cell(0, 10, f"OFFICIAL STORE: {vendor['name']}", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10); pdf.cell(0, 6, f"Address: {vendor['address']}, {vendor['city']} | GST: {vendor['gstin']}", ln=True, align="C")
    pdf.line(10, 45, 200, 45); pdf.ln(12)
    qr_bytes = generate_upi_qr(vendor["upi_id"], vendor["name"], 0.0, "Store Purchase")
    qr_img = io.BytesIO(qr_bytes); pdf.image(qr_img, x=65, y=55, w=80)
    pdf.set_y(145); pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 8, f"UPI ID: {vendor['upi_id']}", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 11); pdf.cell(0, 8, "Scan to pay directly via UPI", ln=True, align="C")
    return pdf.output()

def generate_pdf_invoice(bill_data):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "BHARAT HYPERLOCAL MARKETPLACE", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10); pdf.cell(0, 6, f"Official Digital Bill / Receipt", ln=True, align="C")
    pdf.line(10, 28, 200, 28); pdf.ln(8)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 7, f"Order ID: #{bill_data['order_id']}")
    pdf.cell(90, 7, f"Customer: {bill_data['cust']}", ln=True)
    pdf.cell(100, 7, f"Store: {bill_data['shop']}")
    pdf.cell(90, 7, f"Address: {bill_data['address']}", ln=True); pdf.ln(4)
    pdf.line(10, 50, 200, 50); pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(120, 7, "Description"); pdf.cell(70, 7, "Amount (INR)", ln=True, align="R")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(120, 7, f"{bill_data['item']}"); pdf.cell(70, 7, f"Rs {bill_data['price']:,.2f}", ln=True, align="R")
    
    if bill_data.get('discount', 0) > 0:
        pdf.cell(120, 7, "Coupon Discount Applied"); pdf.cell(70, 7, f"- Rs {bill_data['discount']:,.2f}", ln=True, align="R")
        
    pdf.cell(120, 7, "Delivery Charges"); pdf.cell(70, 7, f"Rs {bill_data['fee']:,.2f}", ln=True, align="R")
    pdf.line(10, 85, 200, 85); pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 9, "Total to Pay Store (UPI on Delivery):"); pdf.cell(70, 9, f"Rs {bill_data['total']:,.2f}", ln=True, align="R")
    return pdf.output()

# -----------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------
st.sidebar.title("👑 Bharat Premium")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Marketplace",
    "🛒 Cart & Checkout",
    "📅 Scheduled Site Visits",
    "🚚 Track My Orders & Chat",
    "🏪 Vendor Terminal",
    "🛵 Rider Terminal (UPI)",
    "🪧 Vendor QR Standee",
    "💳 Vendor Wallet & Refund",
    "📦 Add Product / Property",
    "🏬 Register New Store",
    "📊 Platform Earnings Ledger"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER MARKETPLACE
# -----------------------------------------------------------
if menu == "🛍️ Customer Marketplace":
    st.markdown("<h2>📍 Discover Premium Stores & Properties</h2>", unsafe_allow_html=True)
    
    loc_mode = st.radio("Choose Delivery Location Method:", ["📍 Auto-Detect (Current GPS)", "🏠 Enter Manual Location"], horizontal=True)
    
    detected_lat, detected_lon = 21.1458, 79.0882
    cust_address_text = "Current GPS Location"

    if loc_mode == "📍 Auto-Detect (Current GPS)":
        live_loc = get_geolocation()
        if live_loc and 'coords' in live_loc:
            detected_lat = live_loc['coords']['latitude']
            detected_lon = live_loc['coords']['longitude']
    else:
        cust_address_text = st.text_input("Enter Full Delivery Address & City (e.g., New Amar Nagar, Nagpur)", "New Amar Nagar, Nagpur")
        col_m1, col_m2 = st.columns(2)
        with col_m1: detected_lat = st.number_input("Latitude", value=21.1000, format="%.4f")
        with col_m2: detected_lon = st.number_input("Longitude", value=79.0700, format="%.4f")

    c1, c2 = st.columns(2)
    with c1: cust_name = st.text_input("Name", value="Rahul Sharma")
    with c2: cust_phone = st.text_input("WhatsApp", value="919876500000")
    st.markdown("---")
    
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1: search_query = st.text_input("🔍 Search item or property:", "")
    with f2: cat_filter = st.selectbox("Category Filter", ["All Categories", "Real Estate", "Grocery", "Electronics", "Automobile", "Fashion"])
    with f3: price_range = st.selectbox("Budget Filter", ["All Prices", "Under Rs 500", "Rs 500 - Rs 5,000", "High-Value Deals (Above Rs 50,000)"])

    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT p.*, v.id as v_id, v.name as v_name, v.upi_id, v.wallet_balance, v.lat as v_lat, v.lon as v_lon, v.free_delivery_above_500, v.base_1km, v.base_2km, v.per_km_extra FROM products p JOIN vendors v ON p.vendor_id = v.id', conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        if search_query and search_query.lower() not in row["title"].lower() and search_query.lower() not in row["brand"].lower(): continue
        if cat_filter != "All Categories" and row["category"] != cat_filter: continue
        if price_range == "Under Rs 500" and row["price"] >= 500: continue
        elif price_range == "Rs 500 - Rs 5,000" and (row["price"] < 500 or row["price"] > 5000): continue
        elif price_range == "High-Value Deals (Above Rs 50,000)" and row["price"] < 50000: continue

        dist = calculate_distance(detected_lat, detected_lon, row["v_lat"], row["v_lon"])
        fee, fee_desc = get_delivery_fee(dist, row["price"], row["free_delivery_above_500"], row["base_1km"], row["base_2km"], row["per_km_extra"])
        results.append({
            "p_id": row["id"], "brand": row["brand"], "title": row["title"], "price": row["price"], "is_high_val": row["is_high_value"],
            "advance_token": row["advance_booking_amount"], "image_url": row["image_url"], "v_id": row["v_id"], "v_name": row["v_name"],
            "v_upi": row["upi_id"], "v_wallet": row["wallet_balance"], "distance": dist, "delivery_fee": fee, "fee_desc": fee_desc,
            "v_lat": row["v_lat"], "v_lon": row["v_lon"]
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
                        if item["is_high_val"] == 1:
                            st.markdown(f"Total Valuation: :blue[**Rs {item['price']:,.2f}**]")
                            st.markdown(f"🔒 Token Advance: :green[**Rs {item['advance_token']:,.2f}**]")
                        else:
                            st.markdown(f"Price: :green[**Rs {item['price']:,.2f}**]")
                        st.caption(f"🏬 **Store:** {item['v_name']} | Distance: {item['distance']} KM")

                    if item["is_high_val"] == 0:
                        del_pref = st.radio("Delivery Mode:", [f"🚚 Home Delivery (Rs {item['delivery_fee']})", "🚶 Pickup (Free)"], key=f"rad_{item['p_id']}", horizontal=True)
                        final_fee = 0.0 if "Pickup" in del_pref else item["delivery_fee"]
                        final_mode = "Pickup" if "Pickup" in del_pref else "Delivery"
                    else:
                        final_fee = 0.0; final_mode = "Site Visit / Token"

                    pay_now = item["advance_token"] if item["is_high_val"] == 1 else item["price"]
                    commission_required = round(pay_now * 0.01, 2)
                    
                    if item["v_wallet"] < commission_required:
                        st.error("⚠️ Store Offline (Wallet Recharge pending).")
                    else:
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if item["is_high_val"] == 1:
                                with st.popover("📅 Book Free Site Visit"):
                                    v_date = st.date_input("Select Date", key=f"date_{item['p_id']}")
                                    v_time = st.selectbox("Select Time Slot", ["10:00 AM", "12:00 PM", "03:00 PM", "05:00 PM"], key=f"time_{item['p_id']}")
                                    if st.button("Confirm Site Visit", key=f"sv_btn_{item['p_id']}"):
                                        conn_sv = sqlite3.connect(DB_NAME)
                                        conn_sv.execute("INSERT INTO site_visits (product_id, vendor_id, customer_name, customer_phone, visit_date, visit_time) VALUES (?, ?, ?, ?, ?, ?)",
                                                        (item["p_id"], item["v_id"], cust_name, cust_phone, str(v_date), v_time))
                                        conn_sv.commit(); conn_sv.close(); st.success("Site visit confirmed!")
                            else:
                                if st.button("➕ Add to Cart", key=f"cart_{item['p_id']}"):
                                    st.session_state.cart.append(item); st.toast("Added to Cart!", icon="🛒")

                        with b_col2:
                            loc_confirm = st.checkbox("📍 I confirm my delivery location map.", key=f"loc_{item['p_id']}")
                            if loc_confirm:
                                btn_label = f"🔒 Book Advance (Rs {item['advance_token']:,.2f})" if item["is_high_val"] == 1 else f"🚀 Order Now"
                                if st.button(btn_label, key=f"btn_{item['p_id']}"):
                                    grand_total = pay_now + final_fee
                                    gen_otp = str(random.randint(1000, 9999))
                                    conn_o = sqlite3.connect(DB_NAME)
                                    conn_o.execute('''
                                        INSERT INTO orders (customer_name, customer_phone, delivery_address, vendor_id, delivery_otp, items_summary, item_price, delivery_fee, grand_total, platform_commission_1pct, distance_km, delivery_mode, status)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Order Placed')
                                    ''', (cust_name, cust_phone, cust_address_text, item["v_id"], gen_otp, f"{item['brand']} - {item['title']}", item["price"], final_fee, grand_total, commission_required, item["distance"], final_mode))
                                    conn_o.execute('UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?', (commission_required, item["v_id"]))
                                    conn_o.commit(); order_id = conn_o.execute("SELECT last_insert_rowid()").fetchone()[0]; conn_o.close()

                                    st.session_state.current_bill = {
                                        "order_id": order_id, "cust": cust_name, "address": cust_address_text, "otp": gen_otp,
                                        "item": f"{item['brand']} - {item['title']}", "shop": item["v_name"],
                                        "shop_upi": item["v_upi"], "price": pay_now, "fee": final_fee, 
                                        "total": grand_total, "cut": commission_required, "distance": item["distance"], "mode": final_mode
                                    }
                            else:
                                st.caption("Confirm location to place order.")

    if "current_bill" in st.session_state:
        b = st.session_state.current_bill
        st.markdown("---")
        st.success(f"🎉 Order/Booking #{b['order_id']} Successfully Placed! Delivered to: {b['address']}")
        q1, q2 = st.columns([1, 1])
        with q1:
            st.markdown("### 💳 Payment Pending (UPI on Delivery)")
            st.info(f"आपको डिलीवरी के समय **Rs {b['total']:,.2f}** का पेमेंट सीधे दुकानदार के UPI पर करना होगा।")
            st.warning(f"🔒 **Your Secret Delivery OTP:** `{b['otp']}` (पेमेंट करने के बाद डिलीवरी बॉय/स्टोर को दें)")
        with q2:
            pdf_bytes = generate_pdf_invoice(b)
            st.download_button("📄 Download Invoice Summary", data=bytes(pdf_bytes), file_name=f"Order_{b['order_id']}.pdf", mime="application/pdf")

# -----------------------------------------------------------
# TAB 2: MULTI-ITEM CART & CHECKOUT
# -----------------------------------------------------------
elif menu == "🛒 Cart & Checkout":
    st.markdown("<h2>🛒 Your Shopping Cart (Checkout)</h2>", unsafe_allow_html=True)
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df[["brand", "title", "price", "v_name", "distance"]], use_container_width=True)

        unique_vendors = cart_df["v_id"].nunique()
        if unique_vendors > 1:
            st.warning("⚠️ Cart contains items from different shops. Please place separate orders for each shop.")
        else:
            items_total = cart_df["price"].sum()
            sample_item = st.session_state.cart[0]
            dist = sample_item["distance"]
            fee, fee_desc = get_delivery_fee(dist, items_total, 1, 20.0, 30.0, 10.0)

            coupon_code = st.text_input("Enter Promo Code (e.g. BHARAT10):")
            discount_amount = 0.0
            if coupon_code:
                conn_c = sqlite3.connect(DB_NAME)
                c_row = conn_c.execute("SELECT discount_pct, min_order_value FROM coupons WHERE code = ? AND is_active = 1", (coupon_code.strip().upper(),)).fetchone()
                conn_c.close()
                if c_row and items_total >= c_row[1]:
                    discount_amount = round((items_total * c_row[0] / 100.0), 2)
                    st.success(f"Coupon Applied! You get Rs {discount_amount:,.2f} OFF")
                else: st.error("Invalid or minimum value not met.")

            final_total = items_total - discount_amount + fee
            st.write(f"Items Subtotal: **Rs {items_total:,.2f}** | Discount: **-Rs {discount_amount:,.2f}** | Delivery: **Rs {fee:,.2f}**")
            st.markdown(f"### Grand Total: :green[**Rs {final_total:,.2f}**]")

            cut_1pct = round(items_total * 0.01, 2)
            if sample_item["v_wallet"] < cut_1pct:
                st.error("⚠️ Store has insufficient wallet balance to process orders.")
            else:
                loc_confirm = st.checkbox("📍 I confirm my delivery location map.")
                if loc_confirm and st.button("🚀 Checkout (Pay UPI on Delivery)"):
                    items_summary = ", ".join([f"{x['brand']} {x['title']}" for x in st.session_state.cart])
                    gen_otp = str(random.randint(1000, 9999))
                    conn_co = sqlite3.connect(DB_NAME)
                    conn_co.execute('''INSERT INTO orders (customer_name, customer_phone, vendor_id, delivery_otp, items_summary, item_price, discount_amount, delivery_fee, grand_total, platform_commission_1pct, distance_km, delivery_mode, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Delivery', 'Order Placed')''', 
                        ("Rahul Sharma", "919876500000", sample_item["v_id"], gen_otp, items_summary, items_total, discount_amount, fee, final_total, cut_1pct, dist))
                    conn_co.execute('UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?', (cut_1pct, sample_item["v_id"]))
                    conn_co.commit(); order_id = conn_co.execute("SELECT last_insert_rowid()").fetchone()[0]; conn_co.close()
                    st.session_state.cart = []
                    st.success(f"🎉 Combined Order #{order_id} placed! 1% Commission auto-debited from store wallet."); st.rerun()

        if st.button("🗑️ Clear Entire Cart"): st.session_state.cart = []; st.rerun()
    else: st.info("Your cart is currently empty.")

# -----------------------------------------------------------
# TAB 3: SCHEDULED SITE VISITS
# -----------------------------------------------------------
elif menu == "📅 Scheduled Site Visits":
    st.markdown("<h2>📅 Customer Site Visits & Consultation Schedule</h2>", unsafe_allow_html=True)
    conn_v = sqlite3.connect(DB_NAME)
    sv_df = pd.read_sql_query('SELECT sv.id, sv.customer_name, sv.customer_phone, sv.visit_date, sv.visit_time, sv.status, p.brand, p.title, v.name as firm_name FROM site_visits sv JOIN products p ON sv.product_id = p.id JOIN vendors v ON sv.vendor_id = v.id ORDER BY sv.created_at DESC', conn_v)
    conn_v.close()
    if not sv_df.empty: st.dataframe(sv_df, use_container_width=True)
    else: st.info("No site visits scheduled yet.")

# -----------------------------------------------------------
# TAB 4: TRACK MY ORDERS & CHAT
# -----------------------------------------------------------
elif menu == "🚚 Track My Orders & Chat":
    st.markdown("<h2>🚚 Track Orders, Rate Store & Direct Chat</h2>", unsafe_allow_html=True)
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
                                    avg_r = conn.execute("SELECT AVG(rating) FROM reviews WHERE vendor_id = ?", (o_row['vendor_id'],)).fetchone()[0]
                                    if avg_r: conn.execute("UPDATE vendors SET rating = ? WHERE id = ?", (round(avg_r, 1), o_row['vendor_id']))
                                    conn.commit(); st.success("Rating saved!")

                with c_t2:
                    st.markdown("#### 💬 Live In-App Chat")
                    msgs = pd.read_sql_query("SELECT * FROM messages WHERE order_id = ? ORDER BY sent_at ASC", conn, params=(o_row['id'],))
                    if not msgs.empty:
                        for _, m_row in msgs.iterrows():
                            st.write(f"**{m_row['sender_name']}:** {m_row['message_text']}")
                    
                    with st.form(f"chat_form_{o_row['id']}"):
                        msg_input = st.text_input("Type message / instructions...", key=f"msg_in_{o_row['id']}")
                        if st.form_submit_button("Send"):
                            if msg_input:
                                conn.execute("INSERT INTO messages (order_id, sender_name, message_text) VALUES (?, ?, ?)", (o_row['id'], "Customer", msg_input))
                                conn.commit(); st.rerun()
    else: st.info("No orders found for this phone number.")
    conn.close()

# -----------------------------------------------------------
# TAB 5: VENDOR TERMINAL
# -----------------------------------------------------------
elif menu == "🏪 Vendor Terminal":
    st.markdown("<h2>🔔 Store Orders & Fulfillment Dashboard</h2>", unsafe_allow_html=True)
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
                        st.write(f"Payment to Collect: :green[**Rs {ord_row['grand_total']:,.2f}**]")
                    with col_o2:
                        st.write(f"Mode: **{ord_row['delivery_mode']}**")
                        st.write(f"Status: `{ord_row['status']}`")
                        if "Paid" in ord_row['payment_status']: st.success(f"✅ {ord_row['payment_status']}")
                        else: st.warning(f"⏳ {ord_row['payment_status']}")
                    with col_o3:
                        if ord_row["status"] == "Order Placed":
                            if ord_row['delivery_mode'] == "Pickup":
                                if st.button("✅ Confirm Picked Up & Paid", key=f"pu_{ord_row['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ord_row['id'],))
                                    conn.commit(); st.rerun()
                            elif ord_row['delivery_mode'] == "Delivery":
                                st.write("🚚 Dispatch Options:")
                                if st.button("Self-Dispatch (Own Boy)", key=f"sd_{ord_row['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ord_row['id'],))
                                    conn.commit(); st.rerun()
                                if ord_row['grand_total'] <= 5000:
                                    if st.button("🛵 Request Platform Rider", type="primary", key=f"rr_{ord_row['id']}"):
                                        conn.execute("UPDATE orders SET status = 'Rider Requested' WHERE id = ?", (ord_row['id'],))
                                        conn.commit(); st.rerun()
                                else:
                                    st.error("⚠️ Order > Rs 5000. Use Self-Dispatch.")
                        elif ord_row["status"] == "Dispatched" and ord_row['rider_id'] == 0:
                            if st.button("✅ Mark Delivered & Paid", key=f"md_{ord_row['id']}"):
                                conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ord_row['id'],))
                                conn.commit(); st.rerun()

                        msgs = pd.read_sql_query("SELECT message_text FROM messages WHERE order_id = ? AND sender_name = 'System'", conn, params=(ord_row['id'],))
                        for _, m in msgs.iterrows(): st.info(m['message_text'])
        else: st.info("No orders received yet for this store.")
    conn.close()

# -----------------------------------------------------------
# TAB 6: RIDER TERMINAL
# -----------------------------------------------------------
elif menu == "🛵 Rider Terminal (UPI)":
    st.markdown("<h2>🛵 Delivery Partner Dashboard (UPI Collection)</h2>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    riders_df = pd.read_sql_query("SELECT * FROM riders WHERE status = 'Active'", conn)
    
    if riders_df.empty: st.warning("No active riders registered. Register below.")
    else:
        selected_rider_id = st.selectbox("Select Active Rider Profile", riders_df["id"].tolist(), format_func=lambda x: riders_df[riders_df['id'] == x]['name'].values[0])
        curr_rider = riders_df[riders_df["id"] == selected_rider_id].iloc[0]
        
        st.metric("Rider Security Deposit", f"Rs {curr_rider['wallet_balance']:,.2f}", delta="Required: Rs 5,000")
        st.markdown("---")

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
                        st.write(f"🏬 Pickup: **{ro['shop_name']}** ({ro['shop_address']})")
                        st.write(f"📍 Drop Address: `{ro['delivery_address']}`")
                        st.write(f"Delivery Pay Earned: :green[Rs {ro['delivery_fee']:,.2f}]")
                    with col_r2:
                        if ro["status"] == "Rider Requested":
                            if curr_rider['wallet_balance'] < 5000:
                                st.error("⚠️ Rs 5000 Security required to accept.")
                            else:
                                if st.button("🚴 Accept Delivery", key=f"acc_{ro['id']}"):
                                    conn.execute("UPDATE orders SET status = 'Accepted by Rider', rider_id = ? WHERE id = ?", (selected_rider_id, ro['id']))
                                    conn.commit(); st.rerun()

                        elif ro["status"] == "Accepted by Rider":
                            st.info("Do NOT pay store now. Collect via QR from customer.")
                            if st.button("🚚 Picked Up & Reached Customer", key=f"disp_r_{ro['id']}"):
                                conn.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ro['id'],))
                                conn.commit(); st.rerun()

                        elif ro["status"] == "Dispatched":
                            st.markdown("### 📱 Payment Collection")
                            st.warning(f"ग्राहक से कहें कि वह इस QR को स्कैन करके **Rs {ro['grand_total']:,.2f}** सीधे **{ro['shop_name']}** को पे करे:")
                            qr_bytes = generate_upi_qr(ro['shop_upi'], ro['shop_name'], ro['grand_total'], f"Order_{ro['id']}")
                            st.image(qr_bytes, width=200)
                            
                            otp_in = st.text_input("Customer 4-Digit OTP", key=f"otp_{ro['id']}")
                            if st.button("✅ Verify OTP & Mark Complete", key=f"comp_{ro['id']}"):
                                if otp_in == str(ro['delivery_otp']):
                                    conn.execute("UPDATE orders SET status = 'Delivered', payment_status = 'Paid via UPI' WHERE id = ?", (ro['id'],))
                                    msg = f"✅ Payment of Rs {ro['grand_total']:,.2f} Collected via Rider ({curr_rider['name']}) directly through UPI."
                                    conn.execute("INSERT INTO messages (order_id, sender_name, message_text) VALUES (?, 'System', ?)", (ro['id'], msg))
                                    conn.commit()
                                    st.success(f"🎉 Delivery Completed & Store Notified!"); st.rerun()
                                else: st.error("❌ Invalid OTP!")
        else: st.info("No active delivery orders.")
    conn.close()

# -----------------------------------------------------------
# TAB 7: VENDOR QR STANDEE
# -----------------------------------------------------------
elif menu == "🪧 Vendor QR Standee":
    st.markdown("<h2>🪧 Download Official Store Standee QR</h2>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()
    if not vendors_df.empty:
        selected_vid = st.selectbox("Select Shop", vendors_df["id"].tolist(), format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0])
        curr_v = vendors_df[vendors_df["id"] == selected_vid].iloc[0]
        st.info(f"Generating Standee for **{curr_v['name']}** (UPI: `{curr_v['upi_id']}`) | GST: `{curr_v['gstin']}`")
        standee_pdf_bytes = generate_standee_pdf(curr_v)
        st.download_button("🖨️ Download PDF Counter Standee", data=bytes(standee_pdf_bytes), file_name=f"Standee_{curr_v['name'].replace(' ', '_')}.pdf", mime="application/pdf")

# -----------------------------------------------------------
# TAB 8: VENDOR WALLET & REFUND
# -----------------------------------------------------------
elif menu == "💳 Vendor Wallet & Refund":
    st.markdown("<h2>💳 Store Personal Wallet & Refund Manager</h2>", unsafe_allow_html=True)
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
                st.caption("⚠️ **नोट:** विथड्रॉल पर 2% (न्यूनतम ₹3) बैंक और प्लेटफ़ॉर्म प्रोसेसिंग चार्ज काटा जाएगा।")
                
                withdraw_request = curr_vendor['wallet_balance']
                processing_fee = max(round(withdraw_request * 0.02, 2), 3.0)
                
                if withdraw_request > processing_fee:
                    refund_amt = withdraw_request - processing_fee
                    st.write(f"कुल वॉलेट बैलेंस: **Rs {withdraw_request:,.2f}**")
                    st.write(f"प्रोसेसिंग फीस (2%): :red[**- Rs {processing_fee:,.2f}**]")
                    st.write(f"आपके खाते में आएंगे: :green[**Rs {refund_amt:,.2f}**]")
                    
                    if st.button("💸 Request Balance Withdrawal"):
                        conn_wd = sqlite3.connect(DB_NAME)
                        conn_wd.execute("UPDATE vendors SET wallet_balance = 0.0 WHERE id = ?", (v_select,))
                        conn_wd.execute("INSERT INTO wallet_logs (vendor_id, txn_type, amount, txn_ref, status) VALUES (?, 'WITHDRAWAL_REQUEST', ?, ?, 'Pending Admin Approval')", 
                                        (v_select, refund_amt, f"Refund to UPI: {curr_vendor['upi_id']} (Rs {processing_fee} Fee Deducted)"))
                        conn_wd.commit(); conn_wd.close()
                        st.success(f"🎉 रिक्वेस्ट भेज दी गई है! एडमिन अप्रूवल के बाद Rs {refund_amt:,.2f} आपके UPI पर भेज दिए जाएंगे।"); st.rerun()
                elif withdraw_request > 0:
                    st.error(f"⚠️ आपका बैलेंस (Rs {withdraw_request:,.2f}) प्रोसेसिंग फीस (Rs {processing_fee:,.2f}) चुकाने के लिए बहुत कम है।")

        with w2:
            with st.container(border=True):
                st.markdown("### ⚡ Top-Up In-App Wallet")
                topup_amt = st.radio("Select Top-Up Amount", [100.0, 150.0, 200.0, 500.0], index=1, horizontal=True)
                p_qr = generate_upi_qr(PLATFORM_UPI_ID, "Bharat Platform Admin", topup_amt, f"Wallet_Store_{curr_vendor['id']}")
                st.image(p_qr, width=170)
                st.caption(f"Platform UPI: `{PLATFORM_UPI_ID}` | Amount: **Rs {topup_amt:.0f}**")
                
                txn_ref_in = st.text_input("Enter 12-Digit UPI Ref / UTR No.")
                if st.button("✅ Add Balance to My Wallet"):
                    if txn_ref_in:
                        conn_tu = sqlite3.connect(DB_NAME)
                        conn_tu.execute("UPDATE vendors SET wallet_balance = wallet_balance + ? WHERE id = ?", (topup_amt, v_select))
                        conn_tu.execute("INSERT INTO wallet_logs (vendor_id, txn_type, amount, txn_ref, status) VALUES (?, 'TOP-UP', ?, ?, 'Completed')", (v_select, topup_amt, txn_ref_in))
                        conn_tu.commit(); conn_tu.close()
                        st.success(f"🎉 Rs {topup_amt:,.2f} added to wallet!"); st.rerun()
                    else: st.error("Please enter UTR Number after payment.")

        st.markdown("---")
        st.write("### 📜 Wallet History")
        conn_l = sqlite3.connect(DB_NAME)
        logs_df = pd.read_sql_query("SELECT * FROM wallet_logs WHERE vendor_id = ? ORDER BY created_at DESC", conn_l, params=(v_select,))
        conn_l.close()
        if not logs_df.empty: st.dataframe(logs_df, use_container_width=True)

# -----------------------------------------------------------
# TAB 9: ADD PRODUCT / PROPERTY LISTING
# -----------------------------------------------------------
elif menu == "📦 Add Product / Property":
    st.markdown("<h2>📦 Product & Real Estate Listing Management</h2>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    t1, t2 = st.tabs(["➕ List New Item", "⚙️ Store Settings"])
    with t1:
        with st.form("prod_form"):
            s_id = st.selectbox("Select Store", vendors_df["id"].tolist(), format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0])
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                b_name = st.text_input("Brand / Project Name", placeholder="e.g. Sai Samruddhi, Tata")
                p_name = st.text_input("Product Title / Plot No.", placeholder="e.g. Plot 14, 1kg Rice")
                p_cat = st.selectbox("Category", ["Real Estate", "Grocery", "Electronics", "Automobile", "Fashion"])
                is_high = st.checkbox("High-Value Property/Vehicle?", value=False)
            with c_p2:
                p_val = st.number_input("Full Selling Price (Rs)", min_value=50.0, value=500.0, step=50.0)
                adv_val = st.number_input("Advance Token (if High-Value)", min_value=0.0, value=11000.0 if is_high else 0.0)
                img_link = st.text_input("Cover Image URL", placeholder="https://via.placeholder.com/200")
                vid_link = st.text_input("Video URL (Optional)")
                p_desc = st.text_area("Full Description")

            if st.form_submit_button("🚀 Publish Listing"):
                if b_name and p_name:
                    conn_i = sqlite3.connect(DB_NAME)
                    conn_i.execute('''INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, video_url, image_url, description)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (s_id, b_name, p_name, p_cat, p_val, 1 if is_high else 0, adv_val, vid_link, img_link, p_desc))
                    conn_i.commit(); conn_i.close()
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
# TAB 10: REGISTER NEW STORE / RIDER
# -----------------------------------------------------------
elif menu == "🏬 Register New Store":
    st.markdown("<h2>🏬 Enterprise & Rider Onboarding Portal</h2>", unsafe_allow_html=True)
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

            if st.form_submit_button("✅ Register Store"):
                if name and upi:
                    conn_r = sqlite3.connect(DB_NAME)
                    conn_r.execute('''INSERT INTO vendors (name, phone, upi_id, city, lat, lon, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
                                      VALUES (?, ?, ?, ?, ?, ?, 0.0, 1, ?, ?, ?)''', (name, phone, upi, city, lat, lon, b1, b2, pe))
                    conn_r.commit(); conn_r.close()
                    st.success(f"🎉 Store '{name}' registered! Recharge wallet to activate.")

    with ob_tab2:
        with st.form("rider_reg_form"):
            st.info("⚠️ Delivery Partners must deposit a refundable security amount of **Rs 5,000** to activate ID.")
            r_name = st.text_input("Rider Name")
            r_phone = st.text_input("WhatsApp Phone")
            r_city = st.text_input("City")
            r_veh = st.text_input("Vehicle Number")
            if st.form_submit_button("🛵 Register Rider"):
                if r_name and r_phone:
                    try:
                        conn_rd = sqlite3.connect(DB_NAME)
                        conn_rd.execute("INSERT INTO riders (name, phone, city, vehicle_number, wallet_balance, status) VALUES (?, ?, ?, ?, 0.0, 'Pending')", (r_name, r_phone, r_city, r_veh))
                        conn_rd.commit(); conn_rd.close()
                        st.success(f"🎉 {r_name} registered! Deposit Rs 5,000 Security via Admin to activate.")
                    except Exception: st.error("Phone number already registered.")

# -----------------------------------------------------------
# TAB 11: PLATFORM EARNINGS LEDGER & ADMIN APPROVALS
# -----------------------------------------------------------
else:
    st.markdown("<h2>📊 Platform Admin Panel: 1% Earnings & Withdrawals</h2>", unsafe_allow_html=True)
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
        st.caption("नोट: 2% (न्यूनतम ₹3) प्रोसेसिंग फीस काट ली गई है। बस नीचे लिखी अमाउंट पे करें।")
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