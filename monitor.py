import gspread
import os
import subprocess
import json
from datetime import datetime
from google.oauth2 import service_account

def ping_check(ip):
    """ฟังก์ชัน Ping แบบ ICMP ส่ง 1 ครั้ง รอ 2 วินาที"""
    try:
        # -c 1 คือส่ง 1 ครั้ง, -W 2 คือรอ 2 วินาที
        process = subprocess.run(
            ['ping', '-c', '1', '-W', '2', ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return "Normal" if process.returncode == 0 else "Down"
    except:
        return "Down"

def run_monitor():
    try:
        # 1. ตั้งค่าการเชื่อมต่อ
        scope = [
            'https://googleapis.com',
            'https://googleapis.com'
        ]
        
        # ดึงค่าจาก GitHub Secrets
        creds_raw = os.environ.get('GOOGLE_CREDS')
        if not creds_raw:
            print("❌ ไม่พบข้อมูล GOOGLE_CREDS ใน Secrets")
            return

        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)

        # 2. เปิดไฟล์ (แก้ไขชื่อไฟล์ให้ตรงกับ Google Sheets ของคุณ)
        SHEET_NAME = "sites-mon" 
        sheet = client.open(SHEET_NAME).get_worksheet(0)

        # 3. ดึง IP จากคอลัมน์ O (คอลัมน์ที่ 15) ตั้งแต่แถวที่ 2 ถึง 40
        # ใช้ดึงรวดเดียวเพื่อประหยัด Quota
        ip_values = sheet.col_values(15)[1:40] 

        results = []
        print(f"🚀 เริ่มตรวจสอบ {len(ip_values)} รายการ...")

        for ip in ip_values:
            ip_str = str(ip).strip()
            if ip_str and ip_str != "0.0.0.0":
                status = ping_check(ip_str)
                results.append([status])
                print(f"IP: {ip_str.ljust(15)} -> {status}")
            else:
                results.append(["Down"])

        # 4. อัปเดตสถานะกลับไปที่คอลัมน์ Q (คอลัมน์ที่ 17)
        if results:
            end_row = 1 + len(results)
            sheet.update(f'Q2:Q{end_row}', results)

        # 5. บันทึกเวลาอัปเดตล่าสุดที่ R2 และสถานะตรวจสอบเสร็จที่ R3
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        sheet.update_acell("R2", f"อัปเดตเมื่อ: {now}")
        sheet.update_acell("R3", "ตรวจสอบเสร็จสมบูรณ์")
        
        print(f"✅ สำเร็จ: {now}")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        # หากเกิด Error ให้แจ้งใน Sheet ด้วยถ้าทำได้
        try:
            sheet.update_acell("R3", f"Error: {str(e)[:50]}")
        except:
            pass

if __name__ == "__main__":
    run_monitor()
