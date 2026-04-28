import gspread
import os
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

def run_monitor():
    try:
        print("--- เริ่มการทำงาน ---")
        
        # 1. กำหนด Scope (ต้องมี www และ /auth/)
        scope = [
            'https://googleapis.com',
            'https://googleapis.com'
        ]

        # 2. ดึงค่าจาก GitHub Secrets
        creds_raw = os.environ.get('GOOGLE_CREDS')
        if not creds_raw:
            print("❌ Error: ไม่พบข้อมูล GOOGLE_CREDS ใน GitHub Secrets")
            return

        # ตรวจสอบรูปแบบ JSON
        try:
            creds_info = json.loads(creds_raw)
        except Exception as e:
            print(f"❌ Error: ข้อมูลใน Secrets ไม่ใช่ JSON ที่ถูกต้อง: {e}")
            return

        # 3. สร้าง Credentials และบังคับ Refresh เพื่อทดสอบ Token
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scope)
        
        try:
            print("⏳ กำลังขอ Access Token จาก Google...")
            creds.refresh(Request())
            print("✅ ยืนยันตัวตนสำเร็จ (Token Refreshed)")
        except Exception as auth_err:
            # จุดนี้จะบอกชัดเจนว่าทำไม Google ถึงไม่ให้เข้า
            print(f"❌ Google Auth Error: {auth_err}")
            return

        # 4. เชื่อมต่อ gspread
        client = gspread.authorize(creds)

        # 5. เปิดไฟล์ Google Sheet (ต้อง Share ให้ Email ใน JSON แล้วเท่านั้น)
        SHEET_NAME = "sites-mon"
        try:
            spreadsheet = client.open(SHEET_NAME)
            sheet = spreadsheet.get_worksheet(0)
            print(f"✅ เปิดไฟล์ '{SHEET_NAME}' สำเร็จ")
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"❌ Error: หาไฟล์ '{SHEET_NAME}' ไม่พบ (ลืมกด Share หรือชื่อไฟล์ผิด)")
            return

        # 6. ทดสอบ Logic: อ่าน O2 -> เขียน Q2
        val_o2 = sheet.acell('O2').value
        print(f"📖 ค่าในช่อง O2 คือ: '{val_o2}'")

        if val_o2:
            sheet.update_acell('Q2', f"Success: {val_o2}")
            print("✅ เขียนค่าลง Q2 เรียบร้อยแล้ว!")
        else:
            sheet.update_acell('Q2', "Warning: O2 is empty")
            print("⚠️ ช่อง O2 ว่างเปล่า")

        print("--- จบการทำงาน ---")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {str(e)}")

if __name__ == "__main__":
    run_monitor()
