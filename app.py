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
    page_title="Bharat All-in-One Hyperlocal & Real Estate Platform",
    page_icon="🇮🇳",
    layout="wide"
)

DB_NAME = "hyperlocal_market.db"

# -----------------------------------------------------------
# 1. DATABASE SETUP & MIGRATION HELPER
# -----------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Vendors Table
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
            wallet_balance REAL DEFAULT 0.0,
            free_delivery_above_500 INTEGER DEFAULT 1,
            base_1km REAL DEFAULT 20.0,
            base_2km REAL DEFAULT 30.0,
            per_km_extra REAL DEFAULT 10.0
        )
    ''')

    # Safe Schema Migrations for Vendors (agar purani file ho to columns add ho jayein)
    vendor_cols = [col[1] for col in c.execute("PRAGMA table_info(vendors)").fetchall()]
    if "rera_id" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN rera_id TEXT DEFAULT 'N/A'")
    if "is_kyc_verified" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN is_kyc_verified INTEGER DEFAULT 1")
    if "is_sponsored" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN is_sponsored INTEGER DEFAULT 0")
    if "gstin" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN gstin TEXT DEFAULT 'NON-GST'")

    # Delivery Partners Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS riders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            city TEXT NOT NULL,
            vehicle_number TEXT,
            wallet_balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Active'
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
            is_high_value INTEGER DEFAULT 0,
            advance_booking_amount REAL DEFAULT 0.0,
            video_url TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            description TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id)
        )
    ''')

    prod_cols = [col[1] for col in c.execute("PRAGMA table_info(products)").fetchall()]
    if "is_high_value" not in prod_cols:
        c.execute("ALTER TABLE products ADD COLUMN is_high_value INTEGER DEFAULT 0")
    if "advance_booking_amount" not in prod_cols:
        c.execute("ALTER TABLE products ADD COLUMN advance_booking_amount REAL DEFAULT 0.0")
    if "video_url" not in prod_cols:
        c.execute("ALTER TABLE products ADD COLUMN video_url TEXT DEFAULT ''")
    if "image_url" not in prod_cols:
        c.execute("ALTER TABLE products ADD COLUMN image_url TEXT DEFAULT ''")

    # Site Visit Bookings Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS site_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            vendor_id INTEGER,
            customer_name TEXT,
            customer_phone TEXT,
            visit_date TEXT,
            visit_time TEXT,
            status TEXT DEFAULT 'Confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Coupons Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_pct REAL DEFAULT 10.0,
            min_order_value REAL DEFAULT 200.0,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Orders Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            vendor_id INTEGER,
            rider_id INTEGER DEFAULT 0,
            delivery_otp TEXT,
            items_summary TEXT,
            item_price REAL,
            amount_paid_now REAL,
            discount_amount REAL DEFAULT 0.0,
            delivery_fee REAL,
            grand_total REAL,
            platform_commission_1pct REAL,
            platform_gst_18pct REAL,
            vendor_net_payout REAL,
            distance_km REAL,
            status TEXT DEFAULT 'Order Placed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Reviews Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            customer_name TEXT,
            rating INTEGER,
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Chat Messages Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            sender_name TEXT,
            message_text TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Settlements Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            amount REAL,
            upi_id TEXT,
            status TEXT DEFAULT 'Pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Check & seed default items
    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO vendors (name, phone, upi_id, city, address, gstin, rera_id, is_kyc_verified, is_sponsored, lat, lon, rating, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
            VALUES 
            ('Nagpur Central Mart', '919876543210', 'bharatmart@upi', 'Nagpur', 'Sitabuldi Main Market', '27ABCDE1234F1Z5', 'N/A', 1, 1, 21.1458, 79.0882, 4.9, 1500.0, 1, 20.0, 30.0, 10.0),
            ('First Choice Infra & Deals Hub', '919876543211', 'firstchoice@upi', 'Nagpur', 'Wardha Road / Besa', '27WXYZ8910G2Z1', 'MAHARERA/P5050001234', 1, 1, 21.1000, 79.0700, 4.9, 49500.0, 0, 20.0, 30.0, 10.0)
        ''')
        c.execute('''
            INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, video_url, image_url, description)
            VALUES 
            (1, 'Tata Tea', 'Tata Tea Premium 250g', 'Grocery', 50.0, 0, 0.0, '', 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=500&auto=format&fit=crop&q=60', 'Fresh daily morning tea'),
            (1, 'Fortune', 'Refined Sunflower Oil 5L', 'Grocery', 680.0, 0, 0.0, '', 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500&auto=format&fit=crop&q=60', 'Pure cooking oil pack'),
            (2, 'Sai Samruddhi City', 'Residential NA Plot 1200 Sq.Ft.', 'Real Estate', 1500000.0, 1, 21000.0, '', 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=500&auto=format&fit=crop&q=60', 'NMRDA Sanctioned RL plot with cement road, water & electricity'),
            (2, 'Mahindra', 'Scorpio-N Diesel Z8 L 4x2', 'Automobile', 2150000.0, 1, 25000.0, '', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=500&auto=format&fit=crop&q=60', 'Brand new vehicle VIP booking slot')
        ''')
        c.execute('''
            INSERT INTO coupons (code, discount_pct, min_order_value, is_active)
            VALUES ('BHARAT10', 10.0, 100.0, 1), ('FESTIVE50', 5.0, 500.0, 1)
        ''')
        c.execute('''
            INSERT INTO riders (name, phone, city, vehicle_number, wallet_balance, status)
            VALUES ('Amit Kumar (Rider)', '919876540001', 'Nagpur', 'MH-31-AB-1234', 250.0, 'Active')
        ''')
    
    conn.commit()
    conn.close()

init_db()

if "cart" not in st.session_state:
    st.session_state.cart = []

# -----------------------------------------------------------
# 2. HELPER FUNCTIONS
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

def generate_upi_qr(upi_id, payee_name, amount, note):
    upi_url = f"upi://pay?pa={upi_id}&pn={urllib.parse.quote(payee_name)}&am={amount:.2f}&cu=INR&tn={urllib.parse.quote(note)}"
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_pdf_invoice(bill_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "BHARAT HYPERLOCAL MARKETPLACE", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Official Digital Bill / Token Receipt | GSTIN: {bill_data.get('gstin', 'NON-GST')}", ln=True, align="C")
    pdf.line(10, 28, 200, 28)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 7, f"Order/Booking ID: #{bill_data['order_id']}")
    pdf.cell(90, 7, f"Customer: {bill_data['cust']}", ln=True)
    pdf.cell(100, 7, f"Store/Firm: {bill_data['shop']}")
    pdf.cell(90, 7, f"Distance: {bill_data['distance']} KM", ln=True)
    pdf.ln(4)

    pdf.line(10, 50, 200, 50)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(120, 7, "Description")
    pdf.cell(70, 7, "Amount (INR)", ln=True, align="R")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(120, 7, f"{bill_data['item']}")
    pdf.cell(70, 7, f"Rs {bill_data['price']:,.2f}", ln=True, align="R")
    
    if bill_data.get('discount', 0) > 0:
        pdf.cell(120, 7, "Coupon Discount Applied")
        pdf.cell(70, 7, f"- Rs {bill_data['discount']:,.2f}", ln=True, align="R")

    pdf.cell(120, 7, "Delivery / Logistics Charges")
    pdf.cell(70, 7, f"Rs {bill_data['fee']:,.2f}", ln=True, align="R")
    
    pdf.line(10, 85, 200, 85)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 9, "Amount Paid Now:")
    pdf.cell(70, 9, f"Rs {bill_data['total']:,.2f}", ln=True, align="R")
    
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, f"1% Platform Cut: Rs {bill_data['cut']:,.2f} | Net Vendor Settlement: Rs {bill_data['payout']:,.2f}", ln=True, align="C")
    return pdf.output()

# -----------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------
st.sidebar.title("🇮🇳 Bharat Platform")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Marketplace",
    "🛒 Multi-Item Cart & Checkout",
    "📅 Scheduled Site Visits (Property)",
    "🚚 Track My Orders & Chat",
    "🛵 Delivery Partner / Rider Mode",
    "🏪 Vendor Terminal & Orders",
    "💰 Vendor Settlement & Wallet",
    "📦 Add Product / Property Listing",
    "🏬 Register New Store / Agency",
    "📊 Platform Earnings & Tax Ledger"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER MARKETPLACE
# -----------------------------------------------------------
if menu == "🛍️ Customer Marketplace":
    st.subheader("📍 Nearby Hyperlocal & Real Estate Discovery")
    
    live_loc = get_geolocation()
    detected_lat = 21.1458
    detected_lon = 79.0882
    if live_loc and 'coords' in live_loc:
        detected_lat = live_loc['coords']['latitude']
        detected_lon = live_loc['coords']['longitude']
        st.success(f"📍 GPS Auto-Detected: `{detected_lat:.4f}, {detected_lon:.4f}`")

    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1:
        cust_name = st.text_input("Customer Name", value="Rahul Sharma")
    with c2:
        cust_phone = st.text_input("Customer WhatsApp Phone", value="919876500000")
    with c3:
        cust_lat = st.number_input("Latitude", value=float(detected_lat), format="%.4f")
    with c4:
        cust_lon = st.number_input("Longitude", value=float(detected_lon), format="%.4f")

    st.markdown("---")
    
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        search_query = st.text_input("🔍 Search any item or property (e.g. Chai, Plot, Oil, Scorpio, Atta):", "")
    with f2:
        cat_filter = st.selectbox("Category Filter", ["All Categories", "Real Estate", "Grocery", "Electronics", "Automobile", "Daily Essentials", "Fashion"])
    with f3:
        price_range = st.selectbox("Budget Filter", ["All Prices (₹50 to ₹50L+)", "Under ₹500", "₹500 - ₹5,000", "High-Value Deals (Above ₹50,000)"])

    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT p.id, p.brand, p.title, p.category, p.price, p.is_high_value, p.advance_booking_amount, p.video_url, p.image_url, p.description,
               v.id as vendor_id, v.name as vendor_name, v.phone as vendor_phone, v.upi_id, v.gstin, v.rera_id, v.is_kyc_verified, v.is_sponsored,
               v.rating as vendor_rating, v.lat, v.lon, v.free_delivery_above_500, v.base_1km, v.base_2km, v.per_km_extra
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

        if cat_filter != "All Categories" and row["category"] != cat_filter:
            continue

        if price_range == "Under ₹500" and row["price"] >= 500:
            continue
        elif price_range == "₹500 - ₹5,000" and (row["price"] < 500 or row["price"] > 5000):
            continue
        elif price_range == "High-Value Deals (Above ₹50,000)" and row["price"] < 50000:
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
            "is_high_val": row["is_high_value"],
            "advance_token": row["advance_booking_amount"],
            "video_url": row["video_url"],
            "image_url": row["image_url"] if row["image_url"] else "https://via.placeholder.com/300x200?text=Product+Image",
            "desc": row["description"],
            "v_id": row["vendor_id"],
            "v_name": row["vendor_name"],
            "v_phone": str(row["vendor_phone"]),
            "v_upi": row["upi_id"],
            "v_gstin": row["gstin"],
            "v_rera": row["rera_id"],
            "v_kyc": row["is_kyc_verified"],
            "v_sponsored": row["is_sponsored"],
            "v_rating": row["vendor_rating"],
            "v_lat": row["lat"],
            "v_lon": row["lon"],
            "distance": dist,
            "delivery_fee": fee,
            "fee_desc": fee_desc
        })

    results.sort(key=lambda x: (-x["v_sponsored"], x["distance"]))

    if results:
        m = folium.Map(location=[cust_lat, cust_lon], zoom_start=12)
        folium.Marker([cust_lat, cust_lon], popup="Customer Location", icon=folium.Icon(color="blue", icon="user")).add_to(m)
        for item in results:
            folium.Marker(
                [item["v_lat"], item["v_lon"]],
                popup=f"{item['v_name']} ({item['distance']} KM)",
                icon=folium.Icon(color="green" if item["v_sponsored"] == 0 else "purple", icon="shopping-cart")
            ).add_to(m)
        
        st_folium(m, height=230, use_container_width=True)

        cols = st.columns(2)
        for idx, item in enumerate(results):
            with cols[idx % 2]:
                with st.container(border=True):
                    if item["v_sponsored"] == 1:
                        st.caption("⭐ **SPONSORED STORE**")

                    img_col, info_col = st.columns([1, 2])
                    with img_col:
                        st.image(item["image_url"], use_container_width=True)
                    with info_col:
                        st.markdown(f"### {item['brand']} - {item['title']}")
                        
                        kyc_badge = "🛡️ KYC Verified" if item["v_kyc"] == 1 else ""
                        rera_badge = f"🏛️ RERA: `{item['v_rera']}`" if item["v_rera"] != "N/A" else ""
                        st.caption(f"Category: `{item['category']}` | ⭐ `{item['v_rating']}/5.0` | {kyc_badge} {rera_badge}")
                        
                        if item["is_high_val"] == 1:
                            st.markdown(f"Total Valuation: :blue[**₹{item['price']:,.2f}**]")
                            st.markdown(f"🔒 Token Advance to Book: :green[**₹{item['advance_token']:,.2f}**]")
                        else:
                            st.markdown(f"Price: :green[**₹{item['price']:,.2f}**]")

                        st.caption(f"🏬 **Store/Firm:** {item['v_name']} ({item['distance']} KM away)")
                        del_display = "FREE" if item['delivery_fee'] == 0 else f"₹{item['delivery_fee']:,.2f}"
                        st.write(f"🚚 Delivery/Site Logistics: `{del_display}` ({item['fee_desc']})")

                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if item["is_high_val"] == 1:
                            with st.popover("📅 Book Site Visit"):
                                v_date = st.date_input("Select Date", key=f"date_{item['p_id']}")
                                v_time = st.selectbox("Select Time Slot", ["10:00 AM", "12:00 PM", "03:00 PM", "05:00 PM"], key=f"time_{item['p_id']}")
                                if st.button("Confirm Site Visit", key=f"sv_btn_{item['p_id']}"):
                                    conn_sv = sqlite3.connect(DB_NAME)
                                    conn_sv.execute("INSERT INTO site_visits (product_id, vendor_id, customer_name, customer_phone, visit_date, visit_time) VALUES (?, ?, ?, ?, ?, ?)",
                                                    (item["p_id"], item["v_id"], cust_name, cust_phone, str(v_date), v_time))
                                    conn_sv.commit()
                                    conn_sv.close()
                                    st.success(f"Site visit confirmed for {v_date} at {v_time}!")
                        else:
                            if st.button(f"➕ Add to Cart", key=f"cart_{item['p_id']}"):
                                st.session_state.cart.append(item)
                                st.toast(f"Added '{item['brand']} - {item['title']}' to cart!", icon="🛒")

                    with b_col2:
                        btn_label = f"🔒 Book Advance (₹{item['advance_token']:,.2f})" if item["is_high_val"] == 1 else f"⚡ Buy Now (₹{item['price']:,.2f})"
                        if st.button(btn_label, key=f"btn_{item['p_id']}"):
                            item_total = item["price"]
                            pay_now = item["advance_token"] if item["is_high_val"] == 1 else item["price"]
                            del_fee = 0.0 if item["is_high_val"] == 1 else item["delivery_fee"]
                            grand_total = pay_now + del_fee
                            
                            cut_1pct = round(pay_now * 0.01, 2)
                            gst_on_cut = round(cut_1pct * 0.18, 2)
                            vendor_cut = round(grand_total - cut_1pct, 2)
                            gen_otp = str(random.randint(1000, 9999))

                            conn_o = sqlite3.connect(DB_NAME)
                            cur = conn_o.cursor()
                            cur.execute('''
                                INSERT INTO orders (customer_name, customer_phone, vendor_id, delivery_otp, items_summary, item_price, amount_paid_now, discount_amount, delivery_fee, grand_total, platform_commission_1pct, platform_gst_18pct, vendor_net_payout, distance_km, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, 'Order Placed')
                            ''', (cust_name, cust_phone, item["v_id"], gen_otp, f"{item['brand']} - {item['title']}", item_total, pay_now, del_fee, grand_total, cut_1pct, gst_on_cut, vendor_cut, item["distance"]))
                            
                            cur.execute('UPDATE vendors SET wallet_balance = wallet_balance + ? WHERE id = ?', (vendor_cut, item["v_id"]))
                            conn_o.commit()
                            order_id = cur.lastrowid
                            conn_o.close()

                            st.session_state.current_bill = {
                                "order_id": order_id,
                                "cust": cust_name,
                                "cust_phone": cust_phone,
                                "otp": gen_otp,
                                "item": f"{item['brand']} - {item['title']}",
                                "shop": item["v_name"],
                                "shop_phone": item["v_phone"],
                                "upi_id": item["v_upi"],
                                "gstin": item["v_gstin"],
                                "price": pay_now,
                                "discount": 0.0,
                                "fee": del_fee,
                                "total": grand_total,
                                "cut": cut_1pct,
                                "payout": vendor_cut,
                                "distance": item["distance"]
                            }

    # Invoice & QR Section
    if "current_bill" in st.session_state:
        b = st.session_state.current_bill
        st.markdown("---")
        st.success(f"🎉 Order / Booking #{b['order_id']} Placed! Real-Time UPI QR Generated:")
        
        q1, q2 = st.columns([1, 1])
        with q1:
            st.markdown("### 📱 Scan & Pay via UPI")
            qr_bytes = generate_upi_qr(b["upi_id"], b["shop"], b["total"], f"Order_{b['order_id']}")
            st.image(qr_bytes, width=210)
            st.write(f"**Payee UPI:** `{b['upi_id']}` | **Total:** :green[**₹{b['total']:,.2f}**]")
            st.warning(f"🔒 **Your Secret Delivery/Booking OTP:** `{b.get('otp', '1234')}`")
            
        with q2:
            st.markdown("### 🧾 Invoice Summary")
            st.write(f"**Customer:** {b['cust']} ({b['cust_phone']})")
            st.write(f"**Item(s):** {b['item']}")
            st.write(f"**Delivery:** ₹{b['fee']:,.2f}")
            st.markdown(f"### **Total Amount Paid:** :green[₹{b['total']:,.2f}]")
            st.info(f"Platform 1% Cut: ₹{b['cut']:,.2f} | Net Vendor Share: ₹{b['payout']:,.2f}")

            pdf_bytes = generate_pdf_invoice(b)
            st.download_button(
                label="📄 Download Official PDF Receipt",
                data=bytes(pdf_bytes),
                file_name=f"Invoice_Order_{b['order_id']}.pdf",
                mime="application/pdf"
            )

            msg_text = (
                f"🛍️ *NEW ORDER / BOOKING #{b['order_id']}*\n"
                f"👤 Customer: {b['cust']}\n"
                f"📦 Item: {b['item']}\n"
                f"💰 Total Amount: Rs {b['total']:,.2f}\n"
                f"📍 Distance: {b['distance']} KM"
            )
            encoded_msg = urllib.parse.quote(msg_text)
            st.link_button("📲 Send to Shopkeeper WhatsApp", f"https://wa.me/{b['shop_phone']}?text={encoded_msg}")

# -----------------------------------------------------------
# TAB 2: MULTI-ITEM CART & CHECKOUT
# -----------------------------------------------------------
elif menu == "🛒 Multi-Item Cart & Checkout":
    st.subheader("🛒 Your Shopping Cart (Multi-Item Checkout)")
    
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df[["brand", "title", "category", "price", "v_name", "distance"]], use_container_width=True)

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
                if c_row:
                    if items_total >= c_row[1]:
                        discount_amount = round((items_total * c_row[0] / 100.0), 2)
                        st.success(f"Coupon Applied! You get ₹{discount_amount:,.2f} OFF ({c_row[0]}%)")
                    else:
                        st.error(f"Minimum order of ₹{c_row[1]:,.2f} required for this coupon.")
                else:
                    st.error("Invalid coupon code.")

            final_total = items_total - discount_amount + fee
            st.write(f"Items Subtotal: **₹{items_total:,.2f}** | Discount: **-₹{discount_amount:,.2f}** | Delivery: **₹{fee:,.2f}**")
            st.markdown(f"### Grand Total: :green[**₹{final_total:,.2f}**]")

            if st.button("🚀 Checkout & Place Combined Order"):
                cut_1pct = round(items_total * 0.01, 2)
                gst_on_cut = round(cut_1pct * 0.18, 2)
                vendor_cut = round(final_total - cut_1pct, 2)
                items_summary = ", ".join([f"{x['brand']} {x['title']}" for x in st.session_state.cart])
                gen_otp = str(random.randint(1000, 9999))

                conn_co = sqlite3.connect(DB_NAME)
                cur = conn_co.cursor()
                cur.execute('''
                    INSERT INTO orders (customer_name, customer_phone, vendor_id, delivery_otp, items_summary, item_price, amount_paid_now, discount_amount, delivery_fee, grand_total, platform_commission_1pct, platform_gst_18pct, vendor_net_payout, distance_km, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Order Placed')
                ''', ("Rahul Sharma", "919876500000", sample_item["v_id"], gen_otp, items_summary, items_total, final_total, discount_amount, fee, final_total, cut_1pct, gst_on_cut, vendor_cut, dist))
                
                cur.execute('UPDATE vendors SET wallet_balance = wallet_balance + ? WHERE id = ?', (vendor_cut, sample_item["v_id"]))
                conn_co.commit()
                order_id = cur.lastrowid
                conn_co.close()

                st.session_state.cart = []
                st.success(f"🎉 Combined Order #{order_id} placed! Delivery OTP: {gen_otp}")
                st.rerun()

        if st.button("🗑️ Clear Entire Cart"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("Your cart is currently empty. Browse products in the Customer Marketplace!")

# -----------------------------------------------------------
# TAB 3: SCHEDULED SITE VISITS
# -----------------------------------------------------------
elif menu == "📅 Scheduled Site Visits (Property)":
    st.subheader("📅 Customer Site Visits & Consultation Schedule")
    conn_v = sqlite3.connect(DB_NAME)
    sv_df = pd.read_sql_query('''
        SELECT sv.id, sv.customer_name, sv.customer_phone, sv.visit_date, sv.visit_time, sv.status, sv.created_at,
               p.brand, p.title, v.name as firm_name
        FROM site_visits sv
        JOIN products p ON sv.product_id = p.id
        JOIN vendors v ON sv.vendor_id = v.id
        ORDER BY sv.created_at DESC
    ''', conn_v)
    conn_v.close()

    if not sv_df.empty:
        st.dataframe(sv_df, use_container_width=True)
    else:
        st.info("No site visits scheduled yet.")

# -----------------------------------------------------------
# TAB 4: TRACK MY ORDERS & CHAT
# -----------------------------------------------------------
elif menu == "🚚 Track My Orders & Chat":
    st.subheader("🚚 Track Orders, Rate Store & Direct Chat")
    t_phone = st.text_input("Enter your Registered WhatsApp Phone Number:", value="919876500000")
    
    conn = sqlite3.connect(DB_NAME)
    my_orders = pd.read_sql_query('''
        SELECT o.id, o.vendor_id, o.items_summary, o.grand_total, o.delivery_otp, o.status, o.distance_km, o.created_at,
               v.name as shop_name, v.phone as shop_phone
        FROM orders o
        JOIN vendors v ON o.vendor_id = v.id
        WHERE o.customer_phone = ?
        ORDER BY o.created_at DESC
    ''', conn, params=(t_phone,))
    conn.close()

    if not my_orders.empty:
        for _, o_row in my_orders.iterrows():
            with st.container(border=True):
                c_t1, c_t2 = st.columns([3, 2])
                with c_t1:
                    st.markdown(f"### Order #{o_row['id']} - {o_row['items_summary']}")
                    st.write(f"🏬 **Shop/Firm:** {o_row['shop_name']} | 📍 Distance: `{o_row['distance_km']} KM`")
                    st.write(f"**Amount Paid:** :green[**₹{o_row['grand_total']:,.2f}**] | Date: `{o_row['created_at']}`")
                    st.warning(f"🔒 **Your Delivery / Deal OTP:** `{o_row['delivery_otp']}`")
                    
                    status = o_row['status']
                    if status == "Order Placed":
                        st.warning("🟡 Status: **Order Placed (Waiting for Store Dispatch)**")
                    elif status == "Accepted by Rider":
                        st.info("🚴 Status: **Rider Accepted Order - Pick up in progress**")
                    elif status == "Dispatched":
                        st.info("🔵 Status: **Out for Delivery** 🚚")
                    elif status == "Delivered":
                        st.success("🟢 Status: **Delivered / Token Completed Successfully** ✅")
                        
                        with st.expander("⭐ Leave a Review & Rating for this Store"):
                            with st.form(f"rev_form_{o_row['id']}"):
                                star_val = st.slider("Star Rating (1 to 5)", 1, 5, 5, key=f"star_{o_row['id']}")
                                rev_txt = st.text_input("Feedback", placeholder="Genuine developer / dealer!", key=f"txt_{o_row['id']}")
                                if st.form_submit_button("Submit Rating"):
                                    conn_rv = sqlite3.connect(DB_NAME)
                                    conn_rv.execute("INSERT INTO reviews (vendor_id, customer_name, rating, review_text) VALUES (?, ?, ?, ?)",
                                                    (o_row['vendor_id'], "Rahul Sharma", star_val, rev_txt))
                                    avg_r = conn_rv.execute("SELECT AVG(rating) FROM reviews WHERE vendor_id = ?", (o_row['vendor_id'],)).fetchone()[0]
                                    if avg_r:
                                        conn_rv.execute("UPDATE vendors SET rating = ? WHERE id = ?", (round(avg_r, 1), o_row['vendor_id']))
                                    conn_rv.commit()
                                    conn_rv.close()
                                    st.success("Thank you for your rating!")
                                    st.rerun()

                with c_t2:
                    st.markdown("#### 💬 Live In-App Chat")
                    conn_m = sqlite3.connect(DB_NAME)
                    msgs = pd.read_sql_query("SELECT * FROM messages WHERE order_id = ? ORDER BY sent_at ASC", conn_m, params=(o_row['id'],))
                    conn_m.close()

                    if not msgs.empty:
                        for _, m_row in msgs.iterrows():
                            st.write(f"**{m_row['sender_name']}:** {m_row['message_text']}")
                    
                    with st.form(f"chat_form_{o_row['id']}"):
                        msg_input = st.text_input("Type message / instructions...", key=f"msg_in_{o_row['id']}")
                        if st.form_submit_button("Send"):
                            if msg_input:
                                conn_ins = sqlite3.connect(DB_NAME)
                                conn_ins.execute("INSERT INTO messages (order_id, sender_name, message_text) VALUES (?, ?, ?)",
                                                 (o_row['id'], "Customer", msg_input))
                                conn_ins.commit()
                                conn_ins.close()
                                st.rerun()
    else:
        st.info("No orders found for this phone number.")

# -----------------------------------------------------------
# TAB 5: DELIVERY PARTNER / RIDER MODE
# -----------------------------------------------------------
elif menu == "🛵 Delivery Partner / Rider Mode":
    st.subheader("🛵 Rider Delivery Dashboard (Accept & Deliver Orders)")
    
    conn = sqlite3.connect(DB_NAME)
    riders_df = pd.read_sql_query("SELECT * FROM riders WHERE status = 'Active'", conn)
    conn.close()

    if riders_df.empty:
        st.warning("No active riders registered. Register below.")
    else:
        r_col1, r_col2 = st.columns([1, 1])
        with r_col1:
            selected_rider_id = st.selectbox(
                "Select Active Rider Profile",
                riders_df["id"].tolist(),
                format_func=lambda x: f"{riders_df[riders_df['id'] == x]['name'].values[0]} ({riders_df[riders_df['id'] == x]['vehicle_number'].values[0]})"
            )
            curr_rider = riders_df[riders_df["id"] == selected_rider_id].iloc[0]
        with r_col2:
            st.metric("Rider Delivery Earnings Wallet", f"₹{curr_rider['wallet_balance']:,.2f}", delta="Per-Order Delivery Pay")

        st.markdown("---")
        st.write("### 📦 Available Nearby Orders for Delivery:")

        conn_r = sqlite3.connect(DB_NAME)
        avail_orders = pd.read_sql_query('''
            SELECT o.id, o.customer_name, o.customer_phone, o.items_summary, o.delivery_fee, o.delivery_otp, o.status, o.distance_km,
                   v.name as shop_name, v.address as shop_address
            FROM orders o
            JOIN vendors v ON o.vendor_id = v.id
            WHERE o.status IN ('Order Placed', 'Accepted by Rider', 'Dispatched')
            ORDER BY o.created_at DESC
        ''', conn_r)
        conn_r.close()

        if not avail_orders.empty:
            for _, o_item in avail_orders.iterrows():
                with st.container(border=True):
                    col_r1, col_r2, col_r3 = st.columns([2, 2, 2])
                    with col_r1:
                        st.markdown(f"**Order #{o_item['id']}** | Customer: `{o_item['customer_name']}`")
                        st.write(f"🏬 Pickup Store: **{o_item['shop_name']}** ({o_item['shop_address']})")
                        st.write(f"📦 Items: `{o_item['items_summary']}`")
                    with col_r2:
                        st.write(f"📍 Distance: **{o_item['distance_km']} KM**")
                        st.write(f"💰 Delivery Earning: :green[**₹{o_item['delivery_fee']:,.2f}**]")
                        st.caption(f"Current Status: `{o_item['status']}`")
                    with col_r3:
                        if o_item["status"] == "Order Placed":
                            if st.button("🚴 Accept Delivery", key=f"acc_{o_item['id']}"):
                                conn_up = sqlite3.connect(DB_NAME)
                                conn_up.execute("UPDATE orders SET status = 'Accepted by Rider', rider_id = ? WHERE id = ?", (selected_rider_id, o_item['id']))
                                conn_up.commit()
                                conn_up.close()
                                st.success("Order Accepted! Head to shop for pickup.")
                                st.rerun()

                        elif o_item["status"] == "Accepted by Rider":
                            if st.button("🚚 Picked Up & Dispatched", key=f"disp_r_{o_item['id']}"):
                                conn_up = sqlite3.connect(DB_NAME)
                                conn_up.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (o_item['id'],))
                                conn_up.commit()
                                conn_up.close()
                                st.success("Status updated to Out for Delivery.")
                                st.rerun()

                        elif o_item["status"] == "Dispatched":
                            otp_in = st.text_input("Enter Customer 4-Digit OTP", key=f"otp_{o_item['id']}")
                            if st.button("✅ Verify OTP & Complete Delivery", key=f"comp_{o_item['id']}"):
                                if otp_in == str(o_item['delivery_otp']):
                                    conn_up = sqlite3.connect(DB_NAME)
                                    conn_up.execute("UPDATE orders SET status = 'Delivered' WHERE id = ?", (o_item['id'],))
                                    conn_up.execute("UPDATE riders SET wallet_balance = wallet_balance + ? WHERE id = ?", (o_item['delivery_fee'], selected_rider_id))
                                    conn_up.commit()
                                    conn_up.close()
                                    st.success(f"🎉 Delivery Verified! ₹{o_item['delivery_fee']:,.2f} added to your wallet!")
                                    st.rerun()
                                else:
                                    st.error("❌ Invalid OTP! Ask customer for 4-digit code.")
        else:
            st.info("No active delivery orders available right now.")

# -----------------------------------------------------------
# TAB 6: VENDOR TERMINAL & ORDERS
# -----------------------------------------------------------
elif menu == "🏪 Vendor Terminal & Orders":
    st.subheader("🔔 Live Order Terminal & Dispatch Management")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    if not vendors_df.empty:
        selected_vid = st.selectbox(
            "Select Shop Terminal",
            vendors_df["id"].tolist(),
            format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0]
        )

        conn = sqlite3.connect(DB_NAME)
        v_orders = pd.read_sql_query(
            "SELECT * FROM orders WHERE vendor_id = ? ORDER BY created_at DESC LIMIT 10", 
            conn, params=(selected_vid,)
        )
        conn.close()

        new_orders = v_orders[v_orders["status"] == "Order Placed"]
        if not new_orders.empty:
            st.error(f"🚨 **{len(new_orders)} New Pending Order(s) Received!**")

        st.write("### Recent Orders Table:")
        if not v_orders.empty:
            for _, ord_row in v_orders.iterrows():
                with st.container(border=True):
                    col_o1, col_o2, col_o3 = st.columns([2, 2, 2])
                    with col_o1:
                        st.markdown(f"**Order #{ord_row['id']}** | Customer: `{ord_row['customer_name']}`")
                        st.write(f"Items: `{ord_row['items_summary']}`")
                        st.write(f"Status: `{ord_row['status']}` | Paid: **₹{ord_row['grand_total']:,.2f}**")
                    with col_o2:
                        st.write(f"Vendor Payout: :green[**₹{ord_row['vendor_net_payout']:,.2f}**]")
                        st.caption(f"Platform 1% Cut: ₹{ord_row['platform_commission_1pct']:,.2f}")
                    with col_o3:
                        if ord_row["status"] == "Order Placed":
                            if st.button("Self Dispatch / Handover 🚚", key=f"disp_{ord_row['id']}"):
                                conn_u = sqlite3.connect(DB_NAME)
                                conn_u.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ord_row['id'],))
                                conn_u.commit()
                                conn_u.close()
                                st.rerun()
                        elif ord_row["status"] == "Dispatched":
                            if st.button("Mark Completed ✅", key=f"del_{ord_row['id']}"):
                                conn_u = sqlite3.connect(DB_NAME)
                                conn_u.execute("UPDATE orders SET status = 'Delivered' WHERE id = ?", (ord_row['id'],))
                                conn_u.commit()
                                conn_u.close()
                                st.rerun()
        else:
            st.info("No orders received yet for this store.")

# -----------------------------------------------------------
# TAB 7: VENDOR SETTLEMENT & WALLET
# -----------------------------------------------------------
elif menu == "💰 Vendor Settlement & Wallet":
    st.subheader("💰 Vendor Wallet & Bank Settlement Engine")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    if not vendors_df.empty:
        v_select = st.selectbox(
            "Select Your Store Account",
            vendors_df["id"].tolist(),
            format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0]
        )
        curr_vendor = vendors_df[vendors_df["id"] == v_select].iloc[0]

        w1, w2 = st.columns(2)
        with w1:
            st.metric("Net Available Wallet Balance", f"₹{curr_vendor['wallet_balance']:,.2f}", delta="Ready for Payout")
            st.write(f"Linked UPI ID: `{curr_vendor['upi_id']}`")
        with w2:
            with st.form("payout_request_form"):
                payout_amt = st.number_input("Request Payout Amount (₹)", min_value=100.0, max_value=float(curr_vendor['wallet_balance']) if curr_vendor['wallet_balance'] > 0 else 100.0, value=float(curr_vendor['wallet_balance']) if curr_vendor['wallet_balance'] > 0 else 100.0)
                submit_payout = st.form_submit_button("⚡ Request Instant Settlement")
                if submit_payout:
                    if curr_vendor['wallet_balance'] >= payout_amt:
                        conn_p = sqlite3.connect(DB_NAME)
                        cur = conn_p.cursor()
                        cur.execute("INSERT INTO settlements (vendor_id, amount, upi_id, status) VALUES (?, ?, ?, 'Pending')",
                                    (v_select, payout_amt, curr_vendor['upi_id']))
                        cur.execute("UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?", (payout_amt, v_select))
                        conn_p.commit()
                        conn_p.close()
                        st.success(f"✅ Settlement request of ₹{payout_amt:,.2f} submitted to Platform Admin!")
                        st.rerun()
                    else:
                        st.error("Insufficient wallet balance.")

        st.markdown("---")
        st.write("### Settlement History Log:")
        conn_s = sqlite3.connect(DB_NAME)
        settle_df = pd.read_sql_query("SELECT * FROM settlements WHERE vendor_id = ? ORDER BY requested_at DESC", conn_s, params=(v_select,))
        conn_s.close()
        if not settle_df.empty:
            st.dataframe(settle_df, use_container_width=True)

# -----------------------------------------------------------
# TAB 8: ADD PRODUCT / PROPERTY LISTING
# -----------------------------------------------------------
elif menu == "📦 Add Product / Property Listing":
    st.subheader("📦 Product & Real Estate Listing Management")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    t1, t2 = st.tabs(["➕ List New Item / Property (₹50 to ₹50 Lakh+)", "⚙️ Store Settings & Promotion"])
    with t1:
        with st.form("prod_form"):
            s_id = st.selectbox(
                "Select Store / Enterprise", vendors_df["id"].tolist(),
                format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0]
            )
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                b_name = st.text_input("Brand / Project Name", placeholder="e.g. Sai Samruddhi, Tata, Apple, Mahindra")
                p_name = st.text_input("Product Title / Plot No.", placeholder="e.g. Plot No. 14 (1200 sqft), 1kg Rice, 4K TV")
                p_cat = st.selectbox("Category", ["Real Estate", "Grocery", "Electronics", "Automobile", "Daily Essentials", "Fashion"])
                is_high = st.checkbox("Is this a High-Value Property / Vehicle / Machinery?", value=False)
            with c_p2:
                p_val = st.number_input("Full Selling Price (₹50 to ₹5,00,00,000)", min_value=50.0, max_value=500000000.0, value=500.0, step=50.0)
                adv_val = st.number_input("Advance Booking Token (if High-Value)", min_value=0.0, max_value=5000000.0, value=11000.0 if is_high else 0.0)
                img_link = st.text_input("Cover Image URL", placeholder="https://example.com/cover.jpg")
                vid_link = st.text_input("360° / Layout Video URL (Optional)", placeholder="https://example.com/video.mp4")
                p_desc = st.text_area("Full Description & Sanctioned Details")

            if st.form_submit_button("🚀 Publish Listing (Free)"):
                if b_name and p_name:
                    conn_i = sqlite3.connect(DB_NAME)
                    conn_i.execute('''
                        INSERT INTO products (vendor_id, brand, title, category, price, is_high_value, advance_booking_amount, video_url, image_url, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (s_id, b_name, p_name, p_cat, p_val, 1 if is_high else 0, adv_val, vid_link, img_link, p_desc))
                    conn_i.commit()
                    conn_i.close()
                    st.success(f"✅ '{b_name} - {p_name}' listed successfully!")
                    st.rerun()

    with t2:
        for _, v in vendors_df.iterrows():
            with st.expander(f"📍 {v['name']} ({v['city']})"):
                toggle_free = st.toggle("Offer FREE Delivery above ₹500", value=bool(v["free_delivery_above_500"]), key=f"f_{v['id']}")
                toggle_spon = st.toggle("Enable Sponsored Top Badge (Ad Promotion)", value=bool(v["is_sponsored"]), key=f"sp_{v['id']}")
                if st.button("Save Settings", key=f"s_{v['id']}"):
                    conn_s = sqlite3.connect(DB_NAME)
                    conn_s.execute("UPDATE vendors SET free_delivery_above_500 = ?, is_sponsored = ? WHERE id = ?", (1 if toggle_free else 0, 1 if toggle_spon else 0, v["id"]))
                    conn_s.commit()
                    conn_s.close()
                    st.success("Settings updated!")
                    st.rerun()

# -----------------------------------------------------------
# TAB 9: REGISTER NEW STORE / AGENCY
# -----------------------------------------------------------
elif menu == "🏬 Register New Store / Agency":
    st.subheader("🏬 Enterprise & Rider Onboarding Portal (PAN-India)")
    
    ob_tab1, ob_tab2 = st.tabs(["🏪 Register Shop / Real Estate Firm", "🛵 Register as Delivery Partner"])
    
    with ob_tab1:
        with st.form("shop_form"):
            s_c1, s_c2 = st.columns(2)
            with s_c1:
                name = st.text_input("Store / Firm Name", placeholder="e.g. First Choice Infra")
                phone = st.text_input("WhatsApp Phone (with 91)", value="919876543210")
                upi = st.text_input("Store UPI ID for Payments", value="store@upi")
                gstin = st.text_input("GSTIN Number (Optional)", value="27ABCDE1234F1Z5")
                rera = st.text_input("RERA Registration No. (If Real Estate)", value="N/A")
                city = st.text_input("City", value="Nagpur")
                address = st.text_input("Address / Project Location")
            with s_c2:
                lat = st.number_input("GPS Latitude", value=21.1450, format="%.4f")
                lon = st.number_input("GPS Longitude", value=79.0800, format="%.4f")
                f_del = st.checkbox("Free Delivery above ₹500", value=True)
                b1 = st.number_input("1 KM Fee (₹)", value=20.0)
                b2 = st.number_input("2 KM Fee (₹)", value=30.0)
                pe = st.number_input("Extra KM Fee (₹)", value=10.0)

            if st.form_submit_button("✅ Register Store / Agency Online"):
                if name and city:
                    conn_r = sqlite3.connect(DB_NAME)
                    conn_r.execute('''
                        INSERT INTO vendors (name, phone, upi_id, gstin, rera_id, is_kyc_verified, is_sponsored, city, address, lat, lon, free_delivery_above_500, base_1km, base_2km, per_km_extra)
                        VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, phone, upi, gstin, rera, city, address, lat, lon, 1 if f_del else 0, b1, b2, pe))
                    conn_r.commit()
                    conn_r.close()
                    st.success(f"🎉 '{name}' successfully registered!")

    with ob_tab2:
        with st.form("rider_reg_form"):
            r_name = st.text_input("Rider Full Name", placeholder="Ramesh Patil")
            r_phone = st.text_input("Rider WhatsApp Phone Number", placeholder="919876540002")
            r_city = st.text_input("City of Operation", value="Nagpur")
            r_veh = st.text_input("Vehicle Number / Mode", placeholder="MH-31-CD-5678")
            if st.form_submit_button("🛵 Register as Delivery Partner"):
                if r_name and r_phone:
                    try:
                        conn_rd = sqlite3.connect(DB_NAME)
                        conn_rd.execute("INSERT INTO riders (name, phone, city, vehicle_number, wallet_balance, status) VALUES (?, ?, ?, ?, 0.0, 'Active')",
                                        (r_name, r_phone, r_city, r_veh))
                        conn_rd.commit()
                        conn_rd.close()
                        st.success(f"🎉 Welcome {r_name}! You are registered as a delivery partner.")
                    except Exception as e:
                        st.error("Phone number already registered.")

# -----------------------------------------------------------
# TAB 10: PLATFORM EARNINGS & TAX LEDGER
# -----------------------------------------------------------
else:
    st.subheader("📊 Platform Revenue, Tax Compliance & 1% Pure Cut")
    conn = sqlite3.connect(DB_NAME)
    orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    settle_all = pd.read_sql_query("SELECT * FROM settlements WHERE status = 'Pending'", conn)
    conn.close()

    total_gross = orders_df["item_price"].sum() if not orders_df.empty else 0.0
    total_comm = orders_df["platform_commission_1pct"].sum() if not orders_df.empty else 0.0
    total_gst_liability = orders_df["platform_gst_18pct"].sum() if not orders_df.empty else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross Deal Turnover", f"₹{total_gross:,.2f}")
    m2.metric("Pure 1% Platform Cut", f"₹{total_comm:,.2f}", delta="Your SaaS Income")
    m3.metric("GST Liability (18% on Fee)", f"₹{total_gst_liability:,.2f}")
    m4.metric("Pending Payouts", len(settle_all))

    st.markdown("---")
    
    an1, an2 = st.columns(2)
    with an1:
        st.write("### 📜 Real-Time Financial & Tax Ledger")
        if not orders_df.empty:
            st.dataframe(orders_df[[
                "id", "customer_name", "items_summary", "item_price", "amount_paid_now",
                "platform_commission_1pct", "platform_gst_18pct", "vendor_net_payout", "status"
            ]], use_container_width=True)
        else:
            st.info("No transactions recorded yet.")

    with an2:
        st.write("### ⚡ Pending Vendor Settlement Approvals")
        if not settle_all.empty:
            for _, s_row in settle_all.iterrows():
                with st.container(border=True):
                    st.write(f"**Vendor #{s_row['vendor_id']}** requested **₹{s_row['amount']:,.2f}** to `{s_row['upi_id']}`")
                    if st.button(f"Mark Paid (Settled)", key=f"payout_btn_{s_row['id']}"):
                        conn_ap = sqlite3.connect(DB_NAME)
                        conn_ap.execute("UPDATE settlements SET status = 'Settled' WHERE id = ?", (s_row['id'],))
                        conn_ap.commit()
                        conn_ap.close()
                        st.success("Payout marked as Settled!")
                        st.rerun()
        else:
            st.success("No pending settlement requests!")