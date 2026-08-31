import streamlit as st
import sqlite3
import pulp
import pandas as pd
import requests

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="FPL AI Optimizer | Premier League Hub",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ปรับแต่ง Theme และ CSS สไตล์พรีเมียร์ลีก
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }
    
    /* พื้นหลังหลัก */
    .stApp {
        background-color: #0b0217;
        color: #ffffff;
    }
    
    /* Header Card */
    .pl-header {
        background: linear-gradient(135deg, #38003c 0%, #200022 100%);
        border: 1px solid #7c0085;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 25px;
        box-shadow: 0 8px 24px rgba(56, 0, 60, 0.4);
    }
    
    .pl-title {
        font-size: 2.3rem;
        font-weight: 700;
        color: #00ff87;
        margin: 0;
        text-shadow: 0 0 10px rgba(0, 255, 135, 0.3);
    }
    
    .pl-subtitle {
        color: #e90052;
        font-size: 1.05rem;
        margin-top: 5px;
        font-weight: 600;
    }

    /* สไตล์การ์ดข้อมูลและผู้จัดการทีม */
    .manager-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(0, 255, 135, 0.25);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }

    /* สไตล์ปุ่มกด Premier League Neon */
    div.stButton > button {
        background: linear-gradient(90deg, #00ff87 0%, #02df76 100%) !important;
        color: #38003c !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 255, 135, 0.2) !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 255, 135, 0.4) !important;
        color: #000000 !important;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(56, 0, 60, 0.45);
        border: 1px solid #57005e;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    div[data-testid="stMetricLabel"] {
        color: #00ff87 !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ส่วนหัวของแดชบอร์ด
st.markdown("""
<div class="pl-header">
    <div class="pl-title">⚽ PREMIER LEAGUE AI OPTIMIZER</div>
    <div class="pl-subtitle">ระบบวิเคราะห์ขุมกำลังและวางแผนการซื้อขายนักเตะด้วยอัลกอริทึมปัญญาประดิษฐ์</div>
</div>
""", unsafe_allow_html=True)

# 3. โหลดข้อมูลนักเตะ
@st.cache_data
def load_data():
    conn = sqlite3.connect('fpl_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT player_id, first_name, second_name, team_id, element_type, now_cost, ep_next FROM Players")
    data = cursor.fetchall()
    conn.close()
    return data

all_players = load_data()
active_players = [p for p in all_players if float(p[6]) > 0]

# 4. แท็บเมนูหลัก
tab1, tab2 = st.tabs(["🚀 จัดทีมใหม่ (Wildcard)", "🔄 ผู้ช่วยเปลี่ยนตัว (Transfer Advisor)"])

# ==========================================
# แท็บที่ 1: ระบบจัดทีมใหม่ (Wildcard)
# ==========================================
with tab1:
    st.sidebar.markdown("### ⚙️ ปรับแต่งเงื่อนไขงบประมาณ")
    max_budget = st.sidebar.slider("💰 งบประมาณทีม (£m)", min_value=80.0, max_value=105.0, value=100.0, step=0.1)
    max_players_per_team = st.sidebar.number_input("โควตานักเตะสูงสุดต่อทีม", min_value=1, max_value=3, value=3)

    if st.button("ประมวลผลจัด 11 ตัวจริงที่ดีที่สุด", use_container_width=True):
        with st.spinner("⚡ AI กำลังคำนวณหาส่วนผสมทีมที่ดีที่สุด..."):
            prob = pulp.LpProblem("FPL", pulp.LpMaximize)
            squad = {p[0]: pulp.LpVariable(f"sq_{p[0]}", cat='Binary') for p in active_players}
            lineup = {p[0]: pulp.LpVariable(f"li_{p[0]}", cat='Binary') for p in active_players}
            cap = {p[0]: pulp.LpVariable(f"cap_{p[0]}", cat='Binary') for p in active_players}
            
            prob += pulp.lpSum((lineup[p[0]] * float(p[6])) + (cap[p[0]] * float(p[6])) for p in active_players)
            prob += pulp.lpSum(squad[p[0]] * p[5] for p in active_players) <= (max_budget * 10)
            prob += pulp.lpSum(squad[p[0]] for p in active_players) == 15
            prob += pulp.lpSum(lineup[p[0]] for p in active_players) == 11
            prob += pulp.lpSum(cap[p[0]] for p in active_players) == 1
            
            for p in active_players:
                prob += lineup[p[0]] <= squad[p[0]]
                prob += cap[p[0]] <= lineup[p[0]]
                
            prob += pulp.lpSum(squad[p[0]] for p in active_players if p[4] == 1) == 2
            prob += pulp.lpSum(squad[p[0]] for p in active_players if p[4] == 2) == 5
            prob += pulp.lpSum(squad[p[0]] for p in active_players if p[4] == 3) == 5
            prob += pulp.lpSum(squad[p[0]] for p in active_players if p[4] == 4) == 3
            prob += pulp.lpSum(lineup[p[0]] for p in active_players if p[4] == 1) == 1
            prob += pulp.lpSum(lineup[p[0]] for p in active_players if p[4] == 2) >= 3
            prob += pulp.lpSum(lineup[p[0]] for p in active_players if p[4] == 4) >= 1
            
            teams = set(p[3] for p in active_players)
            for t in teams:
                prob += pulp.lpSum(squad[p[0]] for p in active_players if p[3] == t) <= max_players_per_team
                
            prob.solve()
            
            pos_name = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
            first_11, bench = [], []
            total_cost, total_xp = 0, 0
            
            for p in active_players:
                if pulp.value(squad[p[0]]) == 1:
                    is_cap = " 👑" if pulp.value(cap[p[0]]) == 1 else ""
                    player_data = {"ตำแหน่ง": pos_name[p[4]], "นักเตะ": f"{p[1]} {p[2]}{is_cap}", "ราคา (£m)": p[5]/10, "xP": float(p[6])}
                    total_cost += p[5]
                    if pulp.value(lineup[p[0]]) == 1:
                        first_11.append(player_data)
                        total_xp += float(p[6]) * (2 if is_cap else 1)
                    else:
                        bench.append(player_data)
                        
            st.write("")
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 งบประมาณที่ใช้", f"£{total_cost/10:.1f}m", f"คงเหลือ £{(max_budget*10 - total_cost)/10:.1f}m")
            col2.metric("⭐ xP รวม 11 ตัวจริง", f"{total_xp:.2f}")
            col3.metric("⚽ แผนการเล่น", f"{sum(1 for p in first_11 if p['ตำแหน่ง']=='DEF')}-{sum(1 for p in first_11 if p['ตำแหน่ง']=='MID')}-{sum(1 for p in first_11 if p['ตำแหน่ง']=='FWD')}")
            
            st.write("")
            col_table1, col_table2 = st.columns(2)
            with col_table1:
                st.markdown("### 🟢 11 ตัวจริง (Starting XI)")
                df_11 = pd.DataFrame(first_11).style.format({"ราคา (£m)": "{:.1f}", "xP": "{:.2f}"})
                st.dataframe(df_11, use_container_width=True, hide_index=True)
            with col_table2:
                st.markdown("### 🪑 ตัวสำรอง (Bench)")
                df_b = pd.DataFrame(bench).style.format({"ราคา (£m)": "{:.1f}", "xP": "{:.2f}"})
                st.dataframe(df_b, use_container_width=True, hide_index=True)

# ==========================================
# แท็บที่ 2: ระบบแนะนำการเปลี่ยนตัว (Transfer Advisor)
# ==========================================
with tab2:
    # เพิ่ม Dropdown เลือกชื่อทีมโปรด หรือพิมพ์ ID เอง
    team_presets = {
        "ทีมหลักของฉัน (ID: 6255553)": "6255553",
        "กรอก Team ID อื่นๆ...": ""
    }
    
    col_preset, col_custom = st.columns([1, 1])
    with col_preset:
        selected_option = st.selectbox("👤 เลือกบัญชีผู้จัดการทีม:", list(team_presets.keys()))
    
    with col_custom:
        if selected_option == "กรอก Team ID อื่นๆ...":
            team_id = st.text_input("กรอก FPL Team ID:", placeholder="เช่น 123456")
        else:
            team_id = team_presets[selected_option]
            st.text_input("FPL Team ID:", value=team_id, disabled=True)
    
    if st.button("วิเคราะห์ตัวเลือกการเปลี่ยนตัว", use_container_width=True):
        if not team_id:
            st.warning("⚠️ กรุณาระบุ FPL Team ID")
        else:
            with st.spinner("🔍 กำลังดึงข้อมูลทีมและประมวลผลการย้ายตัว..."):
                try:
                    # ดึงข้อมูลผู้จัดการทีมจริงจาก API
                    entry_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{team_id}/")
                    manager_name, team_name = "ไม่ระบุชื่อ", "FPL Team"
                    if entry_res.status_code == 200:
                        entry_info = entry_res.json()
                        manager_name = f"{entry_info['player_first_name']} {entry_info['player_last_name']}"
                        team_name = entry_info['name']
                    
                    static_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
                    static_data = requests.get(static_url).json()
                    current_gw = next((event['id'] for event in static_data['events'] if event['is_current']), 1)
                    
                    team_url = f"https://fantasy.premierleague.com/api/entry/{team_id}/event/{current_gw}/picks/"
                    response = requests.get(team_url)
                    
                    if response.status_code == 200:
                        team_data = response.json()
                        my_picks = [pick['element'] for pick in team_data['picks']]
                        bank = team_data['entry_history']['bank']
                        
                        my_team = [p for p in all_players if p[0] in my_picks]
                        suggestions = []
                        
                        for p_out in my_team:
                            current_teams = [p[3] for p in my_team if p[0] != p_out[0]]
                            for p_in in all_players:
                                if (p_in[0] not in my_picks and 
                                    p_in[4] == p_out[4] and 
                                    p_in[5] <= (p_out[5] + bank) and 
                                    current_teams.count(p_in[3]) < 3):
                                    
                                    xp_gain = float(p_in[6]) - float(p_out[6])
                                    if xp_gain > 0:
                                        suggestions.append({
                                            "🔴 ขายออก": f"{p_out[1]} {p_out[2]}",
                                            "🟢 ซื้อเข้า": f"{p_in[1]} {p_in[2]}",
                                            "ราคา (£m)": p_in[5] / 10,
                                            "📈 xP เพิ่มขึ้น": round(xp_gain, 2),
                                            "⭐ xP ใหม่": float(p_in[6])
                                        })
                        
                        suggestions.sort(key=lambda x: x["📈 xP เพิ่มขึ้น"], reverse=True)
                        
                        # กล่องข้อมูลแสดงชื่อทีมและผู้จัดการ
                        st.markdown(f"""
                        <div class="manager-card">
                            <h4 style="margin:0; color:#00ff87;">🛡️ สโมสร: {team_name}</h4>
                            <p style="margin:4px 0 0 0; color:#ffffff; opacity:0.85;">👤 ผู้จัดการทีม: <b>{manager_name}</b> | 💰 เงินคงเหลือในธนาคาร: <b>£{bank/10:.1f}m</b> | 📅 Gameweek: <b>{current_gw}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if not suggestions:
                            st.info("ทีมของคุณอยู่ในสภาพสมบูรณ์แบบ ไม่มีตัวเลือกการเปลี่ยนตัวที่คุ้มค่าในสัปดาห์นี้")
                        else:
                            st.markdown("### 🔄 5 ตัวเลือกการเปลี่ยนตัวที่คุ้มค่าที่สุด")
                            df_styled = pd.DataFrame(suggestions[:5]).style.format({
                                "ราคา (£m)": "{:.1f}",
                                "📈 xP เพิ่มขึ้น": "{:.2f}",
                                "⭐ xP ใหม่": "{:.2f}"
                            }).highlight_max(subset=["📈 xP เพิ่มขึ้น"], color="#22543d")
                            
                            st.dataframe(df_styled, use_container_width=True, hide_index=True)
                    else:
                        st.error("❌ ไม่สามารถดึงข้อมูลทีมได้ โปรดตรวจสอบ Team ID")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
