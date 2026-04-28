import gspread
import os
import json
from google.oauth2 import service_account

def run_monitor():  # เปลี่ยนชื่อกลับเป็น run_monitor ตามที่ไฟล์ Workflow เรียก
    try:
        # 1. SCOPE ต้องถูกต้องและครบถ้วน
        scope = [
            'https://googleapis.com',
            'https://googleapis.com'
        ]

        # 2. ดึงค่าจาก GitHub Secrets
        creds_raw = os.environ.get('GOOGLE_CREDS')
        if not creds_raw:
            print("❌ ไม่พบข้อมูล GOOGLE_CREDS ใน Secrets")
            return

        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)

        # 3. ชื่อไฟล์ Sheet ต้องตรงเป๊ะ
        SHEET_NAME = "sites-mon"
        spreadsheet = client.open(SHEET_NAME)
        sheet = spreadsheet.get_worksheet(0)

        # ทดสอบอ่าน O2 เขียน Q2
        val = sheet.acell('O2').value
        print(f"📖 อ่านค่าจาก O2 ได้: {val}")

        if val:
            sheet.update_acell('Q2', f"Success: {val}")
            print("✅ อัปเดต Q2 เรียบร้อยแล้ว!")
        else:
            print("⚠️ ไม่พบข้อมูลใน O2")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")

if __name__ == "__main__":
    run_monitor()
