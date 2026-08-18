import streamlit as st
import sqlite3
import math
import urllib.parse
import pandas as pd
import folium
import qrcode
import io
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from fpdf import FPDF

st.set_page_config(
    page_title="Bharat All-in-One Hyperlocal Network",
    page_icon="🛍️",
    layout="wide"
)

DB_NAME = "hyperlocal_market.db"

# -----------------------------------------------------------
# 1. DATABASE SCHEMA & INITIALIZATION
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

    # Products Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            brand TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT,
            description TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id)
        )
    ''')

    # Orders Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            vendor_id INTEGER,
            product_id INTEGER,
            item_price REAL,
            delivery_fee REAL,
            grand_total REAL,
            platform_commission_1pct REAL,
            vendor_net_payout REAL,
            distance_km REAL,
            status TEXT DEFAULT 'Order Placed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Messages / In-App Inquiries Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            sender_name TEXT,
            message_text TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Payout Settlement Requests Table
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

    # Seed Default Data
    c.execute("SELECT COUNT(*) FROM vendors")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO vendors (name, phone, upi_id, city, address, lat, lon, rating, wallet_balance, free_delivery_above_500, base_1km, base_2km, per_km_extra)
            VALUES 
            ('Nagpur Central Mart', '919876543210', 'bharatmart@upi', 'Nagpur', 'Sitabuldi Main Market', 21.1458, 79.0882, 4.9, 1500.0, 1, 20.0, 30.0, 10.0),
            ('Dharampeth Auto & Electronic World', '919876543211', 'dharampethhub@upi', 'Nagpur', 'West High Court Road', 21.1400, 79.0600, 4.7, 49500.0, 0, 20.0, 30.0, 10.0)
        ''')
        c.execute('''
            INSERT INTO products (vendor_id, brand, title, category, price, image_url, description)
            VALUES 
            (1, 'Tata Tea', 'Tata Tea Premium 250g', 'Grocery', 50.0, 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=500&auto=format&fit=crop&q=60', 'Fresh daily morning tea'),
            (1, 'Fortune', 'Refined Sunflower Oil 5L', 'Grocery', 680.0, 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500&auto=format&fit=crop&q=60', 'Pure cooking oil pack'),
            (2, 'Apple', 'iPhone 15 Pro Max 1TB', 'Electronics', 179900.0, 'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=500&auto=format&fit=crop&q=60', 'Brand new sealed smartphone with warranty'),
            (2, 'Commercial Dealership', 'Vehicle Booking Advance Token', 'Automobile', 50000.0, 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=500&auto=format&fit=crop&q=60', 'Express showroom booking advance token')
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
    pdf.cell(0, 6, "Tax Invoice / Delivery Memo", ln=True, align="C")
    pdf.line(10, 28, 200, 28)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 7, f"Order ID: #{bill_data['order_id']}")
    pdf.cell(90, 7, f"Customer: {bill_data['cust']}", ln=True)
    pdf.cell(100, 7, f"Store: {bill_data['shop']}")
    pdf.cell(90, 7, f"Distance: {bill_data['distance']} KM", ln=True)
    pdf.ln(4)

    pdf.line(10, 50, 200, 50)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(120, 7, "Item Description")
    pdf.cell(70, 7, "Amount (INR)", ln=True, align="R")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(120, 7, f"{bill_data['item']}")
    pdf.cell(70, 7, f"Rs {bill_data['price']:,.2f}", ln=True, align="R")
    pdf.cell(120, 7, "Delivery Charges")
    pdf.cell(70, 7, f"Rs {bill_data['fee']:,.2f}", ln=True, align="R")
    
    pdf.line(10, 78, 200, 78)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 9, "Grand Total Paid:")
    pdf.cell(70, 9, f"Rs {bill_data['total']:,.2f}", ln=True, align="R")
    
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, f"Automated 1% Platform Split: Rs {bill_data['cut']:,.2f} | Net Vendor Settle: Rs {bill_data['payout']:,.2f}", ln=True, align="C")
    return pdf.output()

# -----------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------
st.sidebar.title("🇮🇳 Bharat Hyperlocal")
menu = st.sidebar.radio("Navigation Menu", [
    "🛍️ Customer Marketplace",
    "🚚 Track My Orders & Chat",
    "🏪 Vendor Terminal & Orders",
    "💰 Vendor Settlement & Wallet",
    "📦 Add Product / Manage Shop",
    "🏬 Register New Shop",
    "📊 Platform Earnings & Analytics"
])

# -----------------------------------------------------------
# TAB 1: CUSTOMER MARKETPLACE
# -----------------------------------------------------------
if menu == "🛍️ Customer Marketplace":
    st.subheader("📍 Nearby Hyperlocal Marketplace")
    
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
        search_query = st.text_input("🔍 Search any product (e.g. Chai, iPhone, Oil, Sugar):", "")
    with f2:
        cat_filter = st.selectbox("Category Filter", ["All Categories", "Grocery", "Electronics", "Automobile", "Real Estate", "Daily Essentials", "Fashion"])
    with f3:
        price_range = st.selectbox("Budget Filter", ["All Prices (₹50 to ₹5L+)", "Under ₹500", "₹500 - ₹5,000", "Above ₹5,000"])

    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT p.id, p.brand, p.title, p.category, p.price, p.image_url, p.description,
               v.id as vendor_id, v.name as vendor_name, v.phone as vendor_phone, v.upi_id, v.rating as vendor_rating, v.lat, v.lon, 
               v.free_delivery_above_500, v.base_1km, v.base_2km, v.per_km_extra
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
        elif price_range == "Above ₹5,000" and row["price"] <= 5000:
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
            "image_url": row["image_url"] if row["image_url"] else "https://via.placeholder.com/300x200?text=Product+Image",
            "desc": row["description"],
            "v_id": row["vendor_id"],
            "v_name": row["vendor_name"],
            "v_phone": str(row["vendor_phone"]),
            "v_upi": row["upi_id"],
            "v_rating": row["vendor_rating"],
            "v_lat": row["lat"],
            "v_lon": row["lon"],
            "distance": dist,
            "delivery_fee": fee,
            "fee_desc": fee_desc
        })

    results.sort(key=lambda x: x["distance"])

    if results:
        m = folium.Map(location=[cust_lat, cust_lon], zoom_start=13)
        folium.Marker([cust_lat, cust_lon], popup="Customer Location", icon=folium.Icon(color="blue", icon="user")).add_to(m)
        for item in results:
            folium.Marker(
                [item["v_lat"], item["v_lon"]],
                popup=f"{item['v_name']} ({item['distance']} KM)",
                icon=folium.Icon(color="green", icon="shopping-cart")
            ).add_to(m)
        
        st_folium(m, height=230, use_container_width=True)

        cols = st.columns(2)
        for idx, item in enumerate(results):
            with cols[idx % 2]:
                with st.container(border=True):
                    img_col, info_col = st.columns([1, 2])
                    with img_col:
                        st.image(item["image_url"], use_container_width=True)
                    with info_col:
                        st.markdown(f"### {item['brand']} - {item['title']}")
                        st.markdown(f"**Category:** `{item['category']}` | ⭐ `{item['v_rating']}/5.0`")
                        st.markdown(f"Price: :green[**₹{item['price']:,.2f}**]")
                        st.caption(f"🏬 **Store:** {item['v_name']} ({item['distance']} KM away)")
                        
                        del_display = "FREE" if item['delivery_fee'] == 0 else f"₹{item['delivery_fee']:,.2f}"
                        st.write(f"🚚 Delivery: `{del_display}` ({item['fee_desc']})")

                    if st.button(f"🛒 Order & Pay (₹{item['price']:,.2f})", key=f"btn_{item['p_id']}"):
                        item_total = item["price"]
                        del_fee = item["delivery_fee"]
                        grand_total = item_total + del_fee
                        cut_1pct = round(item_total * 0.01, 2)
                        vendor_cut = round(grand_total - cut_1pct, 2)

                        conn_o = sqlite3.connect(DB_NAME)
                        cur = conn_o.cursor()
                        cur.execute('''
                            INSERT INTO orders (customer_name, customer_phone, vendor_id, product_id, item_price, delivery_fee, grand_total, platform_commission_1pct, vendor_net_payout, distance_km, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Order Placed')
                        ''', (cust_name, cust_phone, item["v_id"], item["p_id"], item_total, del_fee, grand_total, cut_1pct, vendor_cut, item["distance"]))
                        
                        # Add vendor net payout to wallet balance
                        cur.execute('UPDATE vendors SET wallet_balance = wallet_balance + ? WHERE id = ?', (vendor_cut, item["v_id"]))
                        conn_o.commit()
                        order_id = cur.lastrowid
                        conn_o.close()

                        st.session_state.current_bill = {
                            "order_id": order_id,
                            "cust": cust_name,
                            "cust_phone": cust_phone,
                            "item": f"{item['brand']} - {item['title']}",
                            "shop": item["v_name"],
                            "shop_phone": item["v_phone"],
                            "upi_id": item["v_upi"],
                            "price": item_total,
                            "fee": del_fee,
                            "total": grand_total,
                            "cut": cut_1pct,
                            "payout": vendor_cut,
                            "distance": item["distance"]
                        }

    # Invoice, Split & Dynamic UPI QR Section
    if "current_bill" in st.session_state:
        b = st.session_state.current_bill
        st.markdown("---")
        st.success(f"🎉 Order #{b['order_id']} Placed! Real-Time UPI QR Generated:")
        
        q1, q2 = st.columns([1, 1])
        with q1:
            st.markdown("### 📱 Scan & Pay via UPI")
            qr_bytes = generate_upi_qr(b["upi_id"], b["shop"], b["total"], f"Order_{b['order_id']}")
            st.image(qr_bytes, width=210)
            st.write(f"**Payee UPI:** `{b['upi_id']}` | **Total:** :green[**₹{b['total']:,.2f}**]")
            
        with q2:
            st.markdown("### 🧾 Invoice Summary")
            st.write(f"**Customer:** {b['cust']} ({b['cust_phone']})")
            st.write(f"**Item:** {b['item']}")
            st.write(f"**Delivery:** ₹{b['fee']:,.2f}")
            st.markdown(f"### **Grand Total:** :green[₹{b['total']:,.2f}]")
            st.info(f"Platform 1% Cut: ₹{b['cut']:,.2f} | Net Vendor Share: ₹{b['payout']:,.2f}")

            pdf_bytes = generate_pdf_invoice(b)
            st.download_button(
                label="📄 Download Official PDF Receipt",
                data=bytes(pdf_bytes),
                file_name=f"Invoice_Order_{b['order_id']}.pdf",
                mime="application/pdf"
            )

            msg_text = (
                f"🛍️ *NEW ORDER #{b['order_id']}*\n"
                f"👤 Customer: {b['cust']}\n"
                f"📦 Item: {b['item']}\n"
                f"💰 Total Amount: Rs {b['total']:,.2f}\n"
                f"📍 Distance: {b['distance']} KM"
            )
            encoded_msg = urllib.parse.quote(msg_text)
            st.link_button("📲 Send to Shopkeeper WhatsApp", f"https://wa.me/{b['shop_phone']}?text={encoded_msg}")

# -----------------------------------------------------------
# TAB 2: TRACK MY ORDERS & IN-APP CHAT
# -----------------------------------------------------------
elif menu == "🚚 Track My Orders & Chat":
    st.subheader("🚚 Track Your Orders & Direct Shop Chat")
    t_phone = st.text_input("Enter your Registered WhatsApp Phone Number:", value="919876500000")
    
    conn = sqlite3.connect(DB_NAME)
    my_orders = pd.read_sql_query('''
        SELECT o.id, o.grand_total, o.status, o.distance_km, o.created_at,
               p.brand, p.title, v.name as shop_name, v.phone as shop_phone
        FROM orders o
        JOIN products p ON o.product_id = p.id
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
                    st.markdown(f"### Order #{o_row['id']} - {o_row['brand']} {o_row['title']}")
                    st.write(f"🏬 **Shop:** {o_row['shop_name']} | 📍 Distance: `{o_row['distance_km']} KM`")
                    st.write(f"**Amount:** :green[**₹{o_row['grand_total']:,.2f}**] | Date: `{o_row['created_at']}`")
                    
                    status = o_row['status']
                    if status == "Order Placed":
                        st.warning("🟡 Status: **Order Placed (Waiting for Shop Dispatch)**")
                    elif status == "Dispatched":
                        st.info("🔵 Status: **Dispatched / Out for Delivery** 🚚")
                    elif status == "Delivered":
                        st.success("🟢 Status: **Delivered Successfully** ✅")

                with c_t2:
                    st.markdown("#### 💬 Live In-App Chat with Store")
                    conn_m = sqlite3.connect(DB_NAME)
                    msgs = pd.read_sql_query("SELECT * FROM messages WHERE order_id = ? ORDER BY sent_at ASC", conn_m, params=(o_row['id'],))
                    conn_m.close()

                    if not msgs.empty:
                        for _, m_row in msgs.iterrows():
                            st.write(f"**{m_row['sender_name']}:** {m_row['message_text']}")
                    
                    with st.form(f"chat_form_{o_row['id']}"):
                        msg_input = st.text_input("Type message / instruction...", key=f"msg_in_{o_row['id']}")
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
# TAB 3: VENDOR TERMINAL & ORDERS
# -----------------------------------------------------------
elif menu == "🏪 Vendor Terminal & Orders":
    st.subheader("🔔 Live Order Terminal (Dispatch Management)")
    
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
            st.components.v1.html("""
                <script>
                var context = new (window.AudioContext || window.webkitAudioContext)();
                var osc = context.createOscillator();
                var gain = context.createGain();
                osc.type = 'sine';
                osc.frequency.value = 880;
                gain.gain.value = 0.2;
                osc.connect(gain);
                gain.connect(context.destination);
                osc.start();
                setTimeout(function(){ osc.stop(); }, 600);
                </script>
            """, height=0)

        st.write("### Recent Orders Table:")
        if not v_orders.empty:
            for _, ord_row in v_orders.iterrows():
                with st.container(border=True):
                    col_o1, col_o2, col_o3 = st.columns([2, 2, 2])
                    with col_o1:
                        st.markdown(f"**Order #{ord_row['id']}** | Customer: `{ord_row['customer_name']}`")
                        st.write(f"Current Status: `{ord_row['status']}` | Total: **₹{ord_row['grand_total']:,.2f}**")
                    with col_o2:
                        st.write(f"Vendor Payout: :green[**₹{ord_row['vendor_net_payout']:,.2f}**]")
                        st.caption(f"Platform 1% Cut: ₹{ord_row['platform_commission_1pct']:,.2f}")
                    with col_o3:
                        if ord_row["status"] == "Order Placed":
                            if st.button("Mark Dispatched 🚚", key=f"disp_{ord_row['id']}"):
                                conn_u = sqlite3.connect(DB_NAME)
                                conn_u.execute("UPDATE orders SET status = 'Dispatched' WHERE id = ?", (ord_row['id'],))
                                conn_u.commit()
                                conn_u.close()
                                st.rerun()
                        elif ord_row["status"] == "Dispatched":
                            if st.button("Mark Delivered ✅", key=f"del_{ord_row['id']}"):
                                conn_u = sqlite3.connect(DB_NAME)
                                conn_u.execute("UPDATE orders SET status = 'Delivered' WHERE id = ?", (ord_row['id'],))
                                conn_u.commit()
                                conn_u.close()
                                st.rerun()
        else:
            st.info("No orders received yet for this store.")

# -----------------------------------------------------------
# TAB 4: VENDOR SETTLEMENT & WALLET
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
        else:
            st.info("No settlement requests yet.")

# -----------------------------------------------------------
# TAB 5: ADD PRODUCT / MANAGE STORE
# -----------------------------------------------------------
elif menu == "📦 Add Product / Manage Shop":
    st.subheader("📦 Product Catalog Management")
    
    conn = sqlite3.connect(DB_NAME)
    vendors_df = pd.read_sql_query("SELECT * FROM vendors", conn)
    conn.close()

    t1, t2 = st.tabs(["➕ List New Product", "⚙️ Store Settings"])
    with t1:
        with st.form("prod_form"):
            s_id = st.selectbox(
                "Select Store", vendors_df["id"].tolist(),
                format_func=lambda x: vendors_df[vendors_df["id"] == x]["name"].values[0]
            )
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                b_name = st.text_input("Brand Name", placeholder="e.g. Sony, Tata, Royal Enfield")
                p_name = st.text_input("Product Title", placeholder="e.g. 50-inch LED TV, 1kg Rice")
                p_cat = st.selectbox("Category", ["Grocery", "Electronics", "Automobile", "Real Estate", "Daily Essentials", "Fashion"])
            with c_p2:
                p_val = st.number_input("Selling Price (₹50 to ₹5,00,000+)", min_value=50.0, max_value=10000000.0, value=500.0, step=50.0)
                img_link = st.text_input("Product Image URL", placeholder="https://example.com/image.jpg")
                p_desc = st.text_area("Specifications / Details")

            if st.form_submit_button("🚀 Publish Product (Free)"):
                if b_name and p_name:
                    conn_i = sqlite3.connect(DB_NAME)
                    conn_i.execute('''
                        INSERT INTO products (vendor_id, brand, title, category, price, image_url, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (s_id, b_name, p_name, p_cat, p_val, img_link, p_desc))
                    conn_i.commit()
                    conn_i.close()
                    st.success(f"✅ '{b_name} - {p_name}' listed at ₹{p_val:,.2f}!")
                    st.rerun()

    with t2:
        for _, v in vendors_df.iterrows():
            with st.expander(f"📍 {v['name']} ({v['city']})"):
                toggle_free = st.toggle("Offer FREE Delivery above ₹500", value=bool(v["free_delivery_above_500"]), key=f"f_{v['id']}")
                if st.button("Save Policy", key=f"s_{v['id']}"):
                    conn_s = sqlite3.connect(DB_NAME)
                    conn_s.execute("UPDATE vendors SET free_delivery_above_500 = ? WHERE id = ?", (1 if toggle_free else 0, v["id"]))
                    conn_s.commit()
                    conn_s.close()
                    st.success("Updated!")
                    st.rerun()

# -----------------------------------------------------------
# TAB 6: REGISTER NEW SHOP
# -----------------------------------------------------------
elif menu == "🏬 Register New Shop":
    st.subheader("🏬 Register New Shop (PAN-India)")
    with st.form("shop_form"):
        s_c1, s_c2 = st.columns(2)
        with s_c1:
            name = st.text_input("Store Name", placeholder="Nagpur General Stores")
            phone = st.text_input("WhatsApp Phone (with 91)", value="919876543210")
            upi = st.text_input("Store UPI ID for Payments", value="store@upi")
            city = st.text_input("City", value="Nagpur")
            address = st.text_input("Address")
        with s_c2:
            lat = st.number_input("GPS Latitude", value=21.1450, format="%.4f")
            lon = st.number_input("GPS Longitude", value=79.0800, format="%.4f")
            f_del = st.checkbox("Free Delivery above ₹500", value=True)
            b1 = st.number_input("1 KM Fee (₹)", value=20.0)
            b2 = st.number_input("2 KM Fee (₹)", value=30.0)
            pe = st.number_input("Extra KM Fee (₹)", value=10.0)

        if st.form_submit_button("✅ Register Store"):
            if name and city:
                conn_r = sqlite3.connect(DB_NAME)
                conn_r.execute('''
                    INSERT INTO vendors (name, phone, upi_id, city, address, lat, lon, free_delivery_above_500, base_1km, base_2km, per_km_extra)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, phone, upi, city, address, lat, lon, 1 if f_del else 0, b1, b2, pe))
                conn_r.commit()
                conn_r.close()
                st.success(f"🎉 '{name}' successfully registered!")

# -----------------------------------------------------------
# TAB 7: PLATFORM EARNINGS & ANALYTICS
# -----------------------------------------------------------
else:
    st.subheader("📊 Platform Revenue & Business Analytics")
    conn = sqlite3.connect(DB_NAME)
    orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    settle_all = pd.read_sql_query("SELECT * FROM settlements WHERE status = 'Pending'", conn)
    conn.close()

    total_gross = orders_df["item_price"].sum() if not orders_df.empty else 0.0
    total_comm = orders_df["platform_commission_1pct"].sum() if not orders_df.empty else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross Turnover", f"₹{total_gross:,.2f}")
    m2.metric("1% Pure Platform Profit", f"₹{total_comm:,.2f}", delta="Your SaaS Cut")
    m3.metric("Total Orders", len(orders_df))
    m4.metric("Pending Payouts", len(settle_all))

    st.markdown("---")
    
    an1, an2 = st.columns(2)
    with an1:
        st.write("### 📜 Real-Time Transaction Ledger")
        if not orders_df.empty:
            st.dataframe(orders_df[[
                "id", "customer_name", "item_price", "delivery_fee",
                "grand_total", "platform_commission_1pct", "vendor_net_payout", "status"
            ]], use_container_width=True)
        else:
            st.info("No transactions recorded yet.")

    with an2:
        st.write("### ⚡ Pending Vendor Payout Approvals")
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
