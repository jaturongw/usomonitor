import gspread
import os
import subprocess
import json
from datetime import datetime
from google.oauth2 import service_account

def ping_check(ip):
    """ฟังก์ชัน Ping แบบ ICMP ส่ง 1 ครั้ง รอ 2 วินาที (ทำงานบน Linux ของ GitHub)"""
    try:
        # ล้างช่องว่างเผื่อมี space ปนมา
        ip = ip.strip()
        if not ip or ip == "0.0.0.0":
            return "Down"
            
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
        # 1. ตั้งค่า Scopes ให้ถูกต้อง (ต้องมี /auth/)
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

        # 2. เปิดไฟล์ (แนะนำให้ใช้ชื่อหน้าที่แน่นอนแทนเลข 0 ถ้าเป็นไปได้)
        SHEET_NAME = "sites-mon"
        spreadsheet = client.open(SHEET_NAME)
        sheet = spreadsheet.get_worksheet(0) # หน้าแรกซ้ายสุด

        # เขียนสถานะเริ่มต้นลง R1 เพื่อทดสอบว่าเชื่อมต่อถูกไฟล์
        sheet.update_acell("R1", "🔄 กำลังตรวจสอบ...")

        # 3. ดึง IP จากคอลัมน์ O2 ถึง O40
        # get_values คืนค่าเป็น List ของ List เช่น [['1.1.1.1'], ['2.2.2.2']]
        ip_data = sheet.get_values('O2:O40')
        
        results = []
        print(f"🚀 เริ่มตรวจสอบ {len(ip_data)} รายการ...")

        for row in ip_data:
            # ตรวจสอบว่ามีข้อมูลในแถวไหม
            if row and row[0].strip():
                ip_str = row[0].strip()
                status = ping_check(ip_str)
                results.append([status])
                print(f"IP: {ip_str.ljust(15)} -> {status}")
            else:
                # ถ้าแถวว่าง ให้ใส่ "Down" หรือ "-"
                results.append(["Down"])

        # 4. อัปเดตสถานะกลับไปที่คอลัมน์ Q2:Q...
        if results:
            end_row = 1 + len(results)
            range_to_update = f'Q2:Q{end_row}'
            sheet.update(values=results, range_name=range_to_update)

        # 5. บันทึกเวลาอัปเดตล่าสุดที่ R2 และ R3
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        sheet.update_acell("R1", "✅ พร้อม") # ล้างสถานะกำลังทำ
        sheet.update_acell("R2", f"อัปเดตเมื่อ: {now}")
        sheet.update_acell("R3", "ตรวจสอบเสร็จสมบูรณ์")
        
        print(f"✅ ทำงานสำเร็จเมื่อ: {now}")

    except Exception as e:
        error_msg = f"❌ เกิดข้อผิดพลาด: {str(e)}"
        print(error_msg)
        # พยายามเขียน Error ลงใน Sheet ถ้าเปิดไฟล์ได้
        try:
            sheet.update_acell("R3", f"Error: {str(e)[:50]}")
        except:
            pass

if __name__ == "__main__":
    run_monitor()
