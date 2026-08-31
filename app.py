import streamlit as st
import sqlite3
import pulp
import pandas as pd
import requests

st.set_page_config(
    page_title="Premier League Fantasy Hub",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# สไตล์ CSS ถอดแบบ Official FPL Match Engine
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    .stApp {
        background-color: #0b0217;
        color: #ffffff;
    }

    /* แถบหัวเว็บ Nav Bar */
    .pl-nav {
        background: #38003c;
        padding: 14px 24px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
    }
    .pl-nav-logo {
        font-size: 1.5rem;
        font-weight: 700;
        color: #00ff87;
    }

    /* ผืนสนาม FPL (Vector Pitch) */
    .fpl-pitch-wrapper {
        background: #00a651;
        border-radius: 16px;
        padding: 0 0 20px 0;
        overflow: hidden;
        position: relative;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        max-width: 800px;
        margin: 0 auto;
        border: 2px solid #008741;
    }

    /* แบนเนอร์หัวสนามด้านบน */
    .fpl-pitch-top-banner {
        background: #02efff;
        color: #38003c;
        font-weight: 800;
        font-size: 1.1rem;
        padding: 8px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        letter-spacing: 0.5px;
    }

    /* ลวดลายเส้นสนาม */
    .fpl-pitch-body {
        background-image: 
            linear-gradient(to bottom, rgba(255,255,255,0.2) 2px, transparent 2px),
            radial-gradient(circle at 50% 100%, transparent 60px, rgba(255,255,255,0.2) 61px, rgba(255,255,255,0.2) 63px, transparent 64px);
        padding: 25px 10px 10px 10px;
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    .pitch-row {
        display: flex;
        justify-content: space-around;
        align-items: center;
        width: 100%;
    }

    /* กล่องการ์ดนักเตะสไตล์ FPL */
    .fpl-player-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        width: 105px;
    }

    .fpl-shirt-img {
        width: 58px;
        height: 64px;
        object-fit: contain;
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.35));
    }

    .badge-cap {
        position: absolute;
        top: 2px;
        left: 14px;
        background: #000000;
        color: #ffffff;
        font-weight: 700;
        font-size: 0.65rem;
        border-radius: 50%;
        width: 18px;
        height: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #ffffff;
    }

    .fpl-name-tag {
        background: #ffffff;
        color: #38003c;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px 4px 0 0;
        text-align: center;
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    .fpl-score-tag {
        background: #38003c;
        color: #00ff87;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 1px 6px;
        border-radius: 0 0 4px 4px;
        text-align: center;
        width: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    /* กล่องม้านั่งสำรอง */
    .fpl-bench-wrapper {
        background: rgba(4, 88, 43, 0.95);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 12px;
        padding: 12px;
        margin: 15px 12px 0 12px;
    }
    .fpl-bench-title {
        text-align: center;
        font-weight: 700;
        font-size: 0.9rem;
        color: #ffffff;
        margin-bottom: 8px;
    }

    div.stButton > button {
        background: #00ff87 !important;
        color: #38003c !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        width: 100%;
        border: none !important;
    }
    div[data-testid="stMetric"] {
        background: #24002c;
        border: 1px solid #3c004a;
        border-radius: 10px;
        padding: 12px 18px;
    }
    div[data-testid="stMetricLabel"] {
        color: #00ff87 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="pl-nav"><div class="pl-nav-logo">🦁 Fantasy Premier League</div><div style="font-weight:600; color:#00ff87;">AI Squad Hub</div></div>""", unsafe_allow_html=True)

# ดึงรหัสทีมสำหรับรูปชุดแข่ง
@st.cache_data
def get_team_code_map():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    res = requests.get(url).json()
    return {t['id']: t['code'] for t in res['teams']}

team_code_map = get_team_code_map()

# โหลดข้อมูลนักเตะ (ใช้ 7 คอลัมน์เดิมที่มีในฐานข้อมูล)
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

tab1, tab2 = st.tabs(["🏟️ สนามแข่งขันจำลอง (Pitch View)", "🔄 ผู้ช่วยเปลี่ยนตัว (Transfer Advisor)"])

# ==========================================
# แท็บที่ 1: สนามฟุตบอลสไตล์ Official FPL
# ==========================================
with tab1:
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        max_budget = st.slider("💰 เพดานงบประมาณ (£m)", min_value=80.0, max_value=105.0, value=100.0, step=0.1)
    with col_c2:
        max_players_per_team = st.number_input("โควตาสูงสุดต่อนักเตะ 1 สโมสร", min_value=1, max_value=3, value=3)

    if st.button("จัด 11 ตัวจริงที่ดีที่สุด (Optimise XI)"):
        with st.spinner("กำลังจัดตำแหน่งลงสนาม..."):
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
            
            starting_gk, starting_def, starting_mid, starting_fwd = [], [], [], []
            bench_players = []
            total_cost, total_xp = 0, 0
            
            for p in active_players:
                if pulp.value(squad[p[0]]) == 1:
                    is_c = pulp.value(cap[p[0]]) == 1
                    total_cost += p[5]
                    t_code = team_code_map.get(p[3], 1)
                    shirt_type = "1" if p[4] == 1 else "0"
                    shirt_url = f"https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_{t_code}_{shirt_type}-66.webp"
                    
                    p_info = {
                        "name": p[2], # ใช้นามสกุล/ชื่อหลักเป็นชื่อบนเสื้อ
                        "cost": p[5] / 10,
                        "xp": float(p[6]),
                        "is_cap": is_c,
                        "shirt": shirt_url,
                        "pos": p[4]
                    }
                    
                    if pulp.value(lineup[p[0]]) == 1:
                        total_xp += float(p[6]) * (2 if is_c else 1)
                        if p[4] == 1: starting_gk.append(p_info)
                        elif p[4] == 2: starting_def.append(p_info)
                        elif p[4] == 3: starting_mid.append(p_info)
                        elif p[4] == 4: starting_fwd.append(p_info)
                    else:
                        bench_players.append(p_info)
            
            st.write("")
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 งบประมาณรวม", f"£{total_cost/10:.1f}m", f"เหลือ £{(max_budget*10 - total_cost)/10:.1f}m")
            m2.metric("⭐ xP คาดหวังรวม", f"{total_xp:.2f}")
            m3.metric("⚽ แผนการเล่น", f"{len(starting_def)}-{len(starting_mid)}-{len(starting_fwd)}")
            
            def render_fpl_cards(players):
                items = ""
                for p in players:
                    badge = '<div class="badge-cap">C</div>' if p['is_cap'] else ''
                    items += f'<div class="fpl-player-container">{badge}<img src="{p["shirt"]}" class="fpl-shirt-img"><div class="fpl-name-tag">{p["name"]}</div><div class="fpl-score-tag">xP {p["xp"]:.1f}</div></div>'
                return items

            pitch_html = f'''
            <div class="fpl-pitch-wrapper">
                <div class="fpl-pitch-top-banner">
                    <div>🦁 Fantasy</div>
                    <div>Premier League</div>
                </div>
                <div class="fpl-pitch-body">
                    <div class="pitch-row">{render_fpl_cards(starting_gk)}</div>
                    <div class="pitch-row">{render_fpl_cards(starting_def)}</div>
                    <div class="pitch-row">{render_fpl_cards(starting_mid)}</div>
                    <div class="pitch-row">{render_fpl_cards(starting_fwd)}</div>
                </div>
                <div class="fpl-bench-wrapper">
                    <div class="fpl-bench-title">🪑 ตัวสำรอง (Bench)</div>
                    <div class="pitch-row">{render_fpl_cards(bench_players)}</div>
                </div>
            </div>
            '''
            st.markdown(pitch_html, unsafe_allow_html=True)

# ==========================================
# แท็บที่ 2: ระบบแนะนำการเปลี่ยนตัว
# ==========================================
with tab2:
    team_presets = {"ทีมของฉัน (ID: 6255553)": "6255553", "กรอก Team ID อื่นๆ...": ""}
    col_p, col_c = st.columns([1, 1])
    with col_p:
        selected_option = st.selectbox("เลือกบัญชีผู้จัดการทีม:", list(team_presets.keys()))
    with col_c:
        team_id = team_presets[selected_option] if selected_option != "กรอก Team ID อื่นๆ..." else st.text_input("กรอก FPL Team ID:")
    
    if st.button("วิเคราะห์การเปลี่ยนตัวสัปดาห์นี้"):
        if not team_id:
            st.warning("⚠️ กรุณาระบุรหัสทีม")
        else:
            with st.spinner("กำลังวิเคราะห์..."):
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
                                            "🔴 ขายออก": f"{p_out[1]} {p_out[2]}",
                                            "🟢 ซื้อเข้า": f"{p_in[1]} {p_in[2]}",
                                            "ราคา (£m)": p_in[5] / 10,
                                            "📈 xP เพิ่มขึ้น": round(xp_gain, 2),
                                            "⭐ xP ใหม่": float(p_in[6])
                                        })
                        
                        suggestions.sort(key=lambda x: x["📈 xP เพิ่มขึ้น"], reverse=True)
                        
                        st.markdown(f'<div style="background: linear-gradient(135deg, #2b0035 0%, #1c0024 100%); border-left: 4px solid #00ff87; border-radius: 10px; padding: 14px 20px; margin: 15px 0 25px 0;"><div style="font-size:1.25rem; font-weight:700; color:#00ff87;">🛡️ {team_name}</div><div style="font-size:0.95rem; color:#dcdcdc; margin-top:4px;">👤 ผู้จัดการ: <b>{manager_name}</b> | 💰 งบในคลัง: <b>£{bank/10:.1f}m</b> | 📅 สัปดาห์: <b>Gameweek {current_gw}</b></div></div>', unsafe_allow_html=True)
                        
                        if not suggestions:
                            st.info("ทีมของคุณอยู่ในสภาพสมบูรณ์แบบ")
                        else:
                            st.subheader("🔄 5 ดีลการย้ายตัวที่คุ้มค่าที่สุด")
                            df_styled = pd.DataFrame(suggestions[:5]).style.format({
                                "ราคา (£m)": "{:.1f}",
                                "📈 xP เพิ่มขึ้น": "{:.2f}",
                                "⭐ xP ใหม่": "{:.2f}"
                            }).highlight_max(subset=["📈 xP เพิ่มขึ้น"], color="#005a2b")
                            st.dataframe(df_styled, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
