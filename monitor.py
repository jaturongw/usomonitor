import gspread
import os
import subprocess
import json
from datetime import datetime
from google.oauth2 import service_account

def ping_check(ip):
    """ส่ง ICMP 1 ครั้ง รอ 2 วินาที"""
    try:
        # ใช้ -n 1 สำหรับ Windows, -c 1 สำหรับ Linux
        # สั่ง Timeout ด้วย -W (Linux) หรือ -w (Windows)
        process = subprocess.run(
            ['ping', '-c', '1', '-W', '2', ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return "Normal" if process.returncode == 0 else "Down"
    except Exception:
        return "Down"

def run_monitor():
   def run_monitor():
    try:
        # บรรทัดเหล่านี้ต้องมีย่อหน้า (Indent) เข้ามา 2 ระดับ
        scope = [
            'https://googleapis.com',
            'https://googleapis.com'
        ]
        # ... โค้ดส่วนที่เหลือใน try ก็ต้องย่อหน้าให้ตรงกัน ...
        
        creds_raw = os.environ.get('GOOGLE_CREDS')
        if not creds_raw:
            print("❌ Error: GOOGLE_CREDS not found in environment variables")
            return

        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)

        # 2. Open Sheet
        SHEET_NAME = "sites-mon"
        sheet = client.open(SHEET_NAME).get_worksheet(0)
        print(sheet.title)

        # 3. ดึงข้อมูลเฉพาะช่วงที่ต้องการ (O2:O40) เพื่อลด Load
        # get_values คืนค่าเป็น List of Lists [[val], [val]]
        ip_range = sheet.get_values('O2:O40')
        
        results = []
        print(f"🚀 Starting check for {len(ip_range)} items...")

        for row in ip_range:
            # ตรวจสอบว่ามีข้อมูลในแถวนั้นไหม
            ip_str = str(row[0]).strip() if row else ""
            
            if ip_str and ip_str not in ["0.0.0.0", "None", ""]:
                status = ping_check(ip_str)
                results.append([status])
                print(f"IP: {ip_str.ljust(15)} -> {status}")
            else:
                results.append(["Down"])

        # 4. Batch Update กลับไปที่คอลัมน์ Q2 เป็นต้นไป
        if results:
            end_row = 1 + len(results)
            sheet.update(f'Q2:Q{end_row}', results)

        # 5. Timestamp
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        updates = [
            {'range': 'R2', 'values': [[f"อัปเดตเมื่อ: {now} "]]},
            {'range': 'R3', 'values': [["ตรวจสอบเสร็จสมบูรณ์"]]}
        ]
        sheet.batch_update(updates)
        
        print(f"✅ Success: {now}")

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        try:
            sheet.update_acell("R3", f"Error at {datetime.now().strftime('%H:%M')}: {str(e)[:40]}")
        except:
            pass

if __name__ == "__main__":
    run_monitor()
