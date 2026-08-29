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
PLATFORM_UPI_ID = "adminplatform@upi" # आपका करंट अकाउंट UPI (जहाँ वॉलेट रिचार्ज का पैसा आएगा)

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
    if "wallet_balance" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN wallet_balance REAL DEFAULT 150.0")
    if "rera_id" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN rera_id TEXT DEFAULT 'N/A'")
    if "is_kyc_verified" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN is_kyc_verified INTEGER DEFAULT 1")
    if "is_sponsored" not in vendor_cols:
        c.execute("ALTER TABLE vendors ADD COLUMN is_sponsored INTEGER DEFAULT 0")

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
            status TEXT DEFAULT 'Completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    log_cols = [col[1] for col in c.execute("PRAGMA table_info(wallet_logs)").fetchall()]
    if "status" not in log_cols:
        c.execute("ALTER TABLE wallet_logs ADD COLUMN status TEXT DEFAULT 'Completed'")

    # Default Demo Store
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
            (1, 'Cotton King', 'Pure Cotton Shirt', 'Fashion', 1000.0, 0, 0.0, '', 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60', 'Pure breathable formal shirt')
        ''')

    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------
# 2. HELPER FUNCTIONS
# -----------------------------------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
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

def generate_pdf_invoice(bill_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "BHARAT HYPERLOCAL MARKETPLACE", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Official Digital Bill / Receipt | GSTIN: {bill_data.get('gstin', 'NON-GST')}", ln=True, align="C")
    pdf.line(10, 28, 200, 28)
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 7, f"Order ID: #{bill_data['order_id']}")
    pdf.cell(90, 7, f"Customer: {bill_data['cust']}", ln=True)
    pdf.cell(100, 7, f"Direct Merchant Store: {bill_data['shop']}")
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
    pdf.cell(120, 7, "Delivery Charges")
    pdf.cell(70, 7, f"Rs {bill_data['fee']:,.2f}", ln=True, align="R")
    pdf.line(10, 85, 200, 85)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 9, "Total Paid to Store directly:")
    pdf.cell(70, 9, f"Rs {bill_data['total']:,.2f}", ln=True, align="R")
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, f"1% Platform Fee (Rs {bill_data['cut']:,.2f}) auto-deducted from merchant prepaid wallet.", ln=True, align="C")
    return pdf.output()

if "cart" not in st.session_state:
    st.session_state.cart = []

# -----------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------
st.sidebar.title("🇮🇳 Bharat Platform")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Marketplace",
    "🛒 Multi-Item Cart Checkout",
    "🏪 Vendor Terminal & Orders",
    "💳 Vendor Wallet & Refund",
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
    detected_lat, detected_lon = 21.1458, 79.0882
    if live_loc and 'coords' in live_loc:
        detected_lat = live_loc['coords']['latitude']
        detected_lon = live_loc['coords']['longitude']

    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: cust_name = st.text_input("Customer Name", value="Rahul Sharma")
    with c2: cust_phone = st.text_input("Customer Phone", value="919876500000")
    with c3: cust_lat = st.number_input("Latitude", value=float(detected_lat), format="%.4f")
    with c4: cust_lon = st.number_input("Longitude", value=float(detected_lon), format="%.4f")

    st.markdown("---")
    
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT p.id, p.brand, p.title, p.price, p.image_url, p.description,
               v.id as vendor_id, v.name as vendor_name, v.phone as vendor_phone, v.upi_id,
               v.wallet_balance as vendor_wallet, v.lat, v.lon, v.gstin
        FROM products p
        JOIN vendors v ON p.vendor_id = v.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        dist = calculate_distance(cust_lat, cust_lon, row["lat"], row["lon"])
        results.append({
            "p_id": row["id"], "brand": row["brand"], "title": row["title"], "price": row["price"],
            "image_url": row["image_url"] if row["image_url"] else "https://via.placeholder.com/300x200?text=Product",
            "v_id": row["vendor_id"], "v_name": row["vendor_name"], "v_phone": str(row["vendor_phone"]),
            "v_upi": row["upi_id"], "v_wallet": row["vendor_wallet"], "v_gstin": row["gstin"],
            "distance": dist, "delivery_fee": 0.0
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
                    
                    if item["v_wallet"] < commission_required:
                        st.error(f"⚠️ {item['v_name']} is currently Offline (Recharge required by shopkeeper).")
                    else:
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button(f"➕ Add to Cart", key=f"cart_{item['p_id']}"):
                                st.session_state.cart.append(item)
                                st.toast(f"Added '{item['brand']} - {item['title']}' to cart!", icon="🛒")
                        with b_col2:
                            if st.button(f"⚡ Buy Now (Rs {item['price']:,.2f})", key=f"btn_{item['p_id']}"):
                                item_total = item["price"]
                                cut_1pct = commission_required
                                gen_otp = str(random.randint(1000, 9999))

                                conn_o = sqlite3.connect(DB_NAME)
                                cur = conn_o.cursor()
                                cur.execute('''
                                    INSERT INTO orders (customer_name, customer_phone, vendor_id, delivery_otp, items_summary, item_price, grand_total, platform_commission_1pct, distance_km, status)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Order Placed')
                                ''', (cust_name, cust_phone, item["v_id"], gen_otp, f"{item['brand']} - {item['title']}", item_total, item_total, cut_1pct, item["distance"]))
                                
                                # ⚡ सिर्फ बिक्री होने पर ही 1% कमीशन वेंडर के वॉलेट से कटेगा
                                cur.execute('UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?', (cut_1pct, item["v_id"]))
                                conn_o.commit()
                                order_id = cur.lastrowid
                                conn_o.close()

                                st.session_state.current_bill = {
                                    "order_id": order_id, "cust": cust_name, "cust_phone": cust_phone,
                                    "otp": gen_otp, "item": f"{item['brand']} - {item['title']}",
                                    "shop": item["v_name"], "shop_phone": item["v_phone"], "shop_upi": item["v_upi"],
                                    "gstin": item["v_gstin"], "price": item_total, "fee": 0.0,
                                    "total": item_total, "cut": cut_1pct, "distance": item["distance"]
                                }

    if "current_bill" in st.session_state:
        b = st.session_state.current_bill
        st.markdown("---")
        st.success(f"🎉 Order #{b['order_id']} Created! Pay 100% Directly to Store:")
        
        q1, q2 = st.columns([1, 1])
        with q1:
            st.markdown(f"### 📱 Scan to Pay Direct to {b['shop']}")
            qr_bytes = generate_upi_qr(b["shop_upi"], b["shop"], b["total"], f"Order_{b['order_id']}")
            st.image(qr_bytes, width=220)
            st.write(f"**Direct Payee UPI:** `{b['shop_upi']}` | **Total:** :green[**Rs {b['total']:,.2f}**]")
            
        with q2:
            st.markdown("### 🧾 Invoice & Settlement")
            st.write(f"**Item:** {b['item']}")
            st.markdown(f"### **Total Paid to Shop:** :green[Rs {b['total']:,.2f}]")
            st.info(f"✅ 1% Platform Fee (Rs {b['cut']:,.2f}) auto-debited from {b['shop']}'s Wallet.")
            pdf_bytes = generate_pdf_invoice(b)
            st.download_button("📄 Download PDF Receipt", data=bytes(pdf_bytes), file_name=f"Invoice_{b['order_id']}.pdf", mime="application/pdf")

# -----------------------------------------------------------
# TAB: MULTI-ITEM CART & CHECKOUT
# -----------------------------------------------------------
elif menu == "🛒 Multi-Item Cart Checkout":
    st.subheader("🛒 Your Shopping Cart")
    
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df[["brand", "title", "price", "v_name", "distance"]], use_container_width=True)

        unique_vendors = cart_df["v_id"].nunique()
        if unique_vendors > 1:
            st.warning("⚠️ Cart contains items from different shops. Please place separate orders.")
        else:
            items_total = cart_df["price"].sum()
            sample_item = st.session_state.cart[0]
            dist = sample_item["distance"]
            fee = 0.0
            final_total = items_total + fee
            
            st.write(f"Items Subtotal: **Rs {items_total:,.2f}** | Delivery: **Rs {fee:,.2f}**")
            st.markdown(f"### Grand Total: :green[**Rs {final_total:,.2f}**]")

            cut_1pct = round(items_total * 0.01, 2)
            if sample_item["v_wallet"] < cut_1pct:
                st.error("⚠️ Store has insufficient wallet balance to process orders. Please contact shop.")
            else:
                if st.button("🚀 Checkout & Pay Directly to Store"):
                    items_summary = ", ".join([f"{x['brand']} {x['title']}" for x in st.session_state.cart])
                    gen_otp = str(random.randint(1000, 9999))

                    conn_co = sqlite3.connect(DB_NAME)
                    cur = conn_co.cursor()
                    cur.execute('''
                        INSERT INTO orders (customer_name, customer_phone, vendor_id, delivery_otp, items_summary, item_price, grand_total, platform_commission_1pct, distance_km, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Order Placed')
                    ''', ("Customer", "919876500000", sample_item["v_id"], gen_otp, items_summary, items_total, final_total, cut_1pct, dist))
                    
                    cur.execute('UPDATE vendors SET wallet_balance = wallet_balance - ? WHERE id = ?', (cut_1pct, sample_item["v_id"]))
                    conn_co.commit()
                    order_id = cur.lastrowid
                    conn_co.close()

                    st.session_state.cart = []
                    st.success(f"🎉 Order #{order_id} placed! 1% Commission auto-debited from store wallet.")
                    st.rerun()

        if st.button("🗑️ Clear Entire Cart"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("Your cart is currently empty.")

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
        v_orders = pd.read_sql_query("SELECT * FROM orders WHERE vendor_id = ? ORDER BY created_at DESC LIMIT 10", conn, params=(selected_vid,))
        conn.close()

        if not v_orders.empty:
            for _, ord_row in v_orders.iterrows():
                with st.container(border=True):
                    col_o1, col_o2 = st.columns([2, 2])
                    with col_o1:
                        st.markdown(f"**Order #{ord_row['id']}** | Customer: `{ord_row['customer_name']}`")
                        st.write(f"Direct Store Received: :green[**Rs {ord_row['grand_total']:,.2f}**]")
                    with col_o2:
                        st.write(f"1% Platform Commission: :red[**-Rs {ord_row['platform_commission_1pct']:,.2f}**]")
                        st.caption("Auto-debited from your prepaid wallet balance.")
        else:
            st.info("No orders received yet for this store.")

# -----------------------------------------------------------
# TAB 3: VENDOR WALLET & REFUND / WITHDRAWAL
# -----------------------------------------------------------
elif menu == "💳 Vendor Wallet & Refund":
    st.subheader("💳 Store Personal Wallet & Refund Manager")

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
                    st.success("🟢 Store is ACTIVE.")

                # ⚡ Percentage Based Withdrawal Request Logic (2% or Min Rs 3)
                st.markdown("---")
                st.markdown("#### 🔄 Withdraw Remaining Balance")
                st.caption("⚠️ **नोट:** विथड्रॉल पर 2% (न्यूनतम ₹3) बैंक और प्लेटफ़ॉर्म प्रोसेसिंग चार्ज काटा जाएगा।")
                
                withdraw_request = curr_vendor['wallet_balance']
                
                # Percentage Logic: 2% of amount, but minimum Rs 3.0
                processing_fee = round(withdraw_request * 0.02, 2)
                if processing_fee < 3.0:
                    processing_fee = 3.0
                
                if withdraw_request > processing_fee:
                    refund_amt = withdraw_request - processing_fee
                    
                    st.write(f"कुल वॉलेट बैलेंस: **Rs {withdraw_request:,.2f}**")
                    st.write(f"प्रोसेसिंग फीस (2%): :red[**- Rs {processing_fee:,.2f}**]")
                    st.write(f"आपके खाते में आएंगे: :green[**Rs {refund_amt:,.2f}**]")
                    
                    if st.button("💸 Request Balance Withdrawal"):
                        conn_wd = sqlite3.connect(DB_NAME)
                        # Set Wallet to 0
                        conn_wd.execute("UPDATE vendors SET wallet_balance = 0.0 WHERE id = ?", (v_select,))
                        # Create Pending Request for Admin
                        conn_wd.execute("INSERT INTO wallet_logs (vendor_id, txn_type, amount, txn_ref, status) VALUES (?, 'WITHDRAWAL_REQUEST', ?, ?, 'Pending Admin Approval')", 
                                        (v_select, refund_amt, f"Refund to UPI: {curr_vendor['upi_id']} (Rs {processing_fee} Fee Deducted)"))
                        conn_wd.commit()
                        conn_wd.close()
                        st.success(f"🎉 रिक्वेस्ट भेज दी गई है! एडमिन अप्रूवल के बाद Rs {refund_amt:,.2f} आपके UPI पर भेज दिए जाएंगे।")
                        st.rerun()
                elif withdraw_request > 0:
                    st.error(f"⚠️ आपका बैलेंस (Rs {withdraw_request:,.2f}) प्रोसेसिंग फीस (Rs {processing_fee:,.2f}) चुकाने के लिए बहुत कम है।")
                else:
                    st.info("No balance available to withdraw.")

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
                        conn_tu.commit()
                        conn_tu.close()
                        st.success(f"🎉 Rs {topup_amt:,.2f} added to wallet!")
                        st.rerun()
                    else:
                        st.error("Please enter UTR Number after payment.")

        st.markdown("---")
        st.write("### 📜 Wallet History (Top-Ups & Requests):")
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
        s_id = st.selectbox("Select Store", vendors_df["id"].tolist(), format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0])
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            b_name = st.text_input("Brand", placeholder="e.g. Mamta Cloth")
            p_name = st.text_input("Product Name", placeholder="e.g. Cotton Shirt")
            p_cat = st.selectbox("Category", ["Fashion", "Grocery", "Daily Essentials"])
        with c_p2:
            p_val = st.number_input("Selling Price (Rs)", min_value=10.0, value=1000.0, step=50.0)
            img_link = st.text_input("Image URL")
            p_desc = st.text_area("Product Details")

        if st.form_submit_button("🚀 Publish Product"):
            if b_name and p_name:
                conn_i = sqlite3.connect(DB_NAME)
                conn_i.execute("INSERT INTO products (vendor_id, brand, title, category, price, image_url, description) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                               (s_id, b_name, p_name, p_cat, p_val, img_link, p_desc))
                conn_i.commit()
                conn_i.close()
                st.success("✅ Product published successfully!")
                st.rerun()

# -----------------------------------------------------------
# TAB 5: REGISTER NEW STORE
# -----------------------------------------------------------
elif menu == "🏬 Register New Store (Free)":
    st.subheader("🏬 Free Merchant Onboarding")
    with st.form("shop_form"):
        s_c1, s_c2 = st.columns(2)
        with s_c1:
            name = st.text_input("Store Name")
            phone = st.text_input("WhatsApp Phone")
            upi = st.text_input("Store Direct UPI ID")
            city = st.text_input("City", value="Nagpur")
        with s_c2:
            lat = st.number_input("GPS Latitude", value=21.1450, format="%.4f")
            lon = st.number_input("GPS Longitude", value=79.0800, format="%.4f")

        if st.form_submit_button("✅ Register Store (Free)"):
            if name and upi:
                conn_r = sqlite3.connect(DB_NAME)
                conn_r.execute("INSERT INTO vendors (name, phone, upi_id, city, lat, lon, wallet_balance) VALUES (?, ?, ?, ?, ?, ?, 0.0)", (name, phone, upi, city, lat, lon))
                conn_r.commit()
                conn_r.close()
                st.success(f"🎉 Store '{name}' registered! Recharge wallet to activate.")

# -----------------------------------------------------------
# TAB 6: PLATFORM EARNINGS LEDGER & ADMIN APPROVALS
# -----------------------------------------------------------
else:
    st.subheader("📊 Platform Admin Panel: 1% Earnings & Withdrawals")
    
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
        st.write("### 📜 Real-Time Commission Deductions:")
        if not orders_df.empty:
            st.dataframe(orders_df[["id", "customer_name", "grand_total", "platform_commission_1pct", "created_at"]], use_container_width=True)

    with an2:
        st.write("### ⚡ Pending Vendor Withdrawals (To be Paid)")
        st.caption("नोट: प्रोसेसिंग फीस पहले ही काट ली गई है। आपको बस नीचे लिखी अमाउंट पे करनी है।")
        if not pending_withdrawals.empty:
            for _, w_row in pending_withdrawals.iterrows():
                with st.container(border=True):
                    st.write(f"**Vendor ID #{w_row['vendor_id']}** requested **Rs {w_row['amount']:,.2f}**")
                    st.info(f"Transfer details: `{w_row['txn_ref']}`")
                    if st.button("✅ Mark Paid (Approve)", key=f"approve_{w_row['id']}"):
                        conn_ap = sqlite3.connect(DB_NAME)
                        conn_ap.execute("UPDATE wallet_logs SET status = 'Refund Completed' WHERE id = ?", (w_row['id'],))
                        conn_ap.commit()
                        conn_ap.close()
                        st.success("✅ Withdrawal marked as Paid!")
                        st.rerun()
        else:
            st.success("No pending withdrawal requests!")