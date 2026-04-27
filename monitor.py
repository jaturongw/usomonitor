import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import subprocess
import json
from datetime import datetime

# ตั้งค่าสิทธิ์
scope = ["https://google.com", "https://googleapis.com"]
creds_json = json.loads(os.environ['GOOGLE_CREDS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)

# เปิด Sheet (ใส่ชื่อไฟล์ของคุณให้ตรง)
SHEET_NAME = "sites-mon" 
sheet = client.open(SHEET_NAME).get_worksheet(0)

# อ่าน IP จากคอลัมน์ O (15) แถว 2-40
ips = sheet.col_values(15)[1:40]

results = []
for ip in ips:
    ip = ip.strip()
    if ip and ip != "0.0.0.0":
        # ใช้คำสั่ง ping -c 1 (ส่ง 1 แพ็กเกจ)
        process = subprocess.run(['ping', '-c', '1', '-W', '2', ip], stdout=subprocess.DEVNULL)
        results.append(["Normal"] if process.returncode == 0 else ["Down"])
    else:
        results.append(["Down"])

# อัปเดตข้อมูลกลับไปที่คอลัมน์ Q (17) รวดเดียว (ประหยัดโควตา)
sheet.update(f"Q2:Q{len(results)+1}", results)

# บันทึกเวลาล่าสุดที่ช่อง R2
now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
sheet.update_acell("R2", f"Update: {now}")
print(f"Finished at {now}")
