import streamlit as st
import sqlite3
import pulp
import pandas as pd
import requests

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="Premier League AI Hub",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. ปรับแต่ง CSS ถอดแบบธีม Premier League Match Hub
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    /* พื้นหลังหลักธีม Premier League Dark */
    .stApp {
        background-color: #15001c;
        color: #ffffff;
    }

    /* แถบหัวเว็บ Official Top Navigation Bar */
    .pl-nav {
        background: #38003c;
        padding: 16px 28px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .pl-nav-logo {
        font-size: 1.6rem;
        font-weight: 700;
        color: #00ff87;
        letter-spacing: 0.5px;
    }
    .pl-nav-tag {
        background: #e90052;
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* การ์ดสไตล์ Premier League Match Block */
    .pl-card {
        background: #24002c;
        border: 1px solid #3c004a;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 18px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .pl-card:hover {
        border-color: #7c0085;
    }

    /* กล่องรายละเอียดผู้จัดการทีม */
    .pl-manager-box {
        background: linear-gradient(135deg, #2b0035 0%, #1c0024 100%);
        border-left: 4px solid #00ff87;
        border-radius: 10px;
        padding: 14px 20px;
        margin: 15px 0 25px 0;
    }

    /* ปุ่มกดสไตล์ PL */
    div.stButton > button {
        background: #00ff87 !important;
        color: #38003c !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        width: 100%;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background: #02e077 !important;
        color: #000000 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(0, 255, 135, 0.35) !important;
    }

    /* ปรับแต่ง Metrics */
    div[data-testid="stMetric"] {
        background: #24002c;
        border: 1px solid #3c004a;
        border-radius: 10px;
        padding: 12px 18px;
    }
    div[data-testid="stMetricLabel"] {
        color: #00ff87 !important;
        font-size: 0.9rem !important;
    }
</style>
""", unsafe_allow_html=True)

# แถบ Header บาร์บน
st.markdown("""
<div class="pl-nav">
    <div class="pl-nav-logo">🦁 PREMIER LEAGUE <span style="color:#ffffff; font-weight:400; font-size:1.1rem;">| AI Optimizer</span></div>
    <div class="pl-nav-tag">Official Match Engine</div>
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

# 4. แท็บหลัก
tab1, tab2 = st.tabs(["🚀 วางแผนจัดทีม (Squad Builder)", "🔄 ตลาดซื้อขายนักเตะ (Transfer Hub)"])

# ==========================================
# แท็บที่ 1: จัดทีมใหม่
# ==========================================
with tab1:
    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        max_budget = st.slider("💰 เพดานงบประมาณทีม (£m)", min_value=80.0, max_value=105.0, value=100.0, step=0.1)
    with col_ctrl2:
        max_players_per_team = st.number_input("โควตาสูงสุดต่อนักเตะ 1 สโมสร", min_value=1, max_value=3, value=3)

    if st.button("ประมวลผลจัด 11 ตัวจริงที่ดีที่สุด (Optimise XI)"):
        with st.spinner("กำลังวิเคราะห์ความน่าจะเป็นของคะแนน..."):
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
            col1.metric("💰 งบประมาณรวม", f"£{total_cost/10:.1f}m", f"เหลือ £{(max_budget*10 - total_cost)/10:.1f}m")
            col2.metric("⭐ xP คาดหวังรวม", f"{total_xp:.2f}")
            col3.metric("⚽ แผนการเล่น", f"{sum(1 for p in first_11 if p['ตำแหน่ง']=='DEF')}-{sum(1 for p in first_11 if p['ตำแหน่ง']=='MID')}-{sum(1 for p in first_11 if p['ตำแหน่ง']=='FWD')}")
            
            st.write("")
            col_table1, col_table2 = st.columns(2)
            with col_table1:
                st.subheader("🟢 11 ตัวจริง (Starting XI)")
                df_11 = pd.DataFrame(first_11).style.format({"ราคา (£m)": "{:.1f}", "xP": "{:.2f}"})
                st.dataframe(df_11, use_container_width=True, hide_index=True)
            with col_table2:
                st.subheader("🪑 ม้านั่งสำรอง (Bench)")
                df_b = pd.DataFrame(bench).style.format({"ราคา (£m)": "{:.1f}", "xP": "{:.2f}"})
                st.dataframe(df_b, use_container_width=True, hide_index=True)

# ==========================================
# แท็บที่ 2: ระบบแนะนำการเปลี่ยนตัว
# ==========================================
with tab2:
    team_presets = {
        "ทีมของฉัน (ID: 6255553)": "6255553",
        "กรอก Team ID อื่นๆ...": ""
    }
    
    col_p, col_c = st.columns([1, 1])
    with col_p:
        selected_option = st.selectbox("เลือกบัญชีผู้จัดการทีม:", list(team_presets.keys()))
    with col_c:
        if selected_option == "กรอก Team ID อื่นๆ...":
            team_id = st.text_input("กรอก FPL Team ID:", placeholder="เช่น 123456")
        else:
            team_id = team_presets[selected_option]
            st.text_input("FPL Team ID:", value=team_id, disabled=True)
    
    if st.button("วิเคราะห์การเปลี่ยนตัวสัปดาห์นี้ (Analyse Transfers)"):
        if not team_id:
            st.warning("⚠️ กรุณาระบุรหัสทีม")
        else:
            with st.spinner("กำลังเชื่อมต่อเซิร์ฟเวอร์ Premier League..."):
                try:
                    entry_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{team_id}/")
                    manager_name, team_name = "Manager", "Club"
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
                                            "🔴 ขายออก (OUT)": f"{p_out[1]} {p_out[2]}",
                                            "🟢 ซื้อเข้า (IN)": f"{p_in[1]} {p_in[2]}",
                                            "ราคา (£m)": p_in[5] / 10,
                                            "📈 xP เพิ่มขึ้น": round(xp_gain, 2),
                                            "⭐ xP ใหม่": float(p_in[6])
                                        })
                        
                        suggestions.sort(key=lambda x: x["📈 xP เพิ่มขึ้น"], reverse=True)
                        
                        st.markdown(f"""
                        <div class="pl-manager-box">
                            <div style="font-size:1.25rem; font-weight:700; color:#00ff87;">🛡️ {team_name}</div>
                            <div style="font-size:0.95rem; color:#dcdcdc; margin-top:4px;">
                                👤 ผู้จัดการ: <b>{manager_name}</b> | 💰 งบคงเหลือในคลัง: <b>£{bank/10:.1f}m</b> | 📅 สัปดาห์แข่งขัน: <b>Gameweek {current_gw}</b>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if not suggestions:
                            st.info("ทีมของคุณอยู่ในสภาพสมบูรณ์แบบ ไม่มีตัวเลือกการเปลี่ยนตัวที่คุ้มค่าในสัปดาห์นี้")
                        else:
                            st.subheader("🔄 5 ดีลการย้ายตัวที่แนะนำ (Top Transfer Targets)")
                            df_styled = pd.DataFrame(suggestions[:5]).style.format({
                                "ราคา (£m)": "{:.1f}",
                                "📈 xP เพิ่มขึ้น": "{:.2f}",
                                "⭐ xP ใหม่": "{:.2f}"
                            }).highlight_max(subset=["📈 xP เพิ่มขึ้น"], color="#005a2b")
                            
                            st.dataframe(df_styled, use_container_width=True, hide_index=True)
                    else:
                        st.error("❌ ไม่สามารถดึงข้อมูลทีมได้ โปรดตรวจสอบ Team ID")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
