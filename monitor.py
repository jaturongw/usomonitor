import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import subprocess
import json
from datetime import datetime

try:
    scope = ["https://google.com", "https://googleapis.com"]
    
    # เช็คว่ามี Secret หรือไม่
    if 'GOOGLE_CREDS' not in os.environ:
        raise ValueError("หา Secret ชื่อ GOOGLE_CREDS ไม่เจอใน GitHub Settings")

    creds_json = json.loads(os.environ['GOOGLE_CREDS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)

    # *** ตรวจสอบชื่อไฟล์ตรงนี้ให้ตรงเป๊ะ ***
    SHEET_NAME = "sites-mon" 
    sheet = client.open(SHEET_NAME).get_worksheet(0)

    # อ่านค่าจากคอลัมน์ O
    ip_list = sheet.col_values(15)[1:40]
    
    results = []
    for ip in ip_list:
        ip = ip.strip()
        if ip and ip != "0.0.0.0":
            # ส่ง ping 1 ครั้ง รอ 2 วินาที
            process = subprocess.run(['ping', '-c', '1', '-W', '2', ip], stdout=subprocess.DEVNULL)
            results.append(["Normal"] if process.returncode == 0 else ["Down"])
        else:
            results.append(["Down"])

    if results:
        sheet.update(f"Q2:Q{len(results)+1}", results)

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    sheet.update_acell("R2", f"Update: {now}")
    print(f"✅ สำเร็จ: อัปเดตเมื่อ {now}")

except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")
    raise  # บังคับให้แสดง Error ตัวจริงใน Log

