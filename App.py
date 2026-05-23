import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
import os
import sqlite3
import streamlit.components.v1 as components
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date

# --- DIRECTORY FOR LOCAL IMAGE STORAGE ---
IMAGE_DIR = "stored_images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- DATABASE ENGINE & RELATIONSHIPS ---
Base = declarative_base()
engine = create_engine('sqlite:///family_rewards.db', connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    role = Column(String)  # 'Parent' or 'Child'

class TaskTemplate(Base):
    __tablename__ = 'tasks_template'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=0) # 0 means universal master list
    task_name = Column(String)
    points = Column(Float)

class RewardItem(Base):
    __tablename__ = 'rewards_shop'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    store = Column(String) # 'amazon', 'temu', 'custom'
    image_url = Column(String) # Can hold web URLs or local paths like stored_images/abc.png
    url_link = Column(String, default="") # Clickable store link destination
    status = Column(String, default='Active') # 'Active' or 'Pending_Approval'

class Transaction(Base):
    __tablename__ = 'ledger'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    item_name = Column(String)
    amount = Column(Float)
    status = Column(String) # 'Pending', 'Approved', 'Rejected'
    type = Column(String)    # 'Earned', 'Penalty', 'Spent'
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# --- MAP EXPOSED STORAGE FOR STREAMLIT ASSET AVAILABILITY ---
# This allows Streamlit to serve locally saved files over the web structure via a static fallback link
def save_uploaded_image(uploaded_file):
    if uploaded_file is not None:
        file_extension = os.path.splitext(uploaded_file.name)[1]
        filename = f"reward_{int(datetime.utcnow().timestamp())}{file_extension}"
        full_path = os.path.join(IMAGE_DIR, filename)
        with open(full_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return full_path
    return None

# --- INITIAL DATA PROVISIONING ---
if session.query(User).count() == 0:
    session.add_all([
        User(id=0, username="Parent", password="admin123", role="Parent"),
        User(id=1, username="Daughter", password="sparkle123", role="Child")
    ])
    session.commit()

if session.query(TaskTemplate).count() == 0:
    session.add_all([
        TaskTemplate(user_id=0, task_name="🧹 Cleaning My Room", points=1.0),
        TaskTemplate(user_id=0, task_name="😊 Not Crying All Day", points=1.0),
        TaskTemplate(user_id=0, task_name="📚 Doing Homework Without Prompting", points=1.0),
        TaskTemplate(user_id=0, task_name="👭 Helping My Sister", points=1.0),
        TaskTemplate(user_id=0, task_name="🎨 Learning New Skills", points=1.0)
    ])
    session.commit()

# --- BALANCE LEDGER ENGINE ---
def get_balance(user_id, type="spendable"):
    query = session.query(Transaction).filter(Transaction.user_id == user_id, Transaction.status == 'Approved')
    if type == "lifetime":
        return sum([t.amount for t in query.filter(Transaction.type == 'Earned').all()])
    
    earned = sum([t.amount for t in query.filter(Transaction.type == 'Earned').all()])
    spent = sum([t.amount for t in query.filter(Transaction.type == 'Spent').all()])
    penalties = sum([t.amount for t in query.filter(Transaction.type == 'Penalty').all()])
    return earned - spent + penalties

# --- HIDDEN STYLING INJECTION LAYER ---
components.html("""
    <style>
    body { background-color: transparent !important; }
    .stApp { background: linear-gradient(135deg, #FFF0F5 0%, #E6E6FA 100%) !important; }
    </style>
""", height=0)

st.markdown("""
    <link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Fredoka+One&family=Quicksand:wght@500;700&display=swap'>
    <style>
    .stApp { font-family: 'Quicksand', sans-serif !important; }
    h1, h2, h3, h4 { font-family: 'Fredoka One', cursive !important; color: #FF5E97 !important; }
    .lifetime-banner {
        background: linear-gradient(90deg, #FF94B9, #FF69B4); border: 3px solid #FFFFFF;
        border-radius: 25px; padding: 15px; text-align: center; color: white;
        box-shadow: 0px 8px 15px rgba(255, 105, 180, 0.2); margin-bottom: 25px;
    }
    .lifetime-banner h1 { color: #FFFFE0 !important; margin: 5px 0 0 0; font-size: 2.3rem; text-shadow: 2px 2px #FF3385; }
    .shop-card {
        background-color: #FFFFFF; border-radius: 24px; padding: 15px; text-align: center;
        box-shadow: 0 6px 12px rgba(0,0,0,0.04); margin-bottom: 15px; border: 3px solid #FFB2D2;
        position: relative;
    }
    .img-container img { border-radius: 15px; object-fit: cover; margin-bottom: 8px; width: 100%; height: 140px; max-height: 140px; }
    .badge-points { background-color: #FFD700; color: #4A4A4A; font-family: 'Fredoka One'; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; }
    .item-title { font-weight: 700; font-size: 1rem; color: #4A4A4A; margin: 5px 0; }
    .store-tag-link { font-size: 0.85rem; font-weight: bold; text-decoration: none; display: inline-block; margin-bottom: 10px; }
    .tag-amazon { color: #FF9900; } .tag-temu { color: #FF5500; } .tag-custom { color: #9b5de5; }
    .cal-day-box { background-color: white; border: 2px solid #FFD1DC; border-radius: 10px; padding: 8px; text-align: center; min-height: 75px; }
    .cal-points-pos { color: #28a745; font-weight: bold; } .cal-points-neg { color: #dc3545; font-weight: bold; }
    div.stButton > button { font-family: 'Fredoka One' !important; background: linear-gradient(135deg, #FF69B4 0%, #FF1493 100%) !important; color: white !important; border-radius: 20px !important; }
    </style>
""", unsafe_allow_html=True)

# --- APPLICATION CONTROLLER ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; margin-top: 40px;'>👑 Sparkle Rewards</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        user_choice = st.selectbox("Who is logging in?", [u.username for u in session.query(User).all()])
        password = st.text_input("Enter Password", type="password")
        if st.form_submit_button("Let's Go! ✨"):
            user_record = session.query(User).filter(User.username == user_choice, User.password == password).first()
            if user_record:
                st.session_state.logged_in = True
                st.session_state.role = user_record.role
                st.session_state.user_id = user_record.id
                st.session_state.username = user_record.username
                st.rerun()
            else: st.error("Oops! Wrong password! 💕")
else:
    menu = st.sidebar.radio("Navigation Menu", ["Dashboard", "Rewards Shop", "Points Calendar", "Parent Portal", "Settings & Security"])
    
    # --- DASHBOARD VIEW ---
    if menu == "Dashboard":
        st.markdown(f"<h1 style='text-align: center;'>👧 {st.session_state.username}'s Dashboard</h1>", unsafe_allow_html=True)
        st.markdown(f"""<div class="lifetime-banner"><h2>✨ SPENDABLE BALANCE ✨</h2><h1>${get_balance(st.session_state.user_id):.2f}</h1><p style="margin: 5px 0 0 0; font-weight: bold; color: #FFF0F5;">Lifetime Earned: {get_balance(st.session_state.user_id, 'lifetime'):.0f} Points</p></div>""", unsafe_allow_html=True)

        st.subheader("🌟 Claim Your Tasks")
        active_tasks = session.query(TaskTemplate).filter((TaskTemplate.user_id == 0) | (TaskTemplate.user_id == st.session_state.user_id)).all()
        
        for t in active_tasks:
            if st.button(f"Done: {t.task_name} (+${t.points:.2f})", key=f"t_{t.id}"):
                session.add(Transaction(user_id=st.session_state.user_id, item_name=t.task_name, amount=t.points, status='Pending', type='Earned'))
                session.commit()
                st.success("Sent to Mom/Dad for approval! 💌")

    # --- SHOP VIEW ---
    elif menu == "Rewards Shop":
        st.markdown("<h1 style='text-align: center;'>🎁 REWARDS SHOP</h1>", unsafe_allow_html=True)
        st.markdown(f"""<div class="lifetime-banner" style="background: linear-gradient(90deg, #B39DDB, #9575CD);"><h2>👛 YOUR WALLET</h2><h1>${get_balance(st.session_state.user_id):.2f}</h1></div>""", unsafe_allow_html=True)
        
        active_rewards = session.query(RewardItem).filter(RewardItem.status == 'Active').all()
        if not active_rewards:
            st.info("The shop is currently waiting for parents to add items!")
        else:
            col1, col2 = st.columns(2)
            for idx, r in enumerate(active_rewards):
                target_col = col1 if idx % 2 == 0 else col2
                with target_col:
                    # Determine if it's a local file stream or an online image URL link
                    img_src = r.image_url
                    if img_src.startswith("stored_images"):
                        # If image is saved locally, we read the bytes to safely bypass system browser constraints
                        if os.path.exists(img_src):
                            with open(img_src, "rb") as image_file:
                                import base64
                                encoded_string = base64.b64encode(image_file.read()).decode()
                                img_src = f"data:image/png;base64,{encoded_string}"
                    
                    # Store link assignment check
                    link_html = f'<a href="{r.url_link}" target="_blank" class="store-tag-link tag-{r.store}">🛍️ view on {r.store} ↗️</a>' if r.url_link else f'<span class="store-tag-link tag-{r.store}">🛍️ {r.store}</span>'

                    st.markdown(f"""
                        <div class="shop-card">
                            <div class="img-container"><img src="{img_src}"></div>
                            <div class="badge-points">★ {r.price:.2f} POINTS</div>
                            <div class="item-title">{r.name}</div>
                            {link_html}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if get_balance(st.session_state.user_id) >= r.price:
                        if st.button(f"Redeem Now", key=f"buy_{r.id}"):
                            session.add(Transaction(user_id=st.session_state.user_id, item_name=f"Purchased: {r.name}", amount=r.price, status='Pending', type='Spent'))
                            session.commit()
                            st.balloons()
                            st.success("Purchase request sent! 🎉")
                    else:
                        st.button("Locked 🔒", disabled=True, key=f"lock_{r.id}")

        st.divider()
        st.subheader("💡 Pitch/Suggest a Custom Reward!")
        with st.form("suggest_reward_form"):
            s_name = st.text_input("What reward do you want to add?")
            s_link = st.text_input("Paste web store link here (Optional)")
            s_pts = st.number_input("How many points do you think it is worth?", min_value=1.0, step=1.0)
            if st.form_submit_button("Send Pitch to Parents! 🚀"):
                if s_name:
                    session.add(RewardItem(name=f"⭐ Pitch: {s_name}", price=s_pts, store="custom", url_link=s_link, image_url="https://images.unsplash.com/photo-1513151233558-d860c5398176?w=200", status='Pending_Approval'))
                    session.commit()
                    st.success("Pitch submitted successfully!")

    # --- CALENDAR VIEW ---
    elif menu == "Points Calendar":
        st.markdown("<h1 style='text-align: center;'>📅 Calendar Tracking Matrix</h1>", unsafe_allow_html=True)
        child_profiles = session.query(User).filter(User.role == 'Child').all()
        selected_profile = st.selectbox("Select Profile Tracker:", [u.username for u in child_profiles])
        target_user = session.query(User).filter(User.username == selected_profile).first()
        
        col_m, col_y = st.columns(2)
        selected_month = col_m.selectbox("Month", list(calendar.month_name)[1:], index=date.today().month - 1)
        selected_year = col_y.selectbox("Year", [2025, 2026, 2027], index=1)
        
        m_idx = list(calendar.month_name).index(selected_month)
        matrix = calendar.monthcalendar(selected_year, m_idx)
        
        all_tx = session.query(Transaction).filter(Transaction.user_id == target_user.id, Transaction.status == 'Approved').all()
        totals = {}
        for tx in all_tx:
            totals[tx.timestamp.date()] = totals.get(tx.timestamp.date(), 0.0) + tx.amount

        cols = st.columns(7)
        for i, h in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            cols[i].markdown(f"<p style='text-align:center;font-weight:bold;color:#FF5E97;'>{h}</p>", unsafe_allow_html=True)
            
        for week in matrix:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day > 0:
                    box_date = date(selected_year, m_idx, day)
                    pts = totals.get(box_date, 0.0)
                    score_text = f"<span class='cal-points-pos'>+${pts:.1f}</span>" if pts > 0 else (f"<span class='cal-points-neg'>-${abs(pts):.1f}</span>" if pts < 0 else "<span style='color:#bbb;'>$0</span>")
                    cols[i].markdown(f"<div class='cal-day-box'><b>{day}</b><br>{score_text}</div>", unsafe_allow_html=True)

    # --- PARENT PORTAL ---
    elif menu == "Parent Portal":
        if st.session_state.role != "Parent": st.error("Access Denied!")
        else:
            st.title("🔐 Parent Control Center")
            
            # --- INBOX QUEUE ---
            st.subheader("📥 Incoming Approvals Queue")
            pending_tx = session.query(Transaction).filter(Transaction.status == 'Pending').all()
            pending_pitches = session.query(RewardItem).filter(RewardItem.status == 'Pending_Approval').all()
            
            if not pending_tx and not pending_pitches:
                st.write("Inbox clean! No tasks or pitches pending.")
                
            for p in pending_tx:
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"👉 **{p.type}**: {p.item_name} (${p.amount:.2f})")
                if c2.button("Approve ✅", key=f"tx_a_{p.id}"):
                    p.status = 'Approved'
                    session.commit()
                    st.rerun()
                if c3.button("Reject ❌", key=f"tx_r_{p.id}"):
                    p.status = 'Rejected'
                    session.commit()
                    st.rerun()

            for pitch in pending_pitches:
                st.info(f"💡 **Daughter Pitched:** {pitch.name} | Suggested Cost: {pitch.price:.0f} pts")
                c1, c2, c3 = st.columns([2, 1, 1])
                final_p = c1.number_input("Finalized Parent Store Price ($):", min_value=1.0, value=pitch.price, key=f"pt_price_{pitch.id}")
                if c2.button("Unlock👍", key=f"pt_a_{pitch.id}"):
                    pitch.price = final_p
                    pitch.status = 'Active'
                    session.commit()
                    st.rerun()
                if c3.button("Dismiss 🗑️", key=f"pt_r_{pitch.id}"):
                    session.delete(pitch)
                    session.commit()
                    st.rerun()

            # --- MANAGE CHORES ---
            st.divider()
            st.subheader("📋 Task Template Configuration Manager")
            kids = session.query(User).filter(User.role == 'Child').all()
            target_task_kid = st.selectbox("Assign/Manage Tasks for profile:", ["Universal Master List"] + [k.username for k in kids])
            t_user_id = 0 if target_task_kid == "Universal Master List" else session.query(User).filter(User.username == target_task_kid).first().id
            
            with st.form("add_task_form"):
                new_t_name = st.text_input("Chore / Task Name:")
                new_t_pts = st.number_input("Reward Dollar Value ($):", min_value=0.1, value=1.0, step=0.5)
                if st.form_submit_button("Save Task Template"):
                    if new_t_name:
                        session.add(TaskTemplate(user_id=t_user_id, task_name=new_t_name, points=new_t_pts))
                        session.commit()
                        st.rerun()

            current_templates = session.query(TaskTemplate).filter(TaskTemplate.user_id == t_user_id).all()
            for ct in current_templates:
                col_ct1, col_ct2 = st.columns([4, 1])
                col_ct1.write(f"🔹 {ct.task_name} | `${ct.points:.2f}`")
                if col_ct2.button("Delete 🗑️", key=f"del_ct_{ct.id}"):
                    session.delete(ct)
                    session.commit()
                    st.rerun()

            # --- REWARD SHOP MANAGER WITH LOCAL FILE UPLOAD AND LINKS ---
            st.divider()
            st.subheader("🛒 Reward Shop Inventory Manager")
            with st.form("add_shop_item_form", clear_on_submit=True):
                rs_name = st.text_input("Product Title:")
                rs_price = st.number_input("Cost Value ($):", min_value=1.0, value=10.0, step=1.0)
                rs_store = st.selectbox("Platform Tag:", ["amazon", "temu", "custom"])
                rs_link = st.text_input("Store Purchase Web URL Link (e.g., specific item page):")
                
                st.write("Item Image Source Setup:")
                image_source = st.radio("Choose image source type:", ["Upload from local PC", "Paste web image URL"])
                uploaded_img = st.file_uploader("Choose a file from your computer:", type=["png", "jpg", "jpeg"]) if image_source == "Upload from local PC" else None
                fallback_url = st.text_input("Or paste Web Image URL Link here:", value="https://images.unsplash.com/photo-1513151233558-d860c5398176?w=200") if image_source == "Paste web image URL" else ""
                
                if st.form_submit_button("Publish Product Item to Store"):
                    if rs_name:
                        final_img_path = fallback_url
                        if image_source == "Upload from local PC" and uploaded_img is not None:
                            final_img_path = save_uploaded_image(uploaded_img)
                        
                        session.add(RewardItem(
                            name=rs_name, 
                            price=rs_price, 
                            store=rs_store, 
                            image_url=final_img_path if final_img_path else "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=200", 
                            url_link=rs_link,
                            status='Active'
                        ))
                        session.commit()
                        st.success("Successfully added item to the live store database!")
                        st.rerun()

            st.write("Current Store Inventory Items:")
            inv = session.query(RewardItem).filter(RewardItem.status == 'Active').all()
            for item in inv:
                col_i1, col_i2 = st.columns([4, 1])
                link_status_tag = "🔗 has link" if item.url_link else "⚠️ no link"
                col_i1.write(f"🛍️ **{item.name}** [${item.price:.2f}] ({item.store} | {link_status_tag})")
                if col_i2.button("Delete 🗑️", key=f"del_i_{item.id}"):
                    # Clean up local image file if it exists to preserve storage space
                    if item.image_url.startswith("stored_images/") and os.path.exists(item.image_url):
                        os.remove(item.image_url)
                    session.delete(item)
                    session.commit()
                    st.rerun()

            # --- PROFILE CREATOR ---
            st.divider()
            st.subheader("👥 Multi-Kid Profile Manager")
            with st.form("add_profile_form"):
                new_kid_name = st.text_input("Enter New Profile Name:")
                new_kid_pass = st.text_input("Set Profile Password:", type="password")
                if st.form_submit_button("Create Profile Account"):
                    if new_kid_name and new_kid_pass:
                        if session.query(User).filter(User.username == new_kid_name).first():
                            st.error("Profile name already exists!")
                        else:
                            session.add(User(username=new_kid_name, password=new_kid_pass, role="Child"))
                            session.commit()
                            st.rerun()

            # --- BEHAVIOR PENALTY TOOL ---
            st.divider()
            st.subheader("⚠️ Log behavioral Penalty")
            penalty_reason = st.selectbox("Reason", ["Talking back/shouting", "Fighting with sister", "Repeated prompting", "Custom"])
            p_amt = st.number_input("Amount to deduct ($)", min_value=0.0, value=1.0, step=0.5)
            if st.button("Deduct Points"):
                session.add(Transaction(user_id=1, item_name=penalty_reason, amount=-p_amt, status='Approved', type='Penalty'))
                session.commit()
                st.rerun()

            # --- GRANULAR LEDGER AUDITING ---
            st.divider()
            st.subheader("🛠️ Granular Ledger Log Auditing")
            history_tx = session.query(Transaction).filter(Transaction.status == 'Approved').order_by(Transaction.timestamp.desc()).all()
            for tx in history_tx:
                col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
                col_h1.write(f"📅 {tx.timestamp.strftime('%Y-%m-%d')} | **{tx.type}**")
                col_h2.write(f"{tx.item_name}: `${tx.amount:.2f}`")
                if col_h3.button("Delete 🗑️", key=f"del_tx_{tx.id}"):
                    session.delete(tx)
                    session.commit()
                    st.rerun()

            # --- BULK MAINTENANCE CONTROLS ---
            st.divider()
            st.subheader("🧹 Bulk Maintenance Controls")
            maintenance_option = st.radio("Select scope to clear:", ["None", "Clear Specific Day", "Reset Entire Ledger"])
            if maintenance_option == "Clear Specific Day":
                target_date = st.date_input("Select calendar day to clean completely:")
                if st.button("🚨 Clear Selected Day"):
                    session.query(Transaction).filter(text("DATE(timestamp) = :target_date")).params(target_date=str(target_date)).delete(synchronize_session='fetch')
                    session.commit()
                    st.rerun()
            elif maintenance_option == "Reset Entire Ledger":
                confirm_word = st.text_input("Type 'RESET' to wipe data logs:")
                if st.button("💥 Reset Everything"):
                    if confirm_word == "RESET":
                        session.query(Transaction).delete()
                        session.commit()
                        st.rerun()

    # --- SECURITY MANAGEMENT ---
    elif menu == "Settings & Security":
        st.title("⚙️ Security Profiles Settings")
        account_to_update = st.selectbox("Select account to update credentials:", [u.username for u in session.query(User).all()])
        with st.form("password_update_form"):
            current_pass = st.text_input("Current Account Password", type="password")
            new_pass = st.text_input("New Target Password", type="password")
            confirm_new_pass = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                user_account = session.query(User).filter(User.username == account_to_update).first()
                if not user_account or user_account.password != current_pass: st.error("The current password provided is incorrect.")
                elif new_pass != confirm_new_pass: st.error("The new confirmation password text entries do not match.")
                elif len(new_pass.strip()) < 4: st.error("Please pick a safer password (at least 4 characters).")
                else:
                    user_account.password = new_pass
                    session.commit()
                    st.success(f"Successfully updated credentials for {account_to_update}!")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
