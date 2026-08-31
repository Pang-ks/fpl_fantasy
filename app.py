import streamlit as st
import sqlite3
import pulp
import pandas as pd
import requests

st.set_page_config(page_title="FPL AI Optimizer", layout="wide")
st.title("🏆 FPL AI Optimizer Dashboard")

# 1. ดึงข้อมูลจากฐานข้อมูล
@st.cache_data
def load_data():
    conn = sqlite3.connect('fpl_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT player_id, first_name, second_name, team_id, element_type, now_cost, ep_next FROM Players")
    data = cursor.fetchall()
    conn.close()
    return data

all_players = load_data()
active_players = [p for p in all_players if float(p[6]) > 0] # คัดเฉพาะคนมีคะแนนสำหรับจัดทีมใหม่

# 2. สร้างเมนู 2 แท็บ
tab1, tab2 = st.tabs(["🚀 จัดทีมใหม่ (Wildcard / Free Hit)", "🔄 ผู้ช่วยเปลี่ยนตัว (Transfer Advisor)"])

# ==========================================
# แท็บที่ 1: ระบบจัดทีมใหม่ (Wildcard)
# ==========================================
with tab1:
    st.sidebar.header("⚙️ ตั้งค่าเงื่อนไข AI (โหมดจัดทีมใหม่)")
    max_budget = st.sidebar.slider("💰 งบประมาณสูงสุด (£m)", min_value=80.0, max_value=105.0, value=100.0, step=0.1)
    max_players_per_team = st.sidebar.number_input("โควตานักเตะสูงสุดต่อทีม", min_value=1, max_value=3, value=3)

    if st.button("🚀 ประมวลผลจัดทีมที่ดีที่สุด", use_container_width=True):
        with st.spinner("AI กำลังคำนวณหาส่วนผสมที่ดีที่สุด..."):
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
                        
            st.success("✅ จัดทีมเสร็จสิ้น!")
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 งบประมาณที่ใช้", f"£{total_cost/10}m", f"เหลือ £{(max_budget*10 - total_cost)/10:.1f}m")
            col2.metric("⭐ xP รวม (11 ตัวจริง)", f"{total_xp:.2f}")
            col3.metric("⚽ แผนการเล่น", f"{sum(1 for p in first_11 if p['ตำแหน่ง']=='DEF')}-{sum(1 for p in first_11 if p['ตำแหน่ง']=='MID')}-{sum(1 for p in first_11 if p['ตำแหน่ง']=='FWD')}")
            
            col_table1, col_table2 = st.columns(2)
            with col_table1:
                st.subheader("⚽ 11 ตัวจริง")
                st.dataframe(pd.DataFrame(first_11), use_container_width=True, hide_index=True)
            with col_table2:
                st.subheader("🪑 ตัวสำรอง")
                st.dataframe(pd.DataFrame(bench), use_container_width=True, hide_index=True)

# ==========================================
# แท็บที่ 2: ระบบแนะนำการเปลี่ยนตัว (Transfer Advisor)
# ==========================================
with tab2:
    col_input, _ = st.columns([1, 2])
    with col_input:
        team_id = st.text_input("กรุณากรอก FPL Team ID ของคุณ:", placeholder="เช่น 6255553")
    
    if st.button("วิเคราะห์การเปลี่ยนตัว 1 ตำแหน่ง", type="primary"):
        if not team_id:
            st.warning("⚠️ กรุณากรอก Team ID ก่อนเริ่มวิเคราะห์")
        else:
            with st.spinner("กำลังดึงข้อมูลทีมและประมวลผล..."):
                try:
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
                                            "🔴 ขายทิ้ง": f"{p_out[1]} {p_out[2]}",
                                            "🟢 ซื้อเข้า": f"{p_in[1]} {p_in[2]}",
                                            "ราคา (£m)": p_in[5] / 10,
                                            "📈 xP ที่ได้เพิ่ม": round(xp_gain, 2),
                                            "⭐ xP คาดหวัง": float(p_in[6])
                                        })
                        suggestions.sort(key=lambda x: x["📈 xP ที่ได้เพิ่ม"], reverse=True)
                        
                        st.success(f"✅ วิเคราะห์เสร็จสิ้น! (เงินคงเหลือในธนาคาร: £{bank/10}m)")
                        
                        if not suggestions:
                            st.info("ทีมของคุณลงตัวอยู่แล้ว ไม่มีตัวเลือกที่คุ้มค่าในการเปลี่ยนสัปดาห์นี้")
                        else:
                            st.subheader("🔄 Top 5 ตัวเลือกการเปลี่ยนตัวที่คุ้มค่าที่สุด")
                            
                            # ปรับแต่งตัวเลขทศนิยมให้ดูสะอาดตา และใส่สีไฮไลต์
                            df_styled = pd.DataFrame(suggestions[:5]).style.format({
                                "ราคา (£m)": "{:.1f}",
                                "📈 xP ที่ได้เพิ่ม": "{:.2f}",
                                "⭐ xP คาดหวัง": "{:.2f}"
                            }).highlight_max(subset=["📈 xP ที่ได้เพิ่ม"], color="lightgreen")
                            
                            st.dataframe(df_styled, use_container_width=True, hide_index=True)
                    else:
                        st.error("❌ ไม่สามารถดึงข้อมูลได้ โปรดตรวจสอบ Team ID อีกครั้ง")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")