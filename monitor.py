import gspread
import os
import subprocess
import json
from datetime import datetime
from google.oauth2.service_account import Credentials

try:
    # ตั้งค่า Scope
    scope = [
        "https://googleapis.com",
        "https://googleapis.com"
    ]
    
    # ดึง Secret จาก GitHub
    creds_dict = json.loads(os.environ['GOOGLE_CREDS'])
    
    # ใช้ Credentials แบบใหม่ (google-auth)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)

    # *** ระบุชื่อไฟล์ให้ตรงเป๊ะ ***
    SHEET_NAME = "sites-mon" 
    sheet = client.open(SHEET_NAME).get_worksheet(0)

    # อ่าน IP จาก Col O (15) แถว 2 เป็นต้นไป
    ip_list = sheet.col_values(15)[1:40]
    
    results = []
    for ip in ip_list:
        ip = ip.strip()
        if ip and ip != "0.0.0.0":
            # Ping แบบ Linux
            process = subprocess.run(['ping', '-c', '1', '-W', '2', ip], stdout=subprocess.DEVNULL)
            results.append(["Normal"] if process.returncode == 0 else ["Down"])
        else:
            results.append(["Down"])

    if results:
        # อัปเดต Q2 ลงไป
        sheet.update(f"Q2:Q{len(results)+1}", results)

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    sheet.update_acell("R2", f"Update: {now}")
    print(f"✅ Success: {now}")

except Exception as e:
    print(f"❌ Error: {e}")
    raise
