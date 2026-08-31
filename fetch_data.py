import sqlite3
import requests

# 1. เชื่อมต่อฐานข้อมูล
conn = sqlite3.connect('fpl_data.db')
cursor = conn.cursor()

# 2. สร้างตาราง Players ทิ้งไว้ก่อน (หากยังไม่มี)
cursor.execute('''
CREATE TABLE IF NOT EXISTS Players (
    player_id INTEGER PRIMARY KEY,
    first_name TEXT,
    second_name TEXT,
    team_id INTEGER,
    element_type INTEGER,
    now_cost INTEGER,
    total_points INTEGER,
    ep_next REAL
)
''')

# 3. โหลดข้อมูลจาก API
print("กำลังโหลดข้อมูลจาก FPL API...")
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
response = requests.get(url)
data = response.json()

# 4. วนลูปบันทึกข้อมูล
players = data['elements']
count = 0

for p in players:
    cursor.execute('''
        INSERT OR REPLACE INTO Players (player_id, first_name, second_name, team_id, element_type, now_cost, total_points, ep_next)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        p['id'],
        p['first_name'],
        p['second_name'],
        p['team'],
        p['element_type'],
        p['now_cost'],
        p['total_points'],
        p.get('ep_next', 0.0)
    ))
    count += 1

# 5. ยืนยันการบันทึกและปิดการเชื่อมต่อ
conn.commit()
conn.close()

print(f"บันทึกข้อมูลนักเตะลงฐานข้อมูลสำเร็จจำนวน {count} คน!")